from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db import Base
from app.seed import seed
from app import models as m


def test_seed_registry_and_screen():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        assert len(db.scalars(select(m.Organisation)).all()) == 11
        assert db.get(m.BatteryAsset, "battery-1").state == "READY_FOR_LISTING"
        assert db.get(m.BatteryAsset, "battery-3").state == "HOLD"
        assert db.get(m.BatteryAsset, "battery-2").mass_kg is None
