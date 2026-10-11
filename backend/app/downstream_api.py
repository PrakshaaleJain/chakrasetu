from fastapi import APIRouter

router = APIRouter()
from .downstream_scope_api import router as downstream_scope_api

router.include_router(downstream_scope_api)
from .downstream_commercial_api import router as downstream_commercial_api

router.include_router(downstream_commercial_api)
from .downstream_logistics_api import router as downstream_logistics_api

router.include_router(downstream_logistics_api)
from .downstream_shipments_api import router as downstream_shipments_api

router.include_router(downstream_shipments_api)
