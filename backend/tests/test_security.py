import pytest
from app import models as m
from app.db import get_db
from app.main import app
from app.auth_bootstrap import provision
from app.common import future

pytestmark = pytest.mark.real_auth
PASSWORD = "Test-only strong password 2026!"


def setup(client):
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    for id, roles, admin in [
        ("originator", ["ORIGINATOR", "ORG_ADMIN"], False),
        ("originator2", ["ORIGINATOR"], False),
        ("reviewer", ["REVIEWER", "ORG_ADMIN"], True),
        ("buyer", ["TECHNICIAN"], False),
        ("transporter", ["TRANSPORTER"], False),
        ("recycler", ["RECYCLER"], False),
    ]:
        provision(db, db.get(m.User, id), id + "@test.local", PASSWORD, roles, admin)
    db.commit()
    gen.close()


def login(c, id):
    c.cookies.clear()
    r = c.post("/auth/login", json={"email": id + "@test.local", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": c.cookies.get("chakra_csrf")}


def test_cookie_auth_csrf_isolation_and_revocation(client):
    setup(client)
    assert client.get("/batteries").status_code == 401
    assert client.get("/demo/users").status_code == 404
    assert (
        client.get(
            "/batteries", headers={"Authorization": "Bearer demo-originator-local-only"}
        ).status_code
        == 401
    )
    headers = login(client, "originator")
    assert client.get("/batteries/battery-1").status_code == 200
    assert client.get("/batteries/battery-3").status_code == 403
    assert client.post("/batteries/battery-1/screen").status_code == 403
    assert (
        client.post(
            "/auth/accounts/originator/active", headers=headers, json={"active": False}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/auth/memberships",
            headers=headers,
            json={"user_id": "originator", "roles": ["REVIEWER"]},
        ).status_code
        == 403
    )
    old = client.cookies.get("chakra_session")
    assert client.post("/auth/logout", headers=headers).status_code == 200
    client.cookies.set("chakra_session", old)
    assert client.get("/batteries").status_code == 401
    assert (
        client.post(
            "/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "originator@test.local", "password": PASSWORD},
        ).status_code
        == 403
    )


def test_deactivation_reset_password_and_memberships(client):
    setup(client)
    login(client, "originator")
    old = client.cookies.get("chakra_session")
    h = login(client, "reviewer")
    assert (
        client.post(
            "/auth/accounts/originator/active", headers=h, json={"active": False}
        ).status_code
        == 200
    )
    client.cookies.set("chakra_session", old)
    assert client.get("/batteries").status_code == 401
    h = login(client, "reviewer")
    client.post("/auth/accounts/originator/active", headers=h, json={"active": True})
    token = client.post("/auth/accounts/originator/recovery", headers=h).json()["token"]
    body = {"token": token, "new_password": PASSWORD + " changed"}
    assert client.post("/auth/reset", json=body).status_code == 200
    assert client.post("/auth/reset", json=body).status_code == 400
    assert (
        client.post(
            "/auth/login", json={"email": "originator@test.local", "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login",
            json={"email": "originator@test.local", "password": PASSWORD + " changed"},
        ).status_code
        == 200
    )
    h = {"X-CSRF-Token": client.cookies.get("chakra_csrf")}
    assert (
        client.post(
            "/auth/password",
            headers=h,
            json={
                "current_password": PASSWORD + " changed",
                "new_password": PASSWORD + " final",
            },
        ).status_code
        == 200
    )
    assert client.get("/auth/profile").status_code == 401


def test_registration_pending_no_self_admin_and_role_boundaries(client):
    setup(client)
    body = {
        "email": "new@test.local",
        "password": PASSWORD,
        "name": "New user",
        "organisation_name": "New org",
    }
    assert (
        client.post("/auth/register", json={**body, "role": "REVIEWER"}).status_code
        == 422
    )
    assert client.post("/auth/register", json=body).status_code == 200
    assert (
        client.post(
            "/auth/login", json={"email": "new@test.local", "password": PASSWORD}
        ).status_code
        == 401
    )
    h = login(client, "transporter")
    assert (
        client.post(
            "/evidence/evidence-battery-1/review",
            headers=h,
            json={"status": "VERIFIED", "reason": "x", "evidence": "x"},
        ).status_code
        == 403
    )
    h = login(client, "buyer")
    assert (
        client.post(
            "/listings",
            headers=h,
            json={"asset_id": "battery-1", "expires_at": future(days=1)},
        ).status_code
        == 403
    )
    assert client.get("/auth/accounts").status_code == 403


def test_validation_does_not_echo_password_and_production_cookie_headers(client):
    setup(client)
    secret = "short-sensitive-input"
    response = client.post(
        "/auth/register",
        json={
            "email": "bad",
            "password": secret,
            "name": "X",
            "organisation_name": "Org",
        },
    )
    assert response.status_code == 422 and secret not in response.text
    r = client.post(
        "/auth/login", json={"email": "originator@test.local", "password": PASSWORD}
    )
    cookie = r.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"


def test_production_disables_synthetic_accounts_and_sets_secure_cookie(
    client, monkeypatch
):
    setup(client)
    import app.security_api as security

    monkeypatch.setattr(security, "APP_ENV", "production")
    assert (
        client.post(
            "/auth/login", json={"email": "originator@test.local", "password": PASSWORD}
        ).status_code
        == 401
    )
    # A non-synthetic administrator-like identity can receive a Secure cookie.
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    db.get(m.User, "originator").data = {"synthetic": False}
    db.get(m.Organisation, "org-fleet").synthetic = False
    db.commit()
    gen.close()
    r = client.post(
        "/auth/login", json={"email": "originator@test.local", "password": PASSWORD}
    )
    assert r.status_code == 200
    assert "Secure" in r.headers.get("set-cookie", "")


def test_platform_membership_assignment_requires_admin_and_consent(client):
    setup(client)
    body = {
        "user_id": "originator",
        "organisation_id": "org-refurb",
        "roles": ["ORIGINATOR"],
        "consent_evidence": "Synthetic independently reviewed identity and consent",
    }
    h = login(client, "originator")
    assert (
        client.post("/auth/platform-memberships", headers=h, json=body).status_code
        == 403
    )
    h = login(client, "reviewer")
    assert (
        client.post(
            "/auth/platform-memberships",
            headers=h,
            json={**body, "consent_evidence": ""},
        ).status_code
        == 422
    )
    r = client.post("/auth/platform-memberships", headers=h, json=body)
    assert r.status_code == 200, r.text
    h = login(client, "originator")
    assert (
        client.post(
            "/auth/switch",
            headers=h,
            json={"membership_id": r.json()["id"], "role": "REVIEWER"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/auth/switch",
            headers=h,
            json={"membership_id": r.json()["id"], "role": "ORIGINATOR"},
        ).status_code
        == 200
    )
    assert client.get("/batteries/battery-1").status_code == 403
