"""Ollama implementation of ChatProvider. The only file that imports `ollama`."""

from __future__ import annotations

from collections.abc import Sequence

import ollama

from understory.domain.chat import ChatProvider, Message, ModelName


class OllamaChatProvider(ChatProvider):
    def __init__(self, client: ollama.AsyncClient | None = None) -> None:
        self._client = client or ollama.AsyncClient()

    async def complete(self, model: ModelName, messages: Sequence[Message]) -> Message:
        response = await self._client.chat(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        msg = response["message"]
        return Message(role="assistant", content=msg["content"])

    async def list_models(self) -> Sequence[ModelName]:
        info = await self._client.list()
        return [m["model"] for m in info.get("models", [])]
