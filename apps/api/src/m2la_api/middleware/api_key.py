"""POC API token authentication middleware.

This is temporary auth for the proof-of-concept phase and will be replaced
by Microsoft Entra ID authentication in a future iteration.
"""

from fastapi import Security
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from m2la_api.config.settings import get_settings

_api_token_header = APIKeyHeader(name="x-api-token", auto_error=False)


async def verify_api_key(
    api_token: str | None = Security(_api_token_header),
) -> str | None:
    """Validate the ``x-api-token`` header against the configured secret.

    Behaviour:
    * If ``M2LA_API_TOKEN`` is empty/unset the check is skipped so that local
      development works without any key.
    * If ``M2LA_API_TOKEN`` **is** set, every protected request must provide a
      matching ``x-api-token`` header – otherwise a ``401`` is returned.

    Returns the validated token (or *None* when auth is disabled).
    """
    configured_token = get_settings().api_token
    if not configured_token:
        # Auth disabled – allow all requests through (local-dev convenience).
        return None

    if not api_token or api_token != configured_token:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )
    return api_token
