"""
nlp/confidence.py

Shared confidence-scoring utilities used by both extraction and
resolution. Kept separate so scoring logic isn't duplicated across
nlp/extraction.py and nlp/resolution.py.

Status: [TODO]
"""


def normalize_confidence(raw_score: float, method: str = "minmax") -> float:
    """[TODO] Normalize a raw model/similarity score into a consistent
    0.0-1.0 confidence range so extraction confidence and resolution
    confidence are comparable on the same scale.
    """
    raise NotImplementedError


def below_review_threshold(confidence: float, threshold: float = 0.6) -> bool:
    """[TODO] Shared threshold check used by both
    nlp.extraction.confidence_score and nlp.resolution.flag_for_review.
    """
    raise NotImplementedError
