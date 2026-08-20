# penpot-api-mcp

MCP server wrapping the [Penpot](https://penpot.app) REST API for headless design automation. Provides read, search, and export access to Penpot projects, files, and design objects — without requiring a browser session.

Part of the **Bodai Ecosystem** alongside Mahavishnu, Akosha, Dhara, Session-Buddy, and Crackerjack.

## Why this exists

The official `@penpot/mcp` (TypeScript) requires a live browser plugin to operate — it is the right tool for interactive canvas manipulation. This server targets the complementary use case: background automation, asset export pipelines, and AI-driven design queries that run without a browser.

## Tools

| Tool | Description |
|---|---|
| `list_projects` | List all projects for the authenticated user |
| `get_project_files` | List design files in a project |
| `get_file` | Fetch the full content of a design file |
| `get_object_tree` | Return the design object hierarchy for a file |
| `search_objects` | Search objects by name or type |
| `export_object` | Export a design object as PNG/SVG (base64-encoded) |

## Setup

```bash
uv sync
touch .env             # then fill in credentials (see Configuration below)
```

## Configuration

Environment variables (prefix `PENPOT_`):

| Variable | Description | Default |
|---|---|---|
| `PENPOT_ACCESS_TOKEN` | API access token (preferred) | — |
| `PENPOT_EMAIL` | Email for password auth (fallback) | — |
| `PENPOT_PASSWORD` | Password for password auth (fallback) | — |
| `PENPOT_BASE_URL` | API base URL for self-hosted instances | `https://design.penpot.app/api` |

Either `PENPOT_ACCESS_TOKEN` or `PENPOT_EMAIL` + `PENPOT_PASSWORD` must be set.

### Transport settings (prefix `PENPOT_MCP_`)

The CLI transport layer uses a separate env prefix from the Penpot API client. Override defaults via:

| Variable | Description | Default |
|---|---|---|
| `PENPOT_MCP_HTTP_HOST` | Bind host for the MCP HTTP server | `127.0.0.1` |
| `PENPOT_MCP_HTTP_PORT` | Bind port for the MCP HTTP server | `3051` |
| `PENPOT_MCP_ENABLE_HTTP_TRANSPORT` | Toggle HTTP transport on/off | `true` |

Note: `PENPOT_HTTP_PORT` (without the `MCP_` segment) is **not** honored by the CLI; the active prefix is `PENPOT_MCP_`.

## Running

```bash
# HTTP mode (default — Claude Code compatible)
uv run python -m penpot_api_mcp start --force
```

Server listens on `http://localhost:3051/mcp`. The server is HTTP-only; bare `uv run python -m penpot_api_mcp` without a subcommand falls through to Typer help and does not start a JSON-RPC loop. To bridge to stdio, run the HTTP server behind an external stdio-to-HTTP shim.

## MCP configuration

```json
{
  "mcpServers": {
    "penpot-api": {
      "type": "http",
      "url": "http://localhost:3051/mcp"
    }
  }
}
```

## Installation via Bodai Marketplace

This repo ships a Bodai Claude Code plugin manifest (`.claude-plugin/plugin.json`) plus a colocated `.mcp.json` and three slash commands in `commands/`. To install via the Bodai marketplace, first register the marketplace with Claude Code, then install the plugin by name. Once installed, the slash commands `/penpot-list`, `/penpot-search`, and `/penpot-export` become available alongside the `mcp__penpot-api__*` tools, and the MCP client talks to the server over `http://localhost:3051/mcp` as configured in `.mcp.json`. Penpot credentials still need to be present in the environment (`PENPOT_ACCESS_TOKEN` or `PENPOT_EMAIL` + `PENPOT_PASSWORD`); the plugin manifest only wires the transport, it does not provision Penpot auth.

## Development

```bash
uv run pytest                          # Run tests
uv run crackerjack                     # Full quality suite (ruff + mypy + pytest + bandit)
uv run ruff check --fix                # Lint
uv run mypy .                          # Type check
```

## Architecture

```
penpot_api_mcp/
├── utils/transit.py      # Transit+JSON encode/decode (Penpot's wire format)
├── config/settings.py    # Pydantic settings (PENPOT_* env vars)
├── clients/              # httpx async client with dual auth
├── models/               # Pydantic models: Project, File, Object, ObjectTree
├── tools/                # FastMCP tool registrations
├── server.py             # FastMCP app + health endpoints
└── __main__.py           # MCPServerCLIFactory entrypoint (Oneiric)
```

### Transit+JSON

Penpot's RPC layer uses [Transit+JSON](https://github.com/cognitect/transit-format) — a Clojure serialization format where map keys are `~:keyword` and UUIDs are `~uUUID`. The `utils/transit.py` module handles encode/decode at the API boundary, keeping all Python models clean.

### Authentication

Two modes are supported:

- **API token** (`PENPOT_ACCESS_TOKEN`): sent as `Authorization: Token <token>` header
- **Email + password**: authenticates via `/rpc/command/login-with-password`, then relies on the httpx cookie jar (`auth-token` cookie) for all subsequent requests

## License

BSD 3-Clause. See [LICENSE](LICENSE).
