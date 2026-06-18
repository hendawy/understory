"""Tests for post-run outcome verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from understory.domain.trace import Step
from understory.domain.verification import verify_outcome
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace


@pytest.fixture
def ws(tmp_path: Path) -> LocalFilesystemWorkspace:
    return LocalFilesystemWorkspace(tmp_path)


def _write_step(index: int, path: str, *, error: bool = False) -> Step:
    obs = "Error: something went wrong" if error else f"Observation: wrote {path}"
    return Step(
        index=index,
        reply=json.dumps({"tool": "write", "args": {"path": path, "content": "x"}}),
        kind="tool",
        tool="write",
        args={"path": path, "content": "x"},
        observation=obs,
    )


def _done_step(index: int) -> Step:
    return Step(index=index, reply=json.dumps({"done": "all done"}), kind="done")


def test_empty_when_no_writes(ws: LocalFilesystemWorkspace) -> None:
    steps = [_done_step(0)]
    result = verify_outcome(steps, ws)
    assert result.status == "empty"
    assert "never called write" in result.summary


def test_pass_when_files_exist(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    (tmp_path / "out.py").write_text("hello")
    steps = [_write_step(0, "out.py"), _done_step(1)]
    result = verify_outcome(steps, ws)
    assert result.status == "pass"
    assert result.found_files == ("out.py",)
    assert result.missing_files == ()


def test_fail_when_files_missing(ws: LocalFilesystemWorkspace) -> None:
    steps = [_write_step(0, "ghost.py"), _done_step(1)]
    result = verify_outcome(steps, ws)
    assert result.status == "fail"
    assert result.missing_files == ("ghost.py",)
    assert "ghost.py" in result.summary


def test_errored_writes_are_excluded(ws: LocalFilesystemWorkspace) -> None:
    steps = [_write_step(0, "bad.py", error=True), _done_step(1)]
    result = verify_outcome(steps, ws)
    assert result.status == "empty"


def test_mixed_found_and_missing(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("ok")
    steps = [_write_step(0, "a.py"), _write_step(1, "b.py"), _done_step(2)]
    result = verify_outcome(steps, ws)
    assert result.status == "fail"
    assert result.found_files == ("a.py",)
    assert result.missing_files == ("b.py",)


def test_edit_steps_are_verified(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    (tmp_path / "f.py").write_text("edited")
    step = Step(
        index=0,
        reply=json.dumps({"tool": "edit", "args": {"path": "f.py", "old": "a", "new": "b"}}),
        kind="tool",
        tool="edit",
        args={"path": "f.py", "old": "a", "new": "b"},
        observation="Observation: edited f.py",
    )
    result = verify_outcome([step, _done_step(1)], ws)
    assert result.status == "pass"
    assert result.found_files == ("f.py",)
