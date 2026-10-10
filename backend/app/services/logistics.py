from sqlalchemy import select
from .. import models as m
from ..common import get, fail, expired, audit, exception, future, dump
from ..auth import party
from ..config import HOLD_MINUTES
from .commercial import current_terms
from .matching import validate_plan, transporter_check, facility_check, available


def check_quote(db, tx, quote):
    if tx.status != "AGREED_PENDING_LOGISTICS":
        fail(
            "TERMS_NOT_CONFIRMED", "Both parties must confirm current commercial terms."
        )
    if quote.transaction_id != tx.id or quote.terms_version != tx.terms_version:
        fail(
            "QUOTE_SCOPE_CHANGED",
            "Quote does not cover current terms; transporter must reissue.",
        )
    if quote.status not in ["SUBMITTED", "ACCEPTED"]:
        fail("QUOTE_INCOMPLETE", "Only a submitted or accepted quote is usable.")
    if expired(quote.expires_at):
        fail("QUOTE_EXPIRED", "Quote has expired; request a new quote.")
    if (
        quote.total_paise is None
        or quote.data.get("exclusions", "None").strip().lower() != "none"
    ):
        fail(
            "QUOTE_INCOMPLETE",
            "Quote needs complete all-inclusive scope and known total.",
        )
    route = get(db, m.RoutePlan, quote.route_id)
    asset = validate_plan(db, tx, route, tx.id)
    if quote.data.get("scope") != route.data["scope"]:
        fail("QUOTE_SCOPE_CHANGED", "Quote scope is stale.")
    t = get(db, m.TransporterProfile, quote.transporter_id)
    reasons = transporter_check(db, asset, t, route.data["points"], tx.id)
    if reasons:
        fail(reasons[0]["code"], reasons[0]["message"])
    terms = current_terms(db, tx)
    if set(terms.confirmations) != {tx.seller_org_id, tx.buyer_org_id}:
        fail("TERMS_NOT_CONFIRMED", "Current terms lack both confirmations.")
    if quote.total_paise > terms.budget_paise:
        fail(
            "QUOTE_OVER_BUDGET",
            f"Quote exceeds cap by {(quote.total_paise - terms.budget_paise) / 100:.2f} INR for payer {terms.payer_org_id}.",
            next_action="Seek another quote or have payer propose a cap amendment; both parties must confirm.",
        )
    if route.hub_id and not route.data.get("hub_approved_by"):
        fail(
            "HUB_APPROVAL_REQUIRED",
            "Hub operator must explicitly approve the dwell and onward plan.",
        )
    return route, asset, t


def accept_quote(db, user, quote):
    tx = get(db, m.SaleTransaction, quote.transaction_id)
    party(user, tx)
    terms = current_terms(db, tx)
    if user.organisation_id != terms.payer_org_id:
        fail(
            "FORBIDDEN",
            "Only the named logistics payer may accept this quote.",
            status=403,
        )
    # Persist recoverable overrun case even though the commercial action is rejected.
    if quote.total_paise is not None and quote.total_paise > terms.budget_paise:
        exception(
            db,
            "transaction",
            tx.id,
            "QUOTE_OVER_BUDGET",
            terms.payer_org_id,
            "Seek another quote, reconsider route/window, or propose a cap amendment. Both parties must approve.",
            "MEDIUM",
            quote_id=quote.id,
            overrun_paise=quote.total_paise - terms.budget_paise,
            payer_org_id=terms.payer_org_id,
        )
        db.commit()
    route, asset, t = check_quote(db, tx, quote)
    other = db.scalar(
        select(m.TransportQuote).where(
            m.TransportQuote.transaction_id == tx.id,
            m.TransportQuote.status == "ACCEPTED",
            m.TransportQuote.id != quote.id,
        )
    )
    if other:
        fail(
            "DUPLICATE_ACTION",
            "A quote is already accepted; release it before selecting another.",
        )
    quote.status = "ACCEPTED"
    tx.logistics_status = "QUOTE_ACCEPTED"
    audit(
        db,
        user,
        "transaction",
        tx,
        "ACCEPT_QUOTE",
        quote_id=quote.id,
        terms_version=tx.terms_version,
        payer=terms.payer_org_id,
    )
    return quote


def reserve(db, user, tx, route_id):
    party(user, tx)
    if db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == tx.id)):
        fail("DUPLICATE_ACTION", "A shipment already exists for this transaction.")
    quote = db.scalar(
        select(m.TransportQuote).where(
            m.TransportQuote.transaction_id == tx.id,
            m.TransportQuote.route_id == route_id,
            m.TransportQuote.status == "ACCEPTED",
        )
    )
    if not quote:
        fail("QUOTE_INCOMPLETE", "Accept a valid quote before capacity reservation.")
    route, asset, t = check_quote(db, tx, quote)
    resources = []
    for fid in [tx.facility_id] + ([route.hub_id] if route.hub_id else []):
        c = facility_check(db, asset, get(db, m.Facility, fid), tx.pathway, tx.id)
        cap = get(db, m.FacilityCapability, c["capability_id"])
        resources.append(("CAPABILITY", cap.id, min(cap.capacity_kg, cap.available_kg)))
    resources.append(("TRANSPORTER", t.id, t.capacity_kg))
    rows = db.scalars(
        select(m.CapacityReservation).where(
            m.CapacityReservation.transaction_id == tx.id
        )
    ).all()
    for r in rows:
        if r.status == "HELD" and expired(r.expires_at):
            r.status = "EXPIRED"
    live = [
        r
        for r in rows
        if r.status in ["HELD", "COMMITTED"]
        and (r.status == "COMMITTED" or not expired(r.expires_at))
    ]
    if live:
        if all(r.data.get("route_id") == route_id for r in live):
            return {"reservations": [dump(r) for r in live], "status": "HELD"}
        fail(
            "DUPLICATE_ACTION",
            "Active allocation exists for another route; release before replanning.",
        )
    start = asset.data["window_start"]
    end = asset.data["window_end"]
    for kind, id, capacity in resources:
        if available(db, kind, id, capacity, start, end) < asset.mass_kg:
            fail("CAPACITY_CONFLICT", "Capacity changed before reservation; replan.")
    reservations = []
    for kind, id, _ in resources:
        r = m.CapacityReservation(
            transaction_id=tx.id,
            resource_type=kind,
            resource_id=id,
            mass_kg=asset.mass_kg,
            starts_at=start,
            ends_at=end,
            expires_at=future(minutes=HOLD_MINUTES),
            data={
                "route_id": route_id,
                "quote_id": quote.id,
                "terms_version": tx.terms_version,
            },
        )
        db.add(r)
        reservations.append(r)
    db.flush()
    tx.logistics_status = "CAPACITY_HELD"
    audit(
        db,
        user,
        "transaction",
        tx,
        "RESERVE_CAPACITY",
        reservation_ids=[r.id for r in reservations],
    )
    return {"reservations": [dump(r) for r in reservations], "status": "HELD"}


def book(db, user, tx):
    party(user, tx)
    existing = db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == tx.id))
    if existing:
        return existing
    quote = db.scalar(
        select(m.TransportQuote).where(
            m.TransportQuote.transaction_id == tx.id,
            m.TransportQuote.status == "ACCEPTED",
        )
    )
    if not quote:
        fail(
            "QUOTE_INCOMPLETE",
            "No accepted transport quote. Shipment remains unbooked.",
        )
    route, asset, t = check_quote(db, tx, quote)
    rows = db.scalars(
        select(m.CapacityReservation).where(
            m.CapacityReservation.transaction_id == tx.id,
            m.CapacityReservation.status == "HELD",
        )
    ).all()
    needed = 3 if route.hub_id else 2
    if len(rows) != needed or any(
        expired(r.expires_at)
        or r.data.get("route_id") != route.id
        or r.data.get("terms_version") != tx.terms_version
        for r in rows
    ):
        fail("CAPACITY_CONFLICT", "All route resources need unexpired capacity holds.")
    active_items = db.scalars(
        select(m.ShipmentItem).where(m.ShipmentItem.asset_id == asset.id)
    ).all()
    if any(
        get(db, m.Shipment, i.shipment_id).state not in ["CLOSED", "CANCELLED"]
        for i in active_items
    ):
        fail(
            "DUPLICATE_ACTION", "Asset is already allocated to another active shipment."
        )
    for r in rows:
        r.status = "COMMITTED"
    shipment = m.Shipment(
        transaction_id=tx.id,
        route_id=route.id,
        quote_id=quote.id,
        data={
            "synthetic": True,
            "handover_confirmations": {},
            "hub_stage": "AWAITING_INBOUND" if route.hub_id else "DIRECT",
            "terms_version": tx.terms_version,
        },
    )
    db.add(shipment)
    db.flush()
    db.add(
        m.ShipmentItem(
            shipment_id=shipment.id,
            asset_id=asset.id,
            quantity=asset.quantity,
            mass_kg=asset.mass_kg,
            data={"handover_snapshot": dump(asset)},
        )
    )
    tx.logistics_status = "BOOKED"
    audit(
        db,
        user,
        "shipment",
        shipment,
        "BOOK",
        reservations=[r.id for r in rows],
        quote_id=quote.id,
    )
    return shipment


def release(db, user, tx):
    party(user, tx)
    if db.scalar(
        select(m.Shipment).where(
            m.Shipment.transaction_id == tx.id, m.Shipment.state.notin_(["CANCELLED"])
        )
    ):
        fail(
            "STATE_TRANSITION_INVALID",
            "Cancel a booked shipment before releasing capacity.",
        )
    for r in db.scalars(
        select(m.CapacityReservation).where(
            m.CapacityReservation.transaction_id == tx.id,
            m.CapacityReservation.status.in_(["HELD", "COMMITTED"]),
        )
    ).all():
        r.status = "RELEASED"
    for q in db.scalars(
        select(m.TransportQuote).where(
            m.TransportQuote.transaction_id == tx.id,
            m.TransportQuote.status == "ACCEPTED",
        )
    ).all():
        q.status = "RELEASED"
    tx.logistics_status = "PENDING"
    audit(db, user, "transaction", tx, "RELEASE_ALLOCATION")
    return tx
