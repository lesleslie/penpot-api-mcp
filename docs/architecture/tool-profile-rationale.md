# Tool Profile Adoption in penpot-api-mcp (W4.4)

This document captures the rationale for adopting `apply_tool_profile()`
from `mcp-common` 0.18.0 in `penpot-api-mcp`. It is the fourth of ten
Tier-A repos in the W4 wave; the first three were `css-mcp`, `excalidraw-mcp`,
and `neo4j-mcp`.

## Tier-A trivial profile mapping

| Profile   | Tools exposed                                                                                                |
|-----------|--------------------------------------------------------------------------------------------------------------|
| `MINIMAL`  | `health_check` (MCP) + `discover_tools` (W0 meta). HTTP `/health` + `/healthz` routes always available.       |
| `STANDARD` | All 6 `penpot-api-mcp` tools + `health_check` + `discover_tools` (same as FULL — Tier-A trivial).            |
| `FULL`     | All 6 `penpot-api-mcp` tools + `health_check` + `discover_tools`. Default behavior when no env var is set.    |

The 6 Penpot tools (Tier-A trivial — no "core subset" to drop at
STANDARD):

1. `list_projects` (project_tools group)
2. `get_project_files` (file_tools group)
3. `get_file` (file_tools group)
4. `get_object_tree` (object_tools group)
5. `search_objects` (object_tools group)
6. `export_object` (object_tools group)

## Why MINIMAL = health-only

`MINIMAL` exposes only the health probe because every Penpot tool binds a
`PenpotClient` instance that performs real HTTP calls to the Penpot
API. Without configured credentials (`PENPOT_ACCESS_TOKEN` or
`PENPOT_EMAIL` + `PENPOT_PASSWORD`) and a reachable Penpot instance,
every tool call would fail. Operators running a control-plane health
probe (Kubernetes liveness, load-balancer ping) need ONLY the
`health_check` tool — the Penpot-bound tools are dead weight and would
fail anyway.

## Why `essential_tool_names={"health_check"}`

The W0 helper from `mcp-common` 0.18.0 performs a subset check after
registration: it asserts that every name in `essential_tool_names` is
present in the registered tool set. By passing
`essential_tool_names={"health_check"}`, we make the W4 spec invariant
**runtime-enforced** — any future refactor that accidentally drops the
health tool from a profile raises `ValueError` at startup, not silent
degradation in production.

## Caller-supplied settings + client preservation

`create_app(settings, server)` threads the caller-supplied
`PenpotSettings` instance AND the pre-constructed `PenpotClient`
instance through every registration path. Two regression tests
monkey-patch `PenpotSettings.__init__` to count inits — both fail loud
if any registration path silently reloads from the environment
(W4.1 round-1 reviewer finding: caller-supplied settings were
discarded by registration paths in the W4.1 round-0 commit).

## Lifespan cleanup

The pre-W4 lifespan held a closure reference to `client` and called
`await client.close()` in the `finally` block. The W4 refactor
preserves this exactly — the `client` instance constructed at the top
of `create_app` is the same one captured by the lifespan AND the same
one passed to every group registration. Two regression tests
(AST structural guard + end-to-end monkey-patch test) fail loud if any
future refactor drops the close call or substitutes a different
instance (W4.3 reviewer finding: the W4.3 round-0 commit accidentally
replaced `await client.close()` with a no-op that iterated
`server.list_tools()` — long-running servers would leak httpx pools).

## Async-only dispatch path

`apply_penpot_api_tool_profile` is `async` and calls
`_apply_tool_profile` (the async helper), NOT `apply_tool_profile`
(the sync wrapper which raises `RuntimeError` inside an event loop).
Two regression tests verify:

1. AST structural check for `ast.Await(value=ast.Call(func=ast.Name(
   id='apply_penpot_api_tool_profile')))` in `server.py`.
2. Negative test (`test_guard_fails_when_await_is_removed`) — builds a
   synthetic module with an un-awaited call and asserts the guard
   returns False.

## `_GROUP_REGISTRY` as SSOT

The `_GROUP_REGISTRY: list[tuple[str, str]]` constant in
`penpot_api_mcp/tools/profiles.py` is the single source of truth for
group keys. Both `_build_registration_map` and `register_all_tool_groups`
iterate it via `getattr(penpot_api_mcp.tools, attr_name)` — no
name-specific conditionals. Adding a new group requires editing only
this constant (W3.2 lesson).

## Uniform `(mcp, settings, client)` signature

Every group function in `_GROUP_REGISTRY` accepts the same
`(mcp, settings, client)` signature. `register_health_tool` does not
use the `client` argument (it doesn't need a Penpot client), but it
accepts the parameter for uniformity so the W0 dispatch helper can
iterate the registry without a name conditional. The unused parameter
is documented in the function's docstring.

## Behavioral parity at FULL/STANDARD

The FULL profile (the default when no env var is set) registers every
tool that the pre-W4 implementation registered, plus the new MCP
`health_check` tool and the W0 `discover_tools` meta-tool. The HTTP
`/health` route is also new (registered alongside `health_check` inside
`register_health_tool`); the `/healthz` custom route remains
module-level.

| Surface | Pre-W4 | FULL (default) | STANDARD | MINIMAL |
|---------|--------|----------------|----------|---------|
| 6 Penpot tools | yes | yes | yes | no |
| `health_check` MCP tool | no | yes | yes | yes |
| `discover_tools` MCP tool | no | yes | yes | yes |
| `/health` HTTP route | no | yes | yes | yes |
| `/healthz` HTTP route | yes | yes | yes | yes |

## Implementation files

- `penpot_api_mcp/tools/__init__.py` (MODIFIED): added
  `register_health_tool(mcp, settings, client=None)` and the three
  `register_<group>_tools_for_profile(mcp, settings, client)` wrappers.
  Preserved the legacy `register_all_tools(app, client)` re-export.
- `penpot_api_mcp/tools/profiles.py` (NEW): `_GROUP_REGISTRY`,
  `PROFILE_REGISTRATIONS`, `_build_registration_map`,
  `register_all_tool_groups`, `apply_penpot_api_tool_profile`.
- `penpot_api_mcp/server.py` (MODIFIED): async `create_app(settings,
  server)` with `_run_async_safely` bridge + sync `create_app_sync`
  wrapper. Lifespan closes client on shutdown.
- `pyproject.toml` (MODIFIED): `mcp-common>=0.18.0`.
- `tests/unit/test_tool_profile.py` (NEW, 31 tests).
- `CLAUDE.md` (MODIFIED): Tool Profile System subsection.

## Env var precedence

`PENPOT_API_TOOL_PROFILE` (case-insensitive). Falls through to
`FULL` when unset (the pre-W4 behavior — no surprise to existing
deployments). SET-BUT-INVALID values raise `InvalidProfileError` at
startup, not silent fallback.
