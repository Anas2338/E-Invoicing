"""
Automation API router initialization.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/automation", tags=["automation"])

# Import and include sub-routers
from . import excel, dashboard, retry, health

router.include_router(excel.router)
router.include_router(dashboard.router)
router.include_router(retry.router)
router.include_router(health.router)
