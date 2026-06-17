# Dogfooding learnings

Evidence log for the mission: does delegating to local models actually save the
main agent's tokens/time? Each entry records a real delegation, what happened,
and the takeaway. We want a measurable before/after as determinism improves.

## Method

For a feature, measure the same representative task **before** and **after** the
determinism work:
- **Model** and **task**
- **Steps** taken, whether it hit `max_steps`
- **JSON-protocol adherence** (clean / recovered from garbage / failed)
- **Correctness** of the output (did it pass review / guardrails)
- **Main-agent fix-up**: did I have to re-read or redo the work? (the token cost)

## #16 Constrained output

### Baseline (pre-#16) — PENDING
Task: write `slug.py::slugify` (lowercase, strip, hyphenate non-alnum runs,
trim hyphens) via `qwen2.5-coder:3b` in a sandbox.
> Blocked: MCP session went stale after a server restart; needs Claude Code
> reconnect before the baseline run. To be filled in.

### After (with constrained output) — TODO
Re-run the identical task once `delegate_task` passes a JSON schema to the model.
Compare steps / adherence / correctness against the baseline.
