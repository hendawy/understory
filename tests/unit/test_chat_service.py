"""ChatService unit tests using a fake provider (no Ollama, no I/O)."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from understory.application.chat_service import ChatService
from understory.domain.chat import Message, ModelName
from understory.infrastructure.memory_store import InMemoryConversationStore


class FakeProvider:
    def __init__(self, reply: str = "ok", models: Sequence[str] = ("fake-1",)) -> None:
        self.reply = reply
        self.models = models
        self.calls: list[tuple[str, list[Message]]] = []

    async def complete(self, model: ModelName, messages: Sequence[Message]) -> Message:
        self.calls.append((model, list(messages)))
        return Message("assistant", self.reply)

    async def list_models(self) -> Sequence[ModelName]:
        return self.models


@pytest.mark.asyncio
async def test_ask_is_stateless() -> None:
    provider = FakeProvider(reply="hi")
    service = ChatService(provider=provider, store=InMemoryConversationStore())

    out = await service.ask("m", "hello")

    assert out == "hi"
    assert provider.calls == [("m", [Message("user", "hello")])]


@pytest.mark.asyncio
async def test_chat_persists_history_and_system_prompt() -> None:
    provider = FakeProvider(reply="r1")
    store = InMemoryConversationStore()
    service = ChatService(provider=provider, store=store)

    await service.chat("c1", "m", "q1", system_prompt="be brief")
    provider.reply = "r2"
    await service.chat("c1", "m", "q2")

    history = await store.get("c1")
    assert history == [
        Message("system", "be brief"),
        Message("user", "q1"),
        Message("assistant", "r1"),
        Message("user", "q2"),
        Message("assistant", "r2"),
    ]


@pytest.mark.asyncio
async def test_clear_returns_true_only_when_present() -> None:
    service = ChatService(provider=FakeProvider(), store=InMemoryConversationStore())

    await service.chat("c", "m", "hi")
    assert await service.clear("c") is True
    assert await service.clear("c") is False


@pytest.mark.asyncio
async def test_list_models_delegates_to_provider() -> None:
    provider = FakeProvider(models=("a", "b"))
    service = ChatService(provider=provider, store=InMemoryConversationStore())

    assert list(await service.list_models()) == ["a", "b"]
