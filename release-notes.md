## v0.4.3: Update System Overhaul

### Update System Rewrite
- **Removed auto-check popup**: no more tkinter dialog on every launch, update is manual via Settings → Update
- **Batch-based atomic replacement**: download → click "Install & Restart" → batch script waits for exit, copies new exe in place, restarts
- **Versioned installers**: downloads named `AgentLite-v0.4.3.exe` instead of `.new`/`.old` suffixes
- **Auto-cleanup**: old versioned installers in the same directory are deleted, only the latest kept
- **Path-independent**: works no matter where the exe is located (Desktop, Downloads, custom folder)

### Onboarding
- User guide now only appears on first install, no longer re-triggers on version updates

---

## v0.4.2: File Tree, Image Storage & Platform Integration

50+ commits since v0.4.1, focused on UX polish, image handling, and New API platform login.

### New API Platform Integration
- **Login with platform account**: settings → 账户 → login via New API OAuth-like flow
- **Key sync**: fetch all API keys from platform, bulk copy (space or colon separated)
- **Account panel**: display username, logout

### File Tree Overhaul
- **Extension color-coding**: JS=orange, Python=blue, CSS=purple, images=pink, etc.
- **Sort controls**: type/time sort with asc/desc toggle, persisted across sessions
- **Right-click context menu**: open with default app, copy full path, reveal in Explorer
- **Modified date display**: file tree shows last modified date
- **Tighter spacing**: smaller font (12px name, 10px size), no file size display
- **@ button**: hover to reveal, overlays without reserving space
- Sidebar minimum width increased to 220px

### Image Handling
- Images stored as files in `data/attachments/` instead of inline base64 (JSON size reduced 100x)
- Images rendered as separate messages, not mixed with text
- Click-to-preview: click any chat image to open full-size overlay (click or Esc to close)
- Removed 6-image limit
- Auto-scroll to bottom after image loads

### Bug Fixes
- `detectLanguage()` crash on image messages
- i18n: 6 translation keys restored to Chinese
- Key deduplication + colon/space format support
- Model list auto-refresh on panel open, cleared when no keys
- Chat auto-scroll after message render
- System prompt: conciseness + per-subtask summary rules

### UX Improvements
- File tree sort button (auto-width for i18n, left-click toggle / right-click cycle)
- Context menu stays within viewport
- Folder context menu: explore, copy path, open terminal (PowerShell)
