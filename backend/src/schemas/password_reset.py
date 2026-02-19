from pydantic import BaseModel, EmailStr


class PasswordResetRequest(BaseModel):
    """
    Schema for requesting a password reset.
    """
    email: EmailStr


class PasswordResetVerify(BaseModel):
    """
    Schema for verifying a reset token.
    """
    token: str


class PasswordResetConfirm(BaseModel):
    """
    Schema for confirming password reset with new password.
    """
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    """
    Schema for password reset response.
    """
    success: bool
    message: str
