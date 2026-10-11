from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import get, fail, audit, idem, expired, exception
from .services.circularity import enforce
from .services.downstream import (
    allocations,
    carrier_check,
    distance,
    handoff_detail,
    receiver_check,
    receiving_operation,
    terms,
)

router = APIRouter(prefix="/circularity", tags=["downstream logistics"])


@router.post("/handoffs/{id}/book")
def book(
    id: str,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    h = get(db, m.DownstreamHandoff, id)
    t = terms(db, h)
    if user.organisation_id != t.payer_org_id or not has_role(
        user,
        "ORIGINATOR",
        "BUYER",
        "REFURBISHER",
        "SECOND_LIFE",
        "RECYCLER",
        "PROCESSOR",
        "REFINER",
        "MANUFACTURER",
        "CUSTOMER",
    ):
        fail("FORBIDDEN", "Named commercial payer must accept and book.", status=403)

    def booking():
        q = h.data.get("quote")
        item = get(db, m.CircularItem, h.item_id)
        if (
            h.state != "CONTRACTED"
            or not q
            or expired(q["expires_at"])
            or q["terms_version"] != h.version
        ):
            fail(
                "QUOTE_REQUIRED",
                "A current, explicitly submitted transporter quote is required.",
            )
        if t.budget_paise is None or q["total_paise"] > t.budget_paise:
            exception(
                db,
                "handoff",
                h.id,
                "QUOTE_OVER_BUDGET",
                t.payer_org_id,
                "Seek another quote or approve a new terms version with both parties.",
                quote_id=q["quote_id"],
                overrun_paise=(
                    None
                    if t.budget_paise is None
                    else q["total_paise"] - t.budget_paise
                ),
            )
            db.commit()
            fail(
                "QUOTE_OVER_BUDGET",
                "Quote exceeds the responsible payer’s approved logistics cap.",
            )
        if (
            item.state not in ["AVAILABLE", "RETIRED"]
            or item.owner_org_id != h.seller_org_id
            or item.custodian_org_id != h.seller_org_id
        ):
            fail("INPUT_SCOPE_CHANGED", "Ownership, custody or availability changed.")
        carrier = get(db, m.TransporterProfile, q["transporter_id"])
        source = get(db, m.Facility, item.facility_id)
        f = get(db, m.Facility, h.receiver_facility_id)
        enforce(
            carrier_check(
                db,
                item,
                carrier,
                source,
                f,
                h.data["window_start"],
                h.data["window_end"],
            )
        )
        enforce(receiver_check(db, item, f, h.data["window_end"]))
        if not q["acceptance_specification_confirmed"]:
            fail(
                "QUOTE_SCOPE_INCOMPLETE",
                "Carrier must confirm the declared handling/acceptance documentation scope.",
            )
        cap = db.scalar(
            select(m.OperationCapability).where(
                m.OperationCapability.facility_id == f.id,
                m.OperationCapability.operation == receiving_operation(item),
            )
        )
        maximum = cap.capacity_kg if cap else f.data.get("receiving_capacity_kg")
        if (
            maximum is None
            or item.mass_kg is None
            or allocations(
                db, "FACILITY", f.id, h.data["window_start"], h.data["window_end"]
            )
            + item.mass_kg
            > maximum
        ):
            fail(
                "CAPACITY_CONFLICT",
                "Receiving capacity must be known and cannot be overbooked.",
            )
        for kind, resource in [("TRANSPORTER", carrier.id), ("FACILITY", f.id)]:
            db.add(
                m.HandoffAllocation(
                    handoff_id=h.id,
                    resource_type=kind,
                    resource_id=resource,
                    mass_kg=item.mass_kg,
                    starts_at=h.data["window_start"],
                    ends_at=h.data["window_end"],
                )
            )
        h.transporter_id = carrier.id
        h.state = "BOOKED"
        item.state = "ALLOCATED"
        h.data = {
            **h.data,
            "accepted_quote_id": q["quote_id"],
            "booked_by": user.id,
            "route": {
                "stops": [source.id, f.id],
                "distance_km": round(
                    distance([source.lat, source.lng], [f.lat, f.lng]) * 1.3, 2
                ),
                "source": "HAVERSINE_X_1.3_PROXY",
                "warnings": [
                    "Not verified road distance or live ETA",
                    "Direct route only for downstream products/materials",
                ],
            },
        }
        audit(db, user, "handoff", h, "QUOTE_ACCEPTED_AND_CAPACITY_BOOKED")
        db.flush()
        return handoff_detail(db, h)

    return idem(db, user, idempotency_key, "book-handoff", {"id": id}, booking)


@router.get("/quote-requests")
def quote_requests(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    role(user, "TRANSPORTER")
    requests = []
    carriers = db.scalars(
        select(m.TransporterProfile).where(
            m.TransporterProfile.organisation_id == user.organisation_id
        )
    ).all()
    for h in db.scalars(
        select(m.DownstreamHandoff).where(m.DownstreamHandoff.state == "CONTRACTED")
    ):
        item = get(db, m.CircularItem, h.item_id)
        if not item.facility_id:
            continue
        source = get(db, m.Facility, item.facility_id)
        target = get(db, m.Facility, h.receiver_facility_id)
        for carrier in carriers:
            reasons = carrier_check(
                db,
                item,
                carrier,
                source,
                target,
                h.data["window_start"],
                h.data["window_end"],
            )
            if not reasons:
                requests.append(
                    {
                        "handoff_id": h.id,
                        "transporter_id": carrier.id,
                        "kind": item.kind,
                        "category": item.data.get("category"),
                        "mass_kg": item.mass_kg,
                        "source_facility_id": source.id,
                        "receiver_facility_id": target.id,
                        "window_start": h.data["window_start"],
                        "window_end": h.data["window_end"],
                        "required_handling_specification": terms(db, h).data[
                            "acceptance_specification"
                        ],
                        "synthetic": item.data.get("synthetic", False),
                    }
                )
    return requests
