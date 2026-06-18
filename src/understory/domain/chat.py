"""Chat domain — provider-agnostic interfaces and value types.

Interfaces are ``Protocol``s on purpose (not ABCs); implementations also inherit
them for definition-time checking. Rationale: docs/decisions.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

# A provider-neutral JSON-schema (as a plain dict) describing the shape a
# completion must conform to. Providers that support constrained decoding honor
# it; others may ignore it. Never platform-specific.
Schema = Mapping[str, object]

Role = Literal["system", "user", "assistant", "tool"]
ConversationId = str
ModelName = str


@dataclass(frozen=True, slots=True)
class ToolDef:
    """Provider-neutral tool definition passed to the model."""

    name: str
    description: str
    parameters: Schema


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A single tool invocation returned by the model."""

    name: str
    args: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str
    tool_calls: Sequence[ToolCall] = field(default_factory=tuple)
    tool_call_id: str | None = None


class ChatProvider(Protocol):
    """A backend able to complete chat messages and list available models."""

    async def complete(
        self,
        model: ModelName,
        messages: Sequence[Message],
        *,
        schema: Schema | None = None,
        tools: Sequence[ToolDef] | None = None,
    ) -> Message:
        """Complete the messages.

        If *tools* is given, the reply may contain ``tool_calls``. If *schema*
        is given, the reply should conform to it (constrained decoding) where
        the provider supports it. ``tools`` and ``schema`` are mutually
        exclusive — callers must not pass both.
        """
        ...

    async def list_models(self) -> Sequence[ModelName]: ...


class ConversationStore(Protocol):
    """Persists per-conversation message history."""

    async def get(self, conversation_id: ConversationId) -> list[Message]: ...

    async def append(self, conversation_id: ConversationId, message: Message) -> None: ...

    async def clear(self, conversation_id: ConversationId) -> bool: ...

    async def exists(self, conversation_id: ConversationId) -> bool: ...
