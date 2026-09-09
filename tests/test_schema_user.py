"""
tests/test_schema_user.py

Unit tests for schema/user.py's pure business logic: password hashing,
login, the role-authorization hierarchy, and agency-scoped case
visibility. These test the in-memory reference implementation
directly, independent of the database — the DB-backed equivalents
(db.repository) are covered separately via tests/test_api_routes.py.
"""

import pytest

from schema.user import (
    Agency,
    Role,
    User,
    authorize,
    get_user_cases,
    hash_password,
    login,
    register_agency,
    register_user,
    verify_password,
    assign_case,
)


def test_hash_and_verify_password_roundtrip():
    h = hash_password("correct-horse")
    assert verify_password("correct-horse", h)
    assert not verify_password("wrong", h)


def test_login_succeeds_with_correct_credentials():
    register_agency(Agency(id="AG1", name="NCRB", agency_type="ncrb"))
    register_user(User(id="u1", name="R", badge_id="B1", agency_id="AG1", role=Role.INVESTIGATOR, password_hash=hash_password("pw")))
    user = login({"badge_id": "B1", "password": "pw"})
    assert user is not None
    assert user.id == "u1"
    assert user.last_login is not None


def test_login_fails_with_wrong_password():
    register_user(User(id="u1", name="R", badge_id="B1", agency_id="AG1", role=Role.INVESTIGATOR, password_hash=hash_password("pw")))
    assert login({"badge_id": "B1", "password": "wrong"}) is None


def test_login_fails_for_unknown_badge_id():
    assert login({"badge_id": "nope", "password": "x"}) is None


def test_login_rejects_missing_fields():
    assert login({}) is None
    assert login({"badge_id": "B1"}) is None


@pytest.mark.parametrize(
    "role,target,expected",
    [
        (Role.SUPER_ADMIN, Role.ADMIN, True),
        (Role.SUPER_ADMIN, Role.ANALYST, True),
        (Role.ADMIN, Role.ANALYST, True),
        (Role.ADMIN, Role.SUPER_ADMIN, False),
        (Role.INVESTIGATOR, Role.ANALYST, False),
        (Role.ANALYST, Role.INVESTIGATOR, False),
    ],
)
def test_authorize_role_hierarchy(role, target, expected):
    """Higher roles imply lower ones (SUPER_ADMIN -> ADMIN -> ANALYST),
    but INVESTIGATOR is its own lane, not a subset of ANALYST or
    vice versa. See schema.user._ROLE_IMPLIES.
    """
    user = User(id="u1", name="R", badge_id="B1", agency_id="AG1", role=role)
    assert authorize(user, target) is expected


def test_authorize_none_user_is_false():
    assert authorize(None, Role.INVESTIGATOR) is False


def test_get_user_cases_investigator_sees_only_assigned():
    inv = User(id="u1", name="R", badge_id="B1", agency_id="AG1", role=Role.INVESTIGATOR)
    assign_case("u1", "CASE-1", agency_id="AG1")
    assign_case("u1", "CASE-2", agency_id="AG1")
    assert set(get_user_cases(inv)) == {"CASE-1", "CASE-2"}


def test_get_user_cases_analyst_scoped_to_own_agency():
    """An ANALYST sees every case in their own agency, but not another
    agency's cases — cross-case doesn't mean cross-agency.
    """
    assign_case("u1", "CASE-1", agency_id="AG1")
    assign_case("u2", "CASE-2", agency_id="AG2")
    analyst = User(id="u3", name="A", badge_id="B3", agency_id="AG1", role=Role.ANALYST)
    assert get_user_cases(analyst) == ["CASE-1"]


def test_get_user_cases_super_admin_sees_all_agencies():
    assign_case("u1", "CASE-1", agency_id="AG1")
    assign_case("u2", "CASE-2", agency_id="AG2")
    sup = User(id="u9", name="S", badge_id="B9", agency_id="AG1", role=Role.SUPER_ADMIN)
    assert set(get_user_cases(sup)) == {"CASE-1", "CASE-2"}
