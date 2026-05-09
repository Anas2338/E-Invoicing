from fastapi import APIRouter, Depends, Request
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
import logging

from src.database.session import get_db
from src.models.invoice import Invoice, InvoiceStatus
from src.api.middleware.auth_middleware import require_authentication
from src.utils.rate_limits import RateLimits
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/stats")
@limiter.limit(RateLimits.DASHBOARD_STATS)
def get_dashboard_stats(
    request: Request,
    user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db)
):
    """
    Get all dashboard statistics in a single optimized query.

    Returns:
    - Manual invoice counts by status
    - Recent 10 invoices

    PERFORMANCE: Single endpoint with optimized queries.
    Uses COUNT queries instead of fetching full records.
    """
    user_uuid = UUID(user_id)

    # Query 1: Get manual invoice counts by status (single query with GROUP BY)
    manual_counts_query = (
        select(
            Invoice.status,
            func.count(Invoice.id).label('count')
        )
        .where(Invoice.user_id == user_uuid)
        .group_by(Invoice.status)
    )
    manual_counts_result = db.execute(manual_counts_query).all()

    # Convert to dict
    manual_stats = {
        'draft': 0,
        'validated': 0,
        'posted': 0,
        'failed': 0
    }
    for status, count in manual_counts_result:
        status_lower = status.lower()
        if status_lower in manual_stats:
            manual_stats[status_lower] = count

    # Query 2: Get recent 10 manual invoices (lightweight - only needed fields)
    recent_invoices_query = (
        select(Invoice)
        .where(Invoice.user_id == user_uuid)
        .order_by(Invoice.created_at.desc())
        .limit(10)
    )
    recent_invoices = db.execute(recent_invoices_query).scalars().all()

    # Transform recent invoices to lightweight format
    recent_invoices_data = []
    for invoice in recent_invoices:
        # Calculate total amount from items
        total_amount = 0
        if invoice.items:
            for item in invoice.items:
                total_amount += item.get('total_values', 0)

        # Handle date formatting - invoice_date might be string or date object
        if invoice.invoice_date:
            invoice_date_str = invoice.invoice_date if isinstance(invoice.invoice_date, str) else invoice.invoice_date.isoformat()
        else:
            # Fallback to created_at
            invoice_date_str = invoice.created_at.isoformat().split('T')[0] if hasattr(invoice.created_at, 'isoformat') else str(invoice.created_at).split('T')[0]

        recent_invoices_data.append({
            'id': str(invoice.id),
            'number': invoice.external_id,
            'date': invoice_date_str,
            'amount': total_amount,
            'status': invoice.status.lower()
        })

    return {
        'manual_stats': manual_stats,
        'recent_invoices': recent_invoices_data,
        'total_manual': sum(manual_stats.values())
    }
