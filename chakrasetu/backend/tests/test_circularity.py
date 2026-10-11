import pytest
from sqlalchemy import select
from app import models as m
from app.db import get_db
from app.main import app
from app.auth_bootstrap import provision
from app.common import future
from test_security import PASSWORD, login

pytestmark = pytest.mark.real_auth


def prepare(client, mode="recycle"):
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    actors = [
        ("originator", ["ORIGINATOR"]),
        ("buyer", ["REFURBISHER", "SECOND_LIFE"]),
        ("recycler", ["RECYCLER"]),
        ("refiner", ["REFINER"]),
        ("manufacturer", ["MANUFACTURER"]),
        ("customer", ["CUSTOMER"]),
        ("reviewer", ["REVIEWER"]),
        ("transporter", ["TRANSPORTER"]),
    ]
    for id, roles in actors:
        provision(db, db.get(m.User, id), id + "@test.local", PASSWORD, roles)
    tech = m.User(
        id="tech",
        organisation_id="org-refurb",
        name="Test technician",
        role="TECHNICIAN",
        token_hash="disabled",
        data={},
    )
    db.add(tech)
    db.flush()
    provision(db, tech, "tech@test.local", PASSWORD, ["TECHNICIAN"])
    asset = db.get(m.BatteryAsset, "battery-1")
    asset.current_holder_org_id = asset.custodian_org_id = (
        "org-recycle" if mode == "recycle" else "org-refurb"
    )
    asset.state = "RECEIVED"
    db.commit()
    gen.close()


def post(c, actor, path, body=None, expected=200, key=None):
    from uuid import uuid4

    if not hasattr(c, "actor_sessions"):
        c.actor_sessions = {}
    if actor not in c.actor_sessions:
        h = login(c, actor)
        c.actor_sessions[actor] = (dict(c.cookies), h)
    cookies, h = c.actor_sessions[actor]
    c.cookies.clear()
    c.cookies.update(cookies)
    h = {**h, "Idempotency-Key": key or uuid4().hex}
    r = c.post("/circularity" + path, headers=h, json=body or {})
    assert r.status_code == expected, r.text
    return r.json()


def review():
    return {
        "accepted": True,
        "evidence": "Synthetic reviewed operation evidence",
        "reason": "Documentary scope reviewed; no safety certification",
        "valid_until": future(days=5),
    }


def imported(c, actor, asset="battery-1", facility="fac-recycle"):
    return post(
        c,
        actor,
        "/items/import-battery",
        {
            "asset_id": asset,
            "facility_id": facility,
            "receipt_evidence": "Recorded physical receipt evidence",
        },
    )


def job(c, actor, item, facility="fac-recycle", operation="RECYCLING", key=None):
    return post(
        c,
        actor,
        "/jobs",
        {
            "facility_id": facility,
            "operation": operation,
            "item_ids": [item["id"]],
            "procedure": "Documented processing procedure",
            "evidence": "Input and output ownership terms evidence",
        },
        key=key,
    )


def authorize_start(c, j, actor):
    post(c, "originator", "/jobs/" + j["id"] + "/authorize", review())
    return post(c, actor, "/jobs/" + j["id"] + "/start")


def complete(c, j, actor, outputs, loss=0, key=None):
    return post(
        c,
        actor,
        "/jobs/" + j["id"] + "/complete",
        {
            "outputs": outputs,
            "process_evidence": "Synthetic technician completion record",
            "measured_loss_kg": loss,
            "loss_evidence": "Measured documented process loss",
        },
        key=key,
    )


def output(identifier, kind, mass, category):
    return {
        "identifier": identifier,
        "kind": kind,
        "mass_kg": mass,
        "category": category,
        "specification": "Defined receiving specification with documented measurements",
        "evidence": "Synthetic measured output quality evidence",
        "chemistry": "LFP",
    }


def test_processing_split_lineage_permissions_mass_balance_and_idempotency(client):
    prepare(client)
    item = imported(client, "recycler")
    j = job(client, "recycler", item, key="create-recycling")
    post(client, "recycler", "/jobs/" + j["id"] + "/start", expected=409)
    authorize_start(client, j, "recycler")
    complete_body = {
        "outputs": [output("black-one", "MATERIAL", 20, "BLACK_MASS")],
        "process_evidence": "Report evidence",
        "measured_loss_kg": 0,
        "loss_evidence": "Loss evidence",
    }
    post(
        client,
        "recycler",
        "/jobs/" + j["id"] + "/complete",
        complete_body,
        expected=409,
    )
    outs = [
        output("black-one", "MATERIAL", 20, "BLACK_MASS"),
        output("copper-one", "MATERIAL", 10, "COPPER"),
        output("aluminium-one", "MATERIAL", 10, "ALUMINIUM"),
    ]
    done = complete(client, j, "recycler", outs, 2, key="completion-once")
    again = complete(client, j, "recycler", outs, 2, key="completion-once")
    assert again == done and len(done["outputs"]) == 3
    post(client, "reviewer", "/jobs/" + j["id"] + "/review", review())
    login(client, "recycler")
    lots = client.get("/circularity/material-lots").json()
    assert len(lots) == 3
    trace = client.get(
        "/circularity/items/" + done["outputs"][0]["item_id"] + "/trace"
    ).json()
    assert len(trace["links"]) == 1
    login(client, "originator")
    forward = client.get(
        "/circularity/items/" + item["id"] + "/trace?direction=DESCENDANTS"
    ).json()
    assert len(forward["links"]) == 3
    assert (
        all(
            x["data"].get("restricted")
            for x in forward["items"]
            if x["id"] != item["id"]
        )
        and trace["items"][1]["battery_id"] == "battery-1"
    )
    login(client, "originator2") if False else None
    login(client, "customer")
    assert client.get("/circularity/items/" + item["id"] + "/trace").status_code == 403
    post(
        client,
        "customer",
        "/jobs/" + j["id"] + "/complete",
        complete_body,
        expected=403,
    )
    post(
        client,
        "recycler",
        "/capabilities/fac-refiner-REFINING/review",
        review(),
        expected=403,
    )
    login(client, "recycler")
    assert len(client.get("/circularity/recycling-batches").json()[0]["inputs"]) == 1


def test_downstream_quote_budget_physical_custody_settlement_and_blending(client):
    prepare(client)
    item = imported(client, "recycler")
    j = job(client, "recycler", item)
    authorize_start(client, j, "recycler")
    done = complete(
        client, j, "recycler", [output("black-lot", "MATERIAL", 40, "BLACK_MASS")], 2
    )
    post(client, "reviewer", "/jobs/" + j["id"] + "/review", review())
    lot_id = done["outputs"][0]["item_id"]
    b = {
        "item_id": lot_id,
        "receiver_facility_id": "fac-refiner",
        "price_paise": 100000,
        "payer_org_id": "org-refiner",
        "budget_paise": 50000,
        "acceptance_specification": "Reviewed incoming black mass composition specification",
        "evidence": "Synthetic signed offtake scope",
        "window_start": future(days=1),
        "window_end": future(days=2),
    }
    h = post(client, "recycler", "/handoffs", b)
    for actor in ["recycler", "refiner"]:
        post(client, actor, "/handoffs/" + h["id"] + "/confirm", {"version": 1})
    q = {
        "transporter_id": "trans-1",
        "total_paise": 60000,
        "expires_at": future(days=1),
        "evidence": "Synthetic carrier-submitted all-inclusive quote",
        "acceptance_specification_confirmed": True,
    }
    post(client, "transporter", "/handoffs/" + h["id"] + "/quote", q)
    post(client, "refiner", "/handoffs/" + h["id"] + "/book", expected=409)
    post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/amend",
        {**b, "budget_paise": 70000},
    )
    post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/confirm",
        {"version": 1},
        expected=409,
    )
    for actor in ["recycler", "refiner"]:
        post(client, actor, "/handoffs/" + h["id"] + "/confirm", {"version": 2})
    post(client, "transporter", "/handoffs/" + h["id"] + "/quote", q)
    booked = post(client, "refiner", "/handoffs/" + h["id"] + "/book", key="book-once")
    again = post(client, "refiner", "/handoffs/" + h["id"] + "/book", key="book-once")
    assert again == booked
    pickup = {
        "state": "PICKED_UP",
        "physical": True,
        "evidence": "Physical custody handover evidence",
    }
    first = post(client, "recycler", "/handoffs/" + h["id"] + "/events", pickup)
    assert (
        first["pending_confirmation"]
        and first["item"]["custodian_org_id"] == "org-recycle"
    )
    second = post(
        client,
        "transporter",
        "/handoffs/" + h["id"] + "/events",
        pickup,
        key="pickup-once",
    )
    assert second["item"]["custodian_org_id"] == "org-trans"
    assert (
        post(
            client,
            "transporter",
            "/handoffs/" + h["id"] + "/events",
            pickup,
            key="pickup-once",
        )
        == second
    )
    post(
        client,
        "transporter",
        "/handoffs/" + h["id"] + "/events",
        {"state": "ARRIVED", "evidence": "Physical arrival report"},
    )
    disputed = post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/events",
        {
            "state": "RECEIVED",
            "physical": True,
            "condition_matches": False,
            "evidence": "Condition discrepancy evidence",
        },
    )
    assert (
        disputed["state"] == "DISPUTED"
        and disputed["item"]["custodian_org_id"] == "org-trans"
    )
    post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/settlement",
        {"status": "REPORTED", "evidence": "Synthetic payment record"},
        expected=409,
    )
    post(client, "reviewer", "/handoffs/" + h["id"] + "/resolve", review())
    received = post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/events",
        {
            "state": "RECEIVED",
            "physical": True,
            "evidence": "Reconciled receiving inspection acceptance",
        },
    )
    assert received["item"]["owner_org_id"] == "org-refiner"
    post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/events",
        {"state": "CLOSED", "evidence": "Requested closure evidence"},
        expected=409,
    )
    post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/settlement",
        {"status": "REPORTED", "evidence": "Synthetic payer reported payment"},
    )
    post(
        client,
        "recycler",
        "/handoffs/" + h["id"] + "/settlement",
        {"status": "CONFIRMED", "evidence": "Synthetic seller confirmed payment"},
    )
    closed = post(
        client,
        "refiner",
        "/handoffs/" + h["id"] + "/events",
        {"state": "CLOSED", "evidence": "Documented receipt and settlement closure"},
    )
    assert closed["state"] == "CLOSED" and len(closed["custody"]) == 2
    # Refiner consumes the received lot; previous owner has no power over its new job.
    rj = job(client, "refiner", received["item"], "fac-refiner", "REFINING")
    post(client, "recycler", "/jobs/" + rj["id"] + "/authorize", review(), expected=403)
    post(client, "refiner", "/jobs/" + rj["id"] + "/authorize", review())
    post(client, "refiner", "/jobs/" + rj["id"] + "/start")
    refined = complete(
        client,
        rj,
        "refiner",
        [output("refined-lot", "MATERIAL", 35, "REFINED_LITHIUM")],
        5,
    )
    post(client, "reviewer", "/jobs/" + rj["id"] + "/review", review())
    login(client, "refiner")
    trace = client.get(
        "/circularity/items/" + refined["outputs"][0]["item_id"] + "/trace"
    ).json()
    assert len(trace["links"]) == 2


def test_assessment_immutable_revision_and_product_lifecycle(client):
    prepare(client, "refurb")
    assessment = post(
        client,
        "buyer",
        "/assessments",
        {
            "asset_id": "battery-1",
            "facility_id": "fac-refurb",
            "intended_operation": "REFURBISHMENT",
            "procedure": "Qualified documented pack testing procedure",
        },
    )
    report = {
        "observations": "Evidence-recorded technical findings",
        "measurements": [
            {
                "name": "capacity",
                "value": None,
                "unit": "Ah",
                "method": "Missing measurement explicitly recorded",
            }
        ],
        "evidence": "Synthetic technician test record",
        "equipment_reference": "Synthetic calibrated equipment reference",
        "outcome": "SUITABLE_FOR_DEFINED_OPERATION",
        "limitations": "Only valid against the declared specification; no universal suitability claim",
        "acceptance_specification": "Defined stationary energy product incoming requirements",
    }
    post(
        client,
        "transporter",
        "/assessments/" + assessment["id"] + "/submit",
        report,
        expected=403,
    )
    post(client, "tech", "/assessments/" + assessment["id"] + "/submit", report)
    post(
        client,
        "tech",
        "/assessments/" + assessment["id"] + "/submit",
        report,
        expected=409,
    )
    post(client, "reviewer", "/assessments/" + assessment["id"] + "/review", review())
    item = imported(client, "buyer", facility="fac-refurb")
    j = job(client, "buyer", item, "fac-refurb", "REFURBISHMENT")
    authorize_start(client, j, "buyer")
    completed = complete(
        client,
        j,
        "buyer",
        [output("second-life-system", "PRODUCT", 40, "SECOND_LIFE_SYSTEM")],
        2,
    )
    post(client, "reviewer", "/jobs/" + j["id"] + "/review", review())
    login(client, "buyer")
    product = client.get("/circularity/products").json()[0]
    post(
        client,
        "buyer",
        "/products/" + product["id"] + "/events",
        {
            "event": "ACCEPT",
            "evidence": "Application-specific documented product acceptance",
            "notes": "Accepted against this system specification",
        },
    )
    post(
        client,
        "buyer",
        "/products/" + product["id"] + "/events",
        {
            "event": "DEPLOY",
            "evidence": "Installation report",
            "notes": "Installation must be at actual receiving customer",
            "customer_org_id": "org-customer",
        },
        expected=409,
    )


def test_pathway_explanation_unknown_costs_and_safety_holds(client):
    prepare(client)
    h = login(client, "originator")
    no_cost = post(
        client, "originator", "/batteries/battery-1/pathways", {"inputs": {}}
    )
    assert no_cost["recommended_id"] is None and no_cost["candidates"]
    assert all(x["economics"]["net_paise"] is None for x in no_cost["candidates"])
    econ = {
        "terminal_revenue_paise": 500000,
        "acquisition_paise": 100000,
        "assessment_paise": 20000,
        "processing_paise": 50000,
        "transport_paise": 30000,
        "overhead_paise": 10000,
        "source": "SYNTHETIC",
        "reference": "Explicit synthetic whole-pathway assumptions",
    }
    result = post(
        client,
        "originator",
        "/batteries/battery-1/pathways",
        {"inputs": {"RECOVER_MATERIALS": econ}},
    )
    assert (
        result["recommended_id"]
        and next(
            x for x in result["candidates"] if x["id"] == result["recommended_id"]
        )["economics"]["net_paise"]
        == 290000
    )
    login(client, "originator")
    assert len(client.get("/circularity/batteries/battery-1/pathways").json()) == 2
    unknown = post(
        client,
        "originator",
        "/batteries/battery-2/pathways",
        {"inputs": {"RECOVER_MATERIALS": econ}},
    )
    assert not unknown["candidates"] and any(
        "CHEMISTRY_UNSUPPORTED" == r["code"]
        for x in unknown["rejected"]
        for r in x["reasons"]
    )
    held = post(
        client,
        "reviewer",
        "/batteries/battery-3/pathways",
        {"inputs": {"RECOVER_MATERIALS": econ}},
    )
    assert not held["candidates"]


def test_takeback_requires_same_terms_from_both_parties_and_incident_hold(client):
    prepare(client, "refurb")
    # Fixture is a physically received, reviewed system, independent of processing tests.
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    item = m.CircularItem(
        id="contract-product",
        identifier="contract-product",
        kind="PRODUCT",
        owner_org_id="org-customer",
        custodian_org_id="org-customer",
        facility_id="fac-customer",
        mass_kg=20,
        state="AVAILABLE",
        data={"category": "SECOND_LIFE_SYSTEM", "synthetic": True},
    )
    db.add(item)
    db.flush()
    j = m.TransformationJob(
        id="contract-job",
        facility_id="fac-refurb",
        operator_id="buyer",
        operation="INTEGRATION",
        state="ACCEPTED",
        data={},
    )
    db.add(j)
    db.flush()
    p = m.SecondLifeProduct(
        id="contract-system",
        item_id=item.id,
        source_job_id=j.id,
        integrator_org_id="org-refurb",
        intended_application="SECOND_LIFE_SYSTEM",
        state="ACCEPTED",
        customer_org_id="org-customer",
        data={},
    )
    db.add(p)
    db.commit()
    gen.close()
    body = {
        "event": "TAKE_BACK_CONTRACT",
        "evidence": "Synthetic integrator contract evidence",
        "notes": "Same explicit return obligations, collection responsibilities and end date",
        "customer_org_id": "org-customer",
    }
    first = post(client, "buyer", "/products/contract-system/events", body)
    assert first["event_type"] == "TAKE_BACK_PROPOSED"
    post(
        client,
        "customer",
        "/products/contract-system/events",
        {**body, "notes": "Different obligations"},
        expected=409,
    )
    second = post(
        client,
        "customer",
        "/products/contract-system/events",
        {**body, "evidence": "Synthetic customer countersignature"},
    )
    assert second["event_type"] == "TAKE_BACK_CONFIRMED"
    post(
        client,
        "customer",
        "/products/contract-system/events",
        {
            "event": "INCIDENT_REPORTED",
            "evidence": "Synthetic observed incident report",
            "notes": "Potential incident requires qualified review; not a diagnosis",
        },
    )
    login(client, "customer")
    product = next(
        x
        for x in client.get("/circularity/products").json()
        if x["id"] == "contract-system"
    )
    assert product["state"] == "HOLD" and product["item"]["state"] == "HOLD"
    assert any(
        x["category"] == "POTENTIAL_SAFETY_INCIDENT"
        for x in client.get("/exceptions").json()
    )
    post(
        client,
        "customer",
        "/products/contract-system/events",
        {
            "event": "DEPLOY",
            "evidence": "Cannot deploy held product",
            "notes": "Qualified review must happen first",
            "customer_org_id": "org-customer",
        },
        expected=409,
    )
