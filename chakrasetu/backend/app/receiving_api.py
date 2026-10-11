from .auth import has_role
from fastapi import APIRouter, Depends
from sqlalchemy import select
from . import models as m
from .common import get, dump, fail, audit, exception
from .auth import current_user, party, role
from .db import get_db
from .schemas import InspectionIn, AmendmentIn, SettlementIn, DispositionIn
from .services.shipments import context
from .services.commercial import current_terms, amend

router = APIRouter()


@router.post("/shipments/{id}/inspection")
def inspection(
    id: str,
    body: InspectionIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "BUYER")
    s = get(db, m.Shipment, id)
    tx, asset, _ = context(db, s)
    if user.organisation_id != tx.buyer_org_id:
        fail("FORBIDDEN", "Receiving organisation must record inspection.", status=403)
    if s.state not in ["RECEIVED", "DISPOSITION_PENDING", "RECEIPT_DISPUTED"]:
        fail("STATE_TRANSITION_INVALID", "Inspection requires physical receipt.")
    if body.outcome == "ACCEPT_AS_AGREED":
        if s.state == "RECEIPT_DISPUTED":
            fail(
                "CONDITION_MISMATCH",
                "Resolve receipt dispute and record complete receipt first.",
            )
        s.data = {**s.data, "inspection_accepted": True}
        sett = db.scalar(
            select(m.SettlementRecord).where(m.SettlementRecord.transaction_id == tx.id)
        )
        sett.status = "DUE"
    elif body.outcome == "REVISE_PRICE":
        if body.price_paise is None:
            fail(
                "FIELD_REQUIRED",
                "Price revision needs a proposed amount.",
                "price_paise",
            )
        terms = current_terms(db, tx)
        amend(
            db,
            user,
            tx,
            AmendmentIn(
                budget_paise=terms.budget_paise,
                price_paise=body.price_paise,
                reason=body.notes,
                evidence=body.evidence,
            ),
        )
        s.data = {**s.data, "inspection_accepted": False}
    elif body.outcome == "POSSIBLE_HAZARD":
        s.data = {**s.data, "resume_state": s.state}
        s.state = "EXCEPTION_HOLD"
        asset.state = "HOLD"
        asset.data = {
            **asset.data,
            "handling_clearance": None,
            "flags": {**asset.data.get("flags", {}), "unknown_history": "YES"},
        }
        exception(
            db,
            "shipment",
            id,
            "SAFETY_FLAG",
            "org-review",
            "Request qualified review and documented handling instructions.",
            "HIGH",
            evidence=body.evidence,
        )
    else:
        s.data = {**s.data, "inspection_accepted": False}
        exception(
            db,
            "shipment",
            id,
            "CONDITION_MISMATCH",
            "org-review",
            "Agree further inspection or eligible pathway; retain original terms.",
            evidence=body.evidence,
            inspection=body.model_dump(),
        )
    s.data = {
        **s.data,
        "inspections": [
            *s.data.get("inspections", []),
            {**body.model_dump(), "actor_id": user.id, "timestamp": m.now()},
        ],
    }
    audit(db, user, "shipment", s, "INSPECTION", **body.model_dump())
    return dump(s)


@router.get("/transactions/{id}/settlement")
def settlement(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    tx = get(db, m.SaleTransaction, id)
    if not has_role(user, "REVIEWER"):
        party(user, tx)
    row = db.scalar(
        select(m.SettlementRecord).where(m.SettlementRecord.transaction_id == id)
    )
    return dump(row) if row else None


@router.post("/transactions/{id}/settlement")
def update_settlement(
    id: str,
    body: SettlementIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    tx = get(db, m.SaleTransaction, id)
    party(user, tx)
    row = db.scalar(
        select(m.SettlementRecord).where(m.SettlementRecord.transaction_id == id)
    )
    if not row:
        fail(
            "TERMS_NOT_CONFIRMED",
            "Settlement record is created after mutual agreement.",
        )
    allowed = {
        "NOT_DUE": {"DUE", "DISPUTED"},
        "DUE": {"PAYMENT_REPORTED", "DISPUTED", "OVERDUE"},
        "OVERDUE": {"PAYMENT_REPORTED", "DISPUTED"},
        "PAYMENT_REPORTED": {"SETTLED_CONFIRMED", "DISPUTED"},
        "DISPUTED": {"DUE"},
    }
    if body.status not in allowed.get(row.status, set()):
        fail(
            "STATE_TRANSITION_INVALID",
            f"Settlement {row.status} cannot become {body.status}.",
        )
    s = db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == id))
    if body.status in ["PAYMENT_REPORTED", "SETTLED_CONFIRMED"]:
        if (
            not s
            or not s.data.get("inspection_accepted")
            or tx.status != "AGREED_PENDING_LOGISTICS"
        ):
            fail(
                "CONDITION_MISMATCH",
                "Inspection acceptance and current confirmed terms are required.",
            )
        unresolved = [
            c
            for c in db.scalars(
                select(m.ExceptionCase).where(m.ExceptionCase.status != "CLOSED")
            ).all()
            if (c.object_type, c.object_id) in [("shipment", s.id), ("transaction", id)]
            and c.category
            in ["RECEIPT_DISPUTE", "PRICE_DISPUTE", "CONDITION_MISMATCH", "SAFETY_FLAG"]
        ]
        if unresolved:
            fail("CONDITION_MISMATCH", "Disputes block settlement progression.")
    if body.status == "PAYMENT_REPORTED" and user.organisation_id != row.payer_org_id:
        fail("FORBIDDEN", "Only payer can report payment.", status=403)
    if body.status == "SETTLED_CONFIRMED" and user.organisation_id != row.payee_org_id:
        fail("FORBIDDEN", "Only payee may confirm reported settlement.", status=403)
    before = row.status
    row.status = body.status
    row.data = {
        **row.data,
        "history": [
            *row.data.get("history", []),
            {
                "status": body.status,
                "reference": body.reference,
                "actor_id": user.id,
                "timestamp": m.now(),
            },
        ],
        "notice": "Record only; ChakraSetu does not move money.",
    }
    audit(
        db,
        user,
        "transaction",
        tx,
        "SETTLEMENT_RECORD",
        before=before,
        after=body.status,
        reference=body.reference,
    )
    return dump(row)


@router.post("/batteries/{id}/disposition")
def disposition(
    id: str,
    body: DispositionIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "BUYER")
    asset = get(db, m.BatteryAsset, id)
    tx = db.scalar(
        select(m.SaleTransaction)
        .where(m.SaleTransaction.asset_id == id)
        .order_by(m.SaleTransaction.created_at.desc())
    )
    if not tx or user.organisation_id != tx.buyer_org_id:
        fail(
            "FORBIDDEN",
            "Only receiving organisation may attest disposition.",
            status=403,
        )
    s = db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == tx.id))
    if (
        not s
        or s.state not in ["RECEIVED", "DISPOSITION_PENDING"]
        or not s.data.get("inspection_accepted")
    ):
        fail(
            "STATE_TRANSITION_INVALID",
            "Disposition requires received and inspection-accepted assets.",
        )
    compatible = {
        "REPAIR_REFURBISHMENT": {
            "REFURBISHMENT_COMPLETED",
            "TRANSFERRED_TO_ELIGIBLE_OPERATOR",
            "PENDING_FURTHER_ASSESSMENT",
            "SENT_FOR_RECYCLING",
        },
        "SECOND_LIFE_ASSESSMENT": {
            "SECOND_LIFE_ASSESSMENT_COMPLETED",
            "PENDING_FURTHER_ASSESSMENT",
            "SENT_FOR_RECYCLING",
        },
        "QUALIFIED_REVIEW": {
            "TRANSFERRED_TO_ELIGIBLE_OPERATOR",
            "PENDING_FURTHER_ASSESSMENT",
        },
        "RECYCLING": {
            "RECYCLING_COMPLETED",
            "SENT_FOR_RECYCLING",
            "PENDING_FURTHER_ASSESSMENT",
        },
    }
    if body.outcome not in compatible.get(tx.pathway, set()):
        fail(
            "PATHWAY_NOT_SUPPORTED",
            "Outcome does not match agreed pathway; new transfer requires another eligible workflow.",
        )
    row = m.DispositionRecord(
        asset_id=id,
        facility_id=tx.facility_id,
        actor_id=user.id,
        outcome=body.outcome,
        data={
            "evidence": body.evidence,
            "self_reported": True,
            "record_only": True,
            "synthetic": bool(asset.data.get("synthetic", False)),
        },
    )
    db.add(row)
    db.flush()
    final = body.outcome in [
        "REFURBISHMENT_COMPLETED",
        "SECOND_LIFE_ASSESSMENT_COMPLETED",
        "RECYCLING_COMPLETED",
        "TRANSFERRED_TO_ELIGIBLE_OPERATOR",
    ]
    asset.state = "DISPOSITION_RECORDED" if final else "DISPOSITION_PENDING"
    if final:
        for c in db.scalars(
            select(m.ExceptionCase).where(
                m.ExceptionCase.object_type == "battery",
                m.ExceptionCase.object_id == id,
                m.ExceptionCase.category == "DISPOSITION_MISSING",
                m.ExceptionCase.status != "CLOSED",
            )
        ).all():
            c.status = "CLOSED"
            c.resolution = "Final disposition evidence recorded"
            c.data = {
                **c.data,
                "resolution_evidence": body.evidence,
                "disposition_id": row.id,
                "closed_by": user.id,
                "closed_at": m.now(),
            }
            audit(
                db,
                user,
                "exception",
                c,
                "DISPOSITION_FOLLOWUP_RESOLVED",
                disposition_id=row.id,
            )
    audit(
        db,
        user,
        "battery",
        asset,
        "DISPOSITION",
        outcome=body.outcome,
        evidence=body.evidence,
    )
    return dump(row)
