"""Deterministic synthetic network. Reset only through explicit CLI --reset."""

import secrets

import argparse, hashlib
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from . import models as m
from .common import future
from .enums import FLAGS

DEMO_ACTORS = [
    ("originator", "Asha · Fleet originator", "ORIGINATOR", "org-fleet"),
    ("originator2", "Kabir · Service originator", "ORIGINATOR", "org-service"),
    ("buyer", "Meera · Refurbisher", "BUYER", "org-refurb"),
    ("recycler", "Dev · Recycler", "BUYER", "org-recycle"),
    ("secondlife", "Isha · Second-life operator", "BUYER", "org-second"),
    ("transporter", "Ravi · Transporter", "TRANSPORTER", "org-trans"),
    ("transporter2", "Noor · Transporter", "TRANSPORTER", "org-trans2"),
    ("hub", "Neel · Hub operator", "HUB", "org-hub"),
    ("specialist", "Anil · Controlled handling operator", "BUYER", "org-review"),
    (
        "specialtrans",
        "Farah · Controlled handling transporter",
        "TRANSPORTER",
        "org-specialtrans",
    ),
    ("reviewer", "Priya · Network reviewer", "REVIEWER", "org-review"),
]


def seed(db):
    if db.get(m.Organisation, "org-fleet"):
        from .circular_seed import seed_circular

        seed_circular(db)
        from .registration_seed import seed_acceptance

        seed_acceptance(db)
        return
    orgs = [
        ("org-fleet", "Setu Fleet Collective", "ORIGINATOR"),
        ("org-service", "Urban Cell Service", "ORIGINATOR"),
        ("org-refurb", "RenewCell Works", "BUYER"),
        ("org-recycle", "Loop Materials", "BUYER"),
        ("org-second", "Second Current", "BUYER"),
        ("org-trans", "Circular Freight", "TRANSPORTER"),
        ("org-trans2", "Green Mile Logistics", "TRANSPORTER"),
        ("org-hub", "Setu Aggregation Hub", "HUB"),
        ("org-review", "Qualified Review Partner", "REVIEWER"),
        ("org-incompatible", "LeadLoop Works", "BUYER"),
        ("org-specialtrans", "Scoped Freight Partner", "TRANSPORTER"),
    ]
    for id, name, role in orgs:
        db.add(
            m.Organisation(
                id=id,
                name=name,
                role=role,
                verification="VERIFIED",
                synthetic=True,
                data={
                    "status": "ACTIVE",
                    "mock_registration": "SYNTHETIC-NOT-A-LICENCE",
                    "address": "Synthetic operating address, Bengaluru",
                },
            )
        )
    db.flush()
    for id, name, role, org in DEMO_ACTORS:
        db.add(
            m.User(
                id=id,
                name=name,
                role=role,
                organisation_id=org,
                token_hash="disabled-" + secrets.token_hex(32),
                data={"synthetic": True},
            )
        )
    facilities = [
        (
            "fac-refurb",
            "org-refurb",
            "RenewCell · Bengaluru",
            "RECEIVER",
            13.035,
            77.597,
            "REPAIR_REFURBISHMENT",
            ["LFP", "NMC"],
            1200,
        ),
        (
            "fac-recycle",
            "org-recycle",
            "Loop Materials · Hosur",
            "RECEIVER",
            12.74,
            77.83,
            "RECYCLING",
            ["LFP", "NMC", "NCA"],
            3000,
        ),
        (
            "fac-second",
            "org-second",
            "Second Current · Mysuru",
            "RECEIVER",
            12.30,
            76.65,
            "SECOND_LIFE_ASSESSMENT",
            ["LFP"],
            500,
        ),
        (
            "fac-incompatible",
            "org-incompatible",
            "LeadLoop · Bengaluru",
            "RECEIVER",
            13.06,
            77.49,
            "RECYCLING",
            ["lead-acid"],
            800,
        ),
        (
            "fac-hub",
            "org-hub",
            "Setu Hub · Electronic City",
            "HUB",
            12.84,
            77.66,
            "REPAIR_REFURBISHMENT",
            ["LFP", "NMC"],
            1000,
        ),
        (
            "fac-closed",
            "org-refurb",
            "RenewCell · Closed satellite",
            "RECEIVER",
            13.06,
            77.55,
            "REPAIR_REFURBISHMENT",
            ["LFP"],
            100,
        ),
        (
            "fac-expired",
            "org-recycle",
            "Loop Materials · Expired mock registration",
            "RECEIVER",
            12.9,
            77.65,
            "RECYCLING",
            ["LFP", "NMC"],
            300,
        ),
        (
            "fac-review",
            "org-review",
            "Qualified Review Partner",
            "REVIEW",
            12.97,
            77.59,
            "QUALIFIED_REVIEW",
            ["UNKNOWN", "LFP", "NMC"],
            200,
        ),
    ]
    for id, org, name, kind, lat, lng, path, chem, capacity in facilities:
        db.add(
            m.Facility(
                id=id,
                organisation_id=org,
                name=name,
                kind=kind,
                lat=lat,
                lng=lng,
                active=id != "fac-closed",
                registration="EXPIRED" if id == "fac-expired" else "VERIFIED",
                valid_until=(
                    future(minutes=-1) if id == "fac-expired" else future(days=365)
                ),
                data={
                    "synthetic": True,
                    "window_start": future(minutes=1),
                    "window_end": future(days=90),
                    "handling_scope": "ORDINARY" if kind != "REVIEW" else "REVIEW_ONLY",
                    "hub_fee_paise": 20000 if kind == "HUB" else 0,
                    "dwell_hours": 2 if kind == "HUB" else 0,
                },
            )
        )
        db.flush()
        for pathway in (
            [path, "RECYCLING", "SECOND_LIFE_ASSESSMENT"] if kind == "HUB" else [path]
        ):
            db.add(
                m.FacilityCapability(
                    id=id + "-" + pathway,
                    facility_id=id,
                    pathway=pathway,
                    verification="VERIFIED",
                    capacity_kg=capacity,
                    available_kg=0 if id == "fac-second" else capacity,
                    valid_until=future(days=365),
                    data={
                        "declared_chemistries": chem,
                        "verified_chemistries": chem,
                        "forms": (
                            ["PACK", "MODULE", "UNKNOWN"]
                            if kind == "REVIEW"
                            else ["PACK", "MODULE"]
                        ),
                        "conditions": (
                            [
                                "WORKING",
                                "DEGRADED",
                                "NON_FUNCTIONAL",
                                "DAMAGED_REPORTED",
                                "UNKNOWN",
                            ]
                            if kind == "REVIEW"
                            else ["WORKING", "DEGRADED", "NON_FUNCTIONAL"]
                        ),
                        "handling_scope": (
                            "CONTROLLED_HANDLING" if kind == "REVIEW" else "ORDINARY"
                        ),
                        "required_docs": ["TRANSFER_AUTHORITY"],
                        "synthetic": True,
                    },
                )
            )
    for id, org, name, cap, rate in [
        ("trans-1", "org-trans", "Circular Freight", 1500, 1800),
        ("trans-2", "org-trans2", "Green Mile Logistics", 700, None),
        ("trans-special", "org-specialtrans", "Scoped Freight Partner", 250, 3500),
    ]:
        db.add(
            m.TransporterProfile(
                id=id,
                organisation_id=org,
                name=name,
                verification="VERIFIED",
                capacity_kg=cap,
                valid_until=future(days=365),
                data={
                    "synthetic": True,
                    "handling_scope": (
                        "CONTROLLED_HANDLING" if id == "trans-special" else "ORDINARY"
                    ),
                    "chemistries": (
                        ["LFP", "NMC", "NCA", "UNKNOWN"]
                        if id == "trans-special"
                        else ["LFP", "NMC", "NCA"]
                    ),
                    "forms": ["PACK", "MODULE"],
                    "center": [12.97, 77.59],
                    "radius_km": 250,
                    "window_start": future(minutes=1),
                    "window_end": future(days=90),
                    "rate_paise_per_km": rate,
                    "fixed_paise": 50000,
                    "rate_source": (
                        "SYNTHETIC_CONFIGURED_RATE_CARD" if rate else "UNKNOWN"
                    ),
                },
            )
        )
    db.flush()
    for id, internal, chem, mass, flags, org in [
        ("battery-1", "CS-BLR-001", "LFP", 42, {f: "NO" for f in FLAGS}, "org-fleet"),
        (
            "battery-2",
            "CS-BLR-002",
            "UNKNOWN",
            None,
            {f: "NO" for f in FLAGS},
            "org-fleet",
        ),
        (
            "battery-3",
            "CS-SVC-003",
            "NMC",
            36,
            {f: ("YES" if f == "swelling" else "NO") for f in FLAGS},
            "org-service",
        ),
    ]:
        asset = m.BatteryAsset(
            id=id,
            internal_id=internal,
            originator_org_id=org,
            owner_org_id=org,
            custodian_org_id=org,
            current_holder_org_id=org,
            chemistry=chem,
            form="PACK",
            condition="DEGRADED",
            mass_kg=mass,
            quantity=1,
            lat=12.9716,
            lng=77.5946,
            authority_confirmed=True,
            data={
                "synthetic": True,
                "flags": flags,
                "declaration": True,
                "removal_reason": "degradation",
                "address": "Synthetic pickup · Bengaluru",
                "window_start": future(days=1),
                "window_end": future(days=3),
                "provenance": "SELF_DECLARED",
                "recorded_by": "originator",
                "recorded_at": m.now(),
                "notes": "Fictional demo battery; no safety certification.",
            },
        )
        db.add(asset)
        db.flush()
        db.add(
            m.EvidenceDocument(
                asset_id=id,
                uploader_id="originator" if org == "org-fleet" else "originator2",
                kind="TRANSFER_AUTHORITY",
                filename="synthetic-authority.txt",
                checksum=hashlib.sha256(b"Synthetic transfer authority").hexdigest(),
                version=1,
                review_status="VERIFIED",
                data={
                    "synthetic": True,
                    "reference": "Mock ownership and transfer mandate; not a legal record",
                    "visibility": "PARTIES",
                },
            )
        )
    if not db.get(m.SchemaVersion, 5):
        for old in db.scalars(select(m.SchemaVersion)):
            db.delete(old)
        db.add(m.SchemaVersion(version=5))
    db.commit()
    from .services.intake import screen

    for id in ["battery-1", "battery-2", "battery-3"]:
        screen(
            db,
            db.get(m.BatteryAsset, id),
            db.get(m.User, "originator" if id != "battery-3" else "originator2"),
        )
    db.commit()

    from .circular_seed import seed_circular

    seed_circular(db)
    from .registration_seed import seed_acceptance

    seed_acceptance(db)


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--reset", action="store_true")
    opts = args.parse_args()
    if opts.reset:
        Base.metadata.drop_all(engine)
    from .migrations import migrate

    migrate(engine)
    with SessionLocal() as db:
        seed(db)
    print("Synthetic demo database initialised (schema v5).")


if __name__ == "__main__":
    main()
