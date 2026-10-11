"""Additional fictional supply-chain participants; no real verification claims."""

from . import models as m
from .common import future


def seed_circular(db):
    extra = [
        ("processor", "PROCESSOR", "Setu Material Processing", 12.90, 77.64),
        ("refiner", "REFINER", "ReLoop Refining", 13.07, 77.68),
        (
            "manufacturer",
            "MANUFACTURER",
            "CycleWorks Manufacturing",
            13.11,
            77.70,
        ),
        ("customer", "CUSTOMER", "Setu Storage Operations", 12.92, 77.55),
    ]
    for id, r, name, lat, lng in extra:
        org_id = "org-" + id
        if not db.get(m.Organisation, org_id):
            db.add(
                m.Organisation(
                    id=org_id,
                    name=name,
                    role=r,
                    verification="VERIFIED",
                    synthetic=True,
                    data={
                        "synthetic": True,
                        "verification_evidence": "Fictional demonstration registration; not verified in a real registry",
                    },
                )
            )
            db.flush()
            db.add(
                m.User(
                    id=id,
                    organisation_id=org_id,
                    name=name + " operator",
                    role="BUYER",
                    token_hash="disabled-synthetic-account",
                    data={"synthetic": True},
                )
            )
            db.add(
                m.Facility(
                    id="fac-" + id,
                    organisation_id=org_id,
                    name=name,
                    kind="RECEIVER",
                    lat=lat,
                    lng=lng,
                    registration="VERIFIED",
                    active=True,
                    valid_until=future(days=365),
                    data={
                        "synthetic": True,
                        "verified_receiving_categories": [
                            "SECOND_LIFE_SYSTEM",
                            "REFURBISHED_PACK",
                        ],
                        "receiving_capacity_kg": 1000,
                        "receiving_scope_review": {
                            "valid_until": future(days=365),
                            "evidence": "Synthetic product receiving qualification",
                        },
                    },
                )
            )
            db.flush()
    if not db.get(m.User, "technician"):
        db.add(
            m.User(
                id="technician",
                organisation_id="org-refurb",
                name="RenewCell Diagnostics",
                role="TECHNICIAN",
                token_hash="disabled-synthetic-account",
                data={"synthetic": True},
            )
        )
        db.flush()
    operations = [
        ("fac-review", "ASSESSMENT"),
        ("fac-refurb", "ASSESSMENT"),
        ("fac-refurb", "REFURBISHMENT"),
        ("fac-second", "INTEGRATION"),
        ("fac-second", "REPURPOSING"),
        ("fac-recycle", "RECYCLING"),
        ("fac-recycle", "DISMANTLING"),
        ("fac-processor", "PROCESSING"),
        ("fac-refiner", "REFINING"),
        ("fac-manufacturer", "MANUFACTURING"),
    ]
    for fid, op in operations:
        id = fid + "-" + op
        if not db.get(m.OperationCapability, id):
            db.add(
                m.OperationCapability(
                    id=id,
                    facility_id=fid,
                    operation=op,
                    verified=True,
                    capacity_kg=1000,
                    valid_until=future(days=365),
                    chemistries=["LFP", "NMC", "NCA"],
                    formats=["PACK", "MODULE"],
                    material_categories=[
                        "BLACK_MASS",
                        "COPPER",
                        "ALUMINIUM",
                        "REFINED_LITHIUM",
                        "SECOND_LIFE_SYSTEM",
                        "REFURBISHED_PACK",
                    ],
                    data={
                        "synthetic": True,
                        "verification_evidence": "Fictional scoped operation qualification; no real permit",
                    },
                )
            )
    f = db.get(m.Facility, "fac-second")
    f.data = {
        **f.data,
        "verified_receiving_categories": ["SECOND_LIFE_SYSTEM", "REFURBISHED_PACK"],
        "receiving_capacity_kg": 1000,
        "receiving_scope_review": {
            "valid_until": future(days=365),
            "evidence": "Fictional scope",
        },
    }
    t = db.get(m.TransporterProfile, "trans-1")
    t.data = {
        **t.data,
        "verified_downstream_kinds": ["PRODUCT", "MATERIAL"],
        "verified_downstream_categories": [
            "BLACK_MASS",
            "COPPER",
            "ALUMINIUM",
            "REFINED_LITHIUM",
            "SECOND_LIFE_SYSTEM",
            "REFURBISHED_PACK",
        ],
        "downstream_scope_review": {
            "valid_until": future(days=365),
            "evidence": "Synthetic qualified material/product handling scope",
        },
    }
    from .organisation_seed import seed_profiles
    seed_profiles(db)
    db.commit()
