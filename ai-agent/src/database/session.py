"""Database session for automation database with optional main DB read-only access."""

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from contextlib import contextmanager
from typing import Generator
import logging

from src.config.settings import settings

# Pre-import all models so SQLAlchemy can resolve cross-model relationships
# before any query executes. The TYPE_CHECKING guards in the model files
# prevent circular import errors at Python level, but SQLAlchemy needs
# both classes visible at mapper configuration time.
import src.models.base  # noqa
import src.models.user  # noqa
import src.models.invoice  # noqa
import src.models.fbr_response  # noqa
import src.models.user_saved_product  # noqa
import src.models.fbr_master_data  # noqa
import src.models.automation_base  # noqa
import src.models.automation_invoice  # noqa
import src.models.automation_log  # noqa
import src.models.excel_upload_session  # noqa
import src.models.ai_agent_health_check  # noqa

logger = logging.getLogger(__name__)


def validate_database_url_security(url: str) -> None:
    url_lower = url.lower()
    if url_lower.startswith('postgresql://') or url_lower.startswith('postgres://'):
        if 'sslmode=' not in url_lower:
            raise ValueError(
                "SECURITY ERROR: Database connection must use SSL/TLS encryption. "
                "Add '?sslmode=require' to DATABASE_URL."
            )
        if 'sslmode=disable' in url_lower or 'sslmode=allow' in url_lower:
            raise ValueError(
                "SECURITY ERROR: Database SSL mode is insecure. "
                "Use 'sslmode=require' or 'sslmode=verify-full'."
            )


validate_database_url_security(settings.automation_database_url)

engine = create_engine(
    settings.automation_database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=30,
    connect_args={
        "connect_timeout": 60,
    }
)

# Optional read-only main DB engine for User/SavedProduct/FBR master data lookups
main_engine = None
if settings.main_database_url:
    validate_database_url_security(settings.main_database_url)
    main_engine = create_engine(
        settings.main_database_url,
        echo=settings.db_echo,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
        pool_recycle=300,
        pool_timeout=30,
        connect_args={
            "connect_timeout": 60,
        },
    )


def create_db_and_tables():
    """Create automation database tables."""
    from src.models.automation_base import automation_metadata
    automation_metadata.create_all(bind=engine)


@contextmanager
def get_automation_db_session() -> Generator:
    db = Session(engine)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_automation_db():
    with get_automation_db_session() as session:
        yield session


@contextmanager
def get_db_session() -> Generator:
    """Read-only session for main database (User, SavedProducts, FBR master data)."""
    if main_engine is None:
        raise RuntimeError("MAIN_DATABASE_URL not configured. Main DB access not available.")
    db = Session(main_engine)
    try:
        yield db
    finally:
        db.close()


def get_db():
    """Dependency for FastAPI to provide main database sessions (read-only)."""
    with get_db_session() as session:
        yield session
