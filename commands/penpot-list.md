---
description: List the authenticated user's Penpot projects (and optionally enumerate the design files inside one).
argument-hint: [--files <project-id>]
allowed-tools: mcp__penpot-api__list_projects, mcp__penpot-api__get_project_files
---

# /penpot-list

List Penpot projects available to the authenticated user, and optionally enumerate the design files inside a chosen project.

## Usage

`/penpot-list [--files <project-id>]`

Arguments:

- `--files <project-id>`: optional. When supplied, the command switches from listing projects to listing the design files inside the supplied Penpot project ID.

## Workflow

1. Call `mcp__penpot-api__list_projects` to enumerate every project owned by the authenticated Penpot user.
2. If `--files <project-id>` was supplied, call `mcp__penpot-api__get_project_files` with that ID to expand the chosen project into its design files.
3. Report the project list (and the file listing, if requested) with IDs so the next command in the chain can target a specific file.

## Example

`/penpot-list`

`/penpot-list --files 8d3f1c4e-9b2a-4f7e-b5d0-1a2b3c4d5e6f`