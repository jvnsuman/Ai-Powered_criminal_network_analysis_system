"""
nlp/relation_classification.py

Relationship classification and risk flagging using HuggingFace models.
Takes entity pairs from nlp/extraction.py and classifies the relation
between them, plus flags suspicious/high-risk text.

Models:
    - facebook/bart-large-mnli (zero-shot-classification): relation
      classification against a custom label set.
    - unitary/toxic-bert (text-classification): toxic/hostile language
      flagging, used as a proxy risk signal.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from nlp.extraction import ExtractedEntity, EntityType


class RelationType(str, Enum):
    CALLS = "calls"
    PRESENT_AT = "present-at"
    OWNS = "owns"
    ASSOCIATED_WITH = "associated-with"
    TRANSACTS_WITH = "transacts-with"
    UNRELATED = "unrelated"


# Hypothesis template fed to the NLI model for each RelationType.
_RELATION_HYPOTHESES = {
    RelationType.CALLS: "{a} called or contacted {b} by phone",
    RelationType.PRESENT_AT: "{a} was present at {b}",
    RelationType.OWNS: "{a} owns or is registered to {b}",
    RelationType.ASSOCIATED_WITH: "{a} is associated with {b}",
    RelationType.TRANSACTS_WITH: "{a} sent or received money from {b}",
    RelationType.UNRELATED: "{a} and {b} are not mentioned as related",
}

# ASSOCIATED_WITH is deliberately excluded from the main competition
# below (see _SPECIFIC_RELATION_TYPES). In NLI zero-shot classification,
# broader/easier-to-satisfy hypotheses ("is associated with") reliably
# outscore more specific ones ("called by phone") even when the specific
# one is the objectively correct reading of the source text — e.g. real
# diagnostic runs on this project's own sample data ("...contacted from
# phone number...") scored "is associated with" at 0.49 and "called or
# contacted by phone" at only 0.334, despite the text explicitly
# describing a phone contact. Treating ASSOCIATED_WITH as a peer
# hypothesis lets it silently absorb cases that should have been a
# specific, more evidentially useful relation type. Instead, it's only
# assigned as an explicit fallback (see classify_relation) when no
# specific relation type clears the confidence threshold on its own.
_SPECIFIC_RELATION_TYPES = [
    t for t in RelationType
    if t not in (RelationType.UNRELATED, RelationType.ASSOCIATED_WITH)
]

# Once no specific relation clears confidence_threshold, ASSOCIATED_WITH
# is checked on its own against this lower bar before falling all the
# way to UNRELATED — a low-confidence "these two are connected somehow"
# fallback is more useful to an investigator than nothing at all, but
# it should not be treated as equally certain as a specific relation
# that cleared the main threshold.
_ASSOCIATED_WITH_FALLBACK_THRESHOLD = 0.3


@dataclass
class ClassifiedRelation:
    id: str
    entity_a_id: str
    entity_b_id: str
    relation_type: RelationType
    confidence: float
    source_doc_id: str
    source_text: str = ""


@dataclass
class RiskAssessment:
    source_doc_id: str
    is_flagged: bool
    labels: dict = field(default_factory=dict)
    caveat: str = (
        "This flag reflects toxic/hostile LANGUAGE (profanity, insults, "
        "hate speech), not a general 'criminal risk' assessment."
    )


# ---------------------------------------------------------------------------
# Relation classification
# ---------------------------------------------------------------------------

_relation_pipeline = None


def _get_relation_pipeline():
    """Lazily load and cache the zero-shot-classification pipeline.

    Raises:
        RuntimeError: if transformers/torch are not installed.
    """
    global _relation_pipeline
    if _relation_pipeline is not None:
        return _relation_pipeline

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError(
            "transformers is required for relation classification but is "
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

    _relation_pipeline = pipeline(
        "zero-shot-classification", model="facebook/bart-large-mnli"
    )
    return _relation_pipeline


def _classify_single(classifier, source_text: str, hypothesis_to_type: dict) -> tuple[str, float]:
    """Run the classifier over one set of hypotheses and return the
    top (hypothesis, score) pair.
    """
    hypotheses = list(hypothesis_to_type.keys())
    result = classifier(source_text, hypotheses)
    return result["labels"][0], result["scores"][0]


def classify_relation(entity_a: ExtractedEntity, entity_b: ExtractedEntity,
                       source_text: str,
                       confidence_threshold: float = 0.3) -> ClassifiedRelation:
    """Classify the relationship between two extracted entities.

    Two-pass strategy:
      1. Compete only the SPECIFIC relation types (CALLS, PRESENT_AT,
         OWNS, TRANSACTS_WITH) against each other. If the winner clears
         confidence_threshold, use it.
      2. Otherwise, check ASSOCIATED_WITH on its own against a lower
         bar (_ASSOCIATED_WITH_FALLBACK_THRESHOLD). If it clears that,
         use it as a low-confidence fallback.
      3. Otherwise, UNRELATED.

    ASSOCIATED_WITH is deliberately never compared head-to-head with
    the specific types — see the module-level comment on
    _SPECIFIC_RELATION_TYPES for why (it systematically outscores
    specific, more evidentially useful labels in NLI zero-shot
    classification regardless of which one actually matches the text).

    NOTE on confidence_threshold=0.3 (lowered from an original 0.5):
    zero-shot classification across several competing hypotheses
    rarely produces a top score above 0.5 even for the genuinely
    correct label — real diagnostic runs on this project's own sample
    data showed correct top-scoring relations clustering at 0.41-0.48
    even before ASSOCIATED_WITH was split out, which the old 0.5
    cutoff silently discarded as UNRELATED on every single relation.
    0.3 is a starting point (comfortably above the ~0.2 a uniform
    4-5-way random guess would average), not a validated cutoff — tune
    against labelled data before December.

    Raises:
        RuntimeError: if transformers/torch are not installed, or two
            RelationType templates collapse to an identical hypothesis
            string for this entity pair.
    """
    classifier = _get_relation_pipeline()

    specific_hypothesis_to_type = {
        _RELATION_HYPOTHESES[t].format(a=entity_a.text, b=entity_b.text): t
        for t in _SPECIFIC_RELATION_TYPES
    }
    if len(specific_hypothesis_to_type) != len(_SPECIFIC_RELATION_TYPES):
        raise RuntimeError(
            f"Hypothesis collision detected for entities "
            f"{entity_a.text!r}/{entity_b.text!r} — two RelationType "
            f"templates produced identical text."
        )

    top_hypothesis, top_score = _classify_single(classifier, source_text, specific_hypothesis_to_type)

    if top_score >= confidence_threshold:
        return ClassifiedRelation(
            id=f"rel-{uuid.uuid4().hex[:12]}",
            entity_a_id=entity_a.id,
            entity_b_id=entity_b.id,
            relation_type=specific_hypothesis_to_type[top_hypothesis],
            confidence=top_score,
            source_doc_id=entity_a.source_doc_id,
            source_text=source_text,
        )

    # No specific relation cleared the bar — check ASSOCIATED_WITH on
    # its own as a fallback, at a lower threshold, rather than letting
    # it compete directly against the specific types above.
    associated_hypothesis = _RELATION_HYPOTHESES[RelationType.ASSOCIATED_WITH].format(
        a=entity_a.text, b=entity_b.text
    )
    associated_result = classifier(source_text, [associated_hypothesis])
    associated_score = associated_result["scores"][0]

    if associated_score >= _ASSOCIATED_WITH_FALLBACK_THRESHOLD:
        return ClassifiedRelation(
            id=f"rel-{uuid.uuid4().hex[:12]}",
            entity_a_id=entity_a.id,
            entity_b_id=entity_b.id,
            relation_type=RelationType.ASSOCIATED_WITH,
            confidence=associated_score,
            source_doc_id=entity_a.source_doc_id,
            source_text=source_text,
        )

    return ClassifiedRelation(
        id=f"rel-{uuid.uuid4().hex[:12]}",
        entity_a_id=entity_a.id,
        entity_b_id=entity_b.id,
        relation_type=RelationType.UNRELATED,
        confidence=top_score,
        source_doc_id=entity_a.source_doc_id,
        source_text=source_text,
    )


def classify_all_relations(entities: list[ExtractedEntity], source_text: str,
                            confidence_threshold: float = 0.3,
                            skip_unrelated: bool = True) -> list[ClassifiedRelation]:
    """Classify relationships across every pair of entities from the
    same document. O(n^2) pipeline calls (now up to 2x per pair, since
    a pair that doesn't clear the specific-type threshold triggers a
    second classifier call to check ASSOCIATED_WITH as a fallback —
    see classify_relation).

    Raises:
        RuntimeError: if transformers/torch are not installed.
    """
    results = []
    for entity_a, entity_b in itertools.combinations(entities, 2):
        relation = classify_relation(
            entity_a, entity_b, source_text, confidence_threshold
        )
        if skip_unrelated and relation.relation_type == RelationType.UNRELATED:
            continue
        results.append(relation)
    return results


# ---------------------------------------------------------------------------
# Risk / suspicious-content flagging
# ---------------------------------------------------------------------------

_risk_pipeline = None


def _get_risk_pipeline():
    """Lazily load and cache the toxic-bert text-classification pipeline.

    Raises:
        RuntimeError: if transformers/torch are not installed.
    """
    global _risk_pipeline
    if _risk_pipeline is not None:
        return _risk_pipeline

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError(
            "transformers is required for risk flagging but is not "
            "installed. Run:\n"
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

    _risk_pipeline = pipeline(
        "text-classification", model="unitary/toxic-bert", top_k=None
    )
    return _risk_pipeline


def assess_risk(text: str, source_doc_id: str,
                 flag_threshold: float = 0.5) -> RiskAssessment:
    """Run risk/suspicious-content flagging on a document or span.

    Raises:
        RuntimeError: if transformers/torch are not installed.
    """
    classifier = _get_risk_pipeline()
    raw_result = classifier(text)

    # top_k=None returns [[{label, score}, ...]] (batch-of-one) — unwrap it.
    scores = raw_result[0] if raw_result and isinstance(raw_result[0], list) else raw_result

    labels = {item["label"]: float(item["score"]) for item in scores}
    is_flagged = any(score >= flag_threshold for score in labels.values())

    return RiskAssessment(
        source_doc_id=source_doc_id,
        is_flagged=is_flagged,
        labels=labels,
    )


if __name__ == "__main__":
    from nlp.extraction import load_synthetic_fir, extract_entities

    sample_text = (
        "On 12th August, complainant Priya Sharma reported that Raju "
        "Kumar, last seen near MG Road, was contacted from phone "
        "number 9876543210. His vehicle, registered as MH12AB1234, was "
        "spotted outside Sunrise Traders Pvt Ltd."
    )
    fir = load_synthetic_fir(sample_text, doc_id="fir-demo-001")
    entities = extract_entities(fir.raw_text, fir.doc_id)

    print("--- Extracted entities ---")
    for e in entities:
        print(f"  {e.entity_type.value:12} {e.text!r}")

    print("\n--- Classified relations ---")
    relations = classify_all_relations(entities, fir.raw_text)
    for r in relations:
        a = next(e for e in entities if e.id == r.entity_a_id)
        b = next(e for e in entities if e.id == r.entity_b_id)
        print(f"  {a.text!r} --[{r.relation_type.value}]--> {b.text!r} "
              f"(conf={r.confidence:.2f})")

    print("\n--- Risk assessment ---")
    risk = assess_risk(fir.raw_text, fir.doc_id)
    print(f"  flagged={risk.is_flagged}")
    for label, score in sorted(risk.labels.items(), key=lambda kv: -kv[1]):
        print(f"    {label:15} {score:.3f}")
