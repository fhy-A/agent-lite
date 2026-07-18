---
description: Code design decisions and architecture
---

Code is a local web-based AI Coding Agent. It uses a Python `http.server` backend, a vanilla JavaScript frontend, and an OpenAI-compatible gateway such as New API.

## Current architecture

Three tiers: Browser UI → local Python service → model gateway.

- **server.py** owns HTTP routing, filesystem/command safety, session persistence, local tools, upstream model connections, retry, SSE event buffering, cancellation, structured model-round aggregation, and a durable AgentRun state machine with project-read, network, Skill, questionnaire, edit/file authorization, non-replayable command, idempotent project-memory, recoverable direct file mutation, and persistent child-agent delegation protocols.
- **app.js** owns prompt/context assembly, UI projection, and questionnaire/authorization interactions. All four permission profiles delegate new multi-round tasks to the server; the legacy browser Agent loop remains only for checkpoints that explicitly persisted `executionOwner=browser` before the migration.
- **agent-runtime.js** bridges the browser to both server-owned model rounds and durable AgentRun tasks. It polls by cursor, reconnects after transient failures, submits questionnaire/authorization decisions, resumes credentials after a service restart, and cancels parent/child runs. `app.js` projects durable authorization waits into the existing diff review card and stores the stable request in the session checkpoint.
- **New API / compatible gateway** supplies models through `/v1/chat/completions`.

## Runtime boundary

A server model run owns exactly one upstream model round. It survives browser refresh and buffers replayable raw events. The server also aggregates a structured result containing answer text, reasoning, split tool calls, finish reason, and usage.

The independent `/api/agent/runs` path can persist messages and checkpoints, execute the four registered read-only tools, pause durably on `request_user_input`, and run the registered `propose_edit` protocol. Questionnaire state is stored as `pendingInput`; edit approval state is stored as `pendingAuthorization`. Validated answers or authorization decisions become the matching tool result before the run resumes. Edit proposals carry stable content hashes and the original mtime; approved applications are serialized, backed up, atomically replaced, verified, and replay-safe if the process exits after writing. API keys remain memory-only; a process restart loads active model/tool work as `waiting_credentials`, while questionnaire and authorization waits remain actionable without credentials.

The production UI selects a single durable AgentRun execution owner for every valid permission profile. `read` exposes only project reads and interaction, `plan` adds proposal/delegation without direct side effects, `accept` persists user authorization before side effects, and `bypass` executes its allowed side effects without authorization. Session checkpoints store `executionOwner`, `agentRunId`, `agentEventCursor`, the active child `runtimeRunId`, and visible questionnaire/authorization state; an explicitly saved legacy browser owner is preserved during recovery rather than silently changing tracks. Model rounds reuse the existing SSE renderer while durable model/tool events are projected into the session in order. Cursor advancement and the projected message snapshot are persisted together. Authorization cards preserve the real action (`apply_edit`, `write_file`, `delete_file`, or `run_command`), target and diff/command preview across refresh, and a restored card can submit its decision without an in-memory Promise. The server registry and AgentRun execute `web_fetch`, `use_skill`, `read_skill_resource`, `run_command`, `save_memory`, `write_file`, `delete_file`, and `task` delegation without browser relay. Each `task` creates a durable Child AgentRun with parent IDs and depth, inherits the parent model/permission/tool policy, removes nested delegation and questionnaires, proxies child authorizations through the parent, propagates cancellation, and merges child usage once. Same-turn task calls use a concurrency limit of three; additional children wait for a slot, while tool results are appended to the parent protocol in original call order. Restart recovery reuses persisted child IDs and terminal results.

## Safety invariants

- The service listens on `127.0.0.1` by default.
- API keys and request payloads are cleared from model runs at terminal state and are never returned by runtime snapshots.
- Durable AgentRun records never contain API keys; credential-like model option fields and credential-bearing Base URLs are rejected.
- Path and command checks remain server-side.
- A tool call must have one execution owner; frontend and backend must never execute the same tool-call ID concurrently.
- Side-effecting tools require durable idempotency and permission state before they move into the server Agent loop; `propose_edit` is the reference implementation for that rule.
- Child agents cannot raise the parent permission profile, delegate grandchildren, or request their own interactive questionnaire; child side-effect authorizations are exposed and decided through the parent run.

## Persistence

- Packaged builds use `%USERPROFILE%/.code/`; source mode defaults to `data/`.
- Session messages use JSONL while metadata and run checkpoints are stored separately.
- Browser refresh recovery uses persisted session `runState` plus either a single-round runtime ID or a durable AgentRun ID/event cursor.
- Durable AgentRun state is stored separately under `data/agent-runs/`; all new production task checkpoints reference it without copying credentials into session data.
