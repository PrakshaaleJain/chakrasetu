"""Deterministic complete-pathway planning. Estimates remain recommendations."""

from itertools import product, islice
from sqlalchemy import select
from .. import models as m
from ..common import dump, expired, get
from .circularity import capability_check
from .matching import distance, handling_scope

DEFINITIONS = {
    "SECOND_LIFE": [
        ("ASSESSMENT", None),
        ("REFURBISHMENT", None),
        ("INTEGRATION", "REFURBISHED_PACK"),
        ("DEPLOYMENT", "SECOND_LIFE_SYSTEM"),
    ],
    "RECOVER_MATERIALS": [
        ("RECYCLING", None),
        ("REFINING", "BLACK_MASS"),
        ("MANUFACTURING", "REFINED_LITHIUM"),
    ],
    "DISMANTLE_PROCESS": [
        ("DISMANTLING", None),
        ("PROCESSING", "COPPER"),
        ("MANUFACTURING", "COPPER"),
    ],
}
ECONOMIC_KEYS = (
    "terminal_revenue_paise",
    "acquisition_paise",
    "assessment_paise",
    "processing_paise",
    "transport_paise",
    "overhead_paise",
)


def plan(db, asset, inputs):
    from .decision_adapter import decision_for

    evaluation = decision_for(db, asset)
    candidates = []
    rejected = []
    from .registration import routing_reasons

    global_reasons = routing_reasons(asset)
    if (
        asset.state
        in ["HOLD", "DISPUTED", "DRAFT", "REVIEW_REQUIRED", "NEEDS_INFORMATION"]
        or handling_scope(asset) != "ORDINARY"
    ):
        global_reasons.append(
            {
                "code": "SAFETY_REVIEW_REQUIRED",
                "message": "Ordinary pathways require completed screening and resolved handling evidence.",
            }
        )
    if not asset.authority_confirmed:
        global_reasons.append(
            {
                "code": "AUTHORITY_REQUIRED",
                "message": "Transfer authority must be confirmed with reviewed evidence.",
            }
        )
    docs = db.scalars(
        select(m.EvidenceDocument).where(m.EvidenceDocument.asset_id == asset.id)
    ).all()
    if not any(
        x.kind == "TRANSFER_AUTHORITY" and x.review_status == "VERIFIED" for x in docs
    ):
        global_reasons.append(
            {
                "code": "DOCUMENT_MISSING",
                "message": "Reviewed transfer-authority evidence is required.",
            }
        )
    if asset.lat is None or asset.lng is None:
        global_reasons.append(
            {
                "code": "LOCATION_UNKNOWN",
                "message": "Pickup coordinates required for distance estimates.",
            }
        )
    facilities = db.scalars(select(m.Facility).order_by(m.Facility.id)).all()
    evidence = [
        {
            "type": "DOCUMENT",
            "id": x.id,
            "status": x.review_status,
            "provenance": x.data.get("synthetic")
            and "SYNTHETIC"
            or "EXTERNAL_DOCUMENT",
        }
        for x in docs
    ]
    reports = db.scalars(
        select(m.Assessment).where(m.Assessment.asset_id == asset.id)
    ).all()
    evidence.extend(
        {
            "type": "ASSESSMENT",
            "id": x.id,
            "status": x.state,
            "intended_operation": x.intended_operation,
            "valid_until": x.valid_until,
            "provenance": x.data.get("source"),
        }
        for x in reports
    )
    for key, stages in DEFINITIONS.items():
        alternatives = []
        for op, category in stages:
            choices = []
            for f in facilities:
                if op == "DEPLOYMENT":
                    reasons = []
                    if (
                        not f.active
                        or f.registration != "VERIFIED"
                        or expired(f.valid_until)
                        or get(db, m.Organisation, f.organisation_id).verification
                        != "VERIFIED"
                    ):
                        reasons.append(
                            {
                                "code": "RECEIVER_UNQUALIFIED",
                                "message": "Deployment receiving organization and facility must be verified and current.",
                            }
                        )
                    if get(
                        db, m.Organisation, f.organisation_id
                    ).role != "CUSTOMER" or category not in f.data.get(
                        "verified_receiving_categories", []
                    ):
                        reasons.append(
                            {
                                "code": "CUSTOMER_SPEC_UNSUPPORTED",
                                "message": "No qualified deployment customer for the intended product specification.",
                            }
                        )
                    validity = f.data.get("receiving_scope_review", {}).get(
                        "valid_until"
                    )
                    if not validity or expired(validity):
                        reasons.append(
                            {
                                "code": "RECEIVING_SCOPE_EXPIRED",
                                "message": "Current application-specific customer qualification required.",
                            }
                        )
                    if (
                        asset.mass_kg is None
                        or f.data.get("receiving_capacity_kg") is None
                        or f.data["receiving_capacity_kg"] < asset.mass_kg
                    ):
                        reasons.append(
                            {
                                "code": "CAPACITY_UNKNOWN_OR_INSUFFICIENT",
                                "message": "Known deployment receiving capacity required.",
                            }
                        )
                else:
                    reasons = capability_check(
                        db,
                        f,
                        op,
                        asset.mass_kg,
                        asset.chemistry if category is None else None,
                        asset.form if category is None else None,
                        category,
                        asset=asset if category is None else None,
                    )
                if reasons:
                    rejected.append(
                        {
                            "pathway": key,
                            "operation": op,
                            "facility_id": f.id,
                            "reasons": reasons,
                        }
                    )
                else:
                    choices.append(
                        {
                            "operation": op,
                            "facility_id": f.id,
                            "organisation_id": f.organisation_id,
                            "name": f.name,
                            "lat": f.lat,
                            "lng": f.lng,
                            "required_incoming_category": category,
                            "constraints": [
                                {
                                    "code": "IDENTITY_SCOPE_CAPACITY_VALID",
                                    "passed": True,
                                }
                            ],
                        }
                    )
            alternatives.append(choices)
        if global_reasons or any(not x for x in alternatives):
            rejected.append(
                {
                    "pathway": key,
                    "reasons": global_reasons
                    or [
                        {
                            "code": "INCOMPLETE_DOWNSTREAM_CHAIN",
                            "message": "No qualified facility covers at least one required stage.",
                        }
                    ],
                }
            )
            continue
        for chain in islice(product(*alternatives), 100):
            conditions = []
            # Future outputs remain subject to actual measurement and receiver acceptance.
            for op, _ in stages:
                if op in ["REFURBISHMENT", "INTEGRATION"]:
                    if not any(
                        a.state == "ACCEPTED"
                        and a.intended_operation == op
                        and a.valid_until
                        and not expired(a.valid_until)
                        and a.data.get("report", {}).get("outcome")
                        == "SUITABLE_FOR_DEFINED_OPERATION"
                        and not db.scalar(
                            select(m.Assessment).where(m.Assessment.revision_of == a.id)
                        )
                        for a in reports
                    ):
                        conditions.append(
                            {
                                "code": "ASSESSMENT_REQUIRED",
                                "message": f"{op} requires an accepted assessment against its defined technical specification before execution.",
                            }
                        )
            conditions.append(
                {
                    "code": "DOWNSTREAM_OUTPUT_ACCEPTANCE_REQUIRED",
                    "message": "Projected output category and yield are assumptions. Actual output composition, product specifications and receiving acceptance must be documented stage by stage.",
                }
            )
            coords = [[asset.lat, asset.lng]] + [[x["lat"], x["lng"]] for x in chain]
            km = round(sum(distance(a, b) * 1.3 for a, b in zip(coords, coords[1:])), 2)
            econ = inputs.get(key, {})
            missing = [k for k in ECONOMIC_KEYS if econ.get(k) is None]
            net = (
                None
                if missing
                else econ["terminal_revenue_paise"]
                - sum(econ[k] for k in ECONOMIC_KEYS if k != "terminal_revenue_paise")
            )
            candidates.append(
                {
                    "id": key + "|" + ",".join(x["facility_id"] for x in chain),
                    "pathway": key,
                    "stages": list(chain),
                    "status": "TECHNICALLY_CONDITIONAL",
                    "constraints": [
                        {
                            "code": "SCREENING_AUTHORITY_VERIFICATION_CAPACITY",
                            "passed": True,
                        }
                    ],
                    "conditions": conditions,
                    "distance_km": km,
                    "distance_source": "HAVERSINE_X_1.3_PROXY",
                    "economics": {
                        "inputs": econ,
                        "missing": missing,
                        "net_paise": net,
                        "cost_per_battery_paise": (
                            None
                            if missing
                            else sum(
                                econ[k]
                                for k in ECONOMIC_KEYS
                                if k != "terminal_revenue_paise"
                            )
                            / asset.quantity
                        ),
                        "net_per_battery_paise": (
                            None if net is None else net / asset.quantity
                        ),
                        "source": econ.get("source", "UNKNOWN"),
                        "complete": not missing,
                        "perspective": "Whole-pathway terminal revenue minus explicit acquisition, assessment, processing, transport and overhead costs; intermediate internal transfers excluded.",
                    },
                    "warnings": [
                        "Facility scope does not prove output specification; downstream receiving acceptance and actual material yield remain conditional.",
                        "No capacity reserved, quote accepted, contract signed or operation executed by this recommendation.",
                    ],
                }
            )
    # Never promote failed constraints or missing costs through scoring.
    candidates.sort(
        key=lambda x: (
            x["status"] == "TECHNICALLY_CONDITIONAL",
            not x["economics"]["complete"],
            (
                -x["economics"]["net_paise"]
                if x["economics"]["net_paise"] is not None
                else 0
            ),
            x["distance_km"],
            x["id"],
        )
    )
    readiness = {p["pathway"]: p["status"] for p in evaluation["pathways"]}
    mapping = {
        "SECOND_LIFE": "SECOND_LIFE",
        "RECOVER_MATERIALS": "RECYCLING",
        "DISMANTLE_PROCESS": "RECYCLING",
    }
    complete = [
        x
        for x in candidates
        if x["economics"]["complete"]
        and readiness.get(mapping[x["pathway"]]) == "FEASIBLE"
    ]
    return {
        "generated_at": m.now(),
        "rule_version": "circular-pathway-2",
        "asset_id": asset.id,
        "evaluation": evaluation,
        "evidence_used": evidence,
        "candidates": candidates,
        "rejected": rejected,
        "recommended_id": complete[0]["id"] if complete else None,
        "recommendation_reason": (
            "Among candidates passing all hard constraints, rank conditional technical readiness first, then complete estimated net value descending, then proxy distance and stable identifier. Conditional recommendation still requires the listed evidence."
            if complete
            else "No economic recommendation: complete explicit economic inputs are missing or no qualified complete pathway exists."
        ),
        "ranking_configuration": {
            "hard_constraints_before_ranking": True,
            "keys": [
                "technical_conditions",
                "economic_completeness",
                "net_value_desc",
                "proxy_distance_asc",
                "stable_id",
            ],
        },
        "synthetic": asset.data.get("synthetic", False),
    }
