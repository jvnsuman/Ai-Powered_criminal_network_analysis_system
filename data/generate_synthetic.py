"""
data/generate_synthetic.py

Synthetic FIR and CDR generators. Runs in parallel with the technical
pair's NLP/graph work — this is what the 4 non-technical team members
own (project notes Section 5).

Design principle: build deliberate noise in (misspellings, transliteration
variants, incomplete fields, embedded suspicious patterns like burst
calling) — a too-clean synthetic corpus stress-tests nothing. See project
notes Section 9's Judge Q&A Q3 for why this matters.

Status: [TODO]
"""


def generate_synthetic_fir(scenario: dict) -> str:
    """[TODO] Generate a synthetic FIR-style text block for a given
    scenario (e.g. a trafficking-ring case). Uses Faker + templates.
    Should include realistic noise: aliases, partial names, incomplete
    fields — not clean toy sentences.
    """
    raise NotImplementedError


def generate_synthetic_cdr(scenario: dict) -> list[dict]:
    """[TODO] Generate a synthetic call-log (CDR) dataset with embedded
    suspicious patterns — e.g. burst calling before an event, calls to
    a shared intermediary number — tied to the same scenario as
    generate_synthetic_fir so entity resolution has real cross-source
    links to find.
    """
    raise NotImplementedError


def generate_synthetic_financial(scenario: dict) -> list[dict]:
    """[TODO] Generate synthetic financial transaction records with
    structuring/layering patterns, borrowing logic from public AML/
    fraud-detection research. Dec scope — not required for Sep slice.
    """
    raise NotImplementedError
