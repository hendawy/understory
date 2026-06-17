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
6. **The model platform is replaceable.** Ollama is one provider, not the design.
   Nothing in `domain`/`application` imports `ollama` or assumes it. Platform-specific
   features (structured output, model listing, embeddings) are exposed as
   provider-neutral capabilities on the port and implemented per backend — never
   leaked upward. New capabilities get an interface first, an Ollama impl second.

## Roadmap

Ordered by the mission: deterministic, trustworthy delegation first; operability
and reach after. The model platform is **replaceable** — anything platform-specific
(e.g. Ollama's structured-output `format`) lives behind a provider port and never
leaks into `domain`/`application`.

### Shipped
- **Foundation** — layered `src/` layout, guardrails (ty/pytest/ruff), `arch-understudy` skill.
- **Sub-agent runtime** — confined `Workspace`; agent loop + `delegate_task`
  (text JSON protocol, recovers from malformed output); per-session trace + web UI at `/trace`.
- **Constrained output** — provider-neutral `schema` parameter on `ChatProvider.complete()`;
  Ollama impl uses `format`. Eliminates garbage JSON wrapping.
- **Verified outcomes** — `verify_outcome()` checks that files the model claimed
  to write actually exist. Catches hallucinated completion.
- **Tool prompt fix** — tool arg names now visible to the model. First successful
  dogfood run: gemma4:e2b read, wrote 2 files, and completed in 4 steps.

### Now — Native tool calling
The text-based JSON protocol works (gemma4:e2b produces files after the
arg-name fix) but is fragile — the model wasn't trained for our invented
format. Native tool calling uses the platform's built-in tool-use support,
which the model was fine-tuned for.

1. **Native tool calling on `ChatProvider`** — extend `complete()` to accept
   tool definitions and return structured tool calls, not raw text. The agent
   runner passes tool descriptions to the provider; each provider maps them to
   the platform's native format (Ollama `tools` parameter, Apple Foundation
   Models tool calling, etc.). The text protocol becomes a fallback, not the
   default. This also validates the provider abstraction — if two backends
   implement the same tool-calling interface, Ollama is genuinely replaceable.
2. **Structured result** — files changed + verification status as a compact summary,
   not prose. High signal, low tokens.

### Then — Skills & tooling
Let a small model punch above its weight and behave predictably.
- **Skill registry** — load/scope skills so the local agent's prompt stays small.

### v1.0 — General use
**Trigger:** Determinism & trust + Skills shipped, so delegation is reliable and
the main agent can hand off real work and trust the result. Only then is it worth
polishing for outside users.
- **Packaging** — installable (pip/uv), versioned release, `understory` console entrypoint.
- **Configuration** — model/endpoint/host configurable, nothing hardcoded.
- **Persistence** — sessions/traces survive restarts (sqlite or files behind the
  existing `TraceStore`/`ConversationStore` ports). Losing all state on restart is
  not acceptable for a released tool.
- **Docs** — quickstart, tool reference, the security/confinement model.
- **Branding** — name/logo, README polish, runnable examples.

### Later — Operability & reach (when needed, not blocking GA)
- Live trace updates (incremental recording + push).
- Telemetry / cost accounting — measure tokens saved vs spent (proves the mission).
- LSP integration — `definition`/`references`/`diagnostics` as tools, no prompt bloat.
- Pluggable model providers beyond the first two.

## Non-goals (for now)

- Hosting/remote deployment — local-first
- UI — MCP client is the UI
- Multi-tenant — single user

## Open questions

- Where does conversation state live long-term? (sqlite? files?)
- How do we test against real Ollama without flakiness? (record/replay?)
- Skill scoping mechanism — settings.json patch vs new harness primitive?
