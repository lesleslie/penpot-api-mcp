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
cp .env.example .env   # fill in credentials
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

## Running

```bash
# HTTP mode (default — Claude Code compatible)
uv run python -m penpot_api_mcp start --force

# stdio mode
uv run python -m penpot_api_mcp
```

Server listens on `http://localhost:3051/mcp`.

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
