from .auth import has_role
from fastapi import APIRouter, Depends
from sqlalchemy import select
from . import models as m
from .db import get_db
from .auth import current_user, role, can_view_asset
from .common import get, fail, dump, audit, expired, exception
from .circular_schemas import AssessmentIn, AssessmentReportIn, ReviewIn
from .services.circularity import (
    capability_check,
    enforce,
    operation_role,
    own_facility,
)

router = APIRouter(prefix="/circularity", tags=["assessment"])


@router.get("/assessments")
def assessments(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        dump(a)
        for a in db.scalars(
            select(m.Assessment).order_by(m.Assessment.created_at.desc())
        )
        if has_role(user, "REVIEWER")
        or get(db, m.Facility, a.facility_id).organisation_id == user.organisation_id
        or can_view_asset(db, user, get(db, m.BatteryAsset, a.asset_id))
    ]


@router.post("/assessments")
def assign(
    body: AssessmentIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    asset = get(db, m.BatteryAsset, body.asset_id)
    if user.organisation_id not in [
        asset.owner_org_id,
        asset.current_holder_org_id,
    ] and not has_role(user, "REVIEWER"):
        fail(
            "FORBIDDEN",
            "Only an owner, custodian or reviewer may request assessment.",
            status=403,
        )
    f = get(db, m.Facility, body.facility_id)
    # Assessment assignments may precede physical transport. Unknown mass cannot reserve processing capacity.
    enforce(
        capability_check(
            db,
            f,
            "ASSESSMENT",
            asset.mass_kg,
            asset.chemistry,
            asset.form,
            scope_only=True,
            asset=asset,
        )
    )
    if body.revision_of:
        prior = get(db, m.Assessment, body.revision_of)
        if (
            prior.asset_id != asset.id
            or prior.intended_operation != body.intended_operation
        ):
            fail(
                "REVISION_SCOPE_INVALID",
                "Revision must concern the same asset and operation.",
            )
    obj = m.Assessment(
        **body.model_dump(exclude={"procedure"}, mode="json"),
        requested_by=user.id,
        data={
            "procedure": body.procedure,
            "source": "OWNER_REQUESTED",
            "synthetic": asset.data.get("synthetic", False),
        },
    )
    db.add(obj)
    db.flush()
    audit(db, user, "assessment", obj, "ASSIGN")
    return dump(obj)


@router.post("/assessments/{id}/submit")
def submit(
    id: str,
    body: AssessmentReportIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    obj = get(db, m.Assessment, id)
    own_facility(db, user, obj.facility_id)
    operation_role(user, "ASSESSMENT")
    if obj.state != "ASSIGNED":
        fail(
            "STATE_TRANSITION_INVALID",
            "Submitted assessment is immutable; create a revision instead.",
        )
    asset = get(db, m.BatteryAsset, obj.asset_id)
    if asset.current_holder_org_id != user.organisation_id:
        fail(
            "CUSTODY_EVIDENCE_MISSING",
            "Measured assessment requires physical custody; assignment alone does not prove receipt.",
        )
    obj.state = "SUBMITTED"
    obj.operator_id = user.id
    obj.data = {
        **obj.data,
        "report": body.model_dump(mode="json"),
        "source": "TECHNICIAN_RECORDED",
        "submitted_at": m.now(),
    }
    from .services.registration import critical_report

    if critical_report(
        {"additional_information": body.observations + " " + body.limitations}
    ):
        asset.data = {**asset.data, "critical_report_unresolved": True}
        asset.state = "HOLD"
        exception(
            db,
            "battery",
            asset.id,
            "SAFETY_FLAG",
            "org-review",
            "A technician reported an explicit critical hazard. Obtain qualified handling instructions; no routine dispatch.",
            "HIGH",
            assessment_id=obj.id,
        )
    audit(db, user, "assessment", obj, "SUBMIT_ASSESSMENT")
    return dump(obj)


@router.post("/assessments/{id}/review")
def review(
    id: str,
    body: ReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    obj = get(db, m.Assessment, id)
    if obj.state != "SUBMITTED" or obj.operator_id == user.id:
        fail(
            "INDEPENDENT_REVIEW_REQUIRED",
            "A submitted assessment needs independent review; create a revision for corrections.",
        )
    if expired(body.valid_until):
        fail("QUALIFICATION_EXPIRED", "Assessment review must have a current expiry.")
    asset = get(db, m.BatteryAsset, obj.asset_id)
    enforce(
        capability_check(
            db,
            get(db, m.Facility, obj.facility_id),
            "ASSESSMENT",
            asset.mass_kg,
            asset.chemistry,
            asset.form,
            scope_only=True,
            asset=asset,
        )
    )
    obj.state = "ACCEPTED" if body.accepted else "REJECTED"
    obj.reviewer_id = user.id
    obj.valid_until = body.valid_until
    obj.data = {
        **obj.data,
        "review": body.model_dump(),
        "reviewed_at": m.now(),
        "source": "QUALIFIED_FACILITY_ASSESSMENT",
    }
    audit(db, user, "assessment", obj, "REVIEW_ASSESSMENT")
    return dump(obj)
