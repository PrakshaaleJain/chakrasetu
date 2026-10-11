"""Resolve existing commercial records and calculate persisted pathway decisions."""

from hashlib import sha256
import json
from .. import models as m
from ..common import expired, get, fail
from .matching import transporter_check
from .decision_rules import evaluate, POLICY
from .decision_evidence import context_for


def resolve_finance(db, asset, inputs, context):
    result = json.loads(json.dumps(inputs))
    for path, finance in result.items():
        receiver_ids = {r["facility_id"] for r in context["network"][path]["receivers"]}
        if finance.get("facility_id") and finance["facility_id"] not in receiver_ids:
            fail(
                "FINANCE_SCOPE_INVALID",
                "The estimate refers to an ineligible receiving facility.",
            )
        if finance.get("offer_id"):
            offer = get(db, m.Offer, finance["offer_id"])
            listing = get(db, m.Listing, offer.listing_id)
            expected = {
                "AUTOMOTIVE": "REPAIR_REFURBISHMENT",
                "REFURBISHMENT": "REPAIR_REFURBISHMENT",
                "SECOND_LIFE": "SECOND_LIFE_ASSESSMENT",
                "RECYCLING": "RECYCLING",
            }.get(path)
            if (
                listing.asset_id != asset.id
                or offer.pathway != expected
                or offer.facility_id not in receiver_ids
                or offer.status
                not in ["SUBMITTED", "ACCEPTED", "SELECTED", "CONDITIONALLY_ACCEPTED"]
                or expired(offer.expires_at)
            ):
                fail(
                    "FINANCE_SCOPE_INVALID",
                    "Purchase offer is expired, unrelated or incompatible with the qualified route.",
                )
            finance["benefits"] = [
                {
                    "amount_paise": offer.price_paise,
                    "source": "ACTUAL_QUOTE",
                    "reference": offer.id,
                    "recorded_at": offer.created_at,
                    "valid_until": offer.expires_at,
                    "year": 0,
                    "uncertainty_paise": 0,
                }
            ]
            finance["facility_id"] = offer.facility_id
        if finance.get("transport_quote_id"):
            if finance["perspective"] == "WHOLE_PATHWAY" and path in [
                "SECOND_LIFE",
                "RECYCLING",
            ]:
                fail(
                    "ECONOMIC_BASIS_MISMATCH",
                    "An intake transport quote cannot cover every future product/material leg. Use a documented aggregate transport estimate for whole-pathway comparison, or an originator transaction perspective.",
                )
            quote = get(db, m.TransportQuote, finance["transport_quote_id"])
            tx = get(db, m.SaleTransaction, quote.transaction_id)
            route = get(db, m.RoutePlan, quote.route_id)
            if (
                tx.asset_id != asset.id
                or tx.facility_id not in receiver_ids
                or quote.terms_version != tx.terms_version
                or expired(quote.expires_at)
                or quote.status not in ["SUBMITTED", "ACCEPTED"]
                or quote.total_paise is None
                or expired(route.expires_at)
            ):
                fail(
                    "FINANCE_SCOPE_INVALID",
                    "Transport quote is stale or unrelated to the eligible route and current terms.",
                )
            carrier = get(db, m.TransporterProfile, quote.transporter_id)
            if transporter_check(
                db, asset, carrier, route.data.get("points", []), tx.id
            ):
                fail(
                    "FINANCE_SCOPE_INVALID",
                    "Quoted transport no longer passes capability/capacity constraints.",
                )
            finance["costs"]["transport"] = {
                "amount_paise": quote.total_paise,
                "source": "ACTUAL_QUOTE",
                "reference": quote.id,
                "recorded_at": quote.created_at,
                "valid_until": quote.expires_at,
                "year": 0,
                "uncertainty_paise": 0,
            }
    return result


def decision_for(db, asset, inputs=None):
    context = context_for(db, asset)
    economics = resolve_finance(db, asset, inputs or {}, context)
    result = evaluate(context, economics)
    snapshot = {"context": context, "economics": economics, "policy": POLICY}
    result["input_snapshot"] = snapshot
    result["input_fingerprint"] = sha256(
        json.dumps(snapshot, sort_keys=True, default=str).encode()
    ).hexdigest()
    result["asset_id"] = asset.id
    return result
