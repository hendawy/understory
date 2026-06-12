# Understory

A Model Context Protocol (MCP) server that lets Antigravity (or any MCP client) interact with your local Ollama models concurrently using `asyncio` and Server-Sent Events (SSE) via `uvicorn`. The layer of small local models working beneath the canopy.

## Prerequisites

1. Ensure [Ollama](https://ollama.com/) is running locally and you have downloaded at least one model (e.g., `ollama pull llama3.2`).
2. Ensure you have [`uv`](https://docs.astral.sh/uv/) installed. 

## Quickstart

This project uses `uv` for lightning-fast dependency management. You do not need to manually install dependencies; `uv run` will handle it.

Start the MCP server using SSE:

```bash
cd understory
uv run uvicorn --app-dir src understory.infrastructure.mcp_server:app --host 0.0.0.0 --port 8000
```

The server will start listening for Server-Sent Events on `http://localhost:8000/sse`.

> **Do not use `--reload` when an MCP client is connected.** Clients (Claude Code,
> Antigravity, etc.) hold a long-lived SSE session. Each hot reload restarts the
> app and drops that session, so the client's in-flight tool calls fail with
> `MCP error -32602` until it reconnects. Use `--reload` only for solo development
> with no client attached.

The session trace UI is served at `http://localhost:8000/trace/`.

## Connecting Antigravity

Since we are running an SSE server, configure Antigravity to connect via the URL. 
Add the following to your Antigravity MCP settings:

```json
{
  "mcpServers": {
    "understory": {
      "serverURL": "http://localhost:8000/sse"
    }
  }
}
```

## Available Tools

- `ask_ollama(model, prompt)`: Best for one-off stateless questions.
- `chat_with_ollama(conversation_id, model, prompt, system_prompt)`: Best for persistent subagents where conversation history is maintained.
- `clear_ollama_chat(conversation_id)`: Drops the memory for a given agent conversation.
- `list_ollama_models()`: Lists installed Ollama models.
