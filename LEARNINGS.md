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

## Native tool calling + fence stripping

### Dogfood — gemma4:e2b, user-service task (2026-06-18)

- **Model:** gemma4:e2b
- **Task:** identical to baseline (read users.json, create user_service.py + test_user_service.py)
- **Steps:** 4 (read → write user_service.py → write test_user_service.py → done)
- **JSON adherence:** 4/4 parsed via text fallback with fence stripping. Native
  tool calling was passed to Ollama but gemma4:e2b responded with fenced text
  JSON, not structured tool_calls. The fence-stripping fallback caught it.
- **Correctness:** Both files written and correct. User dataclass has all 3 fields,
  all 3 functions present with correct logic. Tests cover all functions.
- **Main-agent fix-up:** None. First fully successful end-to-end run.

**Delta from previous:**
- Output: **fixed** — 2 files written vs 0. First time the model produced usable code.
- Steps: 4 (same as constrained output run, but this time productive).
- Tool protocol: gemma4:e2b doesn't use Ollama's native tool_calls — falls back
  to text JSON. The fence-stripping fix was the key unblocking change.

**Findings:**
1. gemma4:e2b ignores Ollama's `tools` parameter and responds with text JSON
   wrapped in markdown fences. Native tool calling with this model is a no-op.
2. Fence stripping is essential — without it, the text fallback fails on every step.
3. The combination of constrained-output-era prompt + fence stripping + tool arg
   names in the prompt was enough for the model to actually use tools correctly.
4. Should test with a model that actually supports native tool calling (e.g.
   qwen2.5-coder or a larger model) to validate the native path.

## Structured result — real dogfood (2026-06-18)

### Dogfood — gemma4:e2b, implement format_result

- **Model:** gemma4:e2b
- **Task:** Read result_formatter.py containing a stub function (raises
  NotImplementedError), implement the body to construct a TaskResult from
  AgentResult + Verification fields.
- **Steps:** 3 (read → write → done)
- **Correctness:** Exact correct implementation. All 7 field mappings correct.
  Output is identical to what a frontier model produced for the same task.
- **Main-agent fix-up:** None.

**Findings:**
1. First real dogfood where the frontier model (Claude) delegated actual
   project work to the local model via `delegate_task`. Previous dogfood
   runs used the benchmark task; this used a real feature implementation.
2. gemma4:e2b handles "implement this stub" tasks well when the interface
   is fully specified — field names, types, and mapping instructions in
   the docstring were enough.
3. The workspace setup pattern works: put context files + a stub with a
   clear docstring in a temp directory, call `delegate_task`.
4. The running MCP server returned the old prose format (not the new
   structured JSON) because it's running from `main`. Confirms the
   structured-result change is not yet deployed.

## Configurable Ollama host — real dogfood (2026-06-18)

### Dogfood — gemma4:e2b, two-file edit (ollama_provider + mcp_server)

- **Model:** gemma4:e2b
- **Task:** Add `host` param to `OllamaChatProvider.__init__`, add env var
  reading in `mcp_server.py`.
- **Attempt 1:** Both files in one workspace, one task description.
  - **Steps:** 15 (hit max_steps)
  - **Result:** ollama_provider.py correct, mcp_server.py unchanged. Model
    got task 1 right but missed task 2 entirely. Verification passed because
    both files existed (they were pre-existing), but mcp_server.py was
    written back without the requested changes.
- **Attempt 2:** Single file (mcp_server.py only), focused task.
  - **Steps:** 5 (done)
  - **Result:** Both changes correct — `import os` added, env var reading
    added. Import ordering wrong (`os` after `uuid`), fixed by ruff.
- **Main-agent fix-up:** ruff auto-fixed import order. No manual code edits.

**Findings:**
1. Multi-file tasks with independent edits should be split into separate
   `delegate_task` calls. The model handled one file well but dropped the
   second when both were in the same task.
2. Single-file, focused tasks work reliably — 3-5 steps, correct output.
3. The model doesn't know about import ordering conventions — ruff catches
   this, so it's fine. The frontier model runs guardrails, not the local model.
4. Verification can give false positives on edit tasks — "file exists"
   doesn't mean "file was correctly modified." Need content-level
   verification for edits (future improvement).
