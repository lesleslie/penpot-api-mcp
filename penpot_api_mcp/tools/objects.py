"""MCP tools: object tree, search, and export."""

from __future__ import annotations

import base64

from fastmcp import FastMCP

from penpot_api_mcp.clients import PenpotClient


def register_object_tools(app: FastMCP, client: PenpotClient) -> None:
    @app.tool()
    async def get_object_tree(file_id: str) -> dict:
        """Return the full design object hierarchy for a Penpot file."""
        tree = await client.get_object_tree(file_id)
        return {
            "file_id": tree.file_id,
            "object_count": len(tree.objects),
            "objects": {k: v.model_dump() for k, v in tree.objects.items()},
        }

    @app.tool()
    async def search_objects(file_id: str, query: str) -> dict:
        """Search design objects in a file by name or type."""
        results = await client.search_objects(file_id, query)
        return {
            "query": query,
            "count": len(results),
            "objects": [o.model_dump() for o in results],
        }

    @app.tool()
    async def export_object(
        file_id: str,
        object_id: str,
        scale: float = 1.0,
        export_type: str = "png",
    ) -> dict:
        """Export a design object as an image. Returns base64-encoded bytes."""
        data = await client.export_object(
            file_id, object_id, scale=scale, export_type=export_type
        )
        return {
            "file_id": file_id,
            "object_id": object_id,
            "export_type": export_type,
            "scale": scale,
            "data_base64": base64.b64encode(data).decode(),
            "size_bytes": len(data),
        }
