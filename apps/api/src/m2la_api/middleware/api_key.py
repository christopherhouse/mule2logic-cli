"""POC API key authentication middleware.

This is temporary auth for the proof-of-concept phase and will be replaced
by Microsoft Entra ID authentication in a future iteration.
"""

from fastapi import Security
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from m2la_api.config.settings import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """Validate the ``X-API-Key`` header against the configured secret.

    Behaviour:
    * If ``M2LA_API_KEY`` is empty/unset the check is skipped so that local
      development works without any key.
    * If ``M2LA_API_KEY`` **is** set, every protected request must provide a
      matching ``X-API-Key`` header – otherwise a ``401`` is returned.

    Returns the validated key (or *None* when auth is disabled).
    """
    configured_key = get_settings().api_key
    if not configured_key:
        # Auth disabled – allow all requests through (local-dev convenience).
        return None

    if not api_key or api_key != configured_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
