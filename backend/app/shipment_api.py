from .auth import has_role
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, text
from . import models as m
from .common import get, dump, fail, idem, audit, exception
from .auth import current_user
from .db import get_db
from .schemas import ShipmentEventIn, HubEventIn, TelemetryIn
from .services.shipments import context, event, hub_event, closure_check

router = APIRouter()


def shipment_access(db, user, s):
    tx, asset, t = context(db, s)
    hub_id = get(db, m.RoutePlan, s.route_id).hub_id
    orgs = [tx.seller_org_id, tx.buyer_org_id, t.organisation_id] + (
        [get(db, m.Facility, hub_id).organisation_id] if hub_id else []
    )
    if not has_role(user, "REVIEWER") and user.organisation_id not in orgs:
        fail("FORBIDDEN", "Shipment access is restricted.", status=403)


@router.get("/shipments")
def shipments(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    out = []
    for s in db.scalars(
        select(m.Shipment).order_by(m.Shipment.created_at.desc())
    ).all():
        try:
            shipment_access(db, user, s)
        except HTTPException as error:
            if error.status_code == 403:
                continue
            raise
        tx, asset, t = context(db, s)
        out.append(
            {
                **dump(s),
                "asset": {
                    "id": asset.id,
                    "internal_id": asset.internal_id,
                    "current_holder_org_id": asset.current_holder_org_id,
                    "custody_segments": asset.data.get("custody_segments"),
                },
                "transporter_org_id": t.organisation_id,
                "buyer_org_id": tx.buyer_org_id,
                "seller_org_id": tx.seller_org_id,
                "route": dump(get(db, m.RoutePlan, s.route_id)),
            }
        )
    return out


@router.get("/shipments/{id}")
def detail(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    s = get(db, m.Shipment, id)
    shipment_access(db, user, s)
    return {
        **dump(s),
        "items": [
            dump(x)
            for x in db.scalars(
                select(m.ShipmentItem).where(m.ShipmentItem.shipment_id == id)
            ).all()
        ],
        "custody": [
            dump(x)
            for x in db.scalars(
                select(m.CustodyEvent)
                .where(m.CustodyEvent.shipment_id == id)
                .order_by(m.CustodyEvent.created_at)
            ).all()
        ],
        "telemetry": [
            dump(x)
            for x in db.scalars(
                select(m.TelemetryEvent).where(m.TelemetryEvent.shipment_id == id)
            ).all()
        ],
        "closure": closure_check(db, s),
    }


@router.post("/shipments/{id}/events")
def events(
    id: str,
    body: ShipmentEventIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    s = get(db, m.Shipment, id)
    shipment_access(db, user, s)
    return idem(
        db,
        user,
        idempotency_key,
        "shipment-event",
        {"id": id, **body.model_dump(mode="json")},
        lambda: event(db, user, s, body),
    )


@router.post("/shipments/{id}/hub-events")
def hub(
    id: str,
    body: HubEventIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    return idem(
        db,
        user,
        idempotency_key,
        "hub-event",
        {"id": id, **body.model_dump()},
        lambda: hub_event(db, user, get(db, m.Shipment, id), body),
    )


@router.post("/shipments/{id}/telemetry")
def telemetry(
    id: str,
    body: TelemetryIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    s = get(db, m.Shipment, id)
    shipment_access(db, user, s)
    tx, asset, t = context(db, s)
    if user.organisation_id != t.organisation_id:
        fail("FORBIDDEN", "Assigned transporter emits demo telemetry.", status=403)
    if s.state not in ["PICKED_UP", "IN_TRANSIT", "EXCEPTION_HOLD"]:
        fail("STATE_TRANSITION_INVALID", "Telemetry requires an active shipment.")
    from .config import TELEMETRY_THRESHOLDS

    thresholds = TELEMETRY_THRESHOLDS
    alert = body.event in ["MISSING_EVENT", "REPORTED_INCIDENT"] or (
        body.event in thresholds
        and body.value is not None
        and body.value > thresholds[body.event]
    )
    row = m.TelemetryEvent(
        shipment_id=id,
        actor_id=user.id,
        alert=alert,
        data={
            **body.model_dump(),
            "rule_version": "demo-telemetry-1",
            "threshold": thresholds.get(body.event),
            "source": "SIMULATED",
            "notice": "Synthetic demonstration signal. Not a diagnosis or proof of damage.",
        },
    )
    db.add(row)
    db.flush()
    if alert:
        exception(
            db,
            "shipment",
            id,
            "SAFETY_FLAG" if body.event == "REPORTED_INCIDENT" else "TRANSIT_ALERT",
            "org-review",
            "Review synthetic alert and request transporter confirmation. No automatic redirection.",
            "HIGH" if body.event == "REPORTED_INCIDENT" else "MEDIUM",
            telemetry_id=row.id,
            source="SIMULATED",
            event=body.event,
        )
    if body.event == "REPORTED_INCIDENT":
        s.data = {**s.data, "resume_state": s.state}
        s.state = "EXCEPTION_HOLD"
        asset.state = "HOLD"
        asset.data = {
            **asset.data,
            "handling_clearance": None,
            "flags": {**asset.data.get("flags", {}), "thermal_event": "YES"},
        }
    audit(
        db, user, "shipment", s, "SIMULATED_TELEMETRY", telemetry_id=row.id, alert=alert
    )
    return dump(row)
