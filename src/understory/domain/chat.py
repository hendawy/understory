"""Chat domain — provider-agnostic interfaces and value types."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user", "assistant"]
ConversationId = str
ModelName = str


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str


class ChatProvider(Protocol):
    """A backend able to complete chat messages and list available models."""

    async def complete(self, model: ModelName, messages: Sequence[Message]) -> Message: ...

    async def list_models(self) -> Sequence[ModelName]: ...


class ConversationStore(Protocol):
    """Persists per-conversation message history."""

    async def get(self, conversation_id: ConversationId) -> list[Message]: ...

    async def append(self, conversation_id: ConversationId, message: Message) -> None: ...

    async def clear(self, conversation_id: ConversationId) -> bool: ...

    async def exists(self, conversation_id: ConversationId) -> bool: ...
