from app.common import future
from app.enums import FLAGS


def auth(actor):
    return {
        "Authorization": f"Bearer demo-{actor}-local-only",
        "Idempotency-Key": actor + "-key",
    }


def setup_tx(client):
    l = client.post(
        "/listings",
        headers=auth("originator"),
        json={"asset_id": "battery-1", "expires_at": future(days=4)},
    )
    assert l.status_code == 200, l.text
    listing = l.json()
    o = client.post(
        f"/listings/{listing['id']}/offers",
        headers=auth("buyer"),
        json={
            "facility_id": "fac-refurb",
            "pathway": "REPAIR_REFURBISHMENT",
            "price_paise": 2000000,
            "payer_org_id": "org-refurb",
            "budget_paise": 300000,
            "expires_at": future(days=3),
            "acceptance_criteria": "Identity and condition match declared evidence",
        },
    )
    assert o.status_code == 200, o.text
    r = client.post(f"/offers/{o.json()['id']}/accept", headers=auth("originator"))
    assert r.status_code == 200, r.text
    return r.json(), listing, o.json()


def agreed(client):
    tx, _, _ = setup_tx(client)
    for actor in ["originator", "buyer"]:
        r = client.post(
            f"/transactions/{tx['id']}/confirm",
            headers=auth(actor),
            json={"version": 1},
        )
        assert r.status_code == 200, r.text
    return tx


def test_intake_persists_and_flags(client):
    body = {
        "internal_id": "new",
        "registration_title": "Existing regression battery",
        "pbs": "L3",
        "address": "Bengaluru",
        "lat": 12.97,
        "lng": 77.59,
        "owner_org_id": "org-fleet",
        "custodian_org_id": "org-fleet",
        "flags": {f: "NO" for f in FLAGS},
        "declaration": True,
    }
    r = client.post("/batteries", headers=auth("originator"), json=body)
    assert r.status_code == 200, r.text
    id = r.json()["id"]
    assert (
        client.get("/batteries/" + id, headers=auth("originator")).json()["mass_kg"]
        is None
    )
    result = client.post(
        "/batteries/" + id + "/screen", headers=auth("originator")
    ).json()
    assert result["state"] == "REVIEW_REQUIRED"
    held = client.post(
        "/listings",
        headers=auth("originator2"),
        json={"asset_id": "battery-3", "expires_at": future(days=1)},
    )
    assert held.status_code == 409
    assert (
        client.get("/batteries/battery-3", headers=auth("originator")).status_code
        == 403
    )


def test_eligibility_and_confirmation(client):
    tx, l, _ = setup_tx(client)
    candidates = client.get(
        f"/listings/{l['id']}/eligible-buyers", headers=auth("originator")
    ).json()
    incompatible = next(
        x for x in candidates if x["facility"]["id"] == "fac-incompatible"
    )
    assert "CHEMISTRY_NOT_ACCEPTED" in [r["code"] for r in incompatible["reasons"]]
    r = client.post(
        f"/transactions/{tx['id']}/confirm",
        headers=auth("originator"),
        json={"version": 1},
    )
    assert r.json()["status"] == "AWAITING_CONFIRMATION"
    assert (
        client.post(
            f"/transactions/{tx['id']}/confirm",
            headers=auth("buyer"),
            json={"version": 2},
        ).status_code
        == 409
    )
    r = client.post(
        f"/transactions/{tx['id']}/confirm", headers=auth("buyer"), json={"version": 1}
    )
    assert r.json()["status"] == "AGREED_PENDING_LOGISTICS"
    duplicate = client.post(
        f"/offers/{tx['offer_id']}/accept", headers=auth("originator")
    ).json()
    assert duplicate["id"] == tx["id"]
