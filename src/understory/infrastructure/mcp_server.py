"""MCP transport — wires FastMCP tools to ChatService. Thin adapter."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from understory.application.agent_runner import AgentRunner
from understory.application.chat_service import ChatService
from understory.application.workspace_tools import (
    EditTool,
    ListDirTool,
    ReadTool,
    WriteTool,
)
from understory.infrastructure.local_filesystem import LocalFilesystemWorkspace
from understory.infrastructure.memory_store import InMemoryConversationStore
from understory.infrastructure.ollama_provider import OllamaChatProvider


def build_server(service: ChatService | None = None) -> FastMCP:
    service = service or ChatService(
        provider=OllamaChatProvider(),
        store=InMemoryConversationStore(),
    )

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
            return f"[{result.status} in {result.steps} steps] {result.output}"
        except Exception as e:
            return f"Error running task: {e}"

    return mcp


mcp = build_server()
app = mcp.sse_app()
