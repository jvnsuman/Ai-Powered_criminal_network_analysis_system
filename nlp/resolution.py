"""
nlp/resolution.py

Stage 3: entity resolution / deduplication. Thin, single-signal fuzzy
matching only (RapidFuzz) — multi-signal scoring is December scope
(nlp/confidence.py), not added here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

try:
    from rapidfuzz import fuzz
except ImportError as exc:
    raise ImportError(
        "rapidfuzz is required for nlp/resolution.py. Install with:\n"
        "    pip install rapidfuzz --break-system-packages"
    ) from exc

from nlp.extraction import ExtractedEntity, EntityType

# PHONE/VEHICLE never use fuzzy matching: two numbers one digit apart
# score ~90% similarity under token_sort_ratio, which would silently
# merge different people's records. Exact match only.
_EXACT_MATCH_TYPES = frozenset({EntityType.PHONE, EntityType.VEHICLE})

# Not tuned against labelled data. Raising this to catch aliases like
# "Raju S." also catches unrelated people sharing a surname at a HIGHER
# score than the genuine alias pair. Left conservative on purpose;
# closing that gap is nlp/confidence.py's job.
DEFAULT_SIMILARITY_THRESHOLD = 82.0


@dataclass
class ResolvedEntity:
    """One canonical entity merged from one or more ExtractedEntity mentions."""

    id: str
    entity_type: EntityType
    canonical_text: str
    mention_ids: list = field(default_factory=list)
    source_doc_ids: set = field(default_factory=set)
    # True for a cross-document LOCATION/ORGANIZATION merge with no
    # corroborating PERSON/PHONE/VEHICLE shared between the same
    # documents — guards against coincidental string matches (e.g.
    # data/generate_synthetic.py's bounded vocabulary can produce the
    # same place name in two unrelated documents).
    is_low_confidence_cross_merge: bool = False


def compute_similarity(entity_a: ExtractedEntity, entity_b: ExtractedEntity) -> float:
    """Similarity in [0, 100] between two same-type entities.
    PHONE/VEHICLE: exact match only. Others: RapidFuzz token_sort_ratio.
    """
    if entity_a.normalized_text is None or entity_b.normalized_text is None:
        raise ValueError(
            "compute_similarity requires normalized_text on both entities."
        )

    if entity_a.entity_type != entity_b.entity_type:
        return 0.0

    if entity_a.entity_type in _EXACT_MATCH_TYPES:
        return 100.0 if entity_a.normalized_text == entity_b.normalized_text else 0.0

    return fuzz.token_sort_ratio(entity_a.normalized_text, entity_b.normalized_text)


def resolve_match(entity_a: ExtractedEntity, entity_b: ExtractedEntity,
                   threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> bool:
    """True if two entities should be merged as the same real-world entity."""
    return compute_similarity(entity_a, entity_b) >= threshold


def merge_entities(entities: list) -> ResolvedEntity:
    """Combine matched ExtractedEntity mentions into one ResolvedEntity.

    canonical_text is the highest-confidence mention's normalized_text —
    a placeholder, not a validated "best form" strategy (e.g. it doesn't
    prefer "Raju Kumar" over "Raju S." on its own merits). [TODO]
    """
    if not entities:
        raise ValueError("merge_entities requires at least one entity")

    entity_types = {e.entity_type for e in entities}
    if len(entity_types) > 1:
        raise ValueError(
            f"merge_entities requires all entities to share one "
            f"entity_type, got: {sorted(t.value for t in entity_types)}"
        )

    best = max(entities, key=lambda e: e.confidence)

    return ResolvedEntity(
        id=f"resolved-{uuid.uuid4().hex[:12]}",
        entity_type=best.entity_type,
        canonical_text=best.normalized_text or best.text,
        mention_ids=[e.id for e in entities],
        source_doc_ids={e.source_doc_id for e in entities},
    )


def resolve_entities(entities: list,
                      threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> list:
    """Resolve entities across an entire document batch (cross-document,
    not per-document — that's the actual point of network analysis).

    Greedy O(n^2) pairwise clustering within each entity_type group; not
    transitively consistent (A~B, B~C but not A~C still merges all
    three). Acceptable for Sep's thin scope; a real false-merge risk on
    messier data. Also flags low-confidence cross-merges — see
    ResolvedEntity.is_low_confidence_cross_merge.
    """
    by_type: dict = {}
    for entity in entities:
        by_type.setdefault(entity.entity_type, []).append(entity)

    resolved: list = []

    for type_group in by_type.values():
        assigned = [False] * len(type_group)

        for i, entity_a in enumerate(type_group):
            if assigned[i]:
                continue

            cluster = [entity_a]
            assigned[i] = True

            for j in range(i + 1, len(type_group)):
                if assigned[j]:
                    continue
                entity_b = type_group[j]
                if resolve_match(entity_a, entity_b, threshold):
                    cluster.append(entity_b)
                    assigned[j] = True

            resolved.append(merge_entities(cluster))

    _flag_uncorroborated_cross_merges(resolved)

    return resolved


def _flag_uncorroborated_cross_merges(resolved: list) -> None:
    """Sets is_low_confidence_cross_merge on cross-document LOCATION/
    ORGANIZATION entities with no PERSON/PHONE/VEHICLE shared between
    the same document pair. Mutates resolved in place.
    """
    corroborating_types = {EntityType.PERSON, EntityType.PHONE, EntityType.VEHICLE}

    corroborated_doc_pairs: set = set()
    for entity in resolved:
        if entity.entity_type not in corroborating_types:
            continue
        docs = sorted(entity.source_doc_ids)
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                corroborated_doc_pairs.add((docs[i], docs[j]))

    for entity in resolved:
        if entity.entity_type not in (EntityType.LOCATION, EntityType.ORGANIZATION):
            continue
        if len(entity.source_doc_ids) < 2:
            continue

        docs = sorted(entity.source_doc_ids)
        pairs = [(docs[i], docs[j])
                 for i in range(len(docs)) for j in range(i + 1, len(docs))]

        if not any(pair in corroborated_doc_pairs for pair in pairs):
            entity.is_low_confidence_cross_merge = True


def build_mention_to_resolved_map(resolved: list) -> dict:
    """Maps each raw ExtractedEntity.id to its ResolvedEntity.id.

    Needed because ClassifiedRelation references raw mention IDs, not
    resolved ones — without this, graph/build.py would create duplicate
    nodes for the same real-world entity instead of merging them.
    """
    mapping: dict = {}
    for entity in resolved:
        for mention_id in entity.mention_ids:
            mapping[mention_id] = entity.id
    return mapping


if __name__ == "__main__":
    from nlp.extraction import load_synthetic_fir, extract_entities

    doc_a = load_synthetic_fir(
        "Complainant stated that Raju Kumar was seen near MG Road, "
        "contacted from phone number 987-654-3210.",
        doc_id="fir-001",
    )
    doc_b = load_synthetic_fir(
        "A call from Raju S. was traced to number 987-654-3210 near "
        "the same location.",
        doc_id="cdr-002",
    )
    doc_c = load_synthetic_fir(
        "Unrelated witness Priya Sharma reported a different vehicle "
        "MH12AB1234 near phone number 812-345-6789.",
        doc_id="fir-003",
    )
    doc_d = load_synthetic_fir(
        "A separate, unconnected complaint by Deepa Nair mentioned "
        "activity near MG Road with vehicle KA09XZ4455.",
        doc_id="fir-004",
    )

    all_entities = []
    for doc in (doc_a, doc_b, doc_c, doc_d):
        all_entities.extend(extract_entities(doc.raw_text, doc.doc_id))

    print("--- All extracted entities ---")
    for e in all_entities:
        print(f"  [{e.source_doc_id}] {e.entity_type.value:12} {e.text!r}")

    print("\n--- Resolved (cross-document) ---")
    resolved = resolve_entities(all_entities)
    for r in resolved:
        flag = " [LOW-CONFIDENCE CROSS-MERGE]" if r.is_low_confidence_cross_merge else ""
        print(f"  {r.entity_type.value:12} {r.canonical_text!r:20} "
              f"docs={sorted(r.source_doc_ids)} mentions={len(r.mention_ids)}{flag}")
