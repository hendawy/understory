"""Contract tests for a confined Workspace (LocalFilesystemWorkspace).

Security focus: no operation may touch anything outside the root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from understory.domain.workspace import (
    EditConflict,
    PathEscape,
    WorkspaceFileNotFound,
)
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace


@pytest.fixture
def ws(tmp_path: Path) -> LocalFilesystemWorkspace:
    return LocalFilesystemWorkspace(tmp_path)


# --- normal operation ---


def test_write_then_read_round_trips(ws: LocalFilesystemWorkspace) -> None:
    ws.write("notes.txt", "hello")
    assert ws.read("notes.txt") == "hello"


def test_write_creates_parent_dirs_within_root(ws: LocalFilesystemWorkspace) -> None:
    ws.write("a/b/c.txt", "deep")
    assert ws.read("a/b/c.txt") == "deep"


def test_edit_replaces_unique_old(ws: LocalFilesystemWorkspace) -> None:
    ws.write("f.txt", "the quick brown fox")
    ws.edit("f.txt", "quick", "slow")
    assert ws.read("f.txt") == "the slow brown fox"


def test_list_dir_returns_entries(ws: LocalFilesystemWorkspace) -> None:
    ws.write("one.txt", "1")
    ws.write("sub/two.txt", "2")
    entries = set(ws.list_dir("."))
    assert {"one.txt", "sub"} <= entries


def test_dotdot_that_resolves_back_inside_is_allowed(ws: LocalFilesystemWorkspace) -> None:
    ws.write("sub/f.txt", "x")
    assert ws.read("sub/../sub/f.txt") == "x"


# --- error cases ---


def test_read_missing_raises(ws: LocalFilesystemWorkspace) -> None:
    with pytest.raises(WorkspaceFileNotFound):
        ws.read("nope.txt")


def test_edit_missing_file_raises(ws: LocalFilesystemWorkspace) -> None:
    with pytest.raises(WorkspaceFileNotFound):
        ws.edit("nope.txt", "a", "b")


def test_edit_old_absent_raises_conflict(ws: LocalFilesystemWorkspace) -> None:
    ws.write("f.txt", "hello")
    with pytest.raises(EditConflict):
        ws.edit("f.txt", "missing", "x")


def test_edit_old_non_unique_raises_conflict(ws: LocalFilesystemWorkspace) -> None:
    ws.write("f.txt", "ab ab")
    with pytest.raises(EditConflict):
        ws.edit("f.txt", "ab", "cd")


# --- confinement (security) ---


def test_read_dotdot_escape_rejected(ws: LocalFilesystemWorkspace) -> None:
    with pytest.raises(PathEscape):
        ws.read("../outside.txt")


def test_write_dotdot_escape_rejected(ws: LocalFilesystemWorkspace) -> None:
    with pytest.raises(PathEscape):
        ws.write("../outside.txt", "nope")


def test_absolute_path_outside_root_rejected(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(PathEscape):
        ws.read(str(outside))


def test_symlink_escape_rejected(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    secret = tmp_path.parent / "secret.txt"
    secret.write_text("classified")
    link = tmp_path / "link.txt"
    link.symlink_to(secret)
    with pytest.raises(PathEscape):
        ws.read("link.txt")
