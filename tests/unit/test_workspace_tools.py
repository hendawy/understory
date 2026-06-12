"""Contract tests for the workspace-backed tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from understory.application.workspace_tools import (
    EditTool,
    ListDirTool,
    ReadTool,
    WriteTool,
)
from understory.domain.tool import ToolError
from understory.domain.workspace import EditConflict, WorkspaceFileNotFound
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace


@pytest.fixture
def ws(tmp_path: Path) -> LocalFilesystemWorkspace:
    return LocalFilesystemWorkspace(tmp_path)


def test_tools_expose_name_and_description(ws: LocalFilesystemWorkspace) -> None:
    for tool in (ReadTool(ws), WriteTool(ws), EditTool(ws), ListDirTool(ws)):
        assert isinstance(tool.name, str) and tool.name
        assert isinstance(tool.description, str) and tool.description


def test_write_then_read(ws: LocalFilesystemWorkspace) -> None:
    WriteTool(ws).run({"path": "a.txt", "content": "hi"})
    assert ReadTool(ws).run({"path": "a.txt"}) == "hi"


def test_edit_tool(ws: LocalFilesystemWorkspace) -> None:
    WriteTool(ws).run({"path": "a.txt", "content": "one two"})
    EditTool(ws).run({"path": "a.txt", "old": "two", "new": "three"})
    assert ReadTool(ws).run({"path": "a.txt"}) == "one three"


def test_list_dir_tool(ws: LocalFilesystemWorkspace) -> None:
    WriteTool(ws).run({"path": "a.txt", "content": "1"})
    assert "a.txt" in ListDirTool(ws).run({})


def test_missing_arg_raises_tool_error(ws: LocalFilesystemWorkspace) -> None:
    with pytest.raises(ToolError):
        WriteTool(ws).run({"path": "a.txt"})  # no content


def test_workspace_errors_propagate(ws: LocalFilesystemWorkspace) -> None:
    with pytest.raises(WorkspaceFileNotFound):
        ReadTool(ws).run({"path": "missing.txt"})
    WriteTool(ws).run({"path": "a.txt", "content": "x"})
    with pytest.raises(EditConflict):
        EditTool(ws).run({"path": "a.txt", "old": "nope", "new": "y"})
