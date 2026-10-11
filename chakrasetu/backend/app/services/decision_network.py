"""Qualified whole-chain discovery; no reservations or transporter commitments."""

from types import SimpleNamespace
from sqlalchemy import select
from .. import models as m
from ..common import expired, future, get
from ..config import APP_ENV
from .circularity import capability_check
from .matching import transporter_check, available
from .downstream import carrier_check

OPERATIONS = {
    "AUTOMOTIVE": ["ASSESSMENT", "REFURBISHMENT"],
    "REFURBISHMENT": ["ASSESSMENT", "REFURBISHMENT"],
    "SECOND_LIFE": ["ASSESSMENT", "REPURPOSING", "INTEGRATION"],
    "RECYCLING": ["RECYCLING", "REFINING", "MANUFACTURING"],
    "ASSESSMENT": ["ASSESSMENT"],
}
OUTPUTS = {
    "INTEGRATION": "REFURBISHED_PACK",
    "REFINING": "BLACK_MASS",
    "MANUFACTURING": "REFINED_LITHIUM",
}


def network_for(db, asset, path):
    facilities = db.scalars(select(m.Facility).order_by(m.Facility.id)).all()
    carriers = db.scalars(
        select(m.TransporterProfile).order_by(m.TransporterProfile.id)
    ).all()
    stages, rejected = [], []
    previous = (
        [[asset.lat, asset.lng]]
        if asset.lat is not None and asset.lng is not None
        else []
    )
    for op in OPERATIONS[path]:
        receivers = []
        category = OUTPUTS.get(op) if path in ["SECOND_LIFE", "RECYCLING"] else None
        for f in facilities:
            reasons = capability_check(
                db,
                f,
                op,
                asset.mass_kg,
                asset.chemistry if not category else None,
                asset.form if not category else None,
                category,
                asset=asset if not category else None,
            )
            if asset.mass_kg is not None and not category:
                cap = db.scalar(
                    select(m.FacilityCapability).where(
                        m.FacilityCapability.facility_id == f.id
                    )
                )
                if (
                    cap
                    and available(
                        db,
                        "CAPABILITY",
                        cap.id,
                        min(cap.capacity_kg, cap.available_kg),
                        asset.data.get("window_start") or future(days=1),
                        asset.data.get("window_end") or future(days=2),
                    )
                    < asset.mass_kg
                ):
                    reasons.append(
                        {
                            "code": "CAPACITY_CONFLICT",
                            "message": "Active reservations consume available receiving capacity.",
                        }
                    )
            if not previous:
                reasons.append(
                    {
                        "code": "LOCATION_UNKNOWN",
                        "message": "Pickup coordinates required to check the carrier service area.",
                    }
                )
            if not asset.data.get("window_start") or not asset.data.get("window_end"):
                reasons.append(
                    {
                        "code": "COLLECTION_WINDOW_UNKNOWN",
                        "message": "Agree a concrete collection window to validate available carrier service before a financial recommendation.",
                    }
                )
            transporters, transport_rejected = [], []
            for t in carriers:
                # The planner checks every destination against every preceding reachable stop.
                if category:
                    projected = SimpleNamespace(
                        kind=(
                            "PRODUCT" if category == "REFURBISHED_PACK" else "MATERIAL"
                        ),
                        mass_kg=asset.mass_kg,
                        data={
                            "category": category,
                            "synthetic": asset.data.get("synthetic", False),
                        },
                    )
                    leg_checks = [
                        carrier_check(
                            db,
                            projected,
                            t,
                            SimpleNamespace(lat=p[0], lng=p[1]),
                            f,
                            asset.data.get("window_start") or future(days=1),
                            asset.data.get("window_end") or future(days=2),
                        )
                        for p in previous
                    ]
                else:
                    leg_checks = [
                        transporter_check(db, asset, t, [p, [f.lat, f.lng]])
                        for p in previous
                    ]
                errors = (
                    []
                    if any(not x for x in leg_checks)
                    else [r for checks in leg_checks for r in checks]
                )
                if not leg_checks:
                    errors = [
                        {
                            "code": "LOCATION_UNKNOWN",
                            "message": "No reachable preceding stop.",
                        }
                    ]
                if errors:
                    transport_rejected.append(
                        {"transporter_id": t.id, "name": t.name, "reasons": errors}
                    )
                else:
                    transporters.append(
                        {
                            "id": t.id,
                            "name": t.name,
                            "rate_source": t.data.get("rate_source"),
                            "commitment": "NOT_BOOKED",
                        }
                    )
            if not transporters:
                reasons.append(
                    {
                        "code": "NO_QUALIFIED_TRANSPORTER",
                        "message": "No currently qualified carrier covers the chemistry, format, handling, capacity, service area and collection window.",
                    }
                )
            if asset.data.get("window_end") and expired(asset.data["window_end"]):
                reasons.append(
                    {
                        "code": "WINDOW_EXPIRED",
                        "message": "Collection window expired; agree a new window.",
                    }
                )
            if reasons:
                rejected.append(
                    {
                        "operation": op,
                        "facility_id": f.id,
                        "name": f.name,
                        "reasons": reasons,
                        "transport_exclusions": transport_rejected,
                    }
                )
            else:
                receivers.append(
                    {
                        "facility_id": f.id,
                        "organisation_id": f.organisation_id,
                        "name": f.name,
                        "operation": op,
                        "lat": f.lat,
                        "lng": f.lng,
                        "transporters": transporters,
                        "projected_input_category": category,
                    }
                )
        stages.append({"operation": op, "receivers": receivers})
        previous = [[r["lat"], r["lng"]] for r in receivers]
    # Product deployments need an independently qualified customer scope.
    if path == "SECOND_LIFE":
        customers = []
        for f in facilities:
            org = get(db, m.Organisation, f.organisation_id)
            if org.role != "CUSTOMER":
                continue
            reasons = []
            review = f.data.get("receiving_scope_review", {})
            if (
                not org.active
                or org.verification != "VERIFIED"
                or not f.active
                or f.registration != "VERIFIED"
                or expired(f.valid_until)
                or not review.get("valid_until")
                or expired(review["valid_until"])
            ):
                reasons.append(
                    {
                        "code": "CUSTOMER_QUALIFICATION_REQUIRED",
                        "message": "Customer facility and application receiving qualification must be current.",
                    }
                )
            if (
                "SECOND_LIFE_SYSTEM"
                not in f.data.get("verified_receiving_categories", [])
                or asset.mass_kg is None
                or (f.data.get("receiving_capacity_kg") or 0) < asset.mass_kg
            ):
                reasons.append(
                    {
                        "code": "CUSTOMER_SCOPE_CAPACITY_REQUIRED",
                        "message": "Verified intended product category and sufficient known capacity required.",
                    }
                )
            projected = SimpleNamespace(
                kind="PRODUCT",
                mass_kg=asset.mass_kg,
                data={
                    "category": "SECOND_LIFE_SYSTEM",
                    "synthetic": asset.data.get("synthetic", False),
                },
            )
            ts = [
                t
                for t in carriers
                if any(
                    not carrier_check(
                        db,
                        projected,
                        t,
                        SimpleNamespace(lat=p[0], lng=p[1]),
                        f,
                        asset.data.get("window_start") or future(days=1),
                        asset.data.get("window_end") or future(days=2),
                    )
                    for p in previous
                )
            ]
            if not ts:
                reasons.append(
                    {
                        "code": "NO_QUALIFIED_TRANSPORTER",
                        "message": "No qualified service connects an integrator to the customer.",
                    }
                )
            if APP_ENV == "production" and org.synthetic:
                reasons.append(
                    {
                        "code": "EXAMPLE_QUALIFICATION_DISABLED",
                        "message": "Example credentials do not support production operations.",
                    }
                )
            if reasons:
                rejected.append(
                    {
                        "operation": "DEPLOYMENT",
                        "facility_id": f.id,
                        "name": f.name,
                        "reasons": reasons,
                    }
                )
            else:
                customers.append(
                    {
                        "facility_id": f.id,
                        "name": f.name,
                        "organisation_id": f.organisation_id,
                        "transporters": [{"id": t.id, "name": t.name} for t in ts],
                        "operation": "DEPLOYMENT",
                    }
                )
        stages.append({"operation": "DEPLOYMENT", "receivers": customers})
    # Projected outputs are never certified by source battery scope: each later handoff must be revalidated.
    return {
        "complete": all(s["receivers"] for s in stages),
        "stages": stages,
        "receivers": stages[0]["receivers"] if stages else [],
        "rejected": rejected,
        "information_required": asset.mass_kg is None
        or asset.lat is None
        or asset.lng is None
        or not asset.data.get("window_start")
        or not asset.data.get("window_end"),
        "conditions": (
            [
                "Projected output mass uses source input mass as a conservative planning allowance, not a measured yield or product weight. Added components may require more capacity. Each output requires measured quantity, composition/specification, receiver acceptance and output-specific transport revalidation at its handoff. No chain is contracted or reserved."
            ]
            if path in ["SECOND_LIFE", "RECYCLING"]
            else []
        ),
    }
