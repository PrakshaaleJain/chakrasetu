"""Typed owner reports. These observations are not facility assessments."""

from datetime import date as CalendarDate
from typing import Literal
from pydantic import Field
from .base_schemas import Schema
from .enums import Chemistry, Form, Condition

PBSLevel = Literal["L1", "L2", "L3", "L4", "L5"]
Application = Literal[
    "TWO_WHEELER",
    "THREE_WHEELER",
    "FOUR_WHEELER",
    "COMMERCIAL_VEHICLE",
    "OTHER",
    "UNKNOWN",
]


class ReportedInspection(Schema):
    conducted: Literal["YES", "NO", "UNKNOWN"] = "UNKNOWN"
    date: CalendarDate | None = None
    inspector: str | None = Field(default=None, max_length=200)
    source: Literal[
        "MEASURED", "BMS_REPORTED", "ESTIMATED", "OTHER_REPORTED", "UNKNOWN"
    ] = "UNKNOWN"
    scope: Literal["INDIVIDUAL", "SAMPLE_ONLY", "UNKNOWN"] = "UNKNOWN"
    soh_percent: float | None = Field(default=None, ge=0, le=100)
    soc_percent: float | None = Field(default=None, ge=0, le=100)
    voltage_v: float | None = Field(default=None, ge=0)
    capacity_ah: float | None = Field(default=None, ge=0)
    resistance: float | None = Field(default=None, ge=0)
    resistance_unit: Literal["OHM", "MILLIOHM", "UNKNOWN"] = "UNKNOWN"
    resistance_method: str | None = Field(default=None, max_length=500)
    imbalance_v: float | None = Field(default=None, ge=0)
    temperature: str | None = Field(default=None, max_length=1000)
    fault_codes: str | None = Field(default=None, max_length=1000)
    findings: str | None = Field(default=None, max_length=4000)
    charge_discharge_results: str | None = Field(default=None, max_length=4000)
    other_tests: str | None = Field(default=None, max_length=4000)


class RegistrationReview(Schema):
    decision: Literal[
        "APPROVED", "REJECTED", "INFORMATION_REQUESTED", "SPECIALIST_ASSESSMENT"
    ]
    reason: str = Field(min_length=3, max_length=4000)
    reviewer_pbs: PBSLevel | None = None


class SafetyScope(Schema):
    chemistries: list[Chemistry] | None = Field(default=None, max_length=20)
    formats: list[Form] | None = Field(default=None, max_length=10)
    conditions: list[Condition] | None = Field(default=None, max_length=20)
    application_types: list[Application] = Field(default_factory=list, max_length=6)
    max_pbs: PBSLevel | None = None
    specialist_assessment: bool = False
    damaged_handling: bool = False
    critical_hazard_handling: bool = False
    dangerous_goods: bool = False
    service_areas: list[str] = Field(default_factory=list, max_length=30)
    restrictions: str = Field(default="", max_length=2000)


class AcceptanceDeclaration(Schema):
    kind: Literal["PATHWAY", "TRANSPORT", "OPERATION"]
    scope: SafetyScope
