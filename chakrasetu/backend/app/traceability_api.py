from typing import Literal
from fastapi import APIRouter, Depends
from sqlalchemy import select
from . import models as m
from .db import get_db
from .auth import current_user
from .common import get, fail, dump
from .services.circularity import item_access, job_access, job_detail

router = APIRouter(prefix="/circularity", tags=["traceability"])


@router.get("/items/{id}/trace")
def trace(
    id: str,
    direction: Literal["ANCESTORS", "DESCENDANTS", "BOTH"] = "ANCESTORS",
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    item = get(db, m.CircularItem, id)
    if not item_access(db, user, item):
        fail("FORBIDDEN", "Trace is private to authorized participants.", status=403)
    visited = set()
    nodes = []
    links = []
    jobs = []

    def walk(item_id):
        if item_id in visited:
            return
        visited.add(item_id)
        current = get(db, m.CircularItem, item_id)
        # Blended upstream counterparties get only identifiers/quantity; no private evidence leaks.
        allowed = item_access(db, user, current)
        nodes.append(
            dump(current)
            if allowed
            else {
                "id": current.id,
                "kind": current.kind,
                "mass_kg": current.mass_kg,
                "data": {"restricted": True},
            }
        )
        output = db.scalar(select(m.JobOutput).where(m.JobOutput.item_id == item_id))
        if output and direction in ["ANCESTORS", "BOTH"]:
            job = get(db, m.TransformationJob, output.job_id)
            jobs.append(
                job_detail(db, job)
                if job_access(db, user, job)
                else {"id": job.id, "operation": job.operation, "state": job.state}
            )
            for x in db.scalars(select(m.JobInput).where(m.JobInput.job_id == job.id)):
                links.append(
                    {
                        "input_item_id": x.item_id,
                        "job_id": job.id,
                        "output_item_id": item_id,
                        "input_mass_kg": x.mass_kg,
                        "output_mass_kg": output.mass_kg,
                        "allocation": "BLENDED_INPUTS_NO_EXACT_ATOM_ALLOCATION_CLAIM",
                    }
                )
                walk(x.item_id)

        if direction in ["DESCENDANTS", "BOTH"]:
            for source in db.scalars(
                select(m.JobInput).where(m.JobInput.item_id == item_id)
            ):
                job = get(db, m.TransformationJob, source.job_id)
                jobs.append(
                    job_detail(db, job)
                    if job_access(db, user, job)
                    else {"id": job.id, "operation": job.operation, "state": job.state}
                )
                for destination in db.scalars(
                    select(m.JobOutput).where(m.JobOutput.job_id == job.id)
                ):
                    links.append(
                        {
                            "input_item_id": item_id,
                            "job_id": job.id,
                            "output_item_id": destination.item_id,
                            "input_mass_kg": source.mass_kg,
                            "output_mass_kg": destination.mass_kg,
                            "allocation": "BLENDED_INPUTS_NO_EXACT_ATOM_ALLOCATION_CLAIM",
                        }
                    )
                    walk(destination.item_id)

    walk(id)
    jobs = list({x["id"]: x for x in jobs}.values())
    links = list(
        {
            (x["input_item_id"], x["job_id"], x["output_item_id"]): x for x in links
        }.values()
    )
    return {
        "root": id,
        "direction": direction,
        "items": nodes,
        "jobs": jobs,
        "links": links,
        "custody": [
            dump(x)
            for x in db.scalars(
                select(m.ItemCustodyEvent).where(m.ItemCustodyEvent.item_id == id)
            )
        ],
        "warning": "Documented provenance and operator reports; not proof of physical composition or safety certification.",
    }
