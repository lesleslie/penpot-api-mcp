"""httpx2 MockTransport helpers for penpot-api-mcp tests.

Replaces respx for this repo. Provide:

- ``make_response_handler(*responses)``: queue-based handler returning
  responses in order
- ``make_recording_handler(*responses)``: returns ``(captured, handler)``
  pair where ``captured`` is a list accumulating every request
- ``patch_async_client(handler, target_module)``: context manager that
  patches ``<target_module>.httpx.AsyncClient`` to use a MockTransport
  with the given handler
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from unittest.mock import patch

import httpx2 as httpx


def make_response_handler(
    *responses: httpx.Response,
) -> Callable[[httpx.Request], httpx.Response]:
    """Build a MockTransport handler that returns ``responses`` in order."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            raise AssertionError(
                f"MockTransport received unexpected request: {request.method} {request.url}"
            )
        return queue.pop(0)

    return handler


def make_recording_handler(
    *responses: httpx.Response,
) -> tuple[list[httpx.Request], Callable[[httpx.Request], httpx.Response]]:
    """Build a (requests_captured, handler) pair."""
    captured: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if not queue:
            raise AssertionError(
                f"MockTransport received unexpected request: {request.method} {request.url}"
            )
        return queue.pop(0)

    return captured, handler


@contextmanager
def patch_async_client(
    handler: Callable[[httpx.Request], httpx.Response],
    target_module: str,
) -> Iterator[None]:
    """Patch ``<target_module>.httpx.AsyncClient`` to use a MockTransport."""
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs.setdefault("transport", transport)
        return real_async_client(*args, **kwargs)

    with patch(f"{target_module}.httpx.AsyncClient", new=factory):
        yield
