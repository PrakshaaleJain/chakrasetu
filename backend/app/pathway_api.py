from typing import Literal
from pydantic import Field
from sqlalchemy import select
from fastapi import APIRouter, Depends
from . import models as m
from .schemas import Schema
from .db import get_db
from .auth import current_user, can_view_asset
from .common import get, fail, dump, audit
from .services.pathways import plan


class EconomicEstimate(Schema):
    terminal_revenue_paise: int | None = Field(default=None, ge=0, strict=True)
    acquisition_paise: int | None = Field(default=None, ge=0, strict=True)
    assessment_paise: int | None = Field(default=None, ge=0, strict=True)
    processing_paise: int | None = Field(default=None, ge=0, strict=True)
    transport_paise: int | None = Field(default=None, ge=0, strict=True)
    overhead_paise: int | None = Field(default=None, ge=0, strict=True)
    source: Literal["OWNER_ESTIMATED", "SYNTHETIC"]
    reference: str = Field(min_length=3, max_length=1000)


class PlanningIn(Schema):
    inputs: dict[
        Literal["SECOND_LIFE", "RECOVER_MATERIALS", "DISMANTLE_PROCESS"],
        EconomicEstimate,
    ] = Field(default_factory=dict)


router = APIRouter(prefix="/circularity", tags=["explainable pathway recommendations"])


@router.post("/batteries/{id}/pathways")
def generate(
    id: str,
    body: PlanningIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    asset = get(db, m.BatteryAsset, id)
    if not can_view_asset(db, user, asset):
        fail("FORBIDDEN", "Pathway evidence is restricted.", status=403)
    result = plan(db, asset, body.model_dump()["inputs"])
    obj = m.PathwayDecision(asset_id=id, actor_id=user.id, data=result)
    db.add(obj)
    db.flush()
    audit(
        db,
        user,
        "battery",
        asset,
        "PATHWAY_RECOMMENDATION_RECORDED",
        decision_id=obj.id,
    )
    return {**result, "decision_id": obj.id}


@router.get("/batteries/{id}/pathways")
def history(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    asset = get(db, m.BatteryAsset, id)
    if not can_view_asset(db, user, asset):
        fail("FORBIDDEN", "Pathway history is restricted.", status=403)
    return [
        dump(x)
        for x in db.scalars(
            select(m.PathwayDecision)
            .where(m.PathwayDecision.asset_id == id)
            .order_by(m.PathwayDecision.created_at.desc())
        )
    ]
