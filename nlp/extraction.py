"""
nlp/extraction.py

NLP entity extraction pipeline: load_synthetic_fir, extract_entities,
normalize_entity, confidence_score.

Engines:
    - spaCy (en_core_web_sm): PERSON, LOCATION, ORGANIZATION.
    - Regex: PHONE and VEHICLE.
    - HuggingFace transformers pipeline (optional): secondary NER pass
      for names spaCy's English model misses. Off by default, enabled
      via use_multilingual_pass=True and HF_NER_MODEL env var.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class EntityType(str, Enum):
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    PHONE = "PHONE"
    VEHICLE = "VEHICLE"
    ORGANIZATION = "ORGANIZATION"


@dataclass
class ExtractedEntity:
    id: str
    text: str
    entity_type: EntityType
    source_doc_id: str
    start_char: int
    end_char: int
    confidence: float = 0.0
    normalized_text: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SyntheticFIR:
    doc_id: str
    raw_text: str
    source_path: Optional[str] = None


# ---------------------------------------------------------------------------
# 1. load_synthetic_fir
# ---------------------------------------------------------------------------

def load_synthetic_fir(text: str, doc_id: Optional[str] = None,
                        source_path: Optional[str] = None) -> SyntheticFIR:
    """Ingest raw FIR-style text into a SyntheticFIR record.

    If text is empty and source_path is given, reads from disk instead.

    Raises:
        ValueError: if neither text nor a readable source_path is provided.
    """
    if not text and source_path:
        path = Path(source_path)
        if not path.exists():
            raise ValueError(f"source_path does not exist: {source_path}")
        text = path.read_text(encoding="utf-8")

    if not text or not text.strip():
        raise ValueError(
            "load_synthetic_fir requires non-empty text (directly or via "
            "source_path)."
        )

    resolved_doc_id = doc_id or f"fir-{uuid.uuid4().hex[:12]}"

    return SyntheticFIR(
        doc_id=resolved_doc_id,
        raw_text=text.strip(),
        source_path=source_path,
    )


# ---------------------------------------------------------------------------
# 2. extract_entities
# ---------------------------------------------------------------------------

# Indian mobile numbers, tolerant of space/hyphen separators and an
# optional country code. Capture group isolates the 10-digit number so
# a "+91 " prefix isn't included in the matched span.
_PHONE_PATTERN = re.compile(
    r"(?:\+?91[-\s]?|0)?\b([6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4})\b"
)

_VEHICLE_PATTERN = re.compile(
    r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,2}[-\s]?\d{4}\b"
)

_LOCATION_HINTS = (
    "Road", "Nagar", "Colony", "Chowk", "Marg", "Street", "Lane",
)
_ORG_SUFFIXES = (
    "Ltd", "Pvt", "Traders", "Enterprises", "Trust", "Associates",
)


# ---------------------------------------------------------------------------
# spaCy engine
# ---------------------------------------------------------------------------

_spacy_nlp = None

_INDIAN_NAME_COMPONENTS: Optional[frozenset] = None


def _get_indian_name_components() -> frozenset:
    """Lazily build and cache a gazetteer of Indian first/last-name
    components, sampled from Faker's en_IN provider.
    """
    global _INDIAN_NAME_COMPONENTS
    if _INDIAN_NAME_COMPONENTS is not None:
        return _INDIAN_NAME_COMPONENTS

    try:
        from faker import Faker
    except ImportError as exc:
        raise RuntimeError(
            "faker is required to build the Indian-name correction "
            "gazetteer but is not installed. Run:\n"
            "    pip install faker --break-system-packages"
        ) from exc

    fake = Faker("en_IN")
    components: set = set()
    for _ in range(5000):
        components.add(fake.first_name())
        components.add(fake.last_name())

    _INDIAN_NAME_COMPONENTS = frozenset(components)
    return _INDIAN_NAME_COMPONENTS


def _merge_split_person_names(entities: list, text: str,
                               source_doc_id: str) -> list:
    """Merge two adjacent single-word LOCATION spans back into one
    PERSON entity when both words are Indian name-gazetteer components.
    """
    gazetteer = _get_indian_name_components()
    result: list = []
    i = 0

    while i < len(entities):
        current = entities[i]
        merged = False

        if (i + 1 < len(entities)
                and current.entity_type == EntityType.LOCATION
                and entities[i + 1].entity_type == EntityType.LOCATION):
            nxt = entities[i + 1]
            between = text[current.end_char:nxt.start_char]

            is_single_word = (" " not in current.text.strip()
                               and " " not in nxt.text.strip())
            is_just_a_space = between == " "
            both_are_names = (current.text in gazetteer
                               and nxt.text in gazetteer)

            if is_single_word and is_just_a_space and both_are_names:
                combined_text = f"{current.text} {nxt.text}"
                merged_entity = _make_entity(
                    text=combined_text,
                    entity_type=EntityType.PERSON,
                    source_doc_id=source_doc_id,
                    start=current.start_char,
                    end=nxt.end_char,
                )
                merged_entity.metadata["engine"] = "spacy"
                merged_entity.metadata["raw_label"] = "GPE+GPE_corrected"
                merged_entity.metadata["correction_applied"] = (
                    "merged_split_person_name"
                )
                result.append(merged_entity)
                i += 2
                merged = True

        if not merged:
            result.append(current)
            i += 1

    return result


_SPACY_LABEL_MAP = {
    "PERSON": EntityType.PERSON,
    "GPE": EntityType.LOCATION,
    "LOC": EntityType.LOCATION,
    "FAC": EntityType.LOCATION,
    "ORG": EntityType.ORGANIZATION,
}


def _merge_split_location_prefix(entities: list, text: str,
                                  source_doc_id: str) -> list:
    """Recover a location prefix word spaCy dropped, leaving a bare hint
    word behind (e.g. "Station Marg" -> bare "Marg").
    """
    result: list = []

    for entity in entities:
        stripped = entity.text.strip()
        is_bare_hint_word = stripped in _LOCATION_HINTS

        if not is_bare_hint_word:
            result.append(entity)
            continue

        prefix_end = entity.start_char
        prefix_start = text.rfind(" ", 0, prefix_end - 1) + 1
        if prefix_start >= prefix_end - 1:
            result.append(entity)
            continue

        between = text[prefix_end - 1:prefix_end]
        candidate_prefix = text[prefix_start:prefix_end - 1]

        if between != " " or not candidate_prefix or not candidate_prefix[0].isupper():
            result.append(entity)
            continue

        combined_text = f"{candidate_prefix} {stripped}"
        corrected = _make_entity(
            text=combined_text,
            entity_type=EntityType.LOCATION,
            source_doc_id=source_doc_id,
            start=prefix_start,
            end=entity.end_char,
        )
        corrected.metadata["engine"] = "spacy"
        corrected.metadata["raw_label"] = f"{entity.metadata.get('raw_label')}_corrected"
        corrected.metadata["correction_applied"] = "recovered_dropped_location_prefix"
        result.append(corrected)

    return result


def _reclassify_person_mistagged_as_org(entities: list) -> list:
    """Reclassify a two-word Indian name tagged as ORGANIZATION back to
    PERSON, when every word is a gazetteer name and no org suffix is present.
    """
    gazetteer = _get_indian_name_components()
    result: list = []

    for entity in entities:
        if entity.entity_type != EntityType.ORGANIZATION:
            result.append(entity)
            continue

        words = entity.text.strip().split()
        has_org_suffix = any(
            entity.text.endswith(suffix) or f" {suffix}" in entity.text
            for suffix in _ORG_SUFFIXES
        )
        all_words_are_names = len(words) >= 2 and all(w in gazetteer for w in words)

        if all_words_are_names and not has_org_suffix:
            entity.entity_type = EntityType.PERSON
            entity.normalized_text = normalize_entity(entity)
            entity.confidence = confidence_score(entity)
            entity.metadata["correction_applied"] = "reclassified_org_as_person"

        result.append(entity)

    return result


_NON_ORG_PREFIX_WORDS = frozenset({
    "The", "A", "An", "This", "That", "These", "Those", "Local",
    "National", "International", "Regional", "Private", "Public",
    "His", "Her", "Their", "Our", "Some", "Many", "Several", "New",
    "Old", "Small", "Large", "Major", "Minor",
})

_ORG_SUFFIX_SCAN_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]*)\s+(" + "|".join(_ORG_SUFFIXES) + r")\b"
)

_LOCATION_HINT_SCAN_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]*)\s+(" + "|".join(_LOCATION_HINTS) + r")\b"
)


def _recover_dropped_organizations(entities: list, text: str, source_doc_id: str,
                                    spacy_seen_spans: list) -> list:
    """Recover an organization name spaCy emitted no usable entity for at all."""
    return _recover_dropped_entities_by_suffix_scan(
        entities, text, source_doc_id, spacy_seen_spans,
        pattern=_ORG_SUFFIX_SCAN_PATTERN,
        entity_type=EntityType.ORGANIZATION,
        prefix_blocklist=_NON_ORG_PREFIX_WORDS,
        correction_label="recovered_dropped_organization",
    )


def _recover_dropped_locations(entities: list, text: str, source_doc_id: str,
                                spacy_seen_spans: list) -> list:
    """Recover a location that produced zero spaCy entities."""
    return _recover_dropped_entities_by_suffix_scan(
        entities, text, source_doc_id, spacy_seen_spans,
        pattern=_LOCATION_HINT_SCAN_PATTERN,
        entity_type=EntityType.LOCATION,
        prefix_blocklist=_NON_ORG_PREFIX_WORDS,
        correction_label="recovered_dropped_location",
    )


def _recover_dropped_entities_by_suffix_scan(
    entities: list, text: str, source_doc_id: str, spacy_seen_spans: list,
    *, pattern, entity_type: EntityType, prefix_blocklist: frozenset,
    correction_label: str,
) -> list:
    """Scan text for a "[Capitalized word] [known suffix]" pattern and
    recover it as a new entity, only where no existing entity or spaCy
    span already accounts for it.
    """
    claimed = [(e.start_char, e.end_char) for e in entities]
    recovered: list = []

    for match in pattern.finditer(text):
        prefix_word = match.group(1)
        if prefix_word in prefix_blocklist:
            continue

        span = (match.start(), match.end())
        if _overlaps_any(span, claimed):
            continue

        if _fully_contained_in_any(span, spacy_seen_spans):
            continue

        entity = _make_entity(
            text=match.group(),
            entity_type=entity_type,
            source_doc_id=source_doc_id,
            start=match.start(),
            end=match.end(),
        )
        entity.metadata["engine"] = "regex"
        entity.metadata["correction_applied"] = correction_label
        recovered.append(entity)
        claimed.append(span)

    return entities + recovered


def _get_spacy_model():
    """Lazily load and cache the spaCy model.

    Raises:
        RuntimeError: if spaCy or the en_core_web_sm model isn't installed.
    """
    global _spacy_nlp
    if _spacy_nlp is not None:
        return _spacy_nlp

    try:
        import spacy
    except ImportError as exc:
        raise RuntimeError(
            "spaCy is required for entity extraction but is not installed. "
            "Run:\n    pip install spacy --break-system-packages\n"
            "    python -m spacy download en_core_web_sm"
        ) from exc

    try:
        _spacy_nlp = spacy.load("en_core_web_sm")
    except OSError as exc:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is not downloaded. Run:\n"
            "    python -m spacy download en_core_web_sm"
        ) from exc

    return _spacy_nlp


def _extract_with_spacy(text: str, source_doc_id: str,
                         claimed_spans: list) -> list:
    """Run spaCy NER, then apply correction passes for known failure
    modes: split names, dropped location prefixes, PERSON-as-ORG
    mistags, and dropped organizations/locations.
    """
    nlp = _get_spacy_model()
    doc = nlp(text)

    entities = []
    spacy_seen_spans: list = []

    for ent in doc.ents:
        spacy_seen_spans.append((ent.start_char, ent.end_char))

        mapped_type = _SPACY_LABEL_MAP.get(ent.label_)
        if mapped_type is None:
            continue

        span = (ent.start_char, ent.end_char)
        if _overlaps_any(span, claimed_spans):
            continue

        entity = _make_entity(
            text=ent.text,
            entity_type=mapped_type,
            source_doc_id=source_doc_id,
            start=ent.start_char,
            end=ent.end_char,
        )
        entity.metadata["engine"] = "spacy"
        entity.metadata["raw_label"] = ent.label_
        entities.append(entity)
        claimed_spans.append(span)

    entities = _merge_split_person_names(entities, text, source_doc_id)
    entities = _merge_split_location_prefix(entities, text, source_doc_id)
    entities = _reclassify_person_mistagged_as_org(entities)
    entities = _recover_dropped_organizations(
        entities, text, source_doc_id, spacy_seen_spans
    )
    entities = _recover_dropped_locations(
        entities, text, source_doc_id, spacy_seen_spans
    )

    return entities


# ---------------------------------------------------------------------------
# HuggingFace engine (optional secondary pass)
# ---------------------------------------------------------------------------

_hf_pipeline = None


def _get_hf_pipeline():
    """Lazily load and cache a HuggingFace NER pipeline.

    Requires the HF_NER_MODEL env var to be set to a real model checkpoint.

    Raises:
        RuntimeError: if HF_NER_MODEL is unset, or transformers/torch aren't installed.
    """
    global _hf_pipeline
    if _hf_pipeline is not None:
        return _hf_pipeline

    model_name = os.environ.get("HF_NER_MODEL")
    if not model_name:
        raise RuntimeError(
            "No HuggingFace NER model configured. Set the HF_NER_MODEL "
            "environment variable to a real model checkpoint (e.g. an "
            "IndicNER model) before calling extract_entities with "
            "use_multilingual_pass=True."
        )

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError(
            "transformers is required for the HuggingFace NER pass but is "
            "not installed. Run:\n"
            "    pip install transformers torch --break-system-packages"
        ) from exc

    try:
        import torch  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "transformers is installed but no backend (torch) is "
            "available, which causes a misleading 'couldn't connect to "
            "huggingface.co' error instead of a clear one. Run:\n"
            "    pip install torch --break-system-packages"
        ) from exc

    _hf_pipeline = pipeline(
        "ner", model=model_name, aggregation_strategy="simple"
    )
    return _hf_pipeline


def _extract_with_huggingface(text: str, source_doc_id: str,
                               claimed_spans: list) -> list:
    """Run the configured HF NER pipeline. Only PERSON-equivalent labels
    are mapped currently.
    """
    ner_pipeline = _get_hf_pipeline()
    raw_results = ner_pipeline(text)

    hf_label_map = {
        "PER": EntityType.PERSON,
        "PERSON": EntityType.PERSON,
    }

    entities = []
    for result in raw_results:
        mapped_type = hf_label_map.get(result.get("entity_group", "").upper())
        if mapped_type is None:
            continue

        span = (result["start"], result["end"])
        if _overlaps_any(span, claimed_spans):
            continue

        entity = _make_entity(
            text=result["word"],
            entity_type=mapped_type,
            source_doc_id=source_doc_id,
            start=result["start"],
            end=result["end"],
        )
        entity.metadata["engine"] = "huggingface"
        entity.metadata["raw_label"] = result.get("entity_group")
        entity.metadata["hf_score"] = float(result.get("score", 0.0))
        entities.append(entity)
        claimed_spans.append(span)

    return entities


def extract_entities(text: str, source_doc_id: str,
                      use_multilingual_pass: bool = False) -> list:
    """Extract typed entities from document text.

    Pipeline: regex (PHONE, VEHICLE) -> spaCy (PERSON, LOCATION,
    ORGANIZATION) -> optional HuggingFace pass if use_multilingual_pass.

    Raises:
        RuntimeError: if spaCy isn't installed/downloaded, or (when
            use_multilingual_pass=True) the HF pipeline isn't configured.
    """
    entities = []

    for match in _PHONE_PATTERN.finditer(text):
        entity = _make_entity(
            text=match.group(1),
            entity_type=EntityType.PHONE,
            source_doc_id=source_doc_id,
            start=match.start(1),
            end=match.end(1),
        )
        entity.metadata["engine"] = "regex"
        entities.append(entity)

    for match in _VEHICLE_PATTERN.finditer(text):
        entity = _make_entity(
            text=match.group(),
            entity_type=EntityType.VEHICLE,
            source_doc_id=source_doc_id,
            start=match.start(),
            end=match.end(),
        )
        entity.metadata["engine"] = "regex"
        entities.append(entity)

    claimed_spans = [(e.start_char, e.end_char) for e in entities]

    entities.extend(_extract_with_spacy(text, source_doc_id, claimed_spans))

    if use_multilingual_pass:
        entities.extend(_extract_with_huggingface(text, source_doc_id, claimed_spans))

    return entities


def _overlaps_any(span, others) -> bool:
    start, end = span
    for o_start, o_end in others:
        if start < o_end and o_start < end:
            return True
    return False


def _fully_contained_in_any(span, others) -> bool:
    start, end = span
    for o_start, o_end in others:
        if o_start <= start and end <= o_end:
            return True
    return False


def _make_entity(text: str, entity_type: EntityType, source_doc_id: str,
                  start: int, end: int) -> ExtractedEntity:
    entity = ExtractedEntity(
        id=f"ent-{uuid.uuid4().hex[:12]}",
        text=text,
        entity_type=entity_type,
        source_doc_id=source_doc_id,
        start_char=start,
        end_char=end,
    )
    entity.normalized_text = normalize_entity(entity)
    entity.confidence = confidence_score(entity)
    return entity


# ---------------------------------------------------------------------------
# 3. normalize_entity
# ---------------------------------------------------------------------------

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_entity(entity: ExtractedEntity) -> str:
    """Clean casing/punctuation before resolution.

    PHONE: strip to digits, drop leading "91" country code if present.
    VEHICLE: uppercase, strip whitespace/hyphens.
    PERSON/LOCATION/ORGANIZATION: collapse whitespace, title-case.
    """
    raw = entity.text.strip()

    if entity.entity_type == EntityType.PHONE:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits

    if entity.entity_type == EntityType.VEHICLE:
        return re.sub(r"[\s-]", "", raw).upper()

    collapsed = _WHITESPACE_RUN.sub(" ", raw)
    # Preserve short all-caps acronyms (e.g. "MG") instead of .title()-casing them
    words = [w if w.isupper() and len(w) <= 4 else w.title() for w in collapsed.split(" ")]
    return " ".join(words)


# ---------------------------------------------------------------------------
# 4. confidence_score
# ---------------------------------------------------------------------------

def confidence_score(entity: ExtractedEntity) -> float:
    """Extraction confidence in [0.0, 1.0]: 0.9 for regex (PHONE/VEHICLE),
    the model's own score for huggingface, 0.75 fixed for spacy.
    """
    engine = entity.metadata.get("engine")

    if entity.entity_type in (EntityType.PHONE, EntityType.VEHICLE):
        return 0.9

    if engine == "huggingface" and "hf_score" in entity.metadata:
        return float(entity.metadata["hf_score"])

    return 0.75


if __name__ == "__main__":
    sample_text = (
        "On 12th August, complainant Priya Sharma reported that Raju "
        "Kumar, last seen near MG Road, was contacted from phone "
        "number 9876543210. His vehicle, registered as MH12AB1234, was "
        "spotted outside Sunrise Traders Pvt Ltd."
    )
    fir = load_synthetic_fir(sample_text, doc_id="fir-demo-001")
    found = extract_entities(fir.raw_text, fir.doc_id)
    for e in found:
        print(f"{e.entity_type.value:12} | {e.text!r:28} -> "
              f"{e.normalized_text!r:20} | conf={e.confidence:.2f} "
              f"| engine={e.metadata.get('engine')}")
