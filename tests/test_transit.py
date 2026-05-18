"""Unit tests for the Transit+JSON encode/decode utilities."""

from __future__ import annotations

import pytest

from penpot_api_mcp.utils.transit import decode, encode


def test_encode_plain_keys() -> None:
    assert encode({"name": "test"}) == {"~:name": "test"}


def test_encode_uuid_values() -> None:
    result = encode({"id": "abc12345-0000-0000-0000-000000000001"})
    assert result["~:id"] == "~uabc12345-0000-0000-0000-000000000001"


def test_encode_skips_already_transit_keys() -> None:
    result = encode({"~:name": "test"})
    assert "~:~:name" not in result
    assert result["~:name"] == "test"


def test_encode_list_values() -> None:
    result = encode({"ids": ["abc12345-0000-0000-0000-000000000001", "plain"]})
    assert result["~:ids"] == ["~uabc12345-0000-0000-0000-000000000001", "plain"]


def test_decode_strips_keyword_prefix() -> None:
    assert decode({"~:name": "test"}) == {"name": "test"}


def test_decode_strips_uuid_prefix() -> None:
    assert decode("~uabc-123") == "abc-123"


def test_decode_nested() -> None:
    raw = {"~:project": {"~:id": "~u111", "~:name": "Home"}}
    assert decode(raw) == {"project": {"id": "111", "name": "Home"}}


def test_decode_list() -> None:
    assert decode(["~uaaa", "~:kw"]) == ["aaa", "~:kw"]


def test_roundtrip() -> None:
    original = {"file-id": "abc12345-0000-0000-0000-000000000001", "scale": 2.0}
    encoded = encode(original)
    # Encoded keys should have ~: prefix
    assert "~:file-id" in encoded
    # Decode should recover original structure
    decoded = decode(encoded)
    assert decoded["file-id"] == "abc12345-0000-0000-0000-000000000001"
