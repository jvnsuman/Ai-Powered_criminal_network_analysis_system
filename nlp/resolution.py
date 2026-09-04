"""
nlp/resolution.py

Entity resolution / deduplication — merges "Raju", "Raju S.", and a phone
number appearing across sources into one canonical entity.

This is the hardest problem in the whole system (per project notes
Section 8's 20/80 split) and the thing most competing teams skip.

Build path: ships thin first (fuzzy string match only), then deepens in
place — same functions, same file, more signal. Do not fork a separate
"resolution_v2.py"; extend compute_similarity/resolve_match/merge_entities
and add the multi-signal functions below them as they come online.

Status: [TODO]
"""

from schema.entities import Entity


# --- Core (ship first) ---

def compute_similarity(entity_a: Entity, entity_b: Entity) -> float:
    """[TODO] Fuzzy string similarity between two entities' names/aliases.
    Initial implementation: RapidFuzz. Returns 0.0-1.0.
    """
    raise NotImplementedError


def resolve_match(entity_a: Entity, entity_b: Entity) -> bool:
    """[TODO] Decide whether two entities should merge, based on
    similarity threshold. Thin version: single fuzzy-match score only.
    Deepened version (see cross_reference_signals below) combines
    multiple signals into this decision instead of one score.
    """
    raise NotImplementedError


def merge_entities(entity_a: Entity, entity_b: Entity) -> Entity:
    """[TODO] Combine two entities into one canonical node. Must keep
    both source_document_id references (via aliases/provenance) — never
    merge silently in a way that loses the evidence trail. Every match
    should show its supporting evidence, not just merge (per Judge Q&A
    Q1's "strong answer").
    """
    raise NotImplementedError


# --- Deepened (extend once core is working, same file) ---

def cross_reference_signals(entity_a: Entity, entity_b: Entity) -> dict:
    """[TODO] Multi-signal matching: co-occurrence in the same case file,
    shared location/timestamp proximity, partial identifier overlap.
    Returns a dict of signal_name -> score, consumed by confidence_score
    below instead of resolve_match's single threshold.
    """
    raise NotImplementedError


def confidence_score(match: dict) -> float:
    """[TODO] Multi-signal confidence scoring for a proposed match —
    not just string similarity. Combines cross_reference_signals output
    into a single 0.0-1.0 confidence value.
    """
    raise NotImplementedError


def flag_for_review(match: dict, threshold: float) -> bool:
    """[TODO] Low-confidence merges go to manual review, not silent
    auto-merge. This is the false-merge safeguard referenced in Judge
    Q&A Q1's follow-up question.
    """
    raise NotImplementedError
