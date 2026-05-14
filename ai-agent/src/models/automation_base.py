"""
Separate metadata for automation database models.
Ensures automation tables are only created in the automation database,
NOT in the main database.

Usage in automation models:
    from .automation_base import automation_metadata
    class AutomationInvoice(SQLModel, table=True):
        metadata = automation_metadata
        ...
"""

from sqlalchemy import MetaData

automation_metadata = MetaData()
