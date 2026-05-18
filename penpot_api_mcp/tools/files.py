"""MCP tools: file retrieval."""

from __future__ import annotations

from fastmcp import FastMCP

from penpot_api_mcp.clients import PenpotClient


def register_file_tools(app: FastMCP, client: PenpotClient) -> None:
    @app.tool()
    async def get_project_files(project_id: str) -> dict:
        """List all design files in a Penpot project."""
        result = await client.get_project_files(project_id)
        return {
            "count": result.count,
            "files": [f.model_dump() for f in result.items],
        }

    @app.tool()
    async def get_file(file_id: str) -> dict:
        """Fetch the full content of a Penpot design file by ID."""
        return await client.get_file(file_id)
