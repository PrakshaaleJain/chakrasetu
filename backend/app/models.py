from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .enums import (
    BatteryState,
    ShipmentState,
    Verification,
    Chemistry,
    Form,
    Condition,
    Pathway,
    ReservationState,
    QuoteState,
    ExceptionState,
    SettlementState,
    TransactionState,
    ListingState,
    OfferState,
)


def now():
    return datetime.now(timezone.utc).isoformat()


def ident():
    return uuid4().hex[:16]


class Record:
    id: Mapped[str] = mapped_column(String, primary_key=True, default=ident)
    created_at: Mapped[str] = mapped_column(String, default=now)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Organisation(Record, Base):
    __tablename__ = "organisations"
    name: Mapped[str]
    role: Mapped[str]
    verification: Mapped[Verification] = mapped_column(
        Enum(Verification, validate_strings=True), default=Verification.UNVERIFIED
    )
    active: Mapped[bool] = mapped_column(default=True)
    synthetic: Mapped[bool] = mapped_column(default=False)


class User(Record, Base):
    __tablename__ = "users"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    name: Mapped[str]
    role: Mapped[str]
    token_hash: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)


class Facility(Record, Base):
    __tablename__ = "facilities"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    name: Mapped[str]
    kind: Mapped[str]
    lat: Mapped[float]
    lng: Mapped[float]
    active: Mapped[bool] = mapped_column(default=True)
    registration: Mapped[Verification] = mapped_column(
        Enum(Verification, validate_strings=True), default=Verification.UNVERIFIED
    )
    valid_until: Mapped[str]


class FacilityCapability(Record, Base):
    __tablename__ = "facility_capabilities"
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    pathway: Mapped[Pathway] = mapped_column(Enum(Pathway, validate_strings=True))
    verification: Mapped[Verification] = mapped_column(
        Enum(Verification, validate_strings=True), default=Verification.UNVERIFIED
    )
    capacity_kg: Mapped[float]
    available_kg: Mapped[float]
    valid_until: Mapped[str]


class TransporterProfile(Record, Base):
    __tablename__ = "transporters"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    name: Mapped[str]
    verification: Mapped[Verification] = mapped_column(
        Enum(Verification, validate_strings=True), default=Verification.UNVERIFIED
    )
    active: Mapped[bool] = mapped_column(default=True)
    capacity_kg: Mapped[float]
    valid_until: Mapped[str]


class BatteryAsset(Record, Base):
    __tablename__ = "batteries"
    originator_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    owner_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    custodian_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    current_holder_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    internal_id: Mapped[str] = mapped_column(unique=True)
    chemistry: Mapped[Chemistry] = mapped_column(
        Enum(
            Chemistry,
            values_callable=lambda e: [x.value for x in e],
            validate_strings=True,
        )
    )
    form: Mapped[Form] = mapped_column(Enum(Form, validate_strings=True))
    condition: Mapped[Condition] = mapped_column(Enum(Condition, validate_strings=True))
    mass_kg: Mapped[float | None]
    quantity: Mapped[int]
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    authority_confirmed: Mapped[bool] = mapped_column(default=False)
    state: Mapped[BatteryState] = mapped_column(
        Enum(BatteryState), default=BatteryState.DRAFT
    )


class EvidenceDocument(Record, Base):
    __tablename__ = "evidence_documents"
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    uploader_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str]
    filename: Mapped[str]
    checksum: Mapped[str]
    version: Mapped[int]
    review_status: Mapped[str] = mapped_column(default="DOCUMENT_SUBMITTED")


class Listing(Record, Base):
    __tablename__ = "listings"
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    seller_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    status: Mapped[ListingState] = mapped_column(
        Enum(ListingState, validate_strings=True), default=ListingState.OPEN
    )
    expires_at: Mapped[str]


class Offer(Record, Base):
    __tablename__ = "offers"
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"))
    buyer_org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    pathway: Mapped[Pathway] = mapped_column(Enum(Pathway, validate_strings=True))
    price_paise: Mapped[int]
    expires_at: Mapped[str]
    status: Mapped[OfferState] = mapped_column(
        Enum(OfferState, validate_strings=True), default=OfferState.SUBMITTED
    )


class SaleTransaction(Record, Base):
    __tablename__ = "transactions"
    offer_id: Mapped[str] = mapped_column(ForeignKey("offers.id"), unique=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    seller_org_id: Mapped[str]
    buyer_org_id: Mapped[str]
    facility_id: Mapped[str]
    pathway: Mapped[Pathway] = mapped_column(Enum(Pathway, validate_strings=True))
    terms_version: Mapped[int] = mapped_column(default=1)
    status: Mapped[TransactionState] = mapped_column(
        Enum(TransactionState, validate_strings=True),
        default=TransactionState.AWAITING_CONFIRMATION,
    )
    logistics_status: Mapped[str] = mapped_column(default="PENDING")


class TermsVersion(Record, Base):
    __tablename__ = "terms_versions"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    version: Mapped[int]
    payer_org_id: Mapped[str]
    budget_paise: Mapped[int]
    price_paise: Mapped[int]
    confirmations: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("transaction_id", "version"),)


class RoutePlan(Record, Base):
    __tablename__ = "route_plans"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    terms_version: Mapped[int]
    hub_id: Mapped[str | None]
    distance_km: Mapped[float]
    hours: Mapped[float]
    estimated_cost_paise: Mapped[int | None]
    score: Mapped[float]
    expires_at: Mapped[str]


class TransportQuote(Record, Base):
    __tablename__ = "transport_quotes"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    route_id: Mapped[str] = mapped_column(ForeignKey("route_plans.id"))
    transporter_id: Mapped[str] = mapped_column(ForeignKey("transporters.id"))
    total_paise: Mapped[int | None]
    terms_version: Mapped[int]
    expires_at: Mapped[str]
    status: Mapped[QuoteState] = mapped_column(
        Enum(QuoteState, validate_strings=True), default=QuoteState.SUBMITTED
    )


class CapacityReservation(Record, Base):
    __tablename__ = "capacity_reservations"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    resource_type: Mapped[str]
    resource_id: Mapped[str]
    mass_kg: Mapped[float]
    starts_at: Mapped[str]
    ends_at: Mapped[str]
    expires_at: Mapped[str]
    status: Mapped[ReservationState] = mapped_column(
        Enum(ReservationState, validate_strings=True), default=ReservationState.HELD
    )


class Shipment(Record, Base):
    __tablename__ = "shipments"
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), unique=True
    )
    route_id: Mapped[str] = mapped_column(ForeignKey("route_plans.id"))
    quote_id: Mapped[str] = mapped_column(ForeignKey("transport_quotes.id"))
    state: Mapped[ShipmentState] = mapped_column(
        Enum(ShipmentState), default=ShipmentState.BOOKED
    )


class ShipmentItem(Record, Base):
    __tablename__ = "shipment_items"
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    quantity: Mapped[int]
    mass_kg: Mapped[float]
    receipt: Mapped[str] = mapped_column(default="PENDING")
    __table_args__ = (UniqueConstraint("shipment_id", "asset_id"),)


class CustodyEvent(Record, Base):
    __tablename__ = "custody_events"
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    actor_id: Mapped[str]
    previous_holder: Mapped[str]
    new_holder: Mapped[str]
    event_type: Mapped[str]


class TelemetryEvent(Record, Base):
    __tablename__ = "telemetry_events"
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    source: Mapped[str] = mapped_column(default="SIMULATED")
    actor_id: Mapped[str]
    alert: Mapped[bool]


class ExceptionCase(Record, Base):
    __tablename__ = "exceptions"
    object_type: Mapped[str]
    object_id: Mapped[str]
    category: Mapped[str]
    severity: Mapped[str]
    owner_org_id: Mapped[str]
    status: Mapped[ExceptionState] = mapped_column(
        Enum(ExceptionState, validate_strings=True), default=ExceptionState.OPEN
    )
    next_action: Mapped[str]
    due_at: Mapped[str]
    resolution: Mapped[str | None]


class DispositionRecord(Record, Base):
    __tablename__ = "dispositions"
    asset_id: Mapped[str] = mapped_column(ForeignKey("batteries.id"))
    facility_id: Mapped[str]
    actor_id: Mapped[str]
    outcome: Mapped[str]
    review_status: Mapped[str] = mapped_column(default="SELF_REPORTED")


class SettlementRecord(Record, Base):
    __tablename__ = "settlements"
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), unique=True
    )
    status: Mapped[SettlementState] = mapped_column(
        Enum(SettlementState, validate_strings=True), default=SettlementState.NOT_DUE
    )
    payer_org_id: Mapped[str]
    payee_org_id: Mapped[str]
    amount_paise: Mapped[int]


class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[str]
    object_type: Mapped[str]
    object_id: Mapped[str]
    action: Mapped[str]


class IdempotencyRecord(Record, Base):
    __tablename__ = "idempotency"
    actor_id: Mapped[str]
    key: Mapped[str]
    operation: Mapped[str]
    fingerprint: Mapped[str]
    response: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("actor_id", "key", "operation"),)


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    version: Mapped[int] = mapped_column(primary_key=True)


# ORM writes cannot amend or delete critical historical event rows.
from sqlalchemy import event


def immutable_event(*args):
    raise ValueError("Critical history is append-only; create a compensating event.")


for event_model in (CustodyEvent, AuditEvent):
    event.listen(event_model, "before_update", immutable_event)
    event.listen(event_model, "before_delete", immutable_event)


class Consolidation(Record, Base):
    __tablename__ = "consolidations"
    hub_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    facility_id: Mapped[str] = mapped_column(ForeignKey("facilities.id"))
    transporter_id: Mapped[str] = mapped_column(ForeignKey("transporters.id"))
    status: Mapped[str] = mapped_column(default="AWAITING_APPROVAL")
    approvals: Mapped[list] = mapped_column(JSON, default=list)


class ConsolidationMember(Record, Base):
    __tablename__ = "consolidation_members"
    consolidation_id: Mapped[str] = mapped_column(ForeignKey("consolidations.id"))
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), unique=True)
