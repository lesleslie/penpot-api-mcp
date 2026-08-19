"""MCP tool registration for penpot-api-mcp.

Each ``register_<group>_tools()`` function attaches a group of MCP tools to
a ``FastMCP`` server. The pre-W4 entry points take a pre-constructed
``PenpotClient`` (the old sync ``create_app`` constructed the client
once and reused it). The W4 ``_for_profile`` wrappers take
``(mcp, settings, client)`` so the W0 dispatch helper in mcp-common
0.18.0 can bind the caller's settings + client via lambda capture without
re-loading either from the environment.

The W4 split is load-bearing for two reasons:

1. **MINIMAL profile registration** — ``register_health_tool`` exposes
   only the MCP ``health_check`` tool + the HTTP ``/health`` route.
   This MUST be independently callable so the W0 helper can register it
   without also registering the 6 PenpotClient-bound tools (the W4.1
   reviewer finding).
2. **Lifespan cleanup** — the ``PenpotClient`` instance must be the
   SAME object captured by the lifespan finally block (the W4.3 lesson:
   long-running servers leak httpx pools if the close call is dropped).
   Routing the client through every registration lambda keeps a single
   instance alive.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from mcp_common.health import register_http_health_route

from penpot_api_mcp import __version__
from penpot_api_mcp.clients import PenpotClient
from penpot_api_mcp.config import PenpotSettings

# Sentinel used to satisfy the uniform ``(mcp, settings, client)`` signature
# across every group function in ``_GROUP_REGISTRY``. The health probe
# doesn't touch the Penpot client — the third positional arg is accepted
# purely so the W0 dispatch lambdas can invoke every group fn with the
# same call shape.
_UNUSED: Any = None
from penpot_api_mcp.tools.files import register_file_tools
from penpot_api_mcp.tools.objects import register_object_tools
from penpot_api_mcp.tools.projects import register_project_tools


def register_health_tool(
    mcp: FastMCP, settings: PenpotSettings, client: PenpotClient | None = None
) -> None:
    """Register only the MCP ``health_check`` tool + the HTTP ``/health`` route.

    Split out from the pre-W4 monolithic registration so the W0 tool
    profile dispatch can expose ``health_check`` independently at the
    MINIMAL profile (the canonical W4.1 mapping: ``MINIMAL=health``).
    The HTTP ``/health`` route is registered alongside the MCP tool —
    launchd / load-balancer health probes need the HTTP path, not the
    MCP tool, so they remain available whenever the health probe is.

    The third ``client`` argument is accepted (but unused) to give every
    group fn a uniform ``(mcp, settings, client)`` signature so the
    W0 dispatch helper can iterate ``_GROUP_REGISTRY`` without a name
    conditional (the W3.2 lesson).

    Args:
        mcp: FastMCP server instance.
        settings: Server configuration (used for the HTTP route's
            ``service_name`` and ``version``).
        client: Ignored — present only for signature uniformity with the
            other group registration fns.
    """

    @mcp.tool()
    async def health_check() -> dict[str, Any]:
        """Check server health status.

        Returns:
            Health status information including version, server name,
            and configured state (whether PENPOT_ACCESS_TOKEN or
            PENPOT_EMAIL+PENPOT_PASSWORD is set).
        """
        return {
            "status": "healthy",
            "name": "penpot-api-mcp",
            "version": __version__,
            "configured": settings.is_configured,
            "auth_method": (
                "token"
                if settings.has_token_auth
                else "password"
                if settings.has_password_auth
                else "none"
            ),
        }

    _ = _UNUSED  # silence unused-name lint; sentinel exists for signature uniformity

    register_http_health_route(
        mcp,
        service_name="penpot-api",
        version=__version__,
    )


# ---------------------------------------------------------------------------
# Profile-friendly wrappers — take (mcp, settings, client).
# The W0 dispatch helper from mcp-common 0.18.0 expects single-arg
# callables; these wrappers are invoked via lambdas that default-arg
# capture the caller-supplied settings + client.
# ---------------------------------------------------------------------------


def register_project_tools_for_profile(
    mcp: FastMCP, settings: PenpotSettings, client: PenpotClient
) -> None:
    """Profile-dispatch entry for the project tools group.

    Forwards to the legacy ``register_project_tools`` (which takes a
    pre-constructed ``PenpotClient``).
    """
    register_project_tools(mcp, client)


def register_file_tools_for_profile(
    mcp: FastMCP, settings: PenpotSettings, client: PenpotClient
) -> None:
    """Profile-dispatch entry for the file tools group.

    Forwards to the legacy ``register_file_tools``.
    """
    register_file_tools(mcp, client)


def register_object_tools_for_profile(
    mcp: FastMCP, settings: PenpotSettings, client: PenpotClient
) -> None:
    """Profile-dispatch entry for the object tools group.

    Forwards to the legacy ``register_object_tools``.
    """
    register_object_tools(mcp, client)


# ---------------------------------------------------------------------------
# Backward-compat shim — pre-W4 callers (tests, examples) still call
# ``register_all_tools(app, client)`` directly. Kept so this shim does
# not break callers that don't go through the dispatch helper.
# ---------------------------------------------------------------------------


def register_all_tools(app: FastMCP, client: PenpotClient) -> None:
    """Register every Penpot MCP tool group (pre-W4 sync entry point).

    Does NOT register the MCP ``health_check`` tool — that lives in
    ``register_health_tool`` and is dispatched separately at the MINIMAL
    profile. New code should call ``apply_penpot_api_tool_profile``
    (see ``penpot_api_mcp/tools/profiles.py``).

    Args:
        app: FastMCP server instance.
        client: Pre-constructed ``PenpotClient`` (typically from
            ``PenpotClient(settings)``).
    """
    register_project_tools(app, client)
    register_file_tools(app, client)
    register_object_tools(app, client)


__all__ = [
    "register_all_tools",
    "register_file_tools_for_profile",
    "register_health_tool",
    "register_object_tools_for_profile",
    "register_project_tools_for_profile",
]
