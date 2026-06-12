"""Routing tests for the combined ASGI app (trace UI mounted alongside MCP)."""

from __future__ import annotations

from starlette.testclient import TestClient

from understory.infrastructure.mcp_server import _build_app_with_store, build_server
from understory.infrastructure.memory_trace_store import InMemoryTraceStore


def _client() -> TestClient:
    store = InMemoryTraceStore()
    mcp = build_server(trace_store=store)
    return TestClient(_build_app_with_store(mcp, store))


def test_bare_trace_redirects_to_trailing_slash() -> None:
    resp = _client().get("/trace", follow_redirects=False)
    assert resp.status_code in (307, 308)
    assert resp.headers["location"].endswith("/trace/")


def test_trace_slash_serves_index() -> None:
    resp = _client().get("/trace/")
    assert resp.status_code == 200
    assert "Sessions" in resp.text
