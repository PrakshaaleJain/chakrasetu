from sqlalchemy import select
from .. import models as m
from ..common import get, fail, audit, exception, dump
from ..enums import TRANSITIONS
from .matching import ordinary
from .commercial import current_terms, amend


def context(db, s):
    tx = get(db, m.SaleTransaction, s.transaction_id)
    asset = get(db, m.BatteryAsset, tx.asset_id)
    quote = get(db, m.TransportQuote, s.quote_id)
    t = get(db, m.TransporterProfile, quote.transporter_id)
    return tx, asset, t


def custody(db, user, s, asset, new_holder, event_type, evidence, **data):
    row = m.CustodyEvent(
        shipment_id=s.id,
        asset_id=asset.id,
        actor_id=user.id,
        previous_holder=asset.current_holder_org_id,
        new_holder=new_holder,
        event_type=event_type,
        data={
            "evidence": evidence,
            "timestamp": m.now(),
            "location": asset.data.get("physical_location", asset.data.get("address")),
            "quantity": asset.quantity,
            **data,
        },
    )
    db.add(row)
    asset.current_holder_org_id = new_holder
    asset.custodian_org_id = new_holder
    return row


def has_open_cases(db, s, tx, asset):
    return [
        c
        for c in db.scalars(
            select(m.ExceptionCase).where(m.ExceptionCase.status != "CLOSED")
        ).all()
        if (c.object_type, c.object_id)
        in [("shipment", s.id), ("transaction", tx.id), ("battery", asset.id)]
    ]


def closure_check(db, s):
    tx, asset, _ = context(db, s)
    reasons = []
    if s.state not in ["RECEIVED", "DISPOSITION_PENDING"]:
        reasons.append("Physical receipt and inspection acceptance are required.")
    if not s.data.get("inspection_accepted"):
        reasons.append("Inspection has not been accepted.")
    terms = current_terms(db, tx)
    if set(terms.confirmations) != {tx.seller_org_id, tx.buyer_org_id}:
        reasons.append("Current terms lack both confirmations.")
    settlement = db.scalar(
        select(m.SettlementRecord).where(m.SettlementRecord.transaction_id == tx.id)
    )
    if not settlement or settlement.status != "SETTLED_CONFIRMED":
        reasons.append(
            "Record-only settlement must be confirmed by the payee with evidence."
        )
    outcomes = {
        "REFURBISHMENT_COMPLETED",
        "SECOND_LIFE_ASSESSMENT_COMPLETED",
        "RECYCLING_COMPLETED",
        "TRANSFERRED_TO_ELIGIBLE_OPERATOR",
    }
    disposition = db.scalars(
        select(m.DispositionRecord).where(m.DispositionRecord.asset_id == asset.id)
    ).all()
    if not any(d.outcome in outcomes and d.data.get("evidence") for d in disposition):
        reasons.append(
            "Final disposition evidence is required; receipt or sent-for-recycling is insufficient."
        )
    if has_open_cases(db, s, tx, asset):
        reasons.append("Linked exceptions remain unresolved.")
    item = db.scalar(select(m.ShipmentItem).where(m.ShipmentItem.shipment_id == s.id))
    if not item or item.receipt != "ACCEPTED":
        reasons.append("All asset quantities must be physically accepted.")
    return {"can_close": not reasons, "reasons": reasons}


def event(db, user, s, body):
    from ..auth import role

    role(user, "ORIGINATOR", "BUYER", "TRANSPORTER")
    tx, asset, t = context(db, s)
    target = body.state
    before = s.state
    if before == "RECEIPT_DISPUTED":
        fail(
            "CONDITION_MISMATCH",
            "Authorised reviewer must resolve the dispute before another physical receipt.",
        )
    if target not in TRANSITIONS.get(before, set()):
        fail("STATE_TRANSITION_INVALID", f"{before} cannot transition to {target}.")
    if user.organisation_id not in [
        tx.seller_org_id,
        tx.buyer_org_id,
        t.organisation_id,
    ]:
        fail("FORBIDDEN", "Only shipment participants may act.", status=403)
    receiver_states = ["RECEIVED", "RECEIPT_DISPUTED", "DISPOSITION_PENDING", "CLOSED"]
    if target in receiver_states and user.organisation_id != tx.buyer_org_id:
        fail(
            "FORBIDDEN",
            "Only the receiver may record receipt and downstream closure.",
            status=403,
        )
    if (
        target in ["IN_TRANSIT", "ARRIVED_PENDING_RECEIPT", "PICKUP_FAILED"]
        and user.organisation_id != t.organisation_id
    ):
        fail(
            "FORBIDDEN",
            "The assigned transporter must record this physical milestone.",
            status=403,
        )
    if target not in ["EXCEPTION_HOLD", "CANCELLED"]:
        ordinary(asset)
    if target == "CLOSED":
        check = closure_check(db, s)
        if not check["can_close"]:
            fail(
                "CLOSURE_BLOCKED",
                " ".join(check["reasons"]),
                next_action="Resolve pending inspection, settlement, disposition and exceptions.",
            )
        asset.state = "CLOSED"
        for r in db.scalars(
            select(m.CapacityReservation).where(
                m.CapacityReservation.transaction_id == tx.id,
                m.CapacityReservation.status == "COMMITTED",
            )
        ).all():
            r.status = "RELEASED"
        tx.status = "CLOSED"
        tx.logistics_status = "CLOSED"
    elif target == "CANCELLED":
        if not body.evidence or not body.notes:
            fail(
                "FIELD_REQUIRED",
                "Cancellation requires agreed-term rationale and evidence.",
            )
        approvals = dict(s.data.get("cancellation_confirmations", {}))
        approvals[user.organisation_id] = {
            "actor_id": user.id,
            "evidence": body.evidence,
            "reason": body.notes,
        }
        s.data = {**s.data, "cancellation_confirmations": approvals}
        if not {tx.seller_org_id, tx.buyer_org_id}.issubset(approvals):
            audit(
                db,
                user,
                "shipment",
                s,
                "CANCELLATION_CONFIRMATION",
                confirmations=approvals,
            )
            return {"shipment": dump(s), "pending_confirmation": True}
        for r in db.scalars(
            select(m.CapacityReservation).where(
                m.CapacityReservation.transaction_id == tx.id,
                m.CapacityReservation.status.in_(["HELD", "COMMITTED"]),
            )
        ).all():
            r.status = "RELEASED"
        tx.status = "CANCELLED"
        tx.logistics_status = "CANCELLED"
        asset.state = "CANCELLED"
    elif target == "PICKUP_SCHEDULED":
        membership = db.scalar(
            select(m.ConsolidationMember).where(
                m.ConsolidationMember.shipment_id == s.id
            )
        )
        if (
            membership
            and get(db, m.Consolidation, membership.consolidation_id).status
            != "APPROVED"
        ):
            fail(
                "TERMS_NOT_CONFIRMED",
                "All affected parties must approve the consolidation manifest before scheduling pickup.",
            )
        if user.organisation_id not in [tx.seller_org_id, t.organisation_id]:
            fail(
                "FORBIDDEN",
                "Originator or assigned transporter schedules pickup.",
                status=403,
            )
    elif target == "PICKED_UP":
        if user.organisation_id not in [asset.current_holder_org_id, t.organisation_id]:
            fail(
                "FORBIDDEN",
                "Current physical custodian and transporter must confirm handover.",
                status=403,
            )
        if not body.physical or not body.evidence:
            fail(
                "CUSTODY_EVIDENCE_MISSING",
                "Physical handover confirmation and evidence are required.",
            )
        if not body.condition_matches:
            s.data = {**s.data, "resume_state": before}
            s.state = "EXCEPTION_HOLD"
            asset.state = "HOLD"
            exception(
                db,
                "shipment",
                s.id,
                "CONDITION_MISMATCH",
                "org-review",
                "Obtain qualified review of pickup condition discrepancy.",
                "HIGH",
                evidence=body.evidence,
            )
            audit(
                db,
                user,
                "shipment",
                s,
                "PICKUP_CONDITION_MISMATCH",
                evidence=body.evidence,
            )
            return {"shipment": dump(s), "held": True}
        confirmations = dict(s.data.get("handover_confirmations", {}))
        confirmations[user.organisation_id] = {
            "actor_id": user.id,
            "evidence": body.evidence,
            "time": m.now(),
        }
        s.data = {**s.data, "handover_confirmations": confirmations}
        if not {asset.current_holder_org_id, t.organisation_id}.issubset(confirmations):
            audit(
                db,
                user,
                "shipment",
                s,
                "HANDOVER_CONFIRMATION",
                confirmations=confirmations,
            )
            return {"shipment": dump(s), "pending_confirmation": True}
        custody(
            db,
            user,
            s,
            asset,
            t.organisation_id,
            "PICKUP",
            body.evidence,
            confirmations=confirmations,
        )
        asset.state = "IN_SHIPMENT"
    elif target == "ARRIVED_PENDING_RECEIPT":
        route = get(db, m.RoutePlan, s.route_id)
        if route.hub_id and s.data.get("hub_stage") != "DISPATCHED":
            fail(
                "CUSTODY_EVIDENCE_MISSING",
                "Hub inbound and outbound handovers must be complete before destination arrival.",
            )
        asset.data = {
            **asset.data,
            "physical_location": get(db, m.Facility, tx.facility_id).name,
        }
    elif target in ["RECEIVED", "RECEIPT_DISPUTED"]:
        if not body.physical or not body.evidence:
            fail(
                "CUSTODY_EVIDENCE_MISSING",
                "Physical receipt confirmation and evidence are required.",
            )
        item = db.scalar(
            select(m.ShipmentItem).where(m.ShipmentItem.shipment_id == s.id)
        )
        accepted = (
            body.accepted_quantity
            if body.accepted_quantity is not None
            else (
                asset.quantity
                if body.receipt in ["ACCEPTED", "RECEIVED_PENDING_INSPECTION"]
                else 0
            )
        )
        if accepted > asset.quantity:
            fail(
                "VALIDATION_ERROR",
                "Accepted quantity exceeds shipment quantity.",
                "accepted_quantity",
            )
        disputed = (
            not body.condition_matches
            or body.receipt in ["PARTIALLY_ACCEPTED", "REJECTED"]
            or accepted != asset.quantity
            or target == "RECEIPT_DISPUTED"
        )
        item.receipt = "DISPUTED" if disputed else "ACCEPTED"
        if accepted and (not disputed or body.receipt == "PARTIALLY_ACCEPTED"):
            if accepted == asset.quantity:
                previously_accepted = (
                    item.data.get("accepted_quantity", 0)
                    if item.receipt == "DISPUTED" or asset.data.get("custody_segments")
                    else 0
                )
                custody(
                    db,
                    user,
                    s,
                    asset,
                    tx.buyer_org_id,
                    "RECEIPT",
                    body.evidence,
                    quantity=asset.quantity - previously_accepted,
                    total_accepted_quantity=asset.quantity,
                )
                asset.data = {
                    **asset.data,
                    "custody_segments": [
                        {"holder": tx.buyer_org_id, "quantity": asset.quantity}
                    ],
                }
            else:
                # Quantity segments preserve mixed physical custody without pretending the whole record moved.
                db.add(
                    m.CustodyEvent(
                        shipment_id=s.id,
                        asset_id=asset.id,
                        actor_id=user.id,
                        previous_holder=asset.current_holder_org_id,
                        new_holder=tx.buyer_org_id,
                        event_type="PARTIAL_RECEIPT",
                        data={
                            "evidence": body.evidence,
                            "quantity": accepted,
                            "remaining_quantity": asset.quantity - accepted,
                        },
                    )
                )
                asset.data = {
                    **asset.data,
                    "custody_segments": [
                        {"holder": tx.buyer_org_id, "quantity": accepted},
                        {
                            "holder": asset.current_holder_org_id,
                            "quantity": asset.quantity - accepted,
                        },
                    ],
                }
        item.data = {
            **item.data,
            "accepted_quantity": accepted,
            "receipt_evidence": body.evidence,
            "receipt_outcome": body.receipt,
        }
        if disputed:
            target = "RECEIPT_DISPUTED"
            asset.state = "DISPUTED"
            exception(
                db,
                "shipment",
                s.id,
                "RECEIPT_DISPUTE",
                "org-review",
                "Review per-item discrepancy, agree acceptance or return under existing terms.",
                "HIGH",
                evidence=body.evidence,
                accepted_quantity=accepted,
            )
        else:
            asset.state = "DISPOSITION_PENDING"
            s.data = {
                **s.data,
                "receipt_evidence": body.evidence,
                "receipt_outcome": body.receipt,
            }
            exception(
                db,
                "battery",
                asset.id,
                "DISPOSITION_MISSING",
                tx.buyer_org_id,
                "Record evidenced final disposition after receiving inspection.",
                evidence=body.evidence,
            )
    elif target == "PICKUP_FAILED":
        if not body.notes:
            fail("FIELD_REQUIRED", "Record a failed pickup reason.")
        exception(
            db,
            "shipment",
            s.id,
            "PICKUP_FAILED",
            tx.seller_org_id,
            "Resolve pickup failure and reschedule or cancel under terms.",
            evidence=body.notes,
        )
    elif target == "EXCEPTION_HOLD":
        if not body.evidence:
            fail("FIELD_REQUIRED", "Hold needs incident evidence.")
        s.data = {**s.data, "resume_state": before}
        asset.state = "HOLD"
        exception(
            db,
            "shipment",
            s.id,
            "SAFETY_FLAG",
            "org-review",
            "Obtain qualified instructions; do not reroute automatically.",
            "HIGH",
            evidence=body.evidence,
        )
    s.state = target
    tx.logistics_status = target
    audit(
        db,
        user,
        "shipment",
        s,
        "STATE_TRANSITION",
        before=before,
        after=target,
        evidence=body.evidence,
        notes=body.notes,
        physical=body.physical,
    )
    return {"shipment": dump(s), "pending_confirmation": False}


def hub_event(db, user, s, body):
    from ..auth import role

    role(user, "HUB", "TRANSPORTER")
    tx, asset, t = context(db, s)
    route = get(db, m.RoutePlan, s.route_id)
    if not route.hub_id or s.state != "IN_TRANSIT":
        fail(
            "STATE_TRANSITION_INVALID", "Hub handover requires an in-transit hub route."
        )
    hub = get(db, m.Facility, route.hub_id)
    if user.organisation_id not in [hub.organisation_id, t.organisation_id]:
        fail("FORBIDDEN", "Hub and assigned transporter must confirm.", status=403)
    ordinary(asset)
    if not body.physical:
        fail("CUSTODY_EVIDENCE_MISSING", "Physical hub handover must be confirmed.")
    expected = "AWAITING_INBOUND" if body.event == "HUB_RECEIVED" else "RECEIVED"
    if s.data.get("hub_stage") != expected:
        fail("STATE_TRANSITION_INVALID", "Hub handover is duplicate or out of order.")
    confirmations = dict(s.data.get(body.event, {}))
    confirmations[user.organisation_id] = {
        "actor_id": user.id,
        "evidence": body.evidence,
        "time": m.now(),
    }
    s.data = {**s.data, body.event: confirmations}
    if {hub.organisation_id, t.organisation_id}.issubset(confirmations):
        new = hub.organisation_id if body.event == "HUB_RECEIVED" else t.organisation_id
        custody(
            db,
            user,
            s,
            asset,
            new,
            body.event,
            body.evidence,
            confirmations=confirmations,
        )
        s.data = {
            **s.data,
            "hub_stage": "RECEIVED" if body.event == "HUB_RECEIVED" else "DISPATCHED",
        }
        asset.data = {
            **asset.data,
            "physical_location": hub.name
            if body.event == "HUB_RECEIVED"
            else "Outbound transit from " + hub.name,
        }
    audit(db, user, "shipment", s, body.event, confirmations=confirmations)
    return dump(s)
