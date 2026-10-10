from test_intake_commercial import auth
from test_logistics import booked


def advance(client, s, state, actor="transporter", **body):
    h = {
        **auth(actor),
        "Idempotency-Key": s["id"]
        + state
        + actor
        + str(body.get("condition_matches", True)),
    }
    r = client.post(
        f"/shipments/{s['id']}/events", headers=h, json={"state": state, **body}
    )
    assert r.status_code == 200, r.text
    return r.json()


def arrive(client):
    tx, s, _ = booked(client)
    advance(client, s, "PICKUP_SCHEDULED", "originator")
    first = advance(
        client,
        s,
        "PICKED_UP",
        "originator",
        physical=True,
        evidence="Synthetic originator handover",
    )
    assert first["pending_confirmation"]
    assert (
        client.get("/batteries/battery-1", headers=auth("originator")).json()[
            "current_holder_org_id"
        ]
        == "org-fleet"
    )
    advance(
        client, s, "PICKED_UP", physical=True, evidence="Synthetic transporter handover"
    )
    advance(client, s, "IN_TRANSIT")
    advance(client, s, "ARRIVED_PENDING_RECEIPT")
    return tx, s


def test_custody_telemetry_receipt_and_closure(client):
    tx, s, _ = booked(client)
    assert (
        client.post(
            f"/shipments/{s['id']}/events",
            headers=auth("buyer"),
            json={"state": "CLOSED"},
        ).status_code
        == 409
    )
    advance(client, s, "PICKUP_SCHEDULED", "originator")
    advance(
        client,
        s,
        "PICKED_UP",
        "originator",
        physical=True,
        evidence="Seller confirmation",
    )
    advance(client, s, "PICKED_UP", physical=True, evidence="Transport confirmation")
    advance(
        client, s, "PICKED_UP", physical=True, evidence="Transport confirmation"
    )  # idempotent replay
    advance(client, s, "IN_TRANSIT")
    r = client.post(
        f"/shipments/{s['id']}/telemetry",
        headers=auth("transporter"),
        json={"event": "ROUTE_DEVIATION", "value": 8},
    )
    assert r.status_code == 200 and r.json()["source"] == "SIMULATED"
    advance(client, s, "ARRIVED_PENDING_RECEIPT")
    advance(
        client,
        s,
        "RECEIVED",
        "buyer",
        physical=True,
        evidence="Receiver count and identity confirmation",
    )
    detail = client.get(f"/shipments/{s['id']}", headers=auth("buyer")).json()
    assert len(detail["custody"]) == 2
    assert not detail["closure"]["can_close"]
    assert (
        client.post(
            f"/shipments/{s['id']}/inspection",
            headers=auth("buyer"),
            json={
                "outcome": "ACCEPT_AS_AGREED",
                "evidence": "Inspection record",
                "notes": "Matches agreed condition",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/transactions/{tx['id']}/settlement",
            headers=auth("buyer"),
            json={
                "status": "PAYMENT_REPORTED",
                "reference": "Synthetic reported reference",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/transactions/{tx['id']}/settlement",
            headers=auth("originator"),
            json={
                "status": "SETTLED_CONFIRMED",
                "reference": "Synthetic payee attestation",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/batteries/battery-1/disposition",
            headers=auth("buyer"),
            json={
                "outcome": "REFURBISHMENT_COMPLETED",
                "evidence": "Synthetic completion report",
            },
        ).status_code
        == 200
    )
    cases = client.get("/exceptions", headers=auth("reviewer")).json()
    for c in cases:
        if c["object_id"] == s["id"] and c["status"] != "CLOSED":
            assert (
                client.post(
                    f"/exceptions/{c['id']}/resolve",
                    headers=auth("reviewer"),
                    json={
                        "resolution": "Reviewed synthetic deviation",
                        "evidence": "Transporter explanation",
                    },
                ).status_code
                == 200
            )
    advance(client, s, "CLOSED", "buyer")


def test_receipt_discrepancy_preserves_holder(client):
    tx, s = arrive(client)
    r = advance(
        client,
        s,
        "RECEIVED",
        "buyer",
        physical=True,
        condition_matches=False,
        evidence="Condition discrepancy photograph",
    )
    assert r["shipment"]["state"] == "RECEIPT_DISPUTED"
    assert (
        client.get("/batteries/battery-1", headers=auth("buyer")).json()[
            "current_holder_org_id"
        ]
        == "org-trans"
    )
    assert (
        client.post(
            f"/shipments/{s['id']}/inspection",
            headers=auth("buyer"),
            json={
                "outcome": "ACCEPT_AS_AGREED",
                "evidence": "Attempt",
                "notes": "Try bypass",
            },
        ).status_code
        == 409
    )
