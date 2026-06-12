"""Contract tests for the in-memory trace store."""

from __future__ import annotations

from understory.domain.trace import Session, Step
from understory.infrastructure.memory_trace_store import InMemoryTraceStore


def _session(sid: str) -> Session:
    return Session(
        id=sid,
        model="gemma4:e2b",
        task="do thing",
        workspace_path="/tmp/ws",
        status="done",
        steps=(Step(0, '{"done": "ok"}', "done"),),
    )


def test_save_then_get() -> None:
    store = InMemoryTraceStore()
    store.save(_session("a"))
    got = store.get("a")
    assert got is not None
    assert got.id == "a"
    assert got.model == "gemma4:e2b"


def test_get_missing_returns_none() -> None:
    assert InMemoryTraceStore().get("nope") is None


def test_list_is_newest_first() -> None:
    store = InMemoryTraceStore()
    store.save(_session("first"))
    store.save(_session("second"))
    ids = [s.id for s in store.list()]
    assert ids == ["second", "first"]
