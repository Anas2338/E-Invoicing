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
    _validate_staging_row_full,
    _compute_staging_fields,
    build_invoices_from_rows,
    _clean_ntn_cnic,
)
from src.services.invoice_service import InvoiceService
from src.models.invoice import Invoice as InvoiceModel
from src.models.user_saved_product import UserSavedProduct

logger = logging.getLogger(__name__)


def _staging_row_to_data(row: ExcelStagingRow) -> dict:
    """Convert a staging row model to the plain dict the validators expect."""
    return {
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

        Re-validates the whole row against all rules (including duplicate
        invoice number checks) and updates field_errors / is_valid
        immediately. Marks row as dirty. Rejects if session is not in
        editable state.
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
            "product_description",
            "quantity", "value_sales_excluding_st",
            "fixed_notified_value_or_retail_price", "further_tax", "discount",
            "income_tax", "withholding_tax_amount",
        }

        for field, value in updates.items():
            if field in editable_fields:
                setattr(row, field, value)

        # Keep the UI grouping separators in sync when the invoice number
        # changes (rows are grouped by group_key == invoice_number)
        if "invoice_number" in updates:
            row.group_key = row.invoice_number or ""

        # income_tax "None" means no withholding tax is applicable
        if "income_tax" in updates and row.income_tax == "None":
            row.withholding_tax_amount = 0

        # Re-validate the WHOLE row against all rules (not just the edited
        # field) so invalid edits — e.g. an invoice number that already
        # exists in the user's history or elsewhere in this file — are
        # flagged immediately instead of silently accepted.
        saved_items_stmt = select(UserSavedProduct).where(
            UserSavedProduct.user_id == user_id,
            UserSavedProduct.is_active == 1,
        )
        saved_items = db.exec(saved_items_stmt).all()
        saved_items_dict = {item.item_code: item for item in saved_items}

        # Invoice numbers used by OTHER rows in this session (self excluded)
        other_numbers_stmt = select(ExcelStagingRow.invoice_number).where(
            ExcelStagingRow.session_id == session_id,
            ExcelStagingRow.user_id == user_id,
            ExcelStagingRow.id != row_id,
        )
        other_numbers = {n for n in db.exec(other_numbers_stmt).all() if n}

        # Invoice numbers already saved in the user's history
        existing_numbers: set[str] = set()
        invoice_number = str(row.invoice_number or "").strip()
        if invoice_number:
            existing_numbers = set(db.exec(
                select(InvoiceModel.external_id).where(
                    InvoiceModel.external_id == invoice_number,
                    InvoiceModel.user_id == user_id,
                    InvoiceModel.is_deleted == False,
                )
            ).all())

        row.field_errors = _validate_staging_row_full(
            _staging_row_to_data(row),
            saved_items_dict,
            datetime.utcnow().date(),
            other_numbers,
            existing_numbers,
        )

        # Recalculate is_valid immediately (not just on recheck)
        # so the user sees green/red feedback right after editing
        old_valid = row.is_valid
        row.is_valid = len(row.field_errors) == 0

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

        # Invoice numbers used by more than one row in this session
        number_counts: dict[str, int] = {}
        for r in all_rows:
            num = str(r.invoice_number or "").strip()
            if num:
                number_counts[num] = number_counts.get(num, 0) + 1
        other_numbers = {n for n, c in number_counts.items() if c > 1}

        # Invoice numbers already saved in the user's history (batch query)
        dirty_numbers = {
            str(r.invoice_number or "").strip()
            for r in all_rows if r.is_dirty
        }
        dirty_numbers.discard("")
        existing_numbers: set[str] = set()
        if dirty_numbers:
            existing_numbers = set(db.exec(
                select(InvoiceModel.external_id).where(
                    InvoiceModel.external_id.in_(dirty_numbers),
                    InvoiceModel.user_id == user_id,
                    InvoiceModel.is_deleted == False,
                )
            ).all())

        # Re-validate dirty rows against ALL rules (incl. duplicates)
        for row in all_rows:
            if not row.is_dirty:
                continue

            field_errors = _validate_staging_row_full(
                _staging_row_to_data(row),
                saved_items_dict,
                today,
                other_numbers,
                existing_numbers,
            )
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

        # Final duplicate guard: an invoice number may have been saved since
        # this session was reviewed (another upload, manual creation, etc.).
        # Without this, create_invoice silently UPDATES the existing DRAFT
        # invoice instead of creating a new one. Also guard against duplicate
        # numbers within the session itself.
        duplicate_numbers: set[str] = set()
        seen_numbers: set[str] = set()
        for r in valid_rows:
            num = str(r.invoice_number or "").strip()
            if not num:
                continue
            if num in seen_numbers:
                duplicate_numbers.add(num)
            seen_numbers.add(num)

        numbers_to_check = seen_numbers - duplicate_numbers
        if numbers_to_check:
            existing = db.exec(
                select(InvoiceModel.external_id).where(
                    InvoiceModel.external_id.in_(numbers_to_check),
                    InvoiceModel.user_id == user_id,
                    InvoiceModel.is_deleted == False,
                )
            ).all()
            duplicate_numbers.update(existing)

        if duplicate_numbers:
            # Revert to review state so the user can fix the rows and retry
            session.status = "ready_for_review"
            db.add(session)
            db.commit()
            logger.warning(
                "Commit rejected for session %s: duplicate invoice numbers %s",
                session_id, sorted(duplicate_numbers),
            )
            return {
                "error": (
                    "Cannot upload: the following invoice number(s) already "
                    "exist and must be changed: "
                    + ", ".join(sorted(duplicate_numbers))
                )
            }

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
