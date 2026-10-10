from math import radians, sin, cos, atan2, sqrt
from datetime import datetime
from sqlalchemy import select
from .. import models as m
from ..common import expired, get, fail, dump, future, audit, exception, parse_time
from ..config import RULE_VERSION


def distance(a, b):
    lat1, lng1, lat2, lng2 = map(radians, [a[0], a[1], b[0], b[1]])
    h = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    )
    return 6371 * 2 * atan2(sqrt(h), sqrt(max(0, 1 - h)))


def active_reservations(db, resource_type, resource_id, start, end, exclude_tx=None):
    rows = db.scalars(
        select(m.CapacityReservation).where(
            m.CapacityReservation.resource_type == resource_type,
            m.CapacityReservation.resource_id == resource_id,
            m.CapacityReservation.starts_at < end,
            m.CapacityReservation.ends_at > start,
        )
    ).all()
    return sum(
        r.mass_kg
        for r in rows
        if r.transaction_id != exclude_tx
        and (
            r.status == "COMMITTED"
            or (r.status == "HELD" and not expired(r.expires_at))
        )
    )


def available(db, kind, id, cap, start, end, exclude_tx=None):
    return cap - active_reservations(db, kind, id, start, end, exclude_tx)


def service_valid(valid_until, end):
    return not expired(valid_until) and parse_time(valid_until) >= parse_time(end)


def handling_scope(asset):
    flags = asset.data.get("flags", {})
    if (
        len(flags) == 11
        and all(v == "NO" for v in flags.values())
        and asset.condition not in ["UNKNOWN", "DAMAGED_REPORTED"]
    ):
        return "ORDINARY"
    clearance = asset.data.get("handling_clearance")
    end = asset.data.get("window_end") or future(days=2)
    if (
        clearance
        and clearance.get("handling_scope") == "CONTROLLED_HANDLING"
        and service_valid(clearance["valid_until"], end)
    ):
        return "CONTROLLED_HANDLING"
    return "UNREVIEWED"


def ordinary(asset):
    # This gate permits ordinary movement or separately approved, scoped controlled handling.
    if asset.state in [
        "HOLD",
        "REVIEW_REQUIRED",
        "NEEDS_INFORMATION",
        "DRAFT",
        "CANCELLED",
        "CLOSED",
    ]:
        fail(
            "SAFETY_REVIEW_REQUIRED",
            "Asset is not eligible for movement.",
            next_action="Complete intake or resolve the tracked qualified review.",
        )
    if handling_scope(asset) == "UNREVIEWED":
        fail(
            "SAFETY_FLAG_PRESENT",
            "A valid scoped qualified report is required; ordinary movement is blocked.",
        )
    if not asset.authority_confirmed:
        fail("TRANSFER_AUTHORITY_UNCONFIRMED", "Transfer authority is unconfirmed.")


def facility_check(db, asset, facility, pathway, exclude_tx=None):
    reasons = []

    def reject(code, msg):
        reasons.append({"code": code, "message": msg, "blocking": True})

    org = get(db, m.Organisation, facility.organisation_id)
    start = asset.data.get("window_start") or future(days=1)
    end = asset.data.get("window_end") or future(days=2)
    if not org.active or org.verification != "VERIFIED":
        reject(
            "REGISTRATION_INVALID_OR_EXPIRED",
            "Organisation identity/activity verification is unavailable.",
        )
    if not facility.active:
        reject("FACILITY_CLOSED", "Facility is inactive.")
    if facility.registration != "VERIFIED" or not service_valid(
        facility.valid_until, end
    ):
        reject(
            "REGISTRATION_INVALID_OR_EXPIRED",
            "Facility registration is not valid throughout service window.",
        )
    if (
        facility.data.get("window_start", "") > start
        or facility.data.get("window_end", "") < end
    ):
        reject(
            "FACILITY_CLOSED", "Receiving window does not cover the planned interval."
        )
    caps = db.scalars(
        select(m.FacilityCapability).where(
            m.FacilityCapability.facility_id == facility.id,
            m.FacilityCapability.pathway == pathway,
        )
    ).all()
    if not caps:
        reject("PATHWAY_NOT_SUPPORTED", "Requested pathway is not supported.")
        return {
            "facility": dump(facility),
            "eligible": False,
            "reasons": reasons,
            "capability_id": None,
        }
    cap = caps[0]
    if cap.verification != "VERIFIED" or not service_valid(cap.valid_until, end):
        reject(
            "REGISTRATION_INVALID_OR_EXPIRED",
            "Capability is unverified or expires before service.",
        )
    if asset.chemistry not in cap.data.get("verified_chemistries", []):
        reject(
            "CHEMISTRY_NOT_ACCEPTED", f"{asset.chemistry} is not explicitly accepted."
        )
    if asset.form not in cap.data.get("forms", []):
        reject("FORM_FACTOR_NOT_ACCEPTED", f"{asset.form} form is not accepted.")
    if asset.condition not in cap.data.get("conditions", []):
        reject(
            "CONDITION_MISMATCH", "Reported condition is outside acceptance criteria."
        )
    if asset.state in ["HOLD", "REVIEW_REQUIRED"] or cap.data.get(
        "handling_scope"
    ) != handling_scope(asset):
        reject(
            "SAFETY_SCOPE_MISMATCH", "Handling scope is incompatible or under review."
        )
    if asset.mass_kg is None:
        reject(
            "VALUE_UNKNOWN",
            "Known total mass is required for capacity and route planning.",
        )
    elif (
        available(
            db,
            "CAPABILITY",
            cap.id,
            min(cap.capacity_kg, cap.available_kg),
            start,
            end,
            exclude_tx,
        )
        < asset.mass_kg
    ):
        reject(
            "CAPACITY_INSUFFICIENT",
            "Available capacity is less than the total asset mass.",
        )
    docs = {
        x.kind
        for x in db.scalars(
            select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == asset.id)
        ).all()
        if x.review_status == "VERIFIED" or x.kind != "TRANSFER_AUTHORITY"
    }
    for kind in cap.data.get("required_docs", []):
        if kind not in docs:
            reject("DOCUMENT_MISSING", f"Required evidence {kind} is missing.")
    if not asset.authority_confirmed:
        reject("TRANSFER_AUTHORITY_UNCONFIRMED", "Transfer authority is unconfirmed.")
    return {
        "facility": dump(facility),
        "eligible": not reasons,
        "reasons": reasons,
        "capability_id": cap.id,
    }


def eligible_buyers(db, asset, pathway=None, exclude_tx=None):
    results = []
    for f in db.scalars(
        select(m.Facility)
        .where(m.Facility.kind.in_(["RECEIVER", "REVIEW"]))
        .order_by(m.Facility.id)
    ).all():
        paths = (
            [pathway]
            if pathway
            else sorted(
                {
                    c.pathway
                    for c in db.scalars(
                        select(m.FacilityCapability).where(
                            m.FacilityCapability.facility_id == f.id
                        )
                    ).all()
                }
            )
        )
        for path in paths:
            results.append(
                {
                    **facility_check(db, asset, f, path, exclude_tx),
                    "pathway": path,
                    "rule_version": RULE_VERSION,
                }
            )
    return results


def transporter_check(db, asset, t, points, exclude_tx=None):
    reasons = []
    start = asset.data.get("window_start") or future(days=1)
    end = asset.data.get("window_end") or future(days=2)

    def reject(msg):
        reasons.append(
            {"code": "TRANSPORTER_SCOPE_MISMATCH", "message": msg, "blocking": True}
        )

    org = get(db, m.Organisation, t.organisation_id)
    if (
        not org.active
        or org.verification != "VERIFIED"
        or not t.active
        or t.verification != "VERIFIED"
        or not service_valid(t.valid_until, end)
    ):
        reject("Transporter identity/qualification is not current.")
    if (
        t.data.get("handling_scope") != handling_scope(asset)
        or asset.chemistry not in t.data.get("chemistries", [])
        or asset.form not in t.data.get("forms", [])
    ):
        reject("Chemistry, form or handling scope does not match.")
    if (
        asset.mass_kg is None
        or available(db, "TRANSPORTER", t.id, t.capacity_kg, start, end, exclude_tx)
        < asset.mass_kg
    ):
        reject("Vehicle mass capacity is unknown or insufficient.")
    center = t.data.get("center")
    radius = t.data.get("radius_km")
    if (
        not center
        or radius is None
        or any(distance(center, p) > radius for p in points)
    ):
        reject("Route leaves the declared service area.")
    if t.data.get("window_start", "") > start or t.data.get("window_end", "") < end:
        reject("Service window is unavailable.")
    return reasons


def route_scope(asset, tx, points):
    return {
        "asset_id": asset.id,
        "quantity": asset.quantity,
        "mass_kg": asset.mass_kg,
        "chemistry": asset.chemistry,
        "form": asset.form,
        "condition": asset.condition,
        "pathway": tx.pathway,
        "window_start": asset.data.get("window_start"),
        "window_end": asset.data.get("window_end"),
        "points": points,
        "handling_scope": handling_scope(asset),
        "clearance": asset.data.get("handling_clearance"),
    }


def validate_plan(db, tx, route, exclude_tx=None):
    asset = get(db, m.BatteryAsset, tx.asset_id)
    ordinary(asset)
    if (
        route.transaction_id != tx.id
        or route.terms_version != tx.terms_version
        or expired(route.expires_at)
    ):
        fail(
            "QUOTE_SCOPE_CHANGED",
            "Route expired or terms changed; generate a new plan.",
        )
    points = route.data["points"]
    if route.data["scope"] != route_scope(asset, tx, points):
        fail(
            "QUOTE_SCOPE_CHANGED",
            "Asset load or schedule changed; regenerate route and quote.",
        )
    for fid in [tx.facility_id] + ([route.hub_id] if route.hub_id else []):
        check = facility_check(
            db, asset, get(db, m.Facility, fid), tx.pathway, exclude_tx
        )
        if not check["eligible"]:
            fail(check["reasons"][0]["code"], check["reasons"][0]["message"])
    return asset


def generate_routes(db, tx, user):
    if tx.status != "AGREED_PENDING_LOGISTICS":
        fail(
            "TERMS_NOT_CONFIRMED", "Both parties must confirm the current terms first."
        )
    asset = get(db, m.BatteryAsset, tx.asset_id)
    ordinary(asset)
    if (
        asset.mass_kg is None
        or asset.lat is None
        or asset.lng is None
        or not asset.data.get("window_start")
        or not asset.data.get("window_end")
    ):
        fail(
            "VALUE_UNKNOWN",
            "Mass, pickup coordinates and time window are required for routes.",
            field="mass_kg",
        )
    if expired(asset.data["window_end"]):
        fail("FACILITY_CLOSED", "Pickup window has passed; agree a new window.")
    dest = get(db, m.Facility, tx.facility_id)
    rejected = []
    candidates = []
    check = facility_check(db, asset, dest, tx.pathway, tx.id)
    if not check["eligible"]:
        audit(
            db,
            user,
            "transaction",
            tx,
            "GENERATE_ROUTES",
            plans=[],
            rejected=[check],
            input_snapshot=dump(asset),
        )
        exception(
            db,
            "transaction",
            tx.id,
            "NO_ELIGIBLE_RECEIVER",
            tx.seller_org_id,
            "Resolve destination exclusions or request constrained outreach.",
            rejected=[check],
        )
        return {"candidates": [], "rejected": [check], "rule_version": RULE_VERSION}
    hubs = [None] + list(
        db.scalars(
            select(m.Facility).where(m.Facility.kind == "HUB").order_by(m.Facility.id)
        ).all()
    )
    for hub in hubs:
        if hub:
            check = facility_check(db, asset, hub, tx.pathway, tx.id)
            if not check["eligible"]:
                rejected.append(check)
                continue
        points = (
            [[asset.lat, asset.lng]]
            + ([[hub.lat, hub.lng]] if hub else [])
            + [[dest.lat, dest.lng]]
        )
        names = [asset.internal_id] + ([hub.name] if hub else []) + [dest.name]
        legs = [
            {
                "from": names[i],
                "to": names[i + 1],
                "distance_km": round(distance(points[i], points[i + 1]) * 1.3, 2),
                "source": "HAVERSINE_X_1.3_PROXY",
            }
            for i in range(len(points) - 1)
        ]
        km = sum(l["distance_km"] for l in legs)
        hours = round(km / 30 + (hub.data.get("dwell_hours", 2) if hub else 0), 2)
        start = datetime.fromisoformat(asset.data["window_start"])
        end = datetime.fromisoformat(asset.data["window_end"])
        if (end - start).total_seconds() < hours * 3600:
            rejected.append(
                {
                    "hub_id": hub.id if hub else None,
                    "reasons": [
                        {
                            "code": "FACILITY_CLOSED",
                            "message": "Travel and dwell proxy exceed agreed service window.",
                        }
                    ],
                }
            )
            continue
        transporters = []
        costs = []
        for t in db.scalars(
            select(m.TransporterProfile).order_by(m.TransporterProfile.id)
        ).all():
            reasons = transporter_check(db, asset, t, points, tx.id)
            if reasons:
                rejected.append(
                    {
                        "transporter_id": t.id,
                        "hub_id": hub.id if hub else None,
                        "reasons": reasons,
                    }
                )
                continue
            rate = t.data.get("rate_paise_per_km")
            cost = (
                round(
                    km * rate
                    + t.data["fixed_paise"] * len(legs)
                    + (hub.data.get("hub_fee_paise", 0) if hub else 0)
                )
                if rate is not None
                else None
            )
            transporters.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "estimated_cost_paise": cost,
                    "source": t.data.get("rate_source"),
                    "synthetic": True,
                }
            )
            if cost is not None:
                costs.append(cost)
        if not transporters:
            continue
        cost = min(costs) if costs else None
        plan = m.RoutePlan(
            transaction_id=tx.id,
            terms_version=tx.terms_version,
            hub_id=hub.id if hub else None,
            distance_km=km,
            hours=hours,
            estimated_cost_paise=cost,
            score=0,
            expires_at=future(minutes=60),
            data={
                "points": points,
                "stops": names,
                "legs": legs,
                "scope": route_scope(asset, tx, points),
                "transporters": transporters,
                "capability_ids": [check["capability_id"]] if hub else [],
                "source": "SYNTHETIC_CONFIGURED_RATE_CARD"
                if cost is not None
                else "UNKNOWN",
                "cost_status": "COMPLETE_ESTIMATE"
                if cost is not None
                else "INCOMPLETE",
                "rule_version": RULE_VERSION,
                "warnings": [
                    "Distance is a Haversine × 1.3 proxy, not verified road distance.",
                    "Time assumes 30 km/h; no real ETA or transporter commitment.",
                    "Revalidate capacity, registration, scope, quote and terms at booking.",
                ],
                "constraints": {
                    "destination": "PASS",
                    "hub": "PASS" if hub else "NOT_APPLICABLE",
                    "handling": "PASS",
                    "time": "PASS",
                    "authority": "PASS",
                    "capacity": "PASS",
                },
            },
        )
        candidates.append(plan)
    # Comparable cost objective only when every plan has complete estimates.
    complete = bool(candidates) and all(
        p.estimated_cost_paise is not None for p in candidates
    )

    def norm(values, value):
        return (
            (value - min(values)) / (max(values) - min(values))
            if max(values) != min(values)
            else 0
        )

    for p in candidates:
        tn = norm([x.hours for x in candidates], p.hours)
        cn = (
            norm([x.estimated_cost_paise for x in candidates], p.estimated_cost_paise)
            if complete
            else None
        )
        components = {
            "cost": 0.60 * cn if cn is not None else None,
            "time": (0.25 if complete else 0.80) * tn,
            "handling": 0.10 * (1 if p.hub_id else 0),
            "uncertainty": 0.05 if complete else 0.10,
        }
        p.score = round(sum(v for v in components.values() if v is not None), 6)
        p.data = {
            **p.data,
            "ranking": {
                "objective": "COST_TIME_HANDLING"
                if complete
                else "TIME_HANDLING_UNCERTAINTY",
                "weights": {
                    "cost": 0.60 if complete else 0,
                    "time": 0.25 if complete else 0.80,
                    "handling": 0.10,
                    "uncertainty": 0.05 if complete else 0.10,
                },
                "components": components,
                "normalisation": "min-max; equal range => 0",
            },
        }
        db.add(p)
    db.flush()
    candidates.sort(key=lambda p: (p.score, p.distance_km, p.hub_id or ""))
    audit(
        db,
        user,
        "transaction",
        tx,
        "GENERATE_ROUTES",
        input_snapshot=route_scope(asset, tx, []),
        plans=[p.id for p in candidates],
        rejected=rejected,
    )
    if not candidates:
        exception(
            db,
            "transaction",
            tx.id,
            "NO_ELIGIBLE_RECEIVER",
            tx.seller_org_id,
            "Review exclusions; request constrained manual outreach.",
        )
    return {
        "candidates": [dump(p) for p in candidates],
        "rejected": rejected,
        "rule_version": RULE_VERSION,
    }
