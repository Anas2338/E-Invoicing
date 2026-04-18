from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from datetime import timedelta, datetime
from typing import Optional
from sqlmodel import Session, select
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from src.database.session import get_db
from src.models.user import User
from src.schemas.user import UserCreate, UserLogin, UserToken, UserProfile
from src.api.middleware.auth_middleware import require_authentication
from src.utils.jwt_utils import create_access_token, create_refresh_token
from src.utils.helpers import sanitize_input
from src.utils.password_validator import validate_password_strength
from src.utils.encryption import get_encryption_service
from src.utils.security_logging import (
    log_authentication_success,
    log_authentication_failure,
    log_account_locked,
    log_security_event,
    SecurityEventType,
    SecurityEventSeverity
)
from src.config.settings import settings


router = APIRouter()
# PERFORMANCE: Use 10 rounds for faster login (still secure, ~3.8x faster than default 12)
# 10 rounds = ~100ms, 12 rounds = ~400ms per login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


@router.post("/login")
@limiter.limit("5/15minutes")
def login_user(request: Request, user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and set httpOnly cookie with access token.
    Returns user profile without exposing the token.
    Also sets CSRF token for subsequent requests.
    """
    import secrets

    # Sanitize input (but NOT password - passwords must be verified as-is)
    email = sanitize_input(user_login.email)
    password = user_login.password  # Do NOT sanitize passwords!

    logger.info(f"Login attempt for email: {email}")

    try:
        # Find user by email
        statement = select(User).where(User.email == email)
        user = db.exec(statement).first()

        # Get client IP for logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        if not user:
            logger.warning(f"User not found: {email}")
            log_authentication_failure(email, client_ip, user_agent, "User not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"User found: {email}, checking lockout status")

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining_minutes = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            logger.warning(f"Account locked: {email}, remaining: {remaining_minutes} minutes")
            log_account_locked(str(user.id), f"Multiple failed login attempts", client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked due to multiple failed login attempts. Please try again in {remaining_minutes} minutes."
            )

        logger.info(f"Verifying password for: {email}")

        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Password verification failed for: {email}")
            log_authentication_failure(email, client_ip, user_agent, "Invalid password")

            # Increment failed login attempts
            user.failed_login_attempts += 1
            user.last_failed_login_at = datetime.utcnow()

            # Lock account after 5 failed attempts for 30 minutes
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                db.add(user)
                db.commit()
                logger.warning(f"Account locked after 5 failed attempts: {email}")
                log_account_locked(str(user.id), "5 failed login attempts", client_ip)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account locked due to multiple failed login attempts. Please try again in 30 minutes."
                )

            db.add(user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"Password verified for: {email}, checking account status")

        # Check if account is approved
        if user.account_status == 'pending':
            logger.warning(f"Account pending approval: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is pending admin approval. Please wait for approval before logging in."
            )

        if user.account_status == 'rejected':
            rejection_msg = f"Your account has been rejected."
            if user.rejection_reason:
                rejection_msg += f" Reason: {user.rejection_reason}"
            logger.warning(f"Account rejected: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=rejection_msg
            )

        logger.info(f"Account approved, creating tokens for: {email}")

        # Successful login - reset failed attempts and update last login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        db.add(user)
        db.commit()

        # SECURITY: Log successful authentication
        log_authentication_success(str(user.id), client_ip, user_agent)

        # Create access token (2 hours for activity-based timeout)
        access_token_expires = timedelta(hours=2)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            user_token_version=user.token_version,
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Prepare user profile response
        user_profile = {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "approval_flags": user.approval_flags or {},
            "has_production_access": user.approval_flags.get('has_production_access', False) if user.approval_flags else False,
            "can_post_to_production": user.approval_flags.get('can_post_to_production', False) if user.approval_flags else False
        }

        # Create response with httpOnly cookie
        response = JSONResponse(content={"user": user_profile})

        # SECURITY: Use secure cookies in production, allow HTTP in development
        # In development, localhost doesn't use HTTPS, so secure=True breaks cookie functionality
        is_production = settings.app_env.lower() == "production"

        # SECURITY: Always use secure cookies, even in development
        # Use self-signed certificates for local HTTPS instead of disabling security
        # SameSite=Lax provides good balance between security and usability
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # Prevents JavaScript access (XSS protection)
            secure=is_production,  # HTTPS only in production, allow HTTP in development
            samesite="lax",  # Lax works for same-site and top-level navigation
            max_age=7200,  # 2 hours in seconds
            path="/",
            domain=None  # Let browser set domain automatically
        )

        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=is_production,  # HTTPS only in production
            samesite="lax",
            max_age=604800,  # 7 days in seconds
            path="/",
            domain=None
        )

        # SECURITY: Set CSRF token cookie for subsequent requests
        csrf_token = secrets.token_urlsafe(32)
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,  # Must be readable by JavaScript
            secure=is_production,  # HTTPS only in production
            samesite="lax",
            max_age=7200,  # Same as access token (2 hours)
            path="/",
            domain=None
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",  # Generic message for security
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
def logout_user():
    """
    Logout user by clearing authentication cookies.
    """
    response = JSONResponse(content={"message": "Successfully logged out"})

    # Clear access token cookie
    response.delete_cookie(
        key="access_token",
        path="/"
    )

    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/"
    )

    return response


@router.post("/register")
@limiter.limit("3/hour")
def register_user(request: Request, user_create: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user and return access token.
    """
    # Sanitize input
    email = sanitize_input(user_create.email)
    name = sanitize_input(user_create.name) if user_create.name else None

    try:
        # Validate password strength
        is_valid, error_message = validate_password_strength(user_create.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # Check if user already exists
        statement = select(User).where(User.email == email)
        existing_user = db.exec(statement).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        hashed_password = get_password_hash(user_create.password)
        new_user = User(
            email=email,
            name=name,
            hashed_password=hashed_password,
            is_active=True,
            account_status='pending',  # New users start as pending
            approval_flags={"has_production_access": False, "can_post_to_production": False}
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Send notification email to admin
        try:
            from src.utils.email_utils import send_admin_notification_email
            send_admin_notification_email(
                user_email=new_user.email,
                user_name=new_user.name or "N/A",
                user_id=str(new_user.id)
            )
        except Exception as e:
            # Log error but don't fail registration
            print(f"Failed to send admin notification: {str(e)}")

        # Return success message without token (user cannot login until approved)
        return {
            "message": "Registration successful! Your account is pending admin approval. You will receive an email once your account is approved.",
            "email": new_user.email,
            "status": "pending_approval"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/profile", response_model=UserProfile)
def get_profile(
    request: Request,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get the profile of the currently authenticated user.
    """
    logger.info(f"Profile request - user_id: {current_user_id}")
    logger.info(f"Profile request - cookies: {request.cookies.keys()}")
    logger.info(f"Profile request - has access_token cookie: {'access_token' in request.cookies}")

    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            approval_flags=user.approval_flags or {},
            has_production_access=user.approval_flags.get('has_production_access', False) if user.approval_flags else False,
            can_post_to_production=user.approval_flags.get('can_post_to_production', False) if user.approval_flags else False,
            fbr_seller_ntn=user.fbr_seller_ntn,
            fbr_business_name=user.fbr_business_name,
            fbr_seller_province=user.fbr_seller_province,
            fbr_seller_address=user.fbr_seller_address
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {str(e)}"
        )


@router.put("/profile", response_model=UserProfile)
def update_profile(
    request: Request,
    user_update: dict,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Update the profile of the currently authenticated user.
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update name if provided
        if "name" in user_update:
            user.name = sanitize_input(user_update["name"])

        db.add(user)
        db.commit()
        db.refresh(user)

        return UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            approval_flags=user.approval_flags or {},
            has_production_access=user.approval_flags.get('has_production_access', False) if user.approval_flags else False,
            can_post_to_production=user.approval_flags.get('can_post_to_production', False) if user.approval_flags else False,
            fbr_seller_ntn=user.fbr_seller_ntn,
            fbr_business_name=user.fbr_business_name,
            fbr_seller_province=user.fbr_seller_province,
            fbr_seller_address=user.fbr_seller_address
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/refresh")
def refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    Refresh the access token using refresh token from cookie.

    SECURITY: Implements token rotation - issues new refresh token on each use.
    This prevents stolen refresh tokens from being reused indefinitely.
    """
    import secrets

    # Get refresh token from cookie
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )

    try:
        from src.utils.jwt_utils import decode_jwt_token

        # Decode the refresh token
        payload = decode_jwt_token(refresh_token_value)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get user from database to check token_version
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # SECURITY: Create new access token with current token_version
        access_token_expires = timedelta(hours=2)
        new_access_token = create_access_token(
            data={"sub": user_id, "email": email},
            user_token_version=user.token_version,
            expires_delta=access_token_expires
        )

        # SECURITY: Token rotation - create new refresh token
        new_refresh_token = create_refresh_token(
            data={"sub": user_id, "email": email}
        )

        # Create response
        response = JSONResponse(content={"message": "Token refreshed successfully"})

        # Set new access token cookie
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7200,  # 2 hours
            path="/",
            domain=None
        )

        # SECURITY: Set new refresh token cookie (token rotation)
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=604800,  # 7 days
            path="/",
            domain=None
        )

        # Rotate CSRF token as well
        csrf_token = secrets.token_urlsafe(32)
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            secure=True,
            samesite="lax",
            max_age=7200,
            path="/",
            domain=None
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/permissions")
def get_permissions(
    request: Request,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get the permissions of the currently authenticated user.
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        approval_flags = user.approval_flags or {}

        return {
            "user_id": str(user.id),
            "permissions": {
                "has_production_access": approval_flags.get("has_production_access", False),
                "can_post_to_production": approval_flags.get("can_post_to_production", False),
                "can_validate_invoices": True,
                "can_view_own_invoices": True,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {str(e)}"
        )

@router.put("/profile/fbr-credentials")
def update_fbr_credentials(
    request: Request,
    credentials: dict,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Update FBR credentials for the currently authenticated user.
    Supports updating tokens for specific environments (SANDBOX or PRODUCTION).
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Determine which environment to update
        target_environment = credentials.get("fbr_environment", user.fbr_environment or "SANDBOX")

        if target_environment not in ["SANDBOX", "PRODUCTION"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid environment. Must be SANDBOX or PRODUCTION"
            )

        # Update FBR tokens - handle both sandbox and production
        encryption_service = get_encryption_service()

        if "fbr_sandbox_token" in credentials:
            token = credentials["fbr_sandbox_token"]
            if token and token.strip():
                # Encrypt and store token
                user.fbr_sandbox_token = encryption_service.encrypt(token.strip())
            else:
                # Empty string means delete the token
                user.fbr_sandbox_token = None

        if "fbr_production_token" in credentials:
            token = credentials["fbr_production_token"]
            if token and token.strip():
                # Encrypt and store token
                user.fbr_production_token = encryption_service.encrypt(token.strip())
            else:
                # Empty string means delete the token
                user.fbr_production_token = None

        # Legacy support: handle fbr_access_token for backward compatibility
        if "fbr_access_token" in credentials:
            token = credentials["fbr_access_token"]
            encrypted_token = encryption_service.encrypt(token)

            if target_environment == "SANDBOX":
                user.fbr_sandbox_token = encrypted_token
            else:
                user.fbr_production_token = encrypted_token

        # Update current environment preference
        if "fbr_environment" in credentials:
            user.fbr_environment = target_environment

        # Update other FBR settings (no HTML escaping - these are sent to FBR API)
        if "fbr_seller_ntn" in credentials:
            user.fbr_seller_ntn = credentials["fbr_seller_ntn"].strip() if credentials["fbr_seller_ntn"] else None

        if "fbr_business_name" in credentials:
            user.fbr_business_name = credentials["fbr_business_name"].strip() if credentials["fbr_business_name"] else None

        if "fbr_seller_province" in credentials:
            user.fbr_seller_province = credentials["fbr_seller_province"].strip() if credentials["fbr_seller_province"] else None

        if "fbr_seller_address" in credentials:
            user.fbr_seller_address = credentials["fbr_seller_address"].strip() if credentials["fbr_seller_address"] else None

        # Explicitly add to session and commit
        db.add(user)
        db.flush()  # Flush to ensure changes are written
        db.commit()
        db.refresh(user)

        logger.info(f"FBR credentials updated for user {current_user_id}, environment: {target_environment}")
        logger.info(f"Has sandbox token: {bool(user.fbr_sandbox_token)}, Has production token: {bool(user.fbr_production_token)}")

        return {
            "success": True,
            "message": f"FBR credentials updated successfully for {target_environment}",
            "fbr_environment": user.fbr_environment,
            "fbr_seller_ntn": user.fbr_seller_ntn,
            "fbr_business_name": user.fbr_business_name,
            "fbr_seller_province": user.fbr_seller_province,
            "fbr_seller_address": user.fbr_seller_address,
            "has_sandbox_token": bool(user.fbr_sandbox_token),
            "has_production_token": bool(user.fbr_production_token)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update FBR credentials: {str(e)}"
        )


@router.get("/profile/fbr-credentials")
def get_fbr_credentials(
    request: Request,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get FBR credentials for the currently authenticated user.
    Returns both sandbox and production tokens (decrypted).
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Decrypt tokens if they exist
        encryption_service = get_encryption_service()

        sandbox_token = None
        production_token = None

        if user.fbr_sandbox_token:
            try:
                sandbox_token = encryption_service.decrypt(user.fbr_sandbox_token)
            except Exception as e:
                logger.error(f"Failed to decrypt sandbox token: {e}")

        if user.fbr_production_token:
            try:
                production_token = encryption_service.decrypt(user.fbr_production_token)
            except Exception as e:
                logger.error(f"Failed to decrypt production token: {e}")

        return {
            "fbr_environment": user.fbr_environment or "SANDBOX",
            "fbr_seller_ntn": user.fbr_seller_ntn,
            "fbr_business_name": user.fbr_business_name,
            "fbr_seller_province": user.fbr_seller_province,
            "fbr_seller_address": user.fbr_seller_address,
            "fbr_sandbox_token": sandbox_token,
            "fbr_production_token": production_token,
            "has_sandbox_token": bool(user.fbr_sandbox_token),
            "has_production_token": bool(user.fbr_production_token),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {str(e)}"
        )


@router.delete("/profile/fbr-credentials")
def delete_fbr_credentials(
    request: Request,
    environment: str = None,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Delete FBR access token for a specific environment.
    Query parameter 'environment' should be 'SANDBOX' or 'PRODUCTION'.
    If not specified, deletes the token for the current environment.
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Determine which environment to delete
        env_to_delete = environment or user.fbr_environment or "SANDBOX"

        if env_to_delete not in ["SANDBOX", "PRODUCTION"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Environment must be SANDBOX or PRODUCTION"
            )

        # Clear the appropriate token
        if env_to_delete == "SANDBOX":
            user.fbr_sandbox_token = None
            message = "Sandbox FBR access token deleted successfully"
        else:
            user.fbr_production_token = None
            message = "Production FBR access token deleted successfully"

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": message,
            "environment": env_to_delete,
            "has_sandbox_token": bool(user.fbr_sandbox_token),
            "has_production_token": bool(user.fbr_production_token)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete FBR credentials: {str(e)}"
        )


@router.get("/users/me/environment")
def get_environment_preference(
    request: Request,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get the user's environment preference (SANDBOX or PRODUCTION).
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Determine if user can access production
        # User can access production if they have production token or specific approval flags
        can_access_production = bool(user.fbr_production_token)

        return {
            "environment": user.fbr_environment or "SANDBOX",
            "canAccessProduction": can_access_production
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get environment preference: {str(e)}"
        )


@router.put("/users/me/environment")
def update_environment_preference(
    request: Request,
    environment_data: dict,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Update the user's environment preference (SANDBOX or PRODUCTION).
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        environment = environment_data.get("environment", "").upper()

        if environment not in ["SANDBOX", "PRODUCTION"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Environment must be SANDBOX or PRODUCTION"
            )

        # Check if user can access production
        can_access_production = bool(user.fbr_production_token)

        if environment == "PRODUCTION" and not can_access_production:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to the production environment"
            )

        # Update environment preference
        user.fbr_environment = environment
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "environment": user.fbr_environment,
            "canAccessProduction": can_access_production
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update environment preference: {str(e)}"
        )
