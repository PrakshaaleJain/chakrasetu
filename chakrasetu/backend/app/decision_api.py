"""Public non-persistent explorer and resource-authorized operational decisions."""

import json
from pathlib import Path
from fastapi import HTTPException
from threading import Lock
from time import monotonic
from sqlalchemy import select
from fastapi import APIRouter, Depends, Request
from . import models as m
from .auth import current_user, can_view_asset, role, has_role
from .db import get_db
from .common import get, fail, audit, future
from .decision_schemas import DecisionIn, ExplorerIn, OverrideIn, COMPONENTS
from .services.decision_rules import evaluate, POLICY, LABELS
from .services.decision_adapter import decision_for

router = APIRouter(tags=["pathway decision engine"])
_limits, _lock = {}, Lock()
EXPLORER_ASSUMPTIONS = json.loads(
    Path(__file__).with_name("explorer_assumptions.json").read_text()
)


def public_limit(request):
    address = request.client.host if request.client else "unknown"
    now = monotonic()
    with _lock:
        expired_keys = [k for k, (_, start) in _limits.items() if now - start > 60]
        for k in expired_keys:
            _limits.pop(k, None)
        count, start = _limits.get(address, (0, now))
        if count >= 90:
            fail(
                "EXPLORER_RATE_LIMIT",
                "Please wait a minute before evaluating more scenarios.",
                status=429,
            )
        _limits[address] = (count + 1, start)


@router.get("/public/pathway-policy")
def policy():
    from .services.registration import PBS_POLICY

    return {
        "policy": POLICY,
        "pbs_levels": PBS_POLICY,
        "pathways": LABELS,
        "cost_components": COMPONENTS,
    }


@router.post("/public/pathway-explorer")
def explorer(body: ExplorerIn, request: Request):
    public_limit(request)
    data = body.model_dump()
    context = {
        "pbs": body.pbs,
        "critical_hazard": body.critical_hazard,
        "approved": True,
        "chemistry": "LFP",
        "soh_percent": body.soh_percent if body.measurements_available else None,
        "soh_source": (
            "SCENARIO_MEASUREMENT" if body.measurements_available else "UNAVAILABLE"
        ),
        "blocking_reasons": [],
        "findings": {
            "fault_identified": body.repairable is not None,
            "repairable": body.repairable,
            "parts_available": True if body.repairable else None,
            "requalification_possible": True if body.repairable else None,
            "automotive_application_passed": (
                True
                if body.application_qualified and body.application == "VEHICLE"
                else None
            ),
            "second_life_application_passed": (
                True
                if body.application_qualified and body.application == "STATIONARY"
                else None
            ),
            "remaining_life_adequate": True if body.application_qualified else None,
        },
        "qualifications": {
            "AUTOMOTIVE": (
                True
                if body.application_qualified and body.application == "VEHICLE"
                else None
            ),
            "REFURBISHMENT": True if body.repairable else None,
            "SECOND_LIFE": (
                True
                if body.application_qualified and body.application == "STATIONARY"
                else None
            ),
        },
        "network": {
            p: {
                "complete": body.qualified_receiver
                and body.qualified_transporter
                and body.pbs not in ["L4", "L5"],
                "receivers": [],
                "stages": [],
                "rejected": (
                    []
                    if body.qualified_receiver and body.qualified_transporter
                    else [
                        {
                            "reasons": [
                                {
                                    "code": "NO_QUALIFIED_CHAIN",
                                    "message": "The selected scenario lacks a compatible receiver or transporter.",
                                }
                            ]
                        }
                    ]
                ),
            }
            for p in LABELS
        },
        "evidence_used": [
            {"type": "SCENARIO_INPUT", "source": "EXPLORER_ASSUMPTION", "inputs": data}
        ],
    }
    economics = {}
    if body.quotes_available:
        # Curated scenario assumptions, never loaded from or saved to operational data.
        for p, configured in EXPLORER_ASSUMPTIONS["pathways"].items():

            def value(amount, reference):
                return {
                    "amount_paise": amount,
                    "source": "SCENARIO_ASSUMPTION",
                    "reference": reference,
                    "recorded_at": m.now(),
                    "valid_until": future(days=1),
                    "year": 0,
                    "uncertainty_paise": 1000,
                }

            costs = {
                k: value(amount, "Explorer " + k + " assumption")
                for k, amount in configured["costs_paise"].items()
            }
            economics[p] = {
                "currency": "INR",
                "basis": "NET_TRANSACTION",
                "perspective": "WHOLE_PATHWAY",
                "horizon_years": 0,
                "discount_rate": None,
                "benefits": [
                    value(
                        configured["benefit_paise"],
                        "Explorer terminal-value assumption",
                    )
                ],
                "costs": costs,
            }
    result = evaluate(context, economics)
    return {**result, "mode": "EXPLORER", "persistent": False, "scenario_inputs": data}


def authorized_asset(db, user, id):
    asset = get(db, m.BatteryAsset, id)
    if not can_view_asset(db, user, asset):
        fail(
            "FORBIDDEN",
            "Battery decisions and evidence are private to authorized parties.",
            status=403,
        )
    return asset


def latest(db, asset):
    return db.scalar(
        select(m.PathwayDecision)
        .where(m.PathwayDecision.asset_id == asset.id)
        .order_by(m.PathwayDecision.created_at.desc(), m.PathwayDecision.id.desc())
    )


def public_result(result, user):
    # Ordinary users see explanations and provenance, not raw private snapshots.
    return (
        result
        if has_role(user, "REVIEWER")
        else {k: v for k, v in result.items() if k != "input_snapshot"}
    )


@router.get("/circularity/batteries/{id}/recommendation")
def current(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    asset = authorized_asset(db, user, id)
    last = latest(db, asset)
    inputs = last.data.get("request_inputs", {}) if last else {}
    try:
        result = decision_for(db, asset, inputs)
    except HTTPException as error:
        if not last or error.status_code not in [404, 409]:
            raise
        result = decision_for(db, asset)
        result["recalculation_warning"] = (
            "A previously referenced offer or quote is no longer usable. Request refreshed prices."
        )
    stale = bool(
        last and last.data.get("input_fingerprint") != result["input_fingerprint"]
    )
    override_record = last.data.get("override") if last else None
    if override_record:
        override_record = {
            **override_record,
            "active": not stale
            and any(
                p["pathway"] == override_record["selected_pathway"]
                and p["status"] == "FEASIBLE"
                for p in result["pathways"]
            ),
        }
    result.update(
        {
            "decision_id": last.id if last else None,
            "recorded_at": last.created_at if last else None,
            "stale": stale,
            "overrides": override_record,
        }
    )
    return public_result(result, user)


@router.post("/circularity/batteries/{id}/recommendation")
def record(
    id: str,
    body: DecisionIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    asset = authorized_asset(db, user, id)
    if user.organisation_id != asset.owner_org_id and not has_role(user, "REVIEWER"):
        fail(
            "FORBIDDEN",
            "Only the owning organization or operational reviewer may record comparison inputs.",
            status=403,
        )
    inputs = body.model_dump(mode="json")["economics"]
    if not getattr(user, "platform_admin", False) and any(
        v["source"] == "ADMIN_ASSUMPTION"
        for finance in inputs.values()
        for v in [*finance["benefits"], *finance["costs"].values()]
    ):
        fail(
            "FORBIDDEN",
            "Only a platform administrator may record administrative financial assumptions.",
            status=403,
        )
    result = decision_for(db, asset, inputs)
    result["request_inputs"] = inputs
    obj = m.PathwayDecision(asset_id=id, actor_id=user.id, data=result)
    db.add(obj)
    db.flush()
    audit(
        db,
        user,
        "battery",
        asset,
        "PATHWAY_DECISION_RECORDED",
        decision_id=obj.id,
        rule_version=result["rule_version"],
        fingerprint=result["input_fingerprint"],
    )
    return public_result({**result, "decision_id": obj.id, "stale": False}, user)


@router.get("/circularity/batteries/{id}/recommendation-history")
def history(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    asset = authorized_asset(db, user, id)
    return [
        {
            "id": d.id,
            "created_at": d.created_at,
            "actor_id": d.actor_id,
            "result": public_result(d.data, user),
        }
        for d in db.scalars(
            select(m.PathwayDecision)
            .where(m.PathwayDecision.asset_id == asset.id)
            .order_by(m.PathwayDecision.created_at.desc())
        )
        if "pathways" in d.data
    ]


@router.post("/circularity/decisions/{id}/override")
def override(
    id: str,
    body: OverrideIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    role(user, "REVIEWER")
    original = get(db, m.PathwayDecision, id)
    asset = authorized_asset(db, user, original.asset_id)
    result = decision_for(db, asset, original.data.get("request_inputs", {}))
    if not any(
        p["pathway"] == body.pathway and p["status"] == "FEASIBLE"
        for p in result["pathways"]
    ) or result["safety_state"] in ["HOLD", "SPECIALIST_REVIEW", "CRITICAL_HOLD"]:
        fail(
            "OVERRIDE_CONSTRAINT_FAILED",
            "An override cannot bypass safety, evidence, capability or technical constraints.",
        )
    result.update(
        {
            "request_inputs": original.data.get("request_inputs", {}),
            "override": {
                "original_decision_id": id,
                "selected_pathway": body.pathway,
                "reason": body.reason,
                "actor_id": user.id,
                "timestamp": m.now(),
            },
            "engine_recommended_pathway": result["recommended_pathway"],
        }
    )
    obj = m.PathwayDecision(asset_id=asset.id, actor_id=user.id, data=result)
    db.add(obj)
    db.flush()
    audit(
        db,
        user,
        "battery",
        asset,
        "RECOMMENDATION_OVERRIDE",
        decision_id=obj.id,
        original_decision_id=id,
        **body.model_dump()
    )
    return public_result({**result, "decision_id": obj.id}, user)
