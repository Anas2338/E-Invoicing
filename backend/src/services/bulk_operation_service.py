"""
Background processing service for bulk invoice validation and posting.

Each bulk operation runs as a FastAPI BackgroundTask, processing invoices
one-by-one and updating progress in the database after each invoice.
Uses its own database sessions (independent of the request session).
"""
import logging
from uuid import UUID
from typing import List, Optional, Callable, Generator
from datetime import datetime
from contextlib import contextmanager

from sqlmodel import Session, select
from sqlalchemy.orm.attributes import flag_modified

from src.database.session import get_db_session
from src.models.invoice import Invoice, InvoiceStatus
from src.models.bulk_operation import (
    BulkOperationTask,
    BulkOperationStatus,
)
from src.services.fbr_service import fbr_service
from src.services.posting_service import PostingService
from src.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)


class BulkOperationService:
    """
    Processes bulk invoice operations (validate/post) in the background.

    Each method is a coroutine that owns its database lifecycle — it
    creates its own session via the provided session factory (defaults to
    get_db_session()) rather than sharing the request's session, because
    BackgroundTasks outlive the request.
    """

    def __init__(
        self,
        db_session_factory: Optional[Callable[[], Generator[Session, None, None]]] = None,
    ) -> None:
        """
        Initialize the service with helper services.

        Args:
            db_session_factory: Callable that yields a Session context manager.
                Defaults to get_db_session if not provided.
        """
        self.invoice_service = InvoiceService()
        self.posting_service = PostingService()
        self._session_factory = db_session_factory or get_db_session

    async def bulk_validate_invoices(
        self,
        task_id: UUID,
        invoice_ids: List[UUID],
        user_id: UUID,
    ) -> None:
        """
        Validate invoices in the background, updating progress per invoice.

        Args:
            task_id: UUID of the BulkOperationTask to track progress
            invoice_ids: List of invoice UUIDs to validate
            user_id: UUID of the user who owns the operation
        """
        logger.info(
            "Starting bulk validation: task=%s, invoices=%d, user=%s",
            task_id, len(invoice_ids), user_id,
        )

        with self._session_factory() as db:
            try:
                task = db.get(BulkOperationTask, task_id)
                if not task:
                    logger.error("Bulk operation task %s not found", task_id)
                    return

                for invoice_id in invoice_ids:
                    # Check if task was cancelled; if so, stop processing
                    db.refresh(task)
                    if task.status == BulkOperationStatus.CANCELLED:
                        logger.info("Bulk operation task %s was cancelled mid-way", task_id)
                        break

                    try:
                        invoice = self.invoice_service.get_invoice_by_id(
                            db, invoice_id, user_id
                        )

                        if not invoice:
                            task.processed_count += 1
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": str(invoice_id),
                                "error": "Invoice not found",
                            })
                            _update_task(db, task)
                            continue

                        # Skip invoices not in DRAFT or FAILED status
                        if (
                            invoice.status != InvoiceStatus.DRAFT
                            and invoice.status != InvoiceStatus.FAILED
                        ):
                            task.processed_count += 1
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": invoice.external_id,
                                "error": f"Cannot validate invoice in {invoice.status} status",
                            })
                            _update_task(db, task)
                            continue

                        # Get user's FBR token from the invoice's environment
                        from src.models.user import User
                        user = db.get(User, user_id)
                        if not user:
                            task.processed_count += 1
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": invoice.external_id,
                                "error": "User not found",
                            })
                            _update_task(db, task)
                            continue

                        # Select and decrypt token based on environment
                        encrypted_token = _get_fbr_token(user, invoice.environment)
                        if not encrypted_token:
                            task.processed_count += 1
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": invoice.external_id,
                                "error": f"FBR {invoice.environment} token not configured",
                            })
                            _update_task(db, task)
                            continue

                        access_token = _decrypt_token(encrypted_token)

                        # Call FBR validation
                        fbr_response, fbr_request_payload = await fbr_service.validate_invoice(
                            invoice, access_token, db=db
                        )

                        is_valid, error_message, item_errors = (
                            fbr_service.parse_validation_response(fbr_response)
                        )

                        task.processed_count += 1

                        if is_valid:
                            self.invoice_service.update_invoice_status(
                                db, invoice_id, InvoiceStatus.VALIDATED, user_id
                            )
                            task.success_count += 1
                            logger.info(
                                "Invoice %s validated successfully", invoice.external_id
                            )
                        else:
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": invoice.external_id,
                                "error": error_message or "Validation failed",
                            })
                            logger.warning(
                                "Invoice %s validation failed: %s",
                                invoice.external_id, error_message,
                            )

                        _update_task(db, task)

                    except Exception as e:
                        task.processed_count += 1
                        task.failure_count += 1
                        task.errors.append({
                            "invoice_id": str(invoice_id),
                            "invoice_number": str(invoice_id),
                            "error": str(e),
                        })
                        _update_task(db, task)
                        logger.error("Error validating invoice %s: %s", invoice_id, e)

                # Set terminal status
                _finalize_task(db, task)
                logger.info(
                    "Bulk validation completed: task=%s, success=%d, failed=%d",
                    task_id, task.success_count, task.failure_count,
                )

            except Exception as e:
                logger.error(
                    "Bulk validation task %s crashed: %s", task_id, e, exc_info=True
                )
                try:
                    task.status = BulkOperationStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    db.add(task)
                    db.commit()
                except Exception:
                    db.rollback()

    async def bulk_post_invoices(
        self,
        task_id: UUID,
        invoice_ids: List[UUID],
        environment: str,
        user_id: UUID,
    ) -> None:
        """
        Post invoices in the background, updating progress per invoice.

        Args:
            task_id: UUID of the BulkOperationTask to track progress
            invoice_ids: List of invoice UUIDs to post
            environment: FBR environment ("SANDBOX" or "PRODUCTION")
            user_id: UUID of the user who owns the operation
        """
        logger.info(
            "Starting bulk posting: task=%s, invoices=%d, user=%s, env=%s",
            task_id, len(invoice_ids), user_id, environment,
        )

        with self._session_factory() as db:
            try:
                task = db.get(BulkOperationTask, task_id)
                if not task:
                    logger.error("Bulk operation task %s not found", task_id)
                    return

                for invoice_id in invoice_ids:
                    # Check if task was cancelled; if so, stop processing
                    db.refresh(task)
                    if task.status == BulkOperationStatus.CANCELLED:
                        logger.info("Bulk operation task %s was cancelled mid-way", task_id)
                        break

                    try:
                        invoice = self.invoice_service.get_invoice_by_id(
                            db, invoice_id, user_id
                        )

                        if not invoice:
                            task.processed_count += 1
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": str(invoice_id),
                                "error": "Invoice not found",
                            })
                            _update_task(db, task)
                            continue

                        # Skip invoices not in VALIDATED status
                        if invoice.status != InvoiceStatus.VALIDATED:
                            task.processed_count += 1
                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": invoice.external_id,
                                "error": f"Cannot post invoice in {invoice.status} status",
                            })
                            _update_task(db, task)
                            continue

                        # Post via PostingService
                        is_posted, reference_number, response_data = (
                            await self.posting_service.post_single_invoice(
                                db=db,
                                invoice=invoice,
                                user_id=str(user_id),
                                posting_environment=environment,
                            )
                        )

                        task.processed_count += 1

                        if is_posted:
                            task.success_count += 1
                            logger.info(
                                "Invoice %s posted successfully: %s",
                                invoice.external_id, reference_number,
                            )
                        else:
                            error_msg = "Unknown error"
                            if isinstance(response_data, dict):
                                error_msg = response_data.get("error", str(response_data))
                            else:
                                error_msg = str(response_data)

                            task.failure_count += 1
                            task.errors.append({
                                "invoice_id": str(invoice_id),
                                "invoice_number": invoice.external_id,
                                "error": error_msg,
                            })
                            logger.warning(
                                "Invoice %s posting failed: %s",
                                invoice.external_id, error_msg,
                            )

                        _update_task(db, task)

                    except Exception as e:
                        task.processed_count += 1
                        task.failure_count += 1
                        task.errors.append({
                            "invoice_id": str(invoice_id),
                            "invoice_number": str(invoice_id),
                            "error": str(e),
                        })
                        _update_task(db, task)
                        logger.error("Error posting invoice %s: %s", invoice_id, e)

                # Set terminal status
                _finalize_task(db, task)
                logger.info(
                    "Bulk posting completed: task=%s, success=%d, failed=%d",
                    task_id, task.success_count, task.failure_count,
                )

            except Exception as e:
                logger.error(
                    "Bulk posting task %s crashed: %s", task_id, e, exc_info=True
                )
                try:
                    task.status = BulkOperationStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    db.add(task)
                    db.commit()
                except Exception:
                    db.rollback()

    def get_task(
        self, db: Session, task_id: UUID, user_id: UUID
    ) -> Optional[BulkOperationTask]:
        """
        Retrieve a bulk operation task by id and user_id.

        Args:
            db: Database session
            task_id: UUID of the task
            user_id: UUID of the owning user

        Returns:
            BulkOperationTask if found, None otherwise
        """
        statement = select(BulkOperationTask).where(
            BulkOperationTask.id == task_id,
            BulkOperationTask.user_id == user_id,
        )
        return db.exec(statement).first()

    def get_active_tasks(
        self, db: Session, user_id: UUID
    ) -> List[BulkOperationTask]:
        """
        Get all currently processing tasks for a user.

        Args:
            db: Database session
            user_id: UUID of the user

        Returns:
            List of processing BulkOperationTask objects
        """
        statement = select(BulkOperationTask).where(
            BulkOperationTask.user_id == user_id,
            BulkOperationTask.status == BulkOperationStatus.PROCESSING,
        )
        return list(db.exec(statement).all())

    def has_active_operation(
        self, db: Session, user_id: UUID
    ) -> bool:
        """
        Check if a user has any processing bulk operation.

        Args:
            db: Database session
            user_id: UUID of the user

        Returns:
            True if any processing task exists for this user
        """
        statement = select(BulkOperationTask).where(
            BulkOperationTask.user_id == user_id,
            BulkOperationTask.status == BulkOperationStatus.PROCESSING,
        ).limit(1)
        return db.exec(statement).first() is not None

    def cancel_task(
        self, db: Session, task_id: UUID, user_id: UUID
    ) -> Optional[BulkOperationTask]:
        """
        Cancel a processing bulk operation.

        Sets status to CANCELLED so the background loop stops.

        Args:
            db: Database session
            task_id: UUID of the task to cancel
            user_id: UUID of the owning user

        Returns:
            The cancelled task, or None if not found
        """
        task = self.get_task(db, task_id, user_id)
        if not task:
            return None
        if task.status != BulkOperationStatus.PROCESSING:
            return None

        task.status = BulkOperationStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _update_task(db: Session, task: BulkOperationTask) -> None:
    """Save current task progress and commit."""
    task.updated_at = datetime.utcnow()
    # Flag errors as modified so SQLAlchemy detects in-place list mutations
    flag_modified(task, "errors")
    db.add(task)
    db.commit()


def _finalize_task(db: Session, task: BulkOperationTask) -> None:
    """Set terminal status and completed_at timestamp."""
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()

    if task.failure_count == 0:
        task.status = BulkOperationStatus.COMPLETED
    elif task.success_count > 0:
        task.status = BulkOperationStatus.PARTIALLY_COMPLETED
    else:
        task.status = BulkOperationStatus.FAILED

    db.add(task)
    db.commit()


def _get_fbr_token(user, environment: str) -> Optional[str]:
    """
    Get the encrypted FBR token for the given environment.

    Args:
        user: User model instance
        environment: "SANDBOX" or "PRODUCTION"

    Returns:
        Encrypted token string, or None if not configured
    """
    if environment == "SANDBOX":
        return user.fbr_sandbox_token or user.fbr_access_token
    return user.fbr_production_token or user.fbr_access_token


def _decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an FBR token using the encryption service.

    Args:
        encrypted_token: Encrypted token string

    Returns:
        Decrypted token string

    Raises:
        Exception: If decryption fails
    """
    from src.utils.encryption import get_encryption_service
    encryption_service = get_encryption_service()
    return encryption_service.decrypt(encrypted_token)
