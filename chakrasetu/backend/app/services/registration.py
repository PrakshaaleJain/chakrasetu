"""Registration approval is separate from transfer authority and qualified safety clearance."""

import re
import json
import os
from pathlib import Path
from enum import StrEnum
from sqlalchemy import select
from .. import models as m
from ..auth import role
from ..common import audit, exception, fail, expired


class RegistrationStatus(StrEnum):
    PENDING = "PENDING_REVIEW"
    INFORMATION = "INFORMATION_REQUESTED"
    SPECIALIST = "SPECIALIST_ASSESSMENT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def load_policy():
    path = Path(
        os.getenv(
            "PBS_POLICY_PATH",
            str(Path(__file__).resolve().parents[1] / "pbs_policy.json"),
        )
    )
    policy = json.loads(path.read_text())
    levels = policy["levels"]
    expected = [f"L{i}" for i in range(1, 6)]
    if [p["level"] for p in levels] != expected or any(
        not p.get("title") or not p.get("description") for p in levels
    ):
        raise RuntimeError("PBS policy requires all five ordered, labelled levels.")
    concern = policy.get("minimum_handling_concern", {})
    if set(concern) != set(expected) or any(
        v not in expected or v < k for k, v in concern.items()
    ):
        raise RuntimeError(
            "PBS policy may tighten, but cannot weaken, the required handling gates."
        )
    return policy


PBS_CONFIGURATION = load_policy()
PBS_POLICY = PBS_CONFIGURATION["levels"]


DOCUMENT_DESCRIPTION = "You may upload any documents that you consider relevant to this battery registration. These could include a battery datasheet, technical booklet, purchase or ownership records, proof of authorization to transfer the battery, inspection reports, test results, warranty records, or photographs. Please upload only documents that are available to you and that you are permitted to share. Supporting documents are helpful for verification, but you can submit the registration without uploading any files."

# Conservative explicit-language guard, never a diagnosis or a general NLP safety classifier.
CRITICAL = re.compile(
    r"\b(active\s+(?:thermal event|fire)|(?:emitting|producing|visible|currently|is)\s+smoke|smoking|on fire|burning|thermal runaway|fire ongoing|smoke\s+(?:coming|seen|observed|from)|(?:observed|reported|visible|there is)\s+(?:fire|smoke))\b",
    re.I,
)


def critical_report(data):
    inspection = data.get("inspection") or {}
    text = (
        " ".join(
            str(data.get(k) or "")
            for k in [
                "pbs_comments",
                "handling_instructions",
                "additional_information",
                "notes",
            ]
        )
        + " "
        + str(inspection.get("findings") or "")
    )
    return (
        bool(data.get("critical_report_unresolved"))
        or bool(CRITICAL.search(text))
        or any(
            data.get("flags", {}).get(f) == "YES"
            for f in ["smoke_fire", "thermal_event"]
        )
    )


def level(asset):
    r = asset.data.get("registration", {})
    reported = asset.data.get("pbs")
    configured = PBS_CONFIGURATION["minimum_handling_concern"].get(reported)
    return max(
        [
            x
            for x in [
                asset.data.get("pbs"),
                configured,
                "L4" if reported and asset.condition == "DAMAGED_REPORTED" else None,
                r.get("reviewer_pbs"),
                r.get("review_unresolved_level"),
                asset.data.get("originator_concern_floor"),
                (
                    "L3"
                    if asset.data.get("pbs") and asset.condition == "UNKNOWN"
                    else None
                ),
            ]
            if x
        ],
        default=None,
    )


def routing_reasons(asset):
    r = asset.data.get("registration")
    reasons = []

    def add(code, message):
        reasons.append({"code": code, "message": message, "blocking": True})

    if asset.data.get("pbs") and asset.data.get("collection_availability") != "YES":
        add(
            "COLLECTION_UNCONFIRMED",
            "Collection availability must be confirmed before ordinary matching or dispatch.",
        )
    if r and r.get("status") != RegistrationStatus.APPROVED:
        add(
            "REGISTRATION_NOT_APPROVED",
            "Network-operator registration approval is required.",
        )
    if asset.data.get("mixed_batch"):
        add(
            "BATCH_REASSESSMENT_REQUIRED",
            "Mixed specifications or safety conditions must be separated into individual or homogeneous registrations before matching.",
        )
    if level(asset) == "L5" or critical_report(asset.data):
        add(
            "CRITICAL_HAZARD_REPORTED",
            "Routine matching and dispatch are disabled. Qualified emergency/dangerous-goods instructions are required; PBS is not a diagnosis.",
        )
    if (
        asset.data.get("pbs")
        and any(v == "YES" for v in asset.data.get("flags", {}).values())
        and not asset.data.get("handling_clearance")
    ):
        add(
            "SPECIALIST_REVIEW_REQUIRED",
            "Previously reported structured incident flags require scoped review and cannot be erased by a PBS selection.",
        )
    if asset.data.get("registration", {}).get("specialist_review_required"):
        c = asset.data.get("handling_clearance", {})
        if not c.get("valid_until") or expired(c["valid_until"]):
            add(
                "SPECIALIST_REVIEW_REQUIRED",
                "An operator-requested specialist assessment is still outstanding.",
            )
    if level(asset) == "L4":
        c = asset.data.get("handling_clearance", {})
        if (
            c.get("handling_scope") != "CONTROLLED_HANDLING"
            or not c.get("valid_until")
            or expired(c["valid_until"])
        ):
            add(
                "SPECIALIST_REVIEW_REQUIRED",
                "High concern requires a current, scoped qualified handling report.",
            )
    return reasons


def submitted(db, asset, user, changed=False, draft=False):
    r = asset.data.get("registration", {})
    concern = level(asset)
    if concern in ["L4", "L5"]:
        asset.data = {
            **asset.data,
            "originator_concern_floor": max(
                asset.data.get("originator_concern_floor") or "L1", concern
            ),
        }
    if critical_report(asset.data):
        asset.data = {**asset.data, "critical_report_unresolved": True}
    event = {
        "action": (
            "DRAFT_SAVED"
            if draft
            else ("REVISED_AND_RESUBMITTED" if changed else "SUBMITTED")
        ),
        "actor_id": user.id,
        "timestamp": m.now(),
        "pbs": asset.data.get("pbs"),
    }
    asset.data = {
        **asset.data,
        "registration": {
            **r,
            "status": "DRAFT" if draft else RegistrationStatus.PENDING,
            "submitted_by": user.id,
            "submitted_at": m.now(),
            "revision": r.get("revision", 0) + 1,
            "reviewer_pbs": None,
            "history": [*r.get("history", []), event],
        },
    }
    asset.state = "DRAFT" if draft else "REVIEW_REQUIRED"
    pbs = asset.data.get("pbs")
    if (
        level(asset) in ["L4", "L5"]
        or critical_report(asset.data)
        or any(v == "YES" for v in asset.data.get("flags", {}).values())
    ):
        asset.state = "HOLD"
        exception(
            db,
            "battery",
            asset.id,
            "SAFETY_FLAG",
            "org-review",
            "Controlled escalation: obtain qualified instructions. No routine dispatch or automatic recycling.",
            "HIGH",
            reported_pbs=pbs,
            contradiction=critical_report(asset.data) and pbs != "L5",
        )
    audit(
        db,
        user,
        "battery",
        asset,
        event["action"],
        registration=asset.data["registration"],
    )


def approve(db, asset, user, body):
    role(user, "REVIEWER")
    if user.organisation_id == asset.originator_org_id:
        fail(
            "SELF_APPROVAL_FORBIDDEN",
            "Originators cannot review their own registrations.",
            status=403,
        )
    r = asset.data.get("registration", {})
    if r.get("status") not in [
        RegistrationStatus.PENDING,
        RegistrationStatus.INFORMATION,
        RegistrationStatus.SPECIALIST,
    ]:
        fail(
            "STATE_TRANSITION_INVALID",
            "Only a submitted registration awaiting review can be reviewed.",
        )
    decision = body.decision
    review = {**body.model_dump(), "actor_id": user.id, "timestamp": m.now()}
    asset.data = {
        **asset.data,
        "registration": {
            **r,
            "reviewer_pbs": body.reviewer_pbs,
            "specialist_review_required": bool(
                r.get("specialist_review_required")
                or decision == "SPECIALIST_ASSESSMENT"
            ),
            "review_unresolved_level": max(
                [x for x in [r.get("review_unresolved_level"), body.reviewer_pbs] if x],
                default=None,
            ),
            "last_reason": body.reason,
            "history": [*r.get("history", []), review],
        },
    }
    # Approval is an entry permission. It cannot override observed critical hazards or a specialist gate.
    if decision == "APPROVED" and (level(asset) == "L5" or critical_report(asset.data)):
        fail(
            "CRITICAL_HAZARD_REPORTED",
            "Escalate this registration; ordinary approval cannot clear a critical report.",
        )
    asset.data = {
        **asset.data,
        "registration": {**asset.data["registration"], "status": decision},
    }
    active_listing = db.scalar(
        select(m.Listing).where(
            m.Listing.asset_id == asset.id, m.Listing.status == "OPEN"
        )
    )
    asset.state = (
        ("LISTED" if active_listing else "READY_FOR_LISTING")
        if decision == "APPROVED"
        else (
            "HOLD"
            if decision == "SPECIALIST_ASSESSMENT"
            or level(asset) in ["L4", "L5"]
            or critical_report(asset.data)
            else "REVIEW_REQUIRED"
        )
    )
    if decision == "APPROVED" and any(
        x["code"] != "COLLECTION_UNCONFIRMED" for x in routing_reasons(asset)
    ):
        asset.state = "HOLD"
    if decision == "SPECIALIST_ASSESSMENT" or asset.state == "HOLD":
        exception(
            db,
            "battery",
            asset.id,
            (
                "SAFETY_FLAG"
                if level(asset) in ["L4", "L5"] or critical_report(asset.data)
                else "SAFETY_REVIEW_REQUIRED"
            ),
            "org-review",
            "Obtain a qualified scope-specific assessment; preserve originator PBS.",
            "HIGH",
            review=review,
        )
    audit(
        db,
        user,
        "battery",
        asset,
        "REGISTRATION_REVIEW",
        review=review,
        registration_status=decision,
    )
    return asset


def acceptance_reasons(asset, obj, activity):
    """Use only the reviewed safety scope for the exact activity, never self declaration."""
    if not asset.data.get("pbs"):
        return []  # Legacy registrations retain their previously scoped handling rules.
    reasons = routing_reasons(asset)
    scope = dict(obj.data.get("verified_safety_scope") or {})
    declared = obj.data.get("declared_safety_scope")
    if declared is not None:
        # Availability may narrow immediately; declarations cannot expand reviewed permissions.
        if not declared.get("max_pbs"):
            scope["max_pbs"] = None
        elif scope.get("max_pbs"):
            scope["max_pbs"] = min(scope["max_pbs"], declared["max_pbs"])
        scope["application_types"] = sorted(
            set(scope.get("application_types", []))
            & set(declared.get("application_types", []))
        )
        for flag in [
            "specialist_assessment",
            "damaged_handling",
            "critical_hazard_handling",
            "dangerous_goods",
        ]:
            scope[flag] = bool(scope.get(flag) and declared.get(flag))
        if declared.get("service_areas") and not any(
            a.casefold() in asset.data.get("address", "").casefold()
            for a in declared["service_areas"]
        ):
            reasons.append(
                {
                    "code": "SERVICE_AREA_UNAVAILABLE",
                    "message": "Pickup is outside the currently declared service areas.",
                    "blocking": True,
                }
            )

    def add(code, message):
        reasons.append({"code": code, "message": message, "blocking": True})

    pbs = level(asset)
    for k, value, code in [
        ("chemistries", asset.chemistry, "CHEMISTRY_NOT_ACCEPTED"),
        ("formats", asset.form, "FORM_FACTOR_NOT_ACCEPTED"),
        ("conditions", asset.condition, "CONDITION_MISMATCH"),
    ]:
        for description, current in [
            ("reviewed", scope),
            ("currently declared", declared or {}),
        ]:
            if current.get(k) is not None and value not in current[k]:
                add(
                    code, f"{activity} {description} acceptance does not cover {value}."
                )
    if not scope.get("max_pbs"):
        add(
            "HANDLING_CAPABILITY_UNVERIFIED",
            f"{activity} PBS acceptance scope has not been verified.",
        )
    elif pbs > scope["max_pbs"]:
        add(
            "PBS_SCOPE_EXCEEDED",
            f'{activity} accepts up to {scope["max_pbs"]}; required handling concern is {pbs}.',
        )
    apps = scope.get("application_types", [])
    if asset.data.get("application_type", "UNKNOWN") not in apps:
        add(
            "APPLICATION_NOT_ACCEPTED",
            f"{activity} does not explicitly accept this application type.",
        )
    if pbs == "L3" and not scope.get("specialist_assessment"):
        add(
            "ASSESSMENT_CAPABILITY_REQUIRED",
            f"{activity} lacks verified uncertainty/assessment handling scope.",
        )
    if (pbs == "L4" or asset.condition == "DAMAGED_REPORTED") and not scope.get(
        "damaged_handling"
    ):
        add(
            "DAMAGED_HANDLING_REQUIRED",
            f"{activity} lacks reviewed damaged-battery handling scope.",
        )
    if (
        activity == "TRANSPORT"
        and pbs in ["L3", "L4"]
        and not scope.get("dangerous_goods")
    ):
        add(
            "DANGEROUS_GOODS_SCOPE_REQUIRED",
            "Reviewed transport handling qualifications are required for this concern level.",
        )
    areas = scope.get("service_areas", [])
    if areas and not any(
        a.casefold() in asset.data.get("address", "").casefold() for a in areas
    ):
        add(
            "SERVICE_AREA_UNAVAILABLE",
            "Pickup location is outside the reviewed service areas.",
        )
    return reasons


def invalidate_pending(db, org_id, user):
    """Preserve contracts; invalidate recommendations and prevent stale bookings."""
    facilities = list(
        db.scalars(select(m.Facility).where(m.Facility.organisation_id == org_id))
    )
    txs = list(
        db.scalars(
            select(m.SaleTransaction).where(
                m.SaleTransaction.facility_id.in_([f.id for f in facilities])
            )
        )
    )
    carrier_ids = list(
        db.scalars(
            select(m.TransporterProfile.id).where(
                m.TransporterProfile.organisation_id == org_id
            )
        )
    )
    if carrier_ids:
        carrier_tx_ids = list(
            db.scalars(
                select(m.TransportQuote.transaction_id).where(
                    m.TransportQuote.transporter_id.in_(carrier_ids)
                )
            )
        )
        txs.extend(
            db.scalars(
                select(m.SaleTransaction).where(
                    m.SaleTransaction.id.in_(carrier_tx_ids)
                )
            )
        )
    for tx in {t.id: t for t in txs}.values():
        if tx.status in ["CLOSED", "CANCELLED"]:
            continue
        for plan in db.scalars(
            select(m.RoutePlan).where(m.RoutePlan.transaction_id == tx.id)
        ):
            plan.expires_at = m.now()
        exception(
            db,
            "transaction",
            tx.id,
            "CAPABILITY_REASSESSMENT",
            tx.seller_org_id,
            "Participant scope changed; recheck all participants and obtain a fresh feasible route.",
            scope_org_id=org_id,
        )
        audit(
            db,
            user,
            "transaction",
            tx,
            "CAPABILITY_REASSESSMENT_REQUIRED",
            scope_org_id=org_id,
        )


def validate_submission(body, draft=False):
    if draft:
        return
    for key in ["pbs", "registration_title", "address", "lat", "lng"]:
        v = getattr(body, key)
        if v is None or isinstance(v, str) and not v.strip():
            fail(
                "FIELD_REQUIRED",
                f'{key.replace("_", " ").capitalize()} is required for submission. Save a draft if this information is unavailable.',
                key,
                status=422,
            )
