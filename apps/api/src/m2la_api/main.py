"""MuleSoft to Logic Apps Standard Migration API entrypoint."""

import uvicorn
from fastapi import FastAPI

from m2la_api.config.settings import get_settings
from m2la_api.models.errors import ApiError, api_error_handler
from m2la_api.routes import analyze_router, health_router, transform_router, validate_router

app = FastAPI(
    title="MuleSoft to Logic Apps Migration API",
    description="Converts MuleSoft projects to Azure Logic Apps Standard",
    version="0.1.0",
)

# Register routers
app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(transform_router)
app.include_router(validate_router)

# Register exception handlers
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]


def main() -> None:
    """Run the API server."""
    settings = get_settings()
    uvicorn.run("m2la_api.main:app", host=settings.host, port=settings.port, reload=settings.debug)


if __name__ == "__main__":
    main()
