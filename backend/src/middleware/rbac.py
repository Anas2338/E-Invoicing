"""
Role-Based Access Control (RBAC) middleware and dependencies.

Provides role-based authorization for API endpoints.
"""

from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session
from typing import List

from src.database.session import get_db
from src.models.user import User, UserRole
from src.api.middleware.auth_middleware import require_authentication


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory that creates a role-checking dependency.

    Usage:
        @router.get("/admin/users")
        def list_users(user_id: str = Depends(require_role(UserRole.ADMIN))):
            ...

    Args:
        *allowed_roles: One or more UserRole values that are allowed to access the endpoint

    Returns:
        Dependency function that checks user role
    """
    def role_checker(
        current_user_id: str = Depends(require_authentication),
        db: Session = Depends(get_db)
    ) -> str:
        """
        Check if the current user has one of the required roles.

        Args:
            current_user_id: ID of the authenticated user
            db: Database session

        Returns:
            User ID if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        user = db.get(User, current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Admin role has access to everything
        if user.role == UserRole.ADMIN.value:
            return current_user_id

        # Check if user has one of the allowed roles
        if user.role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join([r.value for r in allowed_roles])}"
            )

        return current_user_id

    return role_checker


def require_admin(
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
) -> str:
    """
    Dependency that requires admin role.
    Convenience function for require_role(UserRole.ADMIN).

    Args:
        current_user_id: ID of the authenticated user
        db: Database session

    Returns:
        User ID if user is admin

    Raises:
        HTTPException: If user is not admin
    """
    user = db.get(User, current_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user_id


def get_current_user_with_role(
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user with their role information.

    Args:
        current_user_id: ID of the authenticated user
        db: Database session

    Returns:
        User object with role information

    Raises:
        HTTPException: If user not found
    """
    user = db.get(User, current_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


def check_resource_ownership(user: User, resource_user_id: str) -> bool:
    """
    Check if a user owns a resource or is an admin.

    Args:
        user: The current user
        resource_user_id: The user ID that owns the resource

    Returns:
        True if user owns the resource or is admin
    """
    # Admins can access any resource
    if user.role == UserRole.ADMIN.value:
        return True

    # Users can only access their own resources
    return str(user.id) == resource_user_id


def require_resource_ownership(
    resource_user_id: str,
    current_user: User = Depends(get_current_user_with_role)
) -> User:
    """
    Dependency that checks if user owns a resource or is admin.

    Args:
        resource_user_id: The user ID that owns the resource
        current_user: The current authenticated user

    Returns:
        User object if authorized

    Raises:
        HTTPException: If user doesn't own the resource and is not admin
    """
    if not check_resource_ownership(current_user, resource_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own resources"
        )

    return current_user
