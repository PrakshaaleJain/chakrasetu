from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app import models as m
from app.db import Base, get_db
from app.main import app
from app.seed import seed
from app.enums import FLAGS
from app.common import future
from test_intake_commercial import auth, agreed
from test_logistics import routes, quoted


def second_transaction(c):
    body = {
        "internal_id": "race-second",
        "registration_title": "Existing regression battery",
        "pbs": "L1",
        "collection_availability": "YES",
        "address": "Bengaluru",
        "lat": 12.97,
        "lng": 77.59,
        "owner_org_id": "org-fleet",
        "custodian_org_id": "org-fleet",
        "flags": {f: "NO" for f in FLAGS},
        "declaration": True,
        "authority_confirmed": True,
        "chemistry": "LFP",
        "form": "PACK",
        "condition": "DEGRADED",
        "mass_kg": 42,
        "lat": 12.97,
        "lng": 77.59,
        "window_start": future(days=1),
        "window_end": future(days=3),
    }
    r = c.post("/batteries", headers=auth("originator"), json=body)
    assert r.status_code == 200, r.text
    id = r.json()["id"]
    e = c.post(
        "/batteries/" + id + "/evidence",
        headers=auth("originator"),
        data={
            "kind": "TRANSFER_AUTHORITY",
            "reference": "Synthetic authority reference",
        },
    ).json()
    c.post(
        "/evidence/" + e["id"] + "/review",
        headers=auth("reviewer"),
        json={
            "status": "VERIFIED",
            "reason": "Mock authority review",
            "evidence": "Synthetic reference",
        },
    )
    assert (
        c.post(
            "/batteries/" + id + "/registration-review",
            headers=auth("reviewer"),
            json={
                "decision": "APPROVED",
                "reason": "Synthetic registration information reviewed",
            },
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/batteries/" + id + "/confirm-transfer-authority",
            headers=auth("originator"),
        ).status_code
        == 200
    )
    c.post("/batteries/" + id + "/screen", headers=auth("originator"))
    l = c.post(
        "/listings",
        headers=auth("originator"),
        json={"asset_id": id, "expires_at": future(days=4)},
    ).json()
    o = c.post(
        "/listings/" + l["id"] + "/offers",
        headers=auth("buyer"),
        json={
            "facility_id": "fac-refurb",
            "pathway": "REPAIR_REFURBISHMENT",
            "price_paise": 2000000,
            "payer_org_id": "org-refurb",
            "budget_paise": 300000,
            "expires_at": future(days=3),
            "acceptance_criteria": "Matches evidence",
        },
    ).json()
    r = c.post(
        "/offers/" + o["id"] + "/accept",
        headers={**auth("originator"), "Idempotency-Key": uuid4().hex},
    )
    assert r.status_code == 200, r.text
    tx = r.json()
    for actor in ["originator", "buyer"]:
        c.post(
            "/transactions/" + tx["id"] + "/confirm",
            headers=auth(actor),
            json={"version": 1},
        )
    return tx


def test_two_requests_cannot_overbook_and_expiry_releases(tmp_path):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "race.db"),
        connect_args={"check_same_thread": False, "timeout": 20},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        cap = db.get(m.FacilityCapability, "fac-refurb-REPAIR_REFURBISHMENT")
        cap.capacity_kg = 60
        cap.available_kg = 60
        db.commit()

    def override():
        with Session(engine, expire_on_commit=False) as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = override
    try:
        c = TestClient(app)
        one = agreed(c)
        two = second_transaction(c)
        plans = []
        for tx in [one, two]:
            p = next(p for p in routes(c, tx) if not p["hub_id"])
            plans.append(p)
            q = quoted(c, tx, p)
            r = c.post(
                "/quotes/" + q["id"] + "/accept",
                headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
            )
            assert r.status_code == 200, r.text

        def hold(i):
            return c.post(
                "/transactions/" + [one, two][i]["id"] + "/reserve-capacity",
                headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
                json={"route_id": plans[i]["id"]},
            )

        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(hold, [0, 1]))
        assert sorted(r.status_code for r in results) == [200, 409]
        with Session(engine) as db:
            holds = db.scalars(
                select(m.CapacityReservation).where(
                    m.CapacityReservation.resource_id
                    == "fac-refurb-REPAIR_REFURBISHMENT",
                    m.CapacityReservation.status == "HELD",
                )
            ).all()
            assert sum(h.mass_kg for h in holds) == 42
            for r in db.scalars(
                select(m.CapacityReservation).where(
                    m.CapacityReservation.status == "HELD"
                )
            ).all():
                r.expires_at = future(minutes=-1)
            db.commit()
        failed = next(i for i, r in enumerate(results) if r.status_code == 409)
        assert hold(failed).status_code == 200
        engine.dispose()
        with Session(engine) as restarted:
            assert (
                restarted.scalar(
                    select(m.BatteryAsset).where(
                        m.BatteryAsset.internal_id == "race-second"
                    )
                ).mass_kg
                == 42
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
