from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import get, fail, audit, idem, expired
from .circular_schemas import CompleteIn, JobIn, ReviewIn
from .services.circularity import (
    capability_check,
    complete_job,
    enforce,
    job_access,
    job_detail,
    operation_role,
    own_facility,
    start_job,
)

router = APIRouter(prefix="/circularity", tags=["transformation"])


@router.get("/jobs")
def jobs(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        job_detail(db, x)
        for x in db.scalars(
            select(m.TransformationJob).order_by(m.TransformationJob.created_at.desc())
        )
        if job_access(db, user, x)
    ]


@router.post("/jobs")
def create_job(
    body: JobIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    facility = own_facility(db, user, body.facility_id)
    operation_role(user, body.operation)
    if body.operation == "ASSESSMENT":
        fail(
            "USE_ASSESSMENT_WORKFLOW",
            "Use the structured assessment endpoint for a non-consuming diagnostic operation.",
        )
    if len(set(body.item_ids)) != len(body.item_ids):
        fail("DUPLICATE_INPUT", "An input must appear only once.")

    def create():
        inputs = [get(db, m.CircularItem, id) for id in body.item_ids]
        if any(x.custodian_org_id != user.organisation_id for x in inputs):
            fail("FORBIDDEN", "All job inputs must be in your custody.", status=403)
        if any(x.mass_kg is None for x in inputs):
            fail(
                "MASS_UNKNOWN", "Known input masses are required; unknown is not zero."
            )
        if any(x.state not in ["AVAILABLE", "RETIRED"] for x in inputs):
            fail("INPUT_UNAVAILABLE", "Inputs must be available and accepted.")
        enforce(
            capability_check(
                db, facility, body.operation, sum(x.mass_kg for x in inputs)
            )
        )
        obj = m.TransformationJob(
            facility_id=facility.id,
            operator_id=user.id,
            operation=body.operation,
            data={
                "procedure": body.procedure,
                "evidence": body.evidence,
                "owner_authorizations": {},
                "synthetic": all(x.data.get("synthetic", False) for x in inputs),
                "output_ownership_terms": "Input owners explicitly authorize this operation and transfer ownership of documented outputs to the operating organization; input custody alone is insufficient.",
            },
        )
        db.add(obj)
        db.flush()
        for item in inputs:
            db.add(m.JobInput(job_id=obj.id, item_id=item.id, mass_kg=item.mass_kg))
        if body.operation == "RECYCLING":
            batch = m.RecyclingBatch(
                job_id=obj.id,
                identifier="BATCH-" + obj.id,
                processor_org_id=user.organisation_id,
                data={
                    "synthetic": obj.data["synthetic"],
                    "provenance": "PROCESSOR_RECORDED",
                },
            )
            db.add(batch)
            db.flush()
            for item in inputs:
                db.add(
                    m.BatchInput(
                        batch_id=batch.id, item_id=item.id, mass_kg=item.mass_kg
                    )
                )
        audit(db, user, "job", obj, "CREATE_JOB")
        db.flush()
        return job_detail(db, obj)

    return idem(
        db,
        user,
        idempotency_key,
        "create-transformation",
        body.model_dump(mode="json"),
        create,
    )


@router.post("/jobs/{id}/authorize")
def authorize(
    id: str,
    body: ReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    obj = get(db, m.TransformationJob, id)
    if obj.state != "DRAFT":
        fail(
            "STATE_TRANSITION_INVALID",
            "Ownership terms are locked once processing starts.",
        )
    owner_ids = {
        get(db, m.CircularItem, x.item_id).owner_org_id
        for x in db.scalars(select(m.JobInput).where(m.JobInput.job_id == id))
    }
    if user.organisation_id not in owner_ids or not has_role(
        user,
        "ORIGINATOR",
        "BUYER",
        "REFURBISHER",
        "SECOND_LIFE",
        "RECYCLER",
        "PROCESSOR",
        "REFINER",
        "MANUFACTURER",
        "CUSTOMER",
    ):
        fail(
            "FORBIDDEN",
            "Only an authorized input owner may approve processing and output ownership.",
            status=403,
        )
    if not body.accepted or expired(body.valid_until):
        fail(
            "OWNER_AUTHORIZATION_REQUIRED",
            "Explicit current owner approval is required.",
        )
    obj.data = {
        **obj.data,
        "owner_authorizations": {
            **obj.data.get("owner_authorizations", {}),
            user.organisation_id: {
                **body.model_dump(),
                "actor_id": user.id,
                "timestamp": m.now(),
            },
        },
    }
    audit(db, user, "job", obj, "OWNER_APPROVED_OUTPUT_TERMS")
    return job_detail(db, obj)


@router.post("/jobs/{id}/start")
def start(
    id: str,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    return idem(
        db,
        user,
        idempotency_key,
        "start-job",
        {"id": id},
        lambda: start_job(db, user, get(db, m.TransformationJob, id)),
    )


@router.post("/jobs/{id}/complete")
def complete(
    id: str,
    body: CompleteIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    return idem(
        db,
        user,
        idempotency_key,
        "complete-job",
        {"id": id, **body.model_dump(mode="json")},
        lambda: complete_job(db, user, get(db, m.TransformationJob, id), body),
    )


@router.post("/jobs/{id}/review")
def accept_job(
    id: str,
    body: ReviewIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    obj = get(db, m.TransformationJob, id)
    if obj.state != "COMPLETED_REPORTED" or obj.operator_id == user.id:
        fail(
            "INDEPENDENT_REVIEW_REQUIRED",
            "Reported completion requires independent documentary review.",
        )
    if expired(body.valid_until):
        fail("REVIEW_EXPIRED", "Review validity must be in the future.")
    obj.state = "ACCEPTED" if body.accepted else "DISPUTED"
    obj.accepted_by = user.id
    obj.data = {
        **obj.data,
        "acceptance": {
            **body.model_dump(),
            "timestamp": m.now(),
            "reviewer_id": user.id,
        },
    }
    for link in db.scalars(select(m.JobOutput).where(m.JobOutput.job_id == id)):
        item = get(db, m.CircularItem, link.item_id)
        item.state = "AVAILABLE" if body.accepted else "HOLD"
        item.data = {**item.data, "processing_acceptance_evidence": body.evidence}
    if not body.accepted:
        from .common import exception

        exception(
            db,
            "job",
            id,
            "PROCESSING_DISCREPANCY",
            get(db, m.Facility, obj.facility_id).organisation_id,
            "Resolve documentary discrepancy; outputs remain held.",
            evidence=body.evidence,
        )
    audit(db, user, "job", obj, "REVIEW_REPORTED_PROCESSING")
    return job_detail(db, obj)
