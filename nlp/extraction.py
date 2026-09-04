"""
nlp/extraction.py

NLP entity extraction pipeline — pulls typed entities (Person, Location,
Phone, Vehicle, Organization) out of raw, unstructured FIR-style text.

This is P0 — the first thing that must work, since resolution and graph
construction both depend on its output.

Status: [TODO]
"""

from schema.entities import Entity, EntityType


def load_synthetic_fir(text: str) -> str:
    """[TODO] Ingest raw FIR-style text (from data/) and return cleaned
    input ready for NER. Handles basic whitespace/encoding normalization
    only — does not do entity-level cleanup (see normalize_entity).
    """
    raise NotImplementedError


def extract_entities(text: str) -> list[Entity]:
    """[TODO] Run NER over the input text and return a list of typed
    Entity objects (schema.entities.Entity). Initial version: spaCy or
    HuggingFace Transformers pipeline. Indian name/script handling
    (IndicNER) is a stretch goal — verify model license before bundling
    (see THIRD_PARTY_NOTICES.md).
    """
    raise NotImplementedError


def normalize_entity(entity: Entity) -> Entity:
    """[TODO] Clean casing/punctuation/whitespace on an extracted entity
    before it goes into resolution. Sets entity.normalized_text.
    """
    raise NotImplementedError


def confidence_score(entity: Entity) -> float:
    """[TODO] Attach an extraction confidence score to an entity. Low-
    confidence extractions should be flagged for manual review rather
    than silently trusted — this is what lets the team honestly answer
    Judge Q&A Q3 ("show me one entity your system failed to extract").
    """
    raise NotImplementedError
