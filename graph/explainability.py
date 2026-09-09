"""
graph/explainability.py

Evidence-trail layer — makes every flagged node/edge traceable back to
the source document(s) that justify it. This is what turns a "risk
score" into something court-usable: decision support, not decision-
making — the investigator makes the final call, with the evidence in
front of them.

Distinct from graph.build.get_evidence_trail(graph, node_id), which
reads attributes off one already-built graph object. This module is a
system-wide, ID-keyed index that survives independently of any
specific graph instance — the same entity_id can be looked up here
regardless of which graph build it appeared in.

Status: in-memory reference store implemented (same pattern as
schema/user.py's stores) — nothing in the pipeline calls link_evidence
automatically yet; it needs to be wired into extraction/resolution/
graph-build time to populate on its own rather than requiring a
separate manual call.
"""

from schema.entities import SourceDocument

_EVIDENCE_STORE: dict[str, list[SourceDocument]] = {}


def link_evidence(node_or_edge_id: str, source_document: SourceDocument) -> None:
    """Record that a graph node or edge is backed by a specific source
    document. Idempotent per (id, document.id) pair — linking the same
    document to the same node twice does not duplicate it.
    """
    existing = _EVIDENCE_STORE.setdefault(node_or_edge_id, [])
    if not any(doc.id == source_document.id for doc in existing):
        existing.append(source_document)


def get_evidence_trail(entity_id: str) -> list[SourceDocument]:
    """Retrieve every source document linked to a flagged entity or
    pattern via link_evidence. Returns an empty list (not an error) if
    nothing has been linked yet — powers the dashboard's EvidencePanel
    component via api/routes/evidence.py.
    """
    return list(_EVIDENCE_STORE.get(entity_id, []))
