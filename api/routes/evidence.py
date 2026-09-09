"""
api/routes/evidence.py

Serves evidence-trail data to the dashboard's EvidencePanel component
— the source documents backing a given entity, for explainability.

graph.explainability.get_evidence_trail is now implemented (an
in-memory reference store — see graph/explainability.py), so this
endpoint returns real (possibly empty) results rather than always 501.
Empty is the expected/common case for now, since nothing in the
pipeline calls link_evidence automatically yet.
"""

from fastapi import APIRouter, Depends

import graph.explainability as explainability
from api.auth import get_current_user
from schema.user import User

router = APIRouter()


@router.get("/{entity_id}")
def evidence_endpoint(entity_id: str, user: User = Depends(get_current_user)) -> dict:
    """Return the evidence trail (source documents) for a flagged
    entity. Requires login; does not yet check case-level authorization
    since there's no entity->case lookup to check against — add the
    same scoping query_endpoint uses once that link exists.
    """
    trail = explainability.get_evidence_trail(entity_id)
    return {
        "entity_id": entity_id,
        "evidence": [doc.to_dict() for doc in trail],
    }
