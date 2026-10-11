from fastapi import APIRouter, Depends
from pydantic import Field
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import get, dump, fail, audit, expired
from .schemas import Schema

router = APIRouter(prefix="/circularity", tags=["downstream scope"])


class ScopeIn(Schema):
    kinds: list[str] = Field(min_length=1, max_length=2)
    categories: list[str] = Field(min_length=1, max_length=30)
    evidence: str = Field(min_length=3, max_length=4000)
    valid_until: str


@router.post("/transporters/{id}/scope-review")
def scope_review(
    id: str,
    body: ScopeIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    t = get(db, m.TransporterProfile, id)
    if not set(body.kinds) <= {"PRODUCT", "MATERIAL"} or expired(body.valid_until):
        fail(
            "SCOPE_INVALID",
            "Use PRODUCT/MATERIAL scope with current qualification evidence.",
        )
    t.data = {
        **t.data,
        "verified_downstream_kinds": body.kinds,
        "verified_downstream_categories": body.categories,
        "downstream_scope_review": {
            "evidence": body.evidence,
            "reviewer_id": user.id,
            "timestamp": m.now(),
            "valid_until": body.valid_until,
        },
    }
    audit(db, user, "transporter", t, "DOWNSTREAM_SCOPE_REVIEW")
    return dump(t)


@router.post("/facilities/{id}/receiving-scope")
def facility_scope(
    id: str,
    body: ScopeIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    f = get(db, m.Facility, id)
    if expired(body.valid_until):
        fail("SCOPE_INVALID", "Receiving scope must be current.")
    f.data = {
        **f.data,
        "verified_receiving_categories": body.categories,
        "receiving_scope_review": {
            **body.model_dump(),
            "reviewer_id": user.id,
            "timestamp": m.now(),
        },
    }
    audit(db, user, "facility", f, "RECEIVING_SCOPE_REVIEW")
    return dump(f)
