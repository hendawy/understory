# Understory

Local-first MCP server that lets a primary coding agent delegate work to small
local models — the "understory" working beneath the canopy. See `NORTH_STAR.md`
for vision and roadmap, `LEARNINGS.md` for dogfood results.

## Project structure

```
src/understory/
  domain/          # Protocols, value types, no third-party imports
    chat.py        # ChatProvider, Message, ToolDef, ToolCall, Schema
    tool.py        # Tool protocol, ToolError
    workspace.py   # Workspace protocol, WorkspaceError
    trace.py       # Step, TraceStore
    verification.py
  application/     # Use cases — imports domain only, no provider SDKs
    agent_runner.py    # Agent loop: model drives tools to complete a task
    chat_service.py    # Stateful chat
    workspace_tools.py # Read/Write/Edit/ListDir tools (implement Tool)
  infrastructure/  # Providers, MCP transport — the only layer with deps
    ollama_provider.py # OllamaChatProvider (only file that imports ollama)
    local_filesystem.py
    mcp_server.py      # FastMCP + Starlette, /trace web UI
    memory_store.py
    memory_trace_store.py
    web.py
tests/unit/        # Fakes, not mocks. No provider SDK imports.
benchmarks/        # Canned tasks for dogfooding (user_service.md)
```

## Tech

- Python 3.12+, `uv`-managed
- **Platform-independent** — must run on macOS, Linux, and Windows
- Ollama (local LLM provider, first backend)
- FastMCP + Starlette (MCP transport + HTTP)
- ty (type checking), pytest, ruff (lint + format)

## Architecture

Three layers, dependencies point inward only:

`domain` (protocols, value types) <- `application` (use cases) <- `infrastructure` (providers, transport)

- `domain` and `application` import **no** third-party provider SDKs.
- `OllamaChatProvider` is the only file allowed to import `ollama`.
- Each implementation class explicitly inherits its domain protocol.
- The model platform is replaceable — Ollama is one provider, not the design.

## Dev process

1. **Branch first.** `git checkout -b <type>/<slug>`. Never commit to `main`.
2. **Code and test.** Write tests + interfaces first, then implement. Iterate
   until all guardrails are green:
   ```
   uv run ty check
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   ```
3. **Review changes.** Check the diff for: security, simplicity, separation of
   concerns, code-to-interface, provider isolation. Iterate until clean.
4. **Commit and push.** `git push -u origin <branch>`.
5. **Dogfood after merge.** Run the benchmark task (`benchmarks/user_service.md`)
   via `delegate_task`. Record results in `LEARNINGS.md`.

## Current state

- Agent loop works end-to-end with gemma4:e2b (4-step dogfood success).
- Native tool calling wired up (Ollama tools param), with text JSON + fence
  stripping as fallback for models that don't support it.
- Constrained output, verified outcomes, per-session trace + web UI shipped.
- Next: native tool calling validation with tool-calling-capable models,
  structured result format, skill registry.
