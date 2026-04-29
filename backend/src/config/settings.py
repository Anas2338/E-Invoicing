from pydantic_settings import BaseSettings
from typing import List, Optional, Union
from pydantic import Field, field_validator
import json


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Application settings (defined first so available for validation)
    app_env: str = Field(default="development", validation_alias="APP_ENV")

    # Database settings
    database_url: str = Field(default="postgresql://localhost/fbr_invoices", validation_alias="DATABASE_URL")
    automation_database_url: str = Field(default="postgresql://localhost/fbr_automation", validation_alias="AUTOMATION_DATABASE_URL")

    # Authentication settings
    auth_jwt_secret: str = Field(validation_alias="AUTH_JWT_SECRET")
    auth_issuer: Optional[str] = Field(default="fbr-invoice-portal", validation_alias="AUTH_ISSUER")
    auth_audience: Optional[str] = Field(default="fbr-invoice-portal", validation_alias="AUTH_AUDIENCE")

    # Encryption key for sensitive data (FBR tokens, etc.)
    encryption_key: str = Field(validation_alias="ENCRYPTION_KEY")

    @field_validator('auth_jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT secret strength - enforced in ALL environments."""
        if not v:
            raise ValueError("AUTH_JWT_SECRET must be set")

        # Reject the old insecure default
        if v == "dev-secret-key-change-in-production":
            raise ValueError(
                "Default JWT secret detected. Generate a secure secret with: "
                "openssl rand -base64 32"
            )

        # SECURITY: Enforce strong secrets in ALL environments (dev, staging, production)
        # Weak secrets in development can lead to compromised dev databases and lateral movement
        if len(v) < 32:
            raise ValueError(
                "AUTH_JWT_SECRET must be at least 32 characters in ALL environments. "
                "Generate with: openssl rand -base64 32"
            )

        # Additional entropy check: ensure secret is not all same character or simple pattern
        if len(set(v)) < 10:
            raise ValueError(
                "AUTH_JWT_SECRET has insufficient entropy. "
                "Generate a cryptographically secure secret with: openssl rand -base64 32"
            )

        return v

    @field_validator('encryption_key')
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        """Validate encryption key strength - required for encrypting sensitive data."""
        if not v:
            raise ValueError(
                "ENCRYPTION_KEY not set. Generate with: openssl rand -base64 44"
            )

        # Ensure sufficient length for AES-256 encryption
        if len(v) < 32:
            raise ValueError(
                "ENCRYPTION_KEY must be at least 32 characters. "
                "Generate with: openssl rand -base64 44"
            )

        # Additional entropy check
        if len(set(v)) < 10:
            raise ValueError(
                "ENCRYPTION_KEY has insufficient entropy. "
                "Generate a cryptographically secure key with: openssl rand -base64 44"
            )

        return v

    # FBR API settings
    fbr_sandbox_base_url: str = Field(default="https://gw.fbr.gov.pk/di_data/v1/di", validation_alias="FBR_SANDBOX_BASE_URL")
    fbr_production_base_url: str = Field(default="https://gw.fbr.gov.pk/di_data/v1/di", validation_alias="FBR_PRODUCTION_BASE_URL")
    fbr_api_key: str = Field(default="", validation_alias="FBR_API_KEY")
    fbr_client_id: str = Field(default="", validation_alias="FBR_CLIENT_ID")

    # AI Agent settings
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # Transfer Configuration (Pakistan Time - PKT is UTC+5)
    transfer_schedule_hour: int = Field(default=18, validation_alias="TRANSFER_SCHEDULE_HOUR")
    transfer_schedule_minute: int = Field(default=0, validation_alias="TRANSFER_SCHEDULE_MINUTE")

    # Cleanup Configuration
    cleanup_schedule_hour: int = Field(default=2, validation_alias="CLEANUP_SCHEDULE_HOUR")
    cleanup_schedule_minute: int = Field(default=0, validation_alias="CLEANUP_SCHEDULE_MINUTE")
    cleanup_retention_days: int = Field(default=2, validation_alias="CLEANUP_RETENTION_DAYS")
    automation_log_retention_days: int = Field(default=90, validation_alias="AUTOMATION_LOG_RETENTION_DAYS")

    # Additional application settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    max_invoice_size: int = Field(default=1048576, validation_alias="MAX_INVOICE_SIZE")  # 1MB in bytes

    # Database logging - Set to true to log all SQL queries (useful for debugging)
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    # Dry Run Mode - Simulates FBR responses without actual API calls (for testing)
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")

    # CORS settings - accepts JSON array, comma-separated string, or single URL
    allowed_origins: Union[List[str], str] = Field(default="http://localhost:3000", validation_alias="ALLOWED_ORIGINS")

    # Email settings (Resend)
    resend_api_key: str = Field(default="", validation_alias="RESEND_API_KEY")
    email_from_address: str = Field(default="noreply@yourdomain.com", validation_alias="EMAIL_FROM_ADDRESS")
    email_from_name: str = Field(default="E-Invoicing Portal", validation_alias="EMAIL_FROM_NAME")
    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from various formats: JSON array, comma-separated, or single URL"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Try parsing as JSON first
            if v.strip().startswith('['):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Try comma-separated
            if ',' in v:
                return [origin.strip() for origin in v.split(',') if origin.strip()]
            # Single URL
            if v.strip():
                return [v.strip()]
        # Default fallback
        return ["http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "populate_by_name": True,
        "extra": "ignore"  # Ignore extra environment variables (e.g., from AI agent)
    }


# Create settings instance
settings = Settings()
