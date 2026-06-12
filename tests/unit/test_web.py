"""Contract tests for the trace web UI (server-rendered, 2 pages)."""

from __future__ import annotations

from starlette.testclient import TestClient

from understory.domain.trace import Session, Step
from understory.infrastructure.memory_trace_store import InMemoryTraceStore
from understory.infrastructure.web import build_web_app


def _store_with_session() -> InMemoryTraceStore:
    store = InMemoryTraceStore()
    store.save(
        Session(
            id="sess-1",
            model="gemma4:e2b",
            task="create hello.md",
            workspace_path="/tmp/ws",
            status="done",
            steps=(
                Step(
                    0,
                    '{"tool": "write", "args": {"path": "hello.md"}}',
                    "tool",
                    tool="write",
                    args={"path": "hello.md"},
                    observation="wrote hello.md",
                ),
                Step(1, '{"done": "created"}', "done"),
            ),
        )
    )
    return store


def test_index_lists_sessions() -> None:
    client = TestClient(build_web_app(_store_with_session()))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "sess-1" in resp.text
    assert "gemma4:e2b" in resp.text


def test_detail_shows_steps() -> None:
    client = TestClient(build_web_app(_store_with_session()))
    resp = client.get("/sess-1")
    assert resp.status_code == 200
    assert "write" in resp.text
    assert "wrote hello.md" in resp.text
    assert "created" in resp.text


def test_detail_missing_session_404() -> None:
    client = TestClient(build_web_app(InMemoryTraceStore()))
    assert client.get("/does-not-exist").status_code == 404


def test_model_output_is_html_escaped() -> None:
    # A malicious/odd model reply must not inject raw HTML into the page.
    store = InMemoryTraceStore()
    store.save(
        Session(
            id="xss",
            model="m",
            task="<script>alert(1)</script>",
            workspace_path="/tmp/ws",
            status="done",
            steps=(Step(0, "<img src=x onerror=alert(1)>", "error"),),
        )
    )
    client = TestClient(build_web_app(store))

    detail = client.get("/xss")
    assert "<script>alert(1)</script>" not in detail.text
    assert "&lt;script&gt;" in detail.text
    assert "<img src=x onerror=alert(1)>" not in detail.text
