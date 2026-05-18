"""Unit tests for Pydantic models."""

from __future__ import annotations

from penpot_api_mcp.models import (
    PenpotFile,
    PenpotFileList,
    PenpotObject,
    PenpotObjectTree,
    PenpotProject,
    PenpotProjectList,
)


def test_project_list_count() -> None:
    pl = PenpotProjectList(items=[PenpotProject(id="1", name="A"), PenpotProject(id="2", name="B")])
    assert pl.count == 2


def test_file_list_count() -> None:
    fl = PenpotFileList(items=[PenpotFile(id="f1", name="Design")])
    assert fl.count == 1


def test_object_tree_search() -> None:
    tree = PenpotObjectTree(
        file_id="f1",
        objects={
            "o1": PenpotObject(id="o1", name="Header", type="frame"),
            "o2": PenpotObject(id="o2", name="Button", type="rect"),
        },
    )
    results = tree.search("header")
    assert len(results) == 1
    assert results[0].name == "Header"


def test_object_tree_search_by_type() -> None:
    tree = PenpotObjectTree(
        file_id="f1",
        objects={
            "o1": PenpotObject(id="o1", name="Bg", type="rect"),
            "o2": PenpotObject(id="o2", name="Label", type="text"),
        },
    )
    results = tree.search("text")
    assert len(results) == 1
    assert results[0].type == "text"
