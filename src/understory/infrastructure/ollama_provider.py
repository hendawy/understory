"""Ollama implementation of ChatProvider. The only file that imports `ollama`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

import ollama

from understory.domain.chat import ChatProvider, Message, ModelName, ToolCall, ToolDef


class _OllamaClient(Protocol):
    """The slice of the Ollama async client this provider depends on.

    Typing the seam structurally lets tests inject a fake without `Any` and
    keeps the real ``ollama.AsyncClient`` conforming.
    """

    async def chat(
        self, *, model: str, messages: Any, format: Any = ..., tools: Any = ...
    ) -> Any: ...

    async def list(self) -> Any: ...


def _to_wire(m: Message) -> dict[str, Any]:
    """Convert a domain Message to the Ollama wire format."""
    wire: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        wire["tool_calls"] = [
            {"function": {"name": tc.name, "arguments": dict(tc.args)}} for tc in m.tool_calls
        ]
    if m.tool_call_id is not None:
        # Ollama expects tool results with a name field identifying the tool.
        wire["name"] = m.tool_call_id
    return wire


class OllamaChatProvider(ChatProvider):
    def __init__(self, client: _OllamaClient | None = None, host: str | None = None) -> None:
        self._client: _OllamaClient = client or ollama.AsyncClient(host=host)

    async def complete(
        self,
        model: ModelName,
        messages: Sequence[Message],
        *,
        schema: Mapping[str, object] | None = None,
        tools: Sequence[ToolDef] | None = None,
    ) -> Message:
        wire = [_to_wire(m) for m in messages]
        kwargs: dict[str, Any] = {"model": model, "messages": wire}
        if schema is not None:
            kwargs["format"] = schema
        if tools is not None:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": td.name,
                        "description": td.description,
                        "parameters": dict(td.parameters),
                    },
                }
                for td in tools
            ]
        response = await self._client.chat(**kwargs)
        msg = response["message"]
        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            tool_calls.append(ToolCall(name=fn["name"], args=fn.get("arguments", {})))
        return Message(
            role="assistant",
            content=msg.get("content") or "",
            tool_calls=tuple(tool_calls),
        )

    async def list_models(self) -> Sequence[ModelName]:
        info = await self._client.list()
        return [m["model"] for m in info.get("models", [])]
