"""
schema/entities.py

Entity and relationship type definitions for the criminal network
graph — the shapes that nlp/ extracts and graph/ links together. This
is the foundational schema; every downstream module depends on these
staying stable.

Kept separate from schema/user.py (system login/roles): a Person here
is a suspect/case entity extracted from evidence, never a software
user. See schema/user.py's module docstring for why that separation
matters.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EntityType(str, Enum):
    """The kinds of real-world things that can be extracted as nodes."""

    PERSON = "person"
    LOCATION = "location"
    VEHICLE = "vehicle"
    PHONE = "phone"
    ORGANIZATION = "organization"
    EVENT = "event"


class RelationshipType(str, Enum):
    """The kinds of edges that can connect two entities. Each has a
    fixed, directional (source_type, target_type) pair — see
    ALLOWED_RELATIONSHIP_ENDPOINTS below.
    """

    CALLS = "calls"                       # Person -> Phone
    PRESENT_AT = "present_at"             # Person -> Location
    OWNS = "owns"                         # Person -> Vehicle
    ASSOCIATED_WITH = "associated_with"   # Event -> Organization
    PARTICIPATES_IN = "participates_in"   # Person -> Event


# Which (source, target) EntityType pairs are valid for each
# RelationshipType. Directional: order matters (CALLS is Person ->
# Phone, not Phone -> Person). Used by is_valid_relationship() below
# so this rule is enforced once, not re-implemented at every call site.
ALLOWED_RELATIONSHIP_ENDPOINTS: dict[RelationshipType, tuple[EntityType, EntityType]] = {
    RelationshipType.CALLS: (EntityType.PERSON, EntityType.PHONE),
    RelationshipType.PRESENT_AT: (EntityType.PERSON, EntityType.LOCATION),
    RelationshipType.OWNS: (EntityType.PERSON, EntityType.VEHICLE),
    RelationshipType.ASSOCIATED_WITH: (EntityType.EVENT, EntityType.ORGANIZATION),
    RelationshipType.PARTICIPATES_IN: (EntityType.PERSON, EntityType.EVENT),
}

# Recognized SourceDocument.document_type values.
VALID_DOCUMENT_TYPES = frozenset({
    "fir", "cdr", "financial", "surveillance", "social", "criminal_history", "intel",
})


def is_valid_relationship(
    source_type: EntityType, target_type: EntityType, relationship_type: RelationshipType
) -> bool:
    """Check whether relationship_type is allowed between an entity of
    source_type and one of target_type, per
    ALLOWED_RELATIONSHIP_ENDPOINTS. Callers building edges from
    resolved Entity objects (e.g. graph/build.py) should check this
    before wiring one up.
    """
    expected = ALLOWED_RELATIONSHIP_ENDPOINTS.get(relationship_type)
    return expected is not None and expected == (source_type, target_type)


@dataclass
class Entity:
    """A single extracted entity — a node in the graph."""

    id: str
    entity_type: EntityType
    raw_text: str                             # exact string as it appeared in the source
    normalized_text: Optional[str] = None     # set once nlp.extraction normalizes it
    confidence: Optional[float] = None        # set once nlp.extraction scores it
    source_document_id: Optional[str] = None  # traceability for the explainability layer
    aliases: list = field(default_factory=list)  # populated during resolution merges

    def __post_init__(self):
        """Validate on construction so invalid entities can't exist,
        rather than failing later somewhere downstream.
        """
        if not self.id:
            raise ValueError("Entity.id must be non-empty")
        if not self.raw_text or not self.raw_text.strip():
            raise ValueError("Entity.raw_text must be non-empty")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Entity.confidence must be within 0.0-1.0, got {self.confidence}")

    def to_dict(self) -> dict:
        """Serialize to a plain dict (e.g. for an API JSON response)."""
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "confidence": self.confidence,
            "source_document_id": self.source_document_id,
            "aliases": list(self.aliases),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Build and validate an Entity from a plain dict (e.g. an
        incoming API request body). Raises ValueError with a clear
        message on any missing/invalid field — callers can surface
        that directly as a 400 response.
        """
        try:
            entity_type = EntityType(data["entity_type"])
        except ValueError:
            raise ValueError(f"Unknown entity_type: {data.get('entity_type')!r}")
        except KeyError:
            raise ValueError("Entity dict missing required key 'entity_type'")
        try:
            return cls(
                id=data["id"],
                entity_type=entity_type,
                raw_text=data["raw_text"],
                normalized_text=data.get("normalized_text"),
                confidence=data.get("confidence"),
                source_document_id=data.get("source_document_id"),
                aliases=list(data.get("aliases", [])),
            )
        except KeyError as exc:
            raise ValueError(f"Entity dict missing required key: {exc}")


@dataclass
class Relationship:
    """An edge between two entities, always traceable to a source
    document/event.
    """

    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    source_document_id: Optional[str] = None
    weight: float = 1.0  # feeds graph/analytics.py's centrality calculations

    def __post_init__(self):
        """Validate on construction: non-empty endpoints, no self-loops
        (an entity can't relate to itself), and a positive weight
        (zero/negative would silently corrupt centrality analytics).
        """
        if not self.id:
            raise ValueError("Relationship.id must be non-empty")
        if not self.source_entity_id or not self.target_entity_id:
            raise ValueError("Relationship requires both source_entity_id and target_entity_id")
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("Relationship cannot connect an entity to itself")
        if self.weight <= 0:
            raise ValueError(f"Relationship.weight must be positive, got {self.weight}")

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "id": self.id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type": self.relationship_type.value,
            "source_document_id": self.source_document_id,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        """Build and validate a Relationship from a plain dict."""
        try:
            relationship_type = RelationshipType(data["relationship_type"])
        except ValueError:
            raise ValueError(f"Unknown relationship_type: {data.get('relationship_type')!r}")
        except KeyError:
            raise ValueError("Relationship dict missing required key 'relationship_type'")
        try:
            return cls(
                id=data["id"],
                source_entity_id=data["source_entity_id"],
                target_entity_id=data["target_entity_id"],
                relationship_type=relationship_type,
                source_document_id=data.get("source_document_id"),
                weight=data.get("weight", 1.0),
            )
        except KeyError as exc:
            raise ValueError(f"Relationship dict missing required key: {exc}")


@dataclass
class SourceDocument:
    """A raw FIR / CDR / financial record / surveillance report, etc.
    Every Entity and Relationship should be traceable back to one of
    these — this is what makes the evidence-trail / explainability
    layer (graph/explainability.py) possible.
    """

    id: str
    document_type: str  # one of VALID_DOCUMENT_TYPES
    raw_text: str
    case_id: Optional[str] = None
    created_at: Optional[str] = None  # server-assigned at persistence time (db.models.SourceDocumentORM's default) — not required on input

    def __post_init__(self):
        """Validate on construction."""
        if not self.id:
            raise ValueError("SourceDocument.id must be non-empty")
        if self.document_type not in VALID_DOCUMENT_TYPES:
            raise ValueError(
                f"Unknown document_type {self.document_type!r}; "
                f"must be one of {sorted(VALID_DOCUMENT_TYPES)}"
            )
        if not self.raw_text or not self.raw_text.strip():
            raise ValueError("SourceDocument.raw_text must be non-empty")

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return {
            "id": self.id,
            "document_type": self.document_type,
            "raw_text": self.raw_text,
            "case_id": self.case_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SourceDocument":
        """Build and validate a SourceDocument from a plain dict. This
        is the shape check api/routes/ingestion.py relies on before
        accepting an uploaded document. created_at is normally left
        unset here (the caller is submitting a new document) and
        assigned server-side at persistence time — accepted as an
        optional passthrough only for round-tripping already-stored data.
        """
        try:
            return cls(
                id=data["id"],
                document_type=data["document_type"],
                raw_text=data["raw_text"],
                case_id=data.get("case_id"),
                created_at=data.get("created_at"),
            )
        except KeyError as exc:
            raise ValueError(f"SourceDocument dict missing required key: {exc}")
