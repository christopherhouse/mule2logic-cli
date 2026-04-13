"""API route definitions."""

from m2la_api.routes.analyze import router as analyze_router
from m2la_api.routes.health import router as health_router
from m2la_api.routes.transform import router as transform_router
from m2la_api.routes.validate import router as validate_router

__all__ = ["analyze_router", "health_router", "transform_router", "validate_router"]
