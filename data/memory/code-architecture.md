---
description: Code design decisions and architecture
---

Code is a local web-based AI Coding Agent. It uses a Python `http.server` backend, a vanilla JavaScript frontend, and an OpenAI-compatible gateway such as New API.

## Current architecture

Three tiers: Browser UI → local Python service → model gateway.

- **server.py** owns HTTP routing, filesystem/command safety, session persistence, local tools, upstream model connections, retry, SSE event buffering, cancellation, and structured model-round aggregation.
- **app.js** still owns the full multi-round Agent loop, prompt/context assembly, tool orchestration, permission and questionnaire interaction, sub-agent scheduling, and UI projection.
- **agent-runtime.js** bridges the browser to server-owned model runs. It creates a run, polls event snapshots by cursor, reconstructs an SSE `Response`, reconnects after transient failures, and cancels by run ID.
- **New API / compatible gateway** supplies models through `/v1/chat/completions`.

## Runtime boundary

A server model run currently owns exactly one upstream model round. It survives browser refresh and buffers replayable raw events. The server also aggregates a structured result containing answer text, reasoning, split tool calls, finish reason, and usage.

The browser still consumes a completed round, executes tools, appends tool results, and starts the next round. Therefore closing the browser can pause the task at the model-to-tool boundary even though the active model request itself continues.

The migration plan is documented in `docs/SERVER_AGENT_LOOP_PLAN.md`. A shared `SERVER_TOOL_REGISTRY` now owns the four read-only tools (`list_files`, `read_file`, `search_files`, and `glob_files`) and is used by the existing HTTP routes. The next step is a durable multi-round `AgentRun` state machine that consumes this registry before side-effecting tools are migrated.

## Safety invariants

- The service listens on `127.0.0.1` by default.
- API keys and request payloads are cleared from model runs at terminal state and are never returned by runtime snapshots.
- Path and command checks remain server-side.
- A tool call must have one execution owner; frontend and backend must never execute the same tool-call ID concurrently.
- Side-effecting tools require durable idempotency and permission state before they move into the server Agent loop.

## Persistence

- Packaged builds use `%USERPROFILE%/.code/`; source mode defaults to `data/`.
- Session messages use JSONL while metadata and run checkpoints are stored separately.
- Browser refresh recovery uses persisted session `runState` plus a server runtime run ID when the current model round is still alive.
