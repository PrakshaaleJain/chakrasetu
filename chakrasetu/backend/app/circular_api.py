from fastapi import APIRouter

router = APIRouter()
from .operation_registry_api import router as operation_registry_api

router.include_router(operation_registry_api)
from .assessment_api import router as assessment_api

router.include_router(assessment_api)
from .circular_items_api import router as circular_items_api

router.include_router(circular_items_api)
from .transformation_api import router as transformation_api

router.include_router(transformation_api)
from .products_api import router as products_api

router.include_router(products_api)
from .materials_api import router as materials_api

router.include_router(materials_api)
from .traceability_api import router as traceability_api

router.include_router(traceability_api)
