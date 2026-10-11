"""Normalized lifecycle extensions: physical items and many-to-many genealogy."""

from enum import StrEnum
from sqlalchemy import ForeignKey, Enum, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .models import Record


class Operation(StrEnum):
    ASSESSMENT = "ASSESSMENT"
    REFURBISHMENT = "REFURBISHMENT"
    REPURPOSING = "REPURPOSING"
    INTEGRATION = "INTEGRATION"
    DISMANTLING = "DISMANTLING"
    RECYCLING = "RECYCLING"
    PROCESSING = "PROCESSING"
    REFINING = "REFINING"
    MANUFACTURING = "MANUFACTURING"


class JobState(StrEnum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED_REPORTED = "COMPLETED_REPORTED"
    ACCEPTED = "ACCEPTED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class ItemKind(StrEnum):
    BATTERY = "BATTERY"
    PRODUCT = "PRODUCT"
    MATERIAL = "MATERIAL"


class ItemState(StrEnum):
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"
    CONSUMED = "CONSUMED"
    ACCEPTANCE_PENDING = "ACCEPTANCE_PENDING"
    IN_SHIPMENT = "IN_SHIPMENT"
    DEPLOYED = "DEPLOYED"
    RETIRED = "RETIRED"
    HOLD = "HOLD"


class AssessmentState(StrEnum):
    ASSIGNED = "ASSIGNED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ProductState(StrEnum):
    ACCEPTANCE_PENDING = "ACCEPTANCE_PENDING"
    ACCEPTED = "ACCEPTED"
    DEPLOYED = "DEPLOYED"
    RETIRED = "RETIRED"
    HOLD = "HOLD"


class ProductEventType(StrEnum):
    ACCEPT = "ACCEPT"
    DEPLOY = "DEPLOY"
    SERVICE = "SERVICE"
    RETIRE = "RETIRE"
    TAKE_BACK_PROPOSED = "TAKE_BACK_PROPOSED"
    TAKE_BACK_CONFIRMED = "TAKE_BACK_CONFIRMED"
    INCIDENT_REPORTED = "INCIDENT_REPORTED"


class HandoffState(StrEnum):
    PROPOSED = "PROPOSED"
    CONTRACTED = "CONTRACTED"
    BOOKED = "BOOKED"
    PICKED_UP = "PICKED_UP"
    ARRIVED = "ARRIVED"
    RECEIVED = "RECEIVED"
    DISPUTED = "DISPUTED"
    CLOSED = "CLOSED"


class OperationCapability(Record, Base):
    __tablename__ = "operation_capabilities"
    __table_args__ = (UniqueConstraint("facility_id", "operation"),)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    operation: Mapped[Operation] = mapped_column(Enum(Operation, validate_strings=True))
    verified: Mapped[bool] = mapped_column(default=False)
    capacity_kg: Mapped[float | None]
    valid_until: Mapped[str | None]
    chemistries: Mapped[list] = mapped_column(
        __import__("sqlalchemy").JSON, default=list
    )
    formats: Mapped[list] = mapped_column(__import__("sqlalchemy").JSON, default=list)
    material_categories: Mapped[list] = mapped_column(
        __import__("sqlalchemy").JSON, default=list
    )


class Assessment(Record, Base):
    __tablename__ = "assessments"
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    revision_of: Mapped[str | None] = mapped_column(ForeignKey("assessments.id"))
    state: Mapped[AssessmentState] = mapped_column(
        Enum(AssessmentState, validate_strings=True), default=AssessmentState.ASSIGNED
    )
    intended_operation: Mapped[Operation] = mapped_column(
        Enum(Operation, validate_strings=True)
    )
    valid_until: Mapped[str | None]


class CircularItem(Record, Base):
    __tablename__ = "circular_items"
    identifier: Mapped[str] = mapped_column(unique=True)
    kind: Mapped[ItemKind] = mapped_column(Enum(ItemKind, validate_strings=True))
    battery_id: Mapped[str | None] = mapped_column(
        ForeignKey("batteries.id"), unique=True
    )
    owner_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    custodian_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    facility_id: Mapped[str | None] = mapped_column(ForeignKey("facilities.id"))
    mass_kg: Mapped[float | None]
    state: Mapped[ItemState] = mapped_column(
        Enum(ItemState, validate_strings=True), default=ItemState.AVAILABLE
    )


class TransformationJob(Record, Base):
    __tablename__ = "transformation_jobs"
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    operation: Mapped[Operation] = mapped_column(Enum(Operation, validate_strings=True))
    state: Mapped[JobState] = mapped_column(
        Enum(JobState, validate_strings=True), default=JobState.DRAFT
    )
    started_at: Mapped[str | None]
    completed_at: Mapped[str | None]
    accepted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class JobInput(Record, Base):
    __tablename__ = "job_inputs"
    __table_args__ = (UniqueConstraint("job_id", "item_id"),)
    job_id: Mapped[str] = mapped_column(ForeignKey("transformation_jobs.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"))
    mass_kg: Mapped[float]


class JobOutput(Record, Base):
    __tablename__ = "job_outputs"
    job_id: Mapped[str] = mapped_column(ForeignKey("transformation_jobs.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"), unique=True)
    mass_kg: Mapped[float]


class SecondLifeProduct(Record, Base):
    __tablename__ = "second_life_products"
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"), unique=True)
    source_job_id: Mapped[str] = mapped_column(ForeignKey("transformation_jobs.id"))
    integrator_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    intended_application: Mapped[str]
    customer_org_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.id"))
    state: Mapped[ProductState] = mapped_column(
        Enum(ProductState, validate_strings=True),
        default=ProductState.ACCEPTANCE_PENDING,
    )


class ProductEvent(Record, Base):
    __tablename__ = "product_events"
    product_id: Mapped[str] = mapped_column(ForeignKey("second_life_products.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[ProductEventType] = mapped_column(
        Enum(ProductEventType, validate_strings=True)
    )


class RecyclingBatch(Record, Base):
    __tablename__ = "recycling_batches"
    job_id: Mapped[str] = mapped_column(
        ForeignKey("transformation_jobs.id"), unique=True
    )
    identifier: Mapped[str] = mapped_column(unique=True)
    processor_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))


class BatchInput(Record, Base):
    __tablename__ = "batch_inputs"
    __table_args__ = (UniqueConstraint("batch_id", "item_id"),)
    batch_id: Mapped[str] = mapped_column(ForeignKey("recycling_batches.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"))
    mass_kg: Mapped[float]


class MaterialLot(Record, Base):
    __tablename__ = "material_lots"
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"), unique=True)
    source_job_id: Mapped[str] = mapped_column(ForeignKey("transformation_jobs.id"))
    processor_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    category: Mapped[str]
    quantity: Mapped[float]
    unit: Mapped[str] = mapped_column(default="kg")


class DownstreamHandoff(Record, Base):
    __tablename__ = "downstream_handoffs"
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"))
    seller_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    buyer_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    receiver_facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    transporter_id: Mapped[str | None] = mapped_column(ForeignKey("transporters.id"))
    version: Mapped[int] = mapped_column(default=1)
    state: Mapped[HandoffState] = mapped_column(
        Enum(HandoffState, validate_strings=True), default=HandoffState.PROPOSED
    )


class HandoffTerms(Record, Base):
    __tablename__ = "handoff_terms"
    __table_args__ = (UniqueConstraint("handoff_id", "version"),)
    handoff_id: Mapped[str] = mapped_column(ForeignKey("downstream_handoffs.id"))
    version: Mapped[int]
    price_paise: Mapped[int | None]
    payer_org_id: Mapped[str]
    budget_paise: Mapped[int | None]
    confirmations: Mapped[list] = mapped_column(
        __import__("sqlalchemy").JSON, default=list
    )


class ItemCustodyEvent(Record, Base):
    __tablename__ = "item_custody_events"
    handoff_id: Mapped[str] = mapped_column(ForeignKey("downstream_handoffs.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("circular_items.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    previous_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    new_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    event_type: Mapped[str]


class PathwayDecision(Record, Base):
    __tablename__ = "pathway_decisions"
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


# Historical corrections append a new event or assessment revision, never rewrite history.
from sqlalchemy import event
from .models import immutable_event

for cls in [
    ItemCustodyEvent,
    ProductEvent,
    JobInput,
    JobOutput,
    BatchInput,
    PathwayDecision,
]:
    event.listen(cls, "before_update", immutable_event)
    event.listen(cls, "before_delete", immutable_event)


class HandoffAllocation(Record, Base):
    __tablename__ = "handoff_allocations"
    __table_args__ = (UniqueConstraint("handoff_id", "resource_type", "resource_id"),)
    handoff_id: Mapped[str] = mapped_column(ForeignKey("downstream_handoffs.id"))
    resource_type: Mapped[str]
    resource_id: Mapped[str]
    mass_kg: Mapped[float]
    starts_at: Mapped[str]
    ends_at: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
