"""
Database connection pool management for AI Agent.

Provides connection pooling with pre-ping and connection recycling
to ensure reliable database access.
"""
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlmodel import Session

from config import config

logger = logging.getLogger(__name__)


# Create database engine with connection pooling
engine = create_engine(
    config.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_recycle=config.DB_POOL_RECYCLE,
    pool_pre_ping=config.DB_POOL_PRE_PING,
    echo=False  # Set to True for SQL query logging in development
)

logger.info("AI Agent: Database connection pool initialized")
logger.info(f"  Pool size: {config.DB_POOL_SIZE}")
logger.info(f"  Max overflow: {config.DB_MAX_OVERFLOW}")
logger.info(f"  Pool recycle: {config.DB_POOL_RECYCLE}s")
logger.info(f"  Pre-ping enabled: {config.DB_POOL_PRE_PING}")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions using SQLModel.

    Ensures session is properly closed after use and handles
    transaction management (commit on success, rollback on error).

    Yields:
        SQLModel Session with exec() method support

    Example:
        with get_db_session() as db:
            invoices = db.exec(select(AutomationInvoice)).all()
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_database_connection() -> tuple[bool, int]:
    """
    Test database connectivity and measure latency.

    Returns:
        Tuple of (is_connected, latency_ms)
    """
    import time

    try:
        start_time = time.time()

        with get_db_session() as db:
            # Simple query to test connection
            db.execute(text("SELECT 1"))

        latency_ms = int((time.time() - start_time) * 1000)
        return True, latency_ms

    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False, 0


def get_pool_status() -> dict:
    """
    Get current connection pool status.

    Returns:
        Dictionary with pool statistics
    """
    pool = engine.pool

    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow()
    }
