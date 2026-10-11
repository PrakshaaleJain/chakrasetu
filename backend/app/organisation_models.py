from sqlalchemy import ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column
from .models import Record
from .db import Base


class OrganisationAccount(Record, Base):
    __tablename__ = "organisation_accounts"
    organisation_id: Mapped[str] = mapped_column(
        ForeignKey("organisations.id"), unique=True
    )
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), unique=True)


from enum import StrEnum


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"
    WITHDRAWN = "WITHDRAWN"


class RequestKind(StrEnum):
    ROLE = "ROLE"
    OPERATION = "OPERATION"
    PATHWAY = "PATHWAY"
    TRANSPORT = "TRANSPORT"
    IDENTITY = "IDENTITY"
    FACILITY = "FACILITY"


class RequestAction(StrEnum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    REMOVE = "REMOVE"


class CapabilityRequest(Record, Base):
    __tablename__ = "capability_requests"
    organisation_id: Mapped[str] = mapped_column(
        ForeignKey("organisations.id"), index=True
    )
    submitted_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[RequestKind] = mapped_column(Enum(RequestKind, validate_strings=True))
    action: Mapped[RequestAction] = mapped_column(
        Enum(RequestAction, validate_strings=True)
    )
    target_id: Mapped[str | None]
    facility_id: Mapped[str | None] = mapped_column(ForeignKey("facilities.id"))
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, validate_strings=True), default=RequestStatus.PENDING
    )
    requested_scope: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[str]
