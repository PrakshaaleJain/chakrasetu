from .auth import has_role
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from pydantic import Field
from . import models as m
from .common import get, dump, fail, audit, idem
from .auth import current_user
from .db import get_db
from .schemas import Schema
from .services.shipments import context
from .services.matching import validate_plan, handling_scope

router = APIRouter()


class ConsolidationIn(Schema):
    shipment_ids: list[str] = Field(min_length=2, max_length=20)
    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=3)


def member_context(db, b):
    return [
        context(db, get(db, m.Shipment, row.shipment_id))
        for row in db.scalars(
            select(m.ConsolidationMember).where(
                m.ConsolidationMember.consolidation_id == b.id
            )
        ).all()
    ]


def validate_batch(db, b):
    members = db.scalars(
        select(m.ConsolidationMember).where(
            m.ConsolidationMember.consolidation_id == b.id
        )
    ).all()
    if len(members) < 2:
        fail(
            "BATCH_INCOMPLETE",
            "Consolidation needs at least two independently agreed asset shipments.",
        )
    total = 0
    scopes = set()
    windows = []
    for row in members:
        s = get(db, m.Shipment, row.shipment_id)
        tx, a, t = context(db, s)
        r = get(db, m.RoutePlan, s.route_id)
        if s.state != "BOOKED":
            fail(
                "STATE_TRANSITION_INVALID",
                "Approve consolidation while every asset is booked and before physical pickup.",
            )
        if (
            r.hub_id != b.hub_id
            or tx.facility_id != b.facility_id
            or t.id != b.transporter_id
        ):
            fail(
                "DESTINATION_INCOMPATIBLE",
                "Every member needs the same approved hub, receiver and whole-route transporter.",
            )
        validate_plan(db, tx, r, tx.id)
        if not r.data.get("hub_approved_by"):
            fail(
                "HUB_APPROVAL_REQUIRED",
                "Each inbound/dwell/outbound plan needs hub approval.",
            )
        if a.mass_kg is None:
            fail("VALUE_UNKNOWN", "Combined mass cannot include unknown values.")
        total += a.mass_kg
        scopes.add(handling_scope(a))
        windows.append((a.data["window_start"], a.data["window_end"]))
    if len(scopes) != 1:
        fail("SAFETY_SCOPE_MISMATCH", "Handling scopes cannot be mixed.")
    if max(w[0] for w in windows) >= min(w[1] for w in windows):
        fail("FACILITY_CLOSED", "Batch pickup and dwell windows do not overlap.")
    t = get(db, m.TransporterProfile, b.transporter_id)
    hub = get(db, m.Facility, b.hub_id)
    caps = db.scalars(
        select(m.FacilityCapability).where(
            m.FacilityCapability.facility_id == hub.id,
            m.FacilityCapability.verification == "VERIFIED",
        )
    ).all()
    if total > t.capacity_kg or not caps or total > min(c.available_kg for c in caps):
        fail(
            "CAPACITY_CONFLICT",
            "Combined load exceeds verified hub or vehicle capacity.",
        )
    return total


@router.get("/consolidations")
def batches(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    out = []
    for b in db.scalars(select(m.Consolidation)).all():
        if (
            has_role(user, "REVIEWER")
            or user.organisation_id in b.data["required_org_ids"]
        ):
            out.append(
                {
                    **dump(b),
                    "members": [
                        dump(x)
                        for x in db.scalars(
                            select(m.ConsolidationMember).where(
                                m.ConsolidationMember.consolidation_id == b.id
                            )
                        ).all()
                    ],
                }
            )
    return out


@router.post("/consolidations")
def create(
    body: ConsolidationIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
    idempotency_key: str = Header(default=""),
):
    db.execute(text("BEGIN IMMEDIATE"))

    def run():
        if len(set(body.shipment_ids)) != len(body.shipment_ids):
            fail("DUPLICATE_ACTION", "Each asset shipment can appear once.")
        shipments = [get(db, m.Shipment, id) for id in body.shipment_ids]
        tx, a, t = context(db, shipments[0])
        r = get(db, m.RoutePlan, shipments[0].route_id)
        if not r.hub_id:
            fail(
                "PATHWAY_NOT_SUPPORTED",
                "Consolidation requires explicitly agreed one-hub routes.",
            )
        hub = get(db, m.Facility, r.hub_id)
        required = set([hub.organisation_id, t.organisation_id])
        for s in shipments:
            mt, ma, _ = context(db, s)
            required.update([mt.seller_org_id, mt.buyer_org_id])
            if db.scalar(
                select(m.ConsolidationMember).where(
                    m.ConsolidationMember.shipment_id == s.id
                )
            ):
                fail(
                    "DUPLICATE_ACTION", "Shipment already belongs to a batch manifest."
                )
        if user.organisation_id not in required:
            fail(
                "FORBIDDEN",
                "Only affected participants may propose consolidation.",
                status=403,
            )
        b = m.Consolidation(
            hub_id=r.hub_id,
            facility_id=tx.facility_id,
            transporter_id=t.id,
            data={
                "required_org_ids": sorted(required),
                "evidence": body.evidence,
                "reason": body.reason,
                "synthetic": get(db, m.Organisation, user.organisation_id).synthetic,
                "cost_source": "EXPLICIT_ACCEPTED_PER_ASSET_QUOTES",
                "savings_paise": None,
                "comparison_status": "INCOMPLETE_NO_COMPARABLE_ACCEPTED_DIRECT_BASELINE",
            },
        )
        db.add(b)
        db.flush()
        for s in shipments:
            db.add(
                m.ConsolidationMember(
                    consolidation_id=b.id,
                    shipment_id=s.id,
                    data={"asset_id": context(db, s)[1].id},
                )
            )
        db.flush()
        mass = validate_batch(db, b)
        totals = [get(db, m.TransportQuote, s.quote_id).total_paise for s in shipments]
        b.data = {
            **b.data,
            "total_mass_kg": mass,
            "total_accepted_cost_paise": (
                sum(totals) if all(x is not None for x in totals) else None
            ),
            "notice": "One shared manifest; individual commitments, accepted costs, capacities, custody and receipt remain per asset. No unapproved split or claimed cost saving.",
        }
        audit(
            db,
            user,
            "consolidation",
            b,
            "PROPOSE_MANIFEST",
            members=body.shipment_ids,
            required_org_ids=sorted(required),
        )
        return b

    return idem(db, user, idempotency_key, "consolidate", body.model_dump(), run)


@router.post("/consolidations/{id}/approve")
def approve(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    db.execute(text("BEGIN IMMEDIATE"))
    b = get(db, m.Consolidation, id)
    if user.organisation_id not in b.data["required_org_ids"]:
        fail(
            "FORBIDDEN", "Only affected manifest participants may approve.", status=403
        )
    validate_batch(db, b)
    if user.organisation_id not in b.approvals:
        b.approvals = [*b.approvals, user.organisation_id]
    if set(b.approvals) == set(b.data["required_org_ids"]):
        b.status = "APPROVED"
    audit(db, user, "consolidation", b, "APPROVE_MANIFEST", approvals=b.approvals)
    return dump(b)


@router.get("/consolidations/{id}/economics")
def batch_economics(
    id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    from .auth import can_view_asset
    from .services.commercial import current_terms

    b = get(db, m.Consolidation, id)
    members = db.scalars(
        select(m.ConsolidationMember).where(
            m.ConsolidationMember.consolidation_id == b.id
        )
    ).all()
    rows = []
    for member in members:
        shipment = get(db, m.Shipment, member.shipment_id)
        tx, asset, carrier = context(db, shipment)
        route = get(db, m.RoutePlan, shipment.route_id)
        rows.append((shipment, asset, tx, route, carrier))
    # Costs are private: only expose records that the actor can already inspect.
    all_assets = [row[1] for row in rows]
    if not all(can_view_asset(db, user, a) for a in all_assets):
        fail(
            "FORBIDDEN",
            "Batch cost analysis requires access to every underlying asset.",
            status=403,
        )
    details = []
    for shipment, asset, tx, route, carrier in rows:
        quote = get(db, m.TransportQuote, shipment.quote_id)
        details.append(
            {
                "asset_id": asset.id,
                "quantity": asset.quantity,
                "mass_kg": asset.mass_kg,
                "committed_quote_paise": quote.total_paise,
                "source": (
                    "ACCEPTED_SYNTHETIC_QUOTE"
                    if asset.data.get("synthetic")
                    else "ACCEPTED_QUOTE"
                ),
                "payer_org_id": current_terms(db, tx).payer_org_id,
            }
        )
    unknown = any(x["committed_quote_paise"] is None for x in details)
    count = sum(x["quantity"] for x in details)
    total = None if unknown else sum(x["committed_quote_paise"] for x in details)
    return {
        "consolidation_id": b.id,
        "quantity": count,
        "total_transport_paise": total,
        "transport_per_battery_paise": None if total is None else total / count,
        "items": details,
        "savings_paise": None,
        "warning": "Independent committed quotes; no joint discount or savings can be claimed without a comparable approved baseline.",
    }
