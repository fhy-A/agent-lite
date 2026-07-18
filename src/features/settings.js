(function registerSettingsFeature(global) {
  "use strict";

  const Code = global.Code;
  if (!Code?.features) throw new Error("Code namespace must load before settings feature");

  const UPDATE_NOTICE_STORAGE_KEYS = Object.freeze({
    settings: "code-update-seen-settings",
    page: "code-update-seen-page",
  });

  function loadKeyConfig(storage = global.localStorage) {
    try {
      return JSON.parse(storage?.getItem("code-key-config") || "[]");
    } catch {
      return [];
    }
  }

  function createSettingsFeature(options = {}) {
    const state = options.state || {};
    const els = options.elements || {};
    const t = options.t || ((key) => key);
    const escapeHtml = options.escapeHtml || ((value) => String(value ?? ""));
    const apiJson = options.apiJson;
    const showToast = options.showToast || (() => {});
    const applyI18n = options.applyI18n || (() => {});
    const setLang = options.setLang || (() => {});
    const refreshModels = options.refreshModels || (async () => {});
    const saveLocalSettings = options.saveLocalSettings || (() => {});
    const saveSystemPrompt = options.saveSystemPrompt || (() => {});
    const renderMemoryPanel = options.renderMemoryPanel || (() => {});
    const renderSkillsInSettings = options.renderSkillsInSettings || (() => {});
    const getDefaultSystemPrompt = options.getDefaultSystemPrompt || (() => "");
    const trashIcon = options.trashIcon || (() => "");
    const documentRef = options.document || global.document;
    const storage = options.storage || global.localStorage;
    const fetchFn = options.fetch || global.fetch?.bind(global);
    const navigatorRef = options.navigator || global.navigator;

    if (typeof apiJson !== "function") throw new Error("settings feature requires apiJson");

    const byId = (id) => documentRef.getElementById(id);
    let bound = false;

    function saveKeyConfig(config) {
      storage?.setItem("code-key-config", JSON.stringify(config));
    }

    function parseKeyLines(raw) {
      if (!raw) return [];
      const config = loadKeyConfig(storage);
      const lines = raw.split("\n").map((line) => line.trim()).filter(Boolean);
      if (!lines.length) return [{ name: "", key: "", enabled: true }];
      const seen = new Set();
      const duplicates = [];
      const result = [];
      lines.forEach((line) => {
        let index = line.indexOf(":");
        if (index === -1) index = line.indexOf(" ");
        const name = index > 0 ? line.slice(0, index).trim() : "";
        const key = index > 0 ? line.slice(index + 1).trim() : line.trim();
        if (seen.has(key)) {
          duplicates.push(name || key);
          return;
        }
        seen.add(key);
        const existing = config.find((item) => item.key === key);
        result.push({ name, key, enabled: existing ? existing.enabled !== false : true });
      });
      if (duplicates.length) showToast(t("ignoredDuplicateKeys", { count: duplicates.length }), "warning");
      return result.length ? result : [{ name: "", key: "", enabled: true }];
    }

    function serializeKeys(entries) {
      return entries.map((entry) => {
        const key = (entry.key || "").trim();
        const name = (entry.name || "").trim();
        return name ? `${name}: ${key}` : key;
      }).filter(Boolean).join("\n");
    }

    function eyeIcon() {
      return '<svg width="14" height="14" viewBox="0 0 1024 1024" fill="currentColor"><path d="M942.2 486.2C847.4 286.5 704.1 186 512 186c-192.2 0-335.4 100.5-430.2 300.3-7.7 16.2-7.7 35.2 0 51.5C176.6 737.5 319.9 838 512 838c192.2 0 335.4-100.5 430.2-300.3 7.7-16.2 7.7-35 0-51.5zM512 766c-161.3 0-279.4-81.8-362.7-254C232.6 339.8 350.7 258 512 258c161.3 0 279.4 81.8 362.7 254C791.5 684.2 673.4 766 512 766z"/><path d="M508 336c-97.2 0-176 78.8-176 176s78.8 176 176 176 176-78.8 176-176-78.8-176-176-176zm0 288c-61.9 0-112-50.1-112-112s50.1-112 112-112 112 50.1 112 112-50.1 112-112 112z"/></svg>';
    }

    function eyeOffIcon() {
      return '<svg width="14" height="14" viewBox="0 0 1024 1024" fill="currentColor"><path d="M913.86 396.86c11.76-14.71 9.36-36.18-5.33-47.94-14.72-11.77-36.14-9.34-47.97 5.33-1.23 1.57-128.74 157.74-348.56 157.74-218.58 0-347.36-156.22-348.56-157.74-11.79-14.67-33.21-17.12-47.97-5.33-14.69 11.76-17.09 33.23-5.33 47.94 2.11 2.64 21.66 26.32 56.68 55.72l-59.81 72.89 52.73 43.27 61.98-75.53c25.71 16.71 55.66 33.14 89.71 47.2l-34.34 95.02 64.16 23.18 34.82-96.36c31.36 8.41 65.38 14.16 101.82 16.5v103.8h68.22V578.72c37.15-2.39 71.75-8.36 103.61-17.04l35.19 96.27 64.06-23.44-34.65-94.79c32.3-13.47 60.72-29.1 85.46-45l61.61 76.04 53-42.95-59.44-73.37c36.44-30.26 56.71-54.82 58.87-57.58z"/></svg>';
    }

    function keyNormalActions(entry, index) {
      return `<div class="key-actions">
        <button class="key-act-btn key-eye" type="button" title="${t("toggleVisibility")}" data-idx="${index}">${eyeIcon()}</button>
        <label class="toggle-switch key-enable" title="${entry.enabled !== false ? t("enabledStatus") : t("disabledStatus")}">
          <input type="checkbox" ${entry.enabled !== false ? "checked" : ""} data-idx="${index}" />
          <span class="toggle-track"><span class="toggle-thumb"></span></span>
        </label>
        <button class="key-act-btn key-trash" type="button" title="${t("delete")}" data-idx="${index}">${trashIcon()}</button>
      </div>`;
    }

    function keyConfirmActions(index) {
      return `<div class="key-actions">
        <button class="key-act-btn key-confirm" type="button" title="${t("save")}" data-idx="${index}"><svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 7l2.5 2.5L11 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        <button class="key-act-btn key-cancel" type="button" title="${t("cancel")}" data-idx="${index}"><svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 3l8 8M11 3L3 11" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg></button>
      </div>`;
    }

    function renderKeyEditor(raw, newRow = false) {
      const entries = parseKeyLines(raw);
      if (!entries.length) entries.push({ name: "", key: "", enabled: true });
      return entries.map((entry, index) => {
        const isNew = newRow && index === entries.length - 1;
        return `<div class="key-row ${entry.enabled === false && !isNew ? "disabled" : ""}" data-idx="${index}">
          <span class="key-drag-handle" title="${t("dragSort")}" draggable="true">⠿</span>
          <input class="key-name-input" placeholder="${t("keyNamePlaceholder")}" value="${escapeHtml(entry.name)}" data-idx="${index}" />
          <div class="key-value-wrap"><input class="key-value-input" type="password" value="${escapeHtml(entry.key)}" data-idx="${index}" /></div>
          ${isNew ? keyConfirmActions(index) : keyNormalActions(entry, index)}
        </div>`;
      }).join("");
    }

    function collectKeyEntries(container) {
      const entries = [];
      container?.querySelectorAll(".key-row").forEach((row) => {
        const name = row.querySelector(".key-name-input")?.value || "";
        const key = row.querySelector(".key-value-input")?.value || "";
        const enabled = row.querySelector(".key-enable input")?.checked !== false;
        if (key.trim()) entries.push({ name: name.trim(), key: key.trim(), enabled });
      });
      return entries;
    }

    function persistKeyEntries(container, saveSettings = true) {
      const entries = collectKeyEntries(container);
      els.apiKey.value = serializeKeys(entries);
      saveKeyConfig(entries);
      if (saveSettings) saveLocalSettings();
      return entries;
    }

    function showInlineKeyDeleteConfirm(row, name, onConfirm) {
      documentRef.querySelector(".key-delete-confirm")?.remove();
      const confirm = documentRef.createElement("div");
      confirm.className = "key-delete-confirm";
      confirm.innerHTML = `<span>删除「${escapeHtml(name.slice(0, 20))}」？</span>
        <button class="key-confirm-yes" type="button">${t("confirmDelete")}</button>
        <button class="key-confirm-no" type="button">${t("cancel")}</button>`;
      row.after(confirm);
      confirm.querySelector(".key-confirm-yes").addEventListener("click", () => {
        confirm.remove();
        onConfirm();
      });
      confirm.querySelector(".key-confirm-no").addEventListener("click", () => confirm.remove());
    }

    function bindKeyEditorEvents(container) {
      if (!container) return;
      let dragSource = null;
      container.querySelectorAll(".key-drag-handle").forEach((handle) => {
        handle.addEventListener("dragstart", (event) => {
          dragSource = handle.closest(".key-row");
          dragSource.classList.add("dragging");
          event.dataTransfer.effectAllowed = "move";
        });
        handle.addEventListener("dragend", () => {
          dragSource?.classList.remove("dragging");
          dragSource = null;
          container.querySelectorAll(".key-row").forEach((row) => row.classList.remove("drag-over"));
        });
      });
      container.querySelectorAll(".key-row").forEach((row) => {
        row.addEventListener("dragover", (event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
          row.classList.add("drag-over");
        });
        row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
        row.addEventListener("drop", (event) => {
          event.preventDefault();
          row.classList.remove("drag-over");
          if (!dragSource || dragSource === row) return;
          const rows = [...container.querySelectorAll(".key-row")];
          if (rows.indexOf(dragSource) < rows.indexOf(row)) row.after(dragSource);
          else row.before(dragSource);
          dragSource.classList.remove("dragging");
          dragSource = null;
          persistKeyEntries(container);
        });
      });
      container.querySelectorAll(".key-name-input, .key-value-input").forEach((input) => {
        input.addEventListener("change", () => persistKeyEntries(container));
      });
      container.querySelectorAll(".key-eye").forEach((button) => {
        button.addEventListener("click", () => {
          const input = button.closest(".key-row").querySelector(".key-value-input");
          const showing = input.type === "text";
          input.type = showing ? "password" : "text";
          button.innerHTML = showing ? eyeIcon() : eyeOffIcon();
        });
      });
      container.querySelectorAll(".key-enable input").forEach((checkbox) => {
        checkbox.addEventListener("change", () => persistKeyEntries(container));
      });
      container.querySelectorAll(".key-confirm").forEach((button) => {
        button.addEventListener("click", () => {
          persistKeyEntries(container);
          container.innerHTML = renderKeyEditor(els.apiKey.value);
          bindKeyEditorEvents(container);
        });
      });
      container.querySelectorAll(".key-cancel").forEach((button) => {
        button.addEventListener("click", () => {
          button.closest(".key-row").remove();
          persistKeyEntries(container, false);
        });
      });
      container.querySelectorAll(".key-trash").forEach((button) => {
        button.addEventListener("click", () => {
          const row = button.closest(".key-row");
          const name = row.querySelector(".key-name-input")?.value || "未命名";
          showInlineKeyDeleteConfirm(row, name, () => {
            row.remove();
            persistKeyEntries(container);
          });
        });
      });

      const detail = byId("settingsDetail");
      if (!detail || detail._keyDelegationBound) return;
      detail._keyDelegationBound = true;
      detail.addEventListener("click", (event) => {
        if (event.target.id !== "settingsKeyAddRow" && !event.target.closest("#settingsKeyAddRow")) return;
        const area = byId("settingsKeyAddArea");
        area.innerHTML = `<textarea id="keyBulkInput" class="key-bulk-input" placeholder="${t("keyBulkPlaceholder")}" rows="5"></textarea>
          <div class="key-bulk-actions"><button id="keyBulkSave" class="mini-btn" type="button">${t("save")}</button><button id="keyBulkCancel" class="mini-btn" type="button">${t("cancel")}</button></div>`;
        const bulkInput = byId("keyBulkInput");
        const bulkSave = byId("keyBulkSave");
        bulkInput.addEventListener("input", () => bulkSave.classList.toggle("primary-btn", bulkInput.value.trim().length > 0));
        byId("keyBulkCancel").addEventListener("click", () => {
          area.innerHTML = `<button id="settingsKeyAddRow" class="key-add-btn" type="button">${t("addKey")}</button>`;
        });
        bulkSave.addEventListener("click", () => {
          const lines = bulkInput.value.split("\n").map((line) => line.trim()).filter(Boolean);
          if (!lines.length) return;
          const additions = lines.map((line) => {
            const space = line.indexOf(" ");
            return space > 0
              ? { name: line.slice(0, space).trim(), key: line.slice(space + 1).trim(), enabled: true }
              : { name: "", key: line, enabled: true };
          });
          const keyList = byId("settingsKeyList");
          const merged = [...collectKeyEntries(keyList), ...additions];
          els.apiKey.value = serializeKeys(merged);
          saveKeyConfig(merged);
          saveLocalSettings();
          keyList.innerHTML = renderKeyEditor(els.apiKey.value);
          bindKeyEditorEvents(keyList);
          area.innerHTML = `<button id="settingsKeyAddRow" class="key-add-btn" type="button">${t("addKey")}</button>`;
        });
      });
    }

    function getPlatformUrl() {
      return storage?.getItem("code-platform-url") || "http://localhost:3001";
    }

    function getPlatformAuth() {
      try {
        return JSON.parse(storage?.getItem("code-platform-auth") || "null");
      } catch {
        return null;
      }
    }

    function savePlatformAuth(data) {
      storage?.setItem("code-platform-auth", JSON.stringify(data));
    }

    function clearPlatformAuth() {
      storage?.removeItem("code-platform-auth");
    }

    function applyTheme(mode) {
      const systemDark = global.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
      const isDark = mode === "dark" || (mode === "system" && systemDark);
      documentRef.body.classList.toggle("theme-dark", Boolean(isDark));
      storage?.setItem("code-theme", mode);
      updateThemeButtons();
    }

    function updateThemeButtons() {
      const current = storage?.getItem("code-theme") || "light";
      documentRef.querySelectorAll(".theme-opt").forEach((button) => {
        button.classList.toggle("active", button.dataset.theme === current);
      });
    }

    function showSettings(open = true) {
      els.settingsModal?.classList.toggle("hidden", !open);
    }

    function closeDropdown() {
      byId("settingsDropdown")?.classList.add("hidden");
    }

    function renderModelsPanel(container) {
      container.innerHTML = `<h3 style="margin:0 0 14px">${t("models")}</h3>
        <label class="field"><span>${t("baseUrl")}</span><input id="settingsBaseUrl" value="${escapeHtml(els.baseUrl.value)}" placeholder="https://your-api-host.com" autocomplete="off" /></label>
        <label class="field"><span>${t("apiKeys")}</span>
          <div class="key-list" id="settingsKeyList">${renderKeyEditor(els.apiKey.value)}</div>
          <div id="settingsKeyAddArea"><button id="settingsKeyAddRow" class="key-add-btn" type="button">${t("addKey")}</button></div>
          <button id="settingsConnectPlatform" class="key-connect-btn" type="button">${t("syncGatewayKeys")}</button>
        </label>
        <div class="model-list-header"><span>${t("availableModels")} <button id="settingsRefreshModels" class="icon-refresh-btn" type="button" title="${t("refreshModels")}"><svg width="14" height="14" viewBox="0 0 14 14"><path d="M1 7a6 6 0 0111.1-3.5M13 7a6 6 0 01-11.1 3.5" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round"/><path d="M12 1v3H9M2 13v-3h3" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></button></span></div>
        <div id="settingsModelList" class="model-list-display">${els.modelListBox.innerHTML}</div>
        <div class="grid-two">
          <label class="field"><span>${t("temperature")}</span><input id="settingsTemperature" type="number" min="0" max="2" step="0.1" value="${els.temperature.value}" /></label>
          <label class="field"><span>${t("maxTokens")}</span><select id="settingsMaxTokens">${els.maxTokens.innerHTML}</select></label>
        </div>`;

      byId("settingsConnectPlatform")?.addEventListener("click", () => {
        if (!getPlatformAuth()) {
          showToast(t("loginFirst"), "warning");
          return;
        }
        syncKeysFromPlatform();
      });
      byId("settingsBaseUrl")?.addEventListener("change", (event) => {
        els.baseUrl.value = event.currentTarget.value;
        saveLocalSettings();
      });
      byId("settingsRefreshModels")?.addEventListener("click", () => {
        els.refreshModelsBtn?.click();
        global.setTimeout(() => {
          const list = byId("settingsModelList");
          if (list) list.innerHTML = els.modelListBox.innerHTML;
        }, 2000);
      });
      byId("settingsTemperature")?.addEventListener("change", (event) => {
        els.temperature.value = event.currentTarget.value;
        saveLocalSettings();
      });
      byId("settingsMaxTokens")?.addEventListener("change", (event) => {
        els.maxTokens.value = event.currentTarget.value;
        saveLocalSettings();
      });

      const keyList = byId("settingsKeyList");
      bindKeyEditorEvents(keyList);
      const keyToggle = byId("settingsKeyToggle");
      let keyVisible = false;
      keyToggle?.addEventListener("click", () => {
        keyVisible = !keyVisible;
        keyList.querySelectorAll(".key-value-input").forEach((input) => { input.type = keyVisible ? "text" : "password"; });
        keyToggle.textContent = keyVisible ? t("hide") : t("show");
      });
      keyList?.addEventListener("dblclick", () => {
        keyVisible = true;
        keyList.querySelectorAll(".key-value-input").forEach((input) => { input.type = "text"; });
        if (keyToggle) keyToggle.textContent = t("hide");
      });
    }

    function renderSystemPanel(container) {
      container.innerHTML = `<h3 style="margin:0 0 14px">${t("system")}</h3>
        <textarea id="settingsSystemText" class="system-prompt-text" style="height:400px" spellcheck="false">${escapeHtml(els.systemPromptText.value)}</textarea>
        <div class="panel-actions" style="margin-top:8px"><span>${t("systemPromptHint")}</span><button id="settingsResetSystem" class="mini-btn" type="button">${t("resetDefault")}</button></div>`;
      byId("settingsSystemText").addEventListener("change", (event) => {
        els.systemPromptText.value = event.currentTarget.value;
        saveSystemPrompt();
      });
      byId("settingsResetSystem").addEventListener("click", () => {
        const value = getDefaultSystemPrompt();
        els.systemPromptText.value = value;
        byId("settingsSystemText").value = value;
        saveSystemPrompt();
      });
    }

    function renderLanguagePanel(container) {
      const current = state.lang || "zh";
      container.innerHTML = `<h3 style="margin:0 0 14px">${t("language")}</h3>
        <div class="lang-options"><button class="lang-opt ${current === "zh" ? "active" : ""}" data-lang="zh">中文</button><button class="lang-opt ${current === "en" ? "active" : ""}" data-lang="en">English</button></div>`;
      container.querySelectorAll(".lang-opt").forEach((button) => {
        button.addEventListener("click", () => {
          setLang(button.dataset.lang);
          renderLanguagePanel(container);
        });
      });
    }

    function renderThemePanel(container) {
      const current = storage?.getItem("code-theme") || "light";
      const themes = [
        { value: "light", label: t("light") },
        { value: "dark", label: t("dark") },
        { value: "system", label: t("followSystem") },
      ];
      container.innerHTML = `<h3 style="margin:0 0 14px">${t("theme")}</h3>
        <div class="settings-theme-row" style="max-width:240px">${themes.map((theme) => `<button class="theme-opt settings-theme-btn ${theme.value === current ? "active" : ""}" data-theme="${theme.value}">${theme.label}</button>`).join("")}</div>`;
      container.querySelectorAll(".settings-theme-btn").forEach((button) => {
        button.addEventListener("click", () => {
          applyTheme(button.dataset.theme);
          renderThemePanel(container);
        });
      });
    }

    function renderAccountPanel(container) {
      const auth = getPlatformAuth();
      if (auth) {
        container.innerHTML = `<h3 style="margin:0 0 14px">${t("platformAccount")}</h3>
          <div class="account-card"><div class="account-avatar">${escapeHtml((auth.username || "U")[0].toUpperCase())}</div><div class="account-info"><div class="account-name">${escapeHtml(auth.username || "Unknown")}</div><div class="account-id">${t("accountUserId")}: ${escapeHtml(auth.userId || "")}</div></div></div>
          <div class="field" style="margin-top:12px"><label>${t("platformUrl")}</label><input id="settingsPlatformUrl" class="field-input" type="text" placeholder="http://localhost:3001" value="${escapeHtml(getPlatformUrl())}" /></div>
          <div style="margin-top:12px"><button id="accountLogout" class="mini-btn" type="button">${t("logout")}</button></div>`;
        byId("settingsPlatformUrl").addEventListener("change", (event) => storage?.setItem("code-platform-url", event.currentTarget.value.trim()));
        byId("accountLogout").addEventListener("click", () => {
          clearPlatformAuth();
          showToast(t("loggedOut"), "warning");
          renderAccountPanel(container);
        });
        return;
      }
      container.innerHTML = `<h3 style="margin:0 0 14px">${t("platformAccount")}</h3>
        <div class="muted-line" style="padding:16px;text-align:center"><p>${t("notLoggedIn")}</p>
          <div class="field" style="margin-bottom:8px"><label>${t("platformUrl")}</label><input id="settingsPlatformUrl" class="field-input" type="text" placeholder="http://localhost:3001" value="${escapeHtml(getPlatformUrl())}" /></div>
          <button id="accountLoginNow" class="mini-btn primary" type="button" style="margin-top:8px">${t("loginPlatform")}</button>
        </div>`;
      byId("settingsPlatformUrl").addEventListener("change", (event) => storage?.setItem("code-platform-url", event.currentTarget.value.trim()));
      byId("accountLoginNow").addEventListener("click", () => {
        global.open(`${getPlatformUrl()}/code/connect?callback=${encodeURIComponent("http://127.0.0.1:3010/")}`, "_blank");
      });
    }

    function isUpdateNoticeUnread(target, version) {
      return Boolean(version) && storage?.getItem(UPDATE_NOTICE_STORAGE_KEYS[target]) !== version;
    }

    function markUpdateNoticeSeen(target) {
      const version = state.updateInfo?.updateAvailable ? state.updateInfo.remoteVersion : "";
      const key = UPDATE_NOTICE_STORAGE_KEYS[target];
      if (!version || !key) return;
      storage?.setItem(key, version);
      byId(target === "settings" ? "settingsUpdateDot" : "settingsPageUpdateDot")?.classList.add("hidden");
    }

    function setUpdateNotice(data) {
      state.updateInfo = data || null;
      const remoteVersion = data?.remoteVersion || "";
      const available = Boolean(data?.updateAvailable && remoteVersion);
      byId("settingsUpdateDot")?.classList.toggle("hidden", !available || !isUpdateNoticeUnread("settings", remoteVersion));
      byId("settingsPageUpdateDot")?.classList.toggle("hidden", !available || !isUpdateNoticeUnread("page", remoteVersion));
      const badge = byId("settingsPageUpdateVersion");
      if (badge) {
        badge.textContent = available ? `v${remoteVersion}` : "";
        badge.classList.toggle("hidden", !available);
        badge.title = available ? `${t("updateAvailable")} (v${remoteVersion})` : "";
      }
      const button = byId("settingsMenuBtn");
      if (button) {
        button.classList.toggle("has-update", available);
        button.title = available ? `${t("updateAvailable")} (v${remoteVersion})` : t("settingsBtn");
      }
    }

    async function checkForUpdates({ silent = true } = {}) {
      if (state._updateCheckPromise) return state._updateCheckPromise;
      state._updateCheckPromise = (async () => {
        try {
          const data = await apiJson("/api/check-update");
          setUpdateNotice(data);
          return data;
        } catch (error) {
          if (!silent) throw error;
          return null;
        } finally {
          state._updateCheckPromise = null;
        }
      })();
      return state._updateCheckPromise;
    }

    function renderUpdatePanel(container) {
      const currentVersion = state.appVersion || "unknown";
      let remoteVersion = null;
      let downloadUrl = null;
      const status = (value) => { const element = byId("updateStatus"); if (element) element.textContent = value; };
      const actions = (html) => { const element = byId("updateActions"); if (element) element.innerHTML = html; };
      container.innerHTML = `<h3 style="margin:0 0 14px">${t("update")}</h3>
        <div class="update-ver-row"><span>${t("versionLabel")}:</span><strong class="update-ver-val" id="updateCurVer">v${escapeHtml(currentVersion)}</strong></div>
        <div class="update-status-row"><span id="updateStatus"></span></div>
        <div class="update-progress-wrap hidden" id="updateProgressWrap"><div class="update-progress-bg"><div class="update-progress-fill" id="updateBar"></div></div><span class="update-progress-txt" id="updatePct">0%</span></div>
        <div class="panel-actions" style="margin-top:12px" id="updateActions"><button id="updateCheckBtn" class="mini-btn primary-btn" type="button">${t("checkUpdate")}</button></div>`;
      apiJson("/api/version").then((version) => {
        const element = byId("updateCurVer");
        if (version?.localVersion && element) element.textContent = `v${version.localVersion}`;
      }).catch(() => {});
      byId("updateCheckBtn").addEventListener("click", async () => {
        status(t("checkingUpdate"));
        actions("");
        try {
          const data = await checkForUpdates({ silent: false });
          if (data.updateAvailable) {
            remoteVersion = data.remoteVersion;
            downloadUrl = data.downloadUrl;
            status(`${t("updateAvailable")} (v${remoteVersion})`);
            if (data.isFrozen && downloadUrl) {
              actions(`<button id="updateDlBtn" class="mini-btn primary-btn" type="button">${t("downloadUpdate")} v${remoteVersion}</button>`);
              byId("updateDlBtn").addEventListener("click", startDownload);
            } else {
              actions(`<a href="https://github.com/fhy-A/Code/releases/latest" target="_blank" class="mini-btn">${t("openDownloadPage")}</a>`);
            }
          } else {
            status(t("upToDate"));
            actions(`<button id="updateCheckBtn2" class="mini-btn primary-btn" type="button">${t("checkUpdate")}</button>`);
            byId("updateCheckBtn2").addEventListener("click", () => renderUpdatePanel(container));
          }
        } catch (error) {
          status(`${t("updateFailed")}: ${error.message || ""}`);
          actions(`<button id="updateCheckBtn3" class="mini-btn primary-btn" type="button">${t("checkUpdate")}</button>`);
          byId("updateCheckBtn3").addEventListener("click", () => renderUpdatePanel(container));
        }
      });

      async function startDownload() {
        status(t("downloading"));
        byId("updateProgressWrap").classList.remove("hidden");
        actions("");
        let downloadId;
        let newExePath;
        try {
          const result = await apiJson("/api/download-update", { method: "POST", body: JSON.stringify({ url: downloadUrl }) });
          downloadId = result.downloadId;
          newExePath = result.path;
        } catch (error) {
          status(`${t("updateFailed")}: ${error.message}`);
          return;
        }
        const poll = global.setInterval(async () => {
          try {
            const progress = await apiJson(`/api/download-progress?id=${encodeURIComponent(downloadId)}`);
            byId("updateBar").style.width = `${progress.progress}%`;
            byId("updatePct").textContent = `${progress.progress}%`;
            if (progress.error) {
              global.clearInterval(poll);
              status(`${t("updateFailed")}: ${progress.error}`);
            }
            if (!progress.done) return;
            global.clearInterval(poll);
            byId("updateProgressWrap").classList.add("hidden");
            status(t("readyToInstall"));
            actions(`<button id="updateRestartBtn" class="mini-btn primary-btn" type="button">${t("installRestart")}</button>`);
            byId("updateRestartBtn").addEventListener("click", async () => {
              status(t("restarting"));
              actions("");
              try { await apiJson("/api/restart", { method: "POST", body: JSON.stringify({ path: newExePath }) }); } catch {}
              showToast("Code is restarting...", "success");
              global.setTimeout(() => {
                const check = global.setInterval(() => {
                  fetchFn(`/api/version?_=${Date.now()}`, { cache: "no-store" })
                    .then((response) => response.json())
                    .then((versionInfo) => {
                      if (versionInfo.localVersion !== remoteVersion) return;
                      global.clearInterval(check);
                      const refreshed = new global.URL(global.location.href);
                      refreshed.searchParams.set("updated", `${remoteVersion}-${Date.now()}`);
                      global.location.replace(refreshed.toString());
                    })
                    .catch(() => {});
                }, 800);
              }, 3000);
            });
          } catch { /* server may have restarted */ }
        }, 500);
      }
    }

    async function syncKeysFromPlatform() {
      const auth = getPlatformAuth();
      if (!auth) {
        showToast(t("loginFirst"));
        return;
      }
      const button = byId("settingsConnectPlatform");
      if (button) {
        button.disabled = true;
        button.textContent = t("syncing");
      }
      try {
        const response = await fetchFn("/api/code/sync-keys", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: auth.token, userId: auth.userId, platformUrl: getPlatformUrl() }),
        });
        if (!response.ok) throw new Error(`Sync failed (${response.status})`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        const tokens = data.tokens || [];
        if (!tokens.length) {
          showToast(t("noPlatformKeys"));
          return;
        }
        showKeySyncModal(tokens, data.keys || {});
      } catch (error) {
        const message = error.message || String(error);
        if (message.includes("401") || message.includes("Unauthorized") || message.includes("502")) {
          clearPlatformAuth();
          showToast(t("loginExpired"), "error");
          global.setTimeout(() => {
            global.open(`${getPlatformUrl()}/code/connect?callback=${encodeURIComponent("http://127.0.0.1:3010/")}`, "_blank");
          }, 1000);
        } else {
          showToast(t("syncFailed", { message }), "error");
        }
      } finally {
        if (button) {
          button.disabled = false;
          button.textContent = t("syncGatewayKeys");
        }
      }
    }

    function showKeySyncModal(tokens, fullKeys) {
      byId("keySyncOverlay")?.remove();
      const existingKeys = new Set(parseKeyLines(els.apiKey.value).map((entry) => entry.key.trim()).filter(Boolean));
      let allText = "";
      let newCount = 0;
      const rows = tokens.map((tokenEntry) => {
        const key = fullKeys[String(tokenEntry.id)] || tokenEntry.key || "";
        const exists = existingKeys.has(key);
        if (!exists) {
          allText += `${tokenEntry.name || t("unnamed")} ${key}\n`;
          newCount += 1;
        }
        const copyButton = `<button class="mini-btn key-copy-one" data-line="${escapeHtml(`${tokenEntry.name || t("unnamed")} ${key}`)}" type="button">${t("copy")}</button>`;
        return `<div class="key-sync-row${exists ? " key-sync-exists" : ""}"><span class="key-sync-name">${escapeHtml(tokenEntry.name || t("unnamed"))}</span><span class="key-sync-key">${escapeHtml(`${key.slice(0, 12)}…${key.slice(-4)}`)}</span>${exists ? `<span class="key-sync-badge">${t("alreadyAdded")}</span>` : copyButton}</div>`;
      }).join("");
      const overlay = documentRef.createElement("div");
      overlay.id = "keySyncOverlay";
      overlay.className = "modal-overlay";
      overlay.innerHTML = `<div class="modal-card" style="width:540px;max-height:70vh;display:flex;flex-direction:column">
        <header><h3>${t("syncKeysTitle")}</h3><button class="icon-btn key-sync-close" type="button">&times;</button></header>
        <div class="key-sync-summary"><span>${t("keyCount", { count: tokens.length })}${newCount > 0 && newCount < tokens.length ? `，${t("newKeyCount", { count: newCount })}` : ""}</span>${newCount > 0 ? `<button id="keySyncCopyAll" class="mini-btn primary" type="button">${t("copyAll")}</button>` : ""}</div>
        <div class="key-sync-list">${rows}</div>
        <div class="panel-actions" style="margin-top:12px">${tokens.length > 0 && newCount === 0 ? `<span style="font-size:12px;color:var(--muted)">${t("allKeysAdded")}</span>` : `<span style="font-size:12px;color:var(--muted)">${t("pasteKeysHint")}</span>`}</div>
      </div>`;
      documentRef.body.appendChild(overlay);
      overlay.querySelector(".key-sync-close").addEventListener("click", () => overlay.remove());
      overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
      const copyAllButton = overlay.querySelector("#keySyncCopyAll");
      copyAllButton?.addEventListener("click", () => {
        navigatorRef.clipboard.writeText(allText.trim()).then(() => {
          copyAllButton.textContent = t("copied");
          global.setTimeout(() => { copyAllButton.textContent = t("copyAll"); }, 1500);
        }).catch(() => showToast(t("copyFailed")));
      });
      overlay.querySelectorAll(".key-copy-one").forEach((button) => {
        button.addEventListener("click", () => {
          navigatorRef.clipboard.writeText(button.dataset.line).then(() => {
            button.textContent = t("copied");
            global.setTimeout(() => { button.textContent = t("copy"); }, 1500);
          }).catch(() => showToast(t("copyFailed")));
        });
      });
    }

    async function checkCodeCallback() {
      const params = new global.URLSearchParams(global.location.search);
      const token = params.get("code_token");
      const userId = params.get("user_id");
      const username = params.get("username");
      if (!token || !userId) return false;
      global.history.replaceState(null, "", "/");
      const decodedUsername = decodeURIComponent(username || "");
      savePlatformAuth({ token, userId, username: decodedUsername });
      showToast(t("loggedInAs", { name: decodedUsername }), "warning");
      const detail = byId("settingsDetail");
      if (detail?.children.length) renderModelsPanel(detail);
      return true;
    }

    function shouldShowOnboarding() {
      return !storage?.getItem("code-onboarding");
    }

    function markOnboardingDone() {
      storage?.setItem("code-onboarding", "1");
    }

    function showOnboarding() {
      const overlay = byId("onboardingOverlay");
      if (!overlay) return;
      overlay.classList.remove("hidden");
      let step = 0;
      const steps = [
        { title: t("oboWelcome"), desc: t("oboWelcomeDesc"), features: [String.fromCodePoint(0x1F4D6) + " " + t("oboFeat1"), String.fromCodePoint(0x1F527) + " " + t("oboFeat2"), String.fromCodePoint(0x1F4BB) + " " + t("oboFeat3"), String.fromCodePoint(0x1F512) + " " + t("oboFeat4")] },
        { title: `1/4 ${t("oboStep1")}`, desc: t("oboStep1Desc"), items: [t("oboStep1Item1"), t("oboStep1Item2"), t("oboStep1Item3")], tip: t("oboStep1Tip") },
        { title: `2/4 ${t("oboStep2")}`, desc: t("oboStep2Desc"), items: [t("oboStep2Item1"), t("oboStep2Item2")], tip: t("oboStep2Tip") },
        { title: `3/4 ${t("oboStep3")}`, desc: t("oboStep3Desc"), example: `"${t("oboStep3Example")}"` },
        { title: `4/4 ${t("oboStep4")}`, desc: t("oboStep4Desc"), table: [[String.fromCodePoint(0x1F6E1) + " Plan", t("oboStep4Item1")], [String.fromCodePoint(0x270B) + " Accept Edits", t("oboStep4Item2")], [String.fromCodePoint(0x26A1) + " Auto", t("oboStep4Item3")]], tip: t("oboStep4Tip") },
      ];

      function close() {
        overlay.classList.add("hidden");
        markOnboardingDone();
      }

      function render() {
        const data = steps[step];
        byId("onboardingDots").innerHTML = steps.map((_, index) => `<span class="onboarding-dot${index === step ? " active" : ""}"></span>`).join("");
        let html = data.title ? `<h2>${data.title}</h2>` : "";
        if (data.desc) html += `<p class="obo-desc">${data.desc}</p>`;
        if (data.features) html += `<div class="obo-features">${data.features.map((feature) => `<div class="obo-feat-item">${feature}</div>`).join("")}</div>`;
        if (data.items) html += `<ol>${data.items.map((item) => `<li>${item}</li>`).join("")}</ol>`;
        if (data.example) html += `<p style="background:var(--panel-2);border-radius:8px;padding:12px 16px;font-style:italic;color:var(--accent)">${data.example}</p>`;
        if (data.tip) html += `<div class="obo-tip">${data.tip}</div>`;
        if (data.table) html += `<table>${data.table.map((row) => `<tr><td>${row[0]}</td><td>${row[1]}</td></tr>`).join("")}</table>`;
        byId("onboardingBody").innerHTML = html;
        let buttons = step > 0 ? `<button class="mini-btn" id="oboBack">${t("oboBack")}</button>` : `<button class="mini-btn" id="oboSkipAll">${t("oboSkip")}</button>`;
        buttons += step < steps.length - 1
          ? `<button class="mini-btn primary-btn" id="oboNext">${step === 0 ? t("oboStart") : t("oboNext")}</button>`
          : `<button class="mini-btn primary-btn" id="oboDone">${t("oboDone")}</button>`;
        byId("onboardingActions").innerHTML = buttons;
        byId("oboBack")?.addEventListener("click", () => { step -= 1; render(); });
        byId("oboNext")?.addEventListener("click", () => { step += 1; render(); });
        byId("oboSkipAll")?.addEventListener("click", close);
        byId("oboDone")?.addEventListener("click", close);
      }

      byId("onboardingClose").onclick = close;
      render();
    }

    function switchSettingsPanel(panel) {
      documentRef.querySelectorAll(".settings-nav-item").forEach((element) => {
        element.classList.toggle("active", element.dataset.panel === panel);
      });
      const detail = byId("settingsDetail");
      if (!detail) return;
      switch (panel) {
        case "models":
          renderModelsPanel(detail);
          refreshModels().then(() => {
            const list = byId("settingsModelList");
            if (list) list.innerHTML = els.modelListBox.innerHTML;
          });
          break;
        case "account": renderAccountPanel(detail); break;
        case "memory": renderMemoryPanel(detail); break;
        case "skills": renderSkillsInSettings(detail); break;
        case "system": renderSystemPanel(detail); break;
        case "theme": renderThemePanel(detail); break;
        case "language": renderLanguagePanel(detail); break;
        case "update": renderUpdatePanel(detail); break;
        default: return;
      }
      applyI18n();
    }

    function openSettingsPage(panel = "models") {
      byId("settingsPage")?.classList.remove("hidden");
      switchSettingsPanel(panel);
    }

    function bind() {
      if (bound) return;
      bound = true;
      global.matchMedia?.("(prefers-color-scheme: dark)")?.addEventListener("change", () => {
        if ((storage?.getItem("code-theme") || "light") === "system") applyTheme("system");
      });
      byId("settingsMenuBtn")?.addEventListener("click", () => {
        markUpdateNoticeSeen("settings");
        openSettingsPage("models");
      });
      byId("settingsNav")?.addEventListener("click", (event) => {
        const item = event.target.closest(".settings-nav-item");
        if (!item) return;
        if (item.dataset.panel === "update") markUpdateNoticeSeen("page");
        switchSettingsPanel(item.dataset.panel);
      });
      byId("closeSettingsPage")?.addEventListener("click", () => byId("settingsPage")?.classList.add("hidden"));
      byId("settingsPage")?.addEventListener("click", (event) => {
        if (event.target === event.currentTarget) event.currentTarget.classList.add("hidden");
      });
      [["settingsModels", "models"], ["settingsMemory", "memory"], ["settingsSkills", "skills"], ["settingsSystem", "system"]].forEach(([id, panel]) => {
        byId(id)?.addEventListener("click", () => {
          closeDropdown();
          openSettingsPage(panel);
        });
      });
      byId("closeSystemPrompt")?.addEventListener("click", () => byId("systemPromptModal")?.classList.add("hidden"));
      byId("systemPromptModal")?.addEventListener("click", (event) => {
        if (event.target === event.currentTarget) event.currentTarget.classList.add("hidden");
      });
      documentRef.querySelectorAll(".theme-opt").forEach((button) => {
        button.addEventListener("click", () => applyTheme(button.dataset.theme));
      });
      documentRef.addEventListener("click", (event) => {
        if (!event.target.closest(".settings-dropdown")) closeDropdown();
      });
      els.closeSettings?.addEventListener("click", () => showSettings(false));
      els.settingsModal?.addEventListener("click", (event) => {
        if (event.target === els.settingsModal) showSettings(false);
      });
    }

    return Object.freeze({
      applyTheme,
      bind,
      checkCodeCallback,
      checkForUpdates,
      closeDropdown,
      loadKeyConfig: () => loadKeyConfig(storage),
      openSettingsPage,
      shouldShowOnboarding,
      showOnboarding,
      switchSettingsPanel,
      updateThemeButtons,
    });
  }

  Code.features.settings = Object.freeze({
    UPDATE_NOTICE_STORAGE_KEYS,
    createSettingsFeature,
    loadKeyConfig,
  });
})(window);
