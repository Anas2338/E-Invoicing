"""RBAC middleware for AI-agent. Simplified — no User table, just authentication."""

from fastapi import Depends, HTTPException, status, Request

from src.api.middleware.auth_middleware import require_authentication


def require_automation_access(
    current_user_id: str = Depends(require_authentication),
) -> str:
    """
    Dependency that requires authentication for automation endpoints.
    The main backend controls automation_enabled at the UI level.
    AI-agent trusts the JWT token validity for access control.
    """
    return current_user_id
