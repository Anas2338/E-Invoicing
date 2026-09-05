"""
Company-scope helpers for company-linked accounts.

Semantics (specs/006-company-linked-accounts/data-model.md §1-2):

- ``company_id == id``        → company owner (or standalone single-member company)
- ``company_id == <other id>`` → employee account linked to that owner
- ``company_id is None``      → transient (pre-migration); treated as owner-of-self

The "effective user" is the row that holds company-level state (FBR tokens,
seller identity, numbering settings): the owner's row for employees, the
actor's own row for owners/standalone accounts.
"""
import logging
from typing import List
from uuid import UUID

from sqlmodel import Session, select

from src.models.user import User

logger = logging.getLogger(__name__)


def is_company_owner(user: User) -> bool:
    """True when the account is the root of its own company (``company_id == id``)."""
    return user.company_id is None or user.company_id == user.id


def get_company_root_id(db: Session, actor: User) -> UUID:
    """
    The company root id for an actor: their own id for owners/standalone
    accounts, the owning account's id for employees.
    """
    if is_company_owner(actor):
        return actor.id
    return actor.company_id  # type: ignore[return-value]


def resolve_effective_user(db: Session, actor: User) -> User:
    """
    Resolve the effective company row: the owner's row for employee members
    (holds FBR tokens, seller fields, numbering settings), the actor's own
    row for owners/standalone accounts.
    """
    if is_company_owner(actor):
        return actor
    owner = db.get(User, actor.company_id)
    if owner is None:
        # Defensive: never crash a member's request if the owner row vanished
        logger.error(
            "Company owner %s missing for member %s — falling back to member row",
            actor.company_id, actor.id,
        )
        return actor
    return owner


def get_company_member_ids(db: Session, actor: User) -> List[UUID]:
    """
    All user ids in the actor's company — owner + employees INCLUDING
    deactivated employees (their rows remain company data). For a standalone
    owner this degrades to ``[actor.id]``.
    """
    root_id = get_company_root_id(db, actor)
    statement = select(User.id).where(User.company_id == root_id)
    return [row[0] for row in db.exec(statement).all()]
