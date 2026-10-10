from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine
from . import models


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    from sqlalchemy import select
    from .db import SessionLocal

    with SessionLocal() as db:
        versions = list(db.scalars(select(models.SchemaVersion.version)).all())
        if versions and versions != [1]:
            raise RuntimeError(
                "Unsupported database schema version; migrate or reset the demo explicitly."
            )
        if not versions:
            db.add(models.SchemaVersion(version=1))
            db.commit()
    yield


app = FastAPI(title="ChakraSetu", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
from .schemas import HealthResponse


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "rule_version": "chakra-1.0", "settlement": "record-only"}


from .registry_api import router as registry

app.include_router(registry)
from .intake_api import router as intake
from .commercial_api import router as commercial

app.include_router(intake)
app.include_router(commercial)
from .logistics_api import router as logistics

app.include_router(logistics)
from .shipment_api import router as shipment
from .exception_api import router as exceptions
from .receiving_api import router as receiving

app.include_router(shipment)
app.include_router(exceptions)
app.include_router(receiving)
from .consolidation_api import router as consolidation

app.include_router(consolidation)
