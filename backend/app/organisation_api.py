from io import BytesIO
from pathlib import Path
import secrets
import warnings
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select, text
from PIL import Image, UnidentifiedImageError
from . import models as m
from .auth import current_user, role, has_role
from .db import get_db
from .common import get, fail, dump, audit
from .config import UPLOAD_DIR
from .organisation_schemas import (
    ProfileIn,
    RequestIn,
    ReviewIn,
    ResponseIn,
    FacilityEdit,
)
from .organisation_service import (
    public_profile,
    manage,
    validate_request,
    apply_decision,
    CONFIRMATION,
)

router = APIRouter(tags=["organisation profiles"])


@router.get("/organisation-profiles")
def directory(
    q: str = "",
    capability: str = "",
    location: str = "",
    organisation_type: str = "",
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    results = [
        public_profile(db, o)
        for o in db.scalars(select(m.Organisation).where(m.Organisation.active == True))
        if not o.data.get("internal")
    ]
    return [
        p
        for p in results
        if q.lower() in (p["name"] + " " + p["display_name"]).lower()
        and (
            not organisation_type
            or organisation_type.lower() in p["organisation_type"].lower()
        )
        and (
            not location
            or location.lower()
            in " ".join(p["regions"] + [f["name"] for f in p["facilities"]]).lower()
        )
        and (
            not capability
            or any(
                capability.lower() in str(c["name"]).lower()
                and c["status"] == "APPROVED"
                for c in p["capabilities"]
            )
        )
    ]


@router.get("/organisation-profiles/{id}")
def detail(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    org = get(db, m.Organisation, id)
    result = public_profile(db, org)
    if user.organisation_id == id:
        result["editable_profile"] = org.data.get("profile", {})
        for facility in result["facilities"]:
            facility["address"] = get(db, m.Facility, facility["id"]).data.get(
                "address", ""
            )
        binding = db.scalar(
            select(m.OrganisationAccount).where(
                m.OrganisationAccount.organisation_id == id
            )
        )
        result["account_binding"] = bool(binding)
    return result


@router.patch("/organisation-profiles/{id}")
def edit(
    id: str,
    body: ProfileIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    manage(user, id)
    org = get(db, m.Organisation, id)
    before = org.data.get("profile", {})
    org.data = {**org.data, "profile": body.model_dump(), "profile_updated_at": m.now()}
    audit(
        db,
        user,
        "organisation",
        org,
        "PROFILE_UPDATED",
        changed_fields=[k for k, v in body.model_dump().items() if before.get(k) != v],
    )
    return public_profile(db, org)


@router.get("/organisation-profiles/{id}/contacts")
def contacts(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    org = get(db, m.Organisation, id)
    p = org.data.get("profile", {})
    if (
        p.get("contact_visibility", "PRIVATE") == "PRIVATE"
        and user.organisation_id != id
        and not has_role(user, "REVIEWER")
    ):
        fail(
            "CONTACT_RESTRICTED",
            "This organisation has chosen to keep its contact details private.",
            status=403,
        )
    audit(
        db,
        user,
        "organisation",
        org,
        "BUSINESS_CONTACT_ACCESSED",
        visibility=p.get("contact_visibility", "PRIVATE"),
    )
    return {
        k: p.get(k, "") for k in ["business_email", "business_phone", "primary_address"]
    }


@router.post("/organisation-profiles/{id}/logo")
async def upload_logo(
    id: str,
    file: UploadFile = File(...),
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    manage(user, id)
    org = get(db, m.Organisation, id)
    content = await file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        fail("LOGO_TOO_LARGE", "Choose an image smaller than 2 MB.", status=413)
    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        fail("LOGO_FORMAT_INVALID", "Choose a PNG, JPEG or WebP image.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(content))
            if (
                image.format not in {"PNG", "JPEG", "WEBP"}
                or image.width * image.height > 16000000
            ):
                raise ValueError("Unsupported image")
            image.verify()
            image = Image.open(BytesIO(content))
            image.load()
            image = image.convert("RGBA")
            image.thumbnail((512, 512))
    except (
        UnidentifiedImageError,
        ValueError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        fail("LOGO_FORMAT_INVALID", "The file is not a supported, valid image.")
    folder = UPLOAD_DIR / "logos"
    folder.mkdir(parents=True, exist_ok=True)
    name = secrets.token_hex(24) + ".png"
    path = folder / name
    image.save(
        path, format="PNG"
    )  # Strip metadata, executable payloads and original names.
    org.data = {**org.data, "logo_file": name, "logo_updated_at": m.now()}
    audit(db, user, "organisation", org, "LOGO_UPDATED")
    try:
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"logo_url": f"/api/organisation-profiles/{id}/logo"}


@router.get("/organisation-profiles/{id}/logo")
def logo(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    org = get(db, m.Organisation, id)
    name = org.data.get("logo_file", "")
    if not name or Path(name).name != name:
        fail("NOT_FOUND", "No logo is available.", status=404)
    path = UPLOAD_DIR / "logos" / name
    if not path.is_file():
        fail("NOT_FOUND", "No logo is available.", status=404)
    return FileResponse(path, media_type="image/png")


@router.post("/organisation-profiles/{id}/logo/remove")
def remove_logo(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    manage(user, id)
    org = get(db, m.Organisation, id)
    org.data = {k: v for k, v in org.data.items() if k != "logo_file"}
    audit(db, user, "organisation", org, "LOGO_REMOVED")
    return {"removed": True}


@router.patch("/organisation-facilities/{id}")
def edit_facility(
    id: str,
    body: FacilityEdit,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    f = get(db, m.Facility, id)
    manage(user, f.organisation_id)
    f.name = body.name
    f.data = {
        **f.data,
        "description": body.description,
        "address": body.address,
        "updated_at": m.now(),
    }
    audit(db, user, "facility", f, "FACILITY_PROFILE_UPDATED")
    return {
        "id": f.id,
        "name": f.name,
        "description": body.description,
        "address": body.address,
    }


@router.get("/capability-requests")
def requests(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    query = select(m.CapabilityRequest).order_by(m.CapabilityRequest.updated_at.desc())
    if not has_role(user, "REVIEWER"):
        query = query.where(m.CapabilityRequest.organisation_id == user.organisation_id)
    return [dump(r) for r in db.scalars(query)]


@router.post("/capability-requests")
def submit(
    body: RequestIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    manage(user, user.organisation_id)
    db.execute(text("BEGIN IMMEDIATE"))
    validate_request(db, user, body)
    scope = body.requested_scope.model_dump(mode="json")
    for r in db.scalars(
        select(m.CapabilityRequest).where(
            m.CapabilityRequest.organisation_id == user.organisation_id,
            m.CapabilityRequest.status.in_(["PENDING", "INFORMATION_REQUESTED"]),
        )
    ):
        if (
            r.kind == body.kind
            and r.target_id == body.target_id
            and r.facility_id == body.facility_id
            and r.requested_scope == scope
        ):
            return {"request": dump(r), "message": CONFIRMATION}
    r = m.CapabilityRequest(
        organisation_id=user.organisation_id,
        submitted_by=user.id,
        kind=body.kind,
        action=body.action,
        target_id=body.target_id,
        facility_id=body.facility_id,
        requested_scope=scope,
        status="PENDING",
        updated_at=m.now(),
        data={
            "history": [
                {
                    "action": "SUBMITTED",
                    "actor_id": user.id,
                    "timestamp": m.now(),
                    "scope": scope,
                }
            ]
        },
    )
    db.add(r)
    db.flush()
    audit(db, user, "capability_request", r, "SUBMITTED")
    return {"request": dump(r), "message": CONFIRMATION}


@router.post("/capability-requests/{id}/respond")
def respond(
    id: str,
    body: ResponseIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    db.execute(text("BEGIN IMMEDIATE"))
    r = get(db, m.CapabilityRequest, id)
    manage(user, r.organisation_id)
    if r.status != "INFORMATION_REQUESTED":
        fail(
            "STATE_TRANSITION_INVALID",
            "Respond after the reviewer requests more information.",
        )
    r.status = "PENDING"
    r.updated_at = m.now()
    r.data = {
        **r.data,
        "history": [
            *r.data.get("history", []),
            {
                "action": "RESPONDED",
                "actor_id": user.id,
                "timestamp": m.now(),
                "message": body.message,
            },
        ],
    }
    audit(db, user, "capability_request", r, "RESPONDED")
    return dump(r)


@router.post("/capability-requests/{id}/withdraw")
def withdraw(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    db.execute(text("BEGIN IMMEDIATE"))
    r = get(db, m.CapabilityRequest, id)
    manage(user, r.organisation_id)
    if r.status not in {"PENDING", "INFORMATION_REQUESTED"}:
        fail(
            "STATE_TRANSITION_INVALID",
            "Only an open request can be withdrawn. Request removal separately for approved scope.",
        )
    r.status = "WITHDRAWN"
    r.updated_at = m.now()
    r.data = {
        **r.data,
        "history": [
            *r.data.get("history", []),
            {"action": "WITHDRAWN", "actor_id": user.id, "timestamp": m.now()},
        ],
    }
    audit(db, user, "capability_request", r, "WITHDRAWN")
    return dump(r)


@router.post("/capability-requests/{id}/review")
def review(
    id: str,
    body: ReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    db.execute(text("BEGIN IMMEDIATE"))
    r = get(db, m.CapabilityRequest, id)
    if r.organisation_id == user.organisation_id:
        fail(
            "INDEPENDENT_REVIEW_REQUIRED",
            "Another authorised reviewer must assess your organisation request.",
            status=403,
        )
    if r.status not in {"PENDING", "INFORMATION_REQUESTED"} and not (
        r.status == "APPROVED" and body.decision == "SUSPENDED"
    ):
        fail("STATE_TRANSITION_INVALID", "The review has already been completed.")
    apply_decision(db, user, r, body)
    r.status = body.decision
    r.updated_at = m.now()
    r.data = {
        **r.data,
        "history": [
            *r.data.get("history", []),
            {
                "action": body.decision,
                "actor_id": user.id,
                "timestamp": m.now(),
                "reason": body.reason,
                "evidence": body.evidence,
                "valid_until": body.valid_until,
            },
        ],
    }
    audit(
        db,
        user,
        "capability_request",
        r,
        "REVIEWED",
        decision=body.decision,
        reason=body.reason,
    )
    return dump(r)


from .registration_schemas import AcceptanceDeclaration


@router.patch("/organisation-profiles/{org_id}/capabilities/{id}/declaration")
def acceptance_declaration(
    org_id: str,
    id: str,
    body: AcceptanceDeclaration,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    manage(user, org_id)
    obj = get(
        db,
        {
            "PATHWAY": m.FacilityCapability,
            "OPERATION": m.OperationCapability,
            "TRANSPORT": m.TransporterProfile,
        }[body.kind],
        id,
    )
    owner = (
        obj.organisation_id
        if body.kind == "TRANSPORT"
        else get(db, m.Facility, obj.facility_id).organisation_id
    )
    if owner != org_id:
        fail(
            "FORBIDDEN", "This capability belongs to another organisation.", status=403
        )
    before = obj.data.get("declared_safety_scope")
    obj.data = {
        **obj.data,
        "declared_safety_scope": body.scope.model_dump(),
        "updated_at": m.now(),
    }
    from .services.registration import invalidate_pending

    invalidate_pending(db, org_id, user)
    audit(
        db,
        user,
        "organisation",
        get(db, m.Organisation, org_id),
        "ACCEPTANCE_DECLARATION_CHANGED",
        capability_id=id,
        capability_kind=body.kind,
        before=before,
        after=body.scope.model_dump(),
    )
    return dump(obj)
