import hashlib
from fastapi import Depends, Header
from sqlalchemy import select
from .db import get_db
from . import models as m
from .common import fail, get
from .config import DEMO_MODE


def current_user(authorization: str = Header(default=""), db=Depends(get_db)):
    token = authorization.removeprefix("Bearer ")
    user = db.scalar(
        select(m.User).where(
            m.User.token_hash == hashlib.sha256(token.encode()).hexdigest(),
            m.User.active == True,
        )
    )
    if user and user.data.get("synthetic") and not DEMO_MODE:
        fail("UNAUTHENTICATED", "Synthetic demo login is disabled.", status=401)
    if not user or not get(db, m.Organisation, user.organisation_id).active:
        fail(
            "UNAUTHENTICATED",
            "Select a demo actor or provide a valid token.",
            status=401,
        )
    return user


def role(user, *roles):
    if user.role not in roles:
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
    if user.role == "REVIEWER" or user.organisation_id in [
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
