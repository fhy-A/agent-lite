(function initializeCodeFilesFeature(global) {
  "use strict";

  const features = global.Code && global.Code.features;
  if (!features) {
    throw new Error("Code features namespace must load before files");
  }

  function shortPath(path = "") {
    const normalized = String(path).replaceAll("/", "\\");
    const parts = normalized.split("\\").filter(Boolean);
    if (parts.length <= 2) return normalized || "~";
    return `~\\${parts.slice(-2).join("\\")}`;
  }

  function arrayBufferToBase64(buffer, encode = global.btoa) {
    const bytes = new Uint8Array(buffer);
    const chunkSize = 0x8000;
    let binary = "";
    for (let index = 0; index < bytes.length; index += chunkSize) {
      binary += String.fromCharCode.apply(null, bytes.subarray(index, index + chunkSize));
    }
    return encode(binary);
  }

  function sortFileItems(items = [], mode = "default", ascending = true) {
    const sorted = [...items];
    const direction = ascending ? 1 : -1;

    if (mode === "type") {
      sorted.sort((a, b) => {
        if (a.type !== b.type) return (a.type === "dir" ? -1 : 1) * direction;
        const extA = (a.name.split(".").pop() || "").toLowerCase();
        const extB = (b.name.split(".").pop() || "").toLowerCase();
        if (extA !== extB) return extA.localeCompare(extB) * direction;
        return a.name.localeCompare(b.name) * direction;
      });
    } else if (mode === "time") {
      sorted.sort((a, b) => (
        (new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0)) * direction
      ));
    } else {
      sorted.sort((a, b) => {
        if (a.type !== b.type) return (a.type === "dir" ? -1 : 1) * direction;
        return a.name.localeCompare(b.name) * direction;
      });
    }

    return sorted;
  }

  const FILE_TIME_WIDE_SIDEBAR_MIN = 320;

  function formatFileTimestamp(value, now = new Date()) {
    const date = value instanceof Date ? value : new Date(value || "");
    const current = now instanceof Date ? now : new Date(now);
    if (Number.isNaN(date.getTime()) || Number.isNaN(current.getTime())) {
      return { compact: "", full: "" };
    }
    const pad = (number) => String(number).padStart(2, "0");
    const year = date.getFullYear();
    const monthDay = `${pad(date.getMonth() + 1)}/${pad(date.getDate())}`;
    const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
    const full = `${year}/${monthDay} ${time}`;
    const sameDay = year === current.getFullYear()
      && date.getMonth() === current.getMonth()
      && date.getDate() === current.getDate();
    const compact = sameDay
      ? time
      : year === current.getFullYear()
        ? `${monthDay} ${time}`
        : `${year}/${monthDay}`;
    return { compact, full };
  }

  function createFilesFeature(options = {}) {
    const state = options.state;
    const elements = options.elements;
    const t = options.t;
    const escapeHtml = options.escapeHtml;
    const apiJson = options.apiJson;
    const showToast = options.showToast;
    const openFile = options.openFile;
    const insertPromptText = options.insertPromptText;
    const saveProjectRoot = options.saveProjectRoot;
    const documentRoot = options.documentRoot || global.document;
    const storage = options.storage || global.localStorage;
    const fetchImpl = options.fetch || ((...args) => global.fetch(...args));

    if (!state || !elements || !t || !escapeHtml || !apiJson) {
      throw new Error("Files feature requires state, elements, t, escapeHtml, and apiJson");
    }

    let fileContextMenu = null;
    let bound = false;

    function getRecentFolders() {
      try {
        const value = JSON.parse(storage.getItem("code-recent-folders") || "[]");
        return Array.isArray(value) ? value : [];
      } catch (_) {
        return [];
      }
    }

    function addRecentFolder(path) {
      if (!path) return;
      const filtered = getRecentFolders().filter((item) => item !== path);
      filtered.unshift(path);
      storage.setItem("code-recent-folders", JSON.stringify(filtered.slice(0, 8)));
    }

    function removeRecentFolder(path) {
      if (!path) return;
      storage.setItem(
        "code-recent-folders",
        JSON.stringify(getRecentFolders().filter((item) => item !== path)),
      );
    }

    async function uploadAttachment(file) {
      const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());
      return apiJson("/api/attachments", {
        method: "POST",
        body: JSON.stringify({
          name: file.name,
          contentBase64,
        }),
      });
    }

    function pickProjectFile() {
      if (!elements.filePicker) return;
      elements.filePicker.value = "";
      elements.filePicker.click();
    }

    async function resolvePickedFile(file) {
      if (!file) return;
      if (elements.attachFile) elements.attachFile.disabled = true;
      try {
        const data = await uploadAttachment(file);
        insertPromptText?.(data.path);
      } catch (error) {
        showToast?.(error.message || t("chooseFileFailed"), "error");
      } finally {
        if (elements.attachFile) elements.attachFile.disabled = false;
      }
    }

    function showFileContextMenu(x, y, path, type) {
      if (fileContextMenu) fileContextMenu.remove();
      const menu = documentRoot.createElement("div");
      menu.className = "file-ctx-menu";
      const menuWidth = 180;
      const menuHeight = 130;
      menu.style.left = Math.min(x, global.innerWidth - menuWidth) + "px";
      menu.style.top = Math.min(y, global.innerHeight - menuHeight) + "px";
      const filename = (path || "").split("/").pop() || "";
      if (type === "file") {
        menu.innerHTML = `<div class="file-ctx-name">${escapeHtml(filename)}</div>
          <button data-action="open">${t("openDefaultApp")}</button>
          <button data-action="copy-path">${t("copyPath")}</button>
          <button data-action="reveal">${t("revealInFolder")}</button>`;
      } else {
        menu.innerHTML = `<div class="file-ctx-name">${escapeHtml(filename)}</div>
          <button data-action="explore">${t("openExplorer")}</button>
          <button data-action="copy-path">${t("copyPath")}</button>
          <button data-action="terminal">${t("openTerminal")}</button>`;
      }

      menu.querySelectorAll("button").forEach((button) => {
        button.addEventListener("click", () => {
          const action = button.dataset.action;
          if (action === "copy-path") {
            const root = (elements.projectRoot?.value || "").replace(/[\\/]+$/, "");
            const fullPath = root ? `${root}/${path}`.replace(/\\/g, "/") : path;
            global.navigator.clipboard.writeText(fullPath)
              .then(() => showToast?.(t("pathCopied"), "warning"))
              .catch(() => showToast?.(t("copyFailed"), "error"));
          } else {
            const body = { path };
            if (action === "reveal") body.reveal = true;
            if (action === "terminal") body.terminal = true;
            fetchImpl("/api/open-file", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            }).catch(() => showToast?.(t("openFailed"), "error"));
          }
          menu.remove();
        });
      });

      documentRoot.body.appendChild(menu);
      fileContextMenu = menu;
      const close = (event) => {
        if (!menu.contains(event.target)) {
          menu.remove();
          fileContextMenu = null;
          documentRoot.removeEventListener("click", close);
        }
      };
      global.setTimeout(() => documentRoot.addEventListener("click", close), 0);
    }

    function renderFileTree() {
      if (state._noProject) {
        elements.fileTree.innerHTML = `<div class="muted-line" style="padding:12px;">${t("noProjectDir")}</div>`;
        elements.goUp.disabled = true;
        elements.newFolderBtn.disabled = true;
        elements.refreshFiles.disabled = true;
        return;
      }

      elements.goUp.disabled = false;
      elements.newFolderBtn.disabled = false;
      elements.refreshFiles.disabled = false;

      const query = elements.fileSearch.value.trim().toLowerCase();
      const items = state._fileItems || [];
      const filtered = query
        ? items.filter((item) => item.name.toLowerCase().includes(query))
        : items;
      const sortMode = state._fileSortMode || "default";
      const ascending = state._fileSortAsc !== false;

      if (elements.fileSortBtn) {
        const labels = {
          default: t("sortDefault"),
          type: t("sortType"),
          time: t("sortTime"),
        };
        documentRoot.getElementById("fileSortLabel").textContent = labels[sortMode] || t("sortType");
        documentRoot.getElementById("fileSortArrow").textContent = ascending ? "↑" : "↓";
      }

      const sorted = sortFileItems(filtered, sortMode, ascending);
      elements.fileTree.innerHTML = sorted.length
        ? sorted.map((item) => {
            const extension = item.type === "dir"
              ? ""
              : ((item.name || "").split(".").pop() || "").toLowerCase().slice(0, 6);
            const extensionClass = extension ? ` ext-${extension}` : "";
            const timestamp = formatFileTimestamp(item.updatedAt);
            const timestampHtml = timestamp.full
              ? `<small class="file-time" title="${escapeHtml(timestamp.full)}" aria-label="${escapeHtml(timestamp.full)}"><span class="file-time-compact" aria-hidden="true">${escapeHtml(timestamp.compact)}</span><span class="file-time-full" aria-hidden="true">${escapeHtml(timestamp.full)}</span></small>`
              : "";
            return `<div class="file-item-row ${item.path === state.previewPath ? "active" : ""}">
              <button class="file-item ${item.type}${extensionClass}" type="button" data-path="${escapeHtml(item.path)}" data-type="${item.type}">
                <span class="file-name">${item.type === "dir" ? "📁 " : ""}${escapeHtml(item.name)}</span>
                ${timestampHtml}
              </button>
              <button class="file-at-btn" type="button" data-path="${escapeHtml(item.path)}" title="${t("fileAtTitle")}">@</button>
            </div>`;
          }).join("")
        : `<div class="muted-line" style="padding:8px;">${query ? t("noMatchingFiles") : t("emptyDirectory")}</div>`;

      elements.fileTree.querySelectorAll(".file-item").forEach((button) => {
        button.addEventListener("click", () => {
          if (button.dataset.type === "dir") loadFiles(button.dataset.path);
          else openFile?.(button.dataset.path);
        });
        button.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          showFileContextMenu(
            event.clientX,
            event.clientY,
            button.dataset.path,
            button.dataset.type,
          );
        });
      });

      elements.fileTree.querySelectorAll(".file-at-btn").forEach((button) => {
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          insertPromptText?.(`@${button.dataset.path} `);
        });
      });
    }

    function setFileTimeDensity(sidebarWidth) {
      elements.fileTree?.classList.toggle(
        "file-time-wide",
        Number(sidebarWidth) >= FILE_TIME_WIDE_SIDEBAR_MIN,
      );
    }

    async function loadFiles(path = state.currentDir) {
      const data = await apiJson(`/api/files?path=${encodeURIComponent(path || "")}`);
      state.currentDir = data.path || "";
      elements.filePathBar.textContent = state.currentDir ? `/${state.currentDir}` : "/";
      elements.cwdPathText.textContent = shortPath(data.root || "");
      elements.fileSearch.value = "";
      state._fileItems = data.items || [];
      elements.goUp.disabled = !state.currentDir;
      renderFileTree();
    }

    function goUpDir() {
      if (!state.currentDir) return;
      const parts = state.currentDir.split("/").filter(Boolean);
      parts.pop();
      loadFiles(parts.join("/"));
    }

    function renderRecentFolders() {
      const recentContainer = documentRoot.getElementById("cwdRecentFolders");
      const dropdown = documentRoot.getElementById("cwdDropdown");
      const recents = getRecentFolders();
      if (recents.length === 0) {
        recentContainer.innerHTML = "";
        recentContainer.style.display = "none";
        return;
      }

      recentContainer.style.display = "block";
      recentContainer.innerHTML = `<div class="cwd-dropdown-label">${t("recentLabel")}</div>`
        + recents.slice(0, 5).map((path) => (
          `<button class="cwd-dropdown-item cwd-recent-item" data-path="${escapeHtml(path)}">${escapeHtml(shortPath(path))}</button>`
        )).join("");
      recentContainer.querySelectorAll(".cwd-recent-item").forEach((button) => {
        button.addEventListener("click", async () => {
          const path = button.dataset.path;
          dropdown.classList.add("hidden");
          try {
            await saveProjectRoot?.(path);
          } catch (error) {
            const message = String(error.message || error);
            if (/目录不存在|不是文件夹|not exist|not a directory/i.test(message)) {
              removeRecentFolder(path);
              renderRecentFolders();
            }
            showToast?.(message, "error");
          }
        });
      });
    }

    function toggleCwdDropdown() {
      const dropdown = documentRoot.getElementById("cwdDropdown");
      const open = !dropdown.classList.contains("hidden");
      if (open) {
        dropdown.classList.add("hidden");
        return;
      }

      renderRecentFolders();
      const rect = elements.projectRootShort.getBoundingClientRect();
      const spaceBelow = global.innerHeight - rect.bottom;
      dropdown.style.position = "fixed";
      dropdown.style.left = rect.left + "px";
      dropdown.style.right = "auto";
      dropdown.style.width = rect.width + "px";
      dropdown.style.margin = "4px 0 0 0";
      if (spaceBelow < 200) {
        dropdown.style.top = "auto";
        dropdown.style.bottom = (global.innerHeight - rect.top + 4) + "px";
      } else {
        dropdown.style.top = rect.bottom + "px";
        dropdown.style.bottom = "auto";
      }
      dropdown.classList.remove("hidden");
    }

    async function pickFolder() {
      try {
        const data = await apiJson("/api/pick-folder");
        if (!data.cancelled) await saveProjectRoot?.(data.path);
      } catch (error) {
        showToast?.(error.message, "error");
      }
    }

    function openNewFolder() {
      const modal = documentRoot.getElementById("newFolderModal");
      const input = documentRoot.getElementById("newFolderName");
      modal.classList.remove("hidden");
      input.value = "";
      input.focus();
    }

    function hideNewFolder() {
      documentRoot.getElementById("newFolderModal").classList.add("hidden");
    }

    async function createNewFolder() {
      const input = documentRoot.getElementById("newFolderName");
      const name = input.value.trim();
      if (!name) return;
      try {
        await apiJson("/api/mkdir", {
          method: "POST",
          body: JSON.stringify({ name, parent: state.currentDir }),
        });
        hideNewFolder();
        await loadFiles(state.currentDir);
      } catch (error) {
        showToast?.(error.message, "error");
      }
    }

    function bind() {
      if (bound) return;
      bound = true;

      const dropdown = documentRoot.getElementById("cwdDropdown");
      const newFolderModal = documentRoot.getElementById("newFolderModal");
      const newFolderName = documentRoot.getElementById("newFolderName");

      state._fileSortMode = storage.getItem("code-sort-mode") || "default";
      state._fileSortAsc = storage.getItem("code-sort-asc") !== "false";

      elements.attachFile?.addEventListener("click", pickProjectFile);
      elements.filePicker?.addEventListener("change", () => {
        resolvePickedFile(elements.filePicker.files?.[0]);
      });
      elements.projectRootShort?.addEventListener("click", toggleCwdDropdown);
      documentRoot.getElementById("cwdPickFolderBtn")?.addEventListener("click", () => {
        dropdown.classList.add("hidden");
        pickFolder();
      });
      documentRoot.getElementById("cwdHomeBtn")?.addEventListener("click", () => {
        dropdown.classList.add("hidden");
        saveProjectRoot?.("");
      });
      documentRoot.addEventListener("click", (event) => {
        if (!event.target.closest(".cwd-dropdown") && !event.target.closest("#projectRootShort")) {
          dropdown.classList.add("hidden");
        }
      });

      documentRoot.getElementById("closeNewFolder")?.addEventListener("click", hideNewFolder);
      documentRoot.getElementById("cancelNewFolder")?.addEventListener("click", hideNewFolder);
      newFolderModal?.addEventListener("click", (event) => {
        if (event.target === event.currentTarget) hideNewFolder();
      });
      documentRoot.getElementById("confirmNewFolder")?.addEventListener("click", createNewFolder);
      newFolderName?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") createNewFolder();
        if (event.key === "Escape") hideNewFolder();
      });

      elements.refreshFiles?.addEventListener("click", (event) => {
        event.stopPropagation();
        loadFiles().catch((error) => showToast?.(error.message, "error"));
      });
      elements.newFolderBtn?.addEventListener("click", (event) => {
        event.stopPropagation();
        openNewFolder();
      });
      elements.fileSearch?.addEventListener("input", renderFileTree);
      elements.fileSortBtn?.addEventListener("click", () => {
        state._fileSortAsc = !state._fileSortAsc;
        storage.setItem("code-sort-asc", state._fileSortAsc);
        renderFileTree();
      });
      elements.fileSortBtn?.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        const modes = ["type", "time", "default"];
        const current = state._fileSortMode || "type";
        state._fileSortMode = modes[(modes.indexOf(current) + 1) % modes.length];
        state._fileSortAsc = true;
        storage.setItem("code-sort-mode", state._fileSortMode);
        storage.setItem("code-sort-asc", "true");
        renderFileTree();
      });
      elements.goUp?.addEventListener("click", (event) => {
        event.stopPropagation();
        goUpDir();
      });
    }

    return Object.freeze({
      bind,
      loadFiles,
      renderFileTree,
      setFileTimeDensity,
      addRecentFolder,
      removeRecentFolder,
      pickProjectFile,
      resolvePickedFile,
    });
  }

  features.files = Object.freeze({
    shortPath,
    arrayBufferToBase64,
    sortFileItems,
    formatFileTimestamp,
    FILE_TIME_WIDE_SIDEBAR_MIN,
    createFilesFeature,
  });
})(window);
