from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from pydantic import Field
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import get, fail, audit, idem, exception
from .schemas import Schema
from .circular_schemas import (
    HandoffEventIn,
    ReviewIn,
)
from .services.circularity import enforce
from .services.downstream import (
    carrier_check,
    custody,
    handoff_access,
    handoff_detail,
    receiver_check,
    terms,
)

router = APIRouter(prefix="/circularity", tags=["downstream shipments"])


@router.post("/handoffs/{id}/events")
def physical(
    id: str,
    body: HandoffEventIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    h = get(db, m.DownstreamHandoff, id)
    if not handoff_access(db, user, h) or has_role(user, "REVIEWER"):
        fail("FORBIDDEN", "Only physical shipment participants may act.", status=403)

    def record():
        item = get(db, m.CircularItem, h.item_id)
        if item.state == "HOLD" and body.state != "DISPUTED":
            fail(
                "SAFETY_REVIEW_REQUIRED",
                "Held items cannot move or close; obtain qualified review without automatic redirection.",
            )
        carrier = get(db, m.TransporterProfile, h.transporter_id)
        carrier_org = carrier.organisation_id
        before = h.state
        expected = {
            "BOOKED": {"PICKED_UP"},
            "PICKED_UP": {"ARRIVED"},
            "ARRIVED": {"RECEIVED", "DISPUTED"},
            "RECEIVED": {"CLOSED"},
        }
        if body.state not in expected.get(before, set()):
            fail(
                "STATE_TRANSITION_INVALID",
                f"{before} cannot transition to {body.state}.",
            )
        if body.state in ["PICKED_UP", "RECEIVED", "DISPUTED"] and not body.physical:
            fail(
                "PHYSICAL_CONFIRMATION_REQUIRED",
                "Scheduled time cannot change custody.",
            )
        if body.state == "PICKED_UP":
            if (
                item.state != "ALLOCATED"
                or item.owner_org_id != h.seller_org_id
                or item.custodian_org_id != h.seller_org_id
            ):
                fail(
                    "INPUT_SCOPE_CHANGED",
                    "Booked ownership, custody or availability changed before pickup.",
                )
            source = get(db, m.Facility, h.data["route"]["stops"][0])
            target = get(db, m.Facility, h.receiver_facility_id)
            enforce(
                carrier_check(
                    db,
                    item,
                    carrier,
                    source,
                    target,
                    h.data["window_start"],
                    h.data["window_end"],
                    exclude=h.id,
                )
            )
            if user.organisation_id not in [
                h.seller_org_id,
                carrier_org,
            ] or not has_role(
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
                "TRANSPORTER",
            ):
                fail(
                    "FORBIDDEN",
                    "Sender and assigned carrier must confirm pickup.",
                    status=403,
                )
            if not body.condition_matches:
                h.state = "DISPUTED"
                item.state = "HOLD"
                exception(
                    db,
                    "handoff",
                    h.id,
                    "PICKUP_DISCREPANCY",
                    h.seller_org_id,
                    "Qualified review required before movement.",
                    evidence=body.evidence,
                )
                return handoff_detail(db, h)
            approvals = {
                **h.data.get("physical_confirmations", {}),
                user.organisation_id: {
                    "actor_id": user.id,
                    "evidence": body.evidence,
                    "timestamp": m.now(),
                },
            }
            h.data = {**h.data, "physical_confirmations": approvals}
            if not {h.seller_org_id, carrier_org} <= set(approvals):
                audit(db, user, "handoff", h, "PICKUP_CONFIRMATION")
                return {**handoff_detail(db, h), "pending_confirmation": True}
            custody(db, user, h, item, carrier_org, "PICKUP", body.evidence)
            item.state = "IN_SHIPMENT"
            item.facility_id = None
        elif body.state == "ARRIVED":
            if user.organisation_id != carrier_org:
                fail("FORBIDDEN", "Assigned carrier records arrival.", status=403)
        elif body.state in ["RECEIVED", "DISPUTED"]:
            if user.organisation_id != h.buyer_org_id or not has_role(
                user,
                "BUYER",
                "REFURBISHER",
                "SECOND_LIFE",
                "RECYCLER",
                "PROCESSOR",
                "REFINER",
                "MANUFACTURER",
                "CUSTOMER",
            ):
                fail(
                    "FORBIDDEN",
                    "Assigned receiver must record physical receipt.",
                    status=403,
                )
            if not body.condition_matches or body.state == "DISPUTED":
                h.state = "DISPUTED"
                item.state = "HOLD"
                exception(
                    db,
                    "handoff",
                    h.id,
                    "RECEIPT_DISCREPANCY",
                    h.buyer_org_id,
                    "Resolve documented receiving discrepancy; custody and title remain unchanged.",
                    evidence=body.evidence,
                )
                audit(db, user, "handoff", h, "DISPUTED_RECEIPT")
                return handoff_detail(db, h)
            enforce(
                receiver_check(
                    db,
                    item,
                    get(db, m.Facility, h.receiver_facility_id),
                    h.data["window_end"],
                )
            )
            custody(
                db, user, h, item, h.buyer_org_id, "ACCEPTED_RECEIPT", body.evidence
            )
            item.owner_org_id = h.buyer_org_id
            item.facility_id = h.receiver_facility_id
            item.state = "RETIRED" if h.data.get("retired_product") else "AVAILABLE"
            item.data = {
                **item.data,
                "receiving_acceptance_evidence": body.evidence,
                "acceptance_specification": terms(db, h).data[
                    "acceptance_specification"
                ],
            }
        elif body.state == "CLOSED":
            if user.organisation_id != h.buyer_org_id:
                fail("FORBIDDEN", "Receiver records closure.", status=403)
            if h.data.get("settlement") != "CONFIRMED" or db.scalar(
                select(m.ExceptionCase).where(
                    m.ExceptionCase.object_type == "handoff",
                    m.ExceptionCase.object_id == h.id,
                    m.ExceptionCase.status != "CLOSED",
                )
            ):
                fail(
                    "CLOSURE_BLOCKED",
                    "Receipt, payee-confirmed record-only settlement and resolved exceptions required.",
                )
            for x in db.scalars(
                select(m.HandoffAllocation).where(
                    m.HandoffAllocation.handoff_id == h.id
                )
            ):
                x.active = False
        h.state = body.state
        audit(
            db,
            user,
            "handoff",
            h,
            "PHYSICAL_EVENT",
            before=before,
            after=h.state,
            evidence=body.evidence,
        )
        return handoff_detail(db, h)

    return idem(
        db,
        user,
        idempotency_key,
        "handoff-event",
        {"id": id, **body.model_dump(mode="json")},
        record,
    )


class PaymentIn(Schema):
    status: str = Field(pattern="^(REPORTED|CONFIRMED)$")
    evidence: str = Field(min_length=3, max_length=4000)


@router.post("/handoffs/{id}/settlement")
def payment(
    id: str,
    body: PaymentIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    h = get(db, m.DownstreamHandoff, id)
    if h.state != "RECEIVED":
        fail(
            "RECEIPT_REQUIRED", "Accepted physical receipt required before settlement."
        )
    expected = h.buyer_org_id if body.status == "REPORTED" else h.seller_org_id
    if user.organisation_id != expected or not has_role(
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
        fail(
            "FORBIDDEN",
            "Buyer reports payment; seller separately confirms receipt.",
            status=403,
        )
    if body.status == "CONFIRMED" and h.data.get("settlement") != "REPORTED":
        fail("PAYMENT_REPORT_REQUIRED", "Payer must first report payment.")
    h.data = {
        **h.data,
        "settlement": body.status,
        "settlement_history": [
            *h.data.get("settlement_history", []),
            {
                **body.model_dump(),
                "actor_id": user.id,
                "timestamp": m.now(),
                "record_only": True,
            },
        ],
    }
    audit(db, user, "handoff", h, "RECORD_ONLY_SETTLEMENT", status=body.status)
    return handoff_detail(db, h)


@router.post("/handoffs/{id}/resolve")
def resolve(
    id: str,
    body: ReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    h = get(db, m.DownstreamHandoff, id)
    if h.state not in ["DISPUTED", "RECEIVED", "CONTRACTED"]:
        fail("STATE_TRANSITION_INVALID", "No recoverable discrepancy in this state.")
    if not body.accepted:
        fail("DISPUTE_UNRESOLVED", "Rejected review retains hold.")
    for c in db.scalars(
        select(m.ExceptionCase).where(
            m.ExceptionCase.object_type == "handoff",
            m.ExceptionCase.object_id == id,
            m.ExceptionCase.status != "CLOSED",
        )
    ):
        if c.category not in ["QUOTE_OVER_BUDGET", "RECEIPT_DISCREPANCY"]:
            fail(
                "MANUAL_ESCALATION_REQUIRED",
                "Pickup/safety incident requires qualified manual escalation, not generic resume.",
            )
        c.status = "CLOSED"
        c.resolution = body.reason
        c.data = {
            **c.data,
            "resolution_evidence": body.evidence,
            "reviewer_id": user.id,
        }
    if h.state == "DISPUTED":
        h.state = "ARRIVED"
        get(db, m.CircularItem, h.item_id).state = "IN_SHIPMENT"
    audit(db, user, "handoff", h, "DOCUMENTED_DISPUTE_RESOLUTION", **body.model_dump())
    return handoff_detail(db, h)
