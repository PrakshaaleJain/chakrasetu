"""Real HTTP rehearsal: original intake → second-life integration/deployment → recycling/refining/manufacturing."""

import urllib.request, urllib.error, http.cookiejar, json, os, uuid, argparse
from datetime import datetime, timezone, timedelta
import demo


def run(base):
    asset_id = demo.run(base)
    password = os.environ["CHAKRA_DEMO_PASSWORD"]
    sessions = {}

    def future(n):
        return (datetime.now(timezone.utc) + timedelta(days=n)).isoformat()

    def call(actor, path, body=None):
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
            sessions[actor] = (
                opener,
                next(c.value for c in jar if c.name == "chakra_csrf"),
            )
        opener, csrf = sessions[actor]
        req = urllib.request.Request(
            base + "/circularity" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": csrf,
                "Idempotency-Key": uuid.uuid4().hex,
            },
        )
        try:
            with opener.open(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise AssertionError(f"{actor} {path}: {e.code} {e.read().decode()}") from e

    review = {
        "accepted": True,
        "evidence": "SYNTHETIC documentary scope and completion report",
        "reason": "Synthetic independent review of the specified operation",
        "valid_until": future(30),
    }

    def make_job(actor, facility, operation, items, owner, outputs, loss):
        job = call(
            actor,
            "/jobs",
            {
                "facility_id": facility,
                "operation": operation,
                "item_ids": [i["id"] for i in items],
                "procedure": "Synthetic documented " + operation + " procedure",
                "evidence": "Synthetic input-owner and output-title processing agreement",
            },
        )
        call(owner, "/jobs/" + job["id"] + "/authorize", review)
        call(actor, "/jobs/" + job["id"] + "/start", {})
        completed = call(
            actor,
            "/jobs/" + job["id"] + "/complete",
            {
                "outputs": outputs,
                "process_evidence": "Synthetic measured process completion",
                "measured_loss_kg": loss,
                "loss_evidence": "Synthetic measured documented process loss",
            },
        )
        call("reviewer", "/jobs/" + job["id"] + "/review", review)
        ids = {x["item_id"] for x in completed["outputs"]}
        return [i for i in call(actor, "/items") if i["id"] in ids]

    def output(category, kind, mass):
        return {
            "identifier": "DEMO-" + category + "-" + uuid.uuid4().hex[:6],
            "kind": kind,
            "mass_kg": mass,
            "category": category,
            "specification": "Synthetic measured receiving specification for "
            + category,
            "evidence": "Synthetic operator-recorded composition/product quality evidence",
            "chemistry": "LFP",
        }

    def product(actor, item):
        return next(p for p in call(actor, "/products") if p["item_id"] == item["id"])

    def accept_product(actor, item):
        p = product(actor, item)
        call(
            actor,
            "/products/" + p["id"] + "/events",
            {
                "event": "ACCEPT",
                "evidence": "Synthetic application-specific acceptance report",
                "notes": "Synthetic acceptance against documented product specifications",
            },
        )
        return p

    def transfer(sender, receiver, facility, item):
        h = call(
            sender,
            "/handoffs",
            {
                "item_id": item["id"],
                "receiver_facility_id": facility,
                "price_paise": 100000,
                "payer_org_id": "org-"
                + {
                    "buyer": "refurb",
                    "secondlife": "second",
                    "recycler": "recycle",
                }.get(receiver, receiver),
                "budget_paise": 100000,
                "acceptance_specification": "Synthetic defined receiving quality and handling specification",
                "evidence": "Synthetic all-party offtake terms evidence",
                "window_start": future(1),
                "window_end": future(3),
            },
        )
        for actor in [sender, receiver]:
            call(actor, "/handoffs/" + h["id"] + "/confirm", {"version": 1})
        requests = call("transporter", "/quote-requests")
        assert any(x["handoff_id"] == h["id"] for x in requests)
        call(
            "transporter",
            "/handoffs/" + h["id"] + "/quote",
            {
                "transporter_id": "trans-1",
                "total_paise": 50000,
                "expires_at": future(1),
                "evidence": "Synthetic carrier-submitted committed all-inclusive quote",
                "acceptance_specification_confirmed": True,
            },
        )
        call(receiver, "/handoffs/" + h["id"] + "/book", {})
        for actor in [sender, "transporter"]:
            call(
                actor,
                "/handoffs/" + h["id"] + "/events",
                {
                    "state": "PICKED_UP",
                    "physical": True,
                    "evidence": "Synthetic two-party physical pickup evidence",
                },
            )
        call(
            "transporter",
            "/handoffs/" + h["id"] + "/events",
            {"state": "ARRIVED", "evidence": "Synthetic physical arrival evidence"},
        )
        result = call(
            receiver,
            "/handoffs/" + h["id"] + "/events",
            {
                "state": "RECEIVED",
                "physical": True,
                "evidence": "Synthetic measured receiving inspection accepted against specification",
            },
        )
        call(
            receiver,
            "/handoffs/" + h["id"] + "/settlement",
            {
                "status": "REPORTED",
                "evidence": "Synthetic buyer-reported payment; platform moves no money",
            },
        )
        call(
            sender,
            "/handoffs/" + h["id"] + "/settlement",
            {
                "status": "CONFIRMED",
                "evidence": "Synthetic seller-confirmed payment record",
            },
        )
        closed = call(
            receiver,
            "/handoffs/" + h["id"] + "/events",
            {
                "state": "CLOSED",
                "evidence": "Synthetic reviewed accepted receipt and confirmed settlement",
            },
        )
        assert len(closed["custody"]) == 2 and closed["state"] == "CLOSED"
        return result["item"]

    a = call(
        "buyer",
        "/assessments",
        {
            "asset_id": asset_id,
            "facility_id": "fac-refurb",
            "intended_operation": "REFURBISHMENT",
            "procedure": "Synthetic technician test procedure against incoming refurbishment specification",
        },
    )
    call(
        "technician",
        "/assessments/" + a["id"] + "/submit",
        {
            "observations": "Synthetic measurement observations only",
            "measurements": [
                {
                    "name": "capacity",
                    "value": 35,
                    "unit": "Ah",
                    "method": "Synthetic bench measurement procedure",
                }
            ],
            "equipment_reference": "Synthetic test equipment record",
            "evidence": "Synthetic technician assessment report",
            "outcome": "SUITABLE_FOR_DEFINED_OPERATION",
            "limitations": "Demonstration findings only; no universal product suitability or safety certification",
            "acceptance_specification": "Synthetic defined refurbishment intake technical criteria",
        },
    )
    call("reviewer", "/assessments/" + a["id"] + "/review", review)
    battery = call(
        "buyer",
        "/items/import-battery",
        {
            "asset_id": asset_id,
            "facility_id": "fac-refurb",
            "receipt_evidence": "Already recorded physical receipt in the original shipment",
        },
    )
    pack = make_job(
        "buyer",
        "fac-refurb",
        "REFURBISHMENT",
        [battery],
        "originator",
        [output("REFURBISHED_PACK", "PRODUCT", 40)],
        2,
    )[0]
    accept_product("buyer", pack)
    pack = transfer("buyer", "secondlife", "fac-second", pack)
    system = make_job(
        "secondlife",
        "fac-second",
        "INTEGRATION",
        [pack],
        "secondlife",
        [output("SECOND_LIFE_SYSTEM", "PRODUCT", 38)],
        2,
    )[0]
    accept_product("secondlife", system)
    system = transfer("secondlife", "customer", "fac-customer", system)
    p = product("customer", system)
    for event in ["DEPLOY", "SERVICE", "RETIRE"]:
        call(
            "customer",
            "/products/" + p["id"] + "/events",
            {
                "event": event,
                "evidence": "Synthetic installation/service/retirement record",
                "notes": "Synthetic customer operational evidence",
                "customer_org_id": "org-customer",
            },
        )
    system = next(x for x in call("customer", "/items") if x["id"] == system["id"])
    retired = transfer("customer", "recycler", "fac-recycle", system)
    lots = make_job(
        "recycler",
        "fac-recycle",
        "RECYCLING",
        [retired],
        "recycler",
        [output("BLACK_MASS", "MATERIAL", 30), output("COPPER", "MATERIAL", 5)],
        3,
    )
    black = next(x for x in lots if x["data"]["category"] == "BLACK_MASS")
    black = transfer("recycler", "refiner", "fac-refiner", black)
    refined = make_job(
        "refiner",
        "fac-refiner",
        "REFINING",
        [black],
        "refiner",
        [output("REFINED_LITHIUM", "MATERIAL", 25)],
        5,
    )[0]
    refined = transfer("refiner", "manufacturer", "fac-manufacturer", refined)
    final = make_job(
        "manufacturer",
        "fac-manufacturer",
        "MANUFACTURING",
        [refined],
        "manufacturer",
        [output("REFINED_LITHIUM", "MATERIAL", 24)],
        1,
    )[0]
    trace = call("manufacturer", "/items/" + final["id"] + "/trace")
    assert len(trace["links"]) == 5
    print(
        "PASS real HTTP assessment, refurbishment, integration, customer deployment/service/retirement, recycling, refining, manufacturing and five-stage genealogy",
        flush=True,
    )
    print(
        json.dumps(
            {
                "original_battery_id": asset_id,
                "final_material_id": final["id"],
                "lineage_links": len(trace["links"]),
                "synthetic": True,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run(args.base_url)
