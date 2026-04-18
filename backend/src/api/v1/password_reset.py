from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.database.session import get_db
from src.api.deps import get_database_session
from src.schemas.password_reset import (
    PasswordResetRequest,
    PasswordResetVerify,
    PasswordResetConfirm,
    PasswordResetResponse
)
from src.services.password_reset_service import PasswordResetService
from src.utils.password_validator import validate_password_strength

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/request", response_model=PasswordResetResponse)
@limiter.limit("3/hour")
def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_database_session)
):
    """
    Request a password reset. Sends an email with a reset token.

    SECURITY: Uses constant-time response to prevent account enumeration via timing attacks.
    """
    import time
    import random

    # Record start time for constant-time response
    start_time = time.time()

    # Create reset token
    token = PasswordResetService.create_reset_token(db, reset_request.email)

    if token:
        # Send reset email only if user exists
        PasswordResetService.send_reset_email(reset_request.email, token)
    else:
        # SECURITY: Perform dummy operation to match timing of real operation
        # This prevents timing attacks that could reveal if an email exists
        dummy_token = PasswordResetService.generate_reset_token()
        # Simulate email sending delay
        time.sleep(random.uniform(0.05, 0.15))

    # SECURITY: Add constant delay to make all responses take similar time
    # This prevents attackers from determining if an email exists based on response time
    elapsed = time.time() - start_time
    target_time = 0.5  # Target 500ms response time

    if elapsed < target_time:
        time.sleep(target_time - elapsed + random.uniform(-0.05, 0.05))

    # Always return the same generic message (security best practice)
    return PasswordResetResponse(
        success=True,
        message="If an account exists with this email, a password reset link has been sent."
    )


@router.post("/verify", response_model=PasswordResetResponse)
def verify_reset_token(
    request: PasswordResetVerify,
    db: Session = Depends(get_database_session)
):
    """
    Verify if a reset token is valid.
    """
    user = PasswordResetService.verify_reset_token(db, request.token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return PasswordResetResponse(
        success=True,
        message="Token is valid"
    )


@router.post("/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_database_session)
):
    """
    Confirm password reset with new password.
    """
    # Validate password strength
    is_valid, error_message = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Reset password
    success = PasswordResetService.reset_password(db, request.token, request.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return PasswordResetResponse(
        success=True,
        message="Password has been reset successfully"
    )
