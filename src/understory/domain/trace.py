"""Trace domain — a recorded session of an agent run and its steps.

A Session is one ``delegate_task`` run. A Step is one loop turn: the raw model
reply, what the runner made of it (tool call / done / format error), and the
resulting observation. Provider-agnostic; no I/O here.
"""

from __future__ import annotations

import json
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
    title: str
    model: str
    task: str
    workspace_path: str
    status: SessionStatus
    steps: Sequence[Step] = field(default_factory=tuple)


def default_title(task: str) -> str:
    """Derive a short human-readable session title from the task text.

    First non-empty line, trimmed to 60 chars; ``"untitled"`` if blank.
    """
    for line in task.splitlines():
        line = line.strip()
        if line:
            return line[:60]
    return "untitled"


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Structured result of a delegate_task run — high signal, low tokens."""

    status: SessionStatus
    steps: int
    session_id: str
    output: str
    files_changed: Sequence[str]
    verification_status: str
    verification_summary: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "status": self.status,
                "steps": self.steps,
                "session_id": self.session_id,
                "output": self.output,
                "files_changed": list(self.files_changed),
                "verification": {
                    "status": self.verification_status,
                    "summary": self.verification_summary,
                },
            }
        )


class TraceStore(Protocol):
    """Persists recorded sessions. Newest-first ordering for ``list``."""

    def save(self, session: Session) -> None: ...

    def get(self, session_id: str) -> Session | None: ...

    def list(self) -> Sequence[Session]: ...
