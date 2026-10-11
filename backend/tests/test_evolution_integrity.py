import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app import models as m
from app.db import Base, get_db
from app.main import app
from app.migrations import migrate
from app.seed import seed
from app.common import future
from app.auth_bootstrap import provision
from test_security import setup, login, PASSWORD
from test_circularity import prepare, post, review, output, complete

pytestmark = pytest.mark.real_auth


def test_v1_additive_migration_preserves_battery_and_disables_legacy_tokens(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "migration.db"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        before = db.get(m.BatteryAsset, "battery-1").internal_id
        for version in db.scalars(select(m.SchemaVersion)).all():
            db.delete(version)
        db.add(m.SchemaVersion(version=1))
        db.commit()
    migrate(engine)
    migrate(engine)
    with Session(engine) as db:
        assert db.get(m.BatteryAsset, "battery-1").internal_id == before
        assert list(db.scalars(select(m.SchemaVersion.version))) == [4]
        assert len(db.scalars(select(m.Organisation)).all()) == 15
        assert not db.scalars(select(m.Account)).all()
    engine.dispose()


def test_multi_organization_switch_expiry_and_membership_revocation(client):
    setup(client)
    h = login(client, "reviewer")
    r = client.post(
        "/auth/memberships",
        headers=h,
        json={"user_id": "originator", "roles": ["ORIGINATOR"], "active": True},
    )
    assert r.status_code == 200, r.text
    new_id = r.json()["id"]
    h = login(client, "originator")
    assert client.get("/batteries/battery-1").status_code == 200
    assert (
        client.post(
            "/auth/switch",
            headers=h,
            json={"membership_id": new_id, "role": "REVIEWER"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/auth/switch",
            headers=h,
            json={"membership_id": new_id, "role": "ORIGINATOR"},
        ).status_code
        == 200
    )
    assert client.get("/batteries/battery-1").status_code == 403
    assert (
        client.post(
            "/auth/memberships",
            headers=h,
            json={"user_id": "originator", "roles": ["ORG_ADMIN"], "active": True},
        ).status_code
        == 403
    )
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    for s in db.scalars(
        select(m.AuthSession).where(m.AuthSession.user_id == "originator")
    ):
        s.expires_at = future(minutes=-1)
    db.commit()
    gen.close()
    assert client.get("/batteries").status_code == 401


def test_auth_endpoint_throttle_and_inactive_organization(client):
    setup(client)
    for _ in range(10):
        assert (
            client.post(
                "/auth/login", json={"email": "wrong@test.local", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/auth/login", json={"email": "wrong@test.local", "password": "wrong"}
        ).status_code
        == 429
    )
    h = login(client, "originator")
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    db.get(m.Organisation, "org-fleet").active = False
    db.commit()
    gen.close()
    assert client.get("/batteries").status_code == 401


def test_many_to_one_blending_is_normalized_and_double_processing_blocked(client):
    prepare(client)
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    for id, mass in [("blend-a", 10), ("blend-b", 20)]:
        db.add(
            m.CircularItem(
                id=id,
                identifier=id,
                kind="MATERIAL",
                owner_org_id="org-refiner",
                custodian_org_id="org-refiner",
                facility_id="fac-refiner",
                mass_kg=mass,
                state="AVAILABLE",
                data={
                    "category": "BLACK_MASS",
                    "synthetic": True,
                    "receiving_acceptance_evidence": "Synthetic already-accepted incoming lot",
                },
            )
        )
    db.commit()
    gen.close()
    body = {
        "facility_id": "fac-refiner",
        "operation": "REFINING",
        "item_ids": ["blend-a", "blend-b"],
        "procedure": "Synthetic blend processing procedure",
        "evidence": "Synthetic blending and title agreement",
    }
    j = post(client, "refiner", "/jobs", body)
    other = post(client, "refiner", "/jobs", body)
    for job in [j, other]:
        post(client, "refiner", "/jobs/" + job["id"] + "/authorize", review())
    post(client, "refiner", "/jobs/" + j["id"] + "/start")
    post(client, "refiner", "/jobs/" + other["id"] + "/start", expected=409)
    result = complete(
        client,
        j,
        "refiner",
        [output("blended-output", "MATERIAL", 28, "REFINED_LITHIUM")],
        2,
    )
    post(client, "reviewer", "/jobs/" + j["id"] + "/review", review())
    login(client, "refiner")
    trace = client.get(
        "/circularity/items/" + result["outputs"][0]["item_id"] + "/trace"
    ).json()
    assert {x["input_item_id"] for x in trace["links"]} == {"blend-a", "blend-b"}
    assert all(
        x["allocation"] == "BLENDED_INPUTS_NO_EXACT_ATOM_ALLOCATION_CLAIM"
        for x in trace["links"]
    )
    post(
        client,
        "recycler",
        "/jobs/" + j["id"] + "/complete",
        {
            "outputs": [output("unrelated", "MATERIAL", 1, "COPPER")],
            "process_evidence": "Unauthorized attempt",
            "measured_loss_kg": 29,
            "loss_evidence": "Unauthorized attempt",
        },
        expected=403,
    )


def test_technician_cannot_amend_another_organizations_terms(client):
    setup(client)
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    listing = m.Listing(
        asset_id="battery-1", seller_org_id="org-fleet", expires_at=future(days=2)
    )
    db.add(listing)
    db.flush()
    offer = m.Offer(
        listing_id=listing.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway="REPAIR_REFURBISHMENT",
        price_paise=100000,
        expires_at=future(days=2),
    )
    db.add(offer)
    db.flush()
    tx = m.SaleTransaction(
        offer_id=offer.id,
        asset_id="battery-1",
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway="REPAIR_REFURBISHMENT",
    )
    db.add(tx)
    db.flush()
    id = tx.id
    db.commit()
    gen.close()
    h = login(client, "buyer")  # this test account is assigned TECHNICIAN only
    assert (
        client.post(
            "/transactions/" + id + "/amend",
            headers=h,
            json={
                "budget_paise": 50000,
                "reason": "Not authorized",
                "evidence": "Test evidence",
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/transactions/" + id + "/confirm", headers=h, json={"version": 1}
        ).status_code
        == 403
    )


def test_battery_and_downstream_reservations_share_transporter_capacity(client):
    prepare(client)
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    item = m.CircularItem(
        id="capacity-product",
        identifier="capacity-product",
        kind="PRODUCT",
        owner_org_id="org-customer",
        custodian_org_id="org-customer",
        facility_id="fac-customer",
        mass_kg=20,
        state="ALLOCATED",
        data={"category": "SECOND_LIFE_SYSTEM", "synthetic": True},
    )
    db.add(item)
    db.flush()
    h = m.DownstreamHandoff(
        id="capacity-handoff",
        item_id=item.id,
        seller_org_id="org-customer",
        buyer_org_id="org-second",
        receiver_facility_id="fac-second",
        transporter_id="trans-1",
        state="BOOKED",
        data={
            "window_start": future(days=1),
            "window_end": future(days=3),
            "route": {"stops": ["fac-customer", "fac-second"]},
        },
    )
    db.add(h)
    db.flush()
    db.add(
        m.HandoffAllocation(
            handoff_id=h.id,
            resource_type="TRANSPORTER",
            resource_id="trans-1",
            mass_kg=20,
            starts_at=future(days=1),
            ends_at=future(days=3),
        )
    )
    db.flush()
    from app.services.matching import available

    assert (
        available(db, "TRANSPORTER", "trans-1", 60, future(days=1), future(days=2))
        == 40
    )
    item.state = "HOLD"
    db.commit()
    gen.close()
    post(
        client,
        "customer",
        "/handoffs/capacity-handoff/events",
        {
            "state": "PICKED_UP",
            "physical": True,
            "evidence": "Cannot bypass a new incident hold",
        },
        expected=409,
    )
