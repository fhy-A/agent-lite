## v0.4.1: Security Overhaul & Message Rendering Refactor

3 commits since v0.4.0, focused on security hardening and a cleaner chat experience.

### Security Policy Overhaul
- **Denylist-only model**: Replaced whitelist with comprehensive denylist covering 8 danger categories (file destruction, disk ops, system destruction, permission changes, registry, services, security tampering, destructive git)
- **Compound command detection**: `&&`, `||`, `;`, `|` parsed into subcommands and checked independently
- **Backtick prohibited**: Prevents command substitution and PowerShell escape sequences
- **pip install** no longer blocked by chaining detection

### Message Rendering Refactored (Flat Projection)
- Only 4 content types in chat: user messages, thought process, edit proposals, final answers
- Tool cards hidden from main chat; details consolidated in tool log panel
- Thought process shown as continuous text before final answer (cleaner than collapsible cards)
- Timeline navigation restored (visible only with enough user messages)
- Per-task cumulative usage stats at answer bottom
- Thinking indicator: blue dot + timer during model thinking
- Preview copy button restored to icon style
- Reduced flicker by skipping re-render when visible content unchanged

### New Skills
- **image-generation**: matplotlib + Pillow chart templates (bar/line/pie/3D/dashboard/watermark/stitch)
- **document-design**: 12 color schemes + docx/pptx/xlsx/markdown beautification templates

### Error Handling & Failure Detection
- All empty/missing parameter errors now include actionable guidance (example syntax, path hints)
- 3 consecutive NameError → force break loop with session-save suggestion
- Added IndentationError, KeyError, ValueError, IndexError, ImportError to runtime error detection
- AbortError: drained queued messages into session instead of discarding
- Path resolution: fallback to output/ directory instead of raising error

### UI Improvements
- Esc key: pauses agent run, skipped when typing in inputs
- Composer scrollbar: 6px thin with subtle color
- Clickable file paths in chat: inline code opens preview panel
- Session file copy button: fixed visual feedback
