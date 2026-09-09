"""
tests/test_api_routes.py

Integration tests for the ingestion, query, and case-management routes
— exercised through the real FastAPI app and a real (test) database.
Covers the request-validation, authorization, and agency-scoping
behavior each route is responsible for.
"""

from tests.conftest import auth_headers


def test_ingest_valid_document_returns_202(client, seeded_users):
    """Extraction is now real (spaCy-based) — a plain FIR-shaped
    document should come back "extracted" with an entity count, not
    the old permanently-stubbed "stored_pending_extraction" state.
    """
    headers = auth_headers(client, "B001", "pw1")
    r = client.post(
        "/ingest/",
        json={"id": "D1", "document_type": "fir", "raw_text": "Raju Kumar was seen near MG Road."},
        headers=headers,
    )
    assert r.status_code == 202
    assert r.json()["status"] == "extracted"
    assert r.json()["entity_count"] >= 1


def test_ingest_duplicate_document_returns_409(client, seeded_users):
    headers = auth_headers(client, "B001", "pw1")
    client.post("/ingest/", json={"id": "D1", "document_type": "fir", "raw_text": "text"}, headers=headers)
    r = client.post("/ingest/", json={"id": "D1", "document_type": "fir", "raw_text": "text2"}, headers=headers)
    assert r.status_code == 409


def test_ingest_invalid_shape_returns_400(client, seeded_users):
    headers = auth_headers(client, "B001", "pw1")
    r = client.post("/ingest/", json={"id": "D2", "document_type": "tweet", "raw_text": "x"}, headers=headers)
    assert r.status_code == 400


def test_query_unauthorized_case_returns_403(client, seeded_users):
    headers = auth_headers(client, "B001", "pw1")
    r = client.get("/query/CASE-999", headers=headers)
    assert r.status_code == 403


def test_evidence_requires_auth(client, seeded_users):
    r = client.get("/evidence/E1")
    assert r.status_code == 401


def test_create_case_and_list(client, seeded_users):
    headers = auth_headers(client, "B001", "pw1")
    r = client.post("/cases/", json={"title": "Test case"}, headers=headers)
    assert r.status_code == 201
    case_id = r.json()["id"]

    r = client.get("/cases/", headers=headers)
    assert r.status_code == 200
    assert any(c["id"] == case_id for c in r.json()["cases"])


def test_create_case_for_other_agency_forbidden(client, seeded_users):
    """Only a SUPER_ADMIN may create a case for an agency other than
    their own — an investigator cannot.
    """
    headers = auth_headers(client, "B001", "pw1")
    r = client.post("/cases/", json={"title": "x", "agency_id": "AG2"}, headers=headers)
    assert r.status_code == 403


def test_assign_investigator_requires_admin_role(client, seeded_users):
    inv_headers = auth_headers(client, "B001", "pw1")
    r = client.post("/cases/", json={"title": "Test"}, headers=inv_headers)
    case_id = r.json()["id"]

    r = client.post(f"/cases/{case_id}/assign", json={"user_id": "u2"}, headers=inv_headers)
    assert r.status_code == 403


def test_assign_investigator_cross_agency_forbidden(client, seeded_users):
    """An ADMIN from one agency cannot assign investigators on a case
    belonging to a different agency.
    """
    admin_headers = auth_headers(client, "B003", "pw3")
    r = client.post("/cases/", json={"title": "Test"}, headers=admin_headers)
    case_id = r.json()["id"]

    other_agency_admin = auth_headers(client, "B004", "pw4")
    r = client.post(f"/cases/{case_id}/assign", json={"user_id": "u1"}, headers=other_agency_admin)
    assert r.status_code == 403


def test_assign_investigator_success(client, seeded_users):
    admin_headers = auth_headers(client, "B003", "pw3")
    r = client.post("/cases/", json={"title": "Test"}, headers=admin_headers)
    case_id = r.json()["id"]

    r = client.post(f"/cases/{case_id}/assign", json={"user_id": "u1"}, headers=admin_headers)
    assert r.status_code == 200
    assert "u1" in r.json()["assigned_investigator_ids"]
