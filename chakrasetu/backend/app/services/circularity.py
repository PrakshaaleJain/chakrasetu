from ..auth import has_role
from ..config import APP_ENV
from sqlalchemy import select, text
from .. import models as m
from ..circular_models import Operation
from ..common import get, fail, expired, dump, audit, parse_time
from ..permissions import OPERATION_ROLES
from ..services.matching import available, handling_scope


def own_facility(db, user, id):
    facility = get(db, m.Facility, id)
    if facility.organisation_id != user.organisation_id:
        fail("FORBIDDEN", "Facility belongs to another organization.", status=403)
    return facility


def operation_role(user, operation):
    roles = set(getattr(user, "roles", [user.role]))
    if not roles & OPERATION_ROLES.get(operation, set()):
        fail(
            "FORBIDDEN",
            "An assigned operator role for this operation is required.",
            status=403,
        )


def capability_check(
    db,
    facility,
    operation,
    mass=None,
    chemistry=None,
    form=None,
    category=None,
    scope_only=False,
    asset=None,
):
    reasons = []

    def reject(code, message):
        reasons.append({"code": code, "message": message})

    org = get(db, m.Organisation, facility.organisation_id)
    if APP_ENV == "production" and (org.synthetic or facility.data.get("synthetic")):
        reject(
            "SYNTHETIC_DISABLED",
            "Synthetic qualifications do not support production operations.",
        )
    if not org.active or org.verification != "VERIFIED":
        reject(
            "IDENTITY_UNVERIFIED", "Organization identity must be active and verified."
        )
    if (
        not facility.active
        or facility.registration != "VERIFIED"
        or expired(facility.valid_until)
    ):
        reject(
            "FACILITY_UNQUALIFIED", "Facility registration must be active and current."
        )
    cap = db.scalar(
        select(m.OperationCapability).where(
            m.OperationCapability.facility_id == facility.id,
            m.OperationCapability.operation == operation,
        )
    )
    if not cap or not cap.verified or not cap.valid_until or expired(cap.valid_until):
        reject(
            "OPERATION_UNVERIFIED",
            "A declared capability is not a current verified operation qualification.",
        )
    else:
        if asset is not None:
            from .registration import acceptance_reasons

            checks = acceptance_reasons(asset, cap, str(operation))
            if scope_only and operation == "ASSESSMENT":
                checks = [
                    x
                    for x in checks
                    if x["code"]
                    not in [
                        "REGISTRATION_NOT_APPROVED",
                        "SPECIALIST_REVIEW_REQUIRED",
                        "COLLECTION_UNCONFIRMED",
                    ]
                ]
            reasons.extend(checks)
            if asset.data.get("pbs") and asset.condition not in cap.data.get(
                "conditions", []
            ):
                reject(
                    "CONDITION_MISMATCH",
                    "Operation-specific condition acceptance is not verified.",
                )
        if mass is None and not scope_only:
            reject(
                "MASS_UNKNOWN",
                "A measured/declared known mass is required for capacity planning.",
            )
        elif mass is not None and (cap.capacity_kg is None or mass > cap.capacity_kg):
            reject(
                "CAPACITY_INSUFFICIENT",
                "Known operation capacity is required and must cover the inputs.",
            )
        running = db.scalars(
            select(m.TransformationJob).where(
                m.TransformationJob.facility_id == facility.id,
                m.TransformationJob.operation == operation,
                m.TransformationJob.state == "RUNNING",
            )
        ).all()
        used = sum(
            x.mass_kg
            for job in running
            for x in db.scalars(select(m.JobInput).where(m.JobInput.job_id == job.id))
        )
        if (
            mass is not None
            and cap.capacity_kg is not None
            and used + mass > cap.capacity_kg
        ):
            reject(
                "CAPACITY_CONFLICT",
                "Running jobs already consume this operation capacity.",
            )
        if chemistry is not None and (
            chemistry not in cap.chemistries
            or (chemistry == "UNKNOWN" and operation != "ASSESSMENT")
        ):
            reject(
                "CHEMISTRY_UNSUPPORTED",
                "Unknown or incompatible chemistry cannot pass an operation requirement.",
            )
        if form is not None and (
            form not in cap.formats or (form == "UNKNOWN" and operation != "ASSESSMENT")
        ):
            reject("FORM_UNSUPPORTED", "Unknown or unsupported format.")
        if category is not None and category not in cap.material_categories:
            reject(
                "MATERIAL_SPEC_UNSUPPORTED",
                "Facility has no verified scope for this material or product category.",
            )
    return reasons


def enforce(reasons):
    if reasons:
        fail(
            reasons[0]["code"],
            reasons[0]["message"],
            next_action="Review all operation constraints and supply evidence; do not relax hard gates.",
        )


def item_access(db, user, item):
    if has_role(user, "REVIEWER") or user.organisation_id in [
        item.owner_org_id,
        item.custodian_org_id,
    ]:
        return True
    return any(
        user.organisation_id
        in [
            h.seller_org_id,
            h.buyer_org_id,
            (
                get(db, m.TransporterProfile, h.transporter_id).organisation_id
                if h.transporter_id
                else None
            ),
        ]
        for h in db.scalars(
            select(m.DownstreamHandoff).where(m.DownstreamHandoff.item_id == item.id)
        )
    )


def job_access(db, user, job):
    if (
        has_role(user, "REVIEWER")
        or get(db, m.Facility, job.facility_id).organisation_id == user.organisation_id
    ):
        return True
    return any(
        get(db, m.CircularItem, x.item_id).owner_org_id == user.organisation_id
        for x in db.scalars(select(m.JobInput).where(m.JobInput.job_id == job.id))
    )


def input_checks(db, job):
    facility = get(db, m.Facility, job.facility_id)
    inputs = db.scalars(select(m.JobInput).where(m.JobInput.job_id == job.id)).all()
    total = sum(x.mass_kg for x in inputs)
    enforce(capability_check(db, facility, job.operation, total))
    for link in inputs:
        item = get(db, m.CircularItem, link.item_id)
        if item.state not in ["AVAILABLE", "RETIRED"]:
            fail(
                "INPUT_UNAVAILABLE",
                "Input is allocated, consumed, unaccepted, in shipment or on hold.",
            )
        if (
            item.custodian_org_id != facility.organisation_id
            or item.facility_id != facility.id
        ):
            fail(
                "CUSTODY_EVIDENCE_MISSING",
                "Input must be physically received at the processing facility.",
            )
        if item.owner_org_id not in job.data.get("owner_authorizations", {}) or expired(
            job.data["owner_authorizations"][item.owner_org_id]["valid_until"]
        ):
            fail(
                "OWNER_AUTHORIZATION_REQUIRED",
                "Each input owner must approve the operation and output ownership terms.",
            )
        if item.battery_id:
            asset = get(db, m.BatteryAsset, item.battery_id)
            if (
                asset.current_holder_org_id != facility.organisation_id
                or asset.state
                in ["HOLD", "DISPUTED", "DRAFT", "REVIEW_REQUIRED", "NEEDS_INFORMATION"]
                or handling_scope(asset) != "ORDINARY"
            ):
                fail(
                    "SAFETY_REVIEW_REQUIRED",
                    "Ordinary transformation is blocked for unresolved or unsafe intake. Qualified controlled handling remains a separate review workflow.",
                )
            if asset.mass_kg != item.mass_kg:
                fail(
                    "INPUT_SCOPE_CHANGED", "Battery mass changed; revise the job scope."
                )
            enforce(
                capability_check(
                    db,
                    facility,
                    job.operation,
                    total,
                    asset.chemistry,
                    asset.form,
                    asset=asset,
                )
            )
            if job.operation in ["REFURBISHMENT", "REPURPOSING", "INTEGRATION"]:
                reports = db.scalars(
                    select(m.Assessment).where(
                        m.Assessment.asset_id == asset.id,
                        m.Assessment.intended_operation == job.operation,
                        m.Assessment.state == "ACCEPTED",
                    )
                ).all()
                if not any(
                    a.valid_until
                    and not expired(a.valid_until)
                    and a.data.get("report", {}).get("outcome")
                    == "SUITABLE_FOR_DEFINED_OPERATION"
                    and not db.scalar(
                        select(m.Assessment).where(m.Assessment.revision_of == a.id)
                    )
                    for a in reports
                ):
                    fail(
                        "ASSESSMENT_REQUIRED",
                        "A current accepted assessment for this defined operation/specification is required. A generic SOH score is insufficient.",
                    )
        else:
            if item.kind == "PRODUCT":
                product = db.scalar(
                    select(m.SecondLifeProduct).where(
                        m.SecondLifeProduct.item_id == item.id
                    )
                )
                if not product or product.state not in ["ACCEPTED", "RETIRED"]:
                    fail(
                        "PRODUCT_ACCEPTANCE_REQUIRED",
                        "Application-specific product acceptance or retirement evidence is required before further transformation.",
                    )
            enforce(
                capability_check(
                    db,
                    facility,
                    job.operation,
                    total,
                    category=item.data.get("category", "UNKNOWN"),
                )
            )
    return inputs


def job_detail(db, job):
    return {
        **dump(job),
        "inputs": [
            dump(x)
            for x in db.scalars(select(m.JobInput).where(m.JobInput.job_id == job.id))
        ],
        "outputs": [
            dump(x)
            for x in db.scalars(select(m.JobOutput).where(m.JobOutput.job_id == job.id))
        ],
    }


def start_job(db, user, job):
    own_facility(db, user, job.facility_id)
    operation_role(user, job.operation)
    if job.state != "DRAFT":
        fail("STATE_TRANSITION_INVALID", "Only a draft job can start.")
    inputs = input_checks(db, job)
    for x in inputs:
        get(db, m.CircularItem, x.item_id).state = "ALLOCATED"
    job.state = "RUNNING"
    job.started_at = m.now()
    audit(db, user, "job", job, "START_JOB", input_ids=[x.item_id for x in inputs])
    return job_detail(db, job)


def complete_job(db, user, job, body):
    facility = own_facility(db, user, job.facility_id)
    operation_role(user, job.operation)
    if job.state != "RUNNING":
        fail("STATE_TRANSITION_INVALID", "Only a running job can record outputs.")
    inputs = db.scalars(select(m.JobInput).where(m.JobInput.job_id == job.id)).all()
    total = sum(x.mass_kg for x in inputs)
    # Recheck qualification, but do not count this running job twice against capacity.
    for x in inputs:
        item = get(db, m.CircularItem, x.item_id)
        if (
            item.state != "ALLOCATED"
            or item.custodian_org_id != facility.organisation_id
        ):
            fail("INPUT_SCOPE_CHANGED", "Input allocation or custody changed.")
        if item.battery_id and get(db, m.BatteryAsset, item.battery_id).state in [
            "HOLD",
            "DISPUTED",
        ]:
            fail(
                "SAFETY_REVIEW_REQUIRED",
                "A new battery hold blocks processing completion.",
            )
    cap = db.scalar(
        select(m.OperationCapability).where(
            m.OperationCapability.facility_id == facility.id,
            m.OperationCapability.operation == job.operation,
        )
    )
    if (
        not cap
        or not cap.verified
        or not cap.valid_until
        or expired(cap.valid_until)
        or facility.registration != "VERIFIED"
        or expired(facility.valid_until)
    ):
        fail(
            "OPERATION_UNVERIFIED",
            "Qualification expired or was suspended during processing.",
        )
    output_total = sum(x.mass_kg for x in body.outputs)
    if abs(output_total + body.measured_loss_kg - total) > 0.001:
        fail(
            "MASS_BALANCE_MISMATCH",
            "Measured outputs plus documented loss must reconcile to input mass within 1 gram. Added inputs must be recorded explicitly.",
        )
    identifiers = [x.identifier for x in body.outputs]
    if len(set(identifiers)) != len(identifiers) or db.scalar(
        select(m.CircularItem).where(m.CircularItem.identifier.in_(identifiers))
    ):
        fail("IDENTITY_CONFLICT", "Output identifiers must be unique.")
    expected = {
        "INTEGRATION": {"PRODUCT"},
        "REFURBISHMENT": {"PRODUCT"},
        "REPURPOSING": {"PRODUCT"},
        "RECYCLING": {"MATERIAL"},
        "DISMANTLING": {"MATERIAL"},
        "PROCESSING": {"MATERIAL"},
        "REFINING": {"MATERIAL"},
        "MANUFACTURING": {"MATERIAL", "PRODUCT"},
    }
    if any(x.kind not in expected.get(job.operation, set()) for x in body.outputs):
        fail("OUTPUT_KIND_INVALID", "Output kind does not match the defined operation.")
    for out in body.outputs:
        item = m.CircularItem(
            identifier=out.identifier,
            kind=out.kind,
            owner_org_id=facility.organisation_id,
            custodian_org_id=facility.organisation_id,
            facility_id=facility.id,
            mass_kg=out.mass_kg,
            state="ACCEPTANCE_PENDING",
            data={
                **out.model_dump(mode="json"),
                "source": "TECHNICIAN_RECORDED",
                "synthetic": job.data.get("synthetic", False),
            },
        )
        db.add(item)
        db.flush()
        db.add(m.JobOutput(job_id=job.id, item_id=item.id, mass_kg=out.mass_kg))
        if out.kind == "PRODUCT":
            db.add(
                m.SecondLifeProduct(
                    item_id=item.id,
                    source_job_id=job.id,
                    integrator_org_id=facility.organisation_id,
                    intended_application=out.category,
                    data={
                        "specification": out.specification,
                        "evidence": out.evidence,
                        "synthetic": job.data.get("synthetic", False),
                    },
                )
            )
        else:
            db.add(
                m.MaterialLot(
                    item_id=item.id,
                    source_job_id=job.id,
                    processor_org_id=facility.organisation_id,
                    category=out.category,
                    quantity=out.mass_kg,
                    unit="kg",
                    data={
                        "composition_quality_evidence": out.evidence,
                        "specification": out.specification,
                        "synthetic": job.data.get("synthetic", False),
                    },
                )
            )
    for x in inputs:
        get(db, m.CircularItem, x.item_id).state = "CONSUMED"
    job.state = "COMPLETED_REPORTED"
    job.completed_at = m.now()
    job.data = {
        **job.data,
        "completion": body.model_dump(mode="json"),
        "recorded_by": user.id,
        "recorded_at": m.now(),
    }
    audit(
        db,
        user,
        "job",
        job,
        "OUTPUTS_REPORTED",
        input_mass_kg=total,
        output_mass_kg=output_total,
        loss_kg=body.measured_loss_kg,
    )
    db.flush()
    return job_detail(db, job)
