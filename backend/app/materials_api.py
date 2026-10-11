from .auth import has_role
from fastapi import APIRouter, Depends
from sqlalchemy import select
from . import models as m
from .db import get_db
from .auth import current_user
from .common import get, dump
from .services.circularity import item_access, job_access

router = APIRouter(prefix="/circularity", tags=["materials"])


@router.get("/material-lots")
def lots(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        {**dump(x), "item": dump(get(db, m.CircularItem, x.item_id))}
        for x in db.scalars(select(m.MaterialLot))
        if item_access(db, user, get(db, m.CircularItem, x.item_id))
    ]


@router.get("/recycling-batches")
def batches(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        {
            **dump(x),
            "inputs": [
                dump(i)
                for i in db.scalars(
                    select(m.BatchInput).where(m.BatchInput.batch_id == x.id)
                )
            ],
        }
        for x in db.scalars(select(m.RecyclingBatch))
        if has_role(user, "REVIEWER")
        or x.processor_org_id == user.organisation_id
        or job_access(db, user, get(db, m.TransformationJob, x.job_id))
    ]
