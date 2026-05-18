"""Configuration for penpot-api-mcp using Oneiric/pydantic-settings patterns."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> PenpotSettings:
    return PenpotSettings()
