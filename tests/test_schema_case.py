"""
tests/test_schema_case.py

Unit tests for schema/case.py: construction validation, dict
round-tripping, and the in-memory case registry's lookup/assignment
helpers.
"""

import pytest

from schema.case import Case, CaseStatus, assign_investigator, get_case, list_cases_for_agency, register_case


def test_case_round_trip_dict():
    c = Case(id="C1", title="Test case", agency_id="AG1")
    assert Case.from_dict(c.to_dict()) == c


def test_case_rejects_blank_title():
    with pytest.raises(ValueError):
        Case(id="C1", title="  ", agency_id="AG1")


def test_case_rejects_missing_agency():
    with pytest.raises(ValueError):
        Case(id="C1", title="x", agency_id="")


def test_register_and_get_case():
    c = Case(id="C1", title="Test", agency_id="AG1")
    register_case(c)
    assert get_case("C1") == c
    assert get_case("nonexistent") is None


def test_list_cases_for_agency_filters_correctly():
    register_case(Case(id="C1", title="A", agency_id="AG1"))
    register_case(Case(id="C2", title="B", agency_id="AG2"))
    result = list_cases_for_agency("AG1")
    assert [c.id for c in result] == ["C1"]


def test_assign_investigator_adds_once():
    """Assigning the same investigator twice should not duplicate them
    in assigned_investigator_ids.
    """
    c = Case(id="C1", title="A", agency_id="AG1")
    register_case(c)
    assign_investigator("C1", "u1")
    assign_investigator("C1", "u1")
    assert get_case("C1").assigned_investigator_ids == ["u1"]


def test_assign_investigator_unknown_case_returns_none():
    assert assign_investigator("nonexistent", "u1") is None
