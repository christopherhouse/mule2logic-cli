"""Middleware components for the API."""

from m2la_api.middleware.api_key import verify_api_key

__all__ = ["verify_api_key"]
