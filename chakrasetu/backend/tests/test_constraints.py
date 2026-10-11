from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db import Base
from app import models as m
from app.seed import seed
from app.common import future
from app.services.matching import (
    facility_check,
    transporter_check,
    active_reservations,
    generate_routes,
)
from app.services.intake import screen_result
from app.enums import FLAGS
from test_intake_commercial import auth, agreed
from test_logistics import routes, quoted
import pytest


def test_unknown_and_missing_are_not_safe(client):
    r = client.get("/batteries/battery-2", headers=auth("originator"))
    assert r.json()["chemistry"] == "UNKNOWN" and r.json()["mass_kg"] is None
    r = client.post(
        "/batteries",
        headers=auth("originator"),
        json={
            "internal_id": "bad",
            "owner_org_id": "org-fleet",
            "custodian_org_id": "org-fleet",
            "mass_kg": 0,
        },
    )
    assert r.status_code == 422
    r = client.post(
        "/batteries",
        headers=auth("originator"),
        json={
            "internal_id": "incomplete",
            "registration_title": "Existing regression battery",
            "pbs": "L3",
            "address": "Bengaluru",
            "lat": 12.97,
            "lng": 77.59,
            "owner_org_id": "org-fleet",
            "custodian_org_id": "org-fleet",
        },
    )
    id = r.json()["id"]
    screen = client.post(f"/batteries/{id}/screen", headers=auth("originator")).json()
    assert screen["state"] == "REVIEW_REQUIRED"
    assert screen["screen"] == "OWNER_REPORTED"


def test_expiry_capacity_and_unknown_gates():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        a = db.get(m.BatteryAsset, "battery-1")
        f = db.get(m.Facility, "fac-refurb")
        cap = db.get(m.FacilityCapability, "fac-refurb-REPAIR_REFURBISHMENT")
        assert facility_check(db, a, f, "REPAIR_REFURBISHMENT")["eligible"]
        f.valid_until = future(minutes=-1)
        assert "REGISTRATION_INVALID_OR_EXPIRED" in [
            r["code"]
            for r in facility_check(db, a, f, "REPAIR_REFURBISHMENT")["reasons"]
        ]
        f.valid_until = future(days=365)
        cap.available_kg = 30
        assert "CAPACITY_INSUFFICIENT" in [
            r["code"]
            for r in facility_check(db, a, f, "REPAIR_REFURBISHMENT")["reasons"]
        ]
        cap.available_kg = 1200
        a.chemistry = "UNKNOWN"
        a.mass_kg = None
        reasons = facility_check(db, a, f, "REPAIR_REFURBISHMENT")["reasons"]
        assert {"CHEMISTRY_NOT_ACCEPTED", "VALUE_UNKNOWN"} <= {
            r["code"] for r in reasons
        }


def test_expired_and_released_holds_free_capacity():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        # FK constraints remain off on this isolated domain unit DB; reservation semantics independent of commercial API.
        for status, expiry, mass in [
            ("HELD", future(minutes=10), 10),
            ("HELD", future(minutes=-1), 20),
            ("RELEASED", future(minutes=10), 30),
            ("COMMITTED", future(minutes=-1), 40),
        ]:
            db.add(
                m.CapacityReservation(
                    transaction_id="unit",
                    resource_type="CAPABILITY",
                    resource_id="unit",
                    mass_kg=mass,
                    status=status,
                    starts_at=future(days=1),
                    ends_at=future(days=3),
                    expires_at=expiry,
                )
            )
        db.flush()
        assert (
            active_reservations(
                db, "CAPABILITY", "unit", future(days=1), future(days=3)
            )
            == 50
        )


def test_unauthorised_custody_and_quotes(client):
    tx = agreed(client)
    p = next(p for p in routes(client, tx) if not p["hub_id"])
    q = quoted(client, tx, p)
    assert (
        client.post(
            "/quotes/" + q["id"] + "/accept", headers=auth("originator")
        ).status_code
        == 403
    )
    assert (
        client.get("/audit/battery/battery-3", headers=auth("originator")).status_code
        == 403
    )
    assert (
        client.get(
            "/batteries/battery-1", headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/exceptions/does-not-exist/resolve",
            headers=auth("originator"),
            json={"resolution": "bad", "evidence": "bad"},
        ).status_code
        == 403
    )


def test_upload_type_and_document_privacy(client):
    r = client.post(
        "/batteries/battery-1/evidence",
        headers=auth("originator"),
        data={"kind": "PHOTO"},
        files={"file": ("bad.png", b"not an image", "image/png")},
    )
    assert r.status_code == 422
    r = client.post(
        "/batteries/battery-1/evidence",
        headers=auth("originator"),
        data={"kind": "TRANSFER_AUTHORITY", "reference": "New authority version"},
    )
    assert r.status_code == 200 and r.json()["version"] == 2
    assert (
        client.get(
            "/evidence/" + r.json()["id"] + "/download", headers=auth("originator2")
        ).status_code
        == 403
    )


def test_incomplete_cost_ranking_deterministic_and_not_zero():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        a = db.get(m.BatteryAsset, "battery-1")
        listing = m.Listing(
            asset_id=a.id, seller_org_id="org-fleet", expires_at=future(days=5)
        )
        db.add(listing)
        db.flush()
        offer = m.Offer(
            listing_id=listing.id,
            buyer_org_id="org-refurb",
            facility_id="fac-refurb",
            pathway="REPAIR_REFURBISHMENT",
            price_paise=2000000,
            expires_at=future(days=5),
        )
        db.add(offer)
        db.flush()
        tx = m.SaleTransaction(
            offer_id=offer.id,
            asset_id=a.id,
            seller_org_id="org-fleet",
            buyer_org_id="org-refurb",
            facility_id="fac-refurb",
            pathway="REPAIR_REFURBISHMENT",
            status="AGREED_PENDING_LOGISTICS",
        )
        db.add(tx)
        db.flush()
        a.state = "AGREED"
        t = db.get(m.TransporterProfile, "trans-1")
        t.data = {**t.data, "rate_paise_per_km": None, "rate_source": "UNKNOWN"}
        user = db.get(m.User, "originator")
        one = generate_routes(db, tx, user)["candidates"]
        two = generate_routes(db, tx, user)["candidates"]
        assert all(p["estimated_cost_paise"] is None for p in one)
        assert all(p["data"]["ranking"]["components"]["cost"] is None for p in one)
        assert [(p["hub_id"], p["score"]) for p in one] == [
            (p["hub_id"], p["score"]) for p in two
        ]
        db.get(m.Facility, "fac-hub").active = False
        single = generate_routes(db, tx, user)["candidates"]
        assert (
            len(single) == 1 and single[0]["data"]["ranking"]["components"]["time"] == 0
        )
