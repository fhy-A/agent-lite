(function registerPlatformCore(global) {
  "use strict";

  const Code = global.Code;
  if (!Code?.core) throw new Error("Code namespace must load before platform core");

  const WORKBAR_URL = "https://workbar.ai";
  const KEY_CONFIG_STORAGE_KEY = "code-key-config";

  function normalizeKeyEntry(entry, defaultSource = "manual") {
    if (!entry || typeof entry !== "object") return null;
    const key = String(entry.key || "").trim();
    if (!key) return null;
    return {
      name: String(entry.name || "").trim(),
      key,
      enabled: entry.enabled !== false,
      source: entry.source === "platform" ? "platform" : defaultSource,
    };
  }

  function normalizeKeyConfig(config, defaultSource = "manual") {
    const seen = new Set();
    const normalized = [];
    for (const item of Array.isArray(config) ? config : []) {
      const entry = normalizeKeyEntry(item, defaultSource);
      if (!entry || seen.has(entry.key)) continue;
      seen.add(entry.key);
      normalized.push(entry);
    }
    return normalized;
  }

  function loadKeyConfig(storage = global.localStorage) {
    try {
      const parsed = JSON.parse(storage?.getItem(KEY_CONFIG_STORAGE_KEY) || "[]");
      return normalizeKeyConfig(parsed);
    } catch {
      return [];
    }
  }

  function saveKeyConfig(config, storage = global.localStorage) {
    const normalized = normalizeKeyConfig(config);
    storage?.setItem(KEY_CONFIG_STORAGE_KEY, JSON.stringify(normalized));
    return normalized;
  }

  function splitKeyLine(value) {
    const line = String(value || "").trim();
    if (!line) return null;

    const colonIndex = line.indexOf(":");
    if (colonIndex > 0) {
      return {
        name: line.slice(0, colonIndex).trim(),
        key: line.slice(colonIndex + 1).trim(),
      };
    }

    const spaced = line.match(/^(.+?)\s+(sk-\S+)$/i);
    if (spaced) return { name: spaced[1].trim(), key: spaced[2].trim() };
    return { name: "", key: line };
  }

  function parseKeyText(raw, config = []) {
    const existingByKey = new Map(normalizeKeyConfig(config).map((entry) => [entry.key, entry]));
    const seen = new Set();
    const duplicates = [];
    const entries = [];
    for (const line of String(raw || "").split("\n")) {
      const parsed = splitKeyLine(line);
      if (!parsed?.key) continue;
      if (seen.has(parsed.key)) {
        duplicates.push(parsed.name || parsed.key);
        continue;
      }
      seen.add(parsed.key);
      const existing = existingByKey.get(parsed.key);
      entries.push({
        name: parsed.name || existing?.name || "",
        key: parsed.key,
        enabled: existing?.enabled !== false,
        source: existing?.source === "platform" ? "platform" : "manual",
      });
    }
    return { entries, duplicates };
  }

  function serializeKeyEntries(config) {
    return normalizeKeyConfig(config).map((entry) => (
      entry.name ? `${entry.name}: ${entry.key}` : entry.key
    )).join("\n");
  }

  Code.core.platform = Object.freeze({
    KEY_CONFIG_STORAGE_KEY,
    WORKBAR_URL,
    loadKeyConfig,
    normalizeKeyConfig,
    parseKeyText,
    saveKeyConfig,
    serializeKeyEntries,
    splitKeyLine,
  });
})(window);
