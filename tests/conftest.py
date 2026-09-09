"""
tests/conftest.py

Shared pytest fixtures. Forces DATABASE_URL to a local SQLite file
before any app module is imported, so the test suite never touches a
real PostgreSQL server — the ORM code path is identical either way
(see db/connection.py), so this is a safe stand-in for tests.

reset_db (autouse) wipes and recreates every table before each test,
and clears the in-memory reference stores in schema/user.py and
schema/case.py too, so tests never leak state into each other.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/test_cna.db")

import pytest
from fastapi.testclient import TestClient

import schema.case as case_module
import schema.user as user_module
from api.auth import _SESSION_STORE
from api.main import app
from db import repository as repo
from db.connection import SessionLocal, engine
from db.models import Base
from schema.user import Agency, Role, User, hash_password


@pytest.fixture(autouse=True)
def reset_db():
    """Runs before every test: fresh database tables, cleared session
    store, cleared in-memory reference stores. Automatic (autouse) so
    no test file needs to remember to request it.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _SESSION_STORE.clear()
    user_module._USER_STORE.clear()
    user_module._AGENCY_STORE.clear()
    user_module._CASE_ASSIGNMENTS.clear()
    user_module._CASE_AGENCY.clear()
    user_module._ALL_CASE_IDS.clear()
    case_module._CASE_STORE.clear()
    yield


@pytest.fixture
def db_session():
    """A raw SQLAlchemy Session for tests that need to seed data
    directly through db.repository (see seeded_users below).
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """A FastAPI TestClient wired to the real app (real routes, real
    DB-backed auth) — used by every API-level test.
    """
    return TestClient(app)


@pytest.fixture
def seeded_users(db_session):
    """Seed two agencies and five users (one per role, plus a second
    ADMIN in a different agency for cross-agency authorization tests)
    directly into the test database. Returns the dict of User objects,
    keyed by role name, for tests that need to reference them.
    """
    repo.create_agency(db_session, Agency(id="AG1", name="NCRB", agency_type="ncrb"))
    repo.create_agency(db_session, Agency(id="AG2", name="WSD", agency_type="women_safety_division"))

    users = {
        "investigator": User(id="u1", name="Inv", badge_id="B001", agency_id="AG1", role=Role.INVESTIGATOR, password_hash=hash_password("pw1")),
        "analyst": User(id="u2", name="Ana", badge_id="B002", agency_id="AG1", role=Role.ANALYST, password_hash=hash_password("pw2")),
        "admin": User(id="u3", name="Adm", badge_id="B003", agency_id="AG1", role=Role.ADMIN, password_hash=hash_password("pw3")),
        "admin_other_agency": User(id="u4", name="AdmO", badge_id="B004", agency_id="AG2", role=Role.ADMIN, password_hash=hash_password("pw4")),
        "super_admin": User(id="u5", name="Sup", badge_id="B005", agency_id="AG1", role=Role.SUPER_ADMIN, password_hash=hash_password("pw5")),
    }
    for u in users.values():
        repo.create_user(db_session, u)
    return users


def auth_headers(client, badge_id, password):
    """Log in as the given user and return a ready-to-use
    Authorization header dict, so API tests don't have to repeat the
    login boilerplate.
    """
    r = client.post("/auth/login", json={"badge_id": badge_id, "password": password})
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}
