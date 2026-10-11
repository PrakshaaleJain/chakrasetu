"""Repeatable real-HTTP demonstration. Start backend; run after seed/reset."""

import argparse, json, urllib.request, urllib.error, urllib.parse, uuid, os, http.cookiejar, getpass
from datetime import datetime, timezone, timedelta


def run(base):
    password = os.getenv("CHAKRA_DEMO_PASSWORD") or getpass.getpass(
        "Explicitly provisioned local demo password: "
    )
    sessions = {}

    def session(actor):
        if actor not in sessions:
            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(jar)
            )
            req = urllib.request.Request(
                base + "/auth/login",
                data=json.dumps(
                    {"email": actor + "@demo.chakrasetu.local", "password": password}
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            with opener.open(req):
                pass
            csrf = next(c.value for c in jar if c.name == "chakra_csrf")
            sessions[actor] = (opener, csrf)
        return sessions[actor]

    def call(actor, path, body=None, expected=200, key=None, method=None):
        request = urllib.request.Request(
            base + path,
            data=(
                json.dumps(body).encode()
                if body is not None
                else (b"{}" if method == "POST" else None)
            ),
            method=method or ("POST" if body is not None else "GET"),
            headers={
                "X-CSRF-Token": session(actor)[1],
                "Content-Type": "application/json",
                "Idempotency-Key": key or uuid.uuid4().hex,
            },
        )
        try:
            with session(actor)[0].open(request, timeout=20) as response:
                status = response.status
                result = json.load(response)
        except urllib.error.HTTPError as e:
            status = e.code
            result = json.load(e)
        assert (
            status == expected
        ), f"{path}: expected {expected}, got {status}: {result}"
        return result

    def future(days):
        return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    def post(actor, path, body=None, **kw):
        return call(actor, path, body, method="POST", **kw)

    flags = [
        "collision_crush",
        "swelling",
        "leakage",
        "heat",
        "smoke_fire",
        "odour",
        "exposed_conductors",
        "water_flood",
        "impact_drop",
        "thermal_event",
        "unknown_history",
    ]
    a = post(
        "originator",
        "/batteries",
        {
            "internal_id": "HTTP-DEMO-" + uuid.uuid4().hex[:6],
            "registration_title": "HTTP demonstration battery",
            "pbs": "L1",
            "application_type": "TWO_WHEELER",
            "collection_availability": "YES",
            "owner_org_id": "org-fleet",
            "custodian_org_id": "org-fleet",
            "chemistry": "LFP",
            "form": "PACK",
            "condition": "DEGRADED",
            "mass_kg": 42,
            "quantity": 1,
            "lat": 12.97,
            "lng": 77.59,
            "address": "Synthetic Bengaluru pickup",
            "authority_confirmed": True,
            "declaration": True,
            "flags": {f: "NO" for f in flags},
            "window_start": future(1),
            "window_end": future(3),
        },
    )
    assert call("originator", "/batteries/" + a["id"])["mass_kg"] == 42
    screen = post("originator", "/batteries/" + a["id"] + "/screen")
    assert screen["state"] == "REVIEW_REQUIRED"
    # Supporting authority evidence is reviewed separately from the seller's declaration.
    form = urllib.parse.urlencode(
        {
            "kind": "TRANSFER_AUTHORITY",
            "reference": "Synthetic HTTP-demo transfer mandate",
        }
    ).encode()
    request = urllib.request.Request(
        base + "/batteries/" + a["id"] + "/evidence",
        data=form,
        headers={
            "X-CSRF-Token": session("originator")[1],
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with session("originator")[0].open(request) as response:
        e = json.load(response)
    post(
        "reviewer",
        "/evidence/" + e["id"] + "/review",
        {
            "status": "VERIFIED",
            "reason": "Mock transfer mandate reviewed",
            "evidence": "Synthetic ownership reference",
        },
    )
    post("originator", "/batteries/" + a["id"] + "/confirm-transfer-authority")
    post(
        "reviewer",
        "/batteries/" + a["id"] + "/registration-review",
        {
            "decision": "APPROVED",
            "reason": "Synthetic registration information reviewed",
        },
    )
    assert (
        post("originator", "/batteries/" + a["id"] + "/screen")["state"]
        == "READY_FOR_LISTING"
    )
    print(
        "PASS intake persistence, missing authority gate and separate evidence review"
    )
    l = post("originator", "/listings", {"asset_id": a["id"], "expires_at": future(7)})
    candidates = call("originator", "/listings/" + l["id"] + "/eligible-buyers")
    assert any(
        not c["eligible"]
        and any(r["code"] == "CHEMISTRY_NOT_ACCEPTED" for r in c["reasons"])
        for c in candidates
    )
    o = post(
        "buyer",
        "/listings/" + l["id"] + "/offers",
        {
            "facility_id": "fac-refurb",
            "pathway": "REPAIR_REFURBISHMENT",
            "price_paise": 2000000,
            "payer_org_id": "org-refurb",
            "budget_paise": 300000,
            "expires_at": future(3),
            "acceptance_criteria": "Identity, quantity and condition match the agreed snapshot.",
        },
    )
    tx = post("originator", "/offers/" + o["id"] + "/accept")
    assert (
        post("originator", "/transactions/" + tx["id"] + "/confirm", {"version": 1})[
            "status"
        ]
        == "AWAITING_CONFIRMATION"
    )
    assert (
        post("buyer", "/transactions/" + tx["id"] + "/confirm", {"version": 1})[
            "status"
        ]
        == "AGREED_PENDING_LOGISTICS"
    )
    route_result = post("originator", "/transactions/" + tx["id"] + "/route-plans")
    assert len(route_result["candidates"]) >= 2
    p = next(p for p in route_result["candidates"] if not p["hub_id"])
    print("PASS compatibility exclusions, mutual terms and direct/one-hub alternatives")
    over = post(
        "transporter",
        "/transactions/" + tx["id"] + "/transport-quotes",
        {
            "route_id": p["id"],
            "total_paise": 420000,
            "expires_at": future(1),
            "evidence": "Synthetic all-inclusive quote above cap",
        },
    )
    blocked = post("buyer", "/quotes/" + over["id"] + "/accept", expected=409)
    assert blocked["detail"]["code"] == "QUOTE_OVER_BUDGET"
    q = post(
        "transporter",
        "/transactions/" + tx["id"] + "/transport-quotes",
        {
            "route_id": p["id"],
            "total_paise": 250000,
            "expires_at": future(1),
            "evidence": "Synthetic alternative all-inclusive quote",
        },
    )
    post("buyer", "/quotes/" + q["id"] + "/accept")
    post(
        "buyer",
        "/transactions/" + tx["id"] + "/reserve-capacity",
        {"route_id": p["id"]},
    )
    booking_key = uuid.uuid4().hex
    s = post("buyer", "/transactions/" + tx["id"] + "/shipments", key=booking_key)
    assert (
        post("buyer", "/transactions/" + tx["id"] + "/shipments", key=booking_key)["id"]
        == s["id"]
    )
    assert (
        call("originator", "/batteries/" + a["id"])["current_holder_org_id"]
        == "org-fleet"
    )
    print(
        "PASS over-budget rejection, real quote acceptance, atomic booking and duplicate protection"
    )
    post(
        "originator", "/shipments/" + s["id"] + "/events", {"state": "PICKUP_SCHEDULED"}
    )
    assert post(
        "originator",
        "/shipments/" + s["id"] + "/events",
        {
            "state": "PICKED_UP",
            "physical": True,
            "evidence": "Synthetic originator handover",
        },
    )["pending_confirmation"]
    assert (
        call("originator", "/batteries/" + a["id"])["current_holder_org_id"]
        == "org-fleet"
    )
    post(
        "transporter",
        "/shipments/" + s["id"] + "/events",
        {
            "state": "PICKED_UP",
            "physical": True,
            "evidence": "Synthetic transporter confirmation",
        },
    )
    post("transporter", "/shipments/" + s["id"] + "/events", {"state": "IN_TRANSIT"})
    signal = post(
        "transporter",
        "/shipments/" + s["id"] + "/telemetry",
        {"event": "ROUTE_DEVIATION", "value": 8},
    )
    assert signal["source"] == "SIMULATED"
    post(
        "transporter",
        "/shipments/" + s["id"] + "/events",
        {"state": "ARRIVED_PENDING_RECEIPT"},
    )
    receipt = post(
        "buyer",
        "/shipments/" + s["id"] + "/events",
        {
            "state": "RECEIVED",
            "physical": True,
            "condition_matches": False,
            "evidence": "Synthetic receiving discrepancy",
        },
    )
    assert receipt["shipment"]["state"] == "RECEIPT_DISPUTED"
    print(
        "PASS two-party physical custody, simulated alert and receiving discrepancy hold"
    )
    for case in call("reviewer", "/exceptions"):
        if case["object_id"] in [s["id"], tx["id"]] and case["status"] != "CLOSED":
            post(
                "reviewer",
                "/exceptions/" + case["id"] + "/resolve",
                {
                    "resolution": "Synthetic evidence reviewed; within-cap quote chosen or discrepancy reconciled.",
                    "evidence": "Synthetic documented reviewer resolution",
                    "resume": case["category"] == "RECEIPT_DISPUTE",
                },
            )
    post(
        "buyer",
        "/shipments/" + s["id"] + "/events",
        {
            "state": "RECEIVED",
            "physical": True,
            "evidence": "Synthetic complete reconciled receipt",
        },
    )
    assert not call("buyer", "/shipments/" + s["id"])["closure"]["can_close"]
    post(
        "buyer",
        "/shipments/" + s["id"] + "/inspection",
        {
            "outcome": "ACCEPT_AS_AGREED",
            "notes": "Condition reconciled with evidence",
            "evidence": "Synthetic receiving inspection report",
        },
    )
    post(
        "buyer",
        "/transactions/" + tx["id"] + "/settlement",
        {
            "status": "PAYMENT_REPORTED",
            "reference": "Synthetic report only; no money moved",
        },
    )
    post(
        "originator",
        "/transactions/" + tx["id"] + "/settlement",
        {
            "status": "SETTLED_CONFIRMED",
            "reference": "Synthetic payee confirmation only; no money moved",
        },
    )
    post(
        "buyer",
        "/batteries/" + a["id"] + "/disposition",
        {
            "outcome": "REFURBISHMENT_COMPLETED",
            "evidence": "Synthetic completion report",
        },
    )
    closure = call("buyer", "/shipments/" + s["id"])["closure"]
    assert closure["can_close"], closure["reasons"]
    post("buyer", "/shipments/" + s["id"] + "/events", {"state": "CLOSED"})
    assert call("buyer", "/shipments/" + s["id"])["state"] == "CLOSED"
    print(
        "PASS inspection, reported/confirmed settlement, evidenced disposition and closure"
    )
    print(
        json.dumps(
            {
                "asset_id": a["id"],
                "transaction_id": tx["id"],
                "shipment_id": s["id"],
                "status": "CLOSED",
                "synthetic": True,
            }
        )
    )

    return a["id"]


if __name__ == "__main__":
    import urllib.parse

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run(args.base_url.rstrip("/"))
