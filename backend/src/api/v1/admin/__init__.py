"""
Admin API module.

Contains admin-only endpoints for system management.
"""
from fastapi import APIRouter

# Create main admin router
router = APIRouter()

__all__ = ["router"]
