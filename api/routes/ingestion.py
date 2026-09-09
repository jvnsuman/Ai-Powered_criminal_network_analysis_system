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

Known gap: extracted entities are counted and returned, but not yet
persisted (no EntityORM rows are written here) — that's the next
integration step once there's a case-scoped need to query them back.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import nlp.extraction as extraction
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

    return {
        "document_id": document.id,
        "case_id": document.case_id,
        "status": "extracted",
        "entity_count": len(entities),
    }
