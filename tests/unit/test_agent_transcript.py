"""The agent loop must record a faithful transcript of each turn."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from understory.application.agent_runner import AgentRunner
from understory.application.workspace_tools import (
    EditTool,
    ListDirTool,
    ReadTool,
    WriteTool,
)
from understory.domain.chat import Message, ModelName
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace


class ScriptedProvider:
    def __init__(self, replies: Sequence[str]) -> None:
        self._replies = list(replies)

    async def complete(
        self,
        model: ModelName,
        messages: Sequence[Message],
        *,
        schema: Mapping[str, object] | None = None,
    ) -> Message:
        return Message("assistant", self._replies.pop(0))

    async def list_models(self) -> Sequence[ModelName]:
        return ["scripted"]


def _tools(ws: LocalFilesystemWorkspace):
    return [ReadTool(ws), WriteTool(ws), EditTool(ws), ListDirTool(ws)]


@pytest.fixture
def ws(tmp_path: Path) -> LocalFilesystemWorkspace:
    return LocalFilesystemWorkspace(tmp_path)


@pytest.mark.asyncio
async def test_transcript_records_tool_then_done(ws: LocalFilesystemWorkspace) -> None:
    provider = ScriptedProvider(
        [
            json.dumps({"tool": "write", "args": {"path": "a.txt", "content": "hi"}}),
            json.dumps({"done": "made it"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "task")

    assert len(result.transcript) == result.steps == 2

    step0 = result.transcript[0]
    assert step0.kind == "tool"
    assert step0.tool == "write"
    assert step0.args == {"path": "a.txt", "content": "hi"}
    assert step0.observation is not None and "a.txt" in step0.observation

    step1 = result.transcript[1]
    assert step1.kind == "done"


@pytest.mark.asyncio
async def test_transcript_marks_malformed_as_error(ws: LocalFilesystemWorkspace) -> None:
    provider = ScriptedProvider(["not json", json.dumps({"done": "ok"})])
    result = await AgentRunner(provider, _tools(ws)).run("m", "task")

    assert result.transcript[0].kind == "error"
    assert result.transcript[0].reply == "not json"


@pytest.mark.asyncio
async def test_transcript_preserves_raw_reply(ws: LocalFilesystemWorkspace) -> None:
    raw = json.dumps({"done": "final answer"})
    provider = ScriptedProvider([raw])
    result = await AgentRunner(provider, _tools(ws)).run("m", "task")

    assert result.transcript[0].reply == raw
