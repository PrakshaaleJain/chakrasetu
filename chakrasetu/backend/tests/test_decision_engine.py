from copy import deepcopy
from datetime import datetime, timezone
import json
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from app.db import get_db
from app.main import app
from app.common import future
from app.decision_schemas import COMPONENTS, DecisionIn
from app.services.decision_rules import evaluate, load_policy
from app.services.decision_adapter import decision_for
from test_intake_commercial import auth
from test_registration_redesign import create, review


def context(**changes):
    return {
        "pbs": "L1",
        "approved": True,
        "chemistry": "LFP",
        "soh_percent": 85,
        "soh_source": "QUALIFIED_ASSESSMENT",
        "qualifications": {
            "AUTOMOTIVE": True,
            "REFURBISHMENT": True,
            "SECOND_LIFE": True,
        },
        "findings": {
            "automotive_application_passed": True,
            "second_life_application_passed": True,
            "remaining_life_adequate": True,
            "fault_identified": True,
            "repairable": True,
            "parts_available": True,
            "requalification_possible": True,
        },
        "network": {
            p: {"complete": True, "receivers": [], "stages": [], "rejected": []}
            for p in COMPONENTS
        },
        **changes,
    }


def amount(value=100, **changes):
    return {
        "amount_paise": value,
        "source": "OWNER_ESTIMATE",
        "reference": "Documented allowance",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "valid_until": future(days=10),
        "year": 0,
        "uncertainty_paise": 0,
        **changes,
    }


def finance(path="REFURBISHMENT", benefit=10000, **changes):
    return {
        "currency": "INR",
        "basis": "NET_TRANSACTION",
        "perspective": "WHOLE_PATHWAY",
        "horizon_years": 0,
        "discount_rate": None,
        "benefits": [amount(benefit)],
        "costs": {k: amount() for k in COMPONENTS[path]},
        **changes,
    }


def get_path(result, path):
    return next(p for p in result["pathways"] if p["pathway"] == path)


@pytest.mark.parametrize(
    "pbs,expected",
    [
        ("L1", "ORDINARY_EVALUATION"),
        ("L2", "ORDINARY_EVALUATION"),
        ("L3", "RESTRICTED"),
        ("L4", "SPECIALIST_REVIEW"),
        ("L5", "CRITICAL_HOLD"),
    ],
)
def test_safety_before_value(pbs, expected):
    result = evaluate(context(pbs=pbs), {"REFURBISHMENT": finance()})
    assert result["safety_state"] == expected
    if pbs in ["L4", "L5"]:
        assert result["recommended_pathway"] is None
        assert not get_path(result, "REFURBISHMENT")["economics"]["ranking_eligible"]
    else:
        assert result["recommended_pathway"] == "REFURBISHMENT"


def test_high_soh_critical_contradiction_never_ranks():
    result = evaluate(
        context(pbs="L1", soh_percent=100, critical_hazard=True),
        {"AUTOMOTIVE": finance("AUTOMOTIVE", 10**10)},
    )
    assert (
        result["safety_state"] == "CRITICAL_HOLD"
        and result["recommended_pathway"] is None
    )
    assert all(p["status"] == "HOLD" for p in result["pathways"])


@pytest.mark.parametrize(
    "value,source", [(None, "UNAVAILABLE"), (85, "OWNER_ESTIMATE")]
)
def test_missing_or_unreliable_soh_not_zero_or_qualified(value, source):
    result = evaluate(context(soh_percent=value, soh_source=source))
    assert result["soh"]["screening_band"] == "UNAVAILABLE"
    assert get_path(result, "AUTOMOTIVE")["status"] == "INFORMATION_REQUIRED"
    assert result["soh"]["value"] == value
    assert get_path(result, "RECYCLING")["status"] == "FEASIBLE"


def test_low_soh_is_not_automatic_disposal():
    result = evaluate(
        context(soh_percent=35),
        {
            "REFURBISHMENT": finance(benefit=50000),
            "RECYCLING": finance("RECYCLING", 1000),
        },
    )
    assert result["recommended_pathway"] == "REFURBISHMENT"
    assert get_path(result, "SECOND_LIFE")["status"] == "FEASIBLE"


def test_reported_measurement_cannot_replace_accepted_application_evidence():
    result = evaluate(
        context(soh_source="OWNER_REPORTED_MEASUREMENT", qualifications={})
    )
    assert get_path(result, "AUTOMOTIVE")["status"] == "INFORMATION_REQUIRED"


def test_known_unsuitable_distinct_from_missing_evidence():
    c = context()
    c["findings"]["repairable"] = False
    known = evaluate(c)
    c["findings"]["repairable"] = None
    unknown = evaluate(c)
    assert get_path(known, "REFURBISHMENT")["status"] == "EXCLUDED"
    assert get_path(unknown, "REFURBISHMENT")["status"] == "INFORMATION_REQUIRED"


def test_configurable_bands_without_changing_qualifications(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "version": "custom-1",
                "automotive_screen_soh": 90,
                "second_life_screen_soh": 70,
                "economic_tie_paise": 10,
            }
        )
    )
    policy = load_policy(path)
    result = evaluate(context(soh_percent=85), policy=policy)
    assert (
        result["soh"]["screening_band"] == "MID"
        and result["rule_version"] == "custom-1"
    )
    path.write_text(json.dumps({**policy, "second_life_screen_soh": 95}))
    with pytest.raises(RuntimeError):
        load_policy(path)


def test_missing_financial_components_and_expired_estimates():
    f = finance()
    del f["costs"]["transport"]
    result = evaluate(context(), {"REFURBISHMENT": f})
    assert "transport" in get_path(result, "REFURBISHMENT")["economics"]["missing"]
    assert result["recommended_pathway"] is None
    f = finance()
    f["benefits"][0]["valid_until"] = future(days=-1)
    assert not get_path(evaluate(context(), {"REFURBISHMENT": f}), "REFURBISHMENT")[
        "economics"
    ]["complete"]


def test_net_components_and_npv():
    f = finance()
    result = evaluate(context(), {"REFURBISHMENT": f})
    assert get_path(result, "REFURBISHMENT")["economics"]["net_paise"] == 9300
    f.update(basis="NPV", horizon_years=2, discount_rate=0.1)
    f["benefits"][0]["year"] = 2
    result = evaluate(context(), {"REFURBISHMENT": f})
    assert get_path(result, "REFURBISHMENT")["economics"]["net_paise"] == round(
        10000 / 1.1**2 - 700
    )


@pytest.mark.parametrize(
    "field,value", [("basis", "NPV"), ("perspective", "ORIGINATOR_TRANSACTION")]
)
def test_incompatible_comparison_bases_not_ranked(field, value):
    other = finance("RECYCLING")
    other[field] = value
    if field == "basis":
        other.update(horizon_years=2, discount_rate=0.1)
    result = evaluate(context(), {"REFURBISHMENT": finance(), "RECYCLING": other})
    assert result["recommended_pathway"] is None and not result["ranking"]["comparable"]


def test_uncertainty_overlap_has_no_false_winner():
    a, b = finance(benefit=10000), finance("RECYCLING", 9000)
    a["benefits"][0]["uncertainty_paise"] = 3000
    result = evaluate(context(), {"REFURBISHMENT": a, "RECYCLING": b})
    assert (
        result["recommended_pathway"] is None and len(result["similar_pathways"]) == 2
    )


def test_unqualified_chain_with_huge_value_excluded():
    c = context()
    c["network"]["REFURBISHMENT"]["complete"] = False
    result = evaluate(
        c, {"REFURBISHMENT": finance(benefit=10**10), "RECYCLING": finance("RECYCLING")}
    )
    assert result["recommended_pathway"] == "RECYCLING"
    assert not get_path(result, "REFURBISHMENT")["economics"]["ranking_eligible"]


def test_schema_rejects_double_counts_wrong_currency_and_forged_actual_quote():
    f = finance()
    with pytest.raises(ValueError):
        DecisionIn(economics={"REFURBISHMENT": {**f, "currency": "USD"}})
    f["benefits"][0]["source"] = "ACTUAL_QUOTE"
    with pytest.raises(ValueError):
        DecisionIn(economics={"REFURBISHMENT": f})
    f = finance()
    with pytest.raises(ValueError):
        DecisionIn(economics={"REFURBISHMENT": {**f, "offer_id": "other"}})
    with pytest.raises(ValueError):
        DecisionIn(economics={"REFURBISHMENT": {**f, "transport_quote_id": "other"}})
    f["costs"]["parts_alias"] = amount()
    with pytest.raises(ValueError):
        DecisionIn(economics={"REFURBISHMENT": f})


def test_public_explorer_no_private_data_or_writes(client):
    with next(app.dependency_overrides[get_db]()) as db:
        before = {
            table: len(db.scalars(select(table)).all())
            for table in [m.BatteryAsset, m.PathwayDecision, m.AuditEvent]
        }
    response = client.post(
        "/public/pathway-explorer", json={"pbs": "L1", "quotes_available": True}
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["persistent"] is False and "input_snapshot" not in result
    assert not any(
        x in response.text
        for x in ["org-origin", "fac-refurb", "battery-1", "token_hash", "contacts"]
    )
    with next(app.dependency_overrides[get_db]()) as db:
        assert before == {
            table: len(db.scalars(select(table)).all()) for table in before
        }
    policy = client.get("/public/pathway-policy").json()
    assert len(policy["pbs_levels"]) == 5


def test_explorer_and_shared_engine_same_results(client):
    body = {"pbs": "L5", "soh_percent": 100, "quotes_available": True}
    result = client.post("/public/pathway-explorer", json=body).json()
    pure = evaluate(context(pbs="L5", soh_percent=100))
    assert (
        result["recommended_pathway"] == pure["recommended_pathway"]
        and result["safety_state"] == pure["safety_state"]
    )
    missing = client.post(
        "/public/pathway-explorer",
        json={"measurements_available": False, "application_qualified": False},
    ).json()
    assert (
        missing["soh"]["value"] is None
        and missing["soh"]["screening_band"] == "UNAVAILABLE"
    )


@pytest.mark.real_auth
def test_new_private_endpoints_require_authentication(client):
    for path in [
        "/circularity/batteries/battery-1/recommendation",
        "/circularity/batteries/battery-1/recommendation-history",
    ]:
        assert client.get(path).status_code == 401
    assert (
        client.post(
            "/circularity/batteries/battery-1/recommendation", json={}
        ).status_code
        == 401
    )
    assert client.get("/public/pathway-policy").status_code == 200


def test_organization_id_tampering_and_role_restrictions(client):
    for path in ["recommendation", "recommendation-history"]:
        assert (
            client.get(
                "/circularity/batteries/battery-3/" + path, headers=auth("originator")
            ).status_code
            == 403
        )
    assert (
        client.post(
            "/circularity/batteries/battery-3/recommendation",
            headers=auth("originator"),
            json={},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/circularity/batteries/battery-1/recommendation",
            headers=auth("transporter"),
            json={},
        ).status_code
        == 403
    )


def test_pending_stays_hold_after_preview_and_record(client):
    asset, _ = create(
        client,
        pbs="L1",
        chemistry="LFP",
        mass_kg=42,
        condition="DEGRADED",
        window_start=future(days=1),
        window_end=future(days=3),
    )
    response = client.post(
        "/circularity/batteries/" + asset["id"] + "/recommendation",
        headers=auth("originator"),
        json={},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert (
        result["recommended_pathway"] is None and result["evaluation_state"] == "HOLD"
    )
    stored = client.get("/batteries/" + asset["id"], headers=auth("originator")).json()
    assert stored["data"]["registration"]["status"] == "PENDING_REVIEW"
    assert (
        client.post(
            "/listings",
            headers=auth("originator"),
            json={"asset_id": asset["id"], "expires_at": future(days=4)},
        ).status_code
        == 409
    )


def test_decision_history_recalculation_and_scoped_override(client):
    asset, _ = create(
        client,
        pbs="L1",
        chemistry="LFP",
        mass_kg=42,
        condition="DEGRADED",
        window_start=future(days=1),
        window_end=future(days=3),
    )
    assert review(client, asset["id"]).status_code == 200
    path = "/circularity/batteries/" + asset["id"] + "/recommendation"
    r = client.post(
        path,
        headers=auth("originator"),
        json={"economics": {"RECYCLING": finance("RECYCLING")}},
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["recommended_pathway"] == "RECYCLING", json.dumps(
        result["pathways"], indent=2
    )
    assert "input_snapshot" not in result
    old = result["decision_id"]
    assert (
        client.post(
            "/circularity/decisions/" + old + "/override",
            headers=auth("originator"),
            json={"pathway": "RECYCLING", "reason": "Owner cannot perform this review"},
        ).status_code
        == 403
    )
    override = client.post(
        "/circularity/decisions/" + old + "/override",
        headers=auth("reviewer"),
        json={
            "pathway": "ASSESSMENT",
            "reason": "Request an assessment before agreeing the processing route",
        },
    )
    assert override.status_code == 200, override.text
    assert override.json()["override"]["original_decision_id"] == old
    assert (
        client.post(
            "/circularity/decisions/" + old + "/override",
            headers=auth("reviewer"),
            json={
                "pathway": "AUTOMOTIVE",
                "reason": "Cannot override missing qualification",
            },
        ).status_code
        == 409
    )
    history = client.get(path + "-history", headers=auth("originator")).json()
    assert (
        len(history) == 2 and history[1]["result"]["recommended_pathway"] == "RECYCLING"
    )
    with next(app.dependency_overrides[get_db]()) as db:
        carrier = db.get(m.TransporterProfile, "trans-1")
        carrier.active = False
        db.commit()
    fresh = client.get(path, headers=auth("originator")).json()
    assert fresh["stale"] and fresh["recommended_pathway"] == "ASSESSMENT"


def test_hazard_edit_invalidates_recommendation_without_erasing_history(client):
    asset, body = create(
        client,
        pbs="L1",
        chemistry="LFP",
        mass_kg=42,
        condition="DEGRADED",
        window_start=future(days=1),
        window_end=future(days=3),
    )
    assert review(client, asset["id"]).status_code == 200
    path = "/circularity/batteries/" + asset["id"] + "/recommendation"
    assert client.post(path, headers=auth("originator"), json={}).status_code == 200
    edit = client.patch(
        "/batteries/" + asset["id"],
        headers=auth("originator"),
        json={**body, "pbs": "L1", "pbs_comments": "Observed smoke from the battery"},
    )
    assert edit.status_code == 200, edit.text
    fresh = client.get(path, headers=auth("originator")).json()
    assert fresh["safety_state"] == "CRITICAL_HOLD" and fresh["stale"]
    assert len(client.get(path + "-history", headers=auth("originator")).json()) == 1


def test_expired_qualification_and_unknown_chemistry_excluded_with_reasons(client):
    asset, _ = create(
        client,
        pbs="L1",
        chemistry="UNKNOWN",
        mass_kg=42,
        condition="DEGRADED",
        window_start=future(days=1),
        window_end=future(days=3),
    )
    assert review(client, asset["id"]).status_code == 200
    result = client.get(
        "/circularity/batteries/" + asset["id"] + "/recommendation",
        headers=auth("originator"),
    ).json()
    assert get_path(result, "RECYCLING")["status"] in [
        "EXCLUDED",
        "INFORMATION_REQUIRED",
    ]
    assert any(
        r["code"] == "CHEMISTRY_UNSUPPORTED"
        for p in result["pathways"]
        for f in p["network"]["rejected"]
        for r in f["reasons"]
    )
    with next(app.dependency_overrides[get_db]()) as db:
        cap = db.get(m.OperationCapability, "fac-refurb-REFURBISHMENT")
        cap.valid_until = future(days=-1)
        db.commit()
    result = client.get(
        "/circularity/batteries/" + asset["id"] + "/recommendation",
        headers=auth("originator"),
    ).json()
    assert any(
        r["code"] == "OPERATION_UNVERIFIED"
        for f in get_path(result, "REFURBISHMENT")["network"]["rejected"]
        for r in f["reasons"]
    )


def test_downstream_material_transport_independent_from_battery_qualification(client):
    asset, _ = create(
        client,
        pbs="L1",
        chemistry="LFP",
        mass_kg=42,
        condition="DEGRADED",
        window_start=future(days=1),
        window_end=future(days=3),
    )
    assert review(client, asset["id"]).status_code == 200
    with next(app.dependency_overrides[get_db]()) as db:
        t = db.get(m.TransporterProfile, "trans-1")
        t.data = {**t.data, "verified_downstream_categories": []}
        db.commit()
    result = client.get(
        "/circularity/batteries/" + asset["id"] + "/recommendation",
        headers=auth("originator"),
    ).json()
    assert not get_path(result, "RECYCLING")["network"]["complete"]
    assert get_path(result, "ASSESSMENT")["network"]["complete"]


def test_decision_records_are_append_only(client):
    with next(app.dependency_overrides[get_db]()) as db:
        a = m.PathwayDecision(
            asset_id="battery-1", actor_id="originator", data={"original": True}
        )
        db.add(a)
        db.commit()
        a.data = {"original": False}
        with pytest.raises(ValueError):
            db.commit()
        db.rollback()
        db.delete(a)
        with pytest.raises(ValueError):
            db.commit()


def test_admin_assumption_requires_actual_platform_admin(client):
    f = finance("RECYCLING")
    f["benefits"][0]["source"] = "ADMIN_ASSUMPTION"
    result = client.post(
        "/circularity/batteries/battery-1/recommendation",
        headers=auth("originator"),
        json={"economics": {"RECYCLING": f}},
    )
    assert result.status_code == 403


def add_assessment(
    db,
    asset_id="battery-1",
    value=85,
    operation="REFURBISHMENT",
    revision_of=None,
    **findings
):
    obj = m.Assessment(
        asset_id=asset_id,
        facility_id="fac-refurb",
        requested_by="originator",
        operator_id="technician",
        reviewer_id="reviewer",
        intended_operation=operation,
        state="ACCEPTED",
        valid_until=future(days=4),
        revision_of=revision_of,
        data={
            "source": "QUALIFIED_FACILITY_ASSESSMENT",
            "submitted_at": m.now(),
            "report": {
                "outcome": "SUITABLE_FOR_DEFINED_OPERATION",
                "acceptance_specification": "Defined vehicle and repair specification",
                "limitations": "Capacity and application limitations documented",
                "measurements": [
                    {
                        "name": "SoH",
                        "value": value,
                        "unit": "%",
                        "method": "Qualified measured capacity test",
                    }
                ],
                "technical_findings": {
                    "fault_identified": True,
                    "repairable": True,
                    "parts_available": True,
                    "requalification_possible": True,
                    "automotive_application_passed": True,
                    "application_reference": "Defined vehicle requirement",
                    **findings,
                },
            },
        },
    )
    db.add(obj)
    db.flush()
    return obj


def test_accepted_application_evidence_and_conflicting_reports_need_revision(client):
    from app.services.decision_adapter import context_for

    with next(app.dependency_overrides[get_db]()) as db:
        a = add_assessment(db, value=85)
        b = add_assessment(db, value=35, repairable=False)
        db.commit()
        result = decision_for(db, db.get(m.BatteryAsset, "battery-1"))
        assert result["soh"]["source"] == "CONFLICTING_ASSESSMENTS"
        assert get_path(result, "AUTOMOTIVE")["status"] == "INFORMATION_REQUIRED"
        assert get_path(result, "REFURBISHMENT")["status"] == "INFORMATION_REQUIRED"
        revision = add_assessment(db, value=85, revision_of=b.id)
        db.commit()
        fresh = decision_for(db, db.get(m.BatteryAsset, "battery-1"))
        assert (
            fresh["soh"]["source"] == "QUALIFIED_ASSESSMENT"
            and fresh["soh"]["value"] == 85
        )
        assert get_path(fresh, "AUTOMOTIVE")["status"] == "FEASIBLE"
        assert get_path(fresh, "REFURBISHMENT")["status"] == "FEASIBLE"


def test_actual_offers_quotes_expiry_and_reference_scope(client):
    from test_intake_commercial import agreed
    from test_logistics import routes, quoted

    tx = agreed(client)
    plan = next(p for p in routes(client, tx) if not p["hub_id"])
    quote = quoted(client, tx, plan)
    f = finance(
        "REFURBISHMENT",
        perspective="ORIGINATOR_TRANSACTION",
        offer_id=tx["offer_id"],
        transport_quote_id=quote["id"],
    )
    f["benefits"] = []
    del f["costs"]["transport"]
    with next(app.dependency_overrides[get_db]()) as db:
        add_assessment(db)
        db.commit()
    endpoint = "/circularity/batteries/battery-1/recommendation"
    r = client.post(
        endpoint, headers=auth("originator"), json={"economics": {"REFURBISHMENT": f}}
    )
    assert r.status_code == 200, r.text
    p = get_path(r.json(), "REFURBISHMENT")
    assert p["economics"]["inputs"]["benefits"][0]["source"] == "ACTUAL_QUOTE"
    assert p["economics"]["inputs"]["costs"]["transport"]["source"] == "ACTUAL_QUOTE"
    assert p["economics"]["net_paise"] == 2000000 - 250000 - 600
    assert p["economics"]["provisional"] is True
    with next(app.dependency_overrides[get_db]()) as db:
        q = db.get(m.TransportQuote, quote["id"])
        q.expires_at = future(days=-1)
        db.commit()
    expired = client.get(endpoint, headers=auth("originator")).json()
    assert expired["stale"] and expired["recalculation_warning"]
    assert get_path(expired, "REFURBISHMENT")["economics"]["net_paise"] is None
    incompatible = finance(
        "RECYCLING", perspective="ORIGINATOR_TRANSACTION", offer_id=tx["offer_id"]
    )
    incompatible["benefits"] = []
    invalid = client.post(
        endpoint,
        headers=auth("originator"),
        json={"economics": {"RECYCLING": incompatible}},
    )
    assert invalid.status_code == 409


def test_recurring_annual_costs_discounted_without_double_count():
    f = finance("SECOND_LIFE", basis="NPV", horizon_years=3, discount_rate=0.1)
    f["benefits"][0]["year"] = 3
    f["costs"]["maintenance"].update(year=1, repeat_through_year=3)
    DecisionIn(economics={"SECOND_LIFE": f})
    result = evaluate(context(), {"SECOND_LIFE": f})
    expected = round(10000 / 1.1**3 - 800 - sum(100 / 1.1**y for y in range(1, 4)))
    assert get_path(result, "SECOND_LIFE")["economics"]["net_paise"] == expected


def test_controlled_specialist_route_never_unlocks_ordinary_routes():
    result = evaluate(
        context(pbs="L4", specialist_dispatch_authorized=True),
        {"REFURBISHMENT": finance(benefit=10**10)},
    )
    assert result["recommended_pathway"] == "ASSESSMENT"
    assert result["evaluation_state"] == "RESTRICTED_RECOMMENDATION"
    assert get_path(result, "REFURBISHMENT")["status"] == "HOLD"
    critical = evaluate(
        context(pbs="L4", specialist_dispatch_authorized=True, critical_hazard=True)
    )
    assert critical["recommended_pathway"] is None


def test_technician_critical_report_creates_persistent_hold(client):
    with next(app.dependency_overrides[get_db]()) as db:
        asset = db.get(m.BatteryAsset, "battery-1")
        asset.current_holder_org_id = "org-refurb"
        assessment = m.Assessment(
            asset_id=asset.id,
            facility_id="fac-refurb",
            requested_by="originator",
            intended_operation="REFURBISHMENT",
            state="ASSIGNED",
            data={"procedure": "Assigned diagnostic test"},
        )
        db.add(assessment)
        db.commit()
        assessment_id = assessment.id
    response = client.post(
        "/circularity/assessments/" + assessment_id + "/submit",
        headers=auth("technician"),
        json={
            "observations": "Visible smoke from the pack",
            "measurements": [],
            "evidence": "Operator report of observed hazard",
            "equipment_reference": "Visual observation",
            "outcome": "INFORMATION_INSUFFICIENT",
            "limitations": "No further tests permitted until instructions",
            "acceptance_specification": "Handling instructions required",
        },
    )
    assert response.status_code == 200, response.text
    result = client.get(
        "/circularity/batteries/battery-1/recommendation", headers=auth("originator")
    ).json()
    assert result["safety_state"] == "CRITICAL_HOLD"
    with next(app.dependency_overrides[get_db]()) as db:
        assert db.get(m.BatteryAsset, "battery-1").state == "HOLD"
        assert db.scalar(
            select(m.ExceptionCase).where(
                m.ExceptionCase.object_id == "battery-1",
                m.ExceptionCase.category == "SAFETY_FLAG",
            )
        )


def test_completed_battery_not_recommended_as_available_inventory(client):
    with next(app.dependency_overrides[get_db]()) as db:
        asset = db.get(m.BatteryAsset, "battery-1")
        asset.state = "CLOSED"
        db.commit()
    result = client.get(
        "/circularity/batteries/battery-1/recommendation", headers=auth("originator")
    ).json()
    assert result["recommended_pathway"] is None
    assert any(r["code"] == "ASSET_UNAVAILABLE" for r in result["restrictions"])
