from .auth import has_role
import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, Header
from fastapi.responses import FileResponse
from sqlalchemy import select, text
from . import models as m
from .auth import current_user, seller, can_view_asset
from .common import fail, get, dump, audit, idem
from .db import get_db
from .schemas import BatteryIn
from .services.intake import screen
from .config import UPLOAD_DIR
from .schemas import EntityResponse

from .registration_schemas import RegistrationReview

router = APIRouter()


@router.get("/batteries")
def batteries(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        dump(a)
        for a in db.scalars(
            select(m.BatteryAsset).order_by(m.BatteryAsset.created_at.desc())
        ).all()
        if can_view_asset(db, user, a)
    ]


@router.post("/batteries", response_model=EntityResponse)
def create(
    body: BatteryIn,
    draft: bool = False,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    from .auth import role

    role(user, "ORIGINATOR")
    from .services.registration import validate_submission

    validate_submission(body, draft)
    body.owner_org_id = body.owner_org_id or user.organisation_id
    body.custodian_org_id = body.custodian_org_id or user.organisation_id
    if (
        body.owner_org_id != user.organisation_id
        or body.custodian_org_id != user.organisation_id
    ):
        fail(
            "FORBIDDEN",
            "Use your organisation as the registration account. Declare a different owner/custodian in the optional text fields; registration cannot assign another organisation custody.",
            status=403,
        )
    db.execute(
        text("UPDATE organisations SET id=id WHERE id=:id"),
        {"id": user.organisation_id},
    )
    fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    existing = db.scalar(
        select(m.BatteryAsset).where(m.BatteryAsset.internal_id == body.internal_id)
    )
    if (
        existing
        and existing.originator_org_id == user.organisation_id
        and existing.data.get("submission_fingerprint") == fingerprint
    ):
        return dump(existing)
    if existing:
        fail("IDENTITY_CONFLICT", "Internal asset ID already exists.", "internal_id")
    for id in [body.owner_org_id, body.custodian_org_id]:
        get(db, m.Organisation, id)
    data = body.model_dump(mode="json")
    if body.pbs is not None:
        data["authority_confirmed"] = False
    fields = {
        k: data.pop(k)
        for k in [
            "internal_id",
            "owner_org_id",
            "custodian_org_id",
            "chemistry",
            "form",
            "condition",
            "mass_kg",
            "quantity",
            "lat",
            "lng",
            "authority_confirmed",
        ]
    }
    asset = m.BatteryAsset(
        **fields,
        originator_org_id=user.organisation_id,
        current_holder_org_id=body.custodian_org_id,
        data={
            **data,
            "submission_fingerprint": fingerprint,
            "provenance": "SELF_DECLARED",
            "recorded_by": user.id,
            "recorded_at": m.now(),
            "synthetic": get(db, m.Organisation, user.organisation_id).synthetic,
        },
    )
    db.add(asset)
    db.flush()
    from .services.registration import submitted

    submitted(db, asset, user, draft=draft)
    audit(db, user, "battery", asset, "CREATE", snapshot=dump(asset))
    return dump(asset)


@router.patch("/batteries/{id}")
def update(
    id: str,
    body: BatteryIn,
    draft: bool = False,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    asset = get(db, m.BatteryAsset, id)
    seller(user, asset)
    db.execute(text("UPDATE batteries SET id=id WHERE id=:id"), {"id": id})
    db.refresh(asset)
    if body.pbs is not None or asset.data.get("pbs") is not None:
        from .services.registration import validate_submission

        validate_submission(body, draft)
    if asset.state not in [
        "DRAFT",
        "NEEDS_INFORMATION",
        "REVIEW_REQUIRED",
        "READY_FOR_LISTING",
        "HOLD",
    ]:
        fail(
            "STATE_TRANSITION_INVALID",
            "Intake is locked after listing; preserve the transaction snapshot.",
        )
    body.owner_org_id = body.owner_org_id or asset.owner_org_id
    body.custodian_org_id = body.custodian_org_id or asset.custodian_org_id
    if (
        body.owner_org_id != asset.owner_org_id
        or body.custodian_org_id != asset.custodian_org_id
    ):
        fail(
            "CUSTODY_EVIDENCE_MISSING",
            "Draft edits cannot transfer ownership or custody.",
        )
    if any(
        asset.data.get("flags", {}).get(f) == "YES" and body.flags.get(f) != "YES"
        for f in asset.data.get("flags", {})
    ):
        fail(
            "SAFETY_REVIEW_REQUIRED",
            "Originator edits cannot erase a critical incident flag; record a qualified correction instead.",
        )
    conflict = db.scalar(
        select(m.BatteryAsset).where(
            m.BatteryAsset.internal_id == body.internal_id, m.BatteryAsset.id != id
        )
    )
    if conflict:
        fail("IDENTITY_CONFLICT", "Internal asset ID already exists.", "internal_id")
    if body.authority_confirmed and not asset.authority_confirmed:
        from .services.matching import require_transfer

        require_transfer(db, asset)
    before = dump(asset)
    data = body.model_dump(mode="json")
    for key in [
        "original_vehicle_class",
        "pack_configuration",
        "dimensions_mm",
        "service_history",
        "bms_reference",
        "declaration",
        "notes",
        "access_notes",
    ]:
        if key not in body.model_fields_set:
            data[key] = asset.data.get(key, data[key])
    for k in [
        "internal_id",
        "chemistry",
        "form",
        "condition",
        "mass_kg",
        "quantity",
        "lat",
        "lng",
        "authority_confirmed",
    ]:
        setattr(asset, k, data.pop(k))
    asset.data = {
        **asset.data,
        **data,
        "provenance": "SELF_DECLARED",
        "recorded_by": user.id,
        "recorded_at": m.now(),
    }
    from .services.registration import submitted

    # Every intake edit is material: invalidate approval and any old handling clearance.
    asset.data = {k: v for k, v in asset.data.items() if k != "handling_clearance"}
    submitted(db, asset, user, changed=True, draft=draft)
    audit(db, user, "battery", asset, "UPDATE", before=before, after=dump(asset))
    return dump(asset)


@router.get("/batteries/{id}")
def detail(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    asset = get(db, m.BatteryAsset, id)
    if not can_view_asset(db, user, asset):
        fail("FORBIDDEN", "Asset details are restricted.", status=403)
    evidence = db.scalars(
        select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == id)
    ).all()
    evidence = [e for e in evidence if not e.data.get("removed")]
    if has_role(user, "TRANSPORTER"):
        evidence = [
            x for x in evidence if x.kind in ["PHOTO", "SERVICE_REPORT", "TEST_REPORT"]
        ]
    from .services.registration import level

    return {
        **dump(asset),
        "handling_concern": {
            "required_pbs_capability": level(asset),
            "source": "SYSTEM_DERIVED_CONSERVATIVE_RULE",
            "notice": "A handling requirement only; not a safety assessment or certification.",
        },
        "evidence": [dump(x) for x in evidence],
        "dispositions": [
            dump(x)
            for x in db.scalars(
                select(m.DispositionRecord).where(m.DispositionRecord.asset_id == id)
            ).all()
        ],
    }


@router.post("/batteries/{id}/screen")
def screening(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    asset = get(db, m.BatteryAsset, id)
    seller(user, asset)
    if asset.state not in [
        "DRAFT",
        "NEEDS_INFORMATION",
        "REVIEW_REQUIRED",
        "READY_FOR_LISTING",
        "HOLD",
    ]:
        fail(
            "STATE_TRANSITION_INVALID",
            "Cannot rerun intake screening after commercial allocation.",
        )
    return screen(db, asset, user)


@router.post("/batteries/{id}/evidence")
def evidence(
    id: str,
    kind: str = Form("OTHER"),
    reference: str = Form(""),
    file: UploadFile | None = File(None),
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    asset = get(db, m.BatteryAsset, id)
    seller(user, asset)
    db.execute(text("UPDATE batteries SET id=id WHERE id=:id"), {"id": id})
    db.refresh(asset)
    if asset.state not in [
        "DRAFT",
        "NEEDS_INFORMATION",
        "REVIEW_REQUIRED",
        "READY_FOR_LISTING",
        "HOLD",
        "LISTED",
    ]:
        fail(
            "STATE_TRANSITION_INVALID",
            "Registration attachments are locked after commercial allocation. Use the receiving/assessment evidence workflow.",
        )
    if kind not in [
        "TRANSFER_AUTHORITY",
        "PHOTO",
        "SERVICE_REPORT",
        "TEST_REPORT",
        "INVOICE",
        "OTHER",
    ]:
        fail("VALIDATION_ERROR", "Unsupported evidence type.", status=422)
    from .services.documents import MAX_FILE, MAX_TOTAL, MAX_COUNT, validate_document

    # Serialize count/total checks with uploads and removals, including concurrent requests.
    raw = file.file.read(MAX_FILE + 1) if file else reference.encode()
    name = Path(file.filename or "evidence").name if file else "reference.txt"
    validate_document(name, raw)
    checksum = hashlib.sha256(raw).hexdigest()
    active = list(
        db.scalars(select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == id))
    )
    active = [e for e in active if not e.data.get("removed")]
    existing = next(
        (e for e in active if e.checksum == checksum and e.kind == kind), None
    )
    if existing:
        return dump(existing)
    if len(active) >= MAX_COUNT:
        fail(
            "UPLOAD_COUNT_EXCEEDED",
            "A registration can have at most four active files. Remove a file before replacing it.",
            status=422,
        )
    if sum(e.data.get("size_bytes", 0) for e in active) + len(raw) > MAX_TOTAL:
        fail(
            "UPLOAD_TOTAL_EXCEEDED",
            "Total attachments cannot exceed 25 MB.",
            status=422,
        )
    rows = db.scalars(
        select(m.EvidenceDocument).where(
            m.EvidenceDocument.asset_id == id, m.EvidenceDocument.kind == kind
        )
    ).all()
    obj = m.EvidenceDocument(
        asset_id=id,
        uploader_id=user.id,
        kind=kind,
        filename=name,
        checksum=hashlib.sha256(raw).hexdigest(),
        version=len(rows) + 1,
        data={
            "reference": reference,
            "size_bytes": len(raw),
            "visibility": "PARTIES",
            "synthetic": get(db, m.Organisation, user.organisation_id).synthetic,
        },
    )
    db.add(obj)
    db.flush()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / obj.id).write_bytes(raw)
    audit(
        db,
        user,
        "battery",
        asset,
        "ADD_EVIDENCE",
        evidence_id=obj.id,
        checksum=obj.checksum,
        version=obj.version,
    )
    if asset.data.get("registration", {}).get("status") == "APPROVED":
        from .services.registration import submitted

        submitted(db, asset, user, changed=True)
    return dump(obj)


@router.get("/evidence/{id}/download")
def download(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    obj = get(db, m.EvidenceDocument, id)
    asset = get(db, m.BatteryAsset, obj.asset_id)
    if obj.data.get("removed"):
        fail("NOT_FOUND", "Attachment was removed from the registration.", status=404)
    if not can_view_asset(db, user, asset) or (
        has_role(user, "TRANSPORTER")
        and obj.kind not in ["PHOTO", "SERVICE_REPORT", "TEST_REPORT"]
    ):
        fail(
            "FORBIDDEN",
            "Evidence access is restricted to the required operational subset.",
            status=403,
        )
    path = UPLOAD_DIR / id
    if not path.exists():
        fail(
            "NOT_FOUND",
            "Seed evidence is metadata only; see its synthetic reference.",
            status=404,
        )
    return FileResponse(
        path, filename=obj.filename, media_type="application/octet-stream"
    )


from .schemas import Schema
from typing import Literal


class EvidenceReviewIn(Schema):
    status: Literal["VERIFIED", "REJECTED", "UNDER_REVIEW"]
    evidence: str
    reason: str
    kind: str | None = None


@router.post("/evidence/{id}/review")
def review_evidence(
    id: str,
    body: EvidenceReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    from .auth import role

    role(user, "REVIEWER")
    e = get(db, m.EvidenceDocument, id)
    db.execute(text("UPDATE batteries SET id=id WHERE id=:id"), {"id": e.asset_id})
    db.refresh(e)
    if not body.evidence or not body.reason:
        fail("FIELD_REQUIRED", "Review needs supporting evidence and rationale.")
    if e.data.get("removed"):
        fail("STATE_TRANSITION_INVALID", "Removed evidence cannot grant authority.")
    if body.kind is not None:
        if body.kind not in [
            "TRANSFER_AUTHORITY",
            "PHOTO",
            "SERVICE_REPORT",
            "TEST_REPORT",
            "INVOICE",
            "OTHER",
        ]:
            fail(
                "VALIDATION_ERROR",
                "Unsupported evidence review classification.",
                status=422,
            )
        e.kind = body.kind
    e.review_status = body.status
    e.data = {
        **e.data,
        "reviews": [
            *e.data.get("reviews", []),
            {**body.model_dump(), "actor_id": user.id, "timestamp": m.now()},
        ],
    }
    if body.status == "REJECTED":
        from .common import exception

        asset = get(db, m.BatteryAsset, e.asset_id)
        if e.kind == "TRANSFER_AUTHORITY":
            asset.authority_confirmed = False
            asset.state = "REVIEW_REQUIRED"
        exception(
            db,
            "battery",
            asset.id,
            "EVIDENCE_CONFLICT",
            "org-review",
            "Resolve conflicting/rejected evidence; preserve all original versions.",
            evidence_id=e.id,
            reason=body.reason,
        )
    audit(
        db,
        user,
        "battery",
        get(db, m.BatteryAsset, e.asset_id),
        "EVIDENCE_REVIEW",
        evidence_id=e.id,
        review=body.model_dump(),
    )
    return dump(e)


@router.get("/registration-policy")
def registration_policy(user=Depends(current_user)):
    from .services.registration import (
        PBS_POLICY,
        DOCUMENT_DESCRIPTION,
        PBS_CONFIGURATION,
    )

    return {
        "levels": PBS_POLICY,
        "document_description": DOCUMENT_DESCRIPTION,
        "policy_version": PBS_CONFIGURATION["version"],
        "notice": "Preliminary owner observations only; no safety certification.",
    }


@router.post("/batteries/{id}/registration-review")
def registration_review(
    id: str,
    body: RegistrationReview,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    from .services.registration import approve

    db.execute(text("UPDATE batteries SET id=id WHERE id=:id"), {"id": id})
    return dump(approve(db, get(db, m.BatteryAsset, id), user, body))


@router.get("/batteries/{id}/eligible-participants")
def registration_candidates(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    asset = get(db, m.BatteryAsset, id)
    if user.organisation_id != asset.originator_org_id and not has_role(
        user, "REVIEWER"
    ):
        fail(
            "FORBIDDEN",
            "Candidate explanations are private to the originator and operator.",
            status=403,
        )
    from .services.matching import eligible_buyers
    from .services.registration import routing_reasons

    reasons = routing_reasons(asset)
    candidates = eligible_buyers(db, asset, discovery=True)
    return {
        "registration_reasons": reasons,
        "hold": bool(reasons) or not any(c["eligible"] for c in candidates),
        "candidates": candidates,
    }


@router.post("/batteries/{id}/evidence/{evidence_id}/remove")
def remove_evidence(
    id: str,
    evidence_id: str,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    asset = get(db, m.BatteryAsset, id)
    seller(user, asset)
    db.execute(text("UPDATE batteries SET id=id WHERE id=:id"), {"id": id})
    e = get(db, m.EvidenceDocument, evidence_id)
    if e.asset_id != id:
        fail(
            "FORBIDDEN", "This attachment belongs to another registration.", status=403
        )
    if asset.state not in [
        "DRAFT",
        "REVIEW_REQUIRED",
        "NEEDS_INFORMATION",
        "READY_FOR_LISTING",
        "HOLD",
    ]:
        fail(
            "STATE_TRANSITION_INVALID",
            "Attachments are locked after commercial allocation.",
        )
    if not e.data.get("removed"):
        e.data = {
            **e.data,
            "removed": True,
            "removed_at": m.now(),
            "removed_by": user.id,
        }
        from .services.registration import submitted

        submitted(db, asset, user, changed=True)
        if e.kind == "TRANSFER_AUTHORITY":
            asset.authority_confirmed = False
        audit(db, user, "battery", asset, "REMOVE_ATTACHMENT", evidence_id=e.id)
    return dump(e)


@router.post("/batteries/{id}/confirm-transfer-authority")
def confirm_transfer_authority(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    asset = get(db, m.BatteryAsset, id)
    seller(user, asset)
    evidence = db.scalars(
        select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == id)
    ).all()
    if not any(
        e.kind == "TRANSFER_AUTHORITY"
        and e.review_status == "VERIFIED"
        and not e.data.get("removed")
        for e in evidence
    ):
        fail(
            "TRANSFER_AUTHORITY_UNCONFIRMED",
            "Operator-reviewed transfer-authority evidence is required for commercial commitment.",
        )
    asset.authority_confirmed = True
    audit(db, user, "battery", asset, "CONFIRM_TRANSFER_AUTHORITY")
    return dump(asset)
