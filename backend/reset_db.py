"""
Reset database schema - drops and recreates all tables.
WARNING: This will delete all data!
"""

from src.database.session import engine
from sqlmodel import SQLModel
from src.models.fbr_master_data import FBRBase

# Import all models
from src.models.user import User
from src.models.invoice import Invoice
from src.models.fbr_response import FBRResponse
from src.models.audit_log import AuditLog
from src.models.idempotency import IdempotencyCache
from src.models.automation_invoice import AutomationInvoice
from src.models.automation_log import AutomationLog
from src.models.excel_upload_session import ExcelUploadSession
from src.models.ai_agent_health_check import AIAgentHealthCheck
from src.models.user_saved_product import UserSavedProduct
from src.models.fbr_master_data import (
    FBRProvince, FBRUOM, FBRHSCode, FBRTransactionType,
    FBRInvoiceType, FBRSROItem, FBRSyncLog
)
from src.models.fbr_notifications import FBRChangeNotification, FBRDataSnapshot

print('Dropping all tables...')
SQLModel.metadata.drop_all(engine)
FBRBase.metadata.drop_all(engine)

print('Creating all tables...')
SQLModel.metadata.create_all(engine)
FBRBase.metadata.create_all(engine)

print('✓ Database schema updated!')
print('You can now register a new account.')
