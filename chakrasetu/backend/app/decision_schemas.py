"""Typed pathway inputs; financial assertions never confer a qualification."""

from typing import Literal
from datetime import datetime
from pydantic import Field, model_validator
from .base_schemas import Schema
from .registration_schemas import PBSLevel

DecisionPath = Literal[
    "AUTOMOTIVE", "REFURBISHMENT", "SECOND_LIFE", "RECYCLING", "ASSESSMENT"
]
COMPONENTS = {
    "AUTOMOTIVE": [
        "diagnostics",
        "repair",
        "requalification",
        "transport",
        "maintenance",
        "risk",
    ],
    "REFURBISHMENT": [
        "diagnostics",
        "parts",
        "labor",
        "requalification",
        "transport",
        "warranty",
        "risk",
    ],
    "SECOND_LIFE": [
        "assessment",
        "transport",
        "repurposing",
        "integration",
        "installation",
        "maintenance",
        "warranty",
        "risk",
        "end_of_service",
    ],
    "RECYCLING": [
        "collection",
        "transport",
        "packaging",
        "handling",
        "processing",
        "other",
    ],
    "ASSESSMENT": ["assessment", "transport", "handling"],
}


class FinancialValue(Schema):
    amount_paise: int = Field(ge=0, le=10**13, strict=True)
    source: Literal["OWNER_ESTIMATE", "ORGANISATION_ESTIMATE", "ADMIN_ASSUMPTION"]
    reference: str = Field(min_length=3, max_length=1000)
    recorded_at: datetime
    valid_until: datetime
    year: int = Field(default=0, ge=0, le=30)
    repeat_through_year: int | None = Field(default=None, ge=0, le=30)
    uncertainty_paise: int = Field(default=0, ge=0, le=10**13, strict=True)

    @model_validator(mode="after")
    def timestamps(self):
        if (
            not self.recorded_at.tzinfo
            or not self.valid_until.tzinfo
            or self.valid_until <= self.recorded_at
        ):
            raise ValueError(
                "Financial inputs require timezone-aware dates and a validity after recording."
            )
        if (
            self.repeat_through_year is not None
            and self.repeat_through_year < self.year
        ):
            raise ValueError(
                "Recurring cash flow must end at or after its starting year."
            )
        return self


class PathwayFinance(Schema):
    currency: Literal["INR"] = "INR"
    basis: Literal["NET_TRANSACTION", "NPV"] = "NET_TRANSACTION"
    perspective: Literal["WHOLE_PATHWAY", "ORIGINATOR_TRANSACTION"] = "WHOLE_PATHWAY"
    horizon_years: int = Field(default=0, ge=0, le=30)
    discount_rate: float | None = Field(default=None, ge=0, le=1)
    benefits: list[FinancialValue] = Field(default_factory=list, max_length=40)
    costs: dict[str, FinancialValue] = Field(default_factory=dict, max_length=20)
    offer_id: str | None = Field(default=None, max_length=100)
    transport_quote_id: str | None = Field(default=None, max_length=100)
    facility_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def comparable_basis(self):
        values = [*self.benefits, *self.costs.values()]
        if self.basis == "NET_TRANSACTION" and (
            self.horizon_years
            or self.discount_rate is not None
            or any(x.year or x.repeat_through_year is not None for x in values)
        ):
            raise ValueError(
                "A net transaction comparison uses year zero without a discount rate."
            )
        if self.basis == "NPV" and (
            not self.horizon_years
            or self.discount_rate is None
            or any(
                x.year > self.horizon_years
                or (
                    x.repeat_through_year is not None
                    and x.repeat_through_year > self.horizon_years
                )
                for x in values
            )
        ):
            raise ValueError(
                "NPV requires a positive common horizon, discount rate, and in-horizon cash flows."
            )
        if self.offer_id and self.benefits:
            raise ValueError(
                "Use an existing purchase offer OR estimated benefits, never both."
            )
        if self.offer_id and (
            self.perspective != "ORIGINATOR_TRANSACTION"
            or self.basis != "NET_TRANSACTION"
        ):
            raise ValueError(
                "Purchase offers use the originator transaction perspective and net transaction basis."
            )
        if self.transport_quote_id and "transport" in self.costs:
            raise ValueError(
                "Use a transport quote OR a transport estimate, never both."
            )
        return self


class DecisionIn(Schema):
    economics: dict[DecisionPath, PathwayFinance] = Field(
        default_factory=dict, max_length=5
    )

    @model_validator(mode="after")
    def known_costs(self):
        for path, finance in self.economics.items():
            if set(finance.costs) - set(COMPONENTS[path]):
                raise ValueError(
                    f"Unsupported or duplicated cost component for {path}."
                )
        return self


class TechnicalFindings(Schema):
    fault_identified: bool | None = None
    repairable: bool | None = None
    parts_available: bool | None = None
    requalification_possible: bool | None = None
    automotive_application_passed: bool | None = None
    second_life_application_passed: bool | None = None
    remaining_life_adequate: bool | None = None
    application_reference: str = Field(min_length=3, max_length=2000)


class ExplorerIn(Schema):
    pbs: PBSLevel = "L1"
    soh_percent: float | None = Field(default=85, ge=0, le=100)
    measurements_available: bool = True
    repairable: bool | None = None
    critical_hazard: bool = False
    application_qualified: bool = True
    application: Literal["VEHICLE", "STATIONARY", "UNASSESSED"] = "VEHICLE"
    qualified_receiver: bool = True
    qualified_transporter: bool = True
    quotes_available: bool = False


class OverrideIn(Schema):
    pathway: DecisionPath
    reason: str = Field(min_length=10, max_length=4000)
