"""Accepted assessment provenance and material-change snapshots."""

from sqlalchemy import select
from .. import models as m
from ..common import expired, get
from .registration import level, critical_report, routing_reasons
from .circularity import capability_check
from .decision_network import OPERATIONS, network_for


def context_for(db, asset):
    reports = db.scalars(
        select(m.Assessment)
        .where(m.Assessment.asset_id == asset.id)
        .order_by(m.Assessment.created_at, m.Assessment.id)
    ).all()
    superseded = {a.revision_of for a in reports if a.revision_of}
    current = [
        a
        for a in reports
        if a.id not in superseded
        and a.state == "ACCEPTED"
        and a.valid_until
        and not expired(a.valid_until)
        and not capability_check(
            db,
            get(db, m.Facility, a.facility_id),
            "ASSESSMENT",
            asset.mass_kg,
            asset.chemistry,
            asset.form,
            scope_only=True,
            asset=asset,
        )
    ]
    findings, qualifications, evidence = {}, {}, []
    findings_by_path, qualification_conflicts, finding_conflicts, soh_values = (
        {},
        set(),
        set(),
        set(),
    )

    def qualification(path, value):
        if path in qualifications and qualifications[path] != value:
            qualification_conflicts.add(path)
        qualifications[path] = None if path in qualification_conflicts else value

    def path_findings(path, values):
        target = findings_by_path.setdefault(path, {})
        for key, value in values.items():
            if value is None:
                continue
            if key in target and target[key] != value:
                finding_conflicts.add((path, key))
            target[key] = None if (path, key) in finding_conflicts else value

    soh, source = None, "UNAVAILABLE"
    for a in current:
        report = a.data.get("report", {})
        evidence.append(
            {
                "id": a.id,
                "type": "ASSESSMENT",
                "source": "QUALIFIED_ASSESSMENT",
                "facility_id": a.facility_id,
                "operator_id": a.operator_id,
                "reviewer_id": a.reviewer_id,
                "recorded_at": a.data.get("submitted_at"),
                "valid_until": a.valid_until,
                "application_reference": report.get("acceptance_specification"),
                "limitations": report.get("limitations"),
            }
        )
        technical = report.get("technical_findings") or {}
        suitable = report.get("outcome") == "SUITABLE_FOR_DEFINED_OPERATION"
        key = {"REFURBISHMENT": "REFURBISHMENT", "INTEGRATION": "SECOND_LIFE"}.get(
            a.intended_operation
        )
        if key:
            qualification(key, suitable)
            path_findings(key, technical)
        if (
            a.intended_operation == "REFURBISHMENT"
            and technical.get("automotive_application_passed") is not None
        ):
            qualification(
                "AUTOMOTIVE", suitable and technical["automotive_application_passed"]
            )
            path_findings("AUTOMOTIVE", technical)
        for v in report.get("measurements", []):
            if (
                v.get("name", "").casefold().replace(" ", "_")
                in ["soh", "state_of_health", "soh_percent"]
                and v.get("unit") in ["%", "percent"]
                and v.get("value") is not None
                and 0 <= v["value"] <= 100
            ):
                soh, source = v["value"], "QUALIFIED_ASSESSMENT"
                soh_values.add(soh)
    if len(soh_values) > 1:
        soh, source = None, "CONFLICTING_ASSESSMENTS"
    inspection = asset.data.get("inspection") or {}
    if soh is None and not soh_values and inspection.get("soh_percent") is not None:
        soh = inspection["soh_percent"]
        source = (
            "OWNER_REPORTED_MEASUREMENT"
            if inspection.get("conducted") == "YES"
            and inspection.get("source") in ["MEASURED", "BMS_REPORTED"]
            and inspection.get("scope") == "INDIVIDUAL"
            else "OWNER_ESTIMATE"
        )
        evidence.append(
            {
                "type": "OWNER_INSPECTION",
                "source": source,
                "recorded_at": inspection.get("date"),
                "inspector": inspection.get("inspector"),
                "scope": inspection.get("scope"),
                "soh_percent": soh,
            }
        )
    reasons = routing_reasons(asset)
    report_critical = any(
        critical_report(
            {
                "additional_information": str(
                    a.data.get("report", {}).get("observations", "")
                )
                + " "
                + str(a.data.get("report", {}).get("limitations", ""))
            }
        )
        for a in reports
    )
    if report_critical and not any(
        r["code"] == "CRITICAL_HAZARD_REPORTED" for r in reasons
    ):
        reasons.append(
            {
                "code": "CRITICAL_HAZARD_REPORTED",
                "message": "An assessment reports an explicit critical hazard. Qualified handling instructions are required.",
            }
        )
    if asset.state in ["DISPUTED", "CANCELLED", "WITHDRAWN", "EXPIRED", "CLOSED"]:
        reasons.append(
            {
                "code": "ASSET_UNAVAILABLE",
                "message": "Asset is disputed, unavailable or its recorded lifecycle is complete. Use the linked downstream item for a later recovery cycle.",
            }
        )
    approved = asset.data.get("registration", {}).get("status") == "APPROVED" or (
        not asset.data.get("registration")
        and not asset.data.get("pbs")
        and asset.state
        in [
            "READY_FOR_LISTING",
            "LISTED",
            "OFFER_SELECTED",
            "AGREED",
            "IN_SHIPMENT",
            "RECEIVED",
            "DISPOSITION_PENDING",
            "DISPOSITION_RECORDED",
            "CLOSED",
        ]
    )
    clearance = asset.data.get("handling_clearance", {})
    specialist_dispatch_authorized = (
        approved
        and level(asset) == "L4"
        and not reasons
        and clearance.get("handling_scope") == "CONTROLLED_HANDLING"
        and bool(clearance.get("valid_until"))
        and not expired(clearance["valid_until"])
    )
    context = {
        "asset_id": asset.id,
        "reported_pbs": asset.data.get("pbs"),
        "pbs": level(asset),
        "legacy_screened": not asset.data.get("pbs")
        and approved
        and asset.state not in ["HOLD", "REVIEW_REQUIRED"],
        "critical_hazard": critical_report(asset.data) or report_critical,
        "specialist_dispatch_authorized": specialist_dispatch_authorized,
        "approved": approved,
        "blocking_reasons": reasons,
        "chemistry": asset.chemistry,
        "form": asset.form,
        "soh_percent": soh,
        "soh_source": source,
        "findings": findings,
        "findings_by_path": findings_by_path,
        "qualifications": qualifications,
        "evidence_used": evidence,
        "asset_snapshot": {
            "condition": asset.condition,
            "quantity": asset.quantity,
            "mass_kg": asset.mass_kg,
            "registration": asset.data.get("registration"),
            "authority_confirmed": asset.authority_confirmed,
            "data": asset.data,
        },
        "network": {p: network_for(db, asset, p) for p in OPERATIONS},
    }
    return context
