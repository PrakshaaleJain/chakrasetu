from fastapi import APIRouter, Depends
from sqlalchemy import select
from pydantic import Field
from . import models as m
from .db import get_db
from .auth import current_user, can_view_asset
from .common import get, fail, dump, audit
from .schemas import Schema
from .services.circularity import item_access, own_facility

router = APIRouter(prefix="/circularity", tags=["circular items"])


class ImportIn(Schema):
    asset_id: str
    facility_id: str
    receipt_evidence: str = Field(min_length=3, max_length=4000)


@router.post("/items/import-battery")
def import_battery(
    body: ImportIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    facility = own_facility(db, user, body.facility_id)
    asset = get(db, m.BatteryAsset, body.asset_id)
    if asset.current_holder_org_id != user.organisation_id or not can_view_asset(
        db, user, asset
    ):
        fail("FORBIDDEN", "You must be the recorded physical custodian.", status=403)
    existing = db.scalar(
        select(m.CircularItem).where(m.CircularItem.battery_id == asset.id)
    )
    if existing:
        return dump(existing)
    # Linking never changes the original identity, legal ownership or safety flags.
    obj = m.CircularItem(
        identifier=asset.internal_id,
        kind="BATTERY",
        battery_id=asset.id,
        owner_org_id=asset.owner_org_id,
        custodian_org_id=asset.current_holder_org_id,
        facility_id=facility.id,
        mass_kg=asset.mass_kg,
        state="HOLD" if asset.state in ["HOLD", "DISPUTED"] else "AVAILABLE",
        data={
            "source": "LINKED_BATTERY_REGISTRY",
            "receipt_evidence": body.receipt_evidence,
            "synthetic": asset.data.get("synthetic", False),
        },
    )
    db.add(obj)
    db.flush()
    audit(db, user, "item", obj, "LINK_EXISTING_BATTERY")
    return dump(obj)


@router.get("/items")
def items(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        dump(x)
        for x in db.scalars(
            select(m.CircularItem).order_by(m.CircularItem.created_at.desc())
        )
        if item_access(db, user, x)
    ]
