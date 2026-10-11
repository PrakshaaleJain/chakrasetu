from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from . import models as m
from .auth import current_user, role, party
from .common import get, dump, fail, audit, idem, expired, exception
from .db import get_db
from .schemas import QuoteIn, RouteSelect
from .services.matching import generate_routes, validate_plan, transporter_check
from .services.commercial import current_terms
from .services.logistics import accept_quote, reserve, book, release
from .schemas import EntityResponse

router = APIRouter()


@router.post("/transactions/{id}/route-plans")
def plans(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    tx = get(db, m.SaleTransaction, id)
    party(user, tx)
    return generate_routes(db, tx, user)


@router.get("/transactions/{id}/route-plans")
def list_plans(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    tx = get(db, m.SaleTransaction, id)
    if not has_role(user, "TRANSPORTER", "HUB", "REVIEWER"):
        party(user, tx)
    return [
        dump(p)
        for p in db.scalars(
            select(m.RoutePlan)
            .where(m.RoutePlan.transaction_id == id)
            .order_by(m.RoutePlan.created_at.desc())
        ).all()
    ]


@router.post("/route-plans/{id}/hub-approval")
def approve_hub(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    role(user, "HUB")
    r = get(db, m.RoutePlan, id)
    if (
        not r.hub_id
        or get(db, m.Facility, r.hub_id).organisation_id != user.organisation_id
    ):
        fail("FORBIDDEN", "Only the selected hub can approve this plan.", status=403)
    validate_plan(db, get(db, m.SaleTransaction, r.transaction_id), r, r.transaction_id)
    r.data = {
        **r.data,
        "hub_approved_by": user.id,
        "hub_approved_at": m.now(),
        "inbound_outbound_scope": "Same quoted transporter executes both legs; per-asset handovers required.",
    }
    audit(db, user, "route", r, "HUB_APPROVE")
    return dump(r)


@router.post("/transactions/{id}/transport-quotes")
def quote(
    id: str,
    body: QuoteIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "TRANSPORTER")
    tx = get(db, m.SaleTransaction, id)
    route = get(db, m.RoutePlan, body.route_id)
    asset = validate_plan(db, tx, route, tx.id)
    if tx.status != "AGREED_PENDING_LOGISTICS":
        fail("TERMS_NOT_CONFIRMED", "Terms must be confirmed before quoting.")
    profile = db.scalar(
        select(m.TransporterProfile).where(
            m.TransporterProfile.organisation_id == user.organisation_id
        )
    )
    if not profile:
        fail("TRANSPORTER_SCOPE_MISMATCH", "No transporter profile.")
    reasons = transporter_check(db, asset, profile, route.data["points"], tx.id)
    if reasons:
        fail(reasons[0]["code"], reasons[0]["message"])
    if expired(body.expires_at.isoformat()):
        fail("QUOTE_EXPIRED", "Quote expiry must be in the future.")
    q = m.TransportQuote(
        transaction_id=id,
        route_id=route.id,
        transporter_id=profile.id,
        total_paise=body.total_paise,
        terms_version=tx.terms_version,
        expires_at=body.expires_at.isoformat(),
        status=body.status,
        data={
            **body.model_dump(mode="json"),
            "scope": route.data["scope"],
            "synthetic": get(db, m.Organisation, user.organisation_id).synthetic,
            "currency": "INR",
            "distance_source": "HAVERSINE_PROXY",
            "eta_source": "PROXY_NOT_COMMITMENT",
            "quote_round": tx.data.get("quote_round", 1),
            "hub_fee_included": bool(route.hub_id),
        },
    )
    db.add(q)
    db.flush()
    audit(
        db, user, "transaction", tx, "TRANSPORT_QUOTE", quote_id=q.id, status=q.status
    )
    return dump(q)


@router.get("/transactions/{id}/transport-quotes")
def quotes(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    tx = get(db, m.SaleTransaction, id)
    rows = db.scalars(
        select(m.TransportQuote).where(m.TransportQuote.transaction_id == id)
    ).all()
    commercial_party = user.organisation_id in [
        tx.seller_org_id,
        tx.buyer_org_id,
    ] and has_role(user, "ORIGINATOR", "BUYER")
    if not commercial_party and not has_role(user, "REVIEWER", "TRANSPORTER"):
        fail("FORBIDDEN", "Quote access is restricted.", status=403)
    if (
        has_role(user, "TRANSPORTER")
        and not commercial_party
        and not has_role(user, "REVIEWER")
    ):
        rows = [
            q
            for q in rows
            if get(db, m.TransporterProfile, q.transporter_id).organisation_id
            == user.organisation_id
        ]
    return [dump(q) for q in rows]


@router.post("/quotes/{id}/accept", response_model=EntityResponse)
def accept(
    id: str,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    return idem(
        db,
        user,
        idempotency_key,
        "accept-quote",
        {"id": id},
        lambda: accept_quote(db, user, get(db, m.TransportQuote, id)),
    )


@router.post("/transactions/{id}/reserve-capacity")
def reservation(
    id: str,
    body: RouteSelect,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    return idem(
        db,
        user,
        idempotency_key,
        "reserve-capacity",
        {"id": id, **body.model_dump()},
        lambda: reserve(db, user, get(db, m.SaleTransaction, id), body.route_id),
    )


@router.post("/transactions/{id}/shipments", response_model=EntityResponse)
def booking(
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
        "book",
        {"id": id},
        lambda: book(db, user, get(db, m.SaleTransaction, id)),
    )


@router.post("/transactions/{id}/release-capacity")
def released(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return dump(release(db, user, get(db, m.SaleTransaction, id)))


@router.post("/transactions/{id}/quote-round/close")
def close_round(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    tx = get(db, m.SaleTransaction, id)
    party(user, tx)
    if db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == id)):
        fail("STATE_TRANSITION_INVALID", "A shipment is already booked.")
    quotes = db.scalars(
        select(m.TransportQuote).where(
            m.TransportQuote.transaction_id == id, m.TransportQuote.status == "ACCEPTED"
        )
    ).all()
    if quotes:
        fail(
            "STATE_TRANSITION_INVALID",
            "An accepted quote exists; reserve and book or release it.",
        )
    tx.logistics_status = "NO_ACCEPTANCE"
    owner = current_terms(db, tx).payer_org_id
    case = exception(
        db,
        "transaction",
        id,
        "NO_TRANSPORTER",
        owner,
        "Reschedule, request another quote round, reconsider eligible hub, renegotiate cap, or cancel under accepted terms.",
        responses=[
            {"transporter_id": q.transporter_id, "status": q.status}
            for q in db.scalars(
                select(m.TransportQuote).where(m.TransportQuote.transaction_id == id)
            ).all()
        ],
        round=tx.data.get("quote_round", 1),
    )
    audit(db, user, "transaction", tx, "NO_TRANSPORT_ACCEPTANCE", exception_id=case.id)
    return {"transaction": dump(tx), "exception": dump(case), "shipment_booked": False}


@router.post("/transactions/{id}/quote-round/reopen")
def reopen(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    tx = get(db, m.SaleTransaction, id)
    party(user, tx)
    if tx.logistics_status != "NO_ACCEPTANCE":
        fail("STATE_TRANSITION_INVALID", "Close the unsuccessful quote round first.")
    tx.data = {**tx.data, "quote_round": tx.data.get("quote_round", 1) + 1}
    tx.logistics_status = "PENDING"
    audit(
        db, user, "transaction", tx, "REOPEN_QUOTE_ROUND", round=tx.data["quote_round"]
    )
    return dump(tx)


@router.get("/transactions/{id}/route-diagnostics")
def diagnostics(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    tx = get(db, m.SaleTransaction, id)
    if not has_role(user, "REVIEWER"):
        party(user, tx)
    row = db.scalar(
        select(m.AuditEvent)
        .where(
            m.AuditEvent.object_type == "transaction",
            m.AuditEvent.object_id == id,
            m.AuditEvent.action == "GENERATE_ROUTES",
        )
        .order_by(m.AuditEvent.created_at.desc())
    )
    return row.data if row else {"rejected": []}
