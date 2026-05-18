"""Oneiric CLI entry point for penpot-api-mcp."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_common.cli import MCPServerCLIFactory
from mcp_common.server import BaseOneiricServerMixin, create_runtime_components
from oneiric.core.config import OneiricMCPConfig
from oneiric.runtime.mcp_health import HealthStatus

from penpot_api_mcp.config import get_settings
from penpot_api_mcp.server import create_app

OneiricMCPConfigType = (
    OneiricMCPConfig if not TYPE_CHECKING else "TypedOneiricMCPConfig"
)


class PenpotApiConfig(OneiricMCPConfig):  # type: ignore[misc]
    http_port: int = 3051
    http_host: str = "127.0.0.1"
    enable_http_transport: bool = True

    class Config:
        env_prefix = "PENPOT_MCP_"
        env_file = ".env"


class PenpotApiMCPServer(BaseOneiricServerMixin):
    def __init__(self, config: PenpotApiConfig) -> None:
        self.config = config  # type: ignore[assignment]
        self.app = create_app()
        self.runtime = create_runtime_components(
            server_name="penpot-api-mcp",
            cache_dir=config.cache_dir or ".oneiric_cache",
        )

    @property
    def snapshot_manager(self) -> object:
        return self.runtime.snapshot_manager

    @property
    def cache_manager(self) -> object:
        return self.runtime.cache_manager

    @property
    def health_monitor(self) -> object:
        return self.runtime.health_monitor

    async def startup(self) -> None:
        _ = get_settings()
        await self.runtime.initialize()
        await self._create_startup_snapshot(
            custom_components={"penpot-api": {"status": "initialized"}}
        )

    async def shutdown(self) -> None:
        await self._create_shutdown_snapshot()
        await self.runtime.cleanup()

    async def health_check(self) -> object:
        base = await self._build_health_components()
        settings = get_settings()
        base.append(
            self.runtime.health_monitor.create_component_health(
                name="penpot-api",
                status=HealthStatus.HEALTHY
                if settings.is_configured
                else HealthStatus.UNHEALTHY,
                details={
                    "configured": settings.is_configured,
                    "auth_method": "token" if settings.has_token_auth else "password",
                },
            )
        )
        return self.runtime.health_monitor.create_health_response(base)

    def get_app(self) -> object:
        return self.app.http_app


def main() -> None:
    cli_factory = MCPServerCLIFactory.create_server_cli(
        server_class=PenpotApiMCPServer,
        config_class=PenpotApiConfig,
        name="penpot-api-mcp",
        _description="Penpot API MCP Server — headless design automation via REST API",
    )
    cli_factory.create_app()()


if __name__ == "__main__":
    main()
