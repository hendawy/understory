"""Contract tests for the in-memory trace store."""

from __future__ import annotations

from understory.domain.trace import Session, Step, default_title
from understory.infrastructure.memory_trace_store import InMemoryTraceStore


def _session(sid: str) -> Session:
    return Session(
        id=sid,
        title="Do thing",
        model="gemma4:e2b",
        task="do thing",
        workspace_path="/tmp/ws",
        status="done",
        steps=(Step(0, '{"done": "ok"}', "done"),),
    )


def test_default_title_uses_first_nonempty_line() -> None:
    assert default_title("\n  Create hello.md  \nmore") == "Create hello.md"


def test_default_title_truncates_to_60_chars() -> None:
    assert default_title("x" * 200) == "x" * 60


def test_default_title_blank_is_untitled() -> None:
    assert default_title("   \n  ") == "untitled"


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
