from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from . import models as m
from .db import get_db
from .auth import current_user, role
from .common import get, fail, audit, idem, expired, parse_time
from .circular_schemas import (
    HandoffIn,
    VersionIn,
    HandoffQuoteIn,
)
from .services.circularity import enforce
from .services.downstream import (
    carrier_check,
    handoff_access,
    handoff_detail,
    receiver_check,
    terms,
)

router = APIRouter(prefix="/circularity", tags=["downstream commercial"])


@router.get("/handoffs")
def handoffs(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return [
        handoff_detail(db, h)
        for h in db.scalars(
            select(m.DownstreamHandoff).order_by(m.DownstreamHandoff.created_at.desc())
        )
        if handoff_access(db, user, h)
    ]


@router.post("/handoffs")
def propose(
    body: HandoffIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))
    item = get(db, m.CircularItem, body.item_id)
    if (
        item.owner_org_id != user.organisation_id
        or item.custodian_org_id != user.organisation_id
    ):
        fail(
            "FORBIDDEN",
            "Proposing seller must have title and current physical custody.",
            status=403,
        )
    if not has_role(
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
        fail("FORBIDDEN", "An assigned commercial role is required.", status=403)
    if item.kind == "BATTERY":
        fail(
            "USE_BATTERY_WORKFLOW",
            "Use existing listings and transaction logistics for battery assets.",
        )
    if item.state not in ["AVAILABLE", "RETIRED"]:
        fail(
            "INPUT_UNAVAILABLE",
            "Only accepted, available or retired downstream items can be offered.",
        )
    if parse_time(body.window_end) <= parse_time(body.window_start) or expired(
        body.window_end
    ):
        fail("WINDOW_INVALID", "Choose a future, ordered collection window.")
    f = get(db, m.Facility, body.receiver_facility_id)
    enforce(receiver_check(db, item, f, body.window_end))
    if body.payer_org_id not in [user.organisation_id, f.organisation_id]:
        fail("PAYER_INVALID", "Payer must be a contracting party.")

    def create():
        if db.scalar(
            select(m.DownstreamHandoff).where(
                m.DownstreamHandoff.item_id == item.id,
                m.DownstreamHandoff.state != "CLOSED",
            )
        ):
            fail(
                "DUPLICATE_ALLOCATION",
                "An active offer or shipment already allocates this item.",
            )
        h = m.DownstreamHandoff(
            item_id=item.id,
            seller_org_id=user.organisation_id,
            buyer_org_id=f.organisation_id,
            receiver_facility_id=f.id,
            data={
                **body.model_dump(),
                "synthetic": item.data.get("synthetic", False),
                "settlement": "NOT_REPORTED",
                "quote": None,
                "physical_confirmations": {},
                "retired_product": item.state == "RETIRED",
            },
        )
        db.add(h)
        db.flush()
        db.add(
            m.HandoffTerms(
                handoff_id=h.id,
                version=1,
                price_paise=body.price_paise,
                payer_org_id=body.payer_org_id,
                budget_paise=body.budget_paise,
                data={
                    "acceptance_specification": body.acceptance_specification,
                    "evidence": body.evidence,
                    "title_transfer": "On accepted physical receipt; disputes do not transfer ownership.",
                },
            )
        )
        audit(db, user, "handoff", h, "PROPOSE_DOWNSTREAM_TERMS")
        db.flush()
        return handoff_detail(db, h)

    return idem(db, user, idempotency_key, "propose-handoff", body.model_dump(), create)


@router.post("/handoffs/{id}/confirm")
def confirm(
    id: str,
    body: VersionIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    h = get(db, m.DownstreamHandoff, id)
    t = terms(db, h)
    if user.organisation_id not in [h.seller_org_id, h.buyer_org_id] or not has_role(
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
            "Only assigned commercial parties may approve these terms.",
            status=403,
        )
    if h.state not in ["PROPOSED", "CONTRACTED"] or body.version != h.version:
        fail("TERMS_VERSION_MISMATCH", "Confirm only the current terms before booking.")
    if t.price_paise is None or t.budget_paise is None:
        fail(
            "ECONOMICS_INCOMPLETE",
            "Explicit agreed price and logistics cap required; unknown cannot become zero.",
        )
    t.confirmations = sorted(set([*t.confirmations, user.organisation_id]))
    h.state = (
        "CONTRACTED"
        if set(t.confirmations) == {h.seller_org_id, h.buyer_org_id}
        else "PROPOSED"
    )
    audit(db, user, "handoff", h, "CONFIRM_VERSION", version=h.version)
    return handoff_detail(db, h)


@router.post("/handoffs/{id}/amend")
def amend(
    id: str,
    body: HandoffIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    h = get(db, m.DownstreamHandoff, id)
    old = terms(db, h)
    if user.organisation_id != old.payer_org_id:
        fail("FORBIDDEN", "Only named payer may propose revised cap.", status=403)
    if (
        h.state not in ["PROPOSED", "CONTRACTED"]
        or body.item_id != h.item_id
        or body.receiver_facility_id != h.receiver_facility_id
        or body.payer_org_id != old.payer_org_id
    ):
        fail(
            "TERMS_SCOPE_CHANGED",
            "Booked scope or contracting parties cannot be changed in place.",
        )
    if parse_time(body.window_end) <= parse_time(body.window_start) or expired(
        body.window_end
    ):
        fail("WINDOW_INVALID", "Choose a future ordered window.")
    enforce(
        receiver_check(
            db,
            get(db, m.CircularItem, h.item_id),
            get(db, m.Facility, h.receiver_facility_id),
            body.window_end,
        )
    )
    h.version += 1
    h.state = "PROPOSED"
    h.data = {
        **h.data,
        **body.model_dump(),
        "quote": None,
        "physical_confirmations": {},
    }
    obj = m.HandoffTerms(
        handoff_id=h.id,
        version=h.version,
        price_paise=body.price_paise,
        payer_org_id=body.payer_org_id,
        budget_paise=body.budget_paise,
        data={
            "acceptance_specification": body.acceptance_specification,
            "evidence": body.evidence,
            "previous_version": old.version,
        },
    )
    db.add(obj)
    audit(db, user, "handoff", h, "PROPOSE_REVISED_TERMS")
    db.flush()
    return handoff_detail(db, h)


@router.post("/handoffs/{id}/quote")
def quote(
    id: str,
    body: HandoffQuoteIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "TRANSPORTER")
    h = get(db, m.DownstreamHandoff, id)
    t = get(db, m.TransporterProfile, body.transporter_id)
    item = get(db, m.CircularItem, h.item_id)
    if t.organisation_id != user.organisation_id:
        fail(
            "FORBIDDEN", "Submit only your organization’s transport quote.", status=403
        )
    if h.state != "CONTRACTED" or expired(body.expires_at):
        fail("QUOTE_INVALID", "Current mutual terms and unexpired quote required.")
    source = get(db, m.Facility, item.facility_id)
    target = get(db, m.Facility, h.receiver_facility_id)
    enforce(
        carrier_check(
            db, item, t, source, target, h.data["window_start"], h.data["window_end"]
        )
    )
    q = {
        **body.model_dump(),
        "terms_version": h.version,
        "quote_id": m.ident(),
        "submitted_by": user.id,
        "submitted_at": m.now(),
        "all_inclusive": True,
    }
    h.data = {
        **h.data,
        "quote": q,
        "quote_history": [*h.data.get("quote_history", []), q],
    }
    audit(db, user, "handoff", h, "QUOTE_SUBMITTED", quote_id=q["quote_id"])
    return {
        "handoff_id": h.id,
        "quote": q,
        "message": "Carrier response recorded; payer must explicitly accept before booking.",
    }
