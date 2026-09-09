"""
scripts/seed_data.py

Populate the database with demo agencies, one user per role, and one
demo case — so a fresh checkout has something to log in with and
query, without needing to hand-craft records first.

Idempotent: safe to run multiple times (checks for existing records
by ID/badge_id before creating anything new).

Usage: python -m scripts.seed_data
"""

import uuid

from db.connection import SessionLocal, init_db
from db import repository as repo
from schema.case import Case
from schema.user import Agency, Role, User, hash_password


def seed() -> None:
    """Create the demo agencies/users/case if they don't already exist,
    then print the demo login credentials.
    """
    init_db()
    db = SessionLocal()

    if repo.get_agency(db, "AG-NCRB") is None:
        repo.create_agency(db, Agency(id="AG-NCRB", name="NCRB", agency_type="ncrb"))
    if repo.get_agency(db, "AG-WSD") is None:
        repo.create_agency(
            db, Agency(id="AG-WSD", name="Women Safety Division", agency_type="women_safety_division", parent_agency_id="AG-NCRB")
        )

    # One demo user per role, all in AG-NCRB, so every permission level
    # is immediately testable after a fresh seed.
    demo_users = [
        ("u-investigator", "Demo Investigator", "INV001", "AG-NCRB", Role.INVESTIGATOR, "investigator123"),
        ("u-analyst", "Demo Analyst", "ANL001", "AG-NCRB", Role.ANALYST, "analyst123"),
        ("u-admin", "Demo Admin", "ADM001", "AG-NCRB", Role.ADMIN, "admin123"),
        ("u-superadmin", "Demo Super Admin", "SUP001", "AG-NCRB", Role.SUPER_ADMIN, "super123"),
    ]
    for user_id, name, badge_id, agency_id, role, password in demo_users:
        if repo.get_user_by_badge_id(db, badge_id) is None:
            repo.create_user(
                db,
                User(id=user_id, name=name, badge_id=badge_id, agency_id=agency_id, role=role, password_hash=hash_password(password)),
            )

    demo_case_id = "DEMO-CASE"
    if repo.get_case(db, demo_case_id) is None:
        repo.create_case(
            db, Case(id=demo_case_id, title="Demo case — trafficking network, sector 9", agency_id="AG-NCRB", created_by_user_id="u-investigator")
        )
        repo.assign_investigator(db, demo_case_id, "u-investigator")

    db.close()
    print("Seed complete. Demo logins:")
    for _, name, badge_id, _, role, password in demo_users:
        print(f"  {role.value:14s} badge_id={badge_id:8s} password={password}")


if __name__ == "__main__":
    seed()
