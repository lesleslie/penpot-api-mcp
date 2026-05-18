"""respx-mocked tests for PenpotClient."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from penpot_api_mcp.clients.penpot_client import PenpotClient
from penpot_api_mcp.config.settings import PenpotSettings
from penpot_api_mcp.utils.transit import encode

BASE = "https://design.penpot.app/api"


def _settings(**overrides: Any) -> PenpotSettings:
    defaults: dict[str, Any] = {
        "access_token": "tok-test",
        "base_url": BASE,
    }
    defaults.update(overrides)
    return PenpotSettings.model_validate(defaults)


def _transit_response(data: Any) -> httpx.Response:
    return httpx.Response(200, json=data)


# ---------------------------------------------------------------------------
# Auth: API token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_api_token_sent_as_header() -> None:
    settings = _settings(access_token="my-api-token")
    client = PenpotClient(settings)

    route = respx.post(f"{BASE}/rpc/command/get-all-projects").mock(
        return_value=_transit_response([])
    )

    await client.list_projects()
    await client.close()

    assert route.called
    assert route.calls[0].request.headers["authorization"] == "Token my-api-token"


# ---------------------------------------------------------------------------
# Auth: password login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_password_login_sets_cookie_not_api_token() -> None:
    settings = _settings(access_token="", email="user@example.com", password="secret")
    client = PenpotClient(settings)

    login_response = httpx.Response(
        200,
        json=encode({"id": "profile-1", "email": "user@example.com"}),
        headers={"Set-Cookie": "auth-token=sess-abc; Path=/"},
    )
    respx.post(f"{BASE}/rpc/command/login-with-password").mock(return_value=login_response)
    respx.post(f"{BASE}/rpc/command/get-all-projects").mock(
        return_value=_transit_response([])
    )

    await client.list_projects()
    await client.close()

    # Cookie-based auth: _api_token must remain empty
    assert client._api_token == ""
    assert client._password_authenticated is True


@pytest.mark.asyncio
@respx.mock
async def test_password_login_no_cookie_raises() -> None:
    settings = _settings(access_token="", email="user@example.com", password="secret")
    client = PenpotClient(settings)

    # Login response with no Set-Cookie
    respx.post(f"{BASE}/rpc/command/login-with-password").mock(
        return_value=httpx.Response(200, json={})
    )

    with pytest.raises(RuntimeError, match="auth-token cookie was missing"):
        await client.list_projects()

    await client.close()


@pytest.mark.asyncio
async def test_no_credentials_raises() -> None:
    settings = _settings(access_token="", email="", password="")
    client = PenpotClient(settings)

    with pytest.raises(RuntimeError, match="No Penpot credentials"):
        await client.list_projects()

    await client.close()


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_list_projects_parses_response() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    transit_payload = [
        encode({"id": "pid-1", "name": "My Project", "team-id": "tid-1", "is-default": False}),
        encode({"id": "pid-2", "name": "Shared", "team-id": "tid-1", "is-default": True}),
    ]
    respx.post(f"{BASE}/rpc/command/get-all-projects").mock(
        return_value=_transit_response(transit_payload)
    )

    result = await client.list_projects()
    await client.close()

    assert result.count == 2
    assert result.items[0].id == "pid-1"
    assert result.items[0].name == "My Project"
    assert result.items[1].is_default is True


@pytest.mark.asyncio
@respx.mock
async def test_list_projects_empty_response() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/get-all-projects").mock(
        return_value=_transit_response([])
    )

    result = await client.list_projects()
    await client.close()

    assert result.count == 0


# ---------------------------------------------------------------------------
# get_project_files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_project_files_parses_response() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    transit_payload = [
        encode({
            "id": "fid-1",
            "name": "Landing",
            "project-id": "pid-1",
            "team-id": "tid-1",
            "revn": 5,
            "is-shared": False,
        })
    ]
    respx.post(f"{BASE}/rpc/command/get-project-files").mock(
        return_value=_transit_response(transit_payload)
    )

    result = await client.get_project_files("pid-1")
    await client.close()

    assert result.count == 1
    assert result.items[0].id == "fid-1"
    assert result.items[0].revn == 5

    body = json.loads(
        respx.calls[0].request.content
    )
    # The sent payload must include the transit-encoded project-id
    assert body.get("~:project-id") == "~ufid-1" or "~:project-id" in body


# ---------------------------------------------------------------------------
# get_object_tree
# ---------------------------------------------------------------------------

_OBJECT_TREE_FILE = {
    "data": {
        "pages-index": {
            "page-1": {
                "objects": {
                    "root": {"name": "Root", "type": "frame", "shapes": ["btn-1"]},
                    "btn-1": {
                        "name": "Button",
                        "type": "rect",
                        "parent-id": "root",
                        "frame-id": "root",
                        "x": 10.0,
                        "y": 20.0,
                        "width": 120.0,
                        "height": 40.0,
                        "shapes": [],
                    },
                }
            }
        }
    }
}


@pytest.mark.asyncio
@respx.mock
async def test_get_object_tree_structure() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/get-file").mock(
        return_value=_transit_response(_OBJECT_TREE_FILE)
    )

    tree = await client.get_object_tree("fid-1")
    await client.close()

    assert tree.file_id == "fid-1"
    assert "root" in tree.objects
    assert "btn-1" in tree.objects
    assert tree.objects["btn-1"].width == 120.0
    assert tree.objects["btn-1"].parent_id == "root"


# ---------------------------------------------------------------------------
# search_objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_objects_by_name() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/get-file").mock(
        return_value=_transit_response(_OBJECT_TREE_FILE)
    )

    results = await client.search_objects("fid-1", "button")
    await client.close()

    assert len(results) == 1
    assert results[0].name == "Button"


@pytest.mark.asyncio
@respx.mock
async def test_search_objects_by_type() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/get-file").mock(
        return_value=_transit_response(_OBJECT_TREE_FILE)
    )

    results = await client.search_objects("fid-1", "frame")
    await client.close()

    assert any(o.type == "frame" for o in results)


@pytest.mark.asyncio
@respx.mock
async def test_search_objects_no_match() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/get-file").mock(
        return_value=_transit_response(_OBJECT_TREE_FILE)
    )

    results = await client.search_objects("fid-1", "nonexistent-xyz")
    await client.close()

    assert results == []


# ---------------------------------------------------------------------------
# export_object
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_export_object_returns_bytes() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    respx.post(f"{BASE}/rpc/command/export-binfile").mock(
        return_value=httpx.Response(200, content=fake_png)
    )

    result = await client.export_object("fid-1", "btn-1", scale=2.0, export_type="png")
    await client.close()

    assert result == fake_png


@pytest.mark.asyncio
@respx.mock
async def test_export_object_sends_transit_payload() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/export-binfile").mock(
        return_value=httpx.Response(200, content=b"data")
    )

    await client.export_object("fid-1", "oid-1", scale=1.5, suffix="-thumb", export_type="svg")
    await client.close()

    body = json.loads(respx.calls[0].request.content)
    # Transit-encoded keys must be present
    assert "~:file-id" in body
    assert "~:object-id" in body
    assert "~:type" in body
    assert body["~:type"] == "svg"


# ---------------------------------------------------------------------------
# HTTP error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_rpc_http_error_raises() -> None:
    settings = _settings()
    client = PenpotClient(settings)

    respx.post(f"{BASE}/rpc/command/get-all-projects").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.list_projects()

    await client.close()
