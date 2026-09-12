"""
db/repository.py

The persistence adapter: converts between db.models' ORM rows and the
plain domain dataclasses (schema.user.Agency/User, schema.case.Case).
Callers (api/auth.py, api/routes/) work entirely in terms of the
dataclasses and never see an ORM object — this is the one place that
translation happens, so the rest of the app doesn't need to know
SQLAlchemy exists.
"""

import json
from typing import Optional

from sqlalchemy.orm import Session

from db.models import AgencyORM, CaseORM, EntityORM, RelationshipORM, ReportORM, SourceDocumentORM, UserORM
from nlp.extraction import EntityType as NlpEntityType
from nlp.extraction import ExtractedEntity
from nlp.relation_classification import ClassifiedRelation
from nlp.relation_classification import RelationType as NlpRelationType
from schema.case import Case, CaseStatus
from schema.entities import SourceDocument
from schema.report import Report
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
        preferences=json.loads(row.preferences) if row.preferences else {},
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
        created_at=row.created_at,
    )


def _report_to_domain(row: ReportORM) -> Report:
    """Convert a ReportORM row into a schema.report.Report."""
    return Report(
        id=row.id,
        case_id=row.case_id,
        title=row.title,
        format=row.format,
        content=row.content,
        created_at=row.created_at,
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
        preferences=json.dumps(user.preferences) if user.preferences else None,
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


def get_document_summary_for_case(db: Session, case_id: str) -> list[dict]:
    """Per-document-type counts and the most recent created_at
    timestamp for every source document ingested under a case — the
    real data behind the Data Sources page's summary table (and the
    Reports page's generated summaries). Grouped in Python rather
    than SQL to stay agnostic of SQLite/PostgreSQL dialect differences.
    """
    rows = db.query(SourceDocumentORM).filter(SourceDocumentORM.case_id == case_id).all()
    summary: dict[str, dict] = {}
    for row in rows:
        entry = summary.setdefault(
            row.document_type, {"document_type": row.document_type, "count": 0, "last_updated": None}
        )
        entry["count"] += 1
        if entry["last_updated"] is None or row.created_at > entry["last_updated"]:
            entry["last_updated"] = row.created_at
    return sorted(summary.values(), key=lambda e: e["document_type"])


def update_user_preferences(db: Session, user_id: str, updates: dict) -> Optional[User]:
    """Merge `updates` into a user's stored preferences (Settings page
    toggles) and return the updated User, or None if user_id doesn't
    exist. A merge rather than a replace, so toggling one preference
    from the frontend never clobbers the others.
    """
    row = db.get(UserORM, user_id)
    if row is None:
        return None
    current = json.loads(row.preferences) if row.preferences else {}
    current.update(updates)
    row.preferences = json.dumps(current)
    db.commit()
    db.refresh(row)
    return _user_to_domain(row)


def _entity_to_domain(row: EntityORM) -> ExtractedEntity:
    """Convert an EntityORM row back into an
    nlp.extraction.ExtractedEntity, the shape nlp.resolution.resolve_entities
    and graph.build.build_graph expect as input.

    start_char/end_char aren't persisted (EntityORM has no columns for
    them — they're only useful for highlighting a span in the original
    document text, not for resolution/graph-building), so they're
    reconstructed as 0. Nothing downstream of extraction reads them.
    """
    return ExtractedEntity(
        id=row.id,
        text=row.raw_text,
        entity_type=NlpEntityType(row.entity_type),
        source_doc_id=row.source_document_id,
        start_char=0,
        end_char=0,
        confidence=row.confidence or 0.0,
        normalized_text=row.normalized_text,
    )


def _relationship_to_domain(row: RelationshipORM) -> ClassifiedRelation:
    """Convert a RelationshipORM row back into a
    nlp.relation_classification.ClassifiedRelation, the shape
    graph.build.build_graph expects for its `relations` argument.
    """
    return ClassifiedRelation(
        id=row.id,
        entity_a_id=row.source_entity_id,
        entity_b_id=row.target_entity_id,
        relation_type=NlpRelationType(row.relationship_type),
        confidence=row.weight,
        source_doc_id=row.source_document_id,
    )


def create_entities(db: Session, entities: list[ExtractedEntity]) -> None:
    """Persist a batch of extracted entities (raw per-mention rows,
    not yet resolved/deduplicated — resolution happens at query time
    via nlp.resolution.resolve_entities, so raw mentions are what's
    stored here). No-op on an empty list.

    Called from api/routes/ingestion.py right after
    nlp.extraction.extract_entities succeeds for a document.
    """
    if not entities:
        return
    for entity in entities:
        db.add(EntityORM(
            id=entity.id,
            entity_type=entity.entity_type.value,
            raw_text=entity.text,
            normalized_text=entity.normalized_text,
            confidence=entity.confidence,
            source_document_id=entity.source_doc_id,
        ))
    db.commit()


def get_entities_for_case(db: Session, case_id: str) -> list[ExtractedEntity]:
    """Every extracted entity mention across every document ingested
    under a case — the input api/routes/query.py hands to
    nlp.resolution.resolve_entities to build that case's graph.
    """
    rows = (
        db.query(EntityORM)
        .join(SourceDocumentORM, EntityORM.source_document_id == SourceDocumentORM.id)
        .filter(SourceDocumentORM.case_id == case_id)
        .all()
    )
    return [_entity_to_domain(row) for row in rows]


def create_relationships(db: Session, relations: list[ClassifiedRelation]) -> None:
    """Persist a batch of classified relations. No-op on an empty
    list (e.g. when nlp.relation_classification's heavy dependencies
    aren't installed — see api/routes/ingestion.py's degrade-gracefully
    handling, same pattern as extraction's spaCy-missing case).
    """
    if not relations:
        return
    for relation in relations:
        db.add(RelationshipORM(
            id=relation.id,
            source_entity_id=relation.entity_a_id,
            target_entity_id=relation.entity_b_id,
            relationship_type=relation.relation_type.value,
            source_document_id=relation.source_doc_id,
            weight=relation.confidence,
        ))
    db.commit()


def get_relationships_for_case(db: Session, case_id: str) -> list[ClassifiedRelation]:
    """Every classified relation from every document ingested under a
    case — the input api/routes/query.py hands to graph.build.build_graph
    alongside that case's resolved entities.
    """
    rows = (
        db.query(RelationshipORM)
        .join(SourceDocumentORM, RelationshipORM.source_document_id == SourceDocumentORM.id)
        .filter(SourceDocumentORM.case_id == case_id)
        .all()
    )
    return [_relationship_to_domain(row) for row in rows]


def create_report(db: Session, report: Report) -> Report:
    """Insert a newly-generated report and return it as a domain
    dataclass (with created_at populated from the DB default).
    """
    row = ReportORM(
        id=report.id,
        case_id=report.case_id,
        title=report.title,
        format=report.format,
        content=report.content,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _report_to_domain(row)


def list_reports_for_case(db: Session, case_id: str) -> list[Report]:
    """List every report generated for a case, most recent first."""
    rows = db.query(ReportORM).filter(ReportORM.case_id == case_id).order_by(ReportORM.created_at.desc()).all()
    return [_report_to_domain(row) for row in rows]


def get_report(db: Session, report_id: str) -> Optional[Report]:
    """Look up a report by ID, or None."""
    row = db.get(ReportORM, report_id)
    return _report_to_domain(row) if row else None
