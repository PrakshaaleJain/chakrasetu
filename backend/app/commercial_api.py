from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from . import models as m
from .auth import current_user, seller, role, party, can_view_asset
from .common import get, dump, fail, expired, audit, idem
from .db import get_db
from .schemas import ListingIn, OfferIn, ConfirmIn, AmendmentIn
from .services.matching import ordinary, eligible_buyers, facility_check
from .services.commercial import select_offer, current_terms, confirm, amend
from .schemas import EntityResponse

router = APIRouter()


@router.post("/listings", response_model=EntityResponse)
def create(body: ListingIn, db=Depends(get_db), user=Depends(current_user)):
    asset = get(db, m.BatteryAsset, body.asset_id)
    seller(user, asset)
    ordinary(asset)
    if asset.state != "READY_FOR_LISTING":
        fail(
            "STATE_TRANSITION_INVALID", "Asset must be screened and ready for listing."
        )
    if body.mode == "FIXED_PRICE" and body.asking_paise is None:
        fail(
            "FIELD_REQUIRED",
            "Fixed-price listings need an asking price.",
            "asking_paise",
        )
    if expired(body.expires_at.isoformat()):
        fail("QUOTE_EXPIRED", "Choose a future listing expiry.")
    listing = m.Listing(
        asset_id=asset.id,
        seller_org_id=user.organisation_id,
        expires_at=body.expires_at.isoformat(),
        data={**body.model_dump(mode="json"), "currency": "INR", "synthetic": True},
    )
    db.add(listing)
    db.flush()
    asset.state = "LISTED"
    audit(db, user, "listing", listing, "CREATE")
    return dump(listing)


@router.get("/listings")
def listings(db=Depends(get_db), user=Depends(current_user)):
    results = []
    for l in db.scalars(select(m.Listing).order_by(m.Listing.created_at.desc())).all():
        asset = get(db, m.BatteryAsset, l.asset_id)
        own = user.organisation_id == l.seller_org_id or user.role == "REVIEWER"
        eligible = (
            [
                c
                for c in eligible_buyers(db, asset)
                if c["eligible"]
                and c["facility"]["organisation_id"] == user.organisation_id
            ]
            if user.role == "BUYER"
            else []
        )
        if own or eligible:
            results.append(
                {
                    **dump(l),
                    "asset": {
                        "internal_id": asset.internal_id,
                        "chemistry": asset.chemistry,
                        "form": asset.form,
                        "condition": asset.condition,
                        "mass_kg": asset.mass_kg,
                    },
                    "eligible_for_actor": eligible,
                }
            )
    return results


@router.get("/listings/{id}/eligible-buyers")
def buyers(id: str, db=Depends(get_db), user=Depends(current_user)):
    listing = get(db, m.Listing, id)
    asset = get(db, m.BatteryAsset, listing.asset_id)
    if user.organisation_id != listing.seller_org_id and user.role != "REVIEWER":
        fail(
            "FORBIDDEN",
            "Exclusions are visible to the seller and reviewer.",
            status=403,
        )
    return eligible_buyers(db, asset)


@router.post("/listings/{id}/offers", response_model=EntityResponse)
def offer(id: str, body: OfferIn, db=Depends(get_db), user=Depends(current_user)):
    role(user, "BUYER")
    listing = get(db, m.Listing, id)
    asset = get(db, m.BatteryAsset, listing.asset_id)
    ordinary(asset)
    facility = get(db, m.Facility, body.facility_id)
    if facility.organisation_id != user.organisation_id:
        fail("FORBIDDEN", "You can offer only for your facility.", status=403)
    if (
        listing.status != "OPEN"
        or expired(listing.expires_at)
        or expired(body.expires_at.isoformat())
    ):
        fail("QUOTE_EXPIRED", "Listing or offer is inactive/expired.")
    if body.payer_org_id not in [listing.seller_org_id, user.organisation_id]:
        fail("COST_ALLOCATION_UNDEFINED", "Name buyer or seller as logistics payer.")
    if any(value is not None and value < 0 for value in body.costs.values()):
        fail("VALIDATION_ERROR", "Cost components cannot be negative.")
    check = facility_check(db, asset, facility, body.pathway)
    if not check["eligible"]:
        fail(check["reasons"][0]["code"], check["reasons"][0]["message"])
    data = body.model_dump(mode="json")
    obj = m.Offer(
        listing_id=id,
        buyer_org_id=user.organisation_id,
        facility_id=facility.id,
        pathway=body.pathway,
        price_paise=body.price_paise,
        expires_at=body.expires_at.isoformat(),
        data={
            **data,
            "currency": "INR",
            "synthetic": True,
            "basis": "PER_ASSET_RECORD",
            "tax_treatment": "Included as declared",
            "net_estimate_status": "INCOMPLETE"
            if any(v is None for v in body.costs.values())
            else "COMPLETE",
        },
    )
    db.add(obj)
    db.flush()
    audit(db, user, "offer", obj, "SUBMIT")
    return dump(obj)


@router.get("/listings/{id}/offers")
def offers(id: str, db=Depends(get_db), user=Depends(current_user)):
    listing = get(db, m.Listing, id)
    rows = db.scalars(select(m.Offer).where(m.Offer.listing_id == id)).all()
    return [
        dump(o)
        for o in rows
        if user.organisation_id in [listing.seller_org_id, o.buyer_org_id]
        or user.role == "REVIEWER"
    ]


@router.post("/offers/{id}/accept", response_model=EntityResponse)
def accept(
    id: str,
    db=Depends(get_db),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    return idem(
        db,
        user,
        idempotency_key,
        "accept-offer",
        {"id": id},
        lambda: select_offer(db, user, get(db, m.Offer, id)),
    )


@router.get("/transactions")
def transactions(db=Depends(get_db), user=Depends(current_user)):
    out = []
    for tx in db.scalars(
        select(m.SaleTransaction).order_by(m.SaleTransaction.created_at.desc())
    ).all():
        visible = can_view_asset(db, user, get(db, m.BatteryAsset, tx.asset_id))
        if (
            not visible
            and user.role == "TRANSPORTER"
            and tx.status == "AGREED_PENDING_LOGISTICS"
        ):
            # Shared quote request subset excludes sale price/evidence/private identity.
            out.append(
                {
                    **dump(tx),
                    "data": {},
                    "terms": None,
                    "asset": {
                        "internal_id": get(db, m.BatteryAsset, tx.asset_id).internal_id
                    },
                }
            )
            continue
        if visible:
            asset = get(db, m.BatteryAsset, tx.asset_id)
            out.append(
                {
                    **dump(tx),
                    "terms": dump(current_terms(db, tx))
                    if user.role != "TRANSPORTER"
                    else None,
                    "asset": {
                        "internal_id": asset.internal_id,
                        "state": asset.state,
                        "current_holder_org_id": asset.current_holder_org_id,
                    },
                    "terms_history": [
                        dump(t)
                        for t in db.scalars(
                            select(m.TermsVersion)
                            .where(m.TermsVersion.transaction_id == tx.id)
                            .order_by(m.TermsVersion.version)
                        ).all()
                    ]
                    if user.role in ["BUYER", "ORIGINATOR", "REVIEWER"]
                    else [],
                }
            )
    return out


@router.post("/transactions/{id}/confirm", response_model=EntityResponse)
def confirmation(
    id: str, body: ConfirmIn, db=Depends(get_db), user=Depends(current_user)
):
    return dump(confirm(db, user, get(db, m.SaleTransaction, id), body.version))


@router.post("/transactions/{id}/amend", response_model=EntityResponse)
def amendment(
    id: str, body: AmendmentIn, db=Depends(get_db), user=Depends(current_user)
):
    return dump(amend(db, user, get(db, m.SaleTransaction, id), body))


from datetime import datetime
from pydantic import Field
from .schemas import Schema


class RescheduleIn(Schema):
    window_start: datetime
    window_end: datetime
    reason: str = Field(min_length=3)
    evidence: str = Field(min_length=1)


@router.post("/transactions/{id}/reschedule")
def reschedule(
    id: str, body: RescheduleIn, db=Depends(get_db), user=Depends(current_user)
):
    tx = get(db, m.SaleTransaction, id)
    party(user, tx)
    if db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == id)):
        fail(
            "STATE_TRANSITION_INVALID",
            "Booked appointments require cancellation/rebooking before physical pickup; in-transit schedules cannot be rewritten.",
        )
    if (
        not body.window_start.tzinfo
        or not body.window_end.tzinfo
        or body.window_end <= body.window_start
        or expired(body.window_end.isoformat())
    ):
        fail(
            "VALIDATION_ERROR",
            "Choose a future, ordered, timezone-aware service window.",
        )
    terms = current_terms(db, tx)
    amend(
        db,
        user,
        tx,
        AmendmentIn(
            budget_paise=terms.budget_paise, reason=body.reason, evidence=body.evidence
        ),
    )
    asset = get(db, m.BatteryAsset, tx.asset_id)
    before = dump(asset)
    from datetime import timezone

    asset.data = {
        **asset.data,
        "window_start": body.window_start.astimezone(timezone.utc).isoformat(),
        "window_end": body.window_end.astimezone(timezone.utc).isoformat(),
    }
    new = current_terms(db, tx)
    new.data = {
        **new.data,
        "asset_snapshot": dump(asset),
        "reschedule": body.model_dump(mode="json"),
    }
    tx.logistics_status = "PENDING"
    audit(
        db,
        user,
        "transaction",
        tx,
        "RESCHEDULE_PROPOSAL",
        before=before,
        new_window=body.model_dump(mode="json"),
    )
    return dump(tx)


class CancellationIn(Schema):
    reason: str = Field(min_length=3)
    evidence: str = Field(min_length=1)


@router.post("/transactions/{id}/cancel")
def cancel(
    id: str, body: CancellationIn, db=Depends(get_db), user=Depends(current_user)
):
    tx = get(db, m.SaleTransaction, id)
    party(user, tx)
    if db.scalar(select(m.Shipment).where(m.Shipment.transaction_id == id)):
        fail(
            "STATE_TRANSITION_INVALID",
            "Use the shipment cancellation workflow after booking.",
        )
    if tx.status == "CANCELLED":
        return dump(tx)
    confirmations = dict(tx.data.get("cancellation_confirmations", {}))
    confirmations[user.organisation_id] = {
        **body.model_dump(),
        "actor_id": user.id,
        "timestamp": m.now(),
    }
    tx.data = {**tx.data, "cancellation_confirmations": confirmations}
    if {tx.seller_org_id, tx.buyer_org_id}.issubset(confirmations):
        for r in db.scalars(
            select(m.CapacityReservation).where(
                m.CapacityReservation.transaction_id == id,
                m.CapacityReservation.status == "HELD",
            )
        ).all():
            r.status = "RELEASED"
        tx.status = "CANCELLED"
        tx.logistics_status = "CANCELLED"
        get(db, m.BatteryAsset, tx.asset_id).state = "CANCELLED"
    audit(
        db,
        user,
        "transaction",
        tx,
        "CANCELLATION_CONFIRMATION",
        confirmations=confirmations,
    )
    return dump(tx)


class ListingManageIn(Schema):
    action: str = Field(pattern="^(WITHDRAW|RENEW)$")
    reason: str = Field(min_length=3)
    expires_at: datetime | None = None


@router.post("/listings/{id}/manage")
def manage_listing(
    id: str, body: ListingManageIn, db=Depends(get_db), user=Depends(current_user)
):
    l = get(db, m.Listing, id)
    asset = get(db, m.BatteryAsset, l.asset_id)
    seller(user, asset)
    if l.status == "OFFER_SELECTED":
        fail(
            "STATE_TRANSITION_INVALID",
            "A selected offer must be handled through its transaction.",
        )
    if body.action == "WITHDRAW":
        l.status = "WITHDRAWN"
        asset.state = "WITHDRAWN"
    else:
        if not body.expires_at or expired(body.expires_at.isoformat()):
            fail("FIELD_REQUIRED", "Renewal requires a future expiry.")
        if l.status == "WITHDRAWN":
            fail(
                "STATE_TRANSITION_INVALID",
                "Withdrawn records are terminal; do not reopen history.",
            )
        l.expires_at = body.expires_at.isoformat()
        l.status = "OPEN"
        asset.state = "LISTED"
    audit(db, user, "listing", l, body.action, reason=body.reason)
    return dump(l)
