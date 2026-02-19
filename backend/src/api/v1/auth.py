from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import timedelta
from typing import Optional
from sqlmodel import Session, select
from passlib.context import CryptContext

from src.database.session import get_db
from src.models.user import User
from src.schemas.user import UserCreate, UserLogin, UserToken, UserProfile
from src.api.middleware.auth_middleware import require_authentication
from src.utils.jwt_utils import create_access_token, create_refresh_token
from src.utils.helpers import sanitize_input


router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


@router.post("/login", response_model=UserToken)
def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return access token.
    """
    # Sanitize input
    email = sanitize_input(user_login.email)
    password = sanitize_input(user_login.password)

    try:
        # Find user by email
        statement = select(User).where(User.email == email)
        user = db.exec(statement).first()

        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return UserToken(
            access_token=access_token,
            token_type="bearer",
            user=UserProfile(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
                approval_flags=user.approval_flags or {},
                has_production_access=user.approval_flags.get('has_production_access', False) if user.approval_flags else False,
                can_post_to_production=user.approval_flags.get('can_post_to_production', False) if user.approval_flags else False
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserToken)
def register_user(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user and return access token.
    """
    # Sanitize input
    email = sanitize_input(user_create.email)
    name = sanitize_input(user_create.name) if user_create.name else None

    try:
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
            approval_flags={"has_production_access": False, "can_post_to_production": False}
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(new_user.id), "email": new_user.email},
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token = create_refresh_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )

        return UserToken(
            access_token=access_token,
            token_type="bearer",
            user=UserProfile(
                id=new_user.id,
                email=new_user.email,
                name=name,
                is_active=True,
                created_at=new_user.created_at,
                updated_at=new_user.updated_at,
                approval_flags=new_user.approval_flags,
                has_production_access=False,
                can_post_to_production=False
            )
        )
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
def refresh_token(refresh_token: str):
    """
    Refresh the access token.
    """
    try:
        from src.utils.jwt_utils import decode_jwt_token

        # Decode the refresh token
        payload = decode_jwt_token(refresh_token)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Create new access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user_id, "email": email},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
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

        # Update FBR token for the specified environment
        if "fbr_access_token" in credentials:
            token = credentials["fbr_access_token"]
            if target_environment == "SANDBOX":
                user.fbr_sandbox_token = token
            else:
                user.fbr_production_token = token

        # Update current environment preference
        if "fbr_environment" in credentials:
            user.fbr_environment = target_environment

        # Update other FBR settings
        if "fbr_seller_ntn" in credentials:
            user.fbr_seller_ntn = sanitize_input(credentials["fbr_seller_ntn"])

        if "fbr_business_name" in credentials:
            user.fbr_business_name = sanitize_input(credentials["fbr_business_name"])

        if "fbr_seller_province" in credentials:
            user.fbr_seller_province = sanitize_input(credentials["fbr_seller_province"])

        if "fbr_seller_address" in credentials:
            user.fbr_seller_address = sanitize_input(credentials["fbr_seller_address"])

        db.add(user)
        db.commit()
        db.refresh(user)

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
    Returns both sandbox and production tokens.
    """
    try:
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "fbr_environment": user.fbr_environment or "SANDBOX",
            "fbr_seller_ntn": user.fbr_seller_ntn,
            "fbr_business_name": user.fbr_business_name,
            "fbr_seller_province": user.fbr_seller_province,
            "fbr_seller_address": user.fbr_seller_address,
            "fbr_sandbox_token": user.fbr_sandbox_token,
            "fbr_production_token": user.fbr_production_token,
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
