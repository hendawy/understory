"""Contract tests for the agent loop, driven by a scripted provider.

No Ollama: the provider replays canned assistant messages so we exercise
parsing, tool dispatch, observation feedback, and termination.
"""

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
from understory.domain.chat import Message, ModelName, ToolCall, ToolDef
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace


class ScriptedProvider:
    """Replays a fixed list of assistant messages in order."""

    def __init__(self, replies: Sequence[Message | str]) -> None:
        self._replies: list[Message | str] = list(replies)
        self.seen: list[list[Message]] = []
        self.schemas: list[Mapping[str, object] | None] = []
        self.tool_defs: list[Sequence[ToolDef] | None] = []

    async def complete(
        self,
        model: ModelName,
        messages: Sequence[Message],
        *,
        schema: Mapping[str, object] | None = None,
        tools: Sequence[ToolDef] | None = None,
    ) -> Message:
        self.seen.append(list(messages))
        self.schemas.append(schema)
        self.tool_defs.append(tools)
        raw = self._replies.pop(0)
        if isinstance(raw, str):
            return Message("assistant", raw)
        return raw

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
async def test_system_prompt_includes_tool_descriptions(ws: LocalFilesystemWorkspace) -> None:
    """The system prompt must contain each tool's full description verbatim."""
    tools = _tools(ws)
    provider = ScriptedProvider([json.dumps({"done": "ok"})])
    await AgentRunner(provider, tools).run("m", "anything")

    system_msg = provider.seen[0][0]
    assert system_msg.role == "system"
    for tool in tools:
        assert tool.description in system_msg.content, (
            f"tool '{tool.name}' description missing from system prompt"
        )


@pytest.mark.asyncio
async def test_max_steps_terminates(ws: LocalFilesystemWorkspace) -> None:
    # Model never says done — always calls a tool.
    loop_reply = json.dumps({"tool": "list_dir", "args": {}})
    provider = ScriptedProvider([loop_reply] * 50)
    result = await AgentRunner(provider, _tools(ws), max_steps=3).run("m", "loop forever")

    assert result.status == "max_steps"
    assert result.steps == 3


# --- Native tool-calling tests ---


@pytest.mark.asyncio
async def test_native_tool_call_dispatches(ws: LocalFilesystemWorkspace, tmp_path: Path) -> None:
    """When the provider returns a Message with tool_calls, the runner
    dispatches the tool and feeds the result back as a tool-role message."""
    provider = ScriptedProvider(
        [
            Message(
                "assistant",
                "",
                tool_calls=(ToolCall("write", {"path": "native.txt", "content": "hello"}),),
            ),
            json.dumps({"done": "wrote it"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "create native.txt")

    assert result.status == "done"
    assert (tmp_path / "native.txt").read_text() == "hello"


@pytest.mark.asyncio
async def test_native_tool_call_feeds_observation(ws: LocalFilesystemWorkspace) -> None:
    """The observation from a native tool call is sent back as a tool-role message."""
    ws.write("data.txt", "important-data")
    provider = ScriptedProvider(
        [
            Message(
                "assistant",
                "",
                tool_calls=(ToolCall("read", {"path": "data.txt"}),),
            ),
            json.dumps({"done": "read it"}),
        ]
    )
    await AgentRunner(provider, _tools(ws)).run("m", "read data.txt")

    second_turn = provider.seen[1]
    assert any(m.role == "tool" and "important-data" in m.content for m in second_turn)


@pytest.mark.asyncio
async def test_native_unknown_tool_recovers(ws: LocalFilesystemWorkspace) -> None:
    """Unknown tool name via native calling is fed back as an error, not raised."""
    provider = ScriptedProvider(
        [
            Message(
                "assistant",
                "",
                tool_calls=(ToolCall("nonexistent", {}),),
            ),
            json.dumps({"done": "recovered"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "do thing")
    assert result.status == "done"


@pytest.mark.asyncio
async def test_native_tool_error_becomes_observation(ws: LocalFilesystemWorkspace) -> None:
    """A tool error from native calling is surfaced as a tool-role error message."""
    provider = ScriptedProvider(
        [
            Message(
                "assistant",
                "",
                tool_calls=(ToolCall("read", {"path": "missing.txt"}),),
            ),
            json.dumps({"done": "handled"}),
        ]
    )
    result = await AgentRunner(provider, _tools(ws)).run("m", "read missing")
    assert result.status == "done"
    assert any(m.role == "tool" and "Error" in m.content for m in provider.seen[1])


@pytest.mark.asyncio
async def test_runner_passes_tool_defs_to_provider(ws: LocalFilesystemWorkspace) -> None:
    """The runner must pass ToolDef objects to the provider's complete() call."""
    provider = ScriptedProvider([json.dumps({"done": "ok"})])
    tools = _tools(ws)
    await AgentRunner(provider, tools).run("m", "anything")

    passed_defs = provider.tool_defs[0]
    assert passed_defs is not None
    names = {td.name for td in passed_defs}
    assert names == {"read", "write", "edit", "list_dir"}
