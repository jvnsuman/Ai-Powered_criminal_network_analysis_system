"""
tests/test_schema_entities.py

Unit tests for schema/entities.py: construction validation, dict
(de)serialization round-trips, and the allowed relationship-endpoint
rules (which EntityType pairs a given RelationshipType may connect).
"""

import pytest

from schema.entities import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
    SourceDocument,
    is_valid_relationship,
)


def test_entity_round_trip_dict():
    e = Entity(id="E1", entity_type=EntityType.PERSON, raw_text="Raju", confidence=0.9)
    assert Entity.from_dict(e.to_dict()) == e


def test_entity_rejects_empty_id():
    with pytest.raises(ValueError):
        Entity(id="", entity_type=EntityType.PERSON, raw_text="x")


def test_entity_rejects_blank_raw_text():
    with pytest.raises(ValueError):
        Entity(id="E1", entity_type=EntityType.PERSON, raw_text="   ")


def test_entity_rejects_out_of_range_confidence():
    with pytest.raises(ValueError):
        Entity(id="E1", entity_type=EntityType.PERSON, raw_text="x", confidence=1.5)


def test_entity_from_dict_rejects_unknown_type():
    with pytest.raises(ValueError):
        Entity.from_dict({"id": "E1", "entity_type": "unicorn", "raw_text": "x"})


def test_relationship_round_trip_dict():
    r = Relationship(id="R1", source_entity_id="E1", target_entity_id="E2", relationship_type=RelationshipType.CALLS)
    assert Relationship.from_dict(r.to_dict()) == r


def test_relationship_rejects_self_loop():
    with pytest.raises(ValueError):
        Relationship(id="R1", source_entity_id="E1", target_entity_id="E1", relationship_type=RelationshipType.CALLS)


def test_relationship_rejects_nonpositive_weight():
    with pytest.raises(ValueError):
        Relationship(id="R1", source_entity_id="E1", target_entity_id="E2", relationship_type=RelationshipType.CALLS, weight=0)


def test_source_document_round_trip_dict():
    d = SourceDocument(id="D1", document_type="fir", raw_text="On 12th March...", case_id="CASE-1")
    assert SourceDocument.from_dict(d.to_dict()) == d


def test_source_document_rejects_unknown_type():
    with pytest.raises(ValueError):
        SourceDocument(id="D1", document_type="tweet", raw_text="x")


@pytest.mark.parametrize(
    "source,target,rel,expected",
    [
        (EntityType.PERSON, EntityType.PHONE, RelationshipType.CALLS, True),
        (EntityType.PHONE, EntityType.PERSON, RelationshipType.CALLS, False),  # direction matters
        (EntityType.PERSON, EntityType.VEHICLE, RelationshipType.OWNS, True),
        (EntityType.EVENT, EntityType.ORGANIZATION, RelationshipType.ASSOCIATED_WITH, True),
    ],
)
def test_is_valid_relationship(source, target, rel, expected):
    assert is_valid_relationship(source, target, rel) is expected
