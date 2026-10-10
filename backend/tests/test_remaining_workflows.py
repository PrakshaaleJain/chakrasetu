from uuid import uuid4
from test_intake_commercial import auth, agreed
from test_logistics import routes, quoted
from test_shipment import arrive
from app.common import future


def test_partial_receipt_has_quantity_custody_segments(client):
    a = client.get("/batteries/battery-1", headers=auth("originator")).json()
    fields = [
        "internal_id",
        "owner_org_id",
        "custodian_org_id",
        "chemistry",
        "form",
        "condition",
        "mass_kg",
        "lat",
        "lng",
        "authority_confirmed",
    ]
    body = {k: a[k] for k in fields}
    body.update(
        {
            k: a["data"][k]
            for k in ["flags", "declaration", "window_start", "window_end"]
        }
    )
    body["quantity"] = 3
    assert (
        client.patch(
            "/batteries/battery-1", headers=auth("originator"), json=body
        ).status_code
        == 200
    )
    client.post("/batteries/battery-1/screen", headers=auth("originator"))
    tx, s = arrive(client)
    r = client.post(
        "/shipments/" + s["id"] + "/events",
        headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
        json={
            "state": "RECEIVED",
            "receipt": "PARTIALLY_ACCEPTED",
            "accepted_quantity": 1,
            "physical": True,
            "evidence": "Only one of three units physically accepted",
        },
    )
    assert r.status_code == 200, r.text
    a = client.get("/batteries/battery-1", headers=auth("buyer")).json()
    assert a["data"]["custody_segments"] == [
        {"holder": "org-refurb", "quantity": 1},
        {"holder": "org-trans", "quantity": 2},
    ]
    case = next(
        c
        for c in client.get("/exceptions", headers=auth("reviewer")).json()
        if c["object_id"] == s["id"]
    )
    assert (
        client.post(
            "/exceptions/" + case["id"] + "/resolve",
            headers=auth("reviewer"),
            json={
                "resolution": "Remaining units located and accepted on second receipt",
                "evidence": "Synthetic reconciliation",
                "resume": True,
            },
        ).status_code
        == 200
    )
    r = client.post(
        "/shipments/" + s["id"] + "/events",
        headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
        json={
            "state": "RECEIVED",
            "receipt": "ACCEPTED",
            "accepted_quantity": 3,
            "physical": True,
            "evidence": "All quantities reconciled and physically accepted",
        },
    )
    assert r.status_code == 200, r.text
    d = client.get("/shipments/" + s["id"], headers=auth("buyer")).json()
    assert d["custody"][-1]["data"]["quantity"] == 2


def test_reschedule_invalidates_quotes_and_needs_mutual_version(client):
    tx = agreed(client)
    p = next(p for p in routes(client, tx) if not p["hub_id"])
    q = quoted(client, tx, p)
    r = client.post(
        "/transactions/" + tx["id"] + "/reschedule",
        headers=auth("originator"),
        json={
            "window_start": future(days=4),
            "window_end": future(days=6),
            "reason": "Shift pickup after no response",
            "evidence": "Synthetic mutually reviewable proposal",
        },
    )
    assert r.status_code == 200, r.text
    assert (
        r.json()["terms_version"] == 2 and r.json()["status"] == "AWAITING_CONFIRMATION"
    )
    assert (
        client.post("/quotes/" + q["id"] + "/accept", headers=auth("buyer")).status_code
        == 409
    )
    for actor in ["originator", "buyer"]:
        assert (
            client.post(
                "/transactions/" + tx["id"] + "/confirm",
                headers=auth(actor),
                json={"version": 2},
            ).status_code
            == 200
        )
    assert len(routes(client, tx)) == 2


def test_conditional_price_revision_preserves_previous_terms(client):
    tx, s = arrive(client)
    r = client.post(
        "/shipments/" + s["id"] + "/events",
        headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
        json={
            "state": "RECEIVED",
            "physical": True,
            "evidence": "Receiver physically accepted",
        },
    )
    assert r.status_code == 200
    r = client.post(
        "/shipments/" + s["id"] + "/inspection",
        headers=auth("buyer"),
        json={
            "outcome": "REVISE_PRICE",
            "price_paise": 1800000,
            "notes": "Condition-based price revision",
            "evidence": "Synthetic inspection report",
        },
    )
    assert r.status_code == 200, r.text
    txs = client.get("/transactions", headers=auth("originator")).json()
    current = next(t for t in txs if t["id"] == tx["id"])
    assert current["terms"]["price_paise"] == 1800000
    assert (
        current["terms_history"][0]["price_paise"] == 2000000
        and current["status"] == "AWAITING_CONFIRMATION"
    )
    assert (
        client.post(
            "/transactions/" + tx["id"] + "/settlement",
            headers=auth("buyer"),
            json={"status": "PAYMENT_REPORTED", "reference": "premature"},
        ).status_code
        == 409
    )


def test_critical_flag_cannot_be_erased_by_draft_edit(client):
    a = client.get("/batteries/battery-3", headers=auth("originator2")).json()
    body = {
        k: a[k]
        for k in [
            "internal_id",
            "owner_org_id",
            "custodian_org_id",
            "chemistry",
            "form",
            "condition",
            "mass_kg",
            "quantity",
            "lat",
            "lng",
            "authority_confirmed",
        ]
    }
    body["flags"] = {k: "NO" for k in a["data"]["flags"]}
    assert (
        client.patch(
            "/batteries/battery-3", headers=auth("originator2"), json=body
        ).status_code
        == 409
    )


def test_reviewed_authority_fulfils_owned_intake_followup(client):
    from app.enums import FLAGS

    a = client.post(
        "/batteries",
        headers=auth("originator"),
        json={
            "internal_id": "authority-followup",
            "owner_org_id": "org-fleet",
            "custodian_org_id": "org-fleet",
            "flags": {f: "NO" for f in FLAGS},
            "condition": "DEGRADED",
            "declaration": True,
            "authority_confirmed": True,
        },
    ).json()
    assert (
        client.post(
            "/batteries/" + a["id"] + "/screen", headers=auth("originator")
        ).json()["state"]
        == "REVIEW_REQUIRED"
    )
    e = client.post(
        "/batteries/" + a["id"] + "/evidence",
        headers=auth("originator"),
        data={
            "kind": "TRANSFER_AUTHORITY",
            "reference": "Synthetic reviewed transfer mandate",
        },
    ).json()
    assert (
        client.post(
            "/evidence/" + e["id"] + "/review",
            headers=auth("reviewer"),
            json={
                "status": "VERIFIED",
                "reason": "Mock authority mandate reviewed",
                "evidence": "Synthetic source",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/batteries/" + a["id"] + "/screen", headers=auth("originator")
        ).json()["state"]
        == "READY_FOR_LISTING"
    )
    cases = [
        c
        for c in client.get("/exceptions", headers=auth("originator")).json()
        if c["object_id"] == a["id"]
    ]
    assert (
        len(cases) == 1
        and cases[0]["status"] == "CLOSED"
        and cases[0]["data"]["resolution_evidence_ids"]
    )
