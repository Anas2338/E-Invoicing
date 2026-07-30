from typing import Optional, List, Tuple, Dict
from datetime import datetime, date
from sqlmodel import Session, select, delete
from uuid import UUID
import logging
from fastapi import HTTPException, status

from src.models.invoice import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus
from src.models.user import User
from src.models.fbr_response import FBRResponse
from src.schemas.invoice import InvoiceFilter
from src.utils.helpers import calculate_hash


logger = logging.getLogger(__name__)

# Withholding tax rates per income tax type
WITHHOLDING_TAX_RATES = {
    "236G": 0.001,  # 0.1%
    "236H": 0.005,  # 0.5%
}


def _calculate_withholding_tax(value_sales_excluding_st: float, income_tax_type: str) -> float:
    """Calculate withholding tax amount for an item based on its income tax type."""
    rate = WITHHOLDING_TAX_RATES.get(income_tax_type, 0.001)
    return round(value_sales_excluding_st * rate, 2)


def _normalize_items_with_income_tax(items: list, fallback_income_tax: str = "236G") -> list:
    """
    Ensure every item has income_tax_type and withholding_tax_amount.
    Auto-defaults to "236G" and calculates WHT if missing.

    Args:
        items: List of item dicts
        fallback_income_tax: Fallback if item has no income_tax_type (for old invoices)

    Returns:
        Normalized list of item dicts
    """
    for item in items:
        # Default income_tax_type if missing or empty
        if not item.get("income_tax_type"):
            item["income_tax_type"] = fallback_income_tax

        # Calculate withholding_tax_amount if missing or zero and value exists
        if not item.get("withholding_tax_amount") and item.get("value_sales_excluding_st"):
            item["withholding_tax_amount"] = _calculate_withholding_tax(
                float(item["value_sales_excluding_st"]),
                item["income_tax_type"]
            )
    return items


def _clean_ntn_cnic(value: str) -> str:
    """Normalize NTN/CNIC value — strips .0 suffix from float string artifacts."""
    if not value:
        return value
    s = str(value).strip()
    if s.endswith(".0") and len(s) > 2 and s[:-2].isdigit():
        s = s[:-2]
    return s


def get_user_environment_filter(user: User) -> Optional[str]:
    """
    Determine the FBR environment(s) a user can access based on their tokens.
    Returns:
        None if user has both sandbox and production tokens (show all invoices)
        "SANDBOX" if user only has sandbox token
        "PRODUCTION" if user only has production token
        None if user has neither token (show all invoices — no token configured yet)
    """
    has_sandbox = bool(user.fbr_sandbox_token)
    has_production = bool(user.fbr_production_token)

    if has_sandbox and has_production:
        return None
    elif has_sandbox:
        return "SANDBOX"
    elif has_production:
        return "PRODUCTION"
    else:
        return None


class InvoiceService:
    """
    Service class for handling invoice-related business logic.
    """

    def create_invoice(self, db: Session, invoice_create: InvoiceCreate, user_id: UUID) -> Invoice:
        """
        Create a new invoice in draft status.

        Args:
            db: Database session
            invoice_create: Invoice creation data
            user_id: ID of the user creating the invoice

        Returns:
            Created Invoice object
        """
        # Note: Removed validation that required all items to be from saved products
        # Users can now create invoices with any valid data
        # Saved products are for convenience, not a requirement

        # Generate external ID if not provided
        external_id = invoice_create.external_id or f"INV-{int(datetime.utcnow().timestamp())}-{hash(str(invoice_create.invoice_type)) % 10000}"

        # Check for existing DRAFT invoice with same external_id for this user — update instead of duplicate
        existing = db.query(Invoice).filter(
            Invoice.external_id == external_id,
            Invoice.user_id == user_id,
            Invoice.status == InvoiceStatus.DRAFT
        ).first()
        if existing:
            logger.info(f"Updating existing DRAFT invoice {existing.id} (external_id={external_id}) instead of creating duplicate")
            return self.update_invoice_from_dict(db, existing.id, invoice_create.model_dump(), user_id)

        # Normalize items: auto-default income_tax_type and calculate withholding_tax_amount
        items_data = [item.model_dump() for item in invoice_create.items]
        fallback_income_tax = getattr(invoice_create, 'income_tax', None) or "236G"
        items_data = _normalize_items_with_income_tax(items_data, fallback_income_tax)

        # Derive invoice-level income_tax from first item (backward compat)
        invoice_income_tax = items_data[0].get("income_tax_type", "236G") if items_data else "236G"

        # Create invoice object with FBR-specific fields
        db_invoice = Invoice(
            external_id=external_id,
            user_id=user_id,
            invoice_type=invoice_create.invoice_type,
            invoice_date=invoice_create.invoice_date,
            transaction_type_id=invoice_create.transaction_type_id,
            seller_ntn_cnic=_clean_ntn_cnic(invoice_create.seller_ntn_cnic),
            seller_business_name=invoice_create.seller_business_name,
            seller_province=invoice_create.seller_province,
            seller_address=invoice_create.seller_address,
            buyer_ntn_cnic=_clean_ntn_cnic(invoice_create.buyer_ntn_cnic),
            buyer_business_name=invoice_create.buyer_business_name,
            buyer_province=invoice_create.buyer_province,
            buyer_address=invoice_create.buyer_address,
            buyer_registration_type=invoice_create.buyer_registration_type,
            invoice_ref_no=invoice_create.invoice_ref_no,
            scenario_id=invoice_create.scenario_id,
            income_tax=invoice_income_tax,
            items=items_data,
            environment=invoice_create.environment,
            status=InvoiceStatus.DRAFT
        )

        # Add to database
        db.add(db_invoice)
        db.commit()
        db.refresh(db_invoice)

        logger.info(f"Invoice {db_invoice.id} created for user {user_id}")

        return db_invoice

    def get_invoice_by_id(self, db: Session, invoice_id: UUID, user_id: UUID) -> Optional[Invoice]:
        """
        Get an invoice by its ID, ensuring the user has access.

        Args:
            db: Database session
            invoice_id: ID of the invoice to retrieve
            user_id: ID of the requesting user

        Returns:
            Invoice object if found and user has access, None otherwise
        """
        invoice = db.exec(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.user_id == user_id)
            .where(Invoice.is_deleted == False)
        ).first()

        if invoice:
            logger.debug(f"Invoice {invoice_id} retrieved for user {user_id}")
        else:
            logger.warning(f"Invoice {invoice_id} not found for user {user_id}")

        return invoice

    def get_invoice_with_history(self, db: Session, invoice_id: UUID, user_id: UUID) -> Optional[dict]:
        """
        Get an invoice with its complete history including FBR responses.

        Args:
            db: Database session
            invoice_id: ID of the invoice to retrieve
            user_id: ID of the requesting user

        Returns:
            Dictionary containing invoice and its history, None if not found
        """
        invoice = self.get_invoice_by_id(db, invoice_id, user_id)
        if not invoice:
            return None

        # Get related FBR responses
        fbr_responses = []
        if invoice.fbr_response_id:
            fbr_response = db.exec(
                select(FBRResponse).where(FBRResponse.id == invoice.fbr_response_id)
            ).first()
            if fbr_response:
                fbr_responses.append(fbr_response)

        return {
            "invoice": invoice,
            "fbr_responses": fbr_responses
        }

    def get_invoices_by_user(self, db: Session, user_id: UUID, filters: InvoiceFilter, environment_override: Optional[str] = None) -> List[Invoice]:
        """
        Get all invoices for a specific user with optional filtering.

        Args:
            db: Database session
            user_id: ID of the user whose invoices to retrieve
            filters: Filtering parameters
            environment_override: Hard environment filter based on user's accessible tokens.
                Overrides filters.environment. Used to restrict sandbox-only or production-only users.

        Returns:
            List of Invoice objects matching the criteria
        """
        query = select(Invoice).where(Invoice.user_id == user_id).where(Invoice.is_deleted == False)

        # Apply environment override first (hard limit based on user tokens)
        if environment_override:
            query = query.where(Invoice.environment == environment_override)
        elif filters.environment:
            query = query.where(Invoice.environment == filters.environment)

        # Apply other filters
        if filters.status:
            query = query.where(Invoice.status == filters.status)
        if filters.invoice_type:
            query = query.where(Invoice.invoice_type == filters.invoice_type)
        if filters.source:
            query = query.where(Invoice.source == filters.source)
        if filters.date_from:
            query = query.where(Invoice.created_at >= filters.date_from)
        if filters.date_to:
            query = query.where(Invoice.created_at <= filters.date_to)

        # Apply pagination
        offset = (filters.page - 1) * filters.size
        query = query.offset(offset).limit(filters.size)

        invoices = db.exec(query).all()

        logger.info(f"Retrieved {len(invoices)} invoices for user {user_id} with filters")

        return invoices

    def update_invoice(self, db: Session, invoice_id: UUID, invoice_update: InvoiceUpdate, user_id: UUID) -> Optional[Invoice]:
        """
        Update an existing invoice.

        Args:
            db: Database session
            invoice_id: ID of the invoice to update
            invoice_update: Update data
            user_id: ID of the user updating the invoice

        Returns:
            Updated Invoice object if successful, None otherwise
        """
        # Get the existing invoice
        invoice = self.get_invoice_by_id(db, invoice_id, user_id)
        if not invoice:
            return None

        # Update fields that are provided (exclude None values)
        update_data = invoice_update.dict(exclude_none=True)

        for field, value in update_data.items():
            setattr(invoice, field, value)

        # Update the updated_at timestamp
        invoice.updated_at = datetime.utcnow()

        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        logger.info(f"Invoice {invoice_id} updated for user {user_id}")

        return invoice

    def update_invoice_from_dict(self, db: Session, invoice_id: UUID, update_data: dict, user_id: UUID) -> Optional[Invoice]:
        """
        Update an invoice directly from a dictionary (bypasses Pydantic exclude_none issue).
        If a VALIDATED or FAILED invoice is edited, it will be moved back to DRAFT status.

        Args:
            db: Database session
            invoice_id: UUID of the invoice to update
            update_data: Dictionary containing the fields to update
            user_id: UUID of the user making the update

        Returns:
            Updated Invoice object if successful, None otherwise
        """
        # Get the existing invoice
        invoice = self.get_invoice_by_id(db, invoice_id, user_id)
        if not invoice:
            return None

        # Check if this is a VALIDATED or FAILED invoice being edited (not just status update)
        is_content_update = any(key not in ['status', 'validated_at', 'posted_at', 'fbr_reference_number', 'validation_errors']
                               for key in update_data.keys())

        if (invoice.status == InvoiceStatus.VALIDATED or invoice.status == InvoiceStatus.FAILED) and is_content_update:
            # Move back to DRAFT when validated or failed invoice is edited
            invoice.status = InvoiceStatus.DRAFT
            invoice.validated_at = None
            invoice.validation_errors = None
            logger.info(f"Invoice {invoice_id} moved from {invoice.status} to DRAFT due to content update")

        # Normalize items if they are being updated: auto-default income_tax_type and calculate withholding_tax_amount
        if "items" in update_data and update_data["items"]:
            fallback = update_data.get("income_tax") or invoice.income_tax or "236G"
            update_data["items"] = _normalize_items_with_income_tax(update_data["items"], fallback)
            # Derive invoice-level income_tax from first item if not explicitly provided
            if "income_tax" not in update_data:
                update_data["income_tax"] = update_data["items"][0].get("income_tax_type", "236G")

        # Update fields directly from the dict
        for field, value in update_data.items():
            if hasattr(invoice, field):
                # Clean NTN/CNIC values to strip .0 float artifacts
                if field in ('seller_ntn_cnic', 'buyer_ntn_cnic') and isinstance(value, str):
                    value = _clean_ntn_cnic(value)
                setattr(invoice, field, value)

        # Update the updated_at timestamp
        invoice.updated_at = datetime.utcnow()

        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        logger.info(f"Invoice {invoice_id} updated for user {user_id}")

        return invoice

    def update_invoice_status(self, db: Session, invoice_id: UUID, new_status: InvoiceStatus, user_id: UUID) -> Optional[Invoice]:
        """
        Update the status of an invoice.

        Args:
            db: Database session
            invoice_id: ID of the invoice to update
            new_status: New status to set
            user_id: ID of the user updating the invoice

        Returns:
            Updated Invoice object if successful, None otherwise
        """
        invoice = self.get_invoice_by_id(db, invoice_id, user_id)
        if not invoice:
            return None

        old_status = invoice.status
        invoice.status = new_status

        # Update timestamps based on status change
        if new_status == InvoiceStatus.VALIDATED and old_status != InvoiceStatus.VALIDATED:
            invoice.validated_at = datetime.utcnow()
        elif new_status == InvoiceStatus.POSTED and old_status != InvoiceStatus.POSTED:
            invoice.posted_at = datetime.utcnow()

        invoice.updated_at = datetime.utcnow()

        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        logger.info(f"Invoice {invoice_id} status updated from {old_status} to {new_status} for user {user_id}")

        return invoice

    def delete_invoice(self, db: Session, invoice_id: UUID, user_id: UUID) -> bool:
        """
        Permanently delete an invoice from the database (hard delete).
        Also deletes related posting logs.

        Args:
            db: Database session
            invoice_id: ID of the invoice to delete
            user_id: ID of the user deleting the invoice

        Returns:
            True if successful, False otherwise
        """
        from src.models.posting_log import PostingLog

        # Get the invoice (without is_deleted filter for deletion)
        invoice = db.exec(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.user_id == user_id)
        ).first()

        if not invoice:
            return False

        # Delete related posting logs first (cascade delete)
        posting_logs = db.exec(
            select(PostingLog).where(PostingLog.invoice_id == invoice_id)
        ).all()

        for log in posting_logs:
            db.delete(log)

        logger.info(f"Deleted {len(posting_logs)} posting logs for invoice {invoice_id}")

        # Hard delete - permanently remove from database
        db.delete(invoice)
        db.commit()

        logger.info(f"Invoice {invoice_id} permanently deleted from database for user {user_id}")

        return True

    def bulk_delete_invoices(self, db: Session, invoice_ids: List[UUID], user_id: UUID) -> dict:
        """
        Bulk delete multiple invoices in a single transaction.
        Also bulk deletes related posting logs.

        Args:
            db: Database session
            invoice_ids: List of invoice IDs to delete
            user_id: ID of the user deleting the invoices

        Returns:
            Dict with deleted_count, not_found_ids (IDs not belonging to user or not found)
        """
        from src.models.posting_log import PostingLog

        # Find which invoices belong to this user
        existing_ids = db.exec(
            select(Invoice.id)
            .where(Invoice.id.in_(invoice_ids))
            .where(Invoice.user_id == user_id)
        ).all()

        found_ids = set(existing_ids)
        not_found_ids = [str(uid) for uid in invoice_ids if uid not in found_ids]

        if not found_ids:
            return {"deleted_count": 0, "not_found_ids": not_found_ids, "failed": []}

        # Bulk delete posting logs for all found invoices (single query)
        db.execute(delete(PostingLog).where(PostingLog.invoice_id.in_(found_ids)))

        # Bulk delete invoices (single query)
        db.execute(delete(Invoice).where(Invoice.id.in_(found_ids)))

        db.commit()

        logger.info(f"Bulk deleted {len(found_ids)} invoices for user {user_id} ({len(not_found_ids)} not found)")

        return {
            "deleted_count": len(found_ids),
            "not_found_ids": not_found_ids,
            "failed": [],
        }

    def get_invoice_count(self, db: Session, user_id: UUID, filters: InvoiceFilter = None, environment_override: Optional[str] = None) -> int:
        """
        Get the count of invoices for a user with optional filtering.

        Args:
            db: Database session
            user_id: ID of the user
            filters: Optional filters to apply
            environment_override: Hard environment filter based on user's accessible tokens

        Returns:
            Count of invoices matching criteria
        """
        from sqlalchemy import func

        query = select(func.count(Invoice.id)).where(Invoice.user_id == user_id).where(Invoice.is_deleted == False)

        # Apply environment override (hard limit based on user tokens — applies regardless of filters)
        if environment_override:
            query = query.where(Invoice.environment == environment_override)

        if filters:
            # Apply user-requested environment filter only if no override
            if not environment_override and filters.environment:
                query = query.where(Invoice.environment == filters.environment)
            if filters.status:
                query = query.where(Invoice.status == filters.status)
            if filters.invoice_type:
                query = query.where(Invoice.invoice_type == filters.invoice_type)
            if filters.date_from:
                query = query.where(Invoice.created_at >= filters.date_from)
            if filters.date_to:
                query = query.where(Invoice.created_at <= filters.date_to)

        count = db.exec(query).one()

        return count

    def get_adjacent_invoices(self, db: Session, invoice_id: UUID, user_id: UUID, environment: Optional[str] = None) -> dict:
        """
        Get the previous and next invoice IDs for navigation.

        Args:
            db: Database session
            invoice_id: ID of the current invoice
            user_id: ID of the requesting user
            environment: Optional environment filter ("SANDBOX" or "PRODUCTION" or None for all)

        Returns:
            Dictionary with prev_id and next_id (both nullable UUIDs)
        """
        # Base filters shared across queries
        base_filters = [
            Invoice.user_id == user_id,
            Invoice.is_deleted == False,
        ]
        if environment:
            base_filters.append(Invoice.environment == environment)

        # Get the current invoice for its created_at timestamp
        current = db.exec(
            select(Invoice.created_at)
            .where(Invoice.id == invoice_id)
            .where(Invoice.user_id == user_id)
            .where(Invoice.is_deleted == False)
        ).first()

        if not current:
            return {"prev_id": None, "next_id": None}

        created_at = current  # scalar value from single-column select

        # Find previous invoice (created before current, most recent first)
        prev_result = db.exec(
            select(Invoice.id)
            .where(*base_filters)
            .where(Invoice.created_at < created_at)
            .order_by(Invoice.created_at.desc())
            .limit(1)
        ).first()

        # Find next invoice (created after current, oldest first)
        next_result = db.exec(
            select(Invoice.id)
            .where(*base_filters)
            .where(Invoice.created_at > created_at)
            .order_by(Invoice.created_at.asc())
            .limit(1)
        ).first()

        return {
            "prev_id": str(prev_result) if prev_result else None,
            "next_id": str(next_result) if next_result else None,
        }

    def validate_invoice_transition(self, current_status: InvoiceStatus, target_status: InvoiceStatus) -> bool:
        """
        Validate if a status transition is allowed according to the state machine.

        Args:
            current_status: Current status of the invoice
            target_status: Target status to transition to

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed_transitions = {
            InvoiceStatus.DRAFT: [InvoiceStatus.VALIDATED, InvoiceStatus.FAILED],
            InvoiceStatus.VALIDATED: [InvoiceStatus.POSTED, InvoiceStatus.FAILED],
            InvoiceStatus.POSTED: [InvoiceStatus.FAILED],  # From posted to failed in exceptional circumstances
            InvoiceStatus.FAILED: []  # No transitions from failed unless manually corrected
        }

        allowed_targets = allowed_transitions.get(current_status, [])
        is_allowed = target_status in allowed_targets

        if not is_allowed:
            logger.warning(f"Invalid status transition attempted: {current_status} -> {target_status}")

        return is_allowed

    def get_unified_invoice_history(
        self,
        db: Session,
        user_id: UUID,
        source: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
        environment: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """
        Get unified list of manual and automated invoices from main database only.

        IMPORTANT: This queries ONLY the main database Invoice table.
        Automated invoices appear here AFTER they've been transferred at 6 PM PKT.
        The 'source' field distinguishes between manual and automation invoices.

        Args:
            db: Main database session
            user_id: User UUID
            source: Filter by source ("manual", "automation", or None for all)
            status: Filter by status
            date_from: Filter by date from
            date_to: Filter by date to
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (list of normalized invoice dicts, total count)
        """
        # Build query for main database Invoice table only
        query = select(Invoice).where(
            Invoice.user_id == user_id,
            Invoice.is_deleted == False
        )

        # Apply source filter
        if source == "manual":
            query = query.where(Invoice.source == "manual")
        elif source == "automation":
            query = query.where(Invoice.source == "automation")
        # If source is None, show all (both manual and automation)

        # Apply date filters
        if date_from:
            query = query.where(Invoice.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.where(Invoice.created_at <= datetime.combine(date_to, datetime.max.time()))

        # Apply status filter
        if status:
            query = query.where(Invoice.status == status)

        # Apply environment filter (auto-filter based on user's available tokens)
        if environment:
            query = query.where(Invoice.environment == environment)

        # Order by created_at descending (newest first)
        query = query.order_by(Invoice.created_at.desc())

        # Get total count
        count_query = select(Invoice).where(
            Invoice.user_id == user_id,
            Invoice.is_deleted == False
        )
        if source == "manual":
            count_query = count_query.where(Invoice.source == "manual")
        elif source == "automation":
            count_query = count_query.where(Invoice.source == "automation")
        if date_from:
            count_query = count_query.where(Invoice.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            count_query = count_query.where(Invoice.created_at <= datetime.combine(date_to, datetime.max.time()))
        if status:
            count_query = count_query.where(Invoice.status == status)
        if environment:
            count_query = count_query.where(Invoice.environment == environment)

        from sqlalchemy import func
        total = db.exec(select(func.count()).select_from(count_query.subquery())).one()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        invoices = db.exec(query).all()

        # Normalize invoices
        unified_invoices = []
        for invoice in invoices:
            # Calculate total amount from items
            total_amount = sum(item.get('total_values', 0) for item in invoice.items) if invoice.items else 0

            # Normalize TRANSFERRED to VALIDATED — transferred invoices are validated
            normalized_status = invoice.status
            if invoice.status == InvoiceStatus.TRANSFERRED:
                normalized_status = InvoiceStatus.VALIDATED

            unified_invoices.append({
                "id": invoice.id,
                "source": "manual",  # Always "manual" — automation source is hidden
                "invoice_number": invoice.external_id,
                "invoice_type": invoice.invoice_type,
                "invoice_date": invoice.invoice_date,
                "buyer_business_name": invoice.buyer_business_name,
                "seller_business_name": invoice.seller_business_name,
                "total_amount": total_amount,
                "status": normalized_status,
                "created_at": invoice.created_at,
                "environment": invoice.environment if invoice.environment else None,
                "fbr_reference_number": invoice.fbr_reference_number,
                "income_tax": invoice.income_tax if invoice.income_tax else "236G",
                "scheduled_date": None,
                "scheduled_time": None
            })

        logger.info(f"Retrieved {len(unified_invoices)} invoices for user {user_id} (total: {total})")

        return unified_invoices, total