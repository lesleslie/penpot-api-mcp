"""Base async HTTP client with httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from penpot_api_mcp.config.settings import PenpotSettings

logger = logging.getLogger(__name__)

_TRANSIT_HEADERS = {
    "Content-Type": "application/transit+json",
    "Accept": "application/transit+json",
}
_JSON_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


class BaseHTTPClient:
    def __init__(self, settings: PenpotSettings) -> None:
        self._settings = settings
        self._base_url = str(settings.base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # Carry over any cookies from a closed client so session auth
            # survives a transport error + reconnect.
            prior_cookies = dict(self._client.cookies) if self._client else {}
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._settings.request_timeout,
                limits=httpx.Limits(max_connections=self._settings.max_connections),
                cookies=prior_cookies,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        transit: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        client = await self._get_client()
        headers = dict(_TRANSIT_HEADERS if transit else _JSON_HEADERS)
        if extra_headers:
            headers.update(extra_headers)
        response = await client.post(path, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
