from test_intake_commercial import auth
from app.common import future


def test_scoped_review_keeps_flags_and_excludes_ordinary_receivers(client):
    cases = client.get("/exceptions", headers=auth("reviewer")).json()
    case = next(c for c in cases if c["object_id"] == "battery-3")
    assert (
        client.post(
            "/exceptions/" + case["id"] + "/resolve",
            headers=auth("reviewer"),
            json={
                "resolution": "Self clear attempted",
                "evidence": "none",
                "resume": True,
            },
        ).status_code
        == 409
    )
    r = client.post(
        "/exceptions/" + case["id"] + "/qualified-review",
        headers=auth("reviewer"),
        json={
            "decision": "SCOPED_CLEARANCE",
            "qualification_evidence": "Synthetic qualification reference",
            "report": "Synthetic scope-specific written report",
            "handling_scope": "CONTROLLED_HANDLING",
            "valid_until": future(days=7),
            "conditions": "Only the approved synthetic specialist and scoped transporter; original flags retained.",
        },
    )
    assert r.status_code == 200, r.text
    asset = client.get("/batteries/battery-3", headers=auth("originator2")).json()
    assert (
        asset["state"] == "READY_FOR_LISTING"
        and asset["data"]["flags"]["swelling"] == "YES"
    )
    r = client.post(
        "/listings",
        headers=auth("originator2"),
        json={"asset_id": "battery-3", "expires_at": future(days=1)},
    )
    assert r.status_code == 200, r.text
    candidates = client.get(
        "/listings/" + r.json()["id"] + "/eligible-buyers", headers=auth("originator2")
    ).json()
    assert [c["facility"]["id"] for c in candidates if c["eligible"]] == ["fac-review"]


def test_no_scoped_carrier_remains_held_for_manual_outreach(client):
    assert (
        client.post(
            "/network/transporter/trans-special/review",
            headers=auth("reviewer"),
            json={
                "verification": "SUSPENDED",
                "valid_until": future(days=30),
                "reason": "Mock qualification suspended",
                "evidence": "Synthetic reviewer decision",
            },
        ).status_code
        == 200
    )
    case = next(
        c
        for c in client.get("/exceptions", headers=auth("reviewer")).json()
        if c["object_id"] == "battery-3"
    )
    r = client.post(
        "/exceptions/" + case["id"] + "/qualified-review",
        headers=auth("reviewer"),
        json={
            "decision": "SCOPED_CLEARANCE",
            "qualification_evidence": "Synthetic qualification",
            "report": "Synthetic scoped report",
            "handling_scope": "CONTROLLED_HANDLING",
            "valid_until": future(days=7),
            "conditions": "Only scope-matching parties",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "UNDER_REVIEW" and "Manual" in r.json()["next_action"]
    assert (
        client.get("/batteries/battery-3", headers=auth("originator2")).json()["state"]
        == "HOLD"
    )
