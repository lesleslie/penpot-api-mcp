"""Transit+JSON encode/decode utilities for the Penpot API.

Penpot's RPC layer uses Transit+JSON (a Clojure serialization format):
  - Map keys are Clojure keywords: "name" -> "~:name"
  - UUIDs are tagged strings:       "abc-123" -> "~uabc-123"
  - The reverse applies on decode.
"""

from __future__ import annotations

import re
from typing import Any

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def encode(data: dict[str, Any]) -> dict[str, Any]:
    """Encode a plain dict into Transit+JSON format for Penpot RPC requests."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        t_key = key if key.startswith("~:") else f"~:{key}"
        result[t_key] = _encode_value(value)
    return result


def _encode_value(value: Any) -> Any:
    if isinstance(value, str) and _UUID_RE.match(value):
        return f"~u{value}"
    if isinstance(value, dict):
        return encode(value)
    if isinstance(value, list):
        return [_encode_value(item) for item in value]
    return value


def decode(data: Any) -> Any:
    """Recursively decode a Transit+JSON response into plain Python objects."""
    if isinstance(data, dict):
        return {
            (k[2:] if isinstance(k, str) and k.startswith("~:") else k): decode(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [decode(item) for item in data]
    if isinstance(data, str) and data.startswith("~u"):
        return data[2:]
    return data
