"""
schema/entities.py

Entity and relationship type definitions for the criminal network graph.
This is the foundational schema — every downstream module (nlp/, graph/)
depends on these shapes staying stable, so changes here should be
deliberate and reflected in the project notes' Changelog.

Status: [IN PROGRESS]

Design note: this is separate from schema/user.py (system login/roles).
Never mix the two — a Person here is a suspect/case entity, not a
software user. See project notes Section 13 for why that separation
matters (data-integrity + privacy).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EntityType(str, Enum):
    PERSON = "person"
    LOCATION = "location"
    VEHICLE = "vehicle"
    PHONE = "phone"
    ORGANIZATION = "organization"
    EVENT = "event"


class RelationshipType(str, Enum):
    CALLS = "calls"                    # Person -> Phone
    PRESENT_AT = "present_at"          # Person -> Location
    OWNS = "owns"                      # Person -> Vehicle
    ASSOCIATED_WITH = "associated_with"  # Event -> Organization
    PARTICIPATES_IN = "participates_in"  # Person -> Event


@dataclass
class Entity:
    """Base entity extracted from a source document."""
    id: str
    entity_type: EntityType
    raw_text: str                      # exact string as it appeared in the source
    normalized_text: Optional[str] = None  # set by nlp.extraction.normalize_entity
    confidence: Optional[float] = None     # set by nlp.extraction.confidence_score
    source_document_id: Optional[str] = None  # traceability for explainability layer
    aliases: list = field(default_factory=list)  # populated during resolution merges


@dataclass
class Relationship:
    """Edge between two entities, always traceable to a source event/document."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    source_document_id: Optional[str] = None
    weight: float = 1.0                # for centrality/analytics weighting


@dataclass
class SourceDocument:
    """A raw FIR / CDR / financial record / surveillance report, etc.
    Every entity and relationship must be traceable back to one of these
    — this is what makes the explainability layer (graph/explainability.py)
    possible.
    """
    id: str
    document_type: str  # "fir" | "cdr" | "financial" | "surveillance" | "social" | "criminal_history" | "intel"
    raw_text: str
    case_id: Optional[str] = None
