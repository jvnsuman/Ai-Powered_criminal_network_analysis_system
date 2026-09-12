"""
api/routes/ingestion.py

Accepts multi-source case data (FIRs, CDRs, financial records, etc.)
via the API and hands it to nlp.extraction for entity extraction.

nlp.extraction is now a real, working spaCy-based pipeline (see
nlp/extraction.py) — this endpoint runs it for real, rather than
reporting a permanent "not implemented" state. It still degrades
gracefully (202, not 500) if the spaCy model isn't installed/downloaded
in the current environment, since document storage itself still
succeeded regardless.

Persistence (formerly the "known gap" here): extracted entities are
now written as EntityORM rows via db.repository.create_entities, which
is what unblocks api/routes/query.py and api/routes/alerts.py — both
previously reported an honest empty/501 state purely because there was
nothing persisted to read back. Relation classification
(nlp.relation_classification) is attempted the same way and persisted
via db.repository.create_relationships, but degrades gracefully (same
202-not-500 pattern as spaCy above) since it depends on transformers/
torch, which are heavier, optional installs (see requirements.txt).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import nlp.extraction as extraction
import nlp.relation_classification as relation_classification
from api.auth import get_current_user
from db import repository as repo
from db.connection import get_db
from schema.entities import SourceDocument
from schema.user import User

router = APIRouter()


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def ingest_endpoint(data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Validate a document against schema.entities.SourceDocument's
    shape, persist it, and run entity extraction. Returns 202
    (Accepted) either way: the document itself was successfully
    validated and stored, whether or not extraction actually ran.
    """
    try:
        document = SourceDocument.from_dict(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if repo.get_document(db, document.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A document with id {document.id!r} has already been ingested",
        )
    repo.create_document(db, document)

    try:
        entities = extraction.extract_entities(document.raw_text, document.id)
    except RuntimeError as exc:
        # spaCy (or its model) isn't available in this environment —
        # the document is still successfully stored either way.
        return {
            "document_id": document.id,
            "case_id": document.case_id,
            "status": "stored_pending_extraction",
            "detail": f"Document accepted and stored. Entity extraction unavailable: {exc}",
        }

    repo.create_entities(db, entities)

    relation_count = 0
    relation_detail = None
    if len(entities) >= 2:
        try:
            relations = relation_classification.classify_all_relations(entities, document.raw_text)
            repo.create_relationships(db, relations)
            relation_count = len(relations)
        except RuntimeError as exc:
            # transformers/torch aren't available in this environment —
            # entities are still successfully extracted and persisted
            # either way; relation edges just aren't added yet.
            relation_detail = f"Relation classification unavailable: {exc}"

    response = {
        "document_id": document.id,
        "case_id": document.case_id,
        "status": "extracted",
        "entity_count": len(entities),
        "relation_count": relation_count,
    }
    if relation_detail:
        response["detail"] = relation_detail
    return response


@router.get("/{case_id}/summary")
def document_summary_endpoint(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Per-document-type counts and last-ingested timestamps for a
    case — real data (not fabricated) backing the Data Sources page's
    summary table. Same case-authorization check as api/routes/query.py.
    """
    authorized_case_ids = {c.id for c in repo.get_cases_for_user(db, user)}
    if case_id not in authorized_case_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this case")
    return {"sources": repo.get_document_summary_for_case(db, case_id)}
