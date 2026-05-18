"""FastMCP server for the Penpot REST API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Final

from fastmcp import FastMCP

from penpot_api_mcp import __version__
from penpot_api_mcp.clients import PenpotClient
from penpot_api_mcp.config import get_settings
from penpot_api_mcp.tools import register_all_tools

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

APP_NAME: Final = "penpot-api-mcp"
APP_VERSION: Final = __version__


def create_app() -> FastMCP:
    settings = get_settings()
    client = PenpotClient(settings)

    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await client.close()

    app = FastMCP(name=APP_NAME, version=APP_VERSION, lifespan=lifespan)

    @app.custom_route("/health", methods=["GET"])
    async def health_check(request: Any) -> Any:
        from starlette.responses import JSONResponse
        return JSONResponse({"status": "ok", "service": "penpot-api", "version": APP_VERSION})

    @app.custom_route("/healthz", methods=["GET"])
    async def healthz(request: Any) -> Any:
        from starlette.responses import JSONResponse
        return JSONResponse({"status": "ok"})

    register_all_tools(app, client)
    app._penpot_client = client  # type: ignore[attr-defined]
    return app


def __getattr__(name: str) -> Any:
    if name == "app":
        return create_app()
    if name == "http_app":
        return create_app().http_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["create_app", "APP_NAME", "APP_VERSION"]
