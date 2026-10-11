from .auth import has_role
from fastapi import APIRouter, Depends
from sqlalchemy import select
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import get, fail, dump, audit, expired
from .circular_schemas import CapabilityIn, ReviewIn
from .services.circularity import operation_role, own_facility

router = APIRouter(prefix="/circularity", tags=["operation registry"])


@router.get("/capabilities")
def capabilities(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [dump(x) for x in db.scalars(select(m.OperationCapability))]


@router.post("/capabilities")
def declare(
    body: CapabilityIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    own_facility(db, user, body.facility_id)
    if not has_role(user, "ORG_ADMIN"):
        operation_role(user, body.operation)
    if db.scalar(
        select(m.OperationCapability).where(
            m.OperationCapability.facility_id == body.facility_id,
            m.OperationCapability.operation == body.operation,
        )
    ):
        fail(
            "IDENTITY_CONFLICT",
            "An operation capability already exists; preserve its reviewed scope.",
        )
    obj = m.OperationCapability(
        **body.model_dump(exclude={"evidence"}, mode="json"),
        data={"declared_evidence": body.evidence, "provenance": "OWNER_DECLARED"},
    )
    db.add(obj)
    db.flush()
    audit(db, user, "operation_capability", obj, "DECLARE")
    return dump(obj)


@router.post("/capabilities/{id}/review")
def capability_review(
    id: str,
    body: ReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    obj = get(db, m.OperationCapability, id)
    if expired(body.valid_until):
        fail("QUALIFICATION_EXPIRED", "Qualification expiry must be in the future.")
    obj.verified = body.accepted
    obj.valid_until = body.valid_until
    obj.data = {
        **obj.data,
        "request_status": "APPROVED" if body.accepted else "SUSPENDED",
        "reviews": [
            *obj.data.get("reviews", []),
            {**body.model_dump(), "reviewer_id": user.id, "timestamp": m.now()},
        ],
    }
    audit(
        db,
        user,
        "operation_capability",
        obj,
        "REVIEW_OPERATION_SCOPE",
        **body.model_dump(),
    )
    return dump(obj)
