"""
api/routes/query.py

Retrieve a case's graph for the dashboard.

Authorization/case-scoping (via db.repository.get_cases_for_user) is
fully enforced here. Entities/relationships are now persisted by
api/routes/ingestion.py, so this route builds a real graph: pull every
raw entity mention and classified relation ingested under this case,
resolve mentions into canonical entities (nlp.resolution), then hand
both to graph.build.build_graph. Resolution runs at query time rather
than at ingestion time on purpose — it needs the full cross-document
mention set for a case to do cross-document merging correctly (see
nlp.resolution.resolve_entities's own docstring), and re-running it
per query keeps ingestion simple (append-only) with no invalidation
logic needed when a new document changes an existing case's picture.

Response shape matches dashboard/src/sampleData.js's SAMPLE_GRAPH
(caseId/nodes/edges/stats) so GraphCanvas and friends consume real and
sample data identically — no branching needed on the frontend.

Still honestly reports 501 (not a fabricated empty graph) when a case
has no persisted entities yet — same "authorized, but nothing to show"
distinction as before, now genuinely scoped to *this* case's data
rather than always being true.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import graph.build as graph_build
from api.auth import get_current_user
from db import repository as repo
from db.connection import get_db
from nlp.resolution import resolve_entities
from schema.user import User

router = APIRouter()


@router.get("/{case_id}")
def query_endpoint(case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Return the graph for a case. Checks the user is authorized to
    view this case (403 if not), then builds it from persisted
    entities/relationships, or reports 501 if none exist yet.
    """
    authorized_case_ids = {c.id for c in repo.get_cases_for_user(db, user)}
    if case_id not in authorized_case_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this case",
        )

    mentions = repo.get_entities_for_case(db, case_id)
    if not mentions:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Authorized, but this case has no persisted entities/relationships "
                "to build a graph from yet (ingest a document first via api/routes/ingestion.py)."
            ),
        )

    resolved_entities = resolve_entities(mentions)
    relations = repo.get_relationships_for_case(db, case_id)
    graph = graph_build.build_graph(resolved_entities, relations)

    nodes = [
        {
            "id": node_id,
            "label": attrs["canonical_text"],
            "entity_type": attrs["entity_type"].lower(),
        }
        for node_id, attrs in graph.nodes(data=True)
    ]
    edges = [
        {
            "id": f"{source}-{target}-{key}",
            "source": source,
            "target": target,
            "relationship_type": attrs["relation_type"].replace("-", "_"),
            "weight": attrs.get("confidence", 1.0),
        }
        for source, target, key, attrs in graph.edges(keys=True, data=True)
    ]

    influencer = graph_build.highlight_influencer(graph)

    return {
        "caseId": case_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "entitiesLinked": graph.number_of_nodes(),
            "keyInfluencers": 1 if influencer else 0,
            "flaggedPatterns": 0,  # real anomaly counts are served by api/routes/alerts.py
        },
        "influencer": influencer,
    }
