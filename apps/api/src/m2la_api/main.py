"""MuleSoft to Logic Apps Standard Migration API entrypoint."""

import os

import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="MuleSoft to Logic Apps Migration API",
    description="Converts MuleSoft projects to Azure Logic Apps Standard",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


def main() -> None:
    """Run the API server."""
    host = os.getenv("M2LA_HOST", "127.0.0.1")
    port = int(os.getenv("M2LA_PORT", "8000"))
    uvicorn.run("m2la_api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
