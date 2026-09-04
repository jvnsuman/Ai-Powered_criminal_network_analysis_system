"""
graph/explainability.py

Evidence-trail layer — makes every flagged node/edge traceable back to
the source document(s) that justify it. This is what turns a "risk
score" into something court-usable (per Judge Q&A Q2's "strong answer":
this is decision support, not decision-making — the investigator makes
the final call, with the evidence in front of them).

Status: [TODO] — 0% as of Sep slice, this is Dec P1 scope.
"""

from schema.entities import SourceDocument


def link_evidence(node_or_edge_id: str, source_document: SourceDocument) -> None:
    """[TODO] Record that a graph node or edge is backed by a specific
    source document. Should be called at extraction/resolution/graph-
    build time, not bolted on after — every entity and relationship
    already carries a source_document_id (schema/entities.py), this
    function is what turns that raw reference into a queryable trail.
    """
    raise NotImplementedError


def get_evidence_trail(entity_id: str) -> list[SourceDocument]:
    """[TODO] Retrieve all supporting documents for a flagged entity or
    pattern. This is what powers the dashboard's evidence panel
    (project notes Section 12) — clicking a node shows this output.
    """
    raise NotImplementedError
