from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.api.deps import get_database_session
from src.schemas.password_reset import (
    PasswordResetRequest,
    PasswordResetVerify,
    PasswordResetConfirm,
    PasswordResetResponse
)
from src.services.password_reset_service import PasswordResetService

router = APIRouter()


@router.post("/request", response_model=PasswordResetResponse)
def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_database_session)
):
    """
    Request a password reset. Sends an email with a reset token.
    """
    # Create reset token
    token = PasswordResetService.create_reset_token(db, request.email)

    if not token:
        # For security, don't reveal if email exists or not
        return PasswordResetResponse(
            success=True,
            message="If an account exists with this email, a password reset link has been sent."
        )

    # Send reset email
    PasswordResetService.send_reset_email(request.email, token)

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
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
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
