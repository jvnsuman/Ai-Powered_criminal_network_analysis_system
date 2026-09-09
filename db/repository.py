"""
db/repository.py

The persistence adapter: converts between db.models' ORM rows and the
plain domain dataclasses (schema.user.Agency/User, schema.case.Case).
Callers (api/auth.py, api/routes/) work entirely in terms of the
dataclasses and never see an ORM object — this is the one place that
translation happens, so the rest of the app doesn't need to know
SQLAlchemy exists.
"""

from typing import Optional

from sqlalchemy.orm import Session

from db.models import AgencyORM, CaseORM, SourceDocumentORM, UserORM
from schema.case import Case, CaseStatus
from schema.entities import SourceDocument
from schema.user import Agency, Role, User


def _agency_to_domain(row: AgencyORM) -> Agency:
    """Convert an AgencyORM row into a schema.user.Agency dataclass."""
    return Agency(
        id=row.id,
        name=row.name,
        agency_type=row.agency_type,
        parent_agency_id=row.parent_agency_id,
        is_active=row.is_active == "true",
    )


def _user_to_domain(row: UserORM) -> User:
    """Convert a UserORM row into a schema.user.User dataclass."""
    return User(
        id=row.id,
        name=row.name,
        badge_id=row.badge_id,
        agency_id=row.agency_id,
        role=Role(row.role),
        password_hash=row.password_hash,
        last_login=row.last_login,
    )


def _case_to_domain(row: CaseORM) -> Case:
    """Convert a CaseORM row (with its investigators relationship
    already loaded) into a schema.case.Case dataclass.
    """
    return Case(
        id=row.id,
        title=row.title,
        agency_id=row.agency_id,
        status=CaseStatus(row.status),
        created_by_user_id=row.created_by_user_id,
        opened_at=row.opened_at,
        assigned_investigator_ids=[u.id for u in row.investigators],
    )


def _document_to_domain(row: SourceDocumentORM) -> SourceDocument:
    """Convert a SourceDocumentORM row into a schema.entities.SourceDocument."""
    return SourceDocument(
        id=row.id,
        document_type=row.document_type,
        raw_text=row.raw_text,
        case_id=row.case_id,
    )


def create_agency(db: Session, agency: Agency) -> Agency:
    """Insert a new agency and return it as a domain dataclass."""
    row = AgencyORM(
        id=agency.id,
        name=agency.name,
        agency_type=agency.agency_type,
        parent_agency_id=agency.parent_agency_id,
        is_active="true" if agency.is_active else "false",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _agency_to_domain(row)


def get_agency(db: Session, agency_id: str) -> Optional[Agency]:
    """Look up an agency by ID, or None."""
    row = db.get(AgencyORM, agency_id)
    return _agency_to_domain(row) if row else None


def create_user(db: Session, user: User) -> User:
    """Insert a new user and return it as a domain dataclass. Expects
    user.password_hash to already be set (see schema.user.hash_password) —
    this function does not hash it.
    """
    row = UserORM(
        id=user.id,
        name=user.name,
        badge_id=user.badge_id,
        agency_id=user.agency_id,
        role=user.role.value,
        password_hash=user.password_hash,
        last_login=user.last_login,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _user_to_domain(row)


def get_user_by_badge_id(db: Session, badge_id: str) -> Optional[User]:
    """Look up a user by badge_id, or None. Used by api/auth.py on
    every login and every authenticated request.
    """
    row = db.query(UserORM).filter(UserORM.badge_id == badge_id).one_or_none()
    return _user_to_domain(row) if row else None


def update_last_login(db: Session, badge_id: str, timestamp: str) -> None:
    """Stamp a user's last_login time after a successful login. No-op
    if the badge_id doesn't exist (shouldn't happen in practice, since
    the caller just authenticated against this same badge_id).
    """
    row = db.query(UserORM).filter(UserORM.badge_id == badge_id).one_or_none()
    if row is not None:
        row.last_login = timestamp
        db.commit()


def create_case(db: Session, case: Case) -> Case:
    """Insert a new case and return it as a domain dataclass. Does not
    assign any investigators — call assign_investigator separately.
    """
    row = CaseORM(
        id=case.id,
        title=case.title,
        agency_id=case.agency_id,
        status=case.status.value,
        created_by_user_id=case.created_by_user_id,
        opened_at=case.opened_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _case_to_domain(row)


def get_case(db: Session, case_id: str) -> Optional[Case]:
    """Look up a case by ID, or None."""
    row = db.get(CaseORM, case_id)
    return _case_to_domain(row) if row else None


def get_cases_for_user(db: Session, user: User) -> list[Case]:
    """Return every case this user is authorized to see, scoped by
    role — the DB-backed equivalent of schema.user.get_user_cases:

    - SUPER_ADMIN: every case, across every agency.
    - ANALYST / ADMIN: every case belonging to their own agency.
    - INVESTIGATOR: only cases they're explicitly assigned to.
    """
    if user.role in (Role.SUPER_ADMIN,):
        rows = db.query(CaseORM).all()
    elif user.role in (Role.ANALYST, Role.ADMIN):
        rows = db.query(CaseORM).filter(CaseORM.agency_id == user.agency_id).all()
    else:
        user_row = db.get(UserORM, user.id)
        rows = user_row.assigned_cases if user_row else []
    return [_case_to_domain(row) for row in rows]


def assign_investigator(db: Session, case_id: str, user_id: str) -> Optional[Case]:
    """Add a user to a case's assigned investigators (idempotent).
    Returns the updated Case, or None if either the case or the user
    doesn't exist.
    """
    case_row = db.get(CaseORM, case_id)
    user_row = db.get(UserORM, user_id)
    if case_row is None or user_row is None:
        return None
    if user_row not in case_row.investigators:
        case_row.investigators.append(user_row)
    db.commit()
    db.refresh(case_row)
    return _case_to_domain(case_row)


def create_document(db: Session, document: SourceDocument) -> SourceDocument:
    """Insert a newly-ingested source document and return it as a
    domain dataclass.
    """
    row = SourceDocumentORM(
        id=document.id,
        document_type=document.document_type,
        raw_text=document.raw_text,
        case_id=document.case_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _document_to_domain(row)


def get_document(db: Session, document_id: str) -> Optional[SourceDocument]:
    """Look up a source document by ID, or None. Used by
    api/routes/ingestion.py to reject duplicate ingestion of the same
    document ID.
    """
    row = db.get(SourceDocumentORM, document_id)
    return _document_to_domain(row) if row else None
