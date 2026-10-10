from fastapi import APIRouter, Depends
from sqlalchemy import select
from . import models as m
from .auth import current_user, role, can_view_asset
from .db import get_db
from .common import get, dump, fail, audit
from .schemas import ResolveIn, Schema
from .services.shipments import context

router = APIRouter()


def visible(db, user, c):
    if user.role == "REVIEWER" or user.organisation_id == c.owner_org_id:
        return True
    if c.object_type == "battery":
        return can_view_asset(db, user, get(db, m.BatteryAsset, c.object_id))
    if c.object_type == "transaction":
        return can_view_asset(
            db,
            user,
            get(db, m.BatteryAsset, get(db, m.SaleTransaction, c.object_id).asset_id),
        )
    if c.object_type == "shipment":
        return can_view_asset(
            db, user, context(db, get(db, m.Shipment, c.object_id))[1]
        )
    return False


@router.get("/exceptions")
def exceptions(db=Depends(get_db), user=Depends(current_user)):
    return [
        dump(c)
        for c in db.scalars(
            select(m.ExceptionCase).order_by(m.ExceptionCase.created_at.desc())
        ).all()
        if visible(db, user, c)
    ]


@router.post("/exceptions/{id}/resolve")
def resolve(id: str, body: ResolveIn, db=Depends(get_db), user=Depends(current_user)):
    role(user, "REVIEWER")
    c = get(db, m.ExceptionCase, id)
    if c.status == "CLOSED":
        return dump(c)
    if c.category in ["SAFETY_FLAG", "SAFETY_REVIEW_REQUIRED"] and body.resume:
        fail(
            "SAFETY_REVIEW_REQUIRED",
            "Generic exception resolution cannot clear a reported hazard. Record qualified review; controlled handling is held until a matching specialist is available.",
        )
    if body.resume and c.object_type == "shipment":
        s = get(db, m.Shipment, c.object_id)
        tx, asset, _ = context(db, s)
        if c.category == "RECEIPT_DISPUTE":
            s.state = "ARRIVED_PENDING_RECEIPT"
            asset.state = "IN_SHIPMENT"
            s.data = {**s.data, "review_resolution": body.model_dump()}
        elif s.state == "EXCEPTION_HOLD" and c.category == "CONDITION_MISMATCH":
            # Scope correction needs evidence, and no critical flag can be bypassed.
            if any(v != "NO" for v in asset.data.get("flags", {}).values()):
                fail(
                    "SAFETY_FLAG_PRESENT",
                    "Original critical flags still require qualified handling.",
                )
            s.state = s.data.get("resume_state", "PICKUP_SCHEDULED")
            asset.state = "AGREED" if s.state == "PICKUP_SCHEDULED" else "IN_SHIPMENT"
    c.status = "CLOSED"
    c.resolution = body.resolution
    c.data = {
        **c.data,
        "resolution_evidence": body.evidence,
        "closed_at": m.now(),
        "closed_by": user.id,
    }
    audit(db, user, "exception", c, "RESOLVE", **body.model_dump())
    return dump(c)


class QualifiedReviewIn(Schema):
    decision: str
    qualification_evidence: str
    report: str
    handling_scope: str
    valid_until: str
    conditions: str


@router.post("/exceptions/{id}/qualified-review")
def qualified(
    id: str, body: QualifiedReviewIn, db=Depends(get_db), user=Depends(current_user)
):
    role(user, "REVIEWER")
    c = get(db, m.ExceptionCase, id)
    if c.category not in ["SAFETY_FLAG", "SAFETY_REVIEW_REQUIRED"]:
        fail("STATE_TRANSITION_INVALID", "This is not a safety review case.")
    from .common import expired

    if (
        not body.qualification_evidence
        or not body.report
        or not body.handling_scope
        or expired(body.valid_until)
    ):
        fail(
            "FIELD_REQUIRED",
            "A valid scoped qualified report and qualification evidence are required.",
        )
    if body.decision not in [
        "INFORMATION_INSUFFICIENT",
        "QUALIFIED_ASSESSMENT_REQUIRED",
        "SCOPED_CLEARANCE",
        "ESCALATE",
    ]:
        fail("VALIDATION_ERROR", "Unsupported review decision.")
    c.data = {
        **c.data,
        "qualified_reviews": [
            *c.data.get("qualified_reviews", []),
            {**body.model_dump(), "actor_id": user.id, "timestamp": m.now()},
        ],
    }
    c.status = "UNDER_REVIEW"
    c.next_action = "Obtain qualified assessment or manual outreach; ordinary workflow remains held."
    if body.decision == "SCOPED_CLEARANCE":
        if body.handling_scope != "CONTROLLED_HANDLING":
            fail(
                "SAFETY_SCOPE_MISMATCH",
                "This MVP supports explicitly scoped CONTROLLED_HANDLING; no blanket safety clearance.",
            )
        from .services.matching import eligible_buyers, transporter_check

        asset = (
            get(db, m.BatteryAsset, c.object_id)
            if c.object_type == "battery"
            else context(db, get(db, m.Shipment, c.object_id))[1]
        )
        asset.data = {
            **asset.data,
            "handling_clearance": {
                **body.model_dump(),
                "reviewer_id": user.id,
                "timestamp": m.now(),
                "source_exception_id": c.id,
            },
        }
        previous = asset.state
        asset.state = "READY_FOR_LISTING"
        receivers = [
            x for x in eligible_buyers(db, asset, "QUALIFIED_REVIEW") if x["eligible"]
        ]
        transports = (
            []
            if asset.lat is None or asset.lng is None
            else [
                t
                for t in db.scalars(select(m.TransporterProfile)).all()
                if not transporter_check(db, asset, t, [[asset.lat, asset.lng]])
            ]
        )
        if not receivers or not transports:
            asset.state = "HOLD"
            c.next_action = "No eligible scoped specialist currently available. Manual network-operator outreach required; do not relax constraints."
        elif c.object_type == "shipment":
            asset.state = "HOLD"
            c.next_action = "Incident shipment requires explicitly revised controlled-handling terms and a new eligible plan; cancellation/redirect review remains manual."
        else:
            c.status = "CLOSED"
            c.resolution = "Qualified scoped report recorded; original flags retained. Only controlled-handling specialist pathways are permitted."
            c.data = {
                **c.data,
                "resolution_evidence": body.report,
                "closed_by": user.id,
                "closed_at": m.now(),
            }
            c.next_action = "Create a controlled-handling listing and obtain explicit specialist and transporter acceptance."
        audit(
            db,
            user,
            "battery",
            asset,
            "SCOPED_HANDLING_DECISION",
            before=previous,
            after=asset.state,
            clearance=asset.data["handling_clearance"],
        )
    audit(db, user, "exception", c, "QUALIFIED_REVIEW", **body.model_dump())
    return dump(c)


@router.get("/audit/{kind}/{id}")
def history(kind: str, id: str, db=Depends(get_db), user=Depends(current_user)):
    if user.role != "REVIEWER":
        if kind == "battery":
            allowed = can_view_asset(db, user, get(db, m.BatteryAsset, id))
        elif kind == "transaction":
            allowed = can_view_asset(
                db,
                user,
                get(db, m.BatteryAsset, get(db, m.SaleTransaction, id).asset_id),
            )
        elif kind == "shipment":
            allowed = can_view_asset(db, user, context(db, get(db, m.Shipment, id))[1])
        else:
            allowed = False
        if not allowed:
            fail("FORBIDDEN", "Audit access is restricted.", status=403)
    return [
        dump(x)
        for x in db.scalars(
            select(m.AuditEvent)
            .where(m.AuditEvent.object_type == kind, m.AuditEvent.object_id == id)
            .order_by(m.AuditEvent.created_at)
        ).all()
    ]
