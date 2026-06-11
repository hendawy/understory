"""Use cases — orchestrate provider + store. No I/O, no framework imports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from understory.domain.chat import (
    ChatProvider,
    ConversationId,
    ConversationStore,
    Message,
    ModelName,
)


@dataclass(frozen=True, slots=True)
class ChatService:
    provider: ChatProvider
    store: ConversationStore

    async def ask(self, model: ModelName, prompt: str) -> str:
        """Stateless single-turn completion."""
        reply = await self.provider.complete(model, [Message("user", prompt)])
        return reply.content

    async def chat(
        self,
        conversation_id: ConversationId,
        model: ModelName,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Stateful multi-turn completion."""
        if not await self.store.exists(conversation_id) and system_prompt:
            await self.store.append(conversation_id, Message("system", system_prompt))

        await self.store.append(conversation_id, Message("user", prompt))
        history = await self.store.get(conversation_id)
        reply = await self.provider.complete(model, history)
        await self.store.append(conversation_id, reply)
        return reply.content

    async def clear(self, conversation_id: ConversationId) -> bool:
        return await self.store.clear(conversation_id)

    async def list_models(self) -> Sequence[ModelName]:
        return await self.provider.list_models()
