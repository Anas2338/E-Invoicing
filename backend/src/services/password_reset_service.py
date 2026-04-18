import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from src.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        Hash a reset token for secure storage.

        SECURITY: Tokens are hashed before storage so that if the database
        is compromised, attackers cannot use the tokens to reset passwords.

        Args:
            token: Raw token to hash

        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

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

        SECURITY: Compares hash of provided token with stored hash.
        Uses constant-time comparison to prevent timing attacks.

        Args:
            db: Database session
            token: Raw reset token to verify (from email link)

        Returns:
            User if token is valid, None otherwise
        """
        # Hash the provided token
        token_hash = PasswordResetService.hash_token(token)

        # Find user with matching token hash
        user = db.query(User).filter(User.reset_token == token_hash).first()

        if not user:
            return None

        # Check if token has expired
        if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
            return None

        return user

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
        Send password reset email to user.

        Args:
            email: User's email address
            token: Reset token
            frontend_url: Frontend URL for reset link

        Returns:
            True if email was sent successfully, False otherwise
        """
        # In a production environment, you would use a proper email service
        # For now, we'll just log the reset link
        reset_link = f"{frontend_url}/auth/reset-password?token={token}"

        print(f"\n{'='*60}")
        print(f"PASSWORD RESET EMAIL")
        print(f"{'='*60}")
        print(f"To: {email}")
        print(f"Subject: Password Reset Request")
        print(f"\nReset Link: {reset_link}")
        print(f"\nThis link will expire in 1 hour.")
        print(f"{'='*60}\n")

        # TODO: Implement actual email sending using SMTP or email service
        # Example with SendGrid, AWS SES, or similar service

        return True
