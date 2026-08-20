---
description: Export a Penpot design object as PNG or SVG (base64-encoded in the response).
argument-hint: <file-id> <object-id> [--format png|svg] [--scale N]
allowed-tools: mcp__penpot-api__export_object, mcp__penpot-api__get_object_tree
---

# /penpot-export

Export a single design object out of a Penpot file as PNG or SVG. The response is base64-encoded inside a structured envelope.

## Usage

`/penpot-export <file-id> <object-id> [--format png|svg] [--scale N]`

Arguments:

- `<file-id>`: UUID of the Penpot design file that owns the object.
- `<object-id>`: UUID of the design object (shape, component, frame, group) to export.
- `--format`: optional. `png` (default) or `svg`. PNG is raster; SVG is vector.
- `--scale N`: optional. Integer scale factor applied to PNG exports. Ignored for SVG.

## Workflow

1. (Optional) Call `mcp__penpot-api__get_object_tree` with `<file-id>` to confirm `<object-id>` exists in the file before exporting.
2. Call `mcp__penpot-api__export_object` with `file_id`, `object_id`, and any supplied `format` / `scale` flags.
3. Decode the base64 payload from the response payload when the caller wants to write the asset to disk; otherwise report the dimensions and byte size.

## Example

`/penpot-export 8d3f1c4e-9b2a-4f7e-b5d0-1a2b3c4d5e6f 5b7e9f10-aaaa-bbbb-cccc-111122223333 --format svg`

`/penpot-export 8d3f1c4e-9b2a-4f7e-b5d0-1a2b3c4d5e6f 5b7e9f10-aaaa-bbbb-cccc-111122223333 --format png --scale 2`