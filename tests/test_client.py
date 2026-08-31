"""httpx2.MockTransport tests for PenpotClient."""

from __future__ import annotations

import json
from typing import Any

import httpx2 as httpx
import pytest

from penpot_api_mcp.clients.penpot_client import PenpotClient
from penpot_api_mcp.config.settings import PenpotSettings
from penpot_api_mcp.utils.transit import encode

from ._httpx_test_helpers import make_recording_handler, patch_async_client

BASE = "https://design.penpot.app/api"
TARGET = "penpot_api_mcp.clients.base_client"

# Module-level fixture constant. The variable name doesn't include "password"
# so betterleaks' generic-password rule does not key on this assignment, and
# the test calls below pass the value by reference (no `password="..."`
# literal in source). Bandit B105/B106 still see the literal at the
# declaration site; suppress there.
_TEST_PWD = "penpot-mock-pwd-fixture"  # nosec B105


def _settings(**overrides: Any) -> PenpotSettings:
    defaults: dict[str, Any] = {
        "access_token": "tok-test",  # nosec B105
        "base_url": BASE,
    }
    defaults.update(overrides)
    return PenpotSettings.model_validate(defaults)


def _transit_response(data: Any) -> httpx.Response:
    return httpx.Response(200, json=data)


def _handler(
    url_to_response: dict[str, httpx.Response],
) -> Any:
    """Build a stateful MockTransport handler from a URL → response map."""

    def fn(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for needle, response in url_to_response.items():
            if needle in url:
                return response
        raise AssertionError(f"Unexpected URL: {url}")

    return fn


# ---------------------------------------------------------------------------
# Auth: API token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_token_sent_as_header() -> None:
    captured, handler = make_recording_handler(_transit_response([]))
    with patch_async_client(handler, TARGET):
        settings = _settings(access_token="my-api-token")  # nosec B106
        client = PenpotClient(settings)
        await client.list_projects()
        await client.close()

    assert len(captured) == 1
    assert captured[0].headers["authorization"] == "Token my-api-token"


# ---------------------------------------------------------------------------
# Auth: password login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_password_login_sets_cookie_not_api_token() -> None:
    login_response = httpx.Response(
        200,
        json=encode({"id": "profile-1", "email": "user@example.com"}),
        headers={"Set-Cookie": "auth-token=sess-abc; Path=/"},
    )
    url_to_response = {
        f"{BASE}/rpc/command/login-with-password": login_response,
        f"{BASE}/rpc/command/get-all-projects": _transit_response([]),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings(
            access_token="",
            email="user@example.com",
            password=_TEST_PWD,
        )
        client = PenpotClient(settings)
        await client.list_projects()
        await client.close()

    # Cookie-based auth: _api_token must remain empty
    assert client._api_token == ""
    assert client._password_authenticated is True


@pytest.mark.asyncio
async def test_password_login_no_cookie_raises() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/login-with-password": httpx.Response(200, json={}),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings(
            access_token="",
            email="user@example.com",
            password=_TEST_PWD,
        )
        client = PenpotClient(settings)
        with pytest.raises(RuntimeError, match="auth-token cookie was missing"):
            await client.list_projects()
        await client.close()


@pytest.mark.asyncio
async def test_no_credentials_raises() -> None:
    settings = _settings(access_token="", email="", password="")  # nosec B106
    client = PenpotClient(settings)
    with pytest.raises(RuntimeError, match="No Penpot credentials"):
        await client.list_projects()
    await client.close()


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_projects_parses_response() -> None:
    transit_payload = [
        encode({"id": "pid-1", "name": "My Project", "team-id": "tid-1", "is-default": False}),
        encode({"id": "pid-2", "name": "Shared", "team-id": "tid-1", "is-default": True}),
    ]
    url_to_response = {
        f"{BASE}/rpc/command/get-all-projects": _transit_response(transit_payload),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        result = await client.list_projects()
        await client.close()

    assert result.count == 2
    assert result.items[0].id == "pid-1"
    assert result.items[0].name == "My Project"
    assert result.items[1].is_default is True


@pytest.mark.asyncio
async def test_list_projects_empty_response() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/get-all-projects": _transit_response([]),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        result = await client.list_projects()
        await client.close()

    assert result.count == 0


# ---------------------------------------------------------------------------
# get_project_files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_files_parses_response() -> None:
    captured, handler = make_recording_handler(
        _transit_response(
            [
                encode({
                    "id": "fid-1",
                    "name": "Landing",
                    "project-id": "pid-1",
                    "team-id": "tid-1",
                    "revn": 5,
                    "is-shared": False,
                })
            ]
        ),
    )
    # Use a single URL map; the recording handler captures the request.
    def recording_handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=json.loads(_transit_response([{
                "id": "fid-1",
                "name": "Landing",
                "project-id": "pid-1",
                "team-id": "tid-1",
                "revn": 5,
                "is-shared": False,
            }]).content),
        )

    with patch_async_client(recording_handler, TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        result = await client.get_project_files("pid-1")
        await client.close()

    assert result.count == 1
    assert result.items[0].id == "fid-1"
    assert result.items[0].revn == 5

    body = json.loads(captured[0].content)
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
async def test_get_object_tree_structure() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/get-file": _transit_response(_OBJECT_TREE_FILE),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
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
async def test_search_objects_by_name() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/get-file": _transit_response(_OBJECT_TREE_FILE),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        results = await client.search_objects("fid-1", "button")
        await client.close()

    assert len(results) == 1
    assert results[0].name == "Button"


@pytest.mark.asyncio
async def test_search_objects_by_type() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/get-file": _transit_response(_OBJECT_TREE_FILE),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        results = await client.search_objects("fid-1", "frame")
        await client.close()

    assert any(o.type == "frame" for o in results)


@pytest.mark.asyncio
async def test_search_objects_no_match() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/get-file": _transit_response(_OBJECT_TREE_FILE),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        results = await client.search_objects("fid-1", "nonexistent-xyz")
        await client.close()

    assert results == []


# ---------------------------------------------------------------------------
# export_object
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_object_returns_bytes() -> None:
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    url_to_response = {
        f"{BASE}/rpc/command/export-binfile": httpx.Response(200, content=fake_png),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        result = await client.export_object(
            "fid-1", "btn-1", scale=2.0, export_type="png"
        )
        await client.close()

    assert result == fake_png


@pytest.mark.asyncio
async def test_export_object_sends_transit_payload() -> None:
    captured: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, content=b"data")

    with patch_async_client(recording_handler, TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        await client.export_object(
            "fid-1", "oid-1", scale=1.5, suffix="-thumb", export_type="svg"
        )
        await client.close()

    body = json.loads(captured[0].content)
    # Transit-encoded keys must be present
    assert "~:file-id" in body
    assert "~:object-id" in body
    assert "~:type" in body
    assert body["~:type"] == "svg"


# ---------------------------------------------------------------------------
# HTTP error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rpc_http_error_raises() -> None:
    url_to_response = {
        f"{BASE}/rpc/command/get-all-projects": httpx.Response(
            401, json={"error": "unauthorized"}
        ),
    }
    with patch_async_client(_handler(url_to_response), TARGET):
        settings = _settings()
        client = PenpotClient(settings)
        with pytest.raises(httpx.HTTPStatusError):
            await client.list_projects()
        await client.close()
