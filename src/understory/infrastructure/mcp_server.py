"""MCP transport — wires FastMCP tools to ChatService. Thin adapter."""

from __future__ import annotations

import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from understory.application.agent_runner import AgentRunner
from understory.application.chat_service import ChatService
from understory.application.workspace_tools import (
    EditTool,
    ListDirTool,
    ReadTool,
    WriteTool,
)
from understory.domain.trace import Session, TraceStore, default_title
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace
from understory.infrastructure.memory_store import InMemoryConversationStore
from understory.infrastructure.memory_trace_store import InMemoryTraceStore
from understory.infrastructure.ollama_provider import OllamaChatProvider
from understory.infrastructure.web import build_web_app


def build_server(
    service: ChatService | None = None,
    trace_store: TraceStore | None = None,
) -> FastMCP:
    """Build and return the FastMCP server.

    Pass *trace_store* to share a specific store (so the web UI and the
    delegate_task tool see the same sessions); one is created otherwise.
    """
    service = service or ChatService(
        provider=OllamaChatProvider(),
        store=InMemoryConversationStore(),
    )
    store = trace_store or InMemoryTraceStore()

    mcp = FastMCP("understory")

    @mcp.tool()
    async def ask_ollama(model: str, prompt: str) -> str:
        """Send a stateless prompt to an Ollama model."""
        try:
            return await service.ask(model, prompt)
        except Exception as e:
            return f"Error communicating with Ollama: {e}"

    @mcp.tool()
    async def chat_with_ollama(
        conversation_id: str,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Send a stateful prompt; conversation history is maintained."""
        try:
            return await service.chat(conversation_id, model, prompt, system_prompt)
        except Exception as e:
            return f"Error communicating with Ollama: {e}"

    @mcp.tool()
    async def clear_ollama_chat(conversation_id: str) -> str:
        """Clear conversation history."""
        cleared = await service.clear(conversation_id)
        return (
            f"Conversation '{conversation_id}' cleared."
            if cleared
            else f"Conversation '{conversation_id}' not found."
        )

    @mcp.tool()
    async def list_ollama_models() -> str:
        """List installed Ollama models."""
        try:
            models = await service.list_models()
            return f"Available models: {', '.join(models)}"
        except Exception as e:
            return f"Error listing models: {e}"

    @mcp.tool()
    async def delegate_task(
        task: str,
        model: str,
        workspace_path: str,
        max_steps: int = 10,
        title: str | None = None,
    ) -> str:
        """Delegate a task to a local model that can read/write/edit/list files,
        confined to workspace_path. Returns the model's final answer."""
        try:
            workspace = LocalFilesystemWorkspace(Path(workspace_path))
            tools = [
                ReadTool(workspace),
                WriteTool(workspace),
                EditTool(workspace),
                ListDirTool(workspace),
            ]
            runner = AgentRunner(service.provider, tools, max_steps=max_steps)
            result = await runner.run(model, task)
            sid = uuid.uuid4().hex
            session = Session(
                id=sid,
                title=title or default_title(task),
                model=model,
                task=task,
                workspace_path=workspace_path,
                status=result.status,
                steps=result.transcript,
            )
            store.save(session)
            return f"[{result.status} in {result.steps} steps] (session {sid}) {result.output}"
        except Exception as e:
            return f"Error running task: {e}"

    return mcp


def _build_app_with_store(mcp: FastMCP, store: TraceStore) -> Starlette:
    """Return a single ASGI app: trace UI at ``/trace``, MCP SSE at ``/``."""
    web_app = build_web_app(store)
    sse_app = mcp.sse_app()
    return Starlette(
        routes=[
            Mount("/trace", app=web_app),
            Mount("/", app=sse_app),
        ]
    )


# Module-level singletons — one shared store so trace UI and MCP tool are
# in the same process and see the same sessions.
_store = InMemoryTraceStore()
mcp = build_server(trace_store=_store)
app = _build_app_with_store(mcp, _store)
