# CLAUDE.md

Guidance for Claude Code working with `penpot-api-mcp`. Start with `AGENTS.md` for a shorter bootstrap.

## Ecosystem Context

Part of the **Bodai Ecosystem**:

| Component | Role | Port |
|-----------|------|------|
| Mahavishnu | Orchestrator | 8680 |
| Akosha | Seer | 8682 |
| Dhara | Curator | 8683 |
| Session-Buddy | Builder | 8678 |
| Crackerjack | Inspector | 8676 |
| **penpot-api-mcp** | Penpot REST API | 3051 |

## Project Overview

FastMCP MCP server wrapping the Penpot REST API. Provides headless (no-browser) read and export access for design automation workflows. Complements the official `@penpot/mcp` (TypeScript, browser plugin required).

**Tech stack:** Python 3.13, FastMCP, httpx, Pydantic, mcp-common, Oneiric

## Common Commands

```bash
uv sync                              # Install/sync all dependencies
uv run python -m penpot_api_mcp      # Run (stdio mode)
uv run python -m penpot_api_mcp start --force  # Run (HTTP mode)

uv run pytest                        # Run tests
uv run crackerjack                   # Full quality suite
uv run ruff check --fix              # Lint
uv run mypy .                        # Type check
```

## Architecture

### Key Design Decisions

**Transit+JSON**: Penpot's RPC API uses Transit+JSON (Clojure serialization). All encoding/decoding is centralized in `penpot_api_mcp/utils/transit.py`. Never manually construct `~:key` or `~uUUID` payloads elsewhere — use `encode()` / `decode()`.

**Auth separation**: Two auth paths must stay separate:
- API token (`PENPOT_ACCESS_TOKEN`): stored in `self._api_token`, sent as `Authorization: Token` header
- Password auth: session cookie only, stored in the httpx cookie jar, never converted to a Bearer token

**Consistent transit**: All `_rpc()` calls use `transit=True` (default). The `transit=False` path exists only for edge cases where the server doesn't speak Transit. Do not add new `transit=False` calls without verifying the server response format.

**FastMCP lifespan**: Use the `lifespan=` constructor parameter — never monkey-patch `app._mcp_server.lifespan`.

### Module Layout

```
penpot_api_mcp/
├── utils/transit.py      # encode() / decode() for Transit+JSON
├── config/settings.py    # PenpotSettings (PENPOT_* env vars)
├── clients/
│   ├── base_client.py    # httpx.AsyncClient lifecycle + cookie persistence
│   └── penpot_client.py  # Typed Penpot RPC wrapper
├── models/               # Pydantic: Project, File, Object, ObjectTree
├── tools/                # FastMCP @app.tool() registrations
├── server.py             # create_app() factory
└── __main__.py           # Oneiric MCPServerCLIFactory entrypoint
```

## Coding Standards

- Python 3.13+, strict typing, 88-char lines (Ruff)
- `from __future__ import annotations` in every module
- Pydantic models for all API response shapes
- `httpx` (async) — never `requests`
- Tests in `tests/`, mirrors package layout

## Security

- Credentials only via environment variables — never hardcoded
- Path: `PENPOT_ACCESS_TOKEN` > `PENPOT_EMAIL` + `PENPOT_PASSWORD`
- No secrets in logs — use structured logging with redaction
