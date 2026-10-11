"""Presentation-grade synthetic network data generator for ChakraSetu.
Populates realistic demonstration fixtures across all circularity stages:
Intake, Screening, Marketplace Listings, Terms Confirmation, Routing & Leaflet Maps,
Consolidation Manifests, Two-Party Custody Handover, Simulated Telemetry,
Receiving Inspection, Settlement Verification, and Evidenced Disposition (Refurbishment & Recycling).
"""

import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .db import SessionLocal
from . import models as m
from .common import future
from .enums import (
    FLAGS,
    BatteryState,
    ShipmentState,
    Chemistry,
    Form,
    Condition,
    Pathway,
    ListingState,
    OfferState,
    TransactionState,
    QuoteState,
    ReservationState,
    ExceptionState,
    SettlementState,
)
from .seed import seed as seed_base


def add_authority_doc(db, asset_id, uploader_id, internal_id):
    """Ensures a verified TRANSFER_AUTHORITY evidence document exists for an asset."""
    doc_id = f"ev-auth-{asset_id}"
    if not db.get(m.EvidenceDocument, doc_id):
        db.add(
            m.EvidenceDocument(
                id=doc_id,
                asset_id=asset_id,
                uploader_id=uploader_id,
                kind="TRANSFER_AUTHORITY",
                filename=f"mandate-{internal_id.lower()}.pdf",
                checksum=hashlib.sha256(f"Verified transfer mandate for {internal_id}".encode()).hexdigest(),
                version=1,
                review_status="VERIFIED",
                data={
                    "synthetic": True,
                    "reference": f"Ownership and transfer authorization verified for {internal_id}.",
                    "visibility": "PARTIES",
                },
            )
        )


def seed_presentation_data(db):
    # Ensure baseline actors, facilities and initial assets exist
    seed_base(db)

    # Check if presentation assets already exist to be idempotent
    if db.get(m.BatteryAsset, "battery-pres-intransit"):
        return

    # Enable available capacity for Second Current facility so second-life matching succeeds
    cap_second = db.get(m.FacilityCapability, "fac-second-SECOND_LIFE_ASSESSMENT")
    if cap_second and cap_second.available_kg == 0:
        cap_second.available_kg = 400.0

    # -------------------------------------------------------------------------
    # 1. ASSET: In-Transit Shipment (Hero live tracking & physical custody demo)
    # -------------------------------------------------------------------------
    asset_transit = m.BatteryAsset(
        id="battery-pres-intransit",
        internal_id="CS-EV-101",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-trans",
        current_holder_org_id="org-trans",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=42.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.IN_SHIPMENT,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "address": "Indiranagar Fleet Hub, Bengaluru",
            "window_start": future(days=-1),
            "window_end": future(days=5),
            "provenance": "DOCUMENT_REVIEWED",
            "recorded_by": "originator",
            "recorded_at": future(days=-2),
            "notes": "Ather 450X Gen 3 LFP pack (51.1V, 2.9 kWh). Fleet decommissioned at 72% SoH. Pack casing intact, no thermal or moisture incidents.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_transit)
    db.flush()
    add_authority_doc(db, asset_transit.id, "originator", asset_transit.internal_id)

    listing_transit = m.Listing(
        id="listing-pres-transit",
        asset_id=asset_transit.id,
        seller_org_id="org-fleet",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=10),
        data={
            "synthetic": True,
            "mode": "INVITE_OFFERS",
            "terms": "Physical inspection prior to acceptance. Cancellation by mutual agreement.",
            "currency": "INR",
        },
    )
    db.add(listing_transit)
    db.flush()

    offer_transit = m.Offer(
        id="offer-pres-transit",
        listing_id=listing_transit.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        price_paise=2200000,  # ₹22,000
        expires_at=future(days=7),
        status=OfferState.SELECTED,
        data={
            "synthetic": True,
            "payer_org_id": "org-refurb",
            "budget_paise": 300000,  # ₹3,000 logistics cap
            "acceptance_criteria": "Pack enclosure undamaged; cell internal resistance < 20 mΩ; BMS communication operational.",
            "inspection_condition": "CONDITIONAL",
        },
    )
    db.add(offer_transit)
    db.flush()

    tx_transit = m.SaleTransaction(
        id="tx-pres-transit",
        offer_id=offer_transit.id,
        asset_id=asset_transit.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="IN_TRANSIT",
        data={"synthetic": True},
    )
    db.add(tx_transit)
    db.flush()

    terms_transit = m.TermsVersion(
        id="terms-pres-transit-1",
        transaction_id=tx_transit.id,
        version=1,
        payer_org_id="org-refurb",
        budget_paise=300000,
        price_paise=2200000,
        confirmations=["originator", "buyer"],
        data={
            "synthetic": True,
            "payment_terms": "Due after inspection acceptance",
            "cancellation_terms": "Mutual consent required",
            "history": [
                {
                    "version": 1,
                    "action": "MUTUAL_CONFIRMATION",
                    "actor_ids": ["originator", "buyer"],
                    "timestamp": future(days=-1),
                }
            ],
        },
    )
    db.add(terms_transit)

    route_transit = m.RoutePlan(
        id="route-pres-transit",
        transaction_id=tx_transit.id,
        terms_version=1,
        hub_id=None,
        distance_km=28.4,
        hours=0.95,
        estimated_cost_paise=150000,  # ₹1,500
        score=0.92,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [13.035, 77.597]],
            "stops": ["Indiranagar Fleet Hub", "RenewCell Works · Bengaluru"],
            "legs": [
                {
                    "from": "Indiranagar Fleet Hub",
                    "to": "RenewCell Works · Bengaluru",
                    "distance_km": 28.4,
                    "source": "HAVERSINE_X_1.3_PROXY",
                }
            ],
            "transporters": [
                {
                    "id": "trans-1",
                    "name": "Circular Freight",
                    "estimated_cost_paise": 150000,
                    "source": "SYNTHETIC_CONFIGURED_RATE_CARD",
                }
            ],
            "cost_status": "COMPLETE_ESTIMATE",
            "warnings": [
                "Haversine × 1.3 road proxy distance.",
                "Estimated transit 0.95h under normal city traffic conditions.",
            ],
        },
    )
    db.add(route_transit)
    db.flush()

    quote_transit = m.TransportQuote(
        id="quote-pres-transit",
        transaction_id=tx_transit.id,
        route_id=route_transit.id,
        transporter_id="trans-1",
        total_paise=180000,  # ₹1,800 (within ₹3,000 cap)
        terms_version=1,
        expires_at=future(days=14),
        status=QuoteState.ACCEPTED,
        data={
            "synthetic": True,
            "evidence": "Circular Freight confirmed quote with DG compliance & GPS vehicle.",
            "currency": "INR",
        },
    )
    db.add(quote_transit)
    db.flush()

    db.add(
        m.CapacityReservation(
            id="res-pres-transit",
            transaction_id=tx_transit.id,
            resource_type="FACILITY",
            resource_id="fac-refurb-REPAIR_REFURBISHMENT",
            mass_kg=42.0,
            starts_at=future(days=-1),
            ends_at=future(days=5),
            expires_at=future(days=14),
            status=ReservationState.COMMITTED,
            data={"synthetic": True},
        )
    )

    shipment_transit = m.Shipment(
        id="sh-pres-transit",
        transaction_id=tx_transit.id,
        route_id=route_transit.id,
        quote_id=quote_transit.id,
        state=ShipmentState.IN_TRANSIT,
        data={
            "synthetic": True,
            "handover_confirmations": {"org-fleet": True, "org-trans": True},
            "pickup_notes": "Two-party physical handover completed at Indiranagar Depot.",
            "inspections": [],
        },
    )
    db.add(shipment_transit)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-transit",
            shipment_id=shipment_transit.id,
            asset_id=asset_transit.id,
            quantity=1,
            mass_kg=42.0,
            receipt="PENDING",
            data={"synthetic": True},
        )
    )

    # Custody Events (Immutable history)
    db.add(
        m.CustodyEvent(
            id="cust-pres-1",
            shipment_id=shipment_transit.id,
            asset_id=asset_transit.id,
            actor_id="originator",
            previous_holder="org-fleet",
            new_holder="org-fleet",
            event_type="PICKUP_SCHEDULED",
            data={
                "synthetic": True,
                "evidence": "Pickup scheduled with vehicle allocation KA-01-MJ-4412.",
            },
        )
    )
    db.add(
        m.CustodyEvent(
            id="cust-pres-2",
            shipment_id=shipment_transit.id,
            asset_id=asset_transit.id,
            actor_id="originator",
            previous_holder="org-fleet",
            new_holder="org-fleet",
            event_type="PICKED_UP",
            data={
                "synthetic": True,
                "evidence": "Originator Asha signed physical dispatch slip & verified tamper seal #TS-8841.",
            },
        )
    )
    db.add(
        m.CustodyEvent(
            id="cust-pres-3",
            shipment_id=shipment_transit.id,
            asset_id=asset_transit.id,
            actor_id="transporter",
            previous_holder="org-fleet",
            new_holder="org-trans",
            event_type="PICKED_UP",
            data={
                "synthetic": True,
                "evidence": "Transporter Ravi physically confirmed pack condition; custody transferred to Circular Freight.",
            },
        )
    )
    db.add(
        m.CustodyEvent(
            id="cust-pres-4",
            shipment_id=shipment_transit.id,
            asset_id=asset_transit.id,
            actor_id="transporter",
            previous_holder="org-trans",
            new_holder="org-trans",
            event_type="IN_TRANSIT",
            data={
                "synthetic": True,
                "evidence": "Vehicle departed Indiranagar corridor towards Peenya Industrial Area.",
            },
        )
    )

    # Telemetry Events
    db.add(
        m.TelemetryEvent(
            id="tel-pres-1",
            shipment_id=shipment_transit.id,
            source="SIMULATED",
            actor_id="transporter",
            alert=False,
            data={
                "synthetic": True,
                "event": "TEMPERATURE_SENSOR",
                "value": 28.5,
                "notice": "Pack surface temperature 28.5°C — well within the 15°C–45°C safe transit range.",
            },
        )
    )
    db.add(
        m.TelemetryEvent(
            id="tel-pres-2",
            shipment_id=shipment_transit.id,
            source="SIMULATED",
            actor_id="transporter",
            alert=False,
            data={
                "synthetic": True,
                "event": "ROUTE_WAYPOINT",
                "value": "13.002, 77.595",
                "notice": "Passed Outer Ring Road checkpoint; ETA on schedule.",
            },
        )
    )

    db.add(
        m.SettlementRecord(
            id="sett-pres-transit",
            transaction_id=tx_transit.id,
            status=SettlementState.NOT_DUE,
            payer_org_id="org-refurb",
            payee_org_id="org-fleet",
            amount_paise=2200000,
            data={"synthetic": True, "notice": "Settlement due upon physical receipt and inspection acceptance."},
        )
    )

    # -------------------------------------------------------------------------
    # 2. ASSET: One-Hub Aggregation Route (Setu Hub · Electronic City)
    # -------------------------------------------------------------------------
    asset_hub = m.BatteryAsset(
        id="battery-pres-onehub",
        internal_id="CS-HUB-202",
        originator_org_id="org-service",
        owner_org_id="org-service",
        custodian_org_id="org-hub",
        current_holder_org_id="org-hub",
        chemistry=Chemistry.NMC,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=110.0,
        quantity=1,
        lat=12.925,
        lng=77.585,
        authority_confirmed=True,
        state=BatteryState.IN_SHIPMENT,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "address": "Urban Cell Service Centre, Jayanagar",
            "window_start": future(days=-2),
            "window_end": future(days=5),
            "provenance": "DOCUMENT_REVIEWED",
            "recorded_by": "originator2",
            "recorded_at": future(days=-3),
            "notes": "Tata Nexon EV Max 30.2 kWh NMC battery pack. Decommissioned after 140,000 km fleet operation. Normal degradation to 68% SoH.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_hub)
    db.flush()
    add_authority_doc(db, asset_hub.id, "originator2", asset_hub.internal_id)

    listing_hub = m.Listing(
        id="listing-pres-hub",
        asset_id=asset_hub.id,
        seller_org_id="org-service",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=12),
        data={"synthetic": True, "mode": "INVITE_OFFERS"},
    )
    db.add(listing_hub)
    db.flush()

    offer_hub = m.Offer(
        id="offer-pres-hub",
        listing_id=listing_hub.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        price_paise=4800000,  # ₹48,000
        expires_at=future(days=10),
        status=OfferState.SELECTED,
        data={
            "synthetic": True,
            "payer_org_id": "org-refurb",
            "budget_paise": 400000,  # ₹4,000 logistics budget
            "acceptance_criteria": "Pack modules intact; cell balance within 40mV.",
        },
    )
    db.add(offer_hub)
    db.flush()

    tx_hub = m.SaleTransaction(
        id="tx-pres-hub",
        offer_id=offer_hub.id,
        asset_id=asset_hub.id,
        seller_org_id="org-service",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="IN_TRANSIT",
        data={"synthetic": True},
    )
    db.add(tx_hub)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-hub-1",
            transaction_id=tx_hub.id,
            version=1,
            payer_org_id="org-refurb",
            budget_paise=400000,
            price_paise=4800000,
            confirmations=["originator2", "buyer"],
            data={"synthetic": True},
        )
    )

    route_hub = m.RoutePlan(
        id="route-pres-hub",
        transaction_id=tx_hub.id,
        terms_version=1,
        hub_id="fac-hub",
        distance_km=46.2,
        hours=3.54,
        estimated_cost_paise=283160,  # ₹2,832 (includes hub dwell & fee)
        score=0.88,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.925, 77.585], [12.84, 77.66], [13.035, 77.597]],
            "stops": ["Urban Cell Jayanagar", "Setu Hub · Electronic City", "RenewCell Works · Bengaluru"],
            "legs": [
                {
                    "from": "Urban Cell Jayanagar",
                    "to": "Setu Hub · Electronic City",
                    "distance_km": 18.5,
                    "source": "HAVERSINE_X_1.3_PROXY",
                },
                {
                    "from": "Setu Hub · Electronic City",
                    "to": "RenewCell Works · Bengaluru",
                    "distance_km": 27.7,
                    "source": "HAVERSINE_X_1.3_PROXY",
                },
            ],
            "transporters": [
                {
                    "id": "trans-1",
                    "name": "Circular Freight",
                    "estimated_cost_paise": 283160,
                }
            ],
            "hub_approved_by": "hub",
        },
    )
    db.add(route_hub)
    db.flush()

    quote_hub = m.TransportQuote(
        id="quote-pres-hub",
        transaction_id=tx_hub.id,
        route_id=route_hub.id,
        transporter_id="trans-1",
        total_paise=280000,  # ₹2,800
        terms_version=1,
        expires_at=future(days=14),
        status=QuoteState.ACCEPTED,
        data={"synthetic": True, "evidence": "Circular Freight one-hub quote."},
    )
    db.add(quote_hub)
    db.flush()

    shipment_hub = m.Shipment(
        id="sh-pres-hub",
        transaction_id=tx_hub.id,
        route_id=route_hub.id,
        quote_id=quote_hub.id,
        state=ShipmentState.IN_TRANSIT,
        data={
            "synthetic": True,
            "hub_stage": "HUB_RECEIVED",
            "handover_confirmations": {"org-service": True, "org-trans": True, "org-hub": True},
            "inspections": [],
        },
    )
    db.add(shipment_hub)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-hub",
            shipment_id=shipment_hub.id,
            asset_id=asset_hub.id,
            quantity=1,
            mass_kg=110.0,
            receipt="PENDING",
            data={"synthetic": True},
        )
    )

    db.add(
        m.CustodyEvent(
            id="cust-pres-hub-1",
            shipment_id=shipment_hub.id,
            asset_id=asset_hub.id,
            actor_id="originator2",
            previous_holder="org-service",
            new_holder="org-trans",
            event_type="PICKED_UP",
            data={"synthetic": True, "evidence": "Handed over to carrier Ravi at Jayanagar depot."},
        )
    )
    db.add(
        m.CustodyEvent(
            id="cust-pres-hub-2",
            shipment_id=shipment_hub.id,
            asset_id=asset_hub.id,
            actor_id="hub",
            previous_holder="org-trans",
            new_holder="org-hub",
            event_type="HUB_RECEIVED",
            data={
                "synthetic": True,
                "evidence": "Neel confirmed intake inspection at Setu Hub Electronic City staging bay #3.",
            },
        )
    )

    db.add(
        m.TelemetryEvent(
            id="tel-pres-hub-1",
            shipment_id=shipment_hub.id,
            source="SIMULATED",
            actor_id="hub",
            alert=False,
            data={
                "synthetic": True,
                "event": "HUB_DWELL_TIMER",
                "value": "1.1 hours elapsed",
                "notice": "Pack undergoing scheduled diagnostic soak and staging in climate-controlled zone.",
            },
        )
    )

    db.add(
        m.SettlementRecord(
            id="sett-pres-hub",
            transaction_id=tx_hub.id,
            status=SettlementState.NOT_DUE,
            payer_org_id="org-refurb",
            payee_org_id="org-service",
            amount_paise=4800000,
            data={"synthetic": True},
        )
    )

    # -------------------------------------------------------------------------
    # 3. ASSET: Completed Circularity Loop (Inspection, Double Settlement & Disposition)
    # -------------------------------------------------------------------------
    asset_closed = m.BatteryAsset(
        id="battery-pres-closed",
        internal_id="CS-MYS-404",
        originator_org_id="org-fleet",
        owner_org_id="org-refurb",
        custodian_org_id="org-refurb",
        current_holder_org_id="org-refurb",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=28.0,
        quantity=1,
        lat=13.035,
        lng=77.597,
        authority_confirmed=True,
        state=BatteryState.DISPOSITION_RECORDED,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "address": "RenewCell Works Facility, Bengaluru",
            "notes": "Bounce Infinity E1 swappable battery pack (48V, 2 kWh). Repurposed for second-life stationary solar storage.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_closed)
    db.flush()
    add_authority_doc(db, asset_closed.id, "originator", asset_closed.internal_id)

    listing_closed = m.Listing(
        id="listing-pres-closed",
        asset_id=asset_closed.id,
        seller_org_id="org-fleet",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=1),
        data={"synthetic": True, "mode": "INVITE_OFFERS"},
    )
    db.add(listing_closed)
    db.flush()

    offer_closed = m.Offer(
        id="offer-pres-closed",
        listing_id=listing_closed.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        price_paise=1800000,  # ₹18,000
        expires_at=future(days=1),
        status=OfferState.SELECTED,
        data={"synthetic": True, "payer_org_id": "org-refurb", "budget_paise": 250000},
    )
    db.add(offer_closed)
    db.flush()

    tx_closed = m.SaleTransaction(
        id="tx-pres-closed",
        offer_id=offer_closed.id,
        asset_id=asset_closed.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.CLOSED,
        logistics_status="COMPLETED",
        data={"synthetic": True},
    )
    db.add(tx_closed)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-closed-1",
            transaction_id=tx_closed.id,
            version=1,
            payer_org_id="org-refurb",
            budget_paise=250000,
            price_paise=1800000,
            confirmations=["originator", "buyer"],
            data={"synthetic": True},
        )
    )

    route_closed = m.RoutePlan(
        id="route-pres-closed",
        transaction_id=tx_closed.id,
        terms_version=1,
        hub_id=None,
        distance_km=22.1,
        hours=0.74,
        estimated_cost_paise=120000,
        score=0.95,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.97, 77.59], [13.035, 77.597]],
            "stops": ["Central Bengaluru Depot", "RenewCell Works · Bengaluru"],
            "legs": [{"from": "Central Bengaluru Depot", "to": "RenewCell Works · Bengaluru", "distance_km": 22.1, "source": "HAVERSINE_X_1.3_PROXY"}],
        },
    )
    db.add(route_closed)
    db.flush()

    quote_closed = m.TransportQuote(
        id="quote-pres-closed",
        transaction_id=tx_closed.id,
        route_id=route_closed.id,
        transporter_id="trans-1",
        total_paise=120000,
        terms_version=1,
        expires_at=future(days=10),
        status=QuoteState.ACCEPTED,
        data={"synthetic": True},
    )
    db.add(quote_closed)
    db.flush()

    shipment_closed = m.Shipment(
        id="sh-pres-closed",
        transaction_id=tx_closed.id,
        route_id=route_closed.id,
        quote_id=quote_closed.id,
        state=ShipmentState.CLOSED,
        data={
            "synthetic": True,
            "inspection_accepted": True,
            "handover_confirmations": {"org-fleet": True, "org-trans": True, "org-refurb": True},
            "inspections": [
                {
                    "outcome": "ACCEPT_AS_AGREED",
                    "notes": "Cell impedance 14.8 mΩ avg. Cell chemistry intact; approved for second-life agricultural solar pump storage.",
                    "evidence": "RenewCell Test Report #RC-QC-2026-992",
                    "actor_id": "buyer",
                    "timestamp": future(days=-3),
                }
            ],
        },
    )
    db.add(shipment_closed)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-closed",
            shipment_id=shipment_closed.id,
            asset_id=asset_closed.id,
            quantity=1,
            mass_kg=28.0,
            receipt="ACCEPTED",
            data={"synthetic": True},
        )
    )

    db.add(
        m.CustodyEvent(
            id="cust-pres-closed-1",
            shipment_id=shipment_closed.id,
            asset_id=asset_closed.id,
            actor_id="buyer",
            previous_holder="org-trans",
            new_holder="org-refurb",
            event_type="RECEIVED",
            data={
                "synthetic": True,
                "evidence": "Meera recorded complete physical receipt and condition match.",
            },
        )
    )

    db.add(
        m.SettlementRecord(
            id="sett-pres-closed",
            transaction_id=tx_closed.id,
            status=SettlementState.SETTLED_CONFIRMED,
            payer_org_id="org-refurb",
            payee_org_id="org-fleet",
            amount_paise=1800000,
            data={
                "synthetic": True,
                "history": [
                    {
                        "status": "DUE",
                        "actor_id": "buyer",
                        "timestamp": future(days=-3),
                    },
                    {
                        "status": "PAYMENT_REPORTED",
                        "actor_id": "buyer",
                        "reference": "RTGS UTR #HDFC00028919014 (₹18,000 paid)",
                        "timestamp": future(days=-2),
                    },
                    {
                        "status": "SETTLED_CONFIRMED",
                        "actor_id": "originator",
                        "reference": "Asha verified commercial receipt in fleet ledger",
                        "timestamp": future(days=-1),
                    },
                ],
            },
        )
    )

    db.add(
        m.DispositionRecord(
            id="disp-pres-closed",
            asset_id=asset_closed.id,
            facility_id="fac-refurb",
            actor_id="buyer",
            outcome="REFURBISHMENT_COMPLETED",
            review_status="VERIFIED",
            data={
                "synthetic": True,
                "certificate_id": "CERT-2ND-LIFE-2026-081",
                "application": "Solar Agricultural Pump Station Storage",
                "warranty_months": 12,
                "evidence": "RenewCell Second-Life Quality Certification & Lab Test Results.",
            },
        )
    )

    # -------------------------------------------------------------------------
    # 4. ASSET: Industrial Recycling Pathway (Hosur Hydrometallurgical recovery)
    # -------------------------------------------------------------------------
    asset_recycle = m.BatteryAsset(
        id="battery-pres-recycle",
        internal_id="CS-HOS-505",
        originator_org_id="org-service",
        owner_org_id="org-recycle",
        custodian_org_id="org-recycle",
        current_holder_org_id="org-recycle",
        chemistry=Chemistry.NMC,
        form=Form.MODULE,
        condition=Condition.NON_FUNCTIONAL,
        mass_kg=85.0,
        quantity=1,
        lat=12.74,
        lng=77.83,
        authority_confirmed=True,
        state=BatteryState.DISPOSITION_RECORDED,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "fault",
            "address": "Loop Materials Hydromet Recycling Park, Hosur",
            "notes": "Mahindra e-Verito high-voltage pack module (NMC 72V). Non-functional internal cells routed to black mass extraction.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_recycle)
    db.flush()
    add_authority_doc(db, asset_recycle.id, "originator2", asset_recycle.internal_id)

    listing_recycle = m.Listing(
        id="listing-pres-recycle",
        asset_id=asset_recycle.id,
        seller_org_id="org-service",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=1),
        data={"synthetic": True},
    )
    db.add(listing_recycle)
    db.flush()

    offer_recycle = m.Offer(
        id="offer-pres-recycle",
        listing_id=listing_recycle.id,
        buyer_org_id="org-recycle",
        facility_id="fac-recycle",
        pathway=Pathway.RECYCLING,
        price_paise=1450000,  # ₹14,500
        expires_at=future(days=1),
        status=OfferState.SELECTED,
        data={"synthetic": True, "budget_paise": 300000, "payer_org_id": "org-recycle"},
    )
    db.add(offer_recycle)
    db.flush()

    tx_recycle = m.SaleTransaction(
        id="tx-pres-recycle",
        offer_id=offer_recycle.id,
        asset_id=asset_recycle.id,
        seller_org_id="org-service",
        buyer_org_id="org-recycle",
        facility_id="fac-recycle",
        pathway=Pathway.RECYCLING,
        terms_version=1,
        status=TransactionState.CLOSED,
        logistics_status="COMPLETED",
        data={"synthetic": True},
    )
    db.add(tx_recycle)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-recycle-1",
            transaction_id=tx_recycle.id,
            version=1,
            payer_org_id="org-recycle",
            budget_paise=300000,
            price_paise=1450000,
            confirmations=["originator2", "recycler"],
            data={"synthetic": True},
        )
    )

    route_recycle = m.RoutePlan(
        id="route-pres-recycle",
        transaction_id=tx_recycle.id,
        terms_version=1,
        hub_id=None,
        distance_km=48.5,
        hours=1.62,
        estimated_cost_paise=190000,
        score=0.91,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.925, 77.585], [12.74, 77.83]],
            "stops": ["Urban Cell Jayanagar", "Loop Materials · Hosur"],
            "legs": [{"from": "Urban Cell Jayanagar", "to": "Loop Materials · Hosur", "distance_km": 48.5, "source": "HAVERSINE_X_1.3_PROXY"}],
        },
    )
    db.add(route_recycle)
    db.flush()

    quote_recycle = m.TransportQuote(
        id="quote-pres-recycle",
        transaction_id=tx_recycle.id,
        route_id=route_recycle.id,
        transporter_id="trans-1",
        total_paise=190000,
        terms_version=1,
        expires_at=future(days=10),
        status=QuoteState.ACCEPTED,
        data={"synthetic": True},
    )
    db.add(quote_recycle)
    db.flush()

    shipment_recycle = m.Shipment(
        id="sh-pres-recycle",
        transaction_id=tx_recycle.id,
        route_id=route_recycle.id,
        quote_id=quote_recycle.id,
        state=ShipmentState.CLOSED,
        data={
            "synthetic": True,
            "inspection_accepted": True,
            "inspections": [
                {
                    "outcome": "ACCEPT_AS_AGREED",
                    "notes": "Module intact. Graded Grade-A for hydrometallurgical lithium and nickel recovery.",
                    "evidence": "Loop Materials Lab Receiving Assay #LM-QC-811",
                    "actor_id": "recycler",
                    "timestamp": future(days=-4),
                }
            ],
        },
    )
    db.add(shipment_recycle)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-recycle",
            shipment_id=shipment_recycle.id,
            asset_id=asset_recycle.id,
            quantity=1,
            mass_kg=85.0,
            receipt="ACCEPTED",
            data={"synthetic": True},
        )
    )

    db.add(
        m.CustodyEvent(
            id="cust-pres-recycle-1",
            shipment_id=shipment_recycle.id,
            asset_id=asset_recycle.id,
            actor_id="recycler",
            previous_holder="org-trans",
            new_holder="org-recycle",
            event_type="RECEIVED",
            data={"synthetic": True, "evidence": "Dev confirmed receipt at Hosur Hydromet Facility."},
        )
    )

    db.add(
        m.SettlementRecord(
            id="sett-pres-recycle",
            transaction_id=tx_recycle.id,
            status=SettlementState.SETTLED_CONFIRMED,
            payer_org_id="org-recycle",
            payee_org_id="org-service",
            amount_paise=1450000,
            data={
                "synthetic": True,
                "history": [
                    {"status": "PAYMENT_REPORTED", "reference": "NEFT #LOOPMAT991823", "actor_id": "recycler"},
                    {"status": "SETTLED_CONFIRMED", "reference": "Kabir acknowledged in Urban Cell books", "actor_id": "originator2"},
                ],
            },
        )
    )

    db.add(
        m.DispositionRecord(
            id="disp-pres-recycle",
            asset_id=asset_recycle.id,
            facility_id="fac-recycle",
            actor_id="recycler",
            outcome="RECYCLING_COMPLETED",
            review_status="VERIFIED",
            data={
                "synthetic": True,
                "certificate_id": "EPR-CREDIT-IND-2026-9041",
                "black_mass_kg": 42.1,
                "lithium_carbonate_kg": 6.4,
                "cobalt_sulphate_kg": 9.8,
                "nickel_sulphate_kg": 16.2,
                "elemental_recovery_rate": "94.6%",
                "evidence": "Central Pollution Control Board (CPCB) EPR certificate issued.",
            },
        )
    )

    # -------------------------------------------------------------------------
    # 5. ASSET: Active Marketplace Listing with Competing Offers
    # -------------------------------------------------------------------------
    asset_market = m.BatteryAsset(
        id="battery-pres-marketplace",
        internal_id="CS-HYD-707",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-fleet",
        current_holder_org_id="org-fleet",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=38.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.LISTED,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "address": "Indiranagar Fleet Hub, Bengaluru",
            "notes": "Piaggio Ape E-City electric 3-wheeler pack (LFP, 48V, 7.5 kWh). Tested at 74% remaining capacity.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_market)
    db.flush()
    add_authority_doc(db, asset_market.id, "originator", asset_market.internal_id)

    listing_market = m.Listing(
        id="listing-pres-market",
        asset_id=asset_market.id,
        seller_org_id="org-fleet",
        status=ListingState.OPEN,
        expires_at=future(days=14),
        data={
            "synthetic": True,
            "mode": "INVITE_OFFERS",
            "terms": "Physical delivery to Bengaluru/Hosur cluster. Certified test reports required before release.",
            "currency": "INR",
        },
    )
    db.add(listing_market)
    db.flush()

    db.add(
        m.Offer(
            id="offer-pres-compete-1",
            listing_id=listing_market.id,
            buyer_org_id="org-refurb",
            facility_id="fac-refurb",
            pathway=Pathway.REPAIR_REFURBISHMENT,
            price_paise=2100000,  # ₹21,000
            expires_at=future(days=7),
            status=OfferState.SUBMITTED,
            data={
                "synthetic": True,
                "payer_org_id": "org-refurb",
                "budget_paise": 300000,
                "acceptance_criteria": "Pack modules undamaged; cell delta voltage < 30mV.",
                "inspection_condition": "CONDITIONAL",
            },
        )
    )

    db.add(
        m.Offer(
            id="offer-pres-compete-2",
            listing_id=listing_market.id,
            buyer_org_id="org-recycle",
            facility_id="fac-recycle",
            pathway=Pathway.RECYCLING,
            price_paise=1750000,  # ₹17,500
            expires_at=future(days=7),
            status=OfferState.SUBMITTED,
            data={
                "synthetic": True,
                "payer_org_id": "org-recycle",
                "budget_paise": 250000,
                "acceptance_criteria": "Direct recycling intake grading; full casing return.",
                "inspection_condition": "FIRM_SUBJECT_TO_CHECKS",
            },
        )
    )

    # Clean second open listing ready for live offer demo by the presenter
    asset_open2 = m.BatteryAsset(
        id="battery-pres-open2",
        internal_id="CS-BLR-880",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-fleet",
        current_holder_org_id="org-fleet",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=36.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.LISTED,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "maintenance replacement",
            "address": "Indiranagar Fleet Hub, Bengaluru",
            "notes": "Bounce Infinity E1 modular pack (48V LFP, 2 kWh). Ready for downstream offers.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_open2)
    db.flush()
    add_authority_doc(db, asset_open2.id, "originator", asset_open2.internal_id)

    db.add(
        m.Listing(
            id="listing-pres-open2",
            asset_id=asset_open2.id,
            seller_org_id="org-fleet",
            status=ListingState.OPEN,
            expires_at=future(days=14),
            data={
                "synthetic": True,
                "mode": "INVITE_OFFERS",
                "terms": "Fresh listing open for buyer offers. Inspection before acceptance.",
                "currency": "INR",
            },
        )
    )

    # -------------------------------------------------------------------------
    # 6. ASSET: Transporter Budget Overrun Exception (Exception Queue Showcase)
    # -------------------------------------------------------------------------
    asset_overrun = m.BatteryAsset(
        id="battery-pres-overrun",
        internal_id="CS-BLR-808",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-fleet",
        current_holder_org_id="org-fleet",
        chemistry=Chemistry.NMC,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=120.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.AGREED,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "notes": "Heavy-duty commercial EV battery pack (NMC 60 kWh).",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_overrun)
    db.flush()
    add_authority_doc(db, asset_overrun.id, "originator", asset_overrun.internal_id)

    listing_overrun = m.Listing(
        id="listing-pres-overrun",
        asset_id=asset_overrun.id,
        seller_org_id="org-fleet",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=5),
        data={"synthetic": True},
    )
    db.add(listing_overrun)
    db.flush()

    offer_overrun = m.Offer(
        id="offer-pres-overrun",
        listing_id=listing_overrun.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        price_paise=3800000,  # ₹38,000
        expires_at=future(days=5),
        status=OfferState.SELECTED,
        data={"synthetic": True, "payer_org_id": "org-refurb", "budget_paise": 300000},
    )
    db.add(offer_overrun)
    db.flush()

    tx_overrun = m.SaleTransaction(
        id="tx-pres-overrun",
        offer_id=offer_overrun.id,
        asset_id=asset_overrun.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="NO_ACCEPTANCE",
        data={"synthetic": True},
    )
    db.add(tx_overrun)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-overrun-1",
            transaction_id=tx_overrun.id,
            version=1,
            payer_org_id="org-refurb",
            budget_paise=300000,  # ₹3,000 cap
            price_paise=3800000,
            confirmations=["originator", "buyer"],
            data={"synthetic": True},
        )
    )

    route_overrun = m.RoutePlan(
        id="route-pres-overrun",
        transaction_id=tx_overrun.id,
        terms_version=1,
        hub_id=None,
        distance_km=35.8,
        hours=1.2,
        estimated_cost_paise=320000,
        score=0.85,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [13.035, 77.597]],
            "stops": ["Indiranagar Fleet Hub", "RenewCell Works · Bengaluru"],
            "legs": [{"from": "Indiranagar Fleet Hub", "to": "RenewCell Works · Bengaluru", "distance_km": 35.8, "source": "HAVERSINE_X_1.3_PROXY"}],
        },
    )
    db.add(route_overrun)
    db.flush()

    quote_overrun = m.TransportQuote(
        id="quote-pres-overrun",
        transaction_id=tx_overrun.id,
        route_id=route_overrun.id,
        transporter_id="trans-1",
        total_paise=420000,  # ₹4,200 (over ₹3,000 budget!)
        terms_version=1,
        expires_at=future(days=5),
        status=QuoteState.SUBMITTED,
        data={"synthetic": True, "evidence": "Special heavy-lift transport quote exceeding buyer cap."},
    )
    db.add(quote_overrun)
    db.flush()

    db.add(
        m.ExceptionCase(
            id="exc-pres-overrun",
            object_type="transaction",
            object_id=tx_overrun.id,
            category="QUOTE_OVER_BUDGET",
            severity="MEDIUM",
            owner_org_id="org-refurb",
            status=ExceptionState.OPEN,
            next_action="Buyer Meera must propose amended budget (terms v2) or select alternative carrier quote within ₹3,000 cap.",
            due_at=future(days=2),
            resolution=None,
            data={
                "synthetic": True,
                "quote_id": quote_overrun.id,
                "quote_paise": 420000,
                "budget_paise": 300000,
                "overrun_paise": 120000,
                "notice": "Disclosed logistics quote exceeds buyer cap by ₹1,200.",
            },
        )
    )

    # -------------------------------------------------------------------------
    # 7. ASSET: Receipt Discrepancy Dispute (Exception Queue & Dispute Resolution)
    # -------------------------------------------------------------------------
    asset_dispute = m.BatteryAsset(
        id="battery-pres-dispute",
        internal_id="CS-BLR-909",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-refurb",
        current_holder_org_id="org-refurb",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=30.0,
        quantity=1,
        lat=13.035,
        lng=77.597,
        authority_confirmed=True,
        state=BatteryState.IN_SHIPMENT,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "notes": "Light EV scooter battery pack. Received with physical terminal discrepancy.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_dispute)
    db.flush()
    add_authority_doc(db, asset_dispute.id, "originator", asset_dispute.internal_id)

    listing_dispute = m.Listing(
        id="listing-pres-dispute",
        asset_id=asset_dispute.id,
        seller_org_id="org-fleet",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=5),
        data={"synthetic": True},
    )
    db.add(listing_dispute)
    db.flush()

    offer_dispute = m.Offer(
        id="offer-pres-dispute",
        listing_id=listing_dispute.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        price_paise=1900000,
        expires_at=future(days=5),
        status=OfferState.SELECTED,
        data={"synthetic": True, "payer_org_id": "org-refurb", "budget_paise": 250000},
    )
    db.add(offer_dispute)
    db.flush()

    tx_dispute = m.SaleTransaction(
        id="tx-pres-dispute",
        offer_id=offer_dispute.id,
        asset_id=asset_dispute.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="IN_TRANSIT",
        data={"synthetic": True},
    )
    db.add(tx_dispute)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-dispute-1",
            transaction_id=tx_dispute.id,
            version=1,
            payer_org_id="org-refurb",
            budget_paise=250000,
            price_paise=1900000,
            confirmations=["originator", "buyer"],
            data={"synthetic": True},
        )
    )

    route_dispute = m.RoutePlan(
        id="route-pres-dispute",
        transaction_id=tx_dispute.id,
        terms_version=1,
        hub_id=None,
        distance_km=24.0,
        hours=0.8,
        estimated_cost_paise=140000,
        score=0.9,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [13.035, 77.597]],
            "stops": ["Indiranagar Fleet Hub", "RenewCell Works · Bengaluru"],
            "legs": [{"from": "Indiranagar Fleet Hub", "to": "RenewCell Works · Bengaluru", "distance_km": 24.0, "source": "HAVERSINE_X_1.3_PROXY"}],
        },
    )
    db.add(route_dispute)
    db.flush()

    quote_dispute = m.TransportQuote(
        id="quote-pres-dispute",
        transaction_id=tx_dispute.id,
        route_id=route_dispute.id,
        transporter_id="trans-1",
        total_paise=140000,
        terms_version=1,
        expires_at=future(days=10),
        status=QuoteState.ACCEPTED,
        data={"synthetic": True},
    )
    db.add(quote_dispute)
    db.flush()

    shipment_dispute = m.Shipment(
        id="sh-pres-dispute",
        transaction_id=tx_dispute.id,
        route_id=route_dispute.id,
        quote_id=quote_dispute.id,
        state=ShipmentState.RECEIPT_DISPUTED,
        data={
            "synthetic": True,
            "handover_confirmations": {"org-fleet": True, "org-trans": True},
            "receipt_discrepancy": "Physical terminal post dent observed on receiving intake.",
            "inspections": [],
        },
    )
    db.add(shipment_dispute)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-dispute",
            shipment_id=shipment_dispute.id,
            asset_id=asset_dispute.id,
            quantity=1,
            mass_kg=30.0,
            receipt="DISPUTED",
            data={"synthetic": True},
        )
    )

    db.add(
        m.CustodyEvent(
            id="cust-pres-dispute-1",
            shipment_id=shipment_dispute.id,
            asset_id=asset_dispute.id,
            actor_id="buyer",
            previous_holder="org-trans",
            new_holder="org-refurb",
            event_type="ARRIVED_PENDING_RECEIPT",
            data={"synthetic": True, "evidence": "Vehicle arrived at RenewCell unloading dock."},
        )
    )

    db.add(
        m.ExceptionCase(
            id="exc-pres-dispute",
            object_type="shipment",
            object_id=shipment_dispute.id,
            category="RECEIPT_DISPUTE",
            severity="HIGH",
            owner_org_id="org-review",
            status=ExceptionState.OPEN,
            next_action="Network Reviewer Priya to review photographic evidence of bent terminal post and authorise settlement reconciliation.",
            due_at=future(days=1),
            resolution=None,
            data={
                "synthetic": True,
                "discrepancy_reported": "Negative terminal post bent ~15° during transit handling.",
                "reported_by": "buyer",
            },
        )
    )

    # -------------------------------------------------------------------------
    # 8. ASSET: Second-Life Assessment Routing Ready to Demo
    # -------------------------------------------------------------------------
    asset_2nd = m.BatteryAsset(
        id="battery-pres-secondlife",
        internal_id="CS-2ND-606",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-fleet",
        current_holder_org_id="org-fleet",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=34.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.AGREED,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "notes": "Commercial E-Rickshaw 48V 100Ah battery pack. Ideal candidate for second-life assessment at Mysuru facility.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_2nd)
    db.flush()
    add_authority_doc(db, asset_2nd.id, "originator", asset_2nd.internal_id)

    listing_2nd = m.Listing(
        id="listing-pres-2nd",
        asset_id=asset_2nd.id,
        seller_org_id="org-fleet",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=7),
        data={"synthetic": True},
    )
    db.add(listing_2nd)
    db.flush()

    offer_2nd = m.Offer(
        id="offer-pres-2nd",
        listing_id=listing_2nd.id,
        buyer_org_id="org-second",
        facility_id="fac-second",
        pathway=Pathway.SECOND_LIFE_ASSESSMENT,
        price_paise=1600000,  # ₹16,000
        expires_at=future(days=7),
        status=OfferState.SELECTED,
        data={"synthetic": True, "payer_org_id": "org-second", "budget_paise": 350000},
    )
    db.add(offer_2nd)
    db.flush()

    tx_2nd = m.SaleTransaction(
        id="tx-pres-2nd",
        offer_id=offer_2nd.id,
        asset_id=asset_2nd.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-second",
        facility_id="fac-second",
        pathway=Pathway.SECOND_LIFE_ASSESSMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="PENDING",
        data={"synthetic": True},
    )
    db.add(tx_2nd)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-2nd-1",
            transaction_id=tx_2nd.id,
            version=1,
            payer_org_id="org-second",
            budget_paise=350000,  # ₹3,500
            price_paise=1600000,
            confirmations=["originator", "secondlife"],
            data={"synthetic": True},
        )
    )

    route_2nd_direct = m.RoutePlan(
        id="route-pres-2nd-direct",
        transaction_id=tx_2nd.id,
        terms_version=1,
        hub_id=None,
        distance_km=142.0,
        hours=4.73,
        estimated_cost_paise=305600,  # ₹3,056
        score=0.94,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [12.30, 76.65]],
            "stops": ["Indiranagar Fleet Hub", "Second Current · Mysuru"],
            "legs": [
                {
                    "from": "Indiranagar Fleet Hub",
                    "to": "Second Current · Mysuru",
                    "distance_km": 142.0,
                    "source": "HAVERSINE_X_1.3_PROXY",
                }
            ],
            "transporters": [
                {
                    "id": "trans-1",
                    "name": "Circular Freight",
                    "estimated_cost_paise": 305600,
                }
            ],
        },
    )
    db.add(route_2nd_direct)

    route_2nd_hub = m.RoutePlan(
        id="route-pres-2nd-hub",
        transaction_id=tx_2nd.id,
        terms_version=1,
        hub_id="fac-hub",
        distance_km=158.4,
        hours=7.28,
        estimated_cost_paise=354120,
        score=0.81,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [12.84, 77.66], [12.30, 76.65]],
            "stops": ["Indiranagar Fleet Hub", "Setu Hub · Electronic City", "Second Current · Mysuru"],
            "legs": [
                {"from": "Indiranagar Fleet Hub", "to": "Setu Hub · Electronic City", "distance_km": 21.0, "source": "HAVERSINE_X_1.3_PROXY"},
                {"from": "Setu Hub · Electronic City", "to": "Second Current · Mysuru", "distance_km": 137.4, "source": "HAVERSINE_X_1.3_PROXY"},
            ],
            "transporters": [
                {
                    "id": "trans-1",
                    "name": "Circular Freight",
                    "estimated_cost_paise": 354120,
                }
            ],
        },
    )
    db.add(route_2nd_hub)
    db.flush()

    db.add(
        m.TransportQuote(
            id="quote-pres-2nd",
            transaction_id=tx_2nd.id,
            route_id=route_2nd_direct.id,
            transporter_id="trans-1",
            total_paise=320000,  # ₹3,200 (within ₹3,500 budget)
            terms_version=1,
            expires_at=future(days=14),
            status=QuoteState.SUBMITTED,
            data={
                "synthetic": True,
                "evidence": "Circular Freight scheduled inter-city route quote.",
            },
        )
    )

    # -------------------------------------------------------------------------
    # 9. ASSET: Booked Shipment Ready for Physical Pickup Demo
    # -------------------------------------------------------------------------
    asset_booked = m.BatteryAsset(
        id="battery-pres-booked",
        internal_id="CS-OLA-303",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-fleet",
        current_holder_org_id="org-fleet",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=48.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.IN_SHIPMENT,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "degradation",
            "notes": "Ola S1 Pro 4 kWh LFP battery pack. Booked for transport; awaiting two-party physical pickup.",
            "handling_clearance": "ORDINARY",
        },
    )
    db.add(asset_booked)
    db.flush()
    add_authority_doc(db, asset_booked.id, "originator", asset_booked.internal_id)

    listing_booked = m.Listing(
        id="listing-pres-booked",
        asset_id=asset_booked.id,
        seller_org_id="org-fleet",
        status=ListingState.OFFER_SELECTED,
        expires_at=future(days=8),
        data={"synthetic": True},
    )
    db.add(listing_booked)
    db.flush()

    offer_booked = m.Offer(
        id="offer-pres-booked",
        listing_id=listing_booked.id,
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        price_paise=2400000,
        expires_at=future(days=8),
        status=OfferState.SELECTED,
        data={"synthetic": True, "payer_org_id": "org-refurb", "budget_paise": 300000},
    )
    db.add(offer_booked)
    db.flush()

    tx_booked = m.SaleTransaction(
        id="tx-pres-booked",
        offer_id=offer_booked.id,
        asset_id=asset_booked.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="BOOKED",
        data={"synthetic": True},
    )
    db.add(tx_booked)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-booked-1",
            transaction_id=tx_booked.id,
            version=1,
            payer_org_id="org-refurb",
            budget_paise=300000,
            price_paise=2400000,
            confirmations=["originator", "buyer"],
            data={"synthetic": True},
        )
    )

    route_booked = m.RoutePlan(
        id="route-pres-booked",
        transaction_id=tx_booked.id,
        terms_version=1,
        hub_id=None,
        distance_km=26.5,
        hours=0.88,
        estimated_cost_paise=160000,
        score=0.93,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [13.035, 77.597]],
            "stops": ["Indiranagar Fleet Hub", "RenewCell Works · Bengaluru"],
            "legs": [{"from": "Indiranagar Fleet Hub", "to": "RenewCell Works · Bengaluru", "distance_km": 26.5, "source": "HAVERSINE_X_1.3_PROXY"}],
        },
    )
    db.add(route_booked)
    db.flush()

    quote_booked = m.TransportQuote(
        id="quote-pres-booked",
        transaction_id=tx_booked.id,
        route_id=route_booked.id,
        transporter_id="trans-1",
        total_paise=160000,
        terms_version=1,
        expires_at=future(days=14),
        status=QuoteState.ACCEPTED,
        data={"synthetic": True},
    )
    db.add(quote_booked)
    db.flush()

    shipment_booked = m.Shipment(
        id="sh-pres-booked",
        transaction_id=tx_booked.id,
        route_id=route_booked.id,
        quote_id=quote_booked.id,
        state=ShipmentState.BOOKED,
        data={
            "synthetic": True,
            "handover_confirmations": {},
            "inspections": [],
        },
    )
    db.add(shipment_booked)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-booked",
            shipment_id=shipment_booked.id,
            asset_id=asset_booked.id,
            quantity=1,
            mass_kg=48.0,
            receipt="PENDING",
            data={"synthetic": True},
        )
    )

    # -------------------------------------------------------------------------
    # 10. CONSOLIDATION MANIFEST: Compatible one-hub batch proposal
    # -------------------------------------------------------------------------
    # Another booked shipment via hub for consolidation
    asset_batch2 = m.BatteryAsset(
        id="battery-pres-batch2",
        internal_id="CS-BAT-702",
        originator_org_id="org-fleet",
        owner_org_id="org-fleet",
        custodian_org_id="org-fleet",
        current_holder_org_id="org-fleet",
        chemistry=Chemistry.LFP,
        form=Form.PACK,
        condition=Condition.DEGRADED,
        mass_kg=45.0,
        quantity=1,
        lat=12.9716,
        lng=77.5946,
        authority_confirmed=True,
        state=BatteryState.IN_SHIPMENT,
        data={
            "synthetic": True,
            "flags": {f: "NO" for f in FLAGS},
            "declaration": True,
            "removal_reason": "maintenance replacement",
            "notes": "Consolidation batch partner pack for Setu Hub.",
            "handling_clearance": "ORDINARY",
            "window_start": future(days=1),
            "window_end": future(days=5),
        },
    )
    db.add(asset_batch2)
    db.flush()
    add_authority_doc(db, asset_batch2.id, "originator", asset_batch2.internal_id)

    db.add(
        m.Listing(
            id="listing-pres-batch2",
            asset_id=asset_batch2.id,
            seller_org_id="org-fleet",
            status=ListingState.OFFER_SELECTED,
            expires_at=future(days=8),
            data={"synthetic": True},
        )
    )
    db.flush()

    db.add(
        m.Offer(
            id="offer-pres-batch2",
            listing_id="listing-pres-batch2",
            buyer_org_id="org-refurb",
            facility_id="fac-refurb",
            pathway=Pathway.REPAIR_REFURBISHMENT,
            price_paise=2300000,
            expires_at=future(days=8),
            status=OfferState.SELECTED,
            data={"synthetic": True, "payer_org_id": "org-refurb", "budget_paise": 300000},
        )
    )
    db.flush()

    tx_batch2 = m.SaleTransaction(
        id="tx-pres-batch2",
        offer_id="offer-pres-batch2",
        asset_id=asset_batch2.id,
        seller_org_id="org-fleet",
        buyer_org_id="org-refurb",
        facility_id="fac-refurb",
        pathway=Pathway.REPAIR_REFURBISHMENT,
        terms_version=1,
        status=TransactionState.AGREED_PENDING_LOGISTICS,
        logistics_status="BOOKED",
        data={"synthetic": True},
    )
    db.add(tx_batch2)
    db.flush()

    db.add(
        m.TermsVersion(
            id="terms-pres-batch2-1",
            transaction_id=tx_batch2.id,
            version=1,
            payer_org_id="org-refurb",
            budget_paise=300000,
            price_paise=2300000,
            confirmations=["originator", "buyer"],
            data={"synthetic": True},
        )
    )

    route_batch2 = m.RoutePlan(
        id="route-pres-batch2",
        transaction_id=tx_batch2.id,
        terms_version=1,
        hub_id="fac-hub",
        distance_km=48.5,
        hours=3.6,
        estimated_cost_paise=290000,
        score=0.88,
        expires_at=future(days=30),
        data={
            "synthetic": True,
            "points": [[12.9716, 77.5946], [12.84, 77.66], [13.035, 77.597]],
            "stops": ["Indiranagar Fleet Hub", "Setu Hub · Electronic City", "RenewCell Works · Bengaluru"],
            "legs": [
                {"from": "Indiranagar Fleet Hub", "to": "Setu Hub · Electronic City", "distance_km": 21.0, "source": "HAVERSINE_X_1.3_PROXY"},
                {"from": "Setu Hub · Electronic City", "to": "RenewCell Works · Bengaluru", "distance_km": 27.5, "source": "HAVERSINE_X_1.3_PROXY"},
            ],
            "transporters": [{"id": "trans-1", "name": "Circular Freight", "estimated_cost_paise": 290000}],
            "hub_approved_by": "hub",
        },
    )
    db.add(route_batch2)
    db.flush()

    db.add(
        m.TransportQuote(
            id="quote-pres-batch2",
            transaction_id=tx_batch2.id,
            route_id=route_batch2.id,
            transporter_id="trans-1",
            total_paise=290000,
            terms_version=1,
            expires_at=future(days=14),
            status=QuoteState.ACCEPTED,
            data={"synthetic": True},
        )
    )
    db.flush()

    shipment_batch2 = m.Shipment(
        id="sh-pres-batch2",
        transaction_id=tx_batch2.id,
        route_id=route_batch2.id,
        quote_id="quote-pres-batch2",
        state=ShipmentState.BOOKED,
        data={"synthetic": True, "handover_confirmations": {}, "inspections": []},
    )
    db.add(shipment_batch2)
    db.flush()

    db.add(
        m.ShipmentItem(
            id="item-pres-batch2",
            shipment_id=shipment_batch2.id,
            asset_id=asset_batch2.id,
            quantity=1,
            mass_kg=45.0,
            receipt="PENDING",
            data={"synthetic": True},
        )
    )

    consolidation = m.Consolidation(
        id="con-pres-1",
        hub_id="fac-hub",
        facility_id="fac-refurb",
        transporter_id="trans-1",
        status="AWAITING_APPROVAL",
        approvals=["org-fleet", "org-refurb"],
        data={
            "synthetic": True,
            "total_mass_kg": 93.0,
            "required_org_ids": ["org-fleet", "org-refurb", "org-hub", "org-trans"],
            "notice": "Compatible hub consolidation manifest across Indiranagar to Peenya corridor via Electronic City Hub.",
        },
    )
    db.add(consolidation)
    db.flush()

    db.add(m.ConsolidationMember(consolidation_id=consolidation.id, shipment_id=shipment_booked.id))
    db.add(m.ConsolidationMember(consolidation_id=consolidation.id, shipment_id=shipment_batch2.id))

    db.commit()


def main():
    import argparse
    from .db import engine, Base

    parser = argparse.ArgumentParser(description="Seed presentation-grade data for ChakraSetu")
    parser.add_argument("--reset", action="store_true", help="Reset existing database first")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        seed_presentation_data(db)

    print("Successfully seeded presentation fixtures into ChakraSetu!")


if __name__ == "__main__":
    main()
