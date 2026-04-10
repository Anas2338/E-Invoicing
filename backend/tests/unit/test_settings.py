import pytest
from unittest.mock import patch, MagicMock


def test_settings_defaults():
    """Test that settings can be created with default values."""
    from src.config.settings import Settings
    from pydantic_settings import SettingsConfigDict

    # Create settings without loading .env file
    class TestSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=True,
            populate_by_name=True
        )

    with patch.dict('os.environ', {}, clear=True):
        settings = TestSettings()

        # Check that defaults are applied
        assert settings.database_url == "postgresql://localhost/fbr_invoices"
        assert settings.auth_jwt_secret == "dev-secret-key-change-in-production"
        assert settings.fbr_sandbox_base_url == "https://gw.fbr.gov.pk/di_data/v1/di"
        assert settings.fbr_production_base_url == "https://gw.fbr.gov.pk/di_data/v1/di"
        assert settings.app_env == "development"
        assert settings.log_level == "INFO"


def test_settings_can_be_instantiated():
    """Test that settings can be instantiated."""
    from src.config.settings import Settings

    # Just test that we can create an instance
    settings = Settings()
    assert settings is not None


def test_settings_required_fields_exist():
    """Test that all expected settings fields exist."""
    from src.config.settings import Settings

    with patch.dict('os.environ', {}, clear=True):
        settings = Settings()

        # Check that all expected attributes exist
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'auth_jwt_secret')
        assert hasattr(settings, 'fbr_sandbox_base_url')
        assert hasattr(settings, 'fbr_production_base_url')
        assert hasattr(settings, 'app_env')
        assert hasattr(settings, 'log_level')
        assert hasattr(settings, 'allowed_origins')