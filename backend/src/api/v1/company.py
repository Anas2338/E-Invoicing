"""
Company endpoints: employee provisioning (owner-only).

Company semantics: a user with ``company_id == id`` is a company owner
(standalone accounts are owners of their own single-member company).
Employees point their ``company_id`` at the owner's id.

- POST /employees                      create auto-approved employee
- GET  /employees                      list company members (owner + employees)
- POST /employees/{id}/deactivate      block login, keep data (never delete)
"""
import logging
import secrets
import string
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select

from src.api.middleware.auth_middleware import require_authentication
from src.api.v1.auth import get_password_hash
from src.database.session import get_db
from src.models.user import User
from src.services.company_service import is_company_owner, get_company_member_ids
from src.utils.helpers import sanitize_input
from src.utils.password_validator import validate_password_strength


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

OWNER_ONLY_DETAIL = "Only the company owner can manage employees"

# Password generation alphabet — every generated password is built from all
# four required classes, so it passes validate_password_strength by construction.
_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # no I/O (ambiguous)
_LOWER = "abcdefghijkmnpqrstuvwxyz"   # no l/o
_DIGITS = "23456789"                  # no 0/1
_SPECIAL = "!@#$%&*_-+=?"             # unambiguous, regex-safe specials


class EmployeeCreate(BaseModel):
    """Request body for creating an employee account."""
    email: str
    name: str
    password: str | None = None


def _generate_temporary_password(length: int = 12) -> str:
    """
    Generate a policy-compliant temporary password (upper + lower + digit +
    special, no ambiguous chars, shuffled with ``secrets``).
    """
    while True:
        required = [
            secrets.choice(_UPPER),
            secrets.choice(_LOWER),
            secrets.choice(_DIGITS),
            secrets.choice(_SPECIAL),
        ]
        pool = _UPPER + _LOWER + _DIGITS + _SPECIAL
        remaining = [secrets.choice(pool) for _ in range(length - len(required))]
        chars = required + remaining
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)
        is_valid, _ = validate_password_strength(candidate)
        if is_valid:
            return candidate


def _load_actor(db: Session, current_user_id) -> User:
    """Load the authenticated user; 401 if missing (should not happen)."""
    actor = db.get(User, uuid.UUID(str(current_user_id)))
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return actor


def _require_owner(actor: User) -> None:
    """403 unless the actor is a company owner (``company_id == id``)."""
    if not is_company_owner(actor):
        logger.warning(
            "Non-owner user %s attempted company management (FR-015)",
            actor.id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=OWNER_ONLY_DETAIL,
        )


def _member_payload(user: User) -> dict:
    """Contract §1 member object."""
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_company_owner": is_company_owner(user),
        "automation_enabled": user.automation_enabled,
        "is_active": user.is_active,
        "account_status": user.account_status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/employees", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def create_employee(
    request: Request,
    payload: EmployeeCreate,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Create an auto-approved employee account linked to the caller's company.

    Owner-only. The generated temporary password is returned ONCE in the 201
    response and is never stored in plaintext or returned again.
    """
    actor = _load_actor(db, current_user_id)
    _require_owner(actor)

    email = sanitize_input(payload.email).lower().strip()
    name = sanitize_input(payload.name)

    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email is required",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required",
        )

    # No partial rows: uniqueness is checked before any write (FR-012)
    existing = db.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    if payload.password:
        is_valid, error_message = validate_password_strength(payload.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message,
            )
        temporary_password = None
    else:
        temporary_password = _generate_temporary_password()

    password = payload.password or temporary_password

    employee = User(
        email=email,
        name=name,
        hashed_password=get_password_hash(password),
        is_active=True,
        role="user",
        account_status="approved",  # auto-approved — no pending queue (FR-002)
        approval_flags={"has_production_access": False, "can_post_to_production": False},
        automation_enabled=False,   # automation is owner-only; admin toggle is the only escalation
        company_id=actor.id,        # employee points at the owning account
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    logger.info(
        "Company owner %s provisioned employee %s (%s)",
        actor.id, employee.id, email,
    )

    response = _member_payload(employee)
    response["created_at"] = employee.created_at.isoformat() if employee.created_at else None
    # Returned ONCE — the only time the plaintext password leaves the server
    response["temporary_password"] = temporary_password
    return response


@router.get("/employees")
def list_employees(
    request: Request,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    List the caller's company members — owner + active + deactivated
    employees (deactivated members keep company_id so their rows remain
    company data). Owner-only.
    """
    actor = _load_actor(db, current_user_id)
    _require_owner(actor)

    members = db.exec(
        select(User).where(User.company_id == actor.id).order_by(User.created_at)
    ).all()

    return {
        "members": [_member_payload(m) for m in members],
        "total": len(members),
    }


@router.post("/employees/{employee_id}/deactivate")
def deactivate_employee(
    employee_id: str,
    request: Request,
    current_user_id: str = Depends(require_authentication),
    db: Session = Depends(get_db),
):
    """
    Deactivate an employee: blocks login AND kills existing sessions
    (token_version bump). Company data is retained. Never hard-deletes.
    """
    actor = _load_actor(db, current_user_id)
    _require_owner(actor)

    try:
        target_id = uuid.UUID(employee_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if target_id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate the company owner",
        )

    target = db.get(User, target_id)
    if not target or target.company_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if not target.is_active:
        # Idempotent — already deactivated
        return {"id": str(target.id), "is_active": False}

    target.is_active = False
    target.token_version += 1  # existing sessions die immediately (FR-011)

    db.add(target)
    db.commit()
    db.refresh(target)

    logger.info(
        "Company owner %s deactivated employee %s (%s)",
        actor.id, target.id, target.email,
    )

    return {"id": str(target.id), "is_active": target.is_active}
