from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from . import models as m
from .db import get_db
from .auth import current_user
from .common import get, fail, dump, audit, idem
from .circular_schemas import EventIn
from .services.circularity import item_access

router = APIRouter(prefix="/circularity", tags=["products"])


@router.get("/products")
def products(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        {
            **dump(x),
            "item": dump(get(db, m.CircularItem, x.item_id)),
            "events": [
                dump(e)
                for e in db.scalars(
                    select(m.ProductEvent).where(m.ProductEvent.product_id == x.id)
                )
            ],
        }
        for x in db.scalars(select(m.SecondLifeProduct))
        if item_access(db, user, get(db, m.CircularItem, x.item_id))
    ]


@router.post("/products/{id}/events")
def product_event(
    id: str,
    body: EventIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    product = get(db, m.SecondLifeProduct, id)
    item = get(db, m.CircularItem, product.item_id)
    existing_contract = product.data.get("take_back_terms")
    contracting = body.event == "TAKE_BACK_CONTRACT" and (
        user.organisation_id == product.integrator_org_id
        or (
            existing_contract
            and user.organisation_id == existing_contract["customer_org_id"]
        )
    )
    if item.custodian_org_id != user.organisation_id and not contracting:
        fail(
            "FORBIDDEN",
            "Only the current physical custodian or named take-back counterparty may record this event.",
            status=403,
        )
    if not has_role(
        user,
        "SECOND_LIFE",
        "CUSTOMER",
        "MANUFACTURER",
        "BUYER",
        "REFURBISHER",
        "TRANSPORTER",
    ):
        fail("FORBIDDEN", "Assigned product operator role required.", status=403)

    if (
        has_role(user, "TRANSPORTER")
        and not has_role(
            user, "SECOND_LIFE", "CUSTOMER", "MANUFACTURER", "BUYER", "REFURBISHER"
        )
        and body.event != "INCIDENT_REPORTED"
    ):
        fail(
            "FORBIDDEN",
            "Transporters may only report incidents for products in their physical custody.",
            status=403,
        )

    def record():
        if body.event == "ACCEPT":
            if item.state != "AVAILABLE" or product.state != "ACCEPTANCE_PENDING":
                fail(
                    "STATE_TRANSITION_INVALID",
                    "Processing must be accepted before product acceptance.",
                )
            product.state = "ACCEPTED"
        elif body.event == "DEPLOY":
            if (
                product.state != "ACCEPTED"
                or item.state != "AVAILABLE"
                or not body.customer_org_id
                or body.customer_org_id != user.organisation_id
            ):
                fail(
                    "DEPLOYMENT_ACCEPTANCE_REQUIRED",
                    "Deploy only an accepted product at the receiving customer after physical receipt.",
                )
            if (
                not has_role(user, "CUSTOMER")
                or get(db, m.Organisation, user.organisation_id).verification
                != "VERIFIED"
            ):
                fail(
                    "DEPLOYMENT_CUSTOMER_REQUIRED",
                    "Deployment must be recorded by the assigned verified customer after receipt.",
                )
            product.customer_org_id = body.customer_org_id
            product.state = "DEPLOYED"
            item.state = "DEPLOYED"
        elif body.event == "RETIRE":
            if product.state != "DEPLOYED" or item.state != "DEPLOYED":
                fail("STATE_TRANSITION_INVALID", "Only a deployed product can retire.")
            product.state = "RETIRED"
            item.state = "RETIRED"
            item.data = {**item.data, "lifecycle_retired": True}
        elif body.event == "SERVICE":
            if product.state != "DEPLOYED":
                fail("STATE_TRANSITION_INVALID", "Service record requires deployment.")
        elif body.event == "TAKE_BACK_CONTRACT":
            if (
                not body.customer_org_id
                or body.customer_org_id == product.integrator_org_id
            ):
                fail(
                    "FIELD_REQUIRED",
                    "Name the distinct take-back customer counterparty.",
                )
            get(db, m.Organisation, body.customer_org_id)
            if user.organisation_id not in [
                product.integrator_org_id,
                body.customer_org_id,
            ]:
                fail(
                    "FORBIDDEN",
                    "Only the integrator and addressed customer may approve these terms.",
                    status=403,
                )
            prior = product.data.get("take_back_terms")
            if prior and (
                prior["terms"] != body.notes
                or prior["customer_org_id"] != body.customer_org_id
            ):
                fail(
                    "TERMS_VERSION_MISMATCH",
                    "Both parties must confirm the same recorded take-back terms; corrections require a new contract version.",
                )
            approvals = {
                **(prior or {}).get("approvals", {}),
                user.organisation_id: {
                    "actor_id": user.id,
                    "evidence": body.evidence,
                    "timestamp": m.now(),
                },
            }
            agreed = {product.integrator_org_id, body.customer_org_id} <= set(approvals)
            product.data = {
                **product.data,
                "take_back_terms": {
                    "terms": body.notes,
                    "customer_org_id": body.customer_org_id,
                    "approvals": approvals,
                    "status": "CONTRACTED" if agreed else "PROPOSED",
                },
            }
        elif body.event == "INCIDENT_REPORTED":
            if item.state == "CONSUMED":
                fail(
                    "STATE_TRANSITION_INVALID",
                    "Consumed product has downstream outputs; open an incident on the affected current item.",
                )
            product.state = "HOLD"
            item.state = "HOLD"
            from .common import exception

            exception(
                db,
                "item",
                item.id,
                "POTENTIAL_SAFETY_INCIDENT",
                user.organisation_id,
                "Keep item on hold and obtain qualified review; telemetry/reporting is not a diagnosis.",
                severity="HIGH",
                evidence=body.evidence,
                report=body.notes,
            )
        if body.event in ["ACCEPT", "TAKE_BACK_CONTRACT"] and item.state not in [
            "AVAILABLE",
            "RETIRED",
        ]:
            fail(
                "PRODUCT_UNAVAILABLE",
                "Held, consumed, allocated or in-transit products cannot enter new acceptance contracts.",
            )
        obj = m.ProductEvent(
            product_id=id,
            actor_id=user.id,
            event_type=(
                (
                    "TAKE_BACK_CONFIRMED"
                    if product.data["take_back_terms"]["status"] == "CONTRACTED"
                    else "TAKE_BACK_PROPOSED"
                )
                if body.event == "TAKE_BACK_CONTRACT"
                else body.event
            ),
            data={
                **body.model_dump(),
                "timestamp": m.now(),
                "provenance": "OPERATOR_RECORDED",
                "synthetic": item.data.get("synthetic", False),
            },
        )
        db.add(obj)
        db.flush()
        audit(db, user, "product", product, "APPEND_PRODUCT_EVENT", event_id=obj.id)
        return dump(obj)

    return idem(
        db,
        user,
        idempotency_key,
        "product-event",
        {"id": id, **body.model_dump()},
        record,
    )
