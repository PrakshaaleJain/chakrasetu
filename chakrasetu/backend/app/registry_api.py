from fastapi import APIRouter, Depends
from sqlalchemy import select
from pydantic import Field
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import dump, get, audit, future
from .schemas import Schema
from .enums import Chemistry, Pathway

router = APIRouter()


@router.get("/me")
def me(user=Depends(current_user)):
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "organisation_id": user.organisation_id,
    }


@router.get("/network")
def network(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    # Explicit allowlists: new profile/contact metadata must never leak through the legacy directory.
    orgs = []
    for o in db.scalars(select(m.Organisation)):
        row = dump(o)
        row["data"] = {}
        orgs.append(row)
    allowed = {
        "declared_chemistries",
        "verified_chemistries",
        "chemistries",
        "forms",
        "conditions",
        "handling_scope",
        "center",
        "radius_km",
        "rate_source",
        "window_start",
        "window_end",
    }

    def projection(model):
        return [
            {**dump(x), "data": {k: v for k, v in x.data.items() if k in allowed}}
            for x in db.scalars(select(model))
        ]

    return {
        "organisations": orgs,
        "facilities": projection(m.Facility),
        "capabilities": projection(m.FacilityCapability),
        "transporters": projection(m.TransporterProfile),
    }


class OrgIn(Schema):
    name: str = Field(min_length=2, max_length=200)
    role: str = Field(pattern="^(ORIGINATOR|BUYER|TRANSPORTER|HUB)$")
    address: str = Field(min_length=1)
    contact: str = Field(min_length=1)


@router.post("/organisations")
def organisation(
    body: OrgIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    role(user, "REVIEWER")
    obj = m.Organisation(
        name=body.name,
        role=body.role,
        data={
            "status": "PENDING_REVIEW",
            "address": body.address,
            "contact": body.contact,
        },
    )
    db.add(obj)
    db.flush()
    audit(db, user, "organisation", obj, "ONBOARD")
    return dump(obj)


class FacilityIn(Schema):
    name: str = Field(min_length=2)
    kind: str = Field(pattern="^(RECEIVER|HUB|REVIEW)$")
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    pathway: Pathway
    chemistries: list[Chemistry]
    capacity_kg: float = Field(gt=0)


@router.post("/facilities")
def facility(
    body: FacilityIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    role(user, "BUYER", "HUB", "REVIEWER", "ORG_ADMIN", "TECHNICIAN")
    obj = m.Facility(
        organisation_id=user.organisation_id,
        name=body.name,
        kind=body.kind,
        lat=body.lat,
        lng=body.lng,
        valid_until=future(days=30),
        data={"status": "PENDING_REVIEW"},
    )
    db.add(obj)
    db.flush()
    db.add(
        m.FacilityCapability(
            facility_id=obj.id,
            pathway=body.pathway,
            capacity_kg=body.capacity_kg,
            available_kg=body.capacity_kg,
            valid_until=future(days=30),
            data={
                "declared_chemistries": body.chemistries,
                "verified_chemistries": [],
                "forms": [],
                "conditions": [],
                "handling_scope": "UNVERIFIED",
            },
        )
    )
    audit(db, user, "facility", obj, "ONBOARD")
    return dump(obj)


class TransporterIn(Schema):
    name: str = Field(min_length=2)
    capacity_kg: float = Field(gt=0)
    center: list[float] = Field(min_length=2, max_length=2)
    radius_km: float = Field(gt=0)


@router.post("/transporters")
def transporter(
    body: TransporterIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "TRANSPORTER")
    obj = m.TransporterProfile(
        organisation_id=user.organisation_id,
        name=body.name,
        capacity_kg=body.capacity_kg,
        valid_until=future(days=30),
        data={**body.model_dump(), "handling_scope": "UNVERIFIED"},
    )
    db.add(obj)
    db.flush()
    audit(db, user, "transporter", obj, "ONBOARD")
    return dump(obj)


from typing import Literal
from .enums import Chemistry, Form, Condition, Pathway, Verification


class VerificationIn(Schema):
    verification: Verification
    valid_until: str
    reason: str = Field(min_length=3)
    evidence: str = Field(min_length=1)
    chemistries: list[Chemistry] = Field(default_factory=list)
    forms: list[Form] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    handling_scope: Literal["ORDINARY", "CONTROLLED_HANDLING"] = "ORDINARY"
    window_start: str | None = None
    window_end: str | None = None


@router.post("/network/{kind}/{id}/review")
def review_network(
    kind: str,
    id: str,
    body: VerificationIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    models = {
        "organisation": m.Organisation,
        "facility": m.Facility,
        "capability": m.FacilityCapability,
        "transporter": m.TransporterProfile,
    }
    from .common import fail, expired

    if kind not in models:
        fail("VALIDATION_ERROR", "Unknown registry record type.")
    obj = get(db, models[kind], id)
    before = dump(obj)
    if body.verification == "VERIFIED" and expired(body.valid_until):
        fail(
            "REGISTRATION_INVALID_OR_EXPIRED",
            "Verification cannot be valid with an expired document.",
        )
    if kind == "facility":
        obj.registration = body.verification
    else:
        obj.verification = body.verification
    if kind != "organisation":
        obj.valid_until = body.valid_until
    review = {**body.model_dump(mode="json"), "actor_id": user.id, "timestamp": m.now()}
    obj.data = {
        **obj.data,
        "request_status": (
            "APPROVED" if body.verification == "VERIFIED" else body.verification
        ),
        "verification_reviews": [*obj.data.get("verification_reviews", []), review],
    }
    if kind in ["capability", "transporter"] and body.verification == "VERIFIED":
        obj.data = {
            **obj.data,
            "handling_scope": body.handling_scope,
            "forms": body.forms,
            "conditions": body.conditions,
        }
        key = "verified_chemistries" if kind == "capability" else "chemistries"
        obj.data = {**obj.data, key: body.chemistries}
    if body.window_start and body.window_end:
        obj.data = {
            **obj.data,
            "window_start": body.window_start,
            "window_end": body.window_end,
        }
    audit(
        db,
        user,
        kind,
        obj,
        "VERIFY_SCOPED_REGISTRY",
        before=before,
        after=dump(obj),
        review=review,
    )
    return dump(obj)
