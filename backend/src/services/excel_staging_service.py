"""
Service for managing Excel staging sessions and rows.

Handles session lifecycle: create (parse) → review → recheck → commit/delete.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from io import BytesIO
from uuid import UUID

from sqlmodel import Session, select, delete

from src.models.excel_staging import (
    ExcelStagingSession,
    ExcelStagingRow,
)
from src.utils.manual_excel_helper import (
    parse_excel_for_staging,
    _validate_staging_row,
    _compute_staging_fields,
    build_invoices_from_rows,
    _clean_ntn_cnic,
)
from src.services.invoice_service import InvoiceService
from src.models.invoice import Invoice as InvoiceModel
from src.models.user_saved_product import UserSavedProduct

logger = logging.getLogger(__name__)


class ExcelStagingService:
    """Business logic for Excel staging operations."""

    def __init__(self) -> None:
        self.invoice_service = InvoiceService()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_session_from_upload(
        self,
        db: Session,
        user_id: UUID,
        filename: str,
        file_bytes: BytesIO,
    ) -> ExcelStagingSession:
        """Parse an Excel file and create a staging session with rows.

        Replaces any existing active session for the same user.
        """
        # Cancel any existing active session
        existing = self.get_active_session(db, user_id)
        if existing:
            self._delete_session(db, existing.id, user_id)

        # Parse the file
        rows_data = parse_excel_for_staging(file_bytes, user_id, db)

        if not rows_data:
            raise ValueError(
                "No invoice data found in file. "
                "The template sample row (INV-001) is skipped. "
                "Please fill the template with your invoice data and try again."
            )

        # Debug: log first row keys to verify column normalization
        if rows_data:
            logger.info(
                "Parsed %d rows. First row keys: %s",
                len(rows_data),
                list(rows_data[0].keys())[:20],
            )

        # Count valid/errored
        valid_count = sum(1 for r in rows_data if r.get("is_valid", False))
        errored_count = sum(1 for r in rows_data if not r.get("is_valid", True))

        # Create session
        session = ExcelStagingSession(
            user_id=user_id,
            original_filename=filename,
            status="ready_for_review",
            total_rows=len(rows_data),
            valid_rows=valid_count,
            errored_rows=errored_count,
        )
        db.add(session)
        db.flush()  # Get session.id

        # Create rows
        for rd in rows_data:
            row = ExcelStagingRow(
                session_id=session.id,
                user_id=user_id,
                excel_row_number=rd.get("excel_row_number", 0),
                group_key=rd.get("group_key", rd.get("invoice_number", "")),
                is_valid=rd.get("is_valid", True),
                is_dirty=rd.get("is_dirty", False),
                field_errors=rd.get("field_errors", {}),
                # Template fields
                invoice_number=rd.get("invoice_number", ""),
                invoice_type=rd.get("invoice_type", "Sale Invoice"),
                invoice_date=rd.get("invoice_date", ""),
                buyer_ntn_cnic=rd.get("buyer_ntn_cnic", ""),
                buyer_business_name=rd.get("buyer_business_name", ""),
                buyer_province=rd.get("buyer_province", ""),
                buyer_address=rd.get("buyer_address", ""),
                buyer_registration_type=rd.get("buyer_registration_type", "Registered"),
                saved_item_code=rd.get("saved_item_code", ""),
                quantity=float(rd.get("quantity", 0)),
                value_sales_excluding_st=float(rd.get("value_sales_excluding_st", 0)),
                fixed_notified_value_or_retail_price=float(
                    rd.get("fixed_notified_value_or_retail_price", 0)
                ),
                further_tax=float(rd.get("further_tax", 0)),
                discount=float(rd.get("discount", 0)),
                income_tax=rd.get("income_tax", "236G"),
                withholding_tax_amount=rd.get("withholding_tax_amount"),
                # Computed fields
                product_description=rd.get("product_description"),
                hs_code=rd.get("hs_code"),
                rate=rd.get("rate"),
                uom=rd.get("uom"),
                sale_type=rd.get("sale_type"),
                transaction_type_id=rd.get("transaction_type_id"),
                total_values=rd.get("total_values"),
                sales_tax_applicable=rd.get("sales_tax_applicable"),
                sales_tax_withheld_at_source=float(rd.get("sales_tax_withheld_at_source", 0)),
                extra_tax=float(rd.get("extra_tax", 0)),
                fed_payable=float(rd.get("fed_payable", 0)),
                sro_schedule_no=rd.get("sro_schedule_no"),
                sro_item_serial_no=rd.get("sro_item_serial_no"),
                item_rate=rd.get("item_rate"),
                # Seller fields
                seller_ntn_cnic=rd.get("seller_ntn_cnic", ""),
                seller_business_name=rd.get("seller_business_name", ""),
                seller_province=rd.get("seller_province", ""),
                seller_address=rd.get("seller_address", ""),
            )
            db.add(row)

        db.commit()
        db.refresh(session)
        logger.info(
            "Created staging session %s: %d rows (%d valid, %d errored)",
            session.id, session.total_rows, valid_count, errored_count,
        )
        return session

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_active_session(
        self,
        db: Session,
        user_id: UUID,
    ) -> ExcelStagingSession | None:
        """Get the user's most recent active (non-terminal) session."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        statement = (
            select(ExcelStagingSession)
            .where(
                ExcelStagingSession.user_id == user_id,
                ExcelStagingSession.created_at >= cutoff,
                ExcelStagingSession.status.not_in([
                    "cancelled",
                ]),
            )
            .order_by(ExcelStagingSession.created_at.desc())
            .limit(1)
        )
        return db.exec(statement).first()

    def get_session(
        self,
        db: Session,
        session_id: UUID,
        user_id: UUID,
    ) -> ExcelStagingSession | None:
        """Get a session by ID, verifying ownership."""
        session = db.get(ExcelStagingSession, session_id)
        if session is None or session.user_id != user_id:
            return None
        return session

    def get_session_with_rows(
        self,
        db: Session,
        session_id: UUID,
        user_id: UUID,
    ) -> tuple[ExcelStagingSession | None, list[ExcelStagingRow]]:
        """Get a session with all its rows, verifying ownership."""
        session = self.get_session(db, session_id, user_id)
        if session is None:
            return None, []

        statement = (
            select(ExcelStagingRow)
            .where(
                ExcelStagingRow.session_id == session_id,
                ExcelStagingRow.user_id == user_id,
            )
            .order_by(ExcelStagingRow.excel_row_number)
        )
        rows = list(db.exec(statement).all())
        return session, rows

    # ------------------------------------------------------------------
    # Update row
    # ------------------------------------------------------------------

    def update_row(
        self,
        db: Session,
        session_id: UUID,
        row_id: UUID,
        user_id: UUID,
        updates: dict,
    ) -> ExcelStagingRow | None:
        """Update a single row's fields.

        Clears field_errors for updated fields and marks row as dirty.
        Rejects if session is not in editable state.
        """
        session = self.get_session(db, session_id, user_id)
        if session is None:
            return None

        if session.status not in ("ready_for_review",):
            return None

        row = db.get(ExcelStagingRow, row_id)
        if row is None or row.session_id != session_id or row.user_id != user_id:
            return None

        # Apply updates
        editable_fields = {
            "invoice_number", "invoice_type", "invoice_date",
            "buyer_ntn_cnic", "buyer_business_name", "buyer_province",
            "buyer_address", "buyer_registration_type", "saved_item_code",
            "quantity", "value_sales_excluding_st",
            "fixed_notified_value_or_retail_price", "further_tax", "discount",
            "income_tax", "withholding_tax_amount",
        }

        for field, value in updates.items():
            if field in editable_fields:
                setattr(row, field, value)
                # Clear field_errors for this field — MUST reassign to create
                # a new dict so SQLAlchemy tracks the change (in-place mutation
                # on JSON columns is not detected by SQLAlchemy's change tracking).
                if row.field_errors and field in row.field_errors:
                    row.field_errors = {
                        k: v
                        for k, v in row.field_errors.items()
                        if k != field
                    }

        # Recalculate is_valid immediately (not just on recheck)
        # so the user sees green/red feedback right after editing
        old_valid = row.is_valid
        row.is_valid = len(row.field_errors) == 0 if row.field_errors else True

        # Keep session valid/errored counts in sync with the row change
        if old_valid != row.is_valid:
            if row.is_valid:
                session.valid_rows = max(0, session.valid_rows + 1)
                session.errored_rows = max(0, session.errored_rows - 1)
            else:
                session.valid_rows = max(0, session.valid_rows - 1)
                session.errored_rows = max(0, session.errored_rows + 1)
            db.add(session)

        row.is_dirty = True
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    # ------------------------------------------------------------------
    # Recheck
    # ------------------------------------------------------------------

    def recheck_session(
        self,
        db: Session,
        session_id: UUID,
        user_id: UUID,
    ) -> tuple[list[ExcelStagingRow], int, int, bool] | None:
        """Re-validate all dirty rows.

        Returns (rows, errored_before, errored_after, all_clear) or None.
        """
        session = self.get_session(db, session_id, user_id)
        if session is None:
            return None

        if session.status not in ("ready_for_review",):
            return None

        # Set status to rechecking
        session.status = "rechecking"
        db.add(session)
        db.commit()

        # Get all rows
        statement = select(ExcelStagingRow).where(
            ExcelStagingRow.session_id == session_id,
            ExcelStagingRow.user_id == user_id,
        )
        all_rows = list(db.exec(statement).all())

        errored_before = sum(1 for r in all_rows if not r.is_valid)

        # Fetch saved items for validation
        saved_items_stmt = select(UserSavedProduct).where(
            UserSavedProduct.user_id == user_id,
            UserSavedProduct.is_active == 1,
        )
        saved_items = db.exec(saved_items_stmt).all()
        saved_items_dict = {item.item_code: item for item in saved_items}

        today = datetime.utcnow().date()

        # Re-validate dirty rows
        for row in all_rows:
            if not row.is_dirty:
                continue

            row_data = {
                "invoice_number": row.invoice_number,
                "invoice_type": row.invoice_type,
                "invoice_date": row.invoice_date,
                "buyer_ntn_cnic": row.buyer_ntn_cnic,
                "buyer_business_name": row.buyer_business_name,
                "buyer_province": row.buyer_province,
                "buyer_address": row.buyer_address,
                "buyer_registration_type": row.buyer_registration_type,
                "saved_item_code": row.saved_item_code,
                "quantity": row.quantity,
                "value_sales_excluding_st": row.value_sales_excluding_st,
                "fixed_notified_value_or_retail_price": row.fixed_notified_value_or_retail_price,
                "further_tax": row.further_tax,
                "discount": row.discount,
                "income_tax": row.income_tax,
                "withholding_tax_amount": row.withholding_tax_amount,
            }

            field_errors = _validate_staging_row(row_data, saved_items_dict, today)
            row.field_errors = field_errors
            row.is_valid = len(field_errors) == 0
            row.is_dirty = False
            db.add(row)

        db.flush()

        # Recount
        errored_after = sum(1 for r in all_rows if not r.is_valid)
        valid_count = sum(1 for r in all_rows if r.is_valid)

        session.status = "ready_for_review"
        session.valid_rows = valid_count
        session.errored_rows = errored_after
        db.add(session)
        db.commit()

        all_clear = errored_after == 0

        # Re-fetch rows to return fresh data
        final_rows = list(db.exec(
            select(ExcelStagingRow).where(
                ExcelStagingRow.session_id == session_id,
                ExcelStagingRow.user_id == user_id,
            ).order_by(ExcelStagingRow.excel_row_number)
        ).all())

        return final_rows, errored_before, errored_after, all_clear

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    def commit_session(
        self,
        db: Session,
        session_id: UUID,
        user_id: UUID,
    ) -> dict | None:
        """Create DRAFT invoices from all valid rows, then delete session.

        Returns None if session not found/not committable.
        Returns dict with commit result on success.
        """
        session = self.get_session(db, session_id, user_id)
        if session is None:
            return None

        if session.status != "ready_for_review":
            return None

        if session.errored_rows > 0:
            return {"error": "Session has errored rows. Recheck first."}

        # Set status to committing
        session.status = "committing"
        db.add(session)
        db.commit()

        # Fetch rows
        statement = select(ExcelStagingRow).where(
            ExcelStagingRow.session_id == session_id,
            ExcelStagingRow.user_id == user_id,
            ExcelStagingRow.is_valid == True,
        )
        valid_rows = list(db.exec(statement).all())

        # Convert to row dicts for build_invoices_from_rows
        row_dicts = []
        for r in valid_rows:
            row_dicts.append({
                "invoice_number": r.invoice_number,
                "invoice_type": r.invoice_type,
                "invoice_date": r.invoice_date,
                "buyer_ntn_cnic": r.buyer_ntn_cnic,
                "buyer_business_name": r.buyer_business_name,
                "buyer_province": r.buyer_province,
                "buyer_address": r.buyer_address,
                "buyer_registration_type": r.buyer_registration_type,
                "quantity": r.quantity,
                "value_sales_excluding_st": r.value_sales_excluding_st,
                "fixed_notified_value_or_retail_price": r.fixed_notified_value_or_retail_price,
                "further_tax": r.further_tax,
                "discount": r.discount,
                "income_tax": r.income_tax,
                "withholding_tax_amount": r.withholding_tax_amount,
                # Computed fields
                "hs_code": r.hs_code or "",
                "product_description": r.product_description or "",
                "rate": r.rate or "18",
                "uom": r.uom or "NOS",
                "total_values": r.total_values or 0,
                "sales_tax_applicable": r.sales_tax_applicable or 0,
                "sales_tax_withheld_at_source": r.sales_tax_withheld_at_source or 0,
                "extra_tax": r.extra_tax or 0,
                "fed_payable": r.fed_payable or 0,
                "sro_schedule_no": r.sro_schedule_no or "",
                "sro_item_serial_no": r.sro_item_serial_no or "",
                "sale_type": r.sale_type or "01",
                "income_tax_type": r.income_tax or "236G",
                "item_rate": r.item_rate,
                # Seller
                "seller_ntn_cnic": r.seller_ntn_cnic,
                "seller_business_name": r.seller_business_name,
                "seller_province": r.seller_province,
                "seller_address": r.seller_address,
            })

        seller_info = {
            "seller_ntn_cnic": valid_rows[0].seller_ntn_cnic if valid_rows else "",
            "seller_business_name": valid_rows[0].seller_business_name if valid_rows else "",
            "seller_province": valid_rows[0].seller_province if valid_rows else "",
            "seller_address": valid_rows[0].seller_address if valid_rows else "",
        } if valid_rows else {}

        # Build invoice dicts
        invoice_dicts = build_invoices_from_rows(row_dicts, seller_info)

        # Create invoices via InvoiceService
        committed: list[dict] = []
        errors: list[dict] = []
        from src.schemas.invoice import InvoiceCreate

        for inv_dict in invoice_dicts:
            try:
                # Create invoice as DRAFT
                inv = self.invoice_service.create_invoice(
                    db=db,
                    invoice_create=InvoiceCreate(**inv_dict),
                    user_id=user_id,
                )
                committed.append({
                    "id": str(inv.id),
                    "external_id": inv.external_id,
                    "invoice_type": inv.invoice_type,
                    "status": inv.status.value if hasattr(inv.status, 'value') else inv.status,
                })
            except Exception as e:
                logger.warning(
                    "Failed to create invoice %s: %s",
                    inv_dict.get("external_id", "unknown"), e,
                )
                errors.append({
                    "invoice_number": inv_dict.get("external_id", "unknown"),
                    "error": str(e).split("\n")[0] if str(e) else str(e),
                })

        # Delete session and all rows
        session_id_str = str(session.id)
        total_committed = len(committed)
        total_failed = len(errors)
        self._delete_session(db, session_id, user_id)

        return {
            "session_id": session_id_str,
            "total_committed": total_committed,
            "total_failed": total_failed,
            "invoices": committed,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def cancel_session(
        self,
        db: Session,
        session_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Cancel and delete a staging session.

        Returns True if deleted, False if not found.
        """
        session = self.get_session(db, session_id, user_id)
        if session is None:
            return False

        self._delete_session(db, session_id, user_id)
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _delete_session(
        self,
        db: Session,
        session_id: UUID,
        user_id: UUID,
    ) -> None:
        """Delete a session and all its rows."""
        # Delete rows first
        db.exec(
            delete(ExcelStagingRow).where(
                ExcelStagingRow.session_id == session_id,
                ExcelStagingRow.user_id == user_id,
            )
        )
        # Delete session
        db.exec(
            delete(ExcelStagingSession).where(
                ExcelStagingSession.id == session_id,
                ExcelStagingSession.user_id == user_id,
            )
        )
        db.commit()
        logger.info("Deleted staging session %s", session_id)
