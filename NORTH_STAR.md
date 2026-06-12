# Understory — North Star

## Vision

A local-first MCP server that lets a primary coding agent delegate work to small local models (Ollama today, others later) — the "understory" working beneath the canopy. Privacy-respecting, fast, and composable.

## Principles

1. **Simple beats clever.** Fewer files, fewer abstractions. Add structure only when it carries weight.
2. **Code to interfaces.** Business logic depends on protocols; providers (Ollama, future LLM platforms, MCP transports) sit behind them.
3. **Separation of concerns.** `domain` (rules, interfaces) → `application` (use cases) → `infrastructure` (providers, transport). One direction of dependency.
4. **Secure by default.** No secrets in code. Validate inputs at the boundary. Conservative defaults.
5. **Guardrails are non-negotiable.** `ty` typechecking, `pytest` units, `ruff format` — green before merge.
6. **Swap-friendly.** Ollama may be replaced. Nothing in `domain`/`application` imports `ollama`.

## Roadmap

### v0.1 — Foundation (now)
- [x] Working MCP server with Ollama tools
- [ ] `src/` layout, layered packages
- [ ] Test suite + guardrails wired in CI-ready form
- [ ] `arch-understudy` skill

### v0.2 — Per-project skill / MCP scoping
**Why first:** every other feature inflates the system prompt. Fix the ceiling first.
- Project-local skill discovery
- MCP server scoping per project
- Measure prompt-token reduction

### v0.3 — Sub-agent runtime
Turn the local model from a chat proxy into an agent the main LLM delegates
whole tasks to. Built in slices:
- [x] **Confined workspace** — `Workspace` port + `LocalFilesystemWorkspace`,
  jailed to one root (read/write/edit/list, escapes rejected). Security base.
- [x] **Agent loop** — local model picks tools (JSON protocol), executes, iterates,
  recovers from malformed output; exposed as MCP tool `delegate_task(task, model,
  workspace_path, max_steps)`.
- [ ] **Skill registry** — load/scope skills so the local agent's prompt stays small.

### v0.4 — LSP integration
- Language server client (Python first)
- Expose `definition`, `references`, `diagnostics` as MCP tools
- Streaming diagnostics without prompt bloat

### Later
- Pluggable model providers (not just Ollama)
- Conversation persistence (currently in-memory)
- Telemetry / cost accounting per delegated call

## Non-goals (for now)

- Hosting/remote deployment — local-first
- UI — MCP client is the UI
- Multi-tenant — single user

## Open questions

- Where does conversation state live long-term? (sqlite? files?)
- How do we test against real Ollama without flakiness? (record/replay?)
- Skill scoping mechanism — settings.json patch vs new harness primitive?
