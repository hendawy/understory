---
name: swift-foundation-sidecar
description: Build and maintain the Swift sidecar that wraps Apple's on-device Foundation Models so Understory's Python can use it as a ChatProvider. Use when writing Swift for the macOS Foundation Models bridge, working with LanguageModelSession / guided generation, or running it as a long-lived local service. Covers modern Swift, the bridge contract, and the keep-the-model-warm rule.
---

# swift-foundation-sidecar

Understory is Python; Apple's Foundation Models framework is Swift-only. This
skill is for writing the **sidecar** — a small Swift program that wraps the
on-device model and speaks a tiny local protocol the Python `FoundationProvider`
can call. The Python side never knows it's Swift; it just sees a `ChatProvider`.

This is an **experiment**: the goal is to test whether a local Apple model can
absorb work that would otherwise cost frontier-model tokens. Keep it small.

## The one rule that decides efficiency

**The sidecar is a long-lived service. Load the model once, keep it warm.**
Never spawn a fresh process (and reload the model) per request — that pays seconds
of cold start on every agent step. Start the service once; answer many requests
over localhost. With that, the wrapper overhead is invisible and latency = the
model itself.

- Create one `LanguageModelSession`, reuse it (or pool per conversation).
- Call `prewarm()` at startup so the first real request isn't cold.
- Serve over loopback only (`127.0.0.1`) — never bind a public interface.

## The bridge contract

The sidecar exposes exactly what `ChatProvider` needs — no more:

- `POST /complete` — body `{ "model": str, "messages": [{role, content}], "schema": <json-schema|null> }`
  → `{ "content": str }`. If `schema` is present, use guided generation so the
  reply conforms (this is the provider-neutral `schema` from `domain/chat.py`,
  mapped to Apple's structured output here — the mapping lives ONLY in Swift).
- `GET /models` → `{ "models": [str] }` (availability/identifier of the on-device model).
- Health: a plain `GET /healthz` → 200 once the model is ready.

Transport: a minimal HTTP server (or newline-delimited JSON over a stdin/stdout
pipe). HTTP is easier to test with `curl`. Sub-millisecond next to inference.

## Foundation Models notes

- Gate on availability: `SystemLanguageModel.default.availability` — surface a clear
  "model unavailable" (device unsupported / Apple Intelligence off / not downloaded)
  instead of crashing. `/models` returns `[]` when unavailable.
- Guided generation: prefer a runtime schema (`DynamicGenerationSchema` built from the
  incoming JSON schema) so the model emits exactly `{tool,args}` or `{done}`. This is
  the Swift analogue of Ollama's `format=`.
- Respect the context window (small, ~4k). Don't accumulate unbounded history.
- Text in / text out. No tool execution in Swift — tools run in Python.

## Modern Swift practices

- Swift 6 language mode; `async`/`await` and structured concurrency, no callback soup.
- `Sendable` correctness; isolate the session behind an `actor` if shared across requests.
- Value types (`struct`) for request/response DTOs; `Codable` for JSON.
- Typed errors; never force-unwrap network or model results. No `try!`, no `fatalError`
  on a recoverable path.
- Swift Package Manager; ship a single executable target. Keep dependencies near zero.

## Security

- Loopback bind only; no auth needed because it's local-only, but never expose it.
- Validate/decode every request with `Codable`; reject malformed bodies with 400.
- No file, shell, or network access from the sidecar — it only talks to the model.

## Testing & guardrails

- `swift test` (swift-testing or XCTest) for: JSON decode/encode of the DTOs, the
  JSON-schema → `DynamicGenerationSchema` mapping, and availability handling. These
  don't need the real model — fake the session behind a protocol, mirroring how the
  Python side fakes the provider.
- `swift build` must be warning-clean.
- The Python `FoundationProvider` is tested separately against a **fake sidecar**
  (an in-process stub), so the two halves can be validated independently.

## What you don't do

- Don't run model inference in tests or CI.
- Don't add endpoints beyond the contract above.
- Don't put any tool logic, file access, or agent loop in Swift — that's Python's job.
- Don't make it a per-call CLI. Long-lived service only.
