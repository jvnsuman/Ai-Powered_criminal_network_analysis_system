"""
tests/test_api_alerts.py

Integration tests for api/routes/alerts.py — the new Recent Alerts
feed backing the sidebar-nav dashboard. Covers authorization (same
case-scoping as /query) and the honest-empty-state behavior (no
findings fabricated when nothing is persisted yet — see that module's
docstring).
"""

from tests.conftest import auth_headers


def test_alerts_requires_auth(client, seeded_users):
    r = client.get("/alerts/CASE-1")
    assert r.status_code == 401


def test_alerts_unauthorized_case_returns_403(client, seeded_users):
    headers = auth_headers(client, "B001", "pw1")
    r = client.get("/alerts/CASE-999", headers=headers)
    assert r.status_code == 403


def test_alerts_authorized_case_returns_empty_list_honestly(client, seeded_users):
    """No entity/relationship persistence exists yet (see
    api/routes/query.py's docstring for the same limitation) — the
    alerts endpoint must report an empty list, not fabricate example
    alerts, for a case it has nothing to analyze.
    """
    headers = auth_headers(client, "B001", "pw1")
    r = client.post("/cases/", json={"title": "Alert test case"}, headers=headers)
    case_id = r.json()["id"]

    r = client.get(f"/alerts/{case_id}", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"case_id": case_id, "alerts": []}
