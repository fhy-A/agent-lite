---
description: Code design decisions and architecture
---

Code is a local web-based AI Coding Agent. It uses a Python `http.server` backend, a vanilla JavaScript frontend, and an OpenAI-compatible gateway such as New API.

## Current architecture

Three tiers: Browser UI → local Python service → model gateway.

- **server.py** owns HTTP routing, filesystem/command safety, session persistence, local tools, upstream model connections, retry, SSE event buffering, cancellation, structured model-round aggregation, and an independent durable read-only AgentRun state machine.
- **app.js** owns prompt/context assembly, UI projection, and the existing browser Agent loop for plan/edit/auto modes. The explicit read-only profile delegates its full multi-round loop to the server.
- **agent-runtime.js** bridges the browser to both server-owned model rounds and durable AgentRun tasks. It polls by cursor, reconnects after transient failures, resumes credentials after a service restart, and cancels parent/child runs.
- **New API / compatible gateway** supplies models through `/v1/chat/completions`.

## Runtime boundary

A server model run owns exactly one upstream model round. It survives browser refresh and buffers replayable raw events. The server also aggregates a structured result containing answer text, reasoning, split tool calls, finish reason, and usage.

The independent `/api/agent/runs` path can persist messages and checkpoints, execute the four registered read-only tools, and continue model rounds without browser polling. It records tool-call fingerprints before execution and reuses completed results during recovery. API keys remain memory-only; a process restart loads active runs as `waiting_credentials` until the resume endpoint supplies keys again.

The production UI exposes a `read` permission profile as the explicit ownership switch. Its session checkpoint stores `executionOwner`, `agentRunId`, `agentEventCursor`, and the active child `runtimeRunId`; model rounds reuse the existing SSE renderer while durable model/tool events are projected into the session in order. Cursor advancement and the projected message snapshot are persisted together. The other permission profiles never fall back into this path, so a tool call has only one executor. Permission decisions, questionnaires, commands, writes, and sub-agents remain browser-owned until their durable protocols are implemented.

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
- Browser refresh recovery uses persisted session `runState` plus either a single-round runtime ID or a durable AgentRun ID/event cursor.
- Durable AgentRun state is stored separately under `data/agent-runs/`; production read-only session checkpoints reference it without copying credentials into session data.
