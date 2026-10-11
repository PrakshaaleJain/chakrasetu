"""Explicit fictional activity scopes for the local rehearsal; never real credentials."""

from sqlalchemy import select
from . import models as m


def seed_acceptance(db):
    for model in [m.FacilityCapability, m.TransporterProfile, m.OperationCapability]:
        for obj in db.scalars(select(model)):
            org = db.get(
                m.Organisation,
                (
                    obj.organisation_id
                    if model is m.TransporterProfile
                    else db.get(m.Facility, obj.facility_id).organisation_id
                ),
            )
            if not org.synthetic or obj.data.get("verified_safety_scope") is not None:
                continue
            specialist = obj.data.get("handling_scope") == "CONTROLLED_HANDLING"
            scope = {
                "max_pbs": (
                    "L4"
                    if specialist
                    else (
                        "L3"
                        if getattr(obj, "operation", None) == "ASSESSMENT"
                        else "L2"
                    )
                ),
                "application_types": [
                    "TWO_WHEELER",
                    "THREE_WHEELER",
                    "FOUR_WHEELER",
                    "COMMERCIAL_VEHICLE",
                    "OTHER",
                    "UNKNOWN",
                ],
                "specialist_assessment": specialist
                or getattr(obj, "operation", None) == "ASSESSMENT",
                "damaged_handling": specialist,
                "critical_hazard_handling": False,
                "dangerous_goods": specialist,
                "service_areas": [],
                "restrictions": "Synthetic example scope only. Not a real qualification or safety certificate.",
            }
            obj.data = {
                **obj.data,
                "verified_safety_scope": scope,
                "declared_safety_scope": scope,
                "scope_source": "SYNTHETIC_EXAMPLE",
                "conditions": obj.data.get(
                    "conditions",
                    (
                        [
                            "WORKING",
                            "DEGRADED",
                            "NON_FUNCTIONAL",
                            "DAMAGED_REPORTED",
                            "UNKNOWN",
                        ]
                        if specialist
                        else (
                            ["WORKING", "DEGRADED", "NON_FUNCTIONAL", "UNKNOWN"]
                            if getattr(obj, "operation", None) == "ASSESSMENT"
                            else ["WORKING", "DEGRADED", "NON_FUNCTIONAL"]
                        )
                    ),
                ),
            }
    db.commit()
