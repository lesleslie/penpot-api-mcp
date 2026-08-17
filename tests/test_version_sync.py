"""CI guard: ensure __version__ matches pyproject.toml distribution version."""

from __future__ import annotations

from importlib.metadata import version

from penpot_api_mcp import __version__


def test_version_sync() -> None:
    """Ensure __version__ matches pyproject.toml distribution version."""
    dist_version = version("penpot-api-mcp")
    assert __version__ == dist_version, (
        f"__version__ ({__version__}) drifted from pyproject ({dist_version})"
    )
