from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from contextlib import contextmanager
from typing import Generator

from src.config.settings import settings

# Import all models to register them with SQLModel before creating the engine
from src.models.user import User
from src.models.invoice import Invoice
from src.models.fbr_response import FBRResponse
from src.models.audit_log import AuditLog
from src.models.idempotency import IdempotencyCache
from src.models.automation_invoice import AutomationInvoice
from src.models.automation_log import AutomationLog
from src.models.excel_upload_session import ExcelUploadSession


# Create the database engine
engine = create_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_pre_ping=True,
    pool_recycle=300,
)


def create_db_and_tables():
    """
    Create database tables based on SQLModel models.
    Use Alembic migrations for production.
    """
    SQLModel.metadata.create_all(bind=engine)


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
    Dependency for FastAPI to provide database sessions.
    """
    with get_db_session() as session:
        yield session
