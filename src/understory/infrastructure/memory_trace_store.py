"""In-memory TraceStore. Process-local, no persistence."""

from __future__ import annotations

from collections.abc import Sequence

from understory.domain.trace import Session, TraceStore


class InMemoryTraceStore(TraceStore):
    """Stores sessions in insertion order; ``list`` returns newest first."""

    def __init__(self) -> None:
        self._sessions: list[Session] = []

    def save(self, session: Session) -> None:
        """Persist (or overwrite) a session."""
        self._sessions = [s for s in self._sessions if s.id != session.id]
        self._sessions.append(session)

    def get(self, session_id: str) -> Session | None:
        """Return the session with *session_id*, or ``None`` if absent."""
        for s in self._sessions:
            if s.id == session_id:
                return s
        return None

    def list(self) -> Sequence[Session]:
        """Return all sessions, newest first."""
        return list(reversed(self._sessions))
