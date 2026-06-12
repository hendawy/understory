"""Ollama implementation of ChatProvider. The only file that imports `ollama`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

import ollama

from understory.domain.chat import ChatProvider, Message, ModelName


class _OllamaClient(Protocol):
    """The slice of the Ollama async client this provider depends on.

    Typing the seam structurally lets tests inject a fake without `Any` and
    keeps the real ``ollama.AsyncClient`` conforming.
    """

    async def chat(self, *, model: str, messages: Any, format: Any = ...) -> Any: ...

    async def list(self) -> Any: ...


class OllamaChatProvider(ChatProvider):
    def __init__(self, client: _OllamaClient | None = None) -> None:
        self._client: _OllamaClient = client or ollama.AsyncClient()

    async def complete(
        self,
        model: ModelName,
        messages: Sequence[Message],
        *,
        schema: Mapping[str, object] | None = None,
    ) -> Message:
        wire = [{"role": m.role, "content": m.content} for m in messages]
        if schema is not None:
            response = await self._client.chat(model=model, messages=wire, format=schema)
        else:
            response = await self._client.chat(model=model, messages=wire)
        msg = response["message"]
        return Message(role="assistant", content=msg["content"])

    async def list_models(self) -> Sequence[ModelName]:
        info = await self._client.list()
        return [m["model"] for m in info.get("models", [])]
