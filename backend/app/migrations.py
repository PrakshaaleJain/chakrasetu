from sqlalchemy import text, inspect
from .db import Base


def migrate(engine):
    # v2 adds normalized tables; all v1 columns and records remain intact.
    if inspect(engine).has_table("schema_version"):
        with engine.connect() as connection:
            versions = list(
                connection.execute(text("SELECT version FROM schema_version")).scalars()
            )
            if any(v not in (1, 2, 3, 4) for v in versions):
                raise RuntimeError(
                    "Unsupported schema version; explicit migration required"
                )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        versions = list(
            connection.execute(text("SELECT version FROM schema_version")).scalars()
        )
        if any(v not in (1, 2, 3, 4) for v in versions):
            raise RuntimeError(
                "Unsupported schema version; explicit migration required"
            )
        connection.execute(text("DELETE FROM schema_version"))
        connection.execute(text("INSERT INTO schema_version(version) VALUES(4)"))

    # Bind one primary organisation account without removing legacy identities.
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from . import models as m

    with Session(engine) as db:
        for org in db.scalars(select(m.Organisation)):
            if db.scalar(
                select(m.OrganisationAccount).where(
                    m.OrganisationAccount.organisation_id == org.id
                )
            ):
                continue
            account = db.scalar(
                select(m.Account)
                .join(m.User, m.Account.user_id == m.User.id)
                .where(m.User.organisation_id == org.id)
                .order_by(m.Account.created_at, m.Account.id)
            )
            if account:
                db.add(
                    m.OrganisationAccount(
                        organisation_id=org.id,
                        account_id=account.id,
                        data={"binding_source": "MIGRATED_LEGACY"},
                    )
                )
        # Preserve pre-redesign approvals as legacy operating permissions. Do not infer PBS.
        for asset in db.scalars(select(m.BatteryAsset)):
            if "registration" not in asset.data:
                approved = asset.state not in [
                    "DRAFT",
                    "HOLD",
                    "REVIEW_REQUIRED",
                    "NEEDS_INFORMATION",
                ]
                asset.data = {
                    **asset.data,
                    "registration": {
                        "status": "APPROVED" if approved else "PENDING_REVIEW",
                        "revision": 0,
                        "history": [
                            {
                                "action": "LEGACY_STATE_MIGRATION",
                                "timestamp": m.now(),
                                "previous_state": asset.state,
                            }
                        ],
                        "approval_source": "LEGACY_OPERATING_STATE",
                    },
                }
        db.commit()
