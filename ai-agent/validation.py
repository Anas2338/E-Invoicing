"""
Environment validation for AI Agent startup.

Validates all required configuration before agent starts to prevent
runtime failures due to missing or invalid configuration.
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when environment validation fails."""
    pass


class EnvironmentValidator:
    """Validates environment configuration for AI Agent."""

    def __init__(self):
        """Initialize validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> bool:
        """
        Validate all required environment variables and configuration.

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValidationError: If critical validation fails
        """
        logger.info("Validating environment configuration...")

        # Run all validation checks
        self._validate_database_url()
        self._validate_ai_configuration()
        self._validate_fbr_configuration()
        self._validate_scheduling_configuration()
        self._validate_file_paths()
        self._validate_business_rules()

        # Report results
        if self.warnings:
            logger.warning("=" * 60)
            logger.warning("CONFIGURATION WARNINGS:")
            for warning in self.warnings:
                logger.warning(f"  [WARN] {warning}")
            logger.warning("=" * 60)

        if self.errors:
            logger.error("=" * 60)
            logger.error("CONFIGURATION ERRORS:")
            for error in self.errors:
                logger.error(f"  [ERROR] {error}")
            logger.error("=" * 60)
            raise ValidationError(
                f"Environment validation failed with {len(self.errors)} error(s). "
                "Please fix the configuration and restart."
            )

        logger.info("[OK] Environment validation passed")
        return True

    def _validate_database_url(self) -> None:
        """Validate DATABASE_URL configuration."""
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            self.errors.append(
                "DATABASE_URL is not set. Required format: "
                "postgresql://USERNAME@HOST:PORT/DATABASE"
            )
            return

        # Parse and validate URL structure
        try:
            parsed = urlparse(database_url)

            if parsed.scheme not in ["postgresql", "postgres"]:
                self.errors.append(
                    f"DATABASE_URL has invalid scheme '{parsed.scheme}'. "
                    "Must be 'postgresql' or 'postgres'"
                )

            if not parsed.hostname:
                self.errors.append("DATABASE_URL is missing hostname")

            if not parsed.path or parsed.path == "/":
                self.errors.append("DATABASE_URL is missing database name")

            # Check for credentials (warning only)
            if not parsed.username or not parsed.password:
                self.warnings.append(
                    "DATABASE_URL is missing username or password. "
                    "This may cause connection failures."
                )

        except Exception as e:
            self.errors.append(f"DATABASE_URL is malformed: {str(e)}")

    def _validate_ai_configuration(self) -> None:
        """Validate AI provider configuration."""
        ai_provider = os.getenv("AI_PROVIDER", "gemini")

        if ai_provider not in ["claude", "gemini"]:
            self.errors.append(
                f"AI_PROVIDER '{ai_provider}' is invalid. "
                "Must be 'claude' or 'gemini'"
            )
            return

        # Validate provider-specific configuration
        if ai_provider == "claude":
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not anthropic_key or anthropic_key == "your_claude_api_key_here":
                self.errors.append(
                    "ANTHROPIC_API_KEY is not configured. "
                    "Required when AI_PROVIDER=claude. "
                    "Get your API key from: https://console.anthropic.com/"
                )
            elif len(anthropic_key) < 20:
                self.warnings.append(
                    "ANTHROPIC_API_KEY looks too short. "
                    "Please verify it's a valid API key."
                )

        elif ai_provider == "gemini":
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if not gemini_key:
                self.errors.append(
                    "GEMINI_API_KEY is not configured. "
                    "Required when AI_PROVIDER=gemini. "
                    "Get your free API key from: https://aistudio.google.com/app/apikey"
                )
            elif len(gemini_key) < 20:
                self.warnings.append(
                    "GEMINI_API_KEY looks too short. "
                    "Please verify it's a valid API key."
                )

    def _validate_fbr_configuration(self) -> None:
        """Validate FBR API configuration."""
        sandbox_url = os.getenv("FBR_SANDBOX_BASE_URL")
        production_url = os.getenv("FBR_PRODUCTION_BASE_URL")

        # Check if at least one is configured
        if not sandbox_url and not production_url:
            self.warnings.append(
                "Neither FBR_SANDBOX_BASE_URL nor FBR_PRODUCTION_BASE_URL is set. "
                "Using default FBR endpoints."
            )

        # Validate URL format if provided
        for url_name, url_value in [
            ("FBR_SANDBOX_BASE_URL", sandbox_url),
            ("FBR_PRODUCTION_BASE_URL", production_url)
        ]:
            if url_value:
                try:
                    parsed = urlparse(url_value)
                    if not parsed.scheme or not parsed.netloc:
                        self.errors.append(
                            f"{url_name} is malformed: {url_value}"
                        )
                except Exception as e:
                    self.errors.append(
                        f"{url_name} is invalid: {str(e)}"
                    )

    def _validate_scheduling_configuration(self) -> None:
        """Validate scheduling configuration."""
        check_interval = os.getenv("AGENT_CHECK_INTERVAL", "300")

        try:
            interval = int(check_interval)
            if interval < 60:
                self.warnings.append(
                    f"AGENT_CHECK_INTERVAL is {interval}s. "
                    "Values < 60s may cause excessive load."
                )
            elif interval > 600:
                self.warnings.append(
                    f"AGENT_CHECK_INTERVAL is {interval}s. "
                    "Values > 600s may delay invoice processing."
                )
        except ValueError:
            self.errors.append(
                f"AGENT_CHECK_INTERVAL '{check_interval}' is not a valid integer"
            )

    def _validate_file_paths(self) -> None:
        """Validate file paths and create directories if needed."""
        app_env = os.getenv("APP_ENV", "development")

        # Determine log directory based on environment
        if app_env == "development":
            log_dir = Path("logs")
        else:
            log_dir = Path("/app/logs")

        # Create log directory if it doesn't exist
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[OK] Log directory ready: {log_dir}")
        except Exception as e:
            self.errors.append(
                f"Cannot create log directory {log_dir}: {str(e)}"
            )

        # Check write permissions
        test_file = log_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            self.errors.append(
                f"Log directory {log_dir} is not writable: {str(e)}"
            )

    def _validate_business_rules(self) -> None:
        """Validate business rule configuration."""
        # Validate priority weights sum to 1.0
        try:
            weight_time = float(os.getenv("PRIORITY_WEIGHT_TIME", "0.5"))
            weight_value = float(os.getenv("PRIORITY_WEIGHT_VALUE", "0.3"))
            weight_retry = float(os.getenv("PRIORITY_WEIGHT_RETRY", "0.2"))

            total_weight = weight_time + weight_value + weight_retry
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point error
                self.warnings.append(
                    f"Priority weights sum to {total_weight:.2f}, not 1.0. "
                    "This may cause unexpected prioritization behavior."
                )

            # Check individual weights are reasonable
            for name, value in [
                ("PRIORITY_WEIGHT_TIME", weight_time),
                ("PRIORITY_WEIGHT_VALUE", weight_value),
                ("PRIORITY_WEIGHT_RETRY", weight_retry)
            ]:
                if value < 0 or value > 1:
                    self.errors.append(
                        f"{name} is {value}, must be between 0 and 1"
                    )

        except ValueError as e:
            self.errors.append(f"Invalid priority weight configuration: {str(e)}")

        # Validate retry configuration
        try:
            retry_max = int(os.getenv("RETRY_MAX_ATTEMPTS", "5"))
            if retry_max < 1:
                self.errors.append("RETRY_MAX_ATTEMPTS must be >= 1")
            elif retry_max > 10:
                self.warnings.append(
                    f"RETRY_MAX_ATTEMPTS is {retry_max}. "
                    "High values may delay failure detection."
                )
        except ValueError:
            self.errors.append("RETRY_MAX_ATTEMPTS must be an integer")

        # Validate anomaly detection thresholds
        try:
            failure_rate = float(os.getenv("ANOMALY_FAILURE_RATE_THRESHOLD", "0.20"))
            if failure_rate < 0 or failure_rate > 1:
                self.errors.append(
                    "ANOMALY_FAILURE_RATE_THRESHOLD must be between 0 and 1"
                )
        except ValueError:
            self.errors.append("ANOMALY_FAILURE_RATE_THRESHOLD must be a float")


def validate_environment() -> None:
    """
    Validate environment configuration and exit if validation fails.

    This function should be called at agent startup before any
    other initialization.

    Raises:
        SystemExit: If validation fails
    """
    try:
        validator = EnvironmentValidator()
        validator.validate_all()
    except ValidationError as e:
        logger.error(f"Environment validation failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}", exc_info=True)
        sys.exit(1)
