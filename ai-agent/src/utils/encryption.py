"""
Encryption utility for sensitive data at rest.
Uses Fernet (symmetric encryption) for token encryption.
"""
from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
import base64
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting/decrypting sensitive data."""

    def __init__(self, encryption_key: str):
        """
        Initialize with encryption key.

        Args:
            encryption_key: Base64-encoded encryption key (44 characters)
        """
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY not set. Generate with: "
                "openssl rand -base64 32"
            )

        # SECURITY: Validate encryption key format and strength
        # Fernet requires a 32-byte key encoded as base64 (44 characters)
        try:
            # Attempt to decode the key
            decoded_key = base64.urlsafe_b64decode(encryption_key.encode())

            # Validate key length (must be exactly 32 bytes for Fernet)
            if len(decoded_key) != 32:
                raise ValueError(
                    f"ENCRYPTION_KEY must be exactly 32 bytes when decoded (44 base64 characters). "
                    f"Current decoded length: {len(decoded_key)} bytes. "
                    f"Generate a valid key with: openssl rand -base64 32"
                )

            # Validate key entropy (ensure it's not all zeros or simple pattern)
            if len(set(decoded_key)) < 16:
                raise ValueError(
                    "ENCRYPTION_KEY has insufficient entropy. "
                    "Generate a cryptographically secure key with: openssl rand -base64 32"
                )

            # Initialize Fernet cipher
            self.cipher = Fernet(encryption_key.encode())

            # Test the cipher with a simple encrypt/decrypt operation
            test_data = b"test_encryption_key_validity"
            encrypted = self.cipher.encrypt(test_data)
            decrypted = self.cipher.decrypt(encrypted)

            if decrypted != test_data:
                raise ValueError("ENCRYPTION_KEY validation failed: encrypt/decrypt test failed")

            logger.info("Encryption service initialized successfully with validated key")

        except base64.binascii.Error as e:
            raise ValueError(
                f"ENCRYPTION_KEY is not valid base64. Generate with: openssl rand -base64 32. Error: {e}"
            )
        except InvalidToken as e:
            raise ValueError(
                f"ENCRYPTION_KEY is not a valid Fernet key. Generate with: openssl rand -base64 32. Error: {e}"
            )
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_if_not_empty(self, plaintext: Optional[str]) -> Optional[str]:
        """Encrypt only if plaintext is not None or empty."""
        if plaintext:
            return self.encrypt(plaintext)
        return None

    def decrypt_if_not_empty(self, ciphertext: Optional[str]) -> Optional[str]:
        """Decrypt only if ciphertext is not None or empty."""
        if ciphertext:
            return self.decrypt(ciphertext)
        return None


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service singleton."""
    global _encryption_service
    if _encryption_service is None:
        from src.config.settings import settings
        _encryption_service = EncryptionService(settings.encryption_key)
    return _encryption_service
