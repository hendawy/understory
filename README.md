# Understory

> **An experiment.** Understory is a research spike testing one question:
> *can a layer of small local assistant models absorb enough real work to
> meaningfully cut a frontier model's token consumption?* The frontier agent
> (e.g. Claude Code) is the consumer; every task it can safely delegate to a
> local model is tokens it doesn't spend itself — **if** the local result is
> deterministic and trustworthy enough that the frontier agent doesn't have to
> redo or re-verify it. That "if" is what this project is probing. See
> [NORTH_STAR.md](NORTH_STAR.md) for the mission and [LEARNINGS.md](LEARNINGS.md)
> for the evidence log.

A Model Context Protocol (MCP) server that lets a frontier coding agent delegate
work to small local models — "the understory beneath the canopy." Today the
local models run on [Ollama](https://ollama.com/); the platform is deliberately
**replaceable** (see the Foundation Models spike below). Built on `asyncio` and
Server-Sent Events (SSE) via `uvicorn`.

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

- `delegate_task(task, model, workspace_path, max_steps, title?)`: Hand a whole task
  to a local model running as a sub-agent. It can read/write/edit/list files,
  **confined to `workspace_path`**, and iterates until done. Each run is recorded as
  a session (see `/trace/`). This is the core of the experiment.
- `ask_ollama(model, prompt)`: One-off stateless question.
- `chat_with_ollama(conversation_id, model, prompt, system_prompt)`: Stateful chat with history.
- `clear_ollama_chat(conversation_id)`: Drops the memory for a conversation.
- `list_ollama_models()`: Lists installed local models.

## Experimental spike: Apple Foundation Models as a second provider

To test the claim that the model platform is **replaceable** — and to see whether
Apple's on-device model can absorb work for free on a Mac — there is a planned spike
to add `FoundationProvider` alongside `OllamaChatProvider`.

The design is intentionally clean:

- The Python side is just another `ChatProvider` (`complete` / `list_models`); nothing
  in `domain`/`application` changes. This is the whole point of the provider port.
- Apple's `FoundationModels` framework is **Swift-only**, so the bridge is a small
  **Swift sidecar** — a long-lived local service that loads the on-device model once
  and answers requests over loopback. Python talks to it; it never knows it's Swift.
- Apple's native guided generation maps to our provider-neutral `schema` (constrained
  output), just as Ollama maps it to `format`.

> **Status: experimental, not yet built.** The cost is the Swift sidecar, not the
> Python design. See the `swift-foundation-sidecar` skill for how it should be built
> (the key rule: keep the model warm — long-lived service, never spawn per call).
