import io
import pytest
from PIL import Image
from sqlalchemy import select
from app.main import app
from app.db import get_db
from app import models as m
from app.common import future
from test_security import setup, login

pytestmark = pytest.mark.real_auth


def send(c, h, path, body=None, method="post", expected=200):
    result = getattr(c, method)(path, headers=h, json=body)
    assert result.status_code == expected, result.text
    return result.json()


def test_profile_privacy_contacts_and_persistence(client):
    setup(client)
    h = login(client, "originator")
    p = client.get("/auth/profile").json()
    id = p["organisation_id"]
    body = {
        "display_name": "Circular Fleet",
        "description": "Collecting retired batteries",
        "website": "https://example.org",
        "business_email": "office@example.org",
        "business_phone": "+91 000 000 0000",
        "primary_address": "Private depot",
        "contact_visibility": "PRIVATE",
        "regions": ["Bengaluru"],
    }
    send(client, h, f"/organisation-profiles/{id}", body, "patch")
    assert (
        client.get(f"/organisation-profiles/{id}").json()["editable_profile"][
            "description"
        ]
        == body["description"]
    )
    assert client.get("/capability-requests").json() == []
    assert "business_phone" not in str(client.get("/organisation-profiles").json())
    assert "Private depot" not in str(client.get("/network").json())
    assert (
        client.get(f"/organisation-profiles/{id}/contacts").json()["business_phone"]
        == body["business_phone"]
    )
    h2 = login(client, "originator2")
    assert client.get(f"/organisation-profiles/{id}/contacts").status_code == 403
    assert "editable_profile" not in client.get(f"/organisation-profiles/{id}").json()
    send(client, h2, f"/organisation-profiles/{id}", body, "patch", 403)
    h = login(client, "originator")
    body["contact_visibility"] = "PARTICIPANTS"
    send(client, h, f"/organisation-profiles/{id}", body, "patch")
    login(client, "originator2")
    assert (
        client.get(f"/organisation-profiles/{id}/contacts").json()["business_email"]
        == body["business_email"]
    )
    rows = client.get("/organisation-profiles").json()
    assert len(rows) == len({x["id"] for x in rows})
    assert client.get("/organisation-profiles?q=Circular").json()[0]["id"] == id


def test_multiple_roles_same_account_no_pending_privilege(client):
    setup(client)
    h = login(client, "originator")
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    count = len(db.scalars(select(m.Account)).all())
    gen.close()
    body = {
        "kind": "ROLE",
        "requested_scope": {
            "role": "TRANSPORTER",
            "description": "Fleet collection transport",
        },
    }
    result = send(client, h, "/capability-requests", body)
    request = result["request"]
    assert request["status"] == "PENDING"
    assert "48 hours" in result["message"]
    assert (
        send(client, h, "/capability-requests", body)["request"]["id"] == request["id"]
    )
    transport = {
        "name": "Fleet Logistics",
        "capacity_kg": 300,
        "center": [12.9, 77.6],
        "radius_km": 50,
    }
    send(client, h, "/transporters", transport, expected=403)
    send(
        client,
        h,
        "/auth/memberships",
        {"user_id": "originator", "roles": ["ORG_ADMIN", "ORIGINATOR", "REFURBISHER"]},
        expected=403,
    )
    send(
        client,
        h,
        "/capability-requests",
        {"kind": "ROLE", "requested_scope": {"role": "REVIEWER"}},
        expected=422,
    )
    reviewer = login(client, "reviewer")
    send(
        client,
        reviewer,
        f"/capability-requests/{request['id']}/review",
        {"decision": "APPROVED", "reason": "Reviewed organisation role and consent"},
    )
    h = login(client, "originator")
    profile = client.get("/auth/profile").json()
    assert set(profile["roles"]) == {"ORG_ADMIN", "ORIGINATOR", "TRANSPORTER"}
    assert profile["selected_role"] == "ORG_ADMIN"  # no role switching required
    send(client, h, "/transporters", transport)
    assert client.get("/batteries/battery-1").status_code == 200
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    assert len(db.scalars(select(m.Account)).all()) == count
    gen.close()


def test_request_information_approval_scope_suspension_removal_history(client):
    setup(client)
    h = login(client, "originator")
    facility = send(
        client,
        h,
        "/facilities",
        {
            "name": "Fleet workshop",
            "kind": "REVIEW",
            "lat": 12.9,
            "lng": 77.6,
            "pathway": "QUALIFIED_REVIEW",
            "chemistries": ["LFP"],
            "capacity_kg": 100,
        },
    )
    body = {
        "kind": "OPERATION",
        "facility_id": facility["id"],
        "requested_scope": {
            "operation": "ASSESSMENT",
            "chemistries": ["LFP"],
            "formats": ["PACK"],
            "capacity_kg": 100,
        },
    }
    req = send(client, h, "/capability-requests", body)["request"]
    reviewer = login(client, "reviewer")
    send(
        client,
        reviewer,
        f"/capability-requests/{req['id']}/review",
        {
            "decision": "INFORMATION_REQUESTED",
            "reason": "Describe testing procedure and equipment",
        },
    )
    h = login(client, "originator")
    send(
        client,
        h,
        f"/capability-requests/{req['id']}/respond",
        {"message": "Calibrated equipment and defined procedure reference available"},
    )
    reviewer = login(client, "reviewer")
    decision = {
        "decision": "APPROVED",
        "reason": "Reviewed defined diagnostic scope",
        "evidence": "Qualified review record 001",
        "valid_until": future(days=180),
    }
    cap = send(client, reviewer, f"/capability-requests/{req['id']}/review", decision)
    target = cap["target_id"]
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    obj = db.get(m.OperationCapability, target)
    assert obj.verified and obj.chemistries == ["LFP"]
    gen.close()
    h = login(client, "originator")
    body.update(action="MODIFY", target_id=target)
    body["requested_scope"]["chemistries"] = ["LFP", "NMC"]
    modified = send(client, h, "/capability-requests", body)["request"]
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    assert db.get(m.OperationCapability, target).chemistries == ["LFP"]
    gen.close()
    reviewer = login(client, "reviewer")
    send(
        client,
        reviewer,
        f"/capability-requests/{modified['id']}/review",
        {**decision, "decision": "REJECTED", "reason": "NMC scope is unsupported"},
    )
    send(
        client,
        reviewer,
        f"/capability-requests/{req['id']}/review",
        {"decision": "SUSPENDED", "reason": "Qualification under investigation"},
    )
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    assert not db.get(m.OperationCapability, target).verified
    assert len(db.get(m.OperationCapability, target).data["reviews"]) == 2
    gen.close()
    h = login(client, "originator")
    body["action"] = "REMOVE"
    removal = send(client, h, "/capability-requests", body)["request"]
    reviewer = login(client, "reviewer")
    send(
        client,
        reviewer,
        f"/capability-requests/{removal['id']}/review",
        {"decision": "REMOVED", "reason": "Organisation requested retirement of scope"},
    )
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    assert db.get(m.OperationCapability, target)
    assert (
        db.get(m.CapabilityRequest, removal["id"]).data["history"][-1]["action"]
        == "REMOVED"
    )
    gen.close()
    h = login(client, "originator")
    withdraw = send(
        client,
        h,
        "/capability-requests",
        {"kind": "ROLE", "requested_scope": {"role": "TECHNICIAN"}},
    )["request"]
    send(client, h, f"/capability-requests/{withdraw['id']}/withdraw", {})


def test_logo_validation_ownership_and_retrieval(client, tmp_path, monkeypatch):
    import app.organisation_api as module

    monkeypatch.setattr(module, "UPLOAD_DIR", tmp_path)
    setup(client)
    h = login(client, "originator")
    id = client.get("/auth/profile").json()["organisation_id"]

    def upload(name, content, mime):
        return client.post(
            f"/organisation-profiles/{id}/logo",
            headers=h,
            files={"file": (name, content, mime)},
        )

    assert upload("evil.svg", b"<svg/>", "image/svg+xml").status_code == 409
    assert upload("fake.png", b"not an image", "image/png").status_code == 409
    assert (
        upload("large.png", b"a" * (2 * 1024 * 1024 + 1), "image/png").status_code
        == 413
    )
    image = Image.new("RGB", (40, 40), "green")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    assert upload("../../logo.png", buffer.getvalue(), "image/png").status_code == 200
    result = client.get(f"/organisation-profiles/{id}/logo")
    assert result.status_code == 200 and result.headers["content-type"] == "image/png"
    assert len(list((tmp_path / "logos").glob("*.png"))) == 1
    h = login(client, "originator2")
    assert upload("logo.png", buffer.getvalue(), "image/png").status_code == 403
    h = login(client, "originator")
    send(client, h, f"/organisation-profiles/{id}/logo/remove", {})
    assert client.get(f"/organisation-profiles/{id}/logo").status_code == 404


def test_capability_other_organisation_and_review_access(client):
    setup(client)
    h = login(client, "originator")
    req = send(
        client,
        h,
        "/capability-requests",
        {"kind": "ROLE", "requested_scope": {"role": "TECHNICIAN"}},
    )["request"]
    send(
        client,
        h,
        f"/capability-requests/{req['id']}/review",
        {"decision": "APPROVED", "reason": "I approve myself"},
        expected=403,
    )
    h = login(client, "originator2")
    assert all(r["id"] != req["id"] for r in client.get("/capability-requests").json())
    send(client, h, f"/capability-requests/{req['id']}/withdraw", {}, expected=403)
    assert client.get("/organisation-profiles").status_code == 200
    client.cookies.clear()
    assert client.get("/organisation-profiles").status_code == 401


def test_v2_migration_binds_one_account_preserves_history(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db import Base
    from app.seed import seed
    from app.migrations import migrate
    from app.auth_bootstrap import provision
    from test_security import PASSWORD

    engine = create_engine("sqlite:///" + str(tmp_path / "v2.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        provision(
            db, db.get(m.User, "buyer"), "buyer@test.local", PASSWORD, ["REFURBISHER"]
        )
        provision(
            db,
            db.get(m.User, "technician"),
            "technician@test.local",
            PASSWORD,
            ["TECHNICIAN"],
        )
        db.commit()
        before = {x.id for x in db.scalars(select(m.BatteryAsset))}
        db.query(m.OrganisationAccount).delete()
        db.query(m.SchemaVersion).delete()
        db.add(m.SchemaVersion(version=2))
        db.commit()
    m.OrganisationAccount.__table__.drop(engine)
    m.CapabilityRequest.__table__.drop(engine)
    migrate(engine)
    migrate(engine)
    with Session(engine) as db:
        assert len(db.scalars(select(m.Account)).all()) == 2
        assert (
            len(
                db.scalars(
                    select(m.OrganisationAccount).where(
                        m.OrganisationAccount.organisation_id == "org-refurb"
                    )
                ).all()
            )
            == 1
        )
        assert {x.id for x in db.scalars(select(m.BatteryAsset))} == before
        assert list(db.scalars(select(m.SchemaVersion.version))) == [4]
    engine.dispose()


def test_registration_duplicate_identity_and_reviewed_identity_edit(client):
    setup(client)
    response = client.post(
        "/auth/register",
        json={
            "name": "Primary contact",
            "organisation_name": " SETU FLEET COLLECTIVE ",
            "email": "different@test.local",
            "password": "Strong new account password 2026",
        },
    )
    assert response.status_code == 409
    h = login(client, "originator")
    request = send(
        client,
        h,
        "/capability-requests",
        {
            "kind": "IDENTITY",
            "action": "MODIFY",
            "requested_scope": {"official_name": "Setu Fleet Circularity"},
        },
    )["request"]
    assert (
        client.get("/organisation-profiles/org-fleet").json()["name"]
        == "Setu Fleet Collective"
    )
    h = login(client, "reviewer")
    send(
        client,
        h,
        f"/capability-requests/{request['id']}/review",
        {
            "decision": "APPROVED",
            "reason": "Reviewed identity amendment",
            "evidence": "Identity review reference",
            "valid_until": future(days=180),
        },
    )
    assert (
        client.get("/organisation-profiles/org-fleet").json()["name"]
        == "Setu Fleet Circularity"
    )
