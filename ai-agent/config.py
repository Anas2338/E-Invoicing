"""
AI Agent Configuration Management.

Loads configuration from environment variables and provides
business rule configuration for intelligent processing.
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration for AI Agent."""

    def __init__(self):
        """Initialize configuration from environment variables."""

        # Application Settings (must be first for AI_PROVIDER default)
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        # Dry Run Mode - Simulates FBR responses without actual API calls
        # Set to "true" for testing without posting to real FBR
        self.DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

        # Database Configuration
        # AI Agent uses automation database for processing bulk uploads
        self.DATABASE_URL: str = os.getenv(
            "AUTOMATION_DATABASE_URL",
            os.getenv("DATABASE_URL", "postgresql://localhost/fbr_automation")
        )

        # AI Configuration
        self.AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini" if self.APP_ENV == "development" else "claude")

        # Claude Configuration (Production)
        self.ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
        if self.AI_PROVIDER == "claude" and (not self.ANTHROPIC_API_KEY or self.ANTHROPIC_API_KEY == "your_claude_api_key_here"):
            import logging
            logging.warning("ANTHROPIC_API_KEY not configured - Claude AI features will not work")

        # Gemini Configuration (Development/Free)
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        if self.AI_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            import logging
            logging.warning("GEMINI_API_KEY not configured - Gemini AI features will not work")

        # FBR API Configuration
        self.FBR_SANDBOX_BASE_URL: str = os.getenv(
            "FBR_SANDBOX_BASE_URL",
            "https://gw.fbr.gov.pk/di_data/v1/di"
        )
        self.FBR_PRODUCTION_BASE_URL: str = os.getenv(
            "FBR_PRODUCTION_BASE_URL",
            "https://gw.fbr.gov.pk/di_data/v1/di"
        )

        # Agent Scheduling Configuration
        self.AGENT_CHECK_INTERVAL: int = int(os.getenv("AGENT_CHECK_INTERVAL", "300"))  # 5 minutes in seconds
        self.HEALTH_CHECK_CRON: str = "0 * * * *"  # Every hour at minute 0

        # Log file path - use local path for development, Docker path for production
        if self.APP_ENV == "development":
            self.LOG_FILE: Path = Path("logs/agent.log")
        else:
            self.LOG_FILE: Path = Path("/app/logs/agent.log")

        # Agent Metadata
        self.AGENT_VERSION: str = "1.0.0"

        # Heartbeat Configuration
        self.HEARTBEAT_FILE: Path = Path("/tmp/agent_heartbeat.txt")

        # Business Rules - Priority Weights
        self.PRIORITY_WEIGHT_TIME: float = 0.5  # Weight for scheduled time proximity
        self.PRIORITY_WEIGHT_VALUE: float = 0.3  # Weight for invoice value
        self.PRIORITY_WEIGHT_RETRY: float = 0.2  # Weight for retry count

        # Business Rules - Retry Configuration
        self.RETRY_BASE_DELAY: int = 60  # Base delay in seconds (1 minute)
        self.RETRY_MAX_ATTEMPTS: int = 5  # Maximum retry attempts
        self.RETRY_JITTER_MAX: int = 30  # Maximum jitter in seconds

        # Business Rules - Circuit Breaker
        self.CIRCUIT_BREAKER_THRESHOLD: int = 3  # Consecutive failures before opening circuit
        self.CIRCUIT_BREAKER_TIMEOUT: int = 300  # Circuit breaker timeout in seconds (5 minutes)

        # Business Rules - Anomaly Detection Thresholds
        self.ANOMALY_FAILURE_RATE_THRESHOLD: float = 0.20  # 20% failure rate
        self.ANOMALY_FAILURE_RATE_WINDOW: int = 3600  # 1 hour window in seconds
        self.ANOMALY_CONSECUTIVE_FBR_FAILURES: int = 3  # Consecutive FBR API failures
        self.ANOMALY_BACKLOG_THRESHOLD: int = 500  # Invoice backlog threshold
        self.ANOMALY_DATABASE_LATENCY_THRESHOLD: int = 5000  # Database latency in milliseconds

        # Database Connection Pool Configuration
        self.DB_POOL_SIZE: int = 5
        self.DB_MAX_OVERFLOW: int = 10
        self.DB_POOL_RECYCLE: int = 300  # Recycle connections after 5 minutes
        self.DB_POOL_PRE_PING: bool = True  # Test connections before using

        # Claude API Configuration
        self.CLAUDE_MODEL: str = "claude-sonnet-4-6"
        self.CLAUDE_MAX_TOKENS: int = 1024
        self.CLAUDE_TEMPERATURE: float = 0.0  # Deterministic for business decisions
        self.CLAUDE_RATE_LIMIT_RPM: int = 50  # Requests per minute

        # Gemini API Configuration
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.GEMINI_MAX_TOKENS: int = 1024
        self.GEMINI_TEMPERATURE: float = 0.0  # Deterministic for business decisions
        self.GEMINI_RATE_LIMIT_RPM: int = 15  # Free tier: 15 RPM

        # Processing Configuration
        self.BATCH_SIZE: int = 50  # Maximum invoices to process per cycle
        self.BATCH_SIZE_PER_USER: int = 10  # Maximum invoices per user per cycle (prevents monopolization)
        self.PROCESSING_TIMEOUT: int = 120  # Timeout for processing single invoice in seconds


# Global configuration instance
config = Config()
