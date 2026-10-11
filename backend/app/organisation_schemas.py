from typing import Literal
from pydantic import Field, field_validator
from .schemas import Schema
from .circular_models import Operation
from .enums import Chemistry, Form, Condition, Pathway
from .registration_schemas import SafetyScope
from .permissions import BUSINESS_ROLES
from .organisation_models import RequestKind, RequestAction


class ProfileIn(Schema):
    display_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    organisation_type: str = Field(default="", max_length=100)
    business_email: str = Field(default="", max_length=254)
    business_phone: str = Field(default="", max_length=40)
    website: str = Field(default="", max_length=500)
    primary_address: str = Field(default="", max_length=1000)
    regions: list[str] = Field(default_factory=list, max_length=30)
    business_identifiers: str = Field(default="", max_length=500)
    contact_visibility: Literal["PUBLIC", "PARTICIPANTS", "PRIVATE"] = "PARTICIPANTS"

    @field_validator("website")
    @classmethod
    def website_valid(cls, v):
        if v and not v.startswith(("https://", "http://")):
            raise ValueError("Use a website address starting with https:// or http://")
        return v

    @field_validator("business_email")
    @classmethod
    def email_valid(cls, v):
        if v and (
            "@" not in v
            or any(c.isspace() for c in v)
            or "." not in v.rsplit("@", 1)[1]
        ):
            raise ValueError("Enter a valid business email address")
        return v.strip()


class Scope(Schema):
    safety: SafetyScope | None = None
    official_name: str | None = Field(default=None, min_length=2, max_length=200)
    role: str | None = None
    operation: Operation | None = None
    pathway: Pathway | None = None
    capacity_kg: float | None = Field(default=None, gt=0, le=10000000)
    chemistries: list[Chemistry] = Field(default_factory=list, max_length=20)
    formats: list[Form] = Field(default_factory=list, max_length=10)
    conditions: list[Condition] = Field(default_factory=list, max_length=20)
    material_categories: list[str] = Field(default_factory=list, max_length=30)
    handling_scope: Literal["ORDINARY", "CONTROLLED_HANDLING"] = "ORDINARY"
    radius_km: float | None = Field(default=None, gt=0, le=3000)
    center: tuple[float, float] | None = None
    description: str = Field(default="", max_length=4000)

    @field_validator("official_name")
    @classmethod
    def name_valid(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Enter an official name with at least two characters")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v):
        if v and v not in BUSINESS_ROLES - {"ORG_ADMIN"}:
            raise ValueError(
                "Choose an operational role; administrator roles are restricted"
            )
        return v

    @field_validator("center")
    @classmethod
    def coordinates(cls, v):
        if v and not (-90 <= v[0] <= 90 and -180 <= v[1] <= 180):
            raise ValueError("Enter valid latitude and longitude")
        return v


class RequestIn(Schema):
    kind: RequestKind
    action: RequestAction = RequestAction.ADD
    target_id: str | None = None
    facility_id: str | None = None
    requested_scope: Scope


class ReviewIn(Schema):
    decision: Literal[
        "INFORMATION_REQUESTED", "APPROVED", "REJECTED", "SUSPENDED", "REMOVED"
    ]
    reason: str = Field(min_length=3, max_length=4000)
    evidence: str = Field(default="", max_length=4000)
    valid_until: str | None = None


class ResponseIn(Schema):
    message: str = Field(min_length=3, max_length=4000)


class FacilityEdit(Schema):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    address: str = Field(default="", max_length=1000)
