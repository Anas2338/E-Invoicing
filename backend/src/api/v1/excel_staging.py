"""
API router for Excel staging endpoints.

All endpoints are under /api/v1/invoices/excel/staging
and require authentication.
"""
from __future__ import annotations

import logging
import re
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import DataError
from sqlmodel import Session

from src.api.deps import get_database_session
from src.api.middleware.auth_middleware import require_authentication
from src.schemas.excel_staging import (
    StagingSessionResponse,
    StagingSessionDetailResponse,
    StagingRowResponse,
    StagingUploadResponse,
    StagingRecheckResponse,
    StagingCommitResponse,
    StagingCommitInvoiceInfo,
    StagingCommitError,
    StagingCancelResponse,
    StagingActiveSessionsResponse,
    StagingRowUpdateRequest,
)
from src.services.excel_staging_service import ExcelStagingService
from src.utils.rate_limits import RateLimits

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

staging_service = ExcelStagingService()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=StagingUploadResponse, status_code=201)
@limiter.limit(RateLimits.FILE_UPLOAD)
async def upload_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Upload an Excel file and create a staging session.

    Parses all rows, validates them, and returns a session summary.
    Replaces any existing active session for this user.
    """
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 10 MB limit ({len(contents) / 1024 / 1024:.1f} MB).",
        )

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .xlsx files are accepted.",
        )

    # Validate file content (not empty)
    if len(contents) < 100:  # Minimum valid .xlsx is ~8KB
        raise HTTPException(
            status_code=400,
            detail="File is empty or contains no valid data.",
        )

    # Fetch invoice numbers already in use in the automation DB (not yet
    # transferred) so auto-issued numbers skip them
    from src.utils.helpers import fetch_automation_invoice_numbers
    automation_invoice_numbers = await fetch_automation_invoice_numbers(request)

    try:
        session = staging_service.create_session_from_upload(
            db=db,
            user_id=UUID(user_id),
            filename=file.filename,
            file_bytes=BytesIO(contents),
            automation_invoice_numbers=automation_invoice_numbers,
        )
    except DataError as e:
        # Catch data errors (column size, type mismatches) and show a clean message
        logger.exception("DataError uploading for user %s: %s", user_id, e)
        # Extract the PostgreSQL error detail (column name / value hint)
        err_msg = str(e)
        # Strip the SQL and parameters portion — keep only the DB driver message
        clean_msg = err_msg.split("\n[SQL:")[0] if "\n[SQL:" in err_msg else err_msg
        # Try to extract column name from error
        col_match = re.search(
            r'column "(\w+)"|for (?:column|type) (\w+)|(?:value too long|violates)',
            clean_msg, re.IGNORECASE,
        )
        suffix = f" — check column: {col_match.group(1)}" if col_match else ""
        raise HTTPException(
            status_code=400,
            detail=(
                f"Data error while saving to database{suffix}. "
                "This usually means a field value is too long or has the wrong type. "
                "Please check your Excel file data and try again."
            ),
        )
    except Exception as e:
        logger.exception("Upload failed for user %s: %s", user_id, e)
        err_msg = str(e)
        # Strip SQL and parameters — keep only the DB driver / Python error portion
        if "\n[SQL:" in err_msg:
            err_msg = err_msg.split("\n[SQL:")[0]
        if "\n[parameters:" in err_msg:
            err_msg = err_msg.split("\n[parameters:")[0]
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process file: {err_msg[:500]}",
        )

    return StagingUploadResponse(
        session_id=session.id,
        status=session.status.value if hasattr(session.status, 'value') else str(session.status),
        original_filename=session.original_filename,
        total_rows=session.total_rows,
        valid_rows=session.valid_rows,
        errored_rows=session.errored_rows,
    )


@router.get("/active", response_model=StagingActiveSessionsResponse)
def get_active_sessions(
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Get the user's active (non-terminal) staging sessions."""
    session = staging_service.get_active_session(
        db=db, user_id=UUID(user_id),
    )
    sessions = []
    if session:
        sessions.append(StagingSessionResponse.from_orm(session))
    return StagingActiveSessionsResponse(sessions=sessions)


@router.get(
    "/{session_id}",
    response_model=StagingSessionDetailResponse,
)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Get a staging session with all its rows."""
    session, rows = staging_service.get_session_with_rows(
        db=db, session_id=session_id, user_id=UUID(user_id),
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        return StagingSessionDetailResponse.from_orm(session, rows)
    except Exception as e:
        logger.exception("Failed to serialize session %s: %s", session_id, e)
        raise HTTPException(
            status_code=500,
            detail="Failed to load staging session data. Please try again.",
        )


@router.put(
    "/{session_id}/rows/{row_id}",
    response_model=StagingRowResponse,
)
def update_row(
    session_id: UUID,
    row_id: UUID,
    updates: StagingRowUpdateRequest,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Update one or more fields on a staging row."""
    # Filter out None values (only send changed fields)
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = staging_service.update_row(
        db=db,
        session_id=session_id,
        row_id=row_id,
        user_id=UUID(user_id),
        updates=update_dict,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Session or row not found",
        )

    return StagingRowResponse.model_validate(row)


@router.post("/{session_id}/recheck", response_model=StagingRecheckResponse)
def recheck_session(
    session_id: UUID,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Re-validate all dirty rows in a staging session."""
    result = staging_service.recheck_session(
        db=db, session_id=session_id, user_id=UUID(user_id),
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or not in recheckable state",
        )

    rows, errored_before, errored_after, all_clear = result
    return StagingRecheckResponse(
        session_id=session_id,
        errored_rows_before=errored_before,
        errored_rows_after=errored_after,
        all_clear=all_clear,
        rows=[StagingRowResponse.model_validate(r) for r in rows],
    )


@router.post("/{session_id}/commit", response_model=StagingCommitResponse)
def commit_session(
    session_id: UUID,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Create DRAFT invoices from all valid rows. Deletes session on success."""
    result = staging_service.commit_session(
        db=db, session_id=session_id, user_id=UUID(user_id),
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"],
        )

    return StagingCommitResponse(
        session_id=result["session_id"],
        total_committed=result["total_committed"],
        total_failed=result["total_failed"],
        invoices=[StagingCommitInvoiceInfo(**i) for i in result["invoices"]],
        errors=[StagingCommitError(**e) for e in result["errors"]],
    )


@router.delete("/{session_id}", response_model=StagingCancelResponse)
def cancel_session(
    session_id: UUID,
    db: Session = Depends(get_database_session),
    user_id: str = Depends(require_authentication),
):
    """Cancel and delete a staging session."""
    deleted = staging_service.cancel_session(
        db=db, session_id=session_id, user_id=UUID(user_id),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return StagingCancelResponse()
