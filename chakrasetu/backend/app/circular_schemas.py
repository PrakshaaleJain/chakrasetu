from typing import Literal
from pydantic import Field
from .schemas import Schema
from .circular_models import Operation, ItemKind, JobState, HandoffState
from .enums import Chemistry, Form
from .decision_schemas import TechnicalFindings


class CapabilityIn(Schema):
    facility_id: str
    operation: Operation
    capacity_kg: float | None = Field(default=None, gt=0)
    chemistries: list[Chemistry] = Field(default_factory=list)
    formats: list[Form] = Field(default_factory=list)
    material_categories: list[str] = Field(default_factory=list, max_length=30)
    evidence: str = Field(min_length=3, max_length=4000)


class ReviewIn(Schema):
    accepted: bool
    evidence: str = Field(min_length=3, max_length=4000)
    reason: str = Field(min_length=3, max_length=4000)
    valid_until: str


class AssessmentIn(Schema):
    asset_id: str
    facility_id: str
    intended_operation: Operation
    procedure: str = Field(min_length=3, max_length=2000)
    revision_of: str | None = None


class Measurement(Schema):
    name: str = Field(min_length=1, max_length=100)
    value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=30)
    method: str = Field(min_length=3, max_length=500)


class AssessmentReportIn(Schema):
    observations: str = Field(min_length=3, max_length=4000)
    measurements: list[Measurement] = Field(default_factory=list, max_length=100)
    evidence: str = Field(min_length=3, max_length=4000)
    equipment_reference: str = Field(min_length=3, max_length=500)
    outcome: Literal[
        "SUITABLE_FOR_DEFINED_OPERATION", "UNSUITABLE", "INFORMATION_INSUFFICIENT"
    ]
    limitations: str = Field(min_length=3, max_length=4000)
    acceptance_specification: str = Field(min_length=3, max_length=4000)
    technical_findings: TechnicalFindings | None = None


class JobIn(Schema):
    facility_id: str
    operation: Operation
    item_ids: list[str] = Field(min_length=1, max_length=100)
    procedure: str = Field(min_length=3, max_length=2000)
    evidence: str = Field(min_length=3, max_length=4000)


class OutputIn(Schema):
    identifier: str = Field(min_length=3, max_length=100)
    kind: ItemKind
    mass_kg: float = Field(gt=0, le=100000, allow_inf_nan=False)
    category: str = Field(min_length=3, max_length=100)
    specification: str = Field(min_length=3, max_length=4000)
    evidence: str = Field(min_length=3, max_length=4000)
    chemistry: Chemistry = Chemistry.UNKNOWN


class CompleteIn(Schema):
    outputs: list[OutputIn] = Field(min_length=1, max_length=100)
    process_evidence: str = Field(min_length=3, max_length=4000)
    measured_loss_kg: float = Field(ge=0, allow_inf_nan=False)
    loss_evidence: str = Field(min_length=3, max_length=4000)


class EventIn(Schema):
    event: Literal[
        "ACCEPT",
        "DEPLOY",
        "SERVICE",
        "RETIRE",
        "TAKE_BACK_CONTRACT",
        "INCIDENT_REPORTED",
    ]
    evidence: str = Field(min_length=3, max_length=4000)
    notes: str = Field(min_length=3, max_length=4000)
    customer_org_id: str | None = None


class HandoffIn(Schema):
    item_id: str
    receiver_facility_id: str
    price_paise: int | None = Field(default=None, ge=0)
    payer_org_id: str
    budget_paise: int | None = Field(default=None, ge=0)
    acceptance_specification: str = Field(min_length=3, max_length=4000)
    evidence: str = Field(min_length=3, max_length=4000)
    window_start: str
    window_end: str


class VersionIn(Schema):
    version: int = Field(gt=0)


class HandoffQuoteIn(Schema):
    transporter_id: str
    total_paise: int = Field(ge=0)
    expires_at: str
    evidence: str = Field(min_length=3, max_length=4000)
    acceptance_specification_confirmed: bool


class HandoffEventIn(Schema):
    state: HandoffState
    physical: bool = False
    condition_matches: bool = True
    evidence: str = Field(min_length=3, max_length=4000)


class EconomicsIn(Schema):
    # A whole pathway estimate, not per-leg figures. No invented market defaults.
    inputs: dict[str, dict[str, int | str | None]] = Field(
        default_factory=dict, max_length=3
    )
