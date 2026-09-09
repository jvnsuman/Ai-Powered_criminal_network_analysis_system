"""
nlp/confidence.py

Shared confidence-scoring utilities used by nlp/extraction.py and
nlp/resolution.py.
"""

import math


def normalize_confidence(raw_score: float, method: str = "minmax") -> float:
    """Normalize a raw score into [0.0, 1.0].

    "minmax" clips a score already roughly in [0.0, 1.0]. "sigmoid"
    logistic-squashes an unbounded score (e.g. a weighted sum of several
    signals) into range.

    Raises:
        ValueError: if method is not "minmax" or "sigmoid".
    """
    if method == "minmax":
        return max(0.0, min(1.0, raw_score))
    if method == "sigmoid":
        return 1.0 / (1.0 + math.exp(-raw_score))
    raise ValueError(f"Unknown normalization method: {method!r}. Use 'minmax' or 'sigmoid'.")


def below_review_threshold(confidence: float, threshold: float = 0.6) -> bool:
    """True if confidence is below threshold (should be flagged for review)."""
    return confidence < threshold
