# Understory — North Star

## Vision

A local-first MCP server that lets a primary coding agent delegate work to small local models (Ollama today, others later) — the "understory" working beneath the canopy. Privacy-respecting, fast, and composable.

## Mission (the why)

**Understory exists to cut the main agent's token consumption.** The primary
coding agent (Claude Code) is the consumer. Every task it can safely hand to a
local model is tokens it doesn't spend itself. For delegation to actually pay
off, two things must hold:

1. **Deterministic, trustworthy outcomes.** The local model must produce
   correct, verifiable results — so the main agent can trust a compact signal
   ("done, guardrails green") instead of re-reading files to check. Unreliable
   output costs *more* tokens than doing it directly.
2. **Better skills and tooling.** Scoped skills and sharp tools let a small
   model punch above its weight and behave predictably.

Every feature is judged by: *does this let the main agent delegate more, and
trust the result with fewer tokens spent verifying?*

## Principles

1. **Simple beats clever.** Fewer files, fewer abstractions. Add structure only when it carries weight.
2. **Code to interfaces.** Business logic depends on protocols; providers (Ollama, future LLM platforms, MCP transports) sit behind them.
3. **Separation of concerns.** `domain` (rules, interfaces) → `application` (use cases) → `infrastructure` (providers, transport). One direction of dependency.
4. **Secure by default.** No secrets in code. Validate inputs at the boundary. Conservative defaults.
5. **Guardrails are non-negotiable.** `ty` typechecking, `pytest` units, `ruff format` — green before merge.
6. **Swap-friendly.** Ollama may be replaced. Nothing in `domain`/`application` imports `ollama`.

## Roadmap

### v0.1 — Foundation
- [x] Working MCP server with Ollama tools
- [x] `src/` layout, layered packages
- [x] Test suite + guardrails wired in CI-ready form
- [x] `arch-understudy` skill

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
- [x] **Per-session trace + web UI** — record every step; inspect at `/trace`.
- [ ] **Skill registry** — load/scope skills so the local agent's prompt stays small.

### v0.4 — Determinism & trust (NEXT — serves the mission directly)
Make delegated outcomes reliable enough that the main agent trusts a compact
signal instead of re-verifying. Ordered by leverage:
- [ ] **Constrained output** — use Ollama structured output (`format` / JSON
  schema) so the model is forced to emit valid `{"tool"...}` / `{"done"...}`.
  Fewer wasted steps, fewer garbage recoveries → more deterministic loops.
- [ ] **Verified outcomes** — give the local agent a confined "run check" tool
  and have `delegate_task` run the project's guardrails after edits, reporting
  `verified: green/red`. The main agent trusts green; no file re-reading.
- [ ] **Structured result** — return files changed + verification status as a
  compact summary, not prose. High signal, low tokens.

### v0.5 — LSP integration
- Language server client (Python first)
- Expose `definition`, `references`, `diagnostics` as MCP tools
- Streaming diagnostics without prompt bloat

### Later
- Pluggable model providers (not just Ollama)
- Persist sessions/conversations across restarts (currently in-memory)
- Live trace updates (incremental recording + push)
- Telemetry / cost accounting per delegated call (tokens saved vs spent)

## Non-goals (for now)

- Hosting/remote deployment — local-first
- UI — MCP client is the UI
- Multi-tenant — single user

## Open questions

- Where does conversation state live long-term? (sqlite? files?)
- How do we test against real Ollama without flakiness? (record/replay?)
- Skill scoping mechanism — settings.json patch vs new harness primitive?
