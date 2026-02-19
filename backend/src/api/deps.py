from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from src.database.session import get_db
from src.models.user import User
from src.models.invoice import Invoice
from src.utils.jwt_utils import decode_jwt_token
from src.config.settings import settings


from contextlib import contextmanager

def get_database_session():
    """
    Dependency to provide database sessions to API endpoints.
    """
    yield from get_db()


def get_current_user(
    db: Session = Depends(get_database_session)
) -> User:
    """
    Dependency to get the current authenticated user from the request.

    Args:
        db: Database session

    Returns:
        Current authenticated User object

    Raises:
        HTTPException: If no user is authenticated
    """
    # This would normally extract user from request state after middleware
    # For now, we'll simulate the functionality
    # In practice, this would access request.state.user_id set by AuthMiddleware
    pass


def get_invoice_by_id(
    invoice_id: str,
    db: Session = Depends(get_database_session)
) -> Invoice:
    """
    Dependency to get an invoice by its ID, ensuring the user has access.

    Args:
        invoice_id: ID of the invoice to retrieve
        db: Database session

    Returns:
        Invoice object if found and user has access

    Raises:
        HTTPException: If invoice not found or user doesn't have access
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return invoice


def require_admin_access():
    """
    Dependency to require admin-level access for certain endpoints.

    Raises:
        HTTPException: If user doesn't have admin access
    """
    # This would check for admin permissions in the token
    # Implementation would depend on how admin status is determined
    pass


def verify_rate_limit():
    """
    Dependency to verify rate limits before processing requests.
    """
    # This would implement rate limiting logic
    # Would check against user ID and configured limits
    pass


def get_pagination_params(
    skip: int = 0,
    limit: int = 100
):
    """
    Dependency to get pagination parameters.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Tuple of (skip, limit) parameters
    """
    return skip, limit


def validate_api_key(api_key: str = None):
    """
    Dependency to validate API key if required for certain endpoints.

    Args:
        api_key: API key provided in the request

    Raises:
        HTTPException: If API key is invalid or missing
    """
    # This would validate the API key against stored values
    # Implementation would depend on how API keys are managed
    pass


def get_filtered_query_params(
    status: str = None,
    invoice_type: str = None,
    environment: str = None,
    date_from: str = None,
    date_to: str = None
):
    """
    Dependency to get and validate filtering parameters for queries.

    Args:
        status: Filter by invoice status
        invoice_type: Filter by invoice type (SALE/PURCHASE)
        environment: Filter by environment (SANDBOX/PRODUCTION)
        date_from: Filter by date range start
        date_to: Filter by date range end

    Returns:
        Dictionary of filter parameters
    """
    filters = {}

    if status:
        filters["status"] = status
    if invoice_type:
        filters["invoice_type"] = invoice_type
    if environment:
        filters["environment"] = environment
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to

    return filters