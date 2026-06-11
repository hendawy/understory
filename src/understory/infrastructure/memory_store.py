"""In-memory ConversationStore. Process-local, no persistence."""

from __future__ import annotations

from understory.domain.chat import ConversationId, ConversationStore, Message


class InMemoryConversationStore(ConversationStore):
    def __init__(self) -> None:
        self._data: dict[ConversationId, list[Message]] = {}

    async def get(self, conversation_id: ConversationId) -> list[Message]:
        return list(self._data.get(conversation_id, []))

    async def append(self, conversation_id: ConversationId, message: Message) -> None:
        self._data.setdefault(conversation_id, []).append(message)

    async def clear(self, conversation_id: ConversationId) -> bool:
        return self._data.pop(conversation_id, None) is not None

    async def exists(self, conversation_id: ConversationId) -> bool:
        return conversation_id in self._data
