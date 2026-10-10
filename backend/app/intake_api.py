import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from . import models as m
from .auth import current_user, seller, can_view_asset
from .common import fail, get, dump, audit
from .db import get_db
from .schemas import BatteryIn
from .services.intake import screen
from .config import UPLOAD_DIR
from .schemas import EntityResponse

router = APIRouter()


@router.get("/batteries")
def batteries(db=Depends(get_db), user=Depends(current_user)):
    return [
        dump(a)
        for a in db.scalars(
            select(m.BatteryAsset).order_by(m.BatteryAsset.created_at.desc())
        ).all()
        if can_view_asset(db, user, a)
    ]


@router.post("/batteries", response_model=EntityResponse)
def create(body: BatteryIn, db=Depends(get_db), user=Depends(current_user)):
    from .auth import role

    role(user, "ORIGINATOR")
    if db.scalar(
        select(m.BatteryAsset).where(m.BatteryAsset.internal_id == body.internal_id)
    ):
        fail("IDENTITY_CONFLICT", "Internal asset ID already exists.", "internal_id")
    for id in [body.owner_org_id, body.custodian_org_id]:
        get(db, m.Organisation, id)
    data = body.model_dump(mode="json")
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
            "recorded_by": user.id,
            "recorded_at": m.now(),
            "synthetic": True,
        },
    )
    db.add(asset)
    db.flush()
    audit(db, user, "battery", asset, "CREATE", snapshot=dump(asset))
    return dump(asset)


@router.patch("/batteries/{id}")
def update(id: str, body: BatteryIn, db=Depends(get_db), user=Depends(current_user)):
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
            "Intake is locked after listing; preserve the transaction snapshot.",
        )
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
    before = dump(asset)
    data = body.model_dump(mode="json")
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
    asset.data = {**asset.data, **data, "recorded_by": user.id, "recorded_at": m.now()}
    audit(db, user, "battery", asset, "UPDATE", before=before, after=dump(asset))
    return dump(asset)


@router.get("/batteries/{id}")
def detail(id: str, db=Depends(get_db), user=Depends(current_user)):
    asset = get(db, m.BatteryAsset, id)
    if not can_view_asset(db, user, asset):
        fail("FORBIDDEN", "Asset details are restricted.", status=403)
    evidence = db.scalars(
        select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == id)
    ).all()
    if user.role == "TRANSPORTER":
        evidence = [
            x for x in evidence if x.kind in ["PHOTO", "SERVICE_REPORT", "TEST_REPORT"]
        ]
    return {
        **dump(asset),
        "evidence": [dump(x) for x in evidence],
        "dispositions": [
            dump(x)
            for x in db.scalars(
                select(m.DispositionRecord).where(m.DispositionRecord.asset_id == id)
            ).all()
        ],
    }


@router.post("/batteries/{id}/screen")
def screening(id: str, db=Depends(get_db), user=Depends(current_user)):
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
async def evidence(
    id: str,
    kind: str = Form(...),
    reference: str = Form(""),
    file: UploadFile | None = File(None),
    db=Depends(get_db),
    user=Depends(current_user),
):
    asset = get(db, m.BatteryAsset, id)
    seller(user, asset)
    if kind not in [
        "TRANSFER_AUTHORITY",
        "PHOTO",
        "SERVICE_REPORT",
        "TEST_REPORT",
        "INVOICE",
        "OTHER",
    ]:
        fail("VALIDATION_ERROR", "Unsupported evidence type.", status=422)
    raw = await file.read(5 * 1024 * 1024 + 1) if file else reference.encode()
    if not raw or len(raw) > 5 * 1024 * 1024:
        fail(
            "UPLOAD_INVALID", "Evidence must be nonempty and at most 5 MiB.", status=422
        )
    name = Path(file.filename or "evidence").name if file else "reference.txt"
    suffix = Path(name).suffix.lower()
    if suffix not in [".pdf", ".png", ".jpg", ".jpeg", ".txt"]:
        fail("UPLOAD_INVALID", "Use PDF, PNG, JPEG or text.", status=422)
    if file:
        valid = (
            (suffix == ".pdf" and raw.startswith(b"%PDF-"))
            or (suffix == ".png" and raw.startswith(b"\x89PNG\r\n\x1a\n"))
            or (suffix in [".jpg", ".jpeg"] and raw.startswith(b"\xff\xd8\xff"))
        )
        if suffix == ".txt":
            try:
                raw.decode("utf-8")
                valid = b"\x00" not in raw
            except UnicodeDecodeError:
                valid = False
        if not valid:
            fail(
                "UPLOAD_INVALID",
                "File content does not match the allowed format.",
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
        data={"reference": reference, "visibility": "PARTIES", "synthetic": True},
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
    return dump(obj)


@router.get("/evidence/{id}/download")
def download(id: str, db=Depends(get_db), user=Depends(current_user)):
    obj = get(db, m.EvidenceDocument, id)
    asset = get(db, m.BatteryAsset, obj.asset_id)
    if not can_view_asset(db, user, asset) or (
        user.role == "TRANSPORTER"
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


@router.post("/evidence/{id}/review")
def review_evidence(
    id: str, body: EvidenceReviewIn, db=Depends(get_db), user=Depends(current_user)
):
    from .auth import role

    role(user, "REVIEWER")
    e = get(db, m.EvidenceDocument, id)
    if not body.evidence or not body.reason:
        fail("FIELD_REQUIRED", "Review needs supporting evidence and rationale.")
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
