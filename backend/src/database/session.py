from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from contextlib import contextmanager
from typing import Generator
import logging

from src.config.settings import settings

# Import all models to register them with SQLModel before creating the engine
from src.models.user import User
from src.models.invoice import Invoice
from src.models.fbr_response import FBRResponse
from src.models.idempotency import IdempotencyCache
from src.models.user_saved_product import UserSavedProduct

# Import FBR models (these use a separate declarative base)
from src.models.fbr_master_data import (
    FBRProvince, FBRUOM, FBRHSCode, FBRTransactionType,
    FBRInvoiceType, FBRSROItem, FBRSyncLog, FBRBase
)
from src.models.fbr_notifications import FBRChangeNotification, FBRDataSnapshot

logger = logging.getLogger(__name__)


def validate_database_url_security(url: str) -> None:
    """
    Validate database URL has SSL/TLS encryption enabled.

    SECURITY: Ensures all database connections are encrypted to prevent
    data interception and man-in-the-middle attacks.

    Args:
        url: Database connection URL

    Raises:
        ValueError: If SSL/TLS is not enabled
    """
    url_lower = url.lower()

    # Check for PostgreSQL SSL mode
    if url_lower.startswith('postgresql://') or url_lower.startswith('postgres://'):
        if 'sslmode=' not in url_lower:
            raise ValueError(
                "SECURITY ERROR: Database connection must use SSL/TLS encryption. "
                "Add '?sslmode=require' to DATABASE_URL. "
                "Example format: postgresql://USER@HOST/DATABASE?sslmode=require"
            )

        # Warn about insecure SSL modes
        if 'sslmode=disable' in url_lower or 'sslmode=allow' in url_lower:
            raise ValueError(
                "SECURITY ERROR: Database SSL mode is insecure. "
                "Use 'sslmode=require' or 'sslmode=verify-full' for production. "
                "Current mode allows unencrypted connections."
            )

        logger.info("Database connection encryption validated: SSL/TLS enabled")

    # Check for MySQL SSL
    elif url_lower.startswith('mysql://'):
        if 'ssl=' not in url_lower and 'ssl_ca=' not in url_lower:
            logger.warning(
                "Database connection may not be encrypted. "
                "Add SSL parameters to DATABASE_URL for MySQL."
            )


# Validate database URL security before creating engine
validate_database_url_security(settings.database_url)

# Create the main database engine
# PERFORMANCE: Optimized for cloud databases (Neon) with high latency
# NEON FREE TIER: Increased timeout to handle auto-suspend wake-up (3-5 seconds)
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,  # Only log SQL queries when explicitly enabled
    pool_pre_ping=True,  # Verify connections before use
    pool_size=5,  # Keep 5 connections ready
    max_overflow=10,  # Allow 10 extra connections under load
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_timeout=30,  # Wait up to 30s for a connection from pool
    # Additional configuration for Neon cloud database
    connect_args={
        "connect_timeout": 60,  # 60 second connection timeout for cold start
    }
)


def create_db_and_tables():
    """
    Create database tables based on SQLModel models and FBR models.
    Use Alembic migrations for production.
    """
    # Create SQLModel tables
    SQLModel.metadata.create_all(bind=engine)

    # Create FBR model tables (using separate declarative base)
    FBRBase.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator:
    """
    Context manager for database sessions.
    Ensures session is properly closed after use.
    """
    db = Session(engine)
    try:
        yield db
        db.commit()  # Commit the transaction if no exception occurred
    except Exception:
        db.rollback()  # Rollback on exception
        raise
    finally:
        db.close()


def get_db():
    """
    Dependency for FastAPI to provide main database sessions.
    """
    with get_db_session() as session:
        yield session
