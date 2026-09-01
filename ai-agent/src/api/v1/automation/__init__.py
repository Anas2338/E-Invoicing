"""
Automation API router initialization.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/automation", tags=["automation"])

# Import and include sub-routers
from . import excel, dashboard, retry, health, agent_status, file_management, pdf, invoice_numbers

router.include_router(excel.router)
router.include_router(dashboard.router)
router.include_router(retry.router)
router.include_router(health.router)
router.include_router(agent_status.router)
router.include_router(file_management.router)
router.include_router(pdf.router)
router.include_router(invoice_numbers.router)
