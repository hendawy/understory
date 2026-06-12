"""Contract tests for the agent loop, driven by a scripted provider.

No Ollama: the provider replays canned assistant messages so we exercise
parsing, tool dispatch, observation feedback, and termination.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
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
    """Replays a fixed list of assistant message contents in order."""

    def __init__(self, replies: Sequence[str]) -> None:
        self._replies = list(replies)
        self.seen: list[list[Message]] = []

    async def complete(self, model: ModelName, messages: Sequence[Message]) -> Message:
        self.seen.append(list(messages))
        return Message("assistant", self._replies.pop(0))

    async def list_models(self) -> Sequence[ModelName]:
        return ["scripted"]


def _tools(ws: LocalFilesystemWorkspace):
    return [ReadTool(ws), WriteTool(ws), EditTool(ws), ListDirTool(ws)]


@pytest.fixture
def ws(tmp_path: Path) -> LocalFilesystemWorkspace:
    return LocalFilesystemWorkspace(tmp_path)


@pytest.mark.asyncio
async def test_write_then_done(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    provider = ScriptedProvider(
        [
            json.dumps({"tool": "write", "args": {"path": "out.txt", "content": "hi"}}),
            json.dumps({"done": "wrote the file"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "create out.txt")

    assert result.status == "done"
    assert result.output == "wrote the file"
    assert (tmp_path / "out.txt").read_text() == "hi"


@pytest.mark.asyncio
async def test_observation_is_fed_back(ws: LocalFilesystemWorkspace) -> None:
    ws.write("a.txt", "content-here")
    provider = ScriptedProvider(
        [
            json.dumps({"tool": "read", "args": {"path": "a.txt"}}),
            json.dumps({"done": "ok"}),
        ]
    )
    await AgentRunner(provider, _tools(ws)).run("m", "read a.txt")

    # The second model turn must have seen the read result as an observation.
    second_turn = provider.seen[1]
    assert any("content-here" in msg.content for msg in second_turn)


@pytest.mark.asyncio
async def test_unknown_tool_is_recoverable(ws: LocalFilesystemWorkspace) -> None:
    provider = ScriptedProvider(
        [
            json.dumps({"tool": "frobnicate", "args": {}}),
            json.dumps({"done": "recovered"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "do thing")
    assert result.status == "done"
    assert result.output == "recovered"


@pytest.mark.asyncio
async def test_malformed_json_is_recoverable(ws: LocalFilesystemWorkspace) -> None:
    provider = ScriptedProvider(
        [
            "not json at all",
            json.dumps({"done": "back on track"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "do thing")
    assert result.status == "done"


@pytest.mark.asyncio
async def test_tool_error_becomes_observation(ws: LocalFilesystemWorkspace) -> None:
    provider = ScriptedProvider(
        [
            json.dumps({"tool": "read", "args": {"path": "missing.txt"}}),
            json.dumps({"done": "handled"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "read missing")
    assert result.status == "done"
    # The error must have been surfaced to the model, not raised.
    assert any("missing.txt" in m.content or "Error" in m.content for m in provider.seen[1])


@pytest.mark.asyncio
async def test_non_dict_args_is_recoverable(ws: LocalFilesystemWorkspace) -> None:
    # A flaky model emits args as a bare string instead of an object.
    provider = ScriptedProvider(
        [
            '{"tool": "write", "args": "path content"}',
            json.dumps({"done": "recovered"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "do thing")
    assert result.status == "done"


@pytest.mark.asyncio
async def test_non_string_tool_name_is_recoverable(ws: LocalFilesystemWorkspace) -> None:
    provider = ScriptedProvider(
        [
            '{"tool": ["read"], "args": {}}',
            json.dumps({"done": "recovered"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "do thing")
    assert result.status == "done"


@pytest.mark.asyncio
async def test_max_steps_terminates(ws: LocalFilesystemWorkspace) -> None:
    # Model never says done — always calls a tool.
    loop_reply = json.dumps({"tool": "list_dir", "args": {}})
    provider = ScriptedProvider([loop_reply] * 50)
    result = await AgentRunner(provider, _tools(ws), max_steps=3).run("m", "loop forever")

    assert result.status == "max_steps"
    assert result.steps == 3
