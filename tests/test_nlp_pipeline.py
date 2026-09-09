"""
tests/test_nlp_pipeline.py

Integration-style tests for the real NLP pipeline (nlp/extraction.py,
nlp/resolution.py, nlp/confidence.py) — these actually run spaCy, not
mocks, since the whole point is verifying the real model behaves as
documented. Requires en_core_web_sm to be downloaded (see
requirements.txt).
"""

import pytest

from nlp.confidence import below_review_threshold, normalize_confidence
from nlp.extraction import EntityType, extract_entities
from nlp.resolution import build_mention_to_resolved_map, resolve_entities


def test_extract_entities_finds_all_types():
    text = "Raju Kumar called from 9876543210 near MG Road, driving MH12AB1234, working for Shakti Traders."
    entities = extract_entities(text, "doc-1")
    found_types = {e.entity_type for e in entities}
    assert EntityType.PERSON in found_types
    assert EntityType.PHONE in found_types
    assert EntityType.LOCATION in found_types
    assert EntityType.VEHICLE in found_types
    assert EntityType.ORGANIZATION in found_types


def test_extract_entities_source_doc_id_is_threaded_through():
    entities = extract_entities("Raju Kumar was seen near MG Road.", "doc-42")
    assert all(e.source_doc_id == "doc-42" for e in entities)


def test_resolve_entities_merges_exact_duplicates_across_documents():
    e1 = extract_entities("Raju Kumar was seen near MG Road.", "doc-1")
    e2 = extract_entities("Raju Kumar was seen near MG Road.", "doc-2")
    resolved = resolve_entities(e1 + e2)

    person_nodes = [r for r in resolved if r.entity_type == EntityType.PERSON]
    assert len(person_nodes) == 1
    assert set(person_nodes[0].source_doc_ids) == {"doc-1", "doc-2"}


def test_build_mention_to_resolved_map_covers_every_mention():
    entities = extract_entities("Raju Kumar was seen near MG Road.", "doc-1")
    resolved = resolve_entities(entities)
    mapping = build_mention_to_resolved_map(resolved)
    assert set(mapping.keys()) == {e.id for e in entities}


@pytest.mark.parametrize(
    "raw,method,expected",
    [
        (1.5, "minmax", 1.0),
        (-0.3, "minmax", 0.0),
        (0.7, "minmax", 0.7),
    ],
)
def test_normalize_confidence_minmax(raw, method, expected):
    assert normalize_confidence(raw, method) == expected


def test_normalize_confidence_sigmoid_bounds():
    assert 0.0 < normalize_confidence(-5.0, "sigmoid") < 0.5
    assert 0.5 < normalize_confidence(5.0, "sigmoid") < 1.0


def test_normalize_confidence_rejects_unknown_method():
    with pytest.raises(ValueError):
        normalize_confidence(0.5, "bogus")


def test_below_review_threshold():
    assert below_review_threshold(0.3, threshold=0.6) is True
    assert below_review_threshold(0.9, threshold=0.6) is False
