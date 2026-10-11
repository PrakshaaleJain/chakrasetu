from ..auth import has_role
from ..config import APP_ENV
from sqlalchemy import select
from .. import models as m
from ..common import get, fail, expired, parse_time, dump, audit
from ..services.matching import distance, available
from .circularity import capability_check, enforce


def handoff_access(db, user, h):
    t = get(db, m.TransporterProfile, h.transporter_id) if h.transporter_id else None
    return has_role(user, "REVIEWER") or user.organisation_id in [
        h.seller_org_id,
        h.buyer_org_id,
        t.organisation_id if t else None,
    ]


def terms(db, h):
    return db.scalar(
        select(m.HandoffTerms).where(
            m.HandoffTerms.handoff_id == h.id, m.HandoffTerms.version == h.version
        )
    )


def receiving_operation(item):
    if item.kind == "PRODUCT":
        return (
            "RECYCLING" if item.data.get("lifecycle_retired") else None
        )  # receiving customer/integrator scope verified separately below
    return {
        "BLACK_MASS": "REFINING",
        "REFINED_LITHIUM": "MANUFACTURING",
        "COPPER": "PROCESSING",
        "ALUMINIUM": "PROCESSING",
    }.get(item.data.get("category"), "PROCESSING")


def receiver_check(db, item, f, end):
    operation = receiving_operation(item)
    reasons = []
    org = get(db, m.Organisation, f.organisation_id)
    if APP_ENV == "production" and (org.synthetic or item.data.get("synthetic")):
        reasons.append(
            {
                "code": "SYNTHETIC_DISABLED",
                "message": "Synthetic items and receivers cannot support production booking.",
            }
        )
    if (
        org.verification != "VERIFIED"
        or not org.active
        or f.registration != "VERIFIED"
        or not f.active
        or expired(f.valid_until)
        or parse_time(f.valid_until) < parse_time(end)
    ):
        reasons.append(
            {
                "code": "RECEIVER_UNQUALIFIED",
                "message": "Receiving identity and facility registration must be current through the collection window.",
            }
        )
    if operation:
        reasons.extend(
            capability_check(
                db,
                f,
                operation,
                item.mass_kg,
                category=item.data.get("category", "UNKNOWN"),
            )
        )
    else:
        if item.data.get("category") == "SECOND_LIFE_SYSTEM":
            product = db.scalar(
                select(m.SecondLifeProduct).where(
                    m.SecondLifeProduct.item_id == item.id
                )
            )
            if not product or product.state not in ["ACCEPTED", "RETIRED"]:
                reasons.append(
                    {
                        "code": "PRODUCT_ACCEPTANCE_REQUIRED",
                        "message": "System acceptance must be documented before downstream contracting.",
                    }
                )
        scopes = f.data.get("verified_receiving_categories", [])
        validity = f.data.get("receiving_scope_review", {}).get("valid_until")
        if not validity or expired(validity) or parse_time(validity) < parse_time(end):
            reasons.append(
                {
                    "code": "RECEIVING_SCOPE_EXPIRED",
                    "message": "Product receiving qualification must cover the pickup window.",
                }
            )
        if item.data.get("category") not in scopes:
            reasons.append(
                {
                    "code": "PRODUCT_SPEC_UNSUPPORTED",
                    "message": "No verified receiving scope for this product application.",
                }
            )
    return reasons


def allocations(db, kind, id, start, end, exclude=None):
    return sum(
        x.mass_kg
        for x in db.scalars(
            select(m.HandoffAllocation).where(
                m.HandoffAllocation.resource_type == kind,
                m.HandoffAllocation.resource_id == id,
                m.HandoffAllocation.active == True,
            )
        )
        if x.handoff_id != exclude
        and parse_time(x.starts_at) <= parse_time(end)
        and parse_time(x.ends_at) >= parse_time(start)
    )


def carrier_check(db, item, t, source, target, start, end, exclude=None):
    reasons = []

    def reject(code, message):
        reasons.append({"code": code, "message": message})

    org = get(db, m.Organisation, t.organisation_id)
    if APP_ENV == "production" and (org.synthetic or item.data.get("synthetic")):
        reject(
            "SYNTHETIC_DISABLED",
            "Synthetic items and carriers cannot support production booking.",
        )
    if (
        org.verification != "VERIFIED"
        or not org.active
        or t.verification != "VERIFIED"
        or not t.active
        or expired(t.valid_until)
        or parse_time(t.valid_until) < parse_time(end)
    ):
        reject(
            "TRANSPORTER_UNQUALIFIED",
            "Carrier identity, qualification and validity must cover the shipment.",
        )
    validity = t.data.get("downstream_scope_review", {}).get("valid_until")
    if not validity or expired(validity) or parse_time(validity) < parse_time(end):
        reject(
            "TRANSPORT_SCOPE_EXPIRED",
            "Downstream scope review must cover the pickup window.",
        )
    if item.kind not in t.data.get("verified_downstream_kinds", []) or item.data.get(
        "category"
    ) not in t.data.get("verified_downstream_categories", []):
        reject(
            "TRANSPORT_SCOPE_UNVERIFIED",
            "Carrier needs verified material/product scope; battery-only qualification is insufficient.",
        )
    if item.mass_kg is None:
        reject("MASS_UNKNOWN", "Known shipment mass required.")
    else:
        # available() includes both old battery reservations and downstream allocations.
        free = available(db, "TRANSPORTER", t.id, t.capacity_kg, start, end)
        if exclude:
            free += sum(
                x.mass_kg
                for x in db.scalars(
                    select(m.HandoffAllocation).where(
                        m.HandoffAllocation.handoff_id == exclude,
                        m.HandoffAllocation.resource_type == "TRANSPORTER",
                        m.HandoffAllocation.active == True,
                    )
                )
            )
        if item.mass_kg > free:
            reject(
                "CAPACITY_CONFLICT",
                "Combined battery and downstream allocations exceed carrier capacity.",
            )
    center = t.data.get("center")
    radius = t.data.get("radius_km")
    if (
        not center
        or radius is None
        or any(distance(center, [f.lat, f.lng]) > radius for f in [source, target])
    ):
        reject(
            "COVERAGE_UNSUPPORTED",
            "Both stops must be inside the carrier’s configured coverage.",
        )
    if (
        not t.data.get("window_start")
        or not t.data.get("window_end")
        or parse_time(t.data["window_start"]) > parse_time(start)
        or parse_time(t.data["window_end"]) < parse_time(end)
    ):
        reject(
            "WINDOW_UNSUPPORTED",
            "Carrier must explicitly cover the requested pickup window.",
        )
    return reasons


def handoff_detail(db, h):
    item = get(db, m.CircularItem, h.item_id)
    return {
        **dump(h),
        "item": dump(item),
        "terms": dump(terms(db, h)),
        "history": [
            dump(x)
            for x in db.scalars(
                select(m.HandoffTerms).where(m.HandoffTerms.handoff_id == h.id)
            )
        ],
        "custody": [
            dump(x)
            for x in db.scalars(
                select(m.ItemCustodyEvent).where(m.ItemCustodyEvent.handoff_id == h.id)
            )
        ],
    }


def custody(db, user, h, item, new_org, event, evidence):
    obj = m.ItemCustodyEvent(
        handoff_id=h.id,
        item_id=item.id,
        actor_id=user.id,
        previous_org_id=item.custodian_org_id,
        new_org_id=new_org,
        event_type=event,
        data={
            "evidence": evidence,
            "physical": True,
            "timestamp": m.now(),
            "synthetic": item.data.get("synthetic", False),
        },
    )
    db.add(obj)
    item.custodian_org_id = new_org
    audit(
        db,
        user,
        "item",
        item,
        "PHYSICAL_CUSTODY_CHANGED",
        handoff_id=h.id,
        from_org=obj.previous_org_id,
        to_org=new_org,
    )
