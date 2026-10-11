import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.db import Base, get_db
from app.main import app
from app.seed import seed


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        seed(db)

        def override():
            with Session(engine, expire_on_commit=False) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        app.dependency_overrides[get_db] = override
        yield TestClient(app)
        app.dependency_overrides.clear()


@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer demo-originator-local-only",
        "Idempotency-Key": "test-key",
    }


# Actor impersonation is isolated to regression-test dependency overrides.
@pytest.fixture(autouse=True)
def regression_actor_override(request):
    if "real_auth" in request.keywords:
        yield
        return
    from fastapi import Depends, Header
    from app.auth import current_user
    from app import models as m
    from app.common import fail

    def actor(authorization: str = Header(default=""), db=Depends(get_db)):
        token = authorization.removeprefix("Bearer ")
        if not token.startswith("demo-") or not token.endswith("-local-only"):
            fail("UNAUTHENTICATED", "Test actor required", status=401)
        user = db.get(m.User, token[5:-11])
        if not user or not user.active:
            fail("UNAUTHENTICATED", "Test actor invalid", status=401)
        return user

    app.dependency_overrides[current_user] = actor
    yield
    app.dependency_overrides.pop(current_user, None)
