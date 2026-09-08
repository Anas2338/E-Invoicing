"""RBAC for AI-agent: automation access gate backed by the main users table.

A valid JWT alone is not enough for automation endpoints. The gate loads the
user row from the main database (read-only session, same pattern as
excel.py/retry.py) and only admits portal admins or users whose own row has
``automation_enabled`` set. Company linking never grants access: an employee
whose owner has automation enabled is still denied, because their own row
carries ``automation_enabled=false`` (company_id is deliberately ignored).
"""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from src.api.middleware.auth_middleware import require_authentication
from src.database.session import get_db
from src.models.user import User, UserRole

logger = logging.getLogger(__name__)


def require_automation_access(
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
) -> str:
    """
    Dependency that requires automation access for the authenticated user.

    Loads the user row from the main database (read-only session) and allows
    the call only for portal admins or users with ``automation_enabled`` true
    on their own row. Denials are logged (FR-015) so portal operators can
    inspect them.

    Args:
        current_user_id: ID of the authenticated user
        db: Read-only session against the main database

    Returns:
        User ID (string) when automation access is granted

    Raises:
        HTTPException: 404 when the main-DB user row is missing;
            403 when the user has no automation access
    """
    try:
        user = db.get(User, UUID(current_user_id))
    except (ValueError, TypeError):
        # Unparseable JWT subject — cannot resolve a user, so no access
        user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Admins always have automation access
    if user.role == UserRole.ADMIN.value:
        return current_user_id

    # Non-admins need automation_enabled on THEIR OWN row. Company-linked
    # employees (company_id -> owner) are not granted anything through the
    # link — employees are created with automation_enabled=false.
    if not user.automation_enabled:
        logger.warning(
            "FR-015 Automation access denied for user %s "
            "(automation_enabled=false, role=%s)",
            current_user_id, user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Automation access not enabled. Please contact your administrator."
        )

    return current_user_id
