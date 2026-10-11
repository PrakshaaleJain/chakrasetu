from uuid import uuid4
from test_intake_commercial import auth, agreed
from test_races import second_transaction
from test_logistics import routes, quoted
from test_shipment import advance


def make_hub(client, tx):
    p = next(p for p in routes(client, tx) if p["hub_id"])
    assert (
        client.post(
            "/route-plans/" + p["id"] + "/hub-approval", headers=auth("hub")
        ).status_code
        == 200
    )
    q = quoted(client, tx, p, 250000)
    r = client.post(
        "/quotes/" + q["id"] + "/accept",
        headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/transactions/" + tx["id"] + "/reserve-capacity",
        headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
        json={"route_id": p["id"]},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/transactions/" + tx["id"] + "/shipments",
        headers={**auth("buyer"), "Idempotency-Key": uuid4().hex},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_hub_batch_manifest_and_per_asset_custody(client):
    one = agreed(client)
    s1 = make_hub(client, one)
    two = second_transaction(client)
    s2 = make_hub(client, two)
    r = client.post(
        "/consolidations",
        headers=auth("buyer"),
        json={
            "shipment_ids": [s1["id"], s2["id"]],
            "evidence": "Synthetic receiver and hub consolidation proposal",
            "reason": "Compatible jointly scheduled assets",
        },
    )
    assert r.status_code == 200, r.text
    b = r.json()
    economics = client.get(
        "/consolidations/" + b["id"] + "/economics", headers=auth("buyer")
    )
    assert economics.status_code == 200, economics.text
    assert economics.json()["total_transport_paise"] == 500000
    assert economics.json()["transport_per_battery_paise"] == 250000
    assert economics.json()["savings_paise"] is None

    assert b["data"]["total_mass_kg"] == 84 and b["data"]["savings_paise"] is None
    assert (
        client.post(
            "/shipments/" + s1["id"] + "/events",
            headers=auth("originator"),
            json={"state": "PICKUP_SCHEDULED"},
        ).status_code
        == 409
    )
    for actor in ["originator", "buyer", "hub", "transporter"]:
        assert (
            client.post(
                "/consolidations/" + b["id"] + "/approve", headers=auth(actor)
            ).status_code
            == 200
        )
    advance(client, s1, "PICKUP_SCHEDULED", "originator")
    advance(
        client,
        s1,
        "PICKED_UP",
        "originator",
        physical=True,
        evidence="Asset-specific seller handover",
    )
    advance(
        client,
        s1,
        "PICKED_UP",
        physical=True,
        evidence="Asset-specific transporter confirmation",
    )
    advance(client, s1, "IN_TRANSIT")
    assert (
        client.post(
            "/shipments/" + s1["id"] + "/events",
            headers={**auth("transporter"), "Idempotency-Key": "early"},
            json={"state": "ARRIVED_PENDING_RECEIPT"},
        ).status_code
        == 409
    )
    for event in ["HUB_RECEIVED", "HUB_DISPATCHED"]:
        for actor in ["hub", "transporter"]:
            r = client.post(
                "/shipments/" + s1["id"] + "/hub-events",
                headers={**auth(actor), "Idempotency-Key": uuid4().hex},
                json={
                    "event": event,
                    "physical": True,
                    "evidence": "Synthetic " + event + " " + actor,
                },
            )
            assert r.status_code == 200, r.text
    advance(client, s1, "ARRIVED_PENDING_RECEIPT")
    history = client.get("/shipments/" + s1["id"], headers=auth("buyer")).json()[
        "custody"
    ]
    assert [h["event_type"] for h in history] == [
        "PICKUP",
        "HUB_RECEIVED",
        "HUB_DISPATCHED",
    ]
    assert (
        client.get("/shipments/" + s2["id"], headers=auth("buyer")).json()["custody"]
        == []
    )
