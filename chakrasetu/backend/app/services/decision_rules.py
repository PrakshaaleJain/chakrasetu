"""Pure deterministic gates, technical rules and economics shared by both adapters."""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from ..decision_schemas import COMPONENTS

LABELS = {
    "AUTOMOTIVE": "Continued automotive use",
    "REFURBISHMENT": "Refurbishment and requalification",
    "SECOND_LIFE": "Second-life application",
    "RECYCLING": "Recycling and material recovery",
    "ASSESSMENT": "Qualified assessment",
}


def load_policy(path=None):
    p = json.loads(
        Path(
            path
            or os.getenv(
                "DECISION_POLICY_PATH",
                str(Path(__file__).resolve().parents[1] / "decision_policy.json"),
            )
        ).read_text()
    )
    high, low = p["automotive_screen_soh"], p["second_life_screen_soh"]
    if (
        not (
            isinstance(high, (int, float))
            and isinstance(low, (int, float))
            and 0 <= low < high <= 100
        )
        or not isinstance(p["economic_tie_paise"], int)
        or p["economic_tie_paise"] < 0
        or not p.get("version")
    ):
        raise RuntimeError("Invalid versioned SoH screening configuration.")
    return p


POLICY = load_policy()

from .pathway_economics import financial_result


def evaluate(context, economics=None, policy=None, timestamp=None):
    policy, timestamp = policy or POLICY, timestamp or datetime.now(timezone.utc)
    economics = economics or {}
    pbs, critical = context.get("pbs"), context.get("critical_hazard", False)
    blocked = bool(context.get("blocking_reasons")) or pbs in ["L4", "L5"] or critical
    safety = (
        "CRITICAL_HOLD"
        if pbs == "L5" or critical
        else (
            "SPECIALIST_REVIEW"
            if pbs == "L4"
            else (
                "HOLD"
                if blocked
                else (
                    "RESTRICTED"
                    if pbs == "L3"
                    else "ORDINARY_EVALUATION" if pbs else "INFORMATION_REQUIRED"
                )
            )
        )
    )
    if not pbs and not context.get("legacy_screened"):
        blocked = True
    elif not pbs and context.get("legacy_screened"):
        safety = "LEGACY_SCOPED_EVALUATION"
    soh, quality = context.get("soh_percent"), context.get("soh_source", "UNAVAILABLE")
    usable_soh = (
        soh
        if quality
        in [
            "QUALIFIED_ASSESSMENT",
            "OWNER_REPORTED_MEASUREMENT",
            "SCENARIO_MEASUREMENT",
        ]
        else None
    )
    band = (
        "UNAVAILABLE"
        if usable_soh is None
        else (
            "HIGH"
            if usable_soh >= policy["automotive_screen_soh"]
            else "MID" if usable_soh >= policy["second_life_screen_soh"] else "LOW"
        )
    )
    findings, qualifications = context.get("findings", {}), context.get(
        "qualifications", {}
    )
    routes = []
    for path, label in LABELS.items():
        rules = []
        findings = (
            context.get("findings_by_path", {}).get(path, {})
            if "findings_by_path" in context
            else context.get("findings", {})
        )
        specialist = (
            path == "ASSESSMENT"
            and pbs == "L4"
            and context.get("specialist_dispatch_authorized")
            and not critical
        )

        def check(code, value, message):
            rules.append({"code": code, "passed": value, "message": message})

        check(
            "SAFETY_GATE",
            bool(specialist) or not blocked,
            (
                "Current qualified controlled-handling instructions permit this specialist route only."
                if specialist
                else (
                    "Critical reports and unresolved holds disable ordinary evaluation."
                    if blocked
                    else "Preliminary handling gate permits scoped evaluation; this is not a safety certification."
                )
            ),
        )
        check(
            "REGISTRATION_APPROVAL",
            context.get("approved", False),
            "Network-operator approval is separate from technical qualification.",
        )
        check(
            "CHEMISTRY_KNOWN",
            True if context.get("chemistry") not in [None, "UNKNOWN"] else None,
            (
                "Chemistry must be known for processing compatibility."
                if path != "ASSESSMENT"
                else "Assessment must explicitly support the reported chemistry, including unknown where qualified."
            ),
        )
        if path == "ASSESSMENT" and context.get("chemistry") == "UNKNOWN":
            rules[-1]["passed"] = True
        if path == "AUTOMOTIVE":
            check(
                "APPLICATION_QUALIFICATION",
                qualifications.get(path),
                "Accepted vehicle-specific technical assessment is required; a high SoH alone is insufficient.",
            )
            check(
                "AUTOMOTIVE_SPECIFICATION",
                findings.get("automotive_application_passed"),
                "Defined vehicle energy, power and reliability requirements must be passed.",
            )
        elif path == "REFURBISHMENT":
            for key in [
                "fault_identified",
                "repairable",
                "parts_available",
                "requalification_possible",
            ]:
                check(
                    key.upper(),
                    findings.get(key),
                    {
                        "fault_identified": "Identify the fault or deficiency.",
                        "repairable": "Document whether repair is technically plausible.",
                        "parts_available": "Confirm compatible parts and expertise.",
                        "requalification_possible": "Confirm post-repair testing and requalification procedure.",
                    }[key],
                )
            check(
                "APPLICATION_QUALIFICATION",
                qualifications.get(path),
                "A current accepted assessment must support the defined repair operation.",
            )
        elif path == "SECOND_LIFE":
            check(
                "APPLICATION_QUALIFICATION",
                qualifications.get(path),
                "Accepted application-specific integration assessment is required.",
            )
            check(
                "SECOND_LIFE_SPECIFICATION",
                findings.get("second_life_application_passed"),
                "Document energy, power, efficiency and reliability against the intended application.",
            )
            check(
                "REMAINING_LIFE",
                findings.get("remaining_life_adequate"),
                "Document adequate remaining useful life for the intended application.",
            )
        if path in ["AUTOMOTIVE", "SECOND_LIFE"]:
            check(
                "SOH_SCREEN",
                None if usable_soh is None else True,
                (
                    f"SoH {usable_soh}% is in the {band.lower()} screening band; application evidence determines suitability."
                    if usable_soh is not None
                    else "SoH unavailable or unreliable; request capacity/health testing. No zero or normal value has been substituted."
                ),
            )
        network = context.get("network", {}).get(
            path, {"receivers": [], "rejected": [], "complete": False}
        )
        check(
            "QUALIFIED_CHAIN",
            bool(network.get("complete")),
            "Processing, receiving, transport, time-window and capacity constraints are checked separately for the required chain.",
        )
        known_failure = any(r["passed"] is False for r in rules)
        unknowns = [r for r in rules if r["passed"] is None]
        # Missing evidence is conditional; a known incompatibility is an exclusion.
        status = (
            "HOLD"
            if (blocked and not specialist) or not context.get("approved")
            else (
                "EXCLUDED"
                if known_failure
                else "INFORMATION_REQUIRED" if unknowns else "FEASIBLE"
            )
        )
        if (
            status == "EXCLUDED"
            and not network.get("complete")
            and network.get("information_required")
            and not any(
                r["passed"] is False for r in rules if r["code"] != "QUALIFIED_CHAIN"
            )
        ):
            status = "INFORMATION_REQUIRED"
        finance = financial_result(path, economics.get(path), timestamp)
        if status != "FEASIBLE":
            finance["ranking_eligible"] = False
        else:
            finance["ranking_eligible"] = finance["complete"]
        missing = [r["message"] for r in unknowns]
        missing += [r["message"] for r in context.get("blocking_reasons", [])]
        routes.append(
            {
                "pathway": path,
                "label": label,
                "status": status,
                "rules": rules,
                "missing_information": missing,
                "economics": finance,
                "network": network,
                "qualification_conditions": (
                    [
                        "Requalification and receiving acceptance remain necessary before actual execution."
                    ]
                    if path in ["AUTOMOTIVE", "REFURBISHMENT", "SECOND_LIFE"]
                    else []
                ),
                "next_action": (
                    "Obtain qualified handling instructions; routine dispatch is disabled."
                    if blocked
                    else (
                        "Resolve failed constraints or supply missing evidence and quotes."
                        if status != "FEASIBLE"
                        else "Review terms, confirm transfer authority, obtain and accept scoped transport quotes before booking."
                    )
                ),
            }
        )
    feasible = [
        r for r in routes if r["status"] == "FEASIBLE" and r["pathway"] != "ASSESSMENT"
    ]
    priced = [r for r in feasible if r["economics"]["complete"]]
    groups = {
        (
            r["economics"]["basis"],
            r["economics"]["horizon_years"],
            r["economics"].get("discount_rate"),
            r["economics"]["perspective"],
        )
        for r in priced
    }
    comparable = len(groups) <= 1
    ranked = (
        sorted(priced, key=lambda r: (-r["economics"]["net_paise"], r["pathway"]))
        if comparable
        else []
    )
    winner = ranked[0] if ranked else None
    ties = (
        [
            r["pathway"]
            for r in ranked[1:]
            if r["economics"]["range_paise"][1] + policy["economic_tie_paise"]
            >= winner["economics"]["range_paise"][0]
        ]
        if winner
        else []
    )
    selected = (
        None
        if ties
        else (
            winner["pathway"]
            if winner
            else (
                "ASSESSMENT"
                if not blocked
                and context.get("approved")
                and any(
                    r["pathway"] == "ASSESSMENT" and r["status"] == "FEASIBLE"
                    for r in routes
                )
                and not feasible
                else None
            )
        )
    )
    incomplete = len(priced) < len(feasible)
    reason = (
        f"{winner['label']} has the highest comparable estimated net value among the qualified, feasible priced alternatives. "
        if winner
        else "Economic recommendation unavailable: qualified feasible pathways and complete comparable offers/costs are required. "
    )
    if ties:
        reason = "The leading pathways are economically similar within input uncertainty; no single financial winner is justified. "
    if not comparable:
        reason = "Economic recommendation unavailable: comparison bases, horizons or discount rates differ. "
    if incomplete and winner:
        reason += "Other feasible pathways have missing economic inputs; this is a provisional comparison of available quotes/estimates only. "
    if selected == "ASSESSMENT":
        reason = "Qualified assessment is the next useful step because application evidence is incomplete or processing alternatives are unavailable. "
    if winner and winner["economics"]["net_paise"] < 0:
        reason += "The best priced result is still a net cost; commercial approval and funding are required. "
    if (
        blocked
        and context.get("specialist_dispatch_authorized")
        and pbs == "L4"
        and not critical
        and any(
            r["pathway"] == "ASSESSMENT" and r["status"] == "FEASIBLE" for r in routes
        )
    ):
        selected = "ASSESSMENT"
        reason = "Only the qualified assessment route is available under current controlled-handling instructions and operator approval. Ordinary marketplace routes remain on hold."
    elif blocked:
        reason = "Unresolved handling or registration gates prevent an ordinary recommendation. Obtain the recorded review or qualified instructions. "
    return {
        "generated_at": timestamp.isoformat(),
        "rule_version": policy["version"],
        "policy": policy,
        "safety_state": safety,
        "reported_pbs": context.get("reported_pbs", pbs),
        "required_handling_level": pbs,
        "soh": {"value": soh, "source": quality, "screening_band": band},
        "recommended_pathway": selected,
        "similar_pathways": ([winner["pathway"], *ties] if ties else []),
        "evaluation_state": (
            "RESTRICTED_RECOMMENDATION"
            if blocked and selected == "ASSESSMENT"
            else (
                "HOLD"
                if blocked
                else (
                    "PROVISIONAL"
                    if winner and (incomplete or winner["economics"]["provisional"])
                    else "RECOMMENDATION" if selected else "INFORMATION_REQUIRED"
                )
            )
        ),
        "recommendation_reason": reason.strip(),
        "pathways": routes,
        "ranking": {
            "comparable": comparable,
            "ranked": [r["pathway"] for r in ranked],
            "hard_constraints_before_economics": True,
        },
        "restrictions": context.get("blocking_reasons", []),
        "evidence_used": context.get("evidence_used", []),
        "required_tests": list(
            dict.fromkeys(
                m
                for r in routes
                if r["status"] == "INFORMATION_REQUIRED"
                for m in r["missing_information"]
            )
        ),
        "execution_status": "RECOMMENDATION_ONLY",
        "next_action": "Review the required evidence and obtain missing quotes; recommendations do not contract, reserve capacity, transfer custody or record disposition.",
    }
