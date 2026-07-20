(function registerMarkdownUi(global) {
  "use strict";

  const Code = global.Code;
  if (!Code?.ui) throw new Error("Code namespace must load before markdown UI");

  const SYNTAX_PATTERNS = Object.freeze({
    json: [],
    javascript: [
      [/\b(function|const|let|var|return|if|else|for|while|async|await|class|import|export|from|default|try|catch|throw|new|this|typeof|instanceof|of|in|null|undefined|true|false)\b/g, "syn-kw"],
      [/(["'`])(?:\\.|(?!\1).)*?\1/g, "syn-str"],
      [/(\/\/.*$)/gm, "syn-com"],
      [/(\/\*[\s\S]*?\*\/)/g, "syn-com"],
      [/\b(\d+\.?\d*)\b/g, "syn-num"],
      [/(=>|\b(?:===?|!==?|[+\-*/%])\b)/g, "syn-op"],
    ],
    js: "javascript",
    jsx: "javascript",
    ts: "javascript",
    typescript: "javascript",
    python: [
      [/\b(def|class|return|if|elif|else|for|while|import|from|as|try|except|raise|with|and|or|not|in|is|None|True|False|pass|break|continue|yield|async|await|lambda|global|nonlocal)\b/g, "syn-kw"],
      [/(["'])(?:\\.|(?!\1).)*?\1/g, "syn-str"],
      [/(#.*$)/gm, "syn-com"],
      [/("""[\s\S]*?""")|('''[\s\S]*?''')/g, "syn-com"],
      [/\b(\d+\.?\d*)\b/g, "syn-num"],
      [/@\w+/g, "syn-op"],
    ],
    py: "python",
    html: [
      [/(<\/?)(\w+)/g, "syn-kw"],
      [/("(?:[^"\\]|\\.)*")/g, "syn-str"],
      [/(<!--[\s\S]*?-->)/g, "syn-com"],
      [/(\w+)=/g, "syn-fn"],
    ],
    css: [
      [/([.#]?[a-zA-Z_-]+)(?=\s*\{)/g, "syn-fn"],
      [/(:(?:[^;{]+))/g, "syn-str"],
      [/(\/\*[\s\S]*?\*\/)/g, "syn-com"],
      [/\b(\d+\.?\d*(?:px|em|rem|%|vh|vw|s)?)\b/g, "syn-num"],
      [/\b(important|bold|normal|italic|none|block|inline|flex|grid|hidden|visible|auto|inherit|initial)\b/g, "syn-kw"],
    ],
  });

  function resolveSyntaxPatterns(lang) {
    if (!lang) return null;
    const patterns = SYNTAX_PATTERNS[lang];
    if (!patterns) return null;
    if (typeof patterns === "string") return resolveSyntaxPatterns(patterns);
    return Array.isArray(patterns) ? patterns : null;
  }

  function createMarkdownFeature(options = {}) {
    const escapeHtml = options.escapeHtml || ((value) => String(value ?? ""));
    const renderDiff = options.renderDiff || ((text) => escapeHtml(text));
    const markedRef = options.marked || global.marked;
    const random = options.random || Math.random;

    if (!markedRef?.Renderer || typeof markedRef.parse !== "function" || typeof markedRef.setOptions !== "function") {
      throw new Error("markdown UI requires marked");
    }

    function highlightSyntax(code, lang) {
      const source = String(code ?? "");
      if (lang === "json") {
        const tokenPattern = /"(?:\\.|[^"\\])*"|-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b|\b(?:true|false|null)\b/g;
        let result = "";
        let cursor = 0;
        for (const match of source.matchAll(tokenPattern)) {
          const index = match.index ?? 0;
          const token = match[0];
          result += escapeHtml(source.slice(cursor, index));
          let className = "syn-num";
          if (token.startsWith('"')) {
            className = /^\s*:/.test(source.slice(index + token.length)) ? "syn-key" : "syn-str";
          } else if (/^(?:true|false|null)$/.test(token)) {
            className = "syn-kw";
          }
          result += `<span class="${className}">${escapeHtml(token)}</span>`;
          cursor = index + token.length;
        }
        return result + escapeHtml(source.slice(cursor));
      }

      const patterns = resolveSyntaxPatterns(lang);
      if (!patterns) return escapeHtml(source);
      const tokens = [];
      patterns.forEach(([regex, className], priority) => {
        const flags = regex.flags.includes("g") ? regex.flags : `${regex.flags}g`;
        const matcher = new RegExp(regex.source, flags);
        for (const match of source.matchAll(matcher)) {
          const text = match[0];
          if (!text) continue;
          const start = match.index ?? 0;
          tokens.push({ start, end: start + text.length, text, className, priority });
        }
      });
      tokens.sort((a, b) => a.start - b.start || b.end - a.end || a.priority - b.priority);
      let cursor = 0;
      let result = "";
      tokens.forEach((token) => {
        if (token.start < cursor) return;
        result += escapeHtml(source.slice(cursor, token.start));
        result += `<span class="${token.className}">${escapeHtml(token.text)}</span>`;
        cursor = token.end;
      });
      return result + escapeHtml(source.slice(cursor));
    }

    function renderAnsi(text) {
      let stack = [];
      let result = escapeHtml(text).replace(/\x1b\[(\d+(?:;\d+)*)m/g, (_, codes) => {
        let html = "";
        while (stack.length) {
          html += "</span>";
          stack.pop();
        }
        codes.split(";").map(Number).forEach((code) => {
          if (code >= 30 && code <= 37) stack.push(`ansi-${code}`);
          else if (code === 1 || code === 3 || code === 4) stack.push(`ansi-${code}`);
        });
        stack.forEach((className) => { html += `<span class="${className}">`; });
        return html;
      });
      while (stack.length) {
        result += "</span>";
        stack.pop();
      }
      return result;
    }

    const renderer = new markedRef.Renderer();
    renderer.code = function renderCodeBlock({ text, lang }) {
      if (lang === "diff" || lang === "diff ") return renderDiff(text);
      if (lang === "terminal" || lang === "ansi") {
        return `<div class="code-block"><div class="code-head"><span>terminal</span></div><div class="ansi-block">${renderAnsi(text)}</div></div>`;
      }
      const patterns = resolveSyntaxPatterns(lang);
      const lines = text.split("\n");
      const lineHtml = lines.map((line, index) => {
        const source = line || " ";
        const highlighted = patterns ? highlightSyntax(source, lang) : escapeHtml(source);
        return `<span class="line-no">${index + 1}</span><code class="line-code">${highlighted}</code>`;
      }).join("");
      const codeId = `cb-${random().toString(36).slice(2, 10)}`;
      return `<div class="code-block"><div class="code-head"><span>${escapeHtml(lang || "text")}</span><button class="copy-code" type="button" data-code-id="${codeId}">copy</button></div><pre class="code-lines" id="${codeId}">${lineHtml}</pre></div>`;
    };
    markedRef.setOptions({ renderer, breaks: true, gfm: true });

    function renderMathInText(text) {
      if (!text || typeof global.katex === "undefined") return text;

      // ── Step 1: protect code regions (fenced + inline) so $ inside them stays raw ──
      const codeRegions = [];
      let cid = 0;
      text = text.replace(/```[\s\S]*?```/g, (match) => {
        codeRegions.push(match);
        return `\x00CODE${cid++}\x00`;
      });
      text = text.replace(/`[^`\n]+`/g, (match) => {
        codeRegions.push(match);
        return `\x00CODE${cid++}\x00`;
      });

      // ── Step 2: extract math expressions ──
      const placeholders = [];
      let pid = 0;

      // Display math: $$ ... $$  and  \[ ... \]
      text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, math) => {
        placeholders.push({ math: math.trim(), disp: true });
        return `\x00MATH${pid++}\x00`;
      });
      text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => {
        placeholders.push({ math: math.trim(), disp: true });
        return `\x00MATH${pid++}\x00`;
      });

      // Inline math: $ ... $  (single-line, no lookbehind for broad compat)
      text = text.replace(/\$([^$\s](?:[^$\n]*[^$\s])?)\$/g, (_, math) => {
        placeholders.push({ math: math.trim(), disp: false });
        return `\x00MATH${pid++}\x00`;
      });
      // Inline math: \( ... \)
      text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => {
        placeholders.push({ math: math.trim(), disp: false });
        return `\x00MATH${pid++}\x00`;
      });

      // ── Step 3: render math placeholders to KaTeX HTML ──
      placeholders.forEach(({ math, disp }, idx) => {
        try {
          const rendered = global.katex.renderToString(math, { displayMode: disp, throwOnError: false });
          const attr = math.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
          text = text.replace(
            `\x00MATH${idx}\x00`,
            disp
              ? `<span class="math-block" data-latex="${attr}">${rendered}</span>`
              : `<span class="math-inline" data-latex="${attr}">${rendered}</span>`
          );
        } catch (_) {
          text = text.replace(`\x00MATH${idx}\x00`, escapeHtml(math));
        }
      });

      // ── Step 4: restore protected code regions ──
      codeRegions.forEach((code, idx) => {
        text = text.replace(`\x00CODE${idx}\x00`, code);
      });

      return text;
    }

    function renderMarkdownLite(text) {
      if (!text) return "";
      // Extract and render math BEFORE marked parsing so LaTeX isn't mangled
      let html = renderMathInText(text);
      // Escape setext heading underlines (lines of = or -) so marked doesn't
      // turn preceding text into an <h1>/<h2>. Common in PowerShell here-strings
      // and code-comment separators like "# =======".
      html = html.replace(/^[ \t]*[=\-]{3,}[ \t]*$/gm, (match) => "\\" + match);
      html = markedRef.parse(html);
      html = html.replace(/<code>([^<]+)<\/code>/g, (_, code) => {
        const path = code.trim();
        if (/\.\w{1,8}$/.test(path) || /^[\/\\]|[A-Za-z]:[\/\\]/.test(path)) {
          return `<code class="clickable-path" data-path="${escapeHtml(path)}" title="Click to open">${code}</code>`;
        }
        return `<code>${code}</code>`;
      });
      html = html.replace(/<a /g, '<a target="_blank" rel="noopener" ');
      html = html.replace(/<img\s+src="([^"]+)"/g, (full, src) => {
        if (/^(https?:|data:|\/api\/)/.test(src)) return full;
        const imagePath = src.replace(/\\/g, "/").replace(/^\.?\/?/, "");
        const extension = (imagePath.split(".").pop() || "").toLowerCase();
        if (!/^(png|jpg|jpeg|gif|webp|svg|bmp|ico)$/i.test(extension)) return full;
        const apiUrl = `/api/file?path=${encodeURIComponent(imagePath)}&raw=1`;
        return `<img src="${apiUrl}" loading="lazy" onclick="showImageOverlay(this.src)" class="msg-inline-img"`;
      });
      return html;
    }

    function setupMathCopyHandler(messagesEl) {
      if (!messagesEl) return;
      messagesEl.addEventListener("copy", (e) => {
        const sel = global.getSelection();
        if (!sel || sel.isCollapsed) return;
        const range = sel.getRangeAt(0);
        if (!messagesEl.contains(range.commonAncestorContainer)) return;

        const clone = range.cloneContents();
        const mathEls = clone.querySelectorAll(".math-inline, .math-block");
        mathEls.forEach((el) => {
          const latex = el.getAttribute("data-latex") || el.textContent || "";
          if (!latex) return;
          const isBlock = el.classList.contains("math-block");
          const replacement = isBlock ? `$$\n${latex}\n$$` : `$${latex}$`;
          el.replaceWith(global.document.createTextNode(replacement));
        });

        e.preventDefault();
        e.clipboardData.setData("text/plain", clone.textContent || "");
      });
    }

    return Object.freeze({
      highlightSyntax,
      renderAnsi,
      renderMarkdownLite,
      renderer,
      setupMathCopyHandler,
    });
  }

  Code.ui.markdown = Object.freeze({
    SYNTAX_PATTERNS,
    createMarkdownFeature,
    resolveSyntaxPatterns,
  });
})(window);
