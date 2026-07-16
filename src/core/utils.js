(function initializeCodeUtils(global) {
  "use strict";

  const core = global.Code && global.Code.core;
  if (!core) throw new Error("Code core namespace must load before utils");

  function escapeHtml(text = "") {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatCompact(num) {
    const value = num || 0;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 1 : 2)}M`;
    if (value >= 1_000) return `${Math.round(value / 100) / 10}k`;
    return String(value);
  }

  function formatNumber(num) {
    return (num || 0).toLocaleString();
  }

  function formatElapsed(ms) {
    if (!ms || ms < 0) return "";
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
  }

  function estimateTokens(text = "") {
    return Math.ceil(String(text).length / 3.2);
  }

  core.utils = Object.freeze({
    escapeHtml,
    formatCompact,
    formatNumber,
    formatElapsed,
    estimateTokens,
  });
})(window);
