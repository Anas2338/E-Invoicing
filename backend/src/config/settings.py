from pydantic_settings import BaseSettings
from typing import List, Optional, Union
from pydantic import Field, field_validator
import json


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Database settings
    database_url: str = Field(default="postgresql://localhost/fbr_invoices", validation_alias="DATABASE_URL")

    # Authentication settings
    auth_jwt_secret: str = Field(default="dev-secret-key-change-in-production", validation_alias="AUTH_JWT_SECRET")
    auth_issuer: Optional[str] = Field(default="fbr-invoice-portal", validation_alias="AUTH_ISSUER")
    auth_audience: Optional[str] = Field(default="fbr-invoice-portal", validation_alias="AUTH_AUDIENCE")

    # FBR API settings
    fbr_sandbox_base_url: str = Field(default="https://gw.fbr.gov.pk/di_data/v1/di", validation_alias="FBR_SANDBOX_BASE_URL")
    fbr_production_base_url: str = Field(default="https://gw.fbr.gov.pk/di_data/v1/di", validation_alias="FBR_PRODUCTION_BASE_URL")

    # Application settings
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    max_invoice_size: int = Field(default=1048576, validation_alias="MAX_INVOICE_SIZE")  # 1MB in bytes

    # CORS settings - accepts JSON array, comma-separated string, or single URL
    allowed_origins: Union[List[str], str] = Field(default="http://localhost:3000", validation_alias="ALLOWED_ORIGINS")

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
        "populate_by_name": True
    }


# Create settings instance
settings = Settings()
