"""Explicit first-administrator and development-only account provisioning."""

import argparse, getpass, secrets, os
from sqlalchemy import select
from . import models as m
from .db import engine, SessionLocal
from .migrations import migrate
from .security_api import password_hasher, revoke
from .common import audit


def provision(db, user, email, password, roles, admin=False):
    account = db.scalar(select(m.Account).where(m.Account.user_id == user.id))
    if not account:
        account = m.Account(
            user_id=user.id,
            email=email,
            password_hash=password_hasher.hash(password),
            platform_admin=admin,
        )
        db.add(account)
    else:
        account.email = email
        account.password_hash = password_hasher.hash(password)
        account.platform_admin = admin
    db.flush()
    if not db.scalar(
        select(m.OrganisationAccount).where(
            m.OrganisationAccount.organisation_id == user.organisation_id
        )
    ):
        db.add(
            m.OrganisationAccount(
                organisation_id=user.organisation_id,
                account_id=account.id,
                data={"binding_source": "BOOTSTRAP"},
            )
        )
    user.active = True
    member = db.scalar(
        select(m.Membership).where(
            m.Membership.user_id == user.id,
            m.Membership.organisation_id == user.organisation_id,
        )
    )
    if not member:
        db.add(
            m.Membership(
                user_id=user.id,
                organisation_id=user.organisation_id,
                roles=roles,
                data={"review_scope": "GLOBAL_OPERATIONS"}
                if "REVIEWER" in roles
                else {},
            )
        )
    else:
        member.roles = roles
        member.active = True
        member.data = {
            **member.data,
            "review_scope": "GLOBAL_OPERATIONS" if "REVIEWER" in roles else None,
        }
    revoke(db, user.id)
    audit(db, user, "user", user, "CLI_ACCOUNT_PROVISIONED", platform_admin=admin)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin", action="store_true")
    parser.add_argument("--demo", action="store_true")
    opts = parser.parse_args()
    if opts.admin == opts.demo:
        parser.error("Select exactly one of --admin or --demo")
    migrate(engine)
    with SessionLocal() as db:
        if opts.demo:
            if os.getenv("APP_ENV", "development") != "development":
                parser.error("Demo provisioning is development-only")
            from .seed import seed, DEMO_ACTORS

            seed(db)
            password = os.getenv("CHAKRA_DEMO_PASSWORD") or getpass.getpass(
                "Choose a local demo password (12+ characters): "
            )
            if len(password) < 12:
                parser.error("Password must be at least 12 characters")
            for id, _, r, _ in DEMO_ACTORS:
                extra = {
                    "buyer": ["REFURBISHER", "TECHNICIAN"],
                    "recycler": ["RECYCLER"],
                    "secondlife": ["SECOND_LIFE"],
                    "specialist": ["TECHNICIAN"],
                }.get(id, [])
                provision(
                    db,
                    db.get(m.User, id),
                    id + "@demo.chakrasetu.local",
                    password,
                    [r, *extra],
                )
            for id, r in [
                ("technician", "TECHNICIAN"),
                ("processor", "PROCESSOR"),
                ("refiner", "REFINER"),
                ("manufacturer", "MANUFACTURER"),
                ("customer", "CUSTOMER"),
            ]:
                provision(
                    db, db.get(m.User, id), id + "@demo.chakrasetu.local", password, [r]
                )
            print(
                "Development accounts provisioned. Email: <actor-id>@demo.chakrasetu.local; password is the one you supplied."
            )
        else:
            if db.scalar(select(m.Account).where(m.Account.platform_admin == True)):
                parser.error(
                    "First administrator already exists; use authenticated administration"
                )
            email = input("Administrator email: ").strip().lower()
            password = getpass.getpass("Administrator password (12+ characters): ")
            if len(password) < 12 or "@" not in email:
                parser.error("Valid email and 12+ character password required")
            org = m.Organisation(
                name="Platform administration", role="PLATFORM", data={"internal": True}
            )
            db.add(org)
            db.flush()
            user = m.User(
                name="Platform administrator",
                organisation_id=org.id,
                role="ORG_ADMIN",
                token_hash="disabled-" + secrets.token_hex(32),
                data={},
            )
            db.add(user)
            db.flush()
            provision(db, user, email, password, ["ORG_ADMIN", "REVIEWER"], admin=True)
            print(
                "First administrator created. Sign in using your supplied credentials."
            )
        db.commit()


if __name__ == "__main__":
    main()
