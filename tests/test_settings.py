"""Tests for PenpotSettings configuration."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from penpot_api_mcp.config.settings import PenpotSettings


def _settings(**overrides: Any) -> PenpotSettings:
    """Build a PenpotSettings instance, bypassing the .env file lookup."""
    return PenpotSettings.model_validate(overrides)


# ---------------------------------------------------------------------------
# Auth: configuration flags
# ---------------------------------------------------------------------------


def test_unconfigured_when_no_credentials() -> None:
    settings = _settings()
    assert settings.is_configured is False
    assert settings.has_token_auth is False
    assert settings.has_password_auth is False


def test_configured_with_token() -> None:
    settings = _settings(access_token="real-token-value")
    assert settings.is_configured is True
    assert settings.has_token_auth is True


def test_configured_with_email_and_password() -> None:
    settings = _settings(email="user@example.com", password="hunter2")
    assert settings.is_configured is True
    assert settings.has_password_auth is True


# ---------------------------------------------------------------------------
# Placeholder rejection (defense against unfilled template strings)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "placeholder",
    [
        "TODO_YOUR_PENPOT_ACCESS_TOKEN",
        "todo_replace_me",
        "REPLACE_ME",
        "CHANGEME",
        "XXX",
        "xxxxxxxxxxxx",
    ],
)
def test_placeholder_token_rejected(placeholder: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(access_token=placeholder)
    assert "placeholder" in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "placeholder",
    [
        "TODO_USER",
        "REPLACE_ME",
        "CHANGEME",
    ],
)
def test_placeholder_email_rejected(placeholder: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(email=placeholder, password="real-password")
    assert "placeholder" in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "placeholder",
    [
        "TODO_PASSWORD",
        "REPLACE_ME",
        "CHANGEME",
    ],
)
def test_placeholder_password_rejected(placeholder: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(email="user@example.com", password=placeholder)
    assert "placeholder" in str(exc_info.value).lower()


def test_empty_strings_are_not_placeholders() -> None:
    """Empty credentials are not placeholders — they just mean 'unconfigured'."""
    settings = _settings(access_token="", email="", password="")
    assert settings.is_configured is False
