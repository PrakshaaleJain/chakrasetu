from sqlalchemy import select
from .. import models as m
from ..common import audit, exception
from ..enums import FLAGS, BatteryState
from ..config import RULE_VERSION


def screen_result(asset, evidence_kinds):
    reasons = []

    def reason(code, message, field, next_action):
        reasons.append(
            {
                "code": code,
                "message": message,
                "field": field,
                "blocking": True,
                "next_action": next_action,
            }
        )

    flags = asset.data.get("flags", {})
    # Safety overrides incomplete commercial information; never hide a warning behind a missing field.
    if (
        any(flags.get(f) == "YES" for f in FLAGS)
        or asset.condition == "DAMAGED_REPORTED"
    ):
        reason(
            "SAFETY_FLAG_PRESENT",
            "Reported damage or incident requires qualified review.",
            "flags",
            "Provide evidence to the designated reviewer; ordinary workflow remains held.",
        )
        state = BatteryState.HOLD
    elif (
        any(flags.get(f, "UNKNOWN") == "UNKNOWN" for f in FLAGS)
        or asset.condition == "UNKNOWN"
    ):
        reason(
            "SAFETY_REVIEW_REQUIRED",
            "Safety questionnaire or reported condition is incomplete.",
            "flags",
            "Request qualified review or provide the missing incident history.",
        )
        state = BatteryState.REVIEW_REQUIRED
    elif not asset.data.get("declaration"):
        reason(
            "FIELD_REQUIRED",
            "Originator declaration is required.",
            "declaration",
            "Confirm the declaration.",
        )
        state = BatteryState.NEEDS_INFORMATION
    elif not asset.authority_confirmed or "TRANSFER_AUTHORITY" not in evidence_kinds:
        reason(
            "TRANSFER_AUTHORITY_UNCONFIRMED",
            "Transfer authority needs confirmation and supporting evidence.",
            "authority_confirmed",
            "Upload transfer authority evidence and confirm your authority.",
        )
        state = BatteryState.REVIEW_REQUIRED
    else:
        state = BatteryState.READY_FOR_LISTING
        if asset.chemistry == "UNKNOWN" or asset.form == "UNKNOWN":
            reasons.append(
                {
                    "code": "VALUE_UNKNOWN",
                    "message": "Only capabilities explicitly accepting UNKNOWN can pass; routes still require known mass.",
                    "field": "chemistry",
                    "blocking": False,
                    "next_action": "Supply chemistry/form evidence when available.",
                }
            )
    return {
        "state": state,
        "screen": (
            "FLAG_PRESENT"
            if state == BatteryState.HOLD
            else (
                "UNKNOWN"
                if state == BatteryState.REVIEW_REQUIRED
                else "NO_FLAG_REPORTED"
            )
        ),
        "reasons": reasons,
        "rule_version": RULE_VERSION,
        "message": "Operational screening only. No safety certification.",
    }


def screen(db, asset, user):
    from .registration import routing_reasons

    registration = asset.data.get("registration")
    if registration:
        reasons = routing_reasons(asset)
        result = {
            "state": (
                "READY_FOR_LISTING"
                if not reasons
                else (
                    "HOLD"
                    if asset.data.get("pbs") in ["L4", "L5"]
                    else "REVIEW_REQUIRED"
                )
            ),
            "screen": "OWNER_REPORTED",
            "reasons": reasons,
            "message": "Registration approval and PBS handling gates only; transfer authority remains separately required.",
            "rule_version": RULE_VERSION,
        }
        asset.state = result["state"]
        asset.data = {**asset.data, "screening": result}
        audit(db, user, "battery", asset, "SCREEN", result=result)
        return result

    evidence = db.scalars(
        select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == asset.id)
    ).all()
    result = screen_result(
        asset,
        {
            x.kind
            for x in evidence
            if x.review_status == "VERIFIED" or x.kind != "TRANSFER_AUTHORITY"
        },
    )
    from .matching import handling_scope

    if (
        handling_scope(asset) == "CONTROLLED_HANDLING"
        and asset.authority_confirmed
        and any(
            x.kind == "TRANSFER_AUTHORITY" and x.review_status == "VERIFIED"
            for x in evidence
        )
    ):
        result = {
            "state": BatteryState.READY_FOR_LISTING,
            "screen": "CLEARED_FOR_SPECIFIC_HANDLING",
            "reasons": [],
            "rule_version": RULE_VERSION,
            "message": "Scoped controlled handling only; report conditions and expiry apply.",
        }
    # An unresolved hold cannot be self-cleared by changing declarations or rerunning a screen.
    active = db.scalars(
        select(m.ExceptionCase).where(
            m.ExceptionCase.object_type == "battery",
            m.ExceptionCase.object_id == asset.id,
            m.ExceptionCase.status != "CLOSED",
            m.ExceptionCase.category.in_(["SAFETY_FLAG", "SAFETY_REVIEW_REQUIRED"]),
        )
    ).all()
    if active and result["state"] == BatteryState.READY_FOR_LISTING:
        result["state"] = (
            asset.state
            if asset.state in [BatteryState.HOLD, BatteryState.REVIEW_REQUIRED]
            else BatteryState.REVIEW_REQUIRED
        )
        result["reasons"].append(
            {
                "code": "SAFETY_REVIEW_REQUIRED",
                "message": "An unresolved safety review blocks progression.",
                "blocking": True,
                "next_action": "Reviewer must resolve the original evidence.",
            }
        )
    if result["state"] == BatteryState.READY_FOR_LISTING:
        # Only mechanically fulfilled intake tasks close here. Safety/identity disputes need reviewers.
        for case in db.scalars(
            select(m.ExceptionCase).where(
                m.ExceptionCase.object_type == "battery",
                m.ExceptionCase.object_id == asset.id,
                m.ExceptionCase.status != "CLOSED",
                m.ExceptionCase.category.in_(
                    ["TRANSFER_AUTHORITY_UNCONFIRMED", "FIELD_REQUIRED", "MISSING_DATA"]
                ),
            )
        ).all():
            case.status = "CLOSED"
            case.resolution = "Required intake data supplied and transfer evidence reviewed; deterministic gates passed."
            case.data = {
                **case.data,
                "resolution_evidence_ids": [
                    e.id for e in evidence if e.review_status == "VERIFIED"
                ],
                "closed_by": user.id,
                "closed_at": m.now(),
            }
            audit(
                db,
                user,
                "exception",
                case,
                "INTAKE_REQUIREMENT_FULFILLED",
                rule_result=result,
            )
    before = asset.state
    asset.state = result["state"]
    asset.data = {**asset.data, "screening": result}
    for r in result["reasons"]:
        if r["blocking"]:
            cat = "SAFETY_FLAG" if r["code"] == "SAFETY_FLAG_PRESENT" else r["code"]
            owner = (
                "org-review" if cat.startswith("SAFETY") else asset.originator_org_id
            )
            exception(
                db,
                "battery",
                asset.id,
                cat,
                owner,
                r["next_action"],
                "HIGH" if cat == "SAFETY_FLAG" else "MEDIUM",
                evidence=asset.data,
                reason=r,
            )
    audit(
        db,
        user,
        "battery",
        asset,
        "SCREEN",
        before=before,
        after=asset.state,
        result=result,
        input_snapshot={
            **asset.data,
            "chemistry": asset.chemistry,
            "form": asset.form,
            "mass_kg": asset.mass_kg,
        },
    )
    return result
