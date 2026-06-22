from pydantic_settings import BaseSettings
from typing import List, Optional, Union
from pydantic import Field, field_validator
import json


class Settings(BaseSettings):
    """Automation-specific settings loaded from environment variables."""

    # Application settings
    app_env: str = Field(default="development", validation_alias="APP_ENV")

    # Database settings
    automation_database_url: str = Field(default="postgresql://localhost/fbr_automation", validation_alias="AUTOMATION_DATABASE_URL")
    main_database_url: str = Field(default="", validation_alias="DATABASE_URL")

    # Authentication settings (MUST match main backend)
    auth_jwt_secret: str = Field(validation_alias="AUTH_JWT_SECRET")
    auth_issuer: Optional[str] = Field(default="fbr-invoice-portal", validation_alias="AUTH_ISSUER")
    auth_audience: Optional[str] = Field(default="fbr-invoice-portal", validation_alias="AUTH_AUDIENCE")

    # Encryption key
    encryption_key: str = Field(validation_alias="ENCRYPTION_KEY")

    @field_validator('auth_jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        if not v:
            raise ValueError("AUTH_JWT_SECRET must be set")
        if v == "dev-secret-key-change-in-production":
            raise ValueError("Default JWT secret detected. Generate a secure secret.")
        if len(v) < 32:
            raise ValueError("AUTH_JWT_SECRET must be at least 32 characters.")
        if len(set(v)) < 10:
            raise ValueError("AUTH_JWT_SECRET has insufficient entropy.")
        return v

    @field_validator('encryption_key')
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        if not v:
            raise ValueError("ENCRYPTION_KEY not set.")
        if len(v) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters.")
        if len(set(v)) < 10:
            raise ValueError("ENCRYPTION_KEY has insufficient entropy.")
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

    # Application settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")

    # CORS settings
    allowed_origins: Union[List[str], str] = Field(
        default="http://localhost:3000,https://taxntec.com,https://www.taxntec.com",
        validation_alias="ALLOWED_ORIGINS"
    )

    # CSRF
    csrf_secret: str = Field(default="change-me", validation_alias="CSRF_SECRET")

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if v.strip().startswith('['):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            if ',' in v:
                return [origin.strip() for origin in v.split(',') if origin.strip()]
            if v.strip():
                return [v.strip()]
        return ["http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "populate_by_name": True,
        "extra": "ignore",
    }


settings = Settings()
