"""FastAPI dependencies for AI-agent."""

from typing import Optional

from src.database.session import get_automation_db


def get_database_session():
    """Dependency for automation database sessions."""
    yield from get_automation_db()


def get_pagination_params(skip: int = 0, limit: int = 100):
    """Pagination dependency."""
    return {"skip": skip, "limit": limit}


def get_current_user():
    """Placeholder - actual user extraction happens in auth middleware via request.state."""
    pass
