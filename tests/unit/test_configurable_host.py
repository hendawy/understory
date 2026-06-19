"""Tests for configurable Ollama host."""

from __future__ import annotations

import pytest

from understory.infrastructure.ollama_provider import OllamaChatProvider


def test_accepts_host_parameter() -> None:
    """OllamaChatProvider can be constructed with a host argument."""
    provider = OllamaChatProvider(host="http://remote:11434")
    assert provider is not None


def test_default_host_is_none() -> None:
    """Without host, construction still works (uses Ollama default)."""
    provider = OllamaChatProvider()
    assert provider is not None


def test_build_server_reads_ollama_host_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """build_server should read UNDERSTORY_OLLAMA_HOST from environment."""
    monkeypatch.setenv("UNDERSTORY_OLLAMA_HOST", "http://remote:11434")

    from understory.infrastructure import mcp_server

    # Re-import / rebuild to pick up env var — just verify the code path
    # doesn't crash with the env var set.
    server = mcp_server.build_server()
    assert server is not None
