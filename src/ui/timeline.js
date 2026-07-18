(function registerTimelineUi(global) {
  "use strict";

  const Code = global.Code;
  if (!Code?.ui) throw new Error("Code namespace must load before timeline UI");

  function defaultMessageText(msg) {
    if (Array.isArray(msg?.content)) {
      return msg.content.find((item) => item?.type === "text")?.text || "";
    }
    return String(msg?.content || "");
  }

  function getCompactSummaryStats(msg, getMessageText = defaultMessageText) {
    const meta = msg?.meta || {};
    let compressed = Math.max(0, Number(meta.compressed) || 0);
    let estimatedSaved = Math.max(0, Number(meta.estimatedSaved) || 0);
    const text = getMessageText(msg) || "";
    if (!compressed) {
      const countMatch = text.match(/(?:压缩摘要|自动压缩)[^\d]*(\d+)\s*条/);
      if (countMatch) compressed = Number(countMatch[1]) || 0;
    }
    if (!estimatedSaved) {
      const savedMatch = text.match(/(?:节省|saved)[^\d~]*~?\s*([\d.]+)\s*([kKmM]?)/i);
      if (savedMatch) {
        const base = Number(savedMatch[1]) || 0;
        const unit = String(savedMatch[2] || "").toLowerCase();
        estimatedSaved = Math.round(base * (unit === "m" ? 1000000 : unit === "k" ? 1000 : 1));
      }
    }
    return { compressed, estimatedSaved };
  }

  function projectTimelineNodes(messages = [], getMessageText = defaultMessageText) {
    const nodes = [];
    for (let index = 0; index < messages.length; index += 1) {
      const msg = messages[index];
      if (!msg || msg.role !== "user" || msg.meta?._system) continue;
      const rawLabel = String(getMessageText(msg) || "").replace(/\n/g, " ").trim();
      const label = rawLabel.length > 80 ? `${rawLabel.slice(0, 80)}...` : rawLabel;
      nodes.push({ index, label, type: "user" });
    }
    return nodes;
  }

  function syncSessionBranchMetadata(sessions = [], session = {}) {
    const summary = sessions.find((item) => item?.id === session?.id);
    if (!summary) return null;
    for (const key of ["_parentId", "_branchDepth", "_branches", "_branchMsgCount"]) {
      if (Object.prototype.hasOwnProperty.call(session, key)) summary[key] = session[key];
    }
    return summary;
  }

  function createTimelineFeature(options = {}) {
    const escapeHtml = options.escapeHtml || ((value) => String(value ?? ""));
    const formatCompact = options.formatCompact || ((value) => String(value ?? 0));
    const t = options.t || ((key) => key);
    const getMessageText = options.getMessageText || defaultMessageText;
    const getMessages = options.getMessages || (() => []);
    const getSessions = options.getSessions || (() => []);
    const getSessionId = options.getSessionId || (() => "");
    const getTimelineElement = options.getTimelineElement || (() => null);
    const getMessageContainer = options.getMessageContainer || (() => null);

    function renderCompactSummaryProjection(msg, index) {
      const { compressed, estimatedSaved } = getCompactSummaryStats(msg, getMessageText);
      const details = [];
      if (compressed) details.push(t("compactMarkerMessages", { count: compressed }));
      if (estimatedSaved) details.push(t("compactMarkerSaved", { tokens: formatCompact(estimatedSaved) }));
      const label = details.length
        ? t("compactMarkerWithDetails", { details: details.join(" · ") })
        : t("compactMarker");
      return `<article class="msg branch-indicator compact-indicator" data-msg-index="${index}"><div class="branch-indicator-bar"><span class="branch-indicator-icon" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M7 12h10M9 17h6"/><path d="M3 3h18v18H3z"/></svg></span><span>${escapeHtml(label)}</span></div></article>`;
    }

    function getBranchFlowMarker() {
      const sessions = getSessions();
      const sessionId = getSessionId();
      const current = sessions.find((session) => session.id === sessionId);
      if (!current || current._branchMsgCount == null) return null;
      const rawCount = Number(current._branchMsgCount);
      if (!Number.isFinite(rawCount) || rawCount < 0) return null;
      const parent = sessions.find((session) => session.id === current._parentId)
        || sessions.find((session) => Array.isArray(session._branches) && session._branches.includes(sessionId));
      if (!parent) return null;
      return {
        messageCount: Math.max(0, Math.trunc(rawCount)),
        parentTitle: parent.title || "",
      };
    }

    function renderBranchFlowProjection(parentTitle) {
      const label = t("branchedFromHere", { title: parentTitle || "" });
      return `<article class="msg branch-indicator"><div class="branch-indicator-bar"><span class="branch-indicator-icon" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg></span><span>${escapeHtml(label)}</span></div></article>`;
    }

    function clearTimeline() {
      const timeline = getTimelineElement();
      if (!timeline) return;
      timeline.innerHTML = "";
      timeline.classList.remove("visible");
    }

    function renderTimeline() {
      const timeline = getTimelineElement();
      if (!timeline) return;
      const nodes = projectTimelineNodes(getMessages(), getMessageText);
      if (nodes.length < 2) {
        clearTimeline();
        return;
      }
      const dots = nodes.map((node) => (
        `<div class="tl-dot-wrap" data-index="${node.index}"><div class="tl-dot ${node.type}"></div><span class="tl-bubble">${escapeHtml(node.label)}</span></div>`
      )).join("");
      timeline.innerHTML = `<div class="tl-track">${dots}</div>`;
      timeline.classList.add("visible");
      timeline.querySelectorAll(".tl-dot-wrap").forEach((dot) => {
        dot.addEventListener("click", () => {
          const target = getMessageContainer()?.querySelector(`[data-msg-index="${dot.dataset.index}"]`);
          target?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      });
    }

    return Object.freeze({
      clearTimeline,
      getBranchFlowMarker,
      getCompactSummaryStats: (msg) => getCompactSummaryStats(msg, getMessageText),
      projectTimelineNodes: (messages) => projectTimelineNodes(messages, getMessageText),
      renderBranchFlowProjection,
      renderCompactSummaryProjection,
      renderTimeline,
    });
  }

  Code.ui.timeline = Object.freeze({
    createTimelineFeature,
    getCompactSummaryStats,
    projectTimelineNodes,
    syncSessionBranchMetadata,
  });
})(window);
