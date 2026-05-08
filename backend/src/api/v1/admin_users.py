"""
Admin endpoints for user management and approval.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
import uuid
import logging
from pydantic import BaseModel

from src.database.session import get_db
from src.models.user import User
from src.middleware.rbac import require_admin
from src.utils.email_utils import send_approval_email, send_rejection_email


logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas for FBR credentials management
class FBRCredentialsUpdate(BaseModel):
    fbr_sandbox_token: Optional[str] = None
    fbr_production_token: Optional[str] = None
    fbr_seller_ntn: Optional[str] = None
    fbr_business_name: Optional[str] = None
    fbr_seller_province: Optional[str] = None
    fbr_seller_address: Optional[str] = None


@router.get("/users/pending")
def get_pending_users(
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users with pending approval status.
    """
    try:
        statement = select(User).where(User.account_status == 'pending').order_by(User.created_at.desc())
        pending_users = db.exec(statement).all()

        return {
            "total": len(pending_users),
            "users": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat(),
                    "account_status": user.account_status,
                    "automation_enabled": user.automation_enabled
                }
                for user in pending_users
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending users: {str(e)}"
        )


@router.get("/users/all")
def get_all_users(
    status_filter: Optional[str] = None,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users with optional status filter.
    """
    try:
        statement = select(User)

        if status_filter:
            statement = statement.where(User.account_status == status_filter)

        statement = statement.order_by(User.created_at.desc())
        users = db.exec(statement).all()

        return {
            "total": len(users),
            "users": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat(),
                    "account_status": user.account_status,
                    "approved_at": user.approved_at.isoformat() if user.approved_at else None,
                    "rejection_reason": user.rejection_reason,
                    "is_active": user.is_active,
                    "automation_enabled": user.automation_enabled
                }
                for user in users
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: str,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve a pending user account.
    """
    try:
        # Get the admin user
        admin = db.get(User, uuid.UUID(admin_user_id))

        # Get the user to approve
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.account_status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User account is not pending (current status: {user.account_status})"
            )

        # Update user status
        user.account_status = 'approved'
        user.approved_by = admin.id
        user.approved_at = datetime.utcnow()
        user.rejection_reason = None

        db.add(user)
        db.commit()
        db.refresh(user)

        # Send approval email to user
        try:
            send_approval_email(user.email, user.name or "User")
        except Exception as e:
            print(f"Failed to send approval email: {str(e)}")

        return {
            "success": True,
            "message": f"User {user.email} has been approved",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "account_status": user.account_status,
                "approved_at": user.approved_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve user: {str(e)}"
        )


@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: str,
    rejection_data: dict,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reject a pending user account.
    """
    try:
        # Get the admin user
        admin = db.get(User, uuid.UUID(admin_user_id))

        # Get the user to reject
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.account_status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User account is not pending (current status: {user.account_status})"
            )

        # Get rejection reason
        reason = rejection_data.get('reason', 'No reason provided')

        # Update user status
        user.account_status = 'rejected'
        user.approved_by = admin.id
        user.approved_at = datetime.utcnow()
        user.rejection_reason = reason

        db.add(user)
        db.commit()
        db.refresh(user)

        # Send rejection email to user
        try:
            send_rejection_email(user.email, user.name or "User", reason)
        except Exception as e:
            print(f"Failed to send rejection email: {str(e)}")

        return {
            "success": True,
            "message": f"User {user.email} has been rejected",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "account_status": user.account_status,
                "rejection_reason": user.rejection_reason
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject user: {str(e)}"
        )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user account (admin only).
    """
    try:
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prevent admin from deleting themselves
        if str(user.id) == str(admin_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        db.delete(user)
        db.commit()

        return {
            "success": True,
            "message": f"User {user.email} has been deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.post("/users/{user_id}/toggle-automation")
def toggle_automation_access(
    user_id: str,
    automation_data: dict,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Enable or disable automation access for a user (admin only).
    """
    try:
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get the enabled status from request
        enabled = automation_data.get('enabled', False)

        # Update user automation access
        user.automation_enabled = enabled

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": f"Automation access {'enabled' if enabled else 'disabled'} for user {user.email}",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "automation_enabled": user.automation_enabled
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle automation access: {str(e)}"
        )


@router.get("/users/{user_id}/fbr-tokens")
def get_user_fbr_tokens(
    user_id: str,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get FBR tokens for a specific user (admin only).
    Returns full tokens for admin access.
    """
    try:
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "user_id": str(user.id),
            "email": user.email,
            "name": user.name,
            "has_sandbox_token": bool(user.fbr_sandbox_token),
            "has_production_token": bool(user.fbr_production_token),
            "fbr_sandbox_token": user.fbr_sandbox_token or "",
            "fbr_production_token": user.fbr_production_token or ""
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FBR tokens: {str(e)}"
        )


@router.put("/users/{user_id}/fbr-tokens")
def update_user_fbr_tokens(
    user_id: str,
    credentials: FBRCredentialsUpdate,
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update FBR tokens for a specific user (admin only).
    Can update sandbox token, production token, or both.
    """
    try:
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update tokens if provided - MUST encrypt before storing
        from src.utils.encryption import get_encryption_service
        encryption_service = get_encryption_service()

        if credentials.fbr_sandbox_token is not None:
            if credentials.fbr_sandbox_token and credentials.fbr_sandbox_token.strip():
                # Encrypt the token before storing
                user.fbr_sandbox_token = encryption_service.encrypt(credentials.fbr_sandbox_token.strip())
                logger.info(f"Admin updated encrypted sandbox token for user {user.email}")
            else:
                # Empty string means delete the token
                user.fbr_sandbox_token = None
                logger.info(f"Admin cleared sandbox token for user {user.email}")

        if credentials.fbr_production_token is not None:
            if credentials.fbr_production_token and credentials.fbr_production_token.strip():
                # Encrypt the token before storing
                user.fbr_production_token = encryption_service.encrypt(credentials.fbr_production_token.strip())
                logger.info(f"Admin updated encrypted production token for user {user.email}")
            else:
                # Empty string means delete the token
                user.fbr_production_token = None
                logger.info(f"Admin cleared production token for user {user.email}")

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": f"FBR tokens updated for user {user.email}",
            "has_sandbox_token": bool(user.fbr_sandbox_token),
            "has_production_token": bool(user.fbr_production_token)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update FBR tokens: {str(e)}"
        )


@router.delete("/users/{user_id}/fbr-tokens")
def delete_user_fbr_token(
    user_id: str,
    environment: str,  # "sandbox" or "production"
    admin_user_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a specific FBR token for a user (admin only).
    Environment parameter specifies which token to delete: "sandbox" or "production".
    """
    try:
        user = db.get(User, uuid.UUID(user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if environment.lower() == "sandbox":
            user.fbr_sandbox_token = None
            token_type = "Sandbox"
        elif environment.lower() == "production":
            user.fbr_production_token = None
            token_type = "Production"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid environment. Must be 'sandbox' or 'production'"
            )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": f"{token_type} FBR token deleted for user {user.email}",
            "has_sandbox_token": bool(user.fbr_sandbox_token),
            "has_production_token": bool(user.fbr_production_token)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete FBR token: {str(e)}"
        )
