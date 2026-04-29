"""
Admin API module.

Contains admin-only endpoints for system management.
"""
from fastapi import APIRouter

# Create main admin router
router = APIRouter()

# Import and include sub-routers
from src.api.v1.admin.transfer import router as transfer_router

router.include_router(transfer_router, prefix="/transfer", tags=["admin-transfer"])

__all__ = ["router"]
