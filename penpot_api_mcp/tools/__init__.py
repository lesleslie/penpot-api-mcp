from __future__ import annotations

from fastmcp import FastMCP

from penpot_api_mcp.clients import PenpotClient
from penpot_api_mcp.tools.files import register_file_tools
from penpot_api_mcp.tools.objects import register_object_tools
from penpot_api_mcp.tools.projects import register_project_tools


def register_all_tools(app: FastMCP, client: PenpotClient) -> None:
    register_project_tools(app, client)
    register_file_tools(app, client)
    register_object_tools(app, client)


__all__ = ["register_all_tools"]
