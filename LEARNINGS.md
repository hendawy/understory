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

### Baseline (pre-#16) — gemma4:e2b, user-service task

- **Model:** gemma4:e2b
- **Task:** Read users.json, create user_service.py (dataclass + 3 functions),
  create test_user_service.py
- **Steps:** 5
- **JSON adherence:** 1/4 tool calls parsed (read). 3/4 rejected — model wrapped
  valid JSON in markdown fences / preamble text.
- **Correctness:** No files written. Model said "done" claiming success — workspace
  was empty. Hallucinated completion.
- **Main-agent fix-up:** Total redo required. Zero usable output.

**Findings:**
1. Unconstrained output is unreliable — model can't resist surrounding text.
2. Model lies about completion — said "done" with empty workspace.
3. Constrained output (#16) should eliminate wrapper text via Ollama `format`.
4. Verified outcomes (#17) needed — model can claim success without delivering.

### After (with constrained output) — gemma4:e2b, user-service task

- **Model:** gemma4:e2b
- **Task:** identical to baseline
- **Steps:** 4
- **JSON adherence:** 4/4 tool calls parsed. Constrained output eliminated the
  markdown-wrapping problem entirely — every reply was valid JSON.
- **Correctness:** No files written. Model claimed "done" with empty workspace.
  Same hallucinated completion as baseline.
- **Main-agent fix-up:** Total redo required. Zero usable output.

**Delta from baseline:**
- JSON format: **fixed** — 4/4 vs 1/4 adherence.
- Actual output: **unchanged** — model skips tool use and declares victory.

**Findings:**
1. Constrained output solved the format problem but not the behavior problem.
2. The model either never calls `write` or goes straight to `{"done": "..."}`.
3. Verified outcomes (#17) is now the critical next piece — the agent loop must
   check that claimed work actually exists before accepting "done".
