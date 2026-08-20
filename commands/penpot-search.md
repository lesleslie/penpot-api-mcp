---
description: Search a Penpot design file for objects whose name or type matches a query string.
argument-hint: <file-id> <query>
allowed-tools: mcp__penpot-api__search_objects, mcp__penpot-api__get_object_tree
---

# /penpot-search

Search a Penpot design file for objects matching a query (matched against name and type).

## Usage

`/penpot-search <file-id> <query>`

Arguments:

- `<file-id>`: UUID of the Penpot design file to search inside.
- `<query>`: substring to match against object names and types. Case-insensitive on most backends.

## Workflow

1. (Optional) Call `mcp__penpot-api__get_object_tree` with `<file-id>` first to confirm the file exists and to capture the full object hierarchy for context.
2. Call `mcp__penpot-api__search_objects` with `<file-id>` and `<query>` to return matching objects.
3. Report the matching object IDs, names, and types so the caller can target them with `/penpot-export` next.

## Example

`/penpot-search 8d3f1c4e-9b2a-4f7e-b5d0-1a2b3c4d5e6f "primary button"`