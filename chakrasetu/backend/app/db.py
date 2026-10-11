from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 20}
)


@event.listens_for(engine, "connect")
def pragmas(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            from .common import fail

            fail(
                "DATABASE_WRITE_FAILED",
                "The database operation did not complete. Refresh and retry; no successful save has been confirmed.",
                status=503,
            )
        except Exception:
            db.rollback()
            raise
