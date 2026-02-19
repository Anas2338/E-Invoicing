from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, select
from uuid import UUID
import logging

from src.models.invoice import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus
from src.models.user import User
from src.models.fbr_response import FBRResponse
from src.schemas.invoice import InvoiceFilter
from src.utils.helpers import calculate_hash


logger = logging.getLogger(__name__)


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
        # Generate external ID if not provided
        external_id = invoice_create.external_id or f"INV-{int(datetime.utcnow().timestamp())}-{hash(str(invoice_create.invoice_type)) % 10000}"

        # Create invoice object with FBR-specific fields
        db_invoice = Invoice(
            external_id=external_id,
            user_id=user_id,
            invoice_type=invoice_create.invoice_type,
            invoice_date=invoice_create.invoice_date,
            seller_ntn_cnic=invoice_create.seller_ntn_cnic,
            seller_business_name=invoice_create.seller_business_name,
            seller_province=invoice_create.seller_province,
            seller_address=invoice_create.seller_address,
            buyer_ntn_cnic=invoice_create.buyer_ntn_cnic,
            buyer_business_name=invoice_create.buyer_business_name,
            buyer_province=invoice_create.buyer_province,
            buyer_address=invoice_create.buyer_address,
            buyer_registration_type=invoice_create.buyer_registration_type,
            invoice_ref_no=invoice_create.invoice_ref_no,
            scenario_id=invoice_create.scenario_id,
            items=[item.model_dump() for item in invoice_create.items],
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

    def get_invoices_by_user(self, db: Session, user_id: UUID, filters: InvoiceFilter) -> List[Invoice]:
        """
        Get all invoices for a specific user with optional filtering.

        Args:
            db: Database session
            user_id: ID of the user whose invoices to retrieve
            filters: Filtering parameters

        Returns:
            List of Invoice objects matching the criteria
        """
        query = select(Invoice).where(Invoice.user_id == user_id).where(Invoice.is_deleted == False)

        # Apply filters
        if filters.status:
            query = query.where(Invoice.status == filters.status)
        if filters.invoice_type:
            query = query.where(Invoice.invoice_type == filters.invoice_type)
        if filters.environment:
            query = query.where(Invoice.environment == filters.environment)
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

        # Update fields directly from the dict
        for field, value in update_data.items():
            if hasattr(invoice, field):
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

        Args:
            db: Database session
            invoice_id: ID of the invoice to delete
            user_id: ID of the user deleting the invoice

        Returns:
            True if successful, False otherwise
        """
        # Get the invoice (without is_deleted filter for deletion)
        invoice = db.exec(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .where(Invoice.user_id == user_id)
        ).first()

        if not invoice:
            return False

        # Hard delete - permanently remove from database
        db.delete(invoice)
        db.commit()

        logger.info(f"Invoice {invoice_id} permanently deleted from database for user {user_id}")

        return True

    def get_invoice_count(self, db: Session, user_id: UUID, filters: InvoiceFilter = None) -> int:
        """
        Get the count of invoices for a user with optional filtering.

        Args:
            db: Database session
            user_id: ID of the user
            filters: Optional filters to apply

        Returns:
            Count of invoices matching criteria
        """
        from sqlalchemy import func

        query = select(func.count(Invoice.id)).where(Invoice.user_id == user_id).where(Invoice.is_deleted == False)

        if filters:
            if filters.status:
                query = query.where(Invoice.status == filters.status)
            if filters.invoice_type:
                query = query.where(Invoice.invoice_type == filters.invoice_type)
            if filters.environment:
                query = query.where(Invoice.environment == filters.environment)
            if filters.date_from:
                query = query.where(Invoice.created_at >= filters.date_from)
            if filters.date_to:
                query = query.where(Invoice.created_at <= filters.date_to)

        count = db.exec(query).one()

        return count

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