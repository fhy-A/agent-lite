---
description: agent-lite design decisions and architecture
---

Agent Lite is a local web-based coding agent. It uses Python http.server as backend, vanilla JS frontend, and New API as model gateway. The agent loop runs serialize tool calls with safety guards.

## Architecture

Three-tier: Browser (app.js) → Python HTTP Server (server.py) → New API (模型网关)

- **server.py**: Pure HTTP routing + filesystem ops + transparent proxy. No AI logic, no SSE parsing, no prompt building. All safety checks (command whitelist, path sandbox) live here.
- **app.js**: All intelligence — agent loop (max 50 rounds), SSE stream parsing, message rendering, session persistence, propose_edit confirmation dialogs.
- **New API**: External model gateway, called via `/proxy/chat` (SSE stream) and `/proxy/models`.

## Key Flow

1. User sends message → `runAgentLoop()` starts
2. Build messages (system prompt + history + memory + skills + project context)
3. `callModelOnce()` → POST `/proxy/chat` with native tools array → server.py proxies to New API
4. SSE chunks streamed back, parsed by app.js for content delta + tool_call delta
5. Tool calls executed via `POST /api/tools/{action}` to server.py
6. Results inserted as `role: "tool-result"`, loop continues until pure text or round limit
7. `propose_edit` is two-phase: preview (diff only) → user confirms → `apply_edit` writes with backup

## Safety

- Command whitelist (SAFE_COMMAND_PREFIXES), denied patterns for write/delete/redirect
- Path sandbox: all file ops resolve within project root
- API keys stored in browser localStorage, passed via HTTP headers per request
