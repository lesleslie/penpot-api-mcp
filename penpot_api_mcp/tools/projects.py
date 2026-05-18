"""MCP tools: project listing."""

from __future__ import annotations

from fastmcp import FastMCP

from penpot_api_mcp.clients import PenpotClient


def register_project_tools(app: FastMCP, client: PenpotClient) -> None:
    @app.tool()
    async def list_projects() -> dict:
        """List all Penpot projects accessible to the authenticated user."""
        result = await client.list_projects()
        return {
            "count": result.count,
            "projects": [p.model_dump() for p in result.items],
        }
