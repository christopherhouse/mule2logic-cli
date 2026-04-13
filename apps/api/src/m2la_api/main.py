"""MuleSoft to Logic Apps Standard Migration API entrypoint."""

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
    uvicorn.run("m2la_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
