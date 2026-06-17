"""End-to-end test of the delegate_task MCP tool.

Exercises the full stack Understory owns — MCP tool dispatch -> AgentRunner
-> workspace tools -> LocalFilesystemWorkspace -> real disk. Only the model
is scripted, so the test is deterministic and needs no running Ollama.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from understory.application.chat_service import ChatService
from understory.domain.chat import Message, ModelName
from understory.infrastructure.mcp_server import build_server
from understory.infrastructure.memory_store import InMemoryConversationStore


class ScriptedProvider:
    """Replays canned assistant messages — stands in for a real local model."""

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


@pytest.mark.asyncio
async def test_delegate_task_creates_real_file(tmp_path: Path) -> None:
    provider = ScriptedProvider(
        [
            json.dumps(
                {"tool": "write", "args": {"path": "hello.txt", "content": "hi from understory"}}
            ),
            json.dumps({"done": "created hello.txt"}),
        ]
    )
    mcp = build_server(ChatService(provider=provider, store=InMemoryConversationStore()))

    content, _meta = await mcp.call_tool(
        "delegate_task",
        {"task": "create hello.txt", "model": "scripted", "workspace_path": str(tmp_path)},
    )

    # The model actually wrote the file on disk, confined to the workspace.
    assert (tmp_path / "hello.txt").read_text() == "hi from understory"
    # The tool reported a clean completion back to the caller.
    assert "done" in str(content)
    assert "created hello.txt" in str(content)


@pytest.mark.asyncio
async def test_delegate_task_cannot_escape_workspace(tmp_path: Path) -> None:
    # Model tries to write outside the workspace; the confinement must hold and
    # the loop must recover and finish rather than crash.
    provider = ScriptedProvider(
        [
            json.dumps({"tool": "write", "args": {"path": "../escaped.txt", "content": "x"}}),
            json.dumps({"done": "blocked"}),
        ]
    )
    mcp = build_server(ChatService(provider=provider, store=InMemoryConversationStore()))

    content, _meta = await mcp.call_tool(
        "delegate_task",
        {"task": "escape", "model": "scripted", "workspace_path": str(tmp_path)},
    )

    assert not (tmp_path.parent / "escaped.txt").exists()
    assert "done" in str(content)
