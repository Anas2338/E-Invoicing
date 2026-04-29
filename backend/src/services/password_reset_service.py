import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from src.models.user import User
from src.utils.email_utils import send_password_reset_email

# Use same bcrypt context as password hashing for consistency
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)


class PasswordResetService:
    """
    Service for handling password reset operations.
    """

    @staticmethod
    def generate_reset_token() -> str:
        """
        Generate a secure random token for password reset.
        Returns the raw token (to send to user via email).
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a reset token for secure storage using bcrypt.

        SECURITY: Tokens are hashed with bcrypt (slow hash) before storage so that
        if the database is compromised, attackers cannot easily brute-force the tokens.

        Using bcrypt instead of SHA-256 makes brute-force attacks computationally expensive.

        Args:
            token: Raw token to hash

        Returns:
            Bcrypt hash of the token
        """
        return pwd_context.hash(token)

    @staticmethod
    def create_reset_token(db: Session, email: str) -> Optional[str]:
        """
        Create a password reset token for a user.

        Args:
            db: Database session
            email: User's email address

        Returns:
            Reset token if user exists, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()

        if not user:
            return None

        # Generate token (raw token to send to user)
        raw_token = PasswordResetService.generate_reset_token()

        # Hash token for secure storage
        # SECURITY: Store only the hash, not the raw token
        token_hash = PasswordResetService.hash_token(raw_token)

        # Set token expiration (1 hour from now)
        expires = datetime.utcnow() + timedelta(hours=1)

        # Update user with hashed token
        user.reset_token = token_hash
        user.reset_token_expires = expires

        db.add(user)
        db.commit()

        # Return raw token (to send via email)
        # The raw token is never stored in the database
        return raw_token

    @staticmethod
    def verify_reset_token(db: Session, token: str) -> Optional[User]:
        """
        Verify a password reset token.

        SECURITY: Uses bcrypt's verify method for constant-time comparison
        to prevent timing attacks.

        Args:
            db: Database session
            token: Raw reset token to verify (from email link)

        Returns:
            User if token is valid, None otherwise
        """
        # Find all users with non-null reset tokens
        users = db.query(User).filter(User.reset_token.isnot(None)).all()

        # Check each user's token using bcrypt verify (constant-time)
        for user in users:
            if user.reset_token and pwd_context.verify(token, user.reset_token):
                # Check if token has expired
                if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
                    return None
                return user

        return None

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> bool:
        """
        Reset user's password using a valid token.
        Increments token_version to invalidate all existing sessions.

        Args:
            db: Database session
            token: Reset token
            new_password: New password to set

        Returns:
            True if password was reset successfully, False otherwise
        """
        user = PasswordResetService.verify_reset_token(db, token)

        if not user:
            return False

        # Hash the new password
        hashed_password = pwd_context.hash(new_password)

        # Update user's password and clear reset token
        user.hashed_password = hashed_password
        user.reset_token = None
        user.reset_token_expires = None

        # Increment token version to invalidate all existing sessions
        user.token_version += 1

        db.add(user)
        db.commit()

        return True

    @staticmethod
    def send_reset_email(email: str, token: str, frontend_url: str = "http://localhost:3000") -> bool:
        """
        Send password reset email to user using Resend.

        Args:
            email: User's email address
            token: Reset token
            frontend_url: Frontend URL for reset link

        Returns:
            True (always returns True to prevent account enumeration via timing)
        """
        try:
            # Send email using Resend via email_utils
            send_password_reset_email(email, token, frontend_url)
        except Exception as e:
            # Log error but don't expose it to prevent account enumeration
            print(f"⚠️ Error sending password reset email: {str(e)}")

        # Always return True to prevent account enumeration
        # (Don't reveal whether email exists or sending succeeded)
        return True
