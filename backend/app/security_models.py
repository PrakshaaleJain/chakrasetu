from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .models import Record
from .db import Base


class Account(Record, Base):
    __tablename__ = "accounts"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    platform_admin: Mapped[bool] = mapped_column(default=False)


class Membership(Record, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organisation_id"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"))
    roles: Mapped[list] = mapped_column(__import__("sqlalchemy").JSON)
    active: Mapped[bool] = mapped_column(default=True)


class AuthSession(Record, Base):
    __tablename__ = "auth_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    membership_id: Mapped[str] = mapped_column(ForeignKey("memberships.id"))
    selected_role: Mapped[str]
    token_hash: Mapped[str] = mapped_column(unique=True)
    csrf_hash: Mapped[str]
    expires_at: Mapped[str]
    revoked: Mapped[bool] = mapped_column(default=False)


class RecoveryToken(Record, Base):
    __tablename__ = "recovery_tokens"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[str]
    used: Mapped[bool] = mapped_column(default=False)


class AuthAttempt(Record, Base):
    __tablename__ = "auth_attempts"
    bucket: Mapped[str] = mapped_column(index=True)
    expires_at: Mapped[str]
