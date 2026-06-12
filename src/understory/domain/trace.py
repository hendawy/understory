"""Trace domain — a recorded session of an agent run and its steps.

A Session is one ``delegate_task`` run. A Step is one loop turn: the raw model
reply, what the runner made of it (tool call / done / format error), and the
resulting observation. Provider-agnostic; no I/O here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

StepKind = Literal["tool", "done", "error"]
SessionStatus = Literal["done", "max_steps"]


@dataclass(frozen=True, slots=True)
class Step:
    index: int
    reply: str
    kind: StepKind
    tool: str | None = None
    args: Mapping[str, str] | None = None
    observation: str | None = None


@dataclass(frozen=True, slots=True)
class Session:
    id: str
    model: str
    task: str
    workspace_path: str
    status: SessionStatus
    steps: Sequence[Step] = field(default_factory=tuple)


class TraceStore(Protocol):
    """Persists recorded sessions. Newest-first ordering for ``list``."""

    def save(self, session: Session) -> None: ...

    def get(self, session_id: str) -> Session | None: ...

    def list(self) -> Sequence[Session]: ...
