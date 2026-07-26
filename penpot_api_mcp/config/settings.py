"""Configuration for penpot-api-mcp using Oneiric/pydantic-settings patterns."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Strings that look like credentials but are obviously unfilled template
# placeholders. Caught here so a `TODO_YOUR_PENPOT_ACCESS_TOKEN` literal in
# a launchd plist or .zshrc fails at startup instead of silently breaking
# every downstream API call.
_PLACEHOLDER_PREFIXES: tuple[str, ...] = (
    "TODO_",
    "TODO",
    "REPLACE_",
    "REPLACE",
    "CHANGEME",
    "XXX",
    "XXXXX",
)

_CREDENTIAL_FIELDS: tuple[str, ...] = ("access_token", "email", "password")


class PenpotSettings(BaseSettings):
    """Environment-driven configuration for the Penpot API MCP server."""

    model_config = SettingsConfigDict(
        env_prefix="PENPOT_",
        env_file=(".env",),
        extra="ignore",
        case_sensitive=False,
    )

    # Penpot connection
    base_url: HttpUrl = Field(  # type: ignore[assignment]
        default="https://design.penpot.app/api",  # type: ignore[arg-type]
        description="Penpot API base URL (override for self-hosted instances)",
    )

    # Auth — prefer access_token; fall back to email+password
    access_token: str = Field(
        default="",
        description="Penpot access token (PENPOT_ACCESS_TOKEN env var)",
    )
    email: str = Field(
        default="",
        description="Penpot account email for password auth fallback",
    )
    password: str = Field(
        default="",
        description="Penpot account password for password auth fallback",
    )

    # HTTP transport
    enable_http_transport: bool = Field(
        default=True,
        description="Serve the MCP over streamable HTTP",
    )
    http_host: str = Field(default="127.0.0.1")
    http_port: int = Field(default=3051, ge=1, le=65535)
    http_path: str = Field(default="/mcp")

    # HTTP client behaviour
    request_timeout: float = Field(default=30.0, ge=1.0, le=120.0)
    max_connections: int = Field(default=10, ge=1, le=100)

    # Logging
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    @property
    def has_token_auth(self) -> bool:
        return bool(self.access_token)

    @property
    def has_password_auth(self) -> bool:
        return bool(self.email and self.password)

    @property
    def is_configured(self) -> bool:
        return self.has_token_auth or self.has_password_auth

    @model_validator(mode="after")
    def _reject_placeholder_credentials(self) -> PenpotSettings:
        """Refuse to start with unfilled template strings in any credential field.

        A non-empty string like ``TODO_YOUR_PENPOT_ACCESS_TOKEN`` is truthy, so
        without this guard the server would happily report itself as configured
        and then time out on every real API call to Penpot. Failing here turns
        the problem into a visible startup error in the launchd log.
        """
        for field_name in _CREDENTIAL_FIELDS:
            value = getattr(self, field_name, "") or ""
            if not value:
                continue
            upper = value.upper()
            if any(upper.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES):
                raise ValueError(
                    f"{field_name!r} looks like an unfilled placeholder "
                    f"({value!r}). Set a real value in your shell environment "
                    f"(see ~/.zshrc) or in a .env file, then restart the server."
                )
        return self


@lru_cache
def get_settings() -> PenpotSettings:
    return PenpotSettings()
