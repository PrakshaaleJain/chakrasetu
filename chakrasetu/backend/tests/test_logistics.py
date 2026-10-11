from test_intake_commercial import auth, agreed
from app.common import future


def routes(client, tx):
    r = client.post(f"/transactions/{tx['id']}/route-plans", headers=auth("originator"))
    assert r.status_code == 200, r.text
    plans = r.json()["candidates"]
    assert len(plans) == 2
    return plans


def quoted(client, tx, plan, total=250000):
    r = client.post(
        f"/transactions/{tx['id']}/transport-quotes",
        headers=auth("transporter"),
        json={
            "route_id": plan["id"],
            "total_paise": total,
            "expires_at": future(days=1),
            "evidence": "Synthetic all-inclusive quote",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def booked(client):
    tx = agreed(client)
    plan = next(p for p in routes(client, tx) if not p["hub_id"])
    q = quoted(client, tx, plan)
    r = client.post(f"/quotes/{q['id']}/accept", headers=auth("buyer"))
    assert r.status_code == 200, r.text
    r = client.post(
        f"/transactions/{tx['id']}/reserve-capacity",
        headers=auth("buyer"),
        json={"route_id": plan["id"]},
    )
    assert r.status_code == 200, r.text
    r = client.post(f"/transactions/{tx['id']}/shipments", headers=auth("buyer"))
    assert r.status_code == 200, r.text
    return tx, r.json(), plan


def test_routes_budget_and_mutual_amendment(client):
    tx = agreed(client)
    plans = routes(client, tx)
    assert all(p["data"]["scope"]["mass_kg"] == 42 for p in plans)
    plan = next(p for p in plans if not p["hub_id"])
    q = quoted(client, tx, plan, 420000)
    r = client.post(f"/quotes/{q['id']}/accept", headers=auth("buyer"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "QUOTE_OVER_BUDGET"
    r = client.post(
        f"/transactions/{tx['id']}/amend",
        headers=auth("buyer"),
        json={
            "budget_paise": 450000,
            "reason": "Approve disclosed overrun",
            "evidence": "Synthetic cap approval",
        },
    )
    assert r.status_code == 200
    assert (
        client.post(
            f"/transactions/{tx['id']}/confirm",
            headers=auth("originator"),
            json={"version": 1},
        ).status_code
        == 409
    )
    for actor in ["originator", "buyer"]:
        assert (
            client.post(
                f"/transactions/{tx['id']}/confirm",
                headers=auth(actor),
                json={"version": 2},
            ).status_code
            == 200
        )
    assert (
        client.post(
            f"/quotes/{q['id']}/accept",
            headers={**auth("buyer"), "Idempotency-Key": "retry2"},
        ).status_code
        == 409
    )


def test_booking_idempotent_and_custody_unchanged(client):
    tx, s, plan = booked(client)
    dup = client.post(f"/transactions/{tx['id']}/shipments", headers=auth("buyer"))
    assert dup.json()["id"] == s["id"]
    asset = client.get("/batteries/battery-1", headers=auth("originator")).json()
    assert asset["current_holder_org_id"] == "org-fleet"


def test_no_acceptance_recoverable(client):
    tx = agreed(client)
    routes(client, tx)
    r = client.post(
        f"/transactions/{tx['id']}/quote-round/close", headers=auth("buyer")
    )
    assert r.status_code == 200, r.text
    assert r.json()["transaction"]["status"] == "AGREED_PENDING_LOGISTICS"
    assert r.json()["exception"]["category"] == "NO_TRANSPORTER"
    assert (
        client.post(
            f"/transactions/{tx['id']}/quote-round/reopen", headers=auth("buyer")
        ).status_code
        == 200
    )
