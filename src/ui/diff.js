(function registerDiffUi(global) {
  "use strict";

  const Code = global.Code;
  if (!Code?.ui) throw new Error("Code namespace must load before diff UI");

  function normalizeDiffText(text = "") {
    const source = String(text).replace(/\r\n/g, "\n");
    const fenced = source.match(/```(?:diff)?\s*\n([\s\S]*?)\n?```/i);
    if (fenced) return fenced[1].trimEnd();

    const lines = source.split("\n");
    const firstHeader = lines.findIndex((line) => line.startsWith("--- "));
    const normalized = firstHeader >= 0 ? lines.slice(firstHeader) : lines;
    while (normalized.length && /^```(?:diff)?\s*$/i.test(normalized[0].trim())) normalized.shift();
    while (normalized.length && /^```\s*$/.test(normalized.at(-1).trim())) normalized.pop();
    return normalized.join("\n").trimEnd();
  }

  function getDiffStats(text = "") {
    const lines = normalizeDiffText(text).split("\n");
    return {
      additions: lines.filter((line) => line.startsWith("+") && !line.startsWith("+++")).length,
      removals: lines.filter((line) => line.startsWith("-") && !line.startsWith("---")).length,
      lineCount: lines.length,
    };
  }

  function isEditSuggestionMessage(msg) {
    if (!msg || msg.role !== "tool-result") return false;
    const meta = msg.meta || {};
    const action = meta.action || meta.tool?.action || "";
    return !!meta.pendingEditId && (["propose_edit", "apply_edit", "write_file", "delete_file"].includes(action) || !!meta.newContent);
  }

  function createDiffFeature(options = {}) {
    const escapeHtml = options.escapeHtml || ((value) => String(value ?? ""));
    const highlightSyntax = options.highlightSyntax || ((value) => escapeHtml(value));
    const renderMarkdown = options.renderMarkdown || ((value) => escapeHtml(value));
    const renderCopyButton = options.renderCopyButton || (() => "");
    const t = options.t || ((key) => key);
    const getMessageText = options.getMessageText || ((msg) => String(msg?.content || ""));
    const getPendingEdits = options.getPendingEdits || (() => ({}));
    const getAuthorizationRequests = options.getAuthorizationRequests || (() => []);
    const getPermissionProfile = options.getPermissionProfile || (() => "accept");

    function renderDiff(text) {
      const lines = normalizeDiffText(text).split("\n");
      let lang = null;
      for (const line of lines) {
        const match = line.match(/^(---|\+\+\+) [ab]\/(.+)/);
        if (!match) continue;
        const extension = match[2].split(".").pop().toLowerCase();
        if (extension) lang = extension;
        break;
      }

      let oldLine = 0;
      let newLine = 0;
      const gutter = (value) => `<span class="diff-gutter">${value}</span>`;
      const number = (value) => `<span class="diff-num">${value}</span>`;
      const html = lines.map((line) => {
        if (line.startsWith("+++") || line.startsWith("---")) {
          return `<span class="diff-line diff-header">${gutter("")}${number("")}<span class="diff-code">${escapeHtml(line)}</span></span>`;
        }
        if (line.startsWith("@@")) {
          const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
          if (match) {
            oldLine = parseInt(match[1], 10) - 1;
            newLine = parseInt(match[2], 10) - 1;
          }
          return `<span class="diff-line diff-hunk">${gutter("")}${number("")}<span class="diff-code">${escapeHtml(line)}</span></span>`;
        }

        let lineNumber = "";
        let className;
        let marker;
        let content;
        if (line.startsWith("+")) {
          newLine += 1;
          lineNumber = newLine;
          className = "diff-add";
          marker = "+";
          content = line.slice(1);
        } else if (line.startsWith("-")) {
          oldLine += 1;
          lineNumber = oldLine;
          className = "diff-remove";
          marker = "-";
          content = line.slice(1);
        } else {
          oldLine += 1;
          newLine += 1;
          lineNumber = newLine;
          className = "diff-context";
          marker = " ";
          content = line.startsWith(" ") ? line.slice(1) : line;
        }
        const highlighted = lang ? highlightSyntax(content, lang) : escapeHtml(content);
        return `<span class="diff-line ${className}">${gutter(marker)}${number(lineNumber)}<span class="diff-code">${highlighted}</span></span>`;
      }).join("");

      const isLong = lines.length > 40;
      return `<div class="code-block diff-block${isLong ? " is-collapsed" : ""}"><div class="diff-lines">${html}</div>${isLong ? `<button class="diff-expand-btn" type="button" aria-expanded="false">展开全部 ${lines.length} 行</button>` : ""}</div>`;
    }

    function renderEditSuggestionProjection(msg, index) {
      const meta = msg.meta || {};
      const pendingId = meta.pendingEditId;
      const action = meta.action || meta.tool?.action || "propose_edit";
      const target = meta.path || meta.tool?.path || "";
      const content = getMessageText(msg).trim();
      if (!pendingId || !content) return "";

      const pendingEdits = getPendingEdits() || {};
      const authorizationRequests = getAuthorizationRequests() || [];
      const permissionProfile = getPermissionProfile();
      const editState = pendingEdits[pendingId] || {};
      const applied = !!(meta.applied || editState.applied);
      const rejected = !!(meta.rejected || editState.rejected || editState.resolved && !editState.applied);
      const serverExecuting = Boolean(meta.serverManaged && meta.authorizationDecision === "approved" && !applied && !rejected);
      const queued = authorizationRequests.some((item) => item.status === "pending" && item.editId === pendingId)
        || Boolean(meta.serverManaged && !serverExecuting && !applied && !rejected);
      const proposalOnly = permissionProfile === "plan" || !!meta.proposalOnly;
      const diffText = normalizeDiffText(content);
      if (/^\(no changes\)$/i.test(diffText.trim())) return "";
      const isDiff = /(^|\n)(--- |\+\+\+ |@@ )/.test(diffText);
      const body = isDiff ? renderDiff(diffText) : `<div class="tool-edit-markdown">${renderMarkdown(content)}</div>`;
      const stats = isDiff ? getDiffStats(diffText) : { additions: 0, removals: 0 };
      const canReject = permissionProfile !== "bypass";
      const status = applied ? t("appliedLabel") : (rejected ? t("rejectedLabel") : (proposalOnly ? t("proposalOnly") : (serverExecuting ? t("processingLabel") : (queued ? t("waitingApproval") : t("pendingConfirmation")))));
      const statusClass = applied ? "is-applied" : (rejected ? "is-rejected" : "is-review");

      let actions = "";
      if (!applied && !rejected && !queued && !proposalOnly && !meta.serverManaged) {
        actions = `
          <div class="apply-edit-bar">
            <button class="apply-edit-btn" type="button" data-edit-id="${escapeHtml(pendingId)}">${t("applyEdit")}</button>
            ${canReject ? `<button class="reject-edit-btn" type="button" data-edit-id="${escapeHtml(pendingId)}">${t("rejectEdit")}</button>` : ""}
          </div>
        `;
      }

      return `
        <article class="msg assistant edit-suggestion" data-msg-index="${index}" data-edit-id="${escapeHtml(pendingId)}">
          <div class="tool-edit-card">
            <div class="tool-edit-head">
              <div class="tool-edit-heading">
                ${target ? `<button class="tool-edit-target clickable-path" type="button" data-path="${escapeHtml(target)}" title="${t("openInPreview")}">${escapeHtml(target)}</button>` : `<span class="tool-edit-target">${t("unnamedFile")}</span>`}
                <span class="tool-edit-title">${action === "write_file" ? t("fileWriteProposal") : t("editProposal")}</span>
              </div>
              <div class="tool-edit-summary">
                ${isDiff ? `<span class="diff-stat diff-stat-add">+${stats.additions}</span><span class="diff-stat diff-stat-remove">−${stats.removals}</span>` : ""}
                ${isDiff ? renderCopyButton(diffText) : ""}
                <span class="tool-edit-status ${statusClass}">${escapeHtml(status)}</span>
              </div>
            </div>
            <div class="tool-edit-diff">${body}</div>
            ${actions}
          </div>
        </article>
      `;
    }

    return Object.freeze({
      getDiffStats,
      isEditSuggestionMessage,
      normalizeDiffText,
      renderDiff,
      renderEditSuggestionProjection,
    });
  }

  Code.ui.diff = Object.freeze({
    createDiffFeature,
    getDiffStats,
    isEditSuggestionMessage,
    normalizeDiffText,
  });
})(window);
