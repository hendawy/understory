"""Constrained-output contract: the loop asks for a schema, the Ollama provider
maps it to its native `format`, and nothing platform-specific leaks upward.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from understory.application.agent_runner import AgentRunner, action_schema
from understory.application.workspace_tools import ReadTool, WriteTool
from understory.domain.chat import Message, ModelName, ToolDef
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace
from understory.infrastructure.ollama_provider import OllamaChatProvider

# --- action_schema (pure, provider-neutral) ---


def test_action_schema_covers_tools_and_done() -> None:
    schema = action_schema(["read", "write"])
    blob = json.dumps(schema)
    assert schema["type"] == "object"
    assert "read" in blob and "write" in blob
    assert "done" in blob


# --- the loop forwards a schema to the provider every turn ---


class RecordingProvider:
    def __init__(self, replies: Sequence[str]) -> None:
        self._replies = list(replies)
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
        self.schemas.append(schema)
        self.tool_defs.append(tools)
        return Message("assistant", self._replies.pop(0))

    async def list_models(self) -> Sequence[ModelName]:
        return ["rec"]


@pytest.mark.asyncio
async def test_runner_passes_tool_defs_each_turn(tmp_path: Path) -> None:
    ws = LocalFilesystemWorkspace(tmp_path)
    provider = RecordingProvider([json.dumps({"done": "ok"})])

    await AgentRunner(provider, [ReadTool(ws), WriteTool(ws)]).run("m", "task")

    assert provider.tool_defs, "provider was never called"
    assert provider.tool_defs[0] is not None
    # The tool defs must reference the available tools.
    names = {td.name for td in provider.tool_defs[0]}
    assert "write" in names


# --- OllamaChatProvider maps schema -> native `format` ---


class FakeOllamaClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def chat(self, **kwargs: object) -> dict[str, dict[str, str]]:
        self.calls.append(kwargs)
        return {"message": {"content": '{"done": "x"}'}}

    async def list(self) -> dict[str, object]:
        return {"models": []}


@pytest.mark.asyncio
async def test_ollama_forwards_schema_as_format() -> None:
    client = FakeOllamaClient()
    provider = OllamaChatProvider(client=client)
    schema = {"type": "object"}

    await provider.complete("m", [Message("user", "hi")], schema=schema)

    assert client.calls[0].get("format") == schema


@pytest.mark.asyncio
async def test_ollama_omits_format_when_no_schema() -> None:
    client = FakeOllamaClient()
    provider = OllamaChatProvider(client=client)

    await provider.complete("m", [Message("user", "hi")])

    assert client.calls[0].get("format") is None
