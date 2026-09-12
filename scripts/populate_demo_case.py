"""
scripts/populate_demo_case.py

Bridges data/generate_synthetic.py (which only builds in-memory
SyntheticDocument objects) to the actual database: creates a new Case,
assigns it to an investigator, and ingests generated synthetic
documents into it — so the case shows up in the dashboard's dropdown
with real content already inside.

This exists because generate_synthetic.py's own __main__ block only
prints documents to the terminal; it never touches the database. This
script is the missing link between "I generated synthetic data" and
"I can see a case in the dashboard."

Usage:
    python -m scripts.populate_demo_case
    python -m scripts.populate_demo_case --title "Sector 12 trafficking ring" --firs 5 --cdrs 3 --financial 2
    python -m scripts.populate_demo_case --investigator-badge INV001
"""

import argparse
import uuid

from db.connection import SessionLocal, init_db
from db import repository as repo
from data.generate_synthetic import generate_dataset, DocumentType
from schema.case import Case
from schema.entities import SourceDocument

# Maps data.generate_synthetic's DocumentType to
# schema.entities.VALID_DOCUMENT_TYPES, since the two modules use
# slightly different naming conventions.
_DOC_TYPE_MAP = {
    DocumentType.FIR: "fir",
    DocumentType.CDR: "cdr",
    DocumentType.FINANCIAL_RECORD: "financial",
}


def populate(title: str, num_firs: int, num_cdrs: int, num_financial: int,
             investigator_badge_id: str) -> str:
    """Generate a synthetic dataset, create a case for it, ingest every
    document, and assign the given investigator to the case.

    Returns:
        The new case's ID.

    Raises:
        ValueError: if investigator_badge_id doesn't match any known user.
    """
    init_db()
    db = SessionLocal()
    try:
        investigator = repo.get_user_by_badge_id(db, investigator_badge_id)
        if investigator is None:
            raise ValueError(
                f"No user found with badge_id={investigator_badge_id!r}. "
                f"Run scripts/seed_data.py first, or pass --investigator-badge "
                f"with a real badge id."
            )

        case = Case(
            id=str(uuid.uuid4()),
            title=title,
            agency_id=investigator.agency_id,
            created_by_user_id=investigator.id,
        )
        created_case = repo.create_case(db, case)
        repo.assign_investigator(db, created_case.id, investigator.id)

        dataset = generate_dataset(
            num_firs=num_firs, num_cdrs=num_cdrs, num_financial=num_financial,
        )

        for synth_doc in dataset:
            # FIRs carry their content in .text; CDR/financial records
            # carry it in .structured (see generate_synthetic.py) —
            # SourceDocument.raw_text needs a plain string either way,
            # so structured docs get a str() fallback rather than an
            # empty raw_text (which schema.entities.SourceDocument
            # rejects on validation).
            raw_text = synth_doc.text if synth_doc.text else str(synth_doc.structured)

            document = SourceDocument(
                id=synth_doc.doc_id,
                document_type=_DOC_TYPE_MAP[synth_doc.doc_type],
                raw_text=raw_text,
                case_id=created_case.id,
            )
            repo.create_document(db, document)

        print(f"Created case {created_case.id!r} ({title!r}) in agency "
              f"{investigator.agency_id!r}, assigned to {investigator.name} "
              f"({investigator_badge_id}).")
        print(f"Ingested {len(dataset)} synthetic documents "
              f"({num_firs} FIR, {num_cdrs} CDR, {num_financial} financial).")
        print("Log in as that investigator and the case should now appear "
              "in the dashboard's case dropdown.")

        return created_case.id
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic data and populate a real case with it."
    )
    parser.add_argument("--title", default="Synthetic demo case",
                         help="Title for the new case.")
    parser.add_argument("--firs", type=int, default=5, dest="num_firs",
                         help="Number of synthetic FIRs to generate.")
    parser.add_argument("--cdrs", type=int, default=3, dest="num_cdrs",
                         help="Number of synthetic CDRs to generate.")
    parser.add_argument("--financial", type=int, default=2, dest="num_financial",
                         help="Number of synthetic financial records to generate.")
    parser.add_argument("--investigator-badge", default="INV001",
                         dest="investigator_badge_id",
                         help="Badge ID of the investigator to assign this case to "
                              "(default: INV001, the seed_data.py demo investigator).")
    args = parser.parse_args()

    populate(
        title=args.title,
        num_firs=args.num_firs,
        num_cdrs=args.num_cdrs,
        num_financial=args.num_financial,
        investigator_badge_id=args.investigator_badge_id,
    )


if __name__ == "__main__":
    main()
