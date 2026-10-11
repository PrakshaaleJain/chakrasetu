from sqlalchemy import select
from .. import models as m
from ..common import get, fail, expired, audit, dump
from ..auth import seller, party, role
from .matching import ordinary, facility_check, handling_scope


def select_offer(db, user, offer):
    listing = get(db, m.Listing, offer.listing_id)
    asset = get(db, m.BatteryAsset, listing.asset_id)
    seller(user, asset)
    existing = db.scalar(
        select(m.SaleTransaction).where(m.SaleTransaction.offer_id == offer.id)
    )
    if existing:
        return existing
    ordinary(asset)
    if listing.status != "OPEN" or asset.state != "LISTED":
        fail("DUPLICATE_ACTION", "Asset already allocated or listing inactive.")
    if expired(listing.expires_at) or expired(offer.expires_at):
        fail("QUOTE_EXPIRED", "Listing or offer has expired.")
    if offer.data["inspection_condition"] == "INDICATIVE":
        fail("OFFER_NON_BINDING", "An indicative offer cannot form an agreement.")
    check = facility_check(
        db, asset, get(db, m.Facility, offer.facility_id), offer.pathway
    )
    if not check["eligible"]:
        fail(check["reasons"][0]["code"], check["reasons"][0]["message"])
    tx = m.SaleTransaction(
        offer_id=offer.id,
        asset_id=asset.id,
        seller_org_id=listing.seller_org_id,
        buyer_org_id=offer.buyer_org_id,
        facility_id=offer.facility_id,
        pathway=offer.pathway,
        data={
            "synthetic": bool(asset.data.get("synthetic", False)),
            "selected_by": user.id,
            "quote_round": 1,
        },
    )
    db.add(tx)
    db.flush()
    snapshot = {
        **offer.data,
        "currency": "INR",
        "basis": "PER_ASSET_RECORD",
        "asset_snapshot": dump(asset),
        "listing_terms": listing.data,
        "scope": handling_scope(asset),
    }
    terms = m.TermsVersion(
        transaction_id=tx.id,
        version=1,
        payer_org_id=offer.data["payer_org_id"],
        budget_paise=offer.data["budget_paise"],
        price_paise=offer.price_paise,
        data=snapshot,
    )
    db.add(terms)
    offer.status = "SELECTED"
    listing.status = "OFFER_SELECTED"
    asset.state = "OFFER_SELECTED"
    audit(db, user, "transaction", tx, "SELECT_OFFER", terms=snapshot)
    return tx


def current_terms(db, tx):
    return db.scalar(
        select(m.TermsVersion).where(
            m.TermsVersion.transaction_id == tx.id,
            m.TermsVersion.version == tx.terms_version,
        )
    )


def confirm(db, user, tx, version):
    party(user, tx)
    if tx.status in ["CLOSED", "CANCELLED"]:
        fail("STATE_TRANSITION_INVALID", "Terminal transactions cannot be reopened.")
    terms = current_terms(db, tx)
    if version != tx.terms_version:
        fail(
            "TERMS_VERSION_MISMATCH",
            "Confirm the current terms version; previous versions remain in history.",
        )
    if terms.payer_org_id not in [tx.seller_org_id, tx.buyer_org_id]:
        fail(
            "COST_ALLOCATION_UNDEFINED",
            "Logistics payer must be a party to these terms.",
        )
    if user.organisation_id not in terms.confirmations:
        terms.confirmations = [*terms.confirmations, user.organisation_id]
    if set(terms.confirmations) == {tx.seller_org_id, tx.buyer_org_id}:
        tx.status = "AGREED_PENDING_LOGISTICS"
        if not db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == tx.id)):
            get(db, m.BatteryAsset, tx.asset_id).state = "AGREED"
        settlement = db.scalar(
            select(m.SettlementRecord).where(m.SettlementRecord.transaction_id == tx.id)
        )
        if not settlement:
            db.add(
                m.SettlementRecord(
                    transaction_id=tx.id,
                    payer_org_id=tx.buyer_org_id,
                    payee_org_id=tx.seller_org_id,
                    amount_paise=terms.price_paise,
                    data={
                        "currency": "INR",
                        "record_only": True,
                        "cost_breakdown": terms.data.get("costs"),
                        "logistics_payer": terms.payer_org_id,
                        "logistics_cap_paise": terms.budget_paise,
                    },
                )
            )
        else:
            settlement.amount_paise = terms.price_paise
            settlement.data = {
                **settlement.data,
                "logistics_cap_paise": terms.budget_paise,
            }
    audit(
        db,
        user,
        "transaction",
        tx,
        "CONFIRM_TERMS",
        version=version,
        confirmations=terms.confirmations,
    )
    return tx


def amend(db, user, tx, body):
    party(user, tx)
    if tx.status in ["CLOSED", "CANCELLED"]:
        fail("STATE_TRANSITION_INVALID", "Terminal terms cannot be amended.")
    old = current_terms(db, tx)
    if (
        body.budget_paise != old.budget_paise
        and user.organisation_id != old.payer_org_id
    ):
        fail(
            "FORBIDDEN",
            "Only the responsible payer can propose a new logistics cap.",
            status=403,
        )
    if (
        body.price_paise is not None
        and body.price_paise != old.price_paise
        and not body.evidence
    ):
        fail("FIELD_REQUIRED", "Price revision requires inspection evidence.")
    if (
        db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == tx.id))
        and body.budget_paise != old.budget_paise
    ):
        fail(
            "STATE_TRANSITION_INVALID",
            "Booked transport amendments need a replacement quote; cancel before pickup or retain agreed cap.",
        )
    tx.terms_version += 1
    tx.status = "AWAITING_CONFIRMATION"
    terms = m.TermsVersion(
        transaction_id=tx.id,
        version=tx.terms_version,
        payer_org_id=old.payer_org_id,
        budget_paise=body.budget_paise,
        price_paise=body.price_paise
        if body.price_paise is not None
        else old.price_paise,
        data={
            **old.data,
            "amendment": body.model_dump(),
            "previous_version": old.version,
        },
    )
    db.add(terms)
    for q in db.scalars(
        select(m.TransportQuote).where(
            m.TransportQuote.transaction_id == tx.id,
            m.TransportQuote.status == "ACCEPTED",
        )
    ).all():
        q.status = "REVALIDATION_REQUIRED"
    for r in db.scalars(
        select(m.CapacityReservation).where(
            m.CapacityReservation.transaction_id == tx.id,
            m.CapacityReservation.status == "HELD",
        )
    ).all():
        r.status = "RELEASED"
    audit(
        db,
        user,
        "transaction",
        tx,
        "PROPOSE_AMENDMENT",
        previous=old.version,
        new=tx.terms_version,
        reason=body.reason,
        evidence=body.evidence,
    )
    return tx
