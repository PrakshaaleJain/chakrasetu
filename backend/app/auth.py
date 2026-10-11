import hashlib, secrets
from types import SimpleNamespace
from fastapi import Depends, Request
from sqlalchemy import select
from .db import get_db
from . import models as m
from .common import fail, get, expired
from .permissions import LEGACY_ROLE
from .config import APP_ENV

COOKIE = "chakra_session"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def current_user(request: Request, db=Depends(get_db, scope="function")):
    token = request.cookies.get(COOKIE, "")
    session = (
        db.scalar(
            select(m.AuthSession).where(m.AuthSession.token_hash == digest(token))
        )
        if token
        else None
    )
    if not session or session.revoked or expired(session.expires_at):
        fail(
            "UNAUTHENTICATED",
            "Please sign in; your session may have expired.",
            status=401,
        )
    user = get(db, m.User, session.user_id)
    if APP_ENV == "production" and user.data.get("synthetic"):
        fail(
            "UNAUTHENTICATED",
            "Synthetic accounts are disabled in production.",
            status=401,
        )
    member = get(db, m.Membership, session.membership_id)
    org = get(db, m.Organisation, member.organisation_id)
    if APP_ENV == "production" and org.synthetic:
        fail(
            "UNAUTHENTICATED",
            "Synthetic organizations are disabled in production.",
            status=401,
        )
    if (
        not user.active
        or not member.active
        or member.user_id != user.id
        or not org.active
        or session.selected_role not in member.roles
    ):
        fail(
            "UNAUTHENTICATED", "Account or organisation access is inactive.", status=401
        )
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not secrets.compare_digest(
            digest(request.headers.get("X-CSRF-Token", "")), session.csrf_hash
        ):
            fail("CSRF_INVALID", "Refresh your session and retry.", status=403)
    if (
        session.selected_role == "REVIEWER"
        and member.data.get("review_scope") != "GLOBAL_OPERATIONS"
    ):
        fail(
            "FORBIDDEN",
            "Reviewer needs an explicitly granted operational review scope.",
            status=403,
        )
    account = db.scalar(select(m.Account).where(m.Account.user_id == user.id))
    request.state.auth_session = session
    return SimpleNamespace(
        id=user.id,
        name=user.name,
        organisation_id=org.id,
        role=LEGACY_ROLE.get(session.selected_role, session.selected_role),
        selected_role=session.selected_role,
        roles=member.roles,
        data=user.data,
        platform_admin=bool(account and account.platform_admin),
        membership_id=member.id,
        review_scope=member.data.get("review_scope"),
    )


def has_role(user, *roles):
    assigned = set(getattr(user, "roles", [user.role]))
    effective = assigned | {LEGACY_ROLE.get(r, r) for r in assigned}
    if (
        "REVIEWER" in effective
        and hasattr(user, "roles")
        and getattr(user, "review_scope", None) != "GLOBAL_OPERATIONS"
    ):
        effective.discard("REVIEWER")
    return bool(effective.intersection(roles))


def role(user, *roles):
    if not has_role(user, *roles):
        fail("FORBIDDEN", "Your role cannot perform this action.", status=403)


def seller(user, asset):
    role(user, "ORIGINATOR")
    if user.organisation_id != asset.originator_org_id:
        fail("FORBIDDEN", "This asset belongs to another originator.", status=403)


def party(user, tx):
    role(user, "ORIGINATOR", "BUYER")
    if user.organisation_id not in [tx.seller_org_id, tx.buyer_org_id]:
        fail(
            "FORBIDDEN", "Only transaction parties may perform this action.", status=403
        )


def can_view_asset(db, user, asset):
    if has_role(user, "REVIEWER") or user.organisation_id in [
        asset.originator_org_id,
        asset.owner_org_id,
        asset.current_holder_org_id,
    ]:
        return True
    txs = db.scalars(
        select(m.SaleTransaction).where(m.SaleTransaction.asset_id == asset.id)
    ).all()
    for tx in txs:
        if user.organisation_id in [tx.seller_org_id, tx.buyer_org_id]:
            return True
        for quote in db.scalars(
            select(m.TransportQuote).where(m.TransportQuote.transaction_id == tx.id)
        ).all():
            if (
                get(db, m.TransporterProfile, quote.transporter_id).organisation_id
                == user.organisation_id
            ):
                return True
    return False
