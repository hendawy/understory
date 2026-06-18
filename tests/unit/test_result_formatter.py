"""Tests for structured TaskResult formatting."""

from __future__ import annotations

import json

from understory.application.agent_runner import AgentResult
from understory.application.result_formatter import format_result
from understory.domain.trace import Step
from understory.domain.verification import Verification


def _write_step(index: int, path: str) -> Step:
    return Step(
        index=index,
        reply=json.dumps({"tool": "write", "args": {"path": path, "content": "x"}}),
        kind="tool",
        tool="write",
        args={"path": path, "content": "x"},
        observation=f"Observation: wrote {path}",
    )


def _done_step(index: int) -> Step:
    return Step(index=index, reply=json.dumps({"done": "all done"}), kind="done")


def test_done_with_files_pass() -> None:
    steps = (_write_step(0, "a.py"), _write_step(1, "b.py"), _done_step(2))
    agent = AgentResult(status="done", output="created files", steps=3, transcript=steps)
    verification = Verification(
        status="pass",
        expected_files=("a.py", "b.py"),
        found_files=("a.py", "b.py"),
        missing_files=(),
    )
    result = format_result(agent, verification, "sess-1")

    assert result.status == "done"
    assert result.steps == 3
    assert result.session_id == "sess-1"
    assert result.output == "created files"
    assert list(result.files_changed) == ["a.py", "b.py"]
    assert result.verification_status == "pass"
    assert "2 file" in result.verification_summary


def test_max_steps_with_fail_verification() -> None:
    steps = (_write_step(0, "a.py"), _write_step(1, "b.py"))
    agent = AgentResult(status="max_steps", output="gave up", steps=10, transcript=steps)
    verification = Verification(
        status="fail",
        expected_files=("a.py", "b.py"),
        found_files=("a.py",),
        missing_files=("b.py",),
    )
    result = format_result(agent, verification, "sess-2")

    assert result.status == "max_steps"
    assert result.steps == 10
    assert result.verification_status == "fail"
    assert "b.py" in result.verification_summary


def test_empty_verification_no_files() -> None:
    steps = (_done_step(0),)
    agent = AgentResult(status="done", output="nothing to do", steps=1, transcript=steps)
    verification = Verification(
        status="empty",
        expected_files=(),
        found_files=(),
        missing_files=(),
    )
    result = format_result(agent, verification, "sess-3")

    assert result.files_changed == ()
    assert result.verification_status == "empty"


def test_to_json_roundtrip() -> None:
    steps = (_write_step(0, "out.py"), _done_step(1))
    agent = AgentResult(status="done", output="wrote it", steps=2, transcript=steps)
    verification = Verification(
        status="pass",
        expected_files=("out.py",),
        found_files=("out.py",),
        missing_files=(),
    )
    result = format_result(agent, verification, "sess-4")
    parsed = json.loads(result.to_json())

    assert parsed["status"] == "done"
    assert parsed["steps"] == 2
    assert parsed["session_id"] == "sess-4"
    assert parsed["files_changed"] == ["out.py"]
    assert parsed["verification"]["status"] == "pass"
