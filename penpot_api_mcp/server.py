"""FastMCP server for the Penpot REST API."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Final

from fastmcp import FastMCP

from penpot_api_mcp import __version__
from penpot_api_mcp.clients import PenpotClient
from penpot_api_mcp.config import get_settings
from penpot_api_mcp.tools.profiles import apply_penpot_api_tool_profile

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from penpot_api_mcp.config import PenpotSettings

logger = logging.getLogger(__name__)

APP_NAME: Final = "penpot-api-mcp"
APP_VERSION: Final = __version__


def _run_async_safely(coro: Any) -> Any:
    """Run an async coroutine from a sync context, tolerating a running loop.

    Bridges to the async ``create_app`` via ``asyncio.run`` when no loop
    is running (CLI startup, ``__main__.py``, ``__getattr__``). Falls
    back to a private thread executor when a loop is already running
    (pytest-asyncio tests that import the server module).

    Tool profile dispatch is async because the W0 helper from
    mcp-common 0.18.0 (``_apply_tool_profile``) is async. Per the
    W2b.3 lesson, the sync ``apply_tool_profile`` wrapper raises
    ``RuntimeError`` when called from inside a running event loop, so
    the async path is the only correct entry point for any async
    caller.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Loop already running (pytest-asyncio test). Run the coroutine in a
    # private thread with its own fresh loop, mirroring the W3.4
    # unifi-mcp pattern that avoids blocking the test's loop.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool_executor:
        return pool_executor.submit(asyncio.run, coro).result()


async def create_app(
    settings: PenpotSettings | None = None,
    server: FastMCP | None = None,
) -> FastMCP:
    """Create and configure the MCP server (async production path).

    Async because the W0 tool profile dispatch helper is async.
    Callers from sync contexts (CLI startup, ``get_app``, ``__getattr__``)
    wrap with ``asyncio.run(create_app(...))`` via
    ``_run_async_safely`` (see ``create_app_sync``).

    Args:
        settings: Optional pre-loaded ``PenpotSettings``. When ``None``,
            falls back to ``get_settings()`` (the env-driven loader).
            Pass-through preserves caller-supplied configuration overrides
            (the W4.1 reviewer finding).
        server: Optional pre-constructed ``FastMCP`` server. When
            ``None``, a fresh server is constructed with the lifespan
            wired to the ``PenpotClient`` instance. Tests inject a
            fresh server so they can introspect the registered tool set
            after dispatch.
    """
    if settings is None:
        settings = get_settings()

    # Construct the PenpotClient ONCE upfront. The W0 dispatch lambdas
    # capture the same instance via default-arg capture, AND the
    # lifespan ``finally`` block holds a closure reference so
    # ``await client.close()`` actually closes the registered client.
    # The W4.3 reviewer lesson: long-running servers leak httpx pools
    # if the close call is dropped or refers to a different instance.
    client = PenpotClient(settings)

    if server is None:

        @asynccontextmanager
        async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
            try:
                yield
            finally:
                await client.close()

        server = FastMCP(name=APP_NAME, version=APP_VERSION, lifespan=lifespan)

    # Always register the ``/healthz`` custom route (orchestrator probe)
    # at the module-level — HTTP routes are independent of the W0 tool
    # profile dispatch. Kept identical to the pre-W4 behavior so the
    # load-balancer probe path never breaks.
    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Any) -> Any:
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok"})

    # Apply tool profile dispatch (PENPOT_API_TOOL_PROFILE env var).
    #
    # Replaces the previous direct ``register_all_tools(app, client)``
    # call. The W0 helper from mcp-common 0.18.0+ dispatches by group
    # name and always registers the ``discover_tools`` meta-tool. The
    # default (no env var) remains FULL = all 6 penpot-api-mcp tools
    # — the previous behavior is preserved.
    #
    # Per the W2b.3 keystone: this MUST be the async helper, NOT the
    # sync ``apply_tool_profile`` wrapper (which raises RuntimeError in
    # event loops and would silently break any test that runs
    # ``create_app`` under an async context).
    #
    # The caller-supplied ``settings`` instance AND the single
    # ``client`` instance are forwarded through to the registration
    # paths so test-injected configuration overrides are preserved
    # (the W4.1 round-1 reviewer fix) and the lifespan ``finally``
    # block closes the same instance the tools use (the W4.3 reviewer
    # fix).
    await apply_penpot_api_tool_profile(server, settings, client)

    # Stash the client on the FastMCP instance for tool access; FastMCP's
    # generic type doesn't model this dynamic attribute. Same as
    # pre-W4 — the tools are already registered with this same client
    # via the dispatch lambdas, so this attribute is informational.
    server._penpot_client = client  # ty: ignore[unresolved-attribute]
    return server


def create_app_sync(
    settings: PenpotSettings | None = None,
    server: FastMCP | None = None,
) -> FastMCP:
    """Sync wrapper around the async ``create_app``.

    Bridges via ``_run_async_safely`` so CLI startup, ``__getattr__``
    lazy access (``module.app``, ``module.http_app``), and
    pytest-asyncio tests can all call into the same production path.
    Tests that exercise the real async startup should call
    ``await create_app(...)`` directly so any W2b.3-style regression
    in the production dispatch path is caught.
    """
    return _run_async_safely(create_app(settings, server))


def __getattr__(name: str) -> Any:
    if name == "app":
        return create_app_sync()
    if name == "http_app":
        return create_app_sync().http_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["APP_NAME", "APP_VERSION", "create_app", "create_app_sync"]
