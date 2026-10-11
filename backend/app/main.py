from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine
from . import models
from .config import ALLOWED_ORIGINS


@asynccontextmanager
async def lifespan(app):
    from .migrations import migrate

    migrate(engine)
    yield


app = FastAPI(title="ChakraSetu", version="3.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Token"],
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

from .security_api import router as security

app.include_router(security)


@app.middleware("http")
async def security_headers(request, call_next):
    from fastapi.responses import JSONResponse

    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and request.headers.get("origin")
        and request.headers["origin"] not in ALLOWED_ORIGINS
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "ORIGIN_FORBIDDEN",
                    "message": "Request origin is not allowed.",
                }
            },
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


from .circular_api import router as circularity

app.include_router(circularity)
from .downstream_api import router as downstream

app.include_router(downstream)
from .pathway_api import router as pathways

app.include_router(pathways)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Do not echo submitted passwords, recovery tokens or document bodies in errors.
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                for e in error.errors()
            ]
        },
    )


from .organisation_api import router as organisations

app.include_router(organisations)
