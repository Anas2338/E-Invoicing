"""Sync Python enum values with PostgreSQL enum types on startup.

The DB was created with name-based enums (uppercase: PENDING, PAUSED, etc.).
Later code uses value-based enums (lowercase: pending, paused).
Sync both to ensure compatibility.
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Both cases are needed because DB was created with uppercase, code uses lowercase
ENUM_SYNC = {
    "automationinvoicestatus": [
        "PENDING", "EXPIRED", "VALIDATED", "SUBMITTED", "FAILED",
        "BLOCKED", "PAUSED", "TRANSFERRED", "TRANSFER_FAILED",
        "pending", "expired", "validated", "submitted", "failed",
        "blocked", "paused", "transferred", "transfer_failed",
    ],
}


def sync_enum_values():
    """Add missing enum values to PostgreSQL enum types on startup."""
    from src.database.session import engine

    try:
        raw_conn = engine.raw_connection()
        try:
            raw_conn.set_isolation_level(0)
            cursor = raw_conn.cursor()
            for enum_name, values in ENUM_SYNC.items():
                # First check what exists
                cursor.execute(
                    f"SELECT unnest(enum_range(NULL::{enum_name}))::text"
                )
                existing = {r[0] for r in cursor.fetchall()}
                for val in values:
                    if val not in existing:
                        try:
                            cursor.execute(
                                f"ALTER TYPE {enum_name} ADD VALUE '{val}'"
                            )
                            logger.info(f"Added '{val}' to {enum_name}")
                        except Exception:
                            raw_conn.rollback()
            cursor.close()
            logger.info("Enum sync complete")
        finally:
            raw_conn.set_isolation_level(1)
            raw_conn.close()
    except Exception as e:
        logger.debug(f"Enum sync skipped: {e}")
