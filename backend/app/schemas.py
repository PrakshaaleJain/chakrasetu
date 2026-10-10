from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .enums import (
    Chemistry,
    Form,
    Condition,
    Answer,
    Pathway,
    ShipmentState,
    DispositionOutcome,
    FLAGS,
)


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BatteryIn(Schema):
    internal_id: str = Field(min_length=1, max_length=100)
    owner_org_id: str
    custodian_org_id: str
    chemistry: Chemistry = Chemistry.UNKNOWN
    form: Form = Form.UNKNOWN
    condition: Condition = Condition.UNKNOWN
    removal_reason: Literal[
        "degradation",
        "fault",
        "impact/accident",
        "maintenance replacement",
        "end-of-life",
        "unknown",
        "other",
    ] = "unknown"
    quantity: int = Field(default=1, gt=0, le=10000)
    mass_kg: float | None = Field(default=None, gt=0, le=100000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    address: str = Field(default="", max_length=500)
    access_notes: str = Field(default="", max_length=1000)
    authority_confirmed: bool = False
    declaration: bool = False
    flags: dict[str, Answer] = Field(
        default_factory=lambda: {f: Answer.UNKNOWN for f in FLAGS}
    )
    notes: str = Field(default="", max_length=4000)
    window_start: datetime | None = None
    window_end: datetime | None = None
    provenance: Literal[
        "SELF_DECLARED", "DOCUMENT_REVIEWED", "INSPECTION_REPORTED", "UNKNOWN"
    ] = "SELF_DECLARED"

    @model_validator(mode="after")
    def consistent(self):
        if set(self.flags) != set(FLAGS):
            raise ValueError("All eleven critical flags must be explicitly answered.")
        for date in [self.window_start, self.window_end]:
            if date and date.tzinfo is None:
                raise ValueError("Time windows must include a timezone.")
        if (
            self.window_start
            and self.window_end
            and self.window_end <= self.window_start
        ):
            raise ValueError("Window end must be after start.")
        if self.window_start:
            self.window_start = self.window_start.astimezone(timezone.utc)
        if self.window_end:
            self.window_end = self.window_end.astimezone(timezone.utc)
        return self


class ListingIn(Schema):
    asset_id: str
    mode: Literal["INVITE_OFFERS", "FIXED_PRICE", "REQUEST_ASSESSMENT"] = (
        "INVITE_OFFERS"
    )
    asking_paise: int | None = Field(default=None, ge=0)
    expires_at: datetime
    terms: str = Field(
        default="Inspection before acceptance; cancellation by mutual agreement.",
        min_length=1,
        max_length=4000,
    )


class OfferIn(Schema):
    facility_id: str
    pathway: Pathway
    price_paise: int = Field(ge=0)
    payer_org_id: str
    budget_paise: int = Field(ge=0)
    expires_at: datetime
    inspection_condition: Literal[
        "FIRM_SUBJECT_TO_CHECKS", "CONDITIONAL", "INDICATIVE"
    ] = "CONDITIONAL"
    acceptance_criteria: str = Field(min_length=1, max_length=2000)
    payment_terms: str = "Due after inspection acceptance"
    cancellation_terms: str = (
        "Mutual cancellation before physical pickup; no automatic charges"
    )
    costs: dict[str, int | None] = Field(
        default_factory=lambda: {
            "transport": None,
            "hub": 0,
            "testing": 0,
            "tax": 0,
            "other": 0,
        }
    )


class ConfirmIn(Schema):
    version: int = Field(ge=1)


class AmendmentIn(Schema):
    budget_paise: int = Field(ge=0)
    price_paise: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=3)
    evidence: str = Field(min_length=1)


class QuoteIn(Schema):
    route_id: str
    total_paise: int | None = Field(default=None, ge=0)
    expires_at: datetime
    status: Literal["SUBMITTED", "DECLINED", "NO_RESPONSE"] = "SUBMITTED"
    inclusions: str = (
        "All legs, loading, unloading, tolls, taxes and disclosed hub fees"
    )
    exclusions: str = "None"
    cancellation_terms: str = "By mutual agreement before pickup"
    evidence: str = Field(min_length=1)


class RouteSelect(Schema):
    route_id: str


class ShipmentEventIn(Schema):
    state: ShipmentState
    evidence: str = ""
    notes: str = ""
    physical: bool = False
    condition_matches: bool = True
    receipt: Literal[
        "ACCEPTED", "PARTIALLY_ACCEPTED", "REJECTED", "RECEIVED_PENDING_INSPECTION"
    ] = "ACCEPTED"
    accepted_quantity: int | None = Field(default=None, ge=0)


class HubEventIn(Schema):
    event: Literal["HUB_RECEIVED", "HUB_DISPATCHED"]
    physical: bool
    evidence: str = Field(min_length=1)


class TelemetryIn(Schema):
    event: Literal[
        "POSITION",
        "ROUTE_DEVIATION",
        "PROLONGED_STOP",
        "TEMPERATURE",
        "SHOCK",
        "MISSING_EVENT",
        "REPORTED_INCIDENT",
    ]
    value: float | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    notes: str = ""


class ResolveIn(Schema):
    resolution: str = Field(min_length=3)
    evidence: str = Field(min_length=1)
    resume: bool = False


class DispositionIn(Schema):
    outcome: DispositionOutcome
    evidence: str = Field(min_length=1)


class SettlementIn(Schema):
    status: Literal[
        "DUE",
        "PAYMENT_REPORTED",
        "SETTLED_CONFIRMED",
        "DISPUTED",
        "OVERDUE",
        "CANCELLED",
    ]
    reference: str = Field(min_length=1)


class InspectionIn(Schema):
    outcome: Literal[
        "ACCEPT_AS_AGREED",
        "REVISE_PRICE",
        "FURTHER_INSPECTION",
        "REJECT_PATHWAY",
        "POSSIBLE_HAZARD",
    ]
    evidence: str = Field(min_length=1)
    notes: str = Field(min_length=1)
    price_paise: int | None = Field(default=None, ge=0)


class EntityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    created_at: str
    data: dict


class HealthResponse(Schema):
    status: Literal["ok"]
    rule_version: str
    settlement: Literal["record-only"]


class ErrorDetail(Schema):
    code: str
    message: str
    field: str | None = None
    blocking: bool = True
    next_action: str | None = None
