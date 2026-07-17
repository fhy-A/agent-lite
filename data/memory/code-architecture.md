---
description: Code design decisions and architecture
---

Code is a local web-based AI Coding Agent. It uses a Python `http.server` backend, a vanilla JavaScript frontend, and an OpenAI-compatible gateway such as New API.

## Current architecture

Three tiers: Browser UI → local Python service → model gateway.

- **server.py** owns HTTP routing, filesystem/command safety, session persistence, local tools, upstream model connections, retry, SSE event buffering, cancellation, structured model-round aggregation, and an independent durable read-only AgentRun state machine.
- **app.js** still owns the full multi-round Agent loop, prompt/context assembly, tool orchestration, permission and questionnaire interaction, sub-agent scheduling, and UI projection.
- **agent-runtime.js** bridges the browser to server-owned model runs. It creates a run, polls event snapshots by cursor, reconstructs an SSE `Response`, reconnects after transient failures, and cancels by run ID.
- **New API / compatible gateway** supplies models through `/v1/chat/completions`.

## Runtime boundary

A server model run owns exactly one upstream model round. It survives browser refresh and buffers replayable raw events. The server also aggregates a structured result containing answer text, reasoning, split tool calls, finish reason, and usage.

The independent `/api/agent/runs` path can persist messages and checkpoints, execute the four registered read-only tools, and continue model rounds without browser polling. It records tool-call fingerprints before execution and reuses completed results during recovery. API keys remain memory-only; a process restart loads active runs as `waiting_credentials` until the resume endpoint supplies keys again.

The production browser UI still uses `runAgentLoop()` and the one-round runtime bridge, so the new AgentRun path is not yet the default execution owner. The next step is to persist `agentRunId` in the session checkpoint and project AgentRun events in the browser behind an explicit ownership switch. Only after that boundary is stable should permission, questionnaire, command, and write tools move server-side.

## Safety invariants

- The service listens on `127.0.0.1` by default.
- API keys and request payloads are cleared from model runs at terminal state and are never returned by runtime snapshots.
- Durable AgentRun records never contain API keys; credential-like model option fields and credential-bearing Base URLs are rejected.
- Path and command checks remain server-side.
- A tool call must have one execution owner; frontend and backend must never execute the same tool-call ID concurrently.
- Side-effecting tools require durable idempotency and permission state before they move into the server Agent loop.

## Persistence

- Packaged builds use `%USERPROFILE%/.code/`; source mode defaults to `data/`.
- Session messages use JSONL while metadata and run checkpoints are stored separately.
- Browser refresh recovery uses persisted session `runState` plus a server runtime run ID when the current model round is still alive.
- Durable AgentRun state is stored separately under `data/agent-runs/`; it is not yet referenced by production session checkpoints.
