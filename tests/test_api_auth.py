"""
tests/test_api_auth.py

Integration tests for the login/logout/session flow, exercised through
the real FastAPI app and a real (test) database — not the in-memory
schema.user store directly. See tests/conftest.py's seeded_users
fixture for how the test data gets there.
"""

def test_login_success(client, seeded_users):
    r = client.post("/auth/login", json={"badge_id": "B001", "password": "pw1"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert body["role"] == "investigator"


def test_login_wrong_password(client, seeded_users):
    r = client.post("/auth/login", json={"badge_id": "B001", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_badge(client, seeded_users):
    r = client.post("/auth/login", json={"badge_id": "nope", "password": "x"})
    assert r.status_code == 401


def test_protected_route_requires_auth(client, seeded_users):
    r = client.get("/query/CASE-1")
    assert r.status_code == 401


def test_protected_route_rejects_bad_token(client, seeded_users):
    r = client.get("/query/CASE-1", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_logout_invalidates_token(client, seeded_users):
    """A token that's just been logged out should no longer work on a
    subsequent request.
    """
    r = client.post("/auth/login", json={"badge_id": "B001", "password": "pw1"})
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/auth/logout", params={"token": token})
    r = client.get("/query/CASE-1", headers=headers)
    assert r.status_code == 401
