# AGENTS.md

Bootstrap reference for AI agents and tools working with `penpot-api-mcp`.

## What This Is

MCP server (Python 3.13, FastMCP, port 3051) wrapping the Penpot REST API. Headless — no browser required. Complements the official TypeScript `@penpot/mcp` (which needs a browser plugin for live canvas manipulation).

## Quick Commands

```bash
uv sync                                        # Install deps
uv run pytest                                  # Tests
uv run crackerjack                             # Quality gates
uv run python -m penpot_api_mcp start --force  # Start HTTP server
```

## Key Files

| File | Purpose |
|---|---|
| `penpot_api_mcp/utils/transit.py` | Transit+JSON encode/decode — Penpot's wire format |
| `penpot_api_mcp/clients/penpot_client.py` | Core API client with auth and RPC |
| `penpot_api_mcp/config/settings.py` | `PENPOT_*` env var configuration |
| `penpot_api_mcp/tools/` | FastMCP tool registrations (6 tools) |
| `settings/penpot_api_mcp.yaml` | YAML config (Oneiric-compatible) |
| `~/Library/LaunchAgents/com.mcp.penpot-api.plist` | launchctl service definition |

## MCP Tools

`list_projects` · `get_project_files` · `get_file` · `get_object_tree` · `search_objects` · `export_object`

## Auth

Set `PENPOT_ACCESS_TOKEN` (preferred) or `PENPOT_EMAIL` + `PENPOT_PASSWORD`. Never use password-auth session cookie values as Bearer tokens.

## Critical Invariants

1. All `_rpc()` calls use `transit=True` — Penpot speaks Transit+JSON
2. `encode()` / `decode()` are the only correct way to build/parse Penpot payloads
3. After password login, session is cookie-jar only — `self._api_token` stays empty
4. FastMCP lifespan via constructor `lifespan=` param, not `_mcp_server.lifespan` patch
