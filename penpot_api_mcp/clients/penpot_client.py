"""Async Penpot REST API client with Transit+JSON and dual auth support."""

from __future__ import annotations

import logging
from typing import Any

from penpot_api_mcp.clients.base_client import BaseHTTPClient
from penpot_api_mcp.config.settings import PenpotSettings
from penpot_api_mcp.models import (
    PenpotFile,
    PenpotFileList,
    PenpotObject,
    PenpotObjectTree,
    PenpotProject,
    PenpotProjectList,
)
from penpot_api_mcp.utils.transit import decode, encode

logger = logging.getLogger(__name__)


class PenpotClient(BaseHTTPClient):
    """Typed async wrapper around the Penpot RPC API."""

    def __init__(self, settings: PenpotSettings) -> None:
        super().__init__(settings)
        # _api_token is only set when using direct API token auth.
        # Password-auth sessions are maintained via the httpx cookie jar only.
        self._api_token: str = settings.access_token
        self._password_authenticated: bool = False
        self._profile_id: str | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header for API token auth only.

        Password-auth sessions use the httpx cookie jar — no header needed.
        """
        if self._api_token:
            return {"Authorization": f"Token {self._api_token}"}
        return {}

    async def _ensure_authenticated(self) -> None:
        if self._api_token or self._password_authenticated:
            return
        if not self._settings.has_password_auth:
            raise RuntimeError(
                "No Penpot credentials. Set PENPOT_ACCESS_TOKEN or "
                "PENPOT_EMAIL + PENPOT_PASSWORD."
            )
        await self._login()

    async def _login(self) -> None:
        """Authenticate with email+password. Stores the session cookie in the
        httpx client jar — does NOT store it as a Bearer token."""
        client = await self._get_client()
        payload = encode(
            {"email": self._settings.email, "password": self._settings.password}
        )
        headers = {
            "Content-Type": "application/transit+json",
            "Accept": "application/transit+json",
        }
        response = await client.post(
            "/rpc/command/login-with-password", json=payload, headers=headers
        )
        response.raise_for_status()

        token = response.cookies.get("auth-token")
        if not token:
            raise RuntimeError(
                "Penpot login succeeded but auth-token cookie was missing"
            )

        # Persist the session cookie in the client jar for all subsequent requests.
        # Do NOT set self._api_token — cookie value != Bearer API token.
        client.cookies.set("auth-token", token)
        self._password_authenticated = True

        auth_data = response.cookies.get("auth-data", "")
        if "profile-id=" in auth_data:
            self._profile_id = (
                auth_data.split("profile-id=")[1].split(";")[0].strip('"')
            )

        logger.info("Penpot password login successful")

    # ------------------------------------------------------------------
    # Internal RPC helper
    # ------------------------------------------------------------------

    async def _rpc(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        *,
        transit: bool = True,
    ) -> Any:
        """POST to /rpc/command/{command} with Transit+JSON encode/decode."""
        await self._ensure_authenticated()
        body = encode(params or {}) if transit else (params or {})
        raw = await self._post(
            f"/rpc/command/{command}",
            body,
            transit=transit,
            extra_headers=self._auth_headers(),
        )
        return decode(raw) if transit else raw

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def list_projects(self) -> PenpotProjectList:
        data = await self._rpc("get-all-projects")
        items = [
            PenpotProject(
                id=raw.get("id", ""),
                name=raw.get("name", ""),
                team_id=raw.get("team-id", ""),
                created_at=raw.get("created-at"),
                modified_at=raw.get("modified-at"),
                is_default=raw.get("is-default", False),
            )
            for raw in (data if isinstance(data, list) else [])
        ]
        return PenpotProjectList(items=items)

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    async def get_project_files(self, project_id: str) -> PenpotFileList:
        data = await self._rpc("get-project-files", {"project-id": project_id})
        items = [
            PenpotFile(
                id=raw.get("id", ""),
                name=raw.get("name", ""),
                project_id=raw.get("project-id", ""),
                team_id=raw.get("team-id", ""),
                created_at=raw.get("created-at"),
                modified_at=raw.get("modified-at"),
                revn=raw.get("revn", 0),
                is_shared=raw.get("is-shared", False),
            )
            for raw in (data if isinstance(data, list) else [])
        ]
        return PenpotFileList(items=items)

    async def get_file(self, file_id: str) -> dict[str, Any]:
        return await self._rpc("get-file", {"id": file_id})

    # ------------------------------------------------------------------
    # Objects
    # ------------------------------------------------------------------

    async def get_object_tree(self, file_id: str) -> PenpotObjectTree:
        raw_file = await self.get_file(file_id)
        objects: dict[str, PenpotObject] = {}

        for page in raw_file.get("data", {}).get("pages-index", {}).values():
            for obj_id, obj_raw in page.get("objects", {}).items():
                objects[obj_id] = PenpotObject(
                    id=obj_id,
                    name=obj_raw.get("name", ""),
                    type=obj_raw.get("type", ""),
                    parent_id=obj_raw.get("parent-id"),
                    frame_id=obj_raw.get("frame-id"),
                    x=obj_raw.get("x"),
                    y=obj_raw.get("y"),
                    width=obj_raw.get("width"),
                    height=obj_raw.get("height"),
                    children=obj_raw.get("shapes", []),
                )

        return PenpotObjectTree(file_id=file_id, objects=objects)

    async def search_objects(self, file_id: str, query: str) -> list[PenpotObject]:
        tree = await self.get_object_tree(file_id)
        return tree.search(query)

    async def export_object(
        self,
        file_id: str,
        object_id: str,
        scale: float = 1.0,
        suffix: str = "",
        export_type: str = "png",
    ) -> bytes:
        """Export a single object as an image. Returns raw bytes."""
        await self._ensure_authenticated()
        client = await self._get_client()
        payload = encode(
            {
                "file-id": file_id,
                "object-id": object_id,
                "scale": scale,
                "suffix": suffix,
                "type": export_type,
            }
        )
        headers = {
            "Content-Type": "application/transit+json",
            "Accept": "application/octet-stream",
            **self._auth_headers(),
        }
        response = await client.post(
            "/rpc/command/export-binfile", json=payload, headers=headers
        )
        response.raise_for_status()
        return response.content

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    async def get_profile(self) -> dict[str, Any]:
        return await self._rpc("get-profile")
