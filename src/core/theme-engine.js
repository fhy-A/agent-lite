(function registerThemeEngine(global) {
  "use strict";

  const Code = global.Code;
  if (!Code?.core) throw new Error("Code namespace must load before theme engine");

  /* ── Color math ─────────────────────────────────────────────── */

  function hexToRgb(hex) {
    const h = hex.replace("#", "");
    return {
      r: parseInt(h.substring(0, 2), 16),
      g: parseInt(h.substring(2, 4), 16),
      b: parseInt(h.substring(4, 6), 16),
    };
  }

  function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map((c) => Math.max(0, Math.min(255, Math.round(c))).toString(16).padStart(2, "0")).join("");
  }

  function mixColors(c1, c2, ratio) {
    const a = hexToRgb(c1);
    const b = hexToRgb(c2);
    const r = 1 - ratio;
    return rgbToHex(a.r * r + b.r * ratio, a.g * r + b.g * ratio, a.b * r + b.b * ratio);
  }

  function alphaStr(hex, a) {
    const { r, g, b } = hexToRgb(hex);
    return `rgba(${r},${g},${b},${a})`;
  }

  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b);
    var l = (max + min) / 2;
    if (max === min) return { h: 0, s: 0, l: l };
    var d = max - min;
    var s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    var h;
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      default: h = ((r - g) / d + 4) / 6; break;
    }
    return { h: h * 360, s: s, l: l };
  }

  function hslToRgb(h, s, l) {
    h /= 360;
    var hue2rgb = function(p, q, t) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    return {
      r: Math.round(hue2rgb(p, q, h + 1/3) * 255),
      g: Math.round(hue2rgb(p, q, h) * 255),
      b: Math.round(hue2rgb(p, q, h - 1/3) * 255),
    };
  }

  /* ── File-type semantic hues ─────────────────────────────────── */

  var FILE_HUES = {
    js: 38,         // amber
    py: 215,        // blue
    css: 280,       // purple
    html: 5,        // red-orange
    json: 48,       // gold
    md: 200,        // cyan-blue
    image: 330,     // pink
    pdf: 0,         // red
    yaml: 260,      // indigo
    powershell: 185,// teal
    shell: 135,     // green
  };

  /* ── Theme registry ─────────────────────────────────────────── */

  const LIGHT_THEMES = {
    absolutely:  { accent:"#cc7d5e", ink:"#2d2d2b", surface:"#f9f9f7", green:"#00c853", red:"#ff5f38", skill:"#cc7d5e" },
    catppuccin:  { accent:"#8839ef", ink:"#4c4f69", surface:"#eff1f5", green:"#40a02b", red:"#d20f39", skill:"#8839ef" },
    codex:       { accent:"#0169cc", ink:"#0d0d0d", surface:"#ffffff", green:"#00a240", red:"#e02e2a", skill:"#751ed9" },
    everforest:  { accent:"#93b259", ink:"#5c6a72", surface:"#fdf6e3", green:"#8da101", red:"#f85552", skill:"#df69ba" },
    github:      { accent:"#0969da", ink:"#1f2328", surface:"#ffffff", green:"#1a7f37", red:"#cf222e", skill:"#8250df" },
    gruvbox:     { accent:"#458588", ink:"#3c3836", surface:"#fbf1c7", green:"#3c3836", red:"#cc241d", skill:"#b16286" },
    linear:      { accent:"#5e6ad2", ink:"#1b1b1b", surface:"#fcfcfd", green:"#52a450", red:"#c94446", skill:"#8160d8" },
    notion:      { accent:"#3183d8", ink:"#37352f", surface:"#ffffff", green:"#008000", red:"#a31515", skill:"#0000ff" },
    one:         { accent:"#526fff", ink:"#383a42", surface:"#fafafa", green:"#3bba54", red:"#e45649", skill:"#526fff" },
    proof:       { accent:"#3d755d", ink:"#2f312d", surface:"#f5f3ed", green:"#3d755d", red:"#ba2623", skill:"#5f6ac2" },
    raycast:     { accent:"#ff6363", ink:"#030303", surface:"#ffffff", green:"#006b4f", red:"#b12424", skill:"#9a1b6e" },
    "rose-pine": { accent:"#d7827e", ink:"#575279", surface:"#faf4ed", green:"#56949f", red:"#797593", skill:"#907aa9" },
    solarized:   { accent:"#b58900", ink:"#657b83", surface:"#fdf6e3", green:"#859900", red:"#dc322f", skill:"#d33682" },
    vercel:      { accent:"#006aff", ink:"#171717", surface:"#ffffff", green:"#28A948", red:"#EB001D", skill:"#A100F8" },
    "vscode-plus":{ accent:"#007acc", ink:"#000000", surface:"#ffffff", green:"#008000", red:"#ee0000", skill:"#0000ff" },
  };

  const DARK_THEMES = {
    absolutely:  { accent:"#cc7d5e", ink:"#f9f9f7", surface:"#2d2d2b", green:"#00c853", red:"#ff5f38", skill:"#cc7d5e" },
    ayu:         { accent:"#e6b450", ink:"#bfbdb6", surface:"#10141c", green:"#70bf56", red:"#f26d78", skill:"#d0a1ff" },
    catppuccin:  { accent:"#cba6f7", ink:"#cdd6f4", surface:"#1e1e2e", green:"#a6e3a1", red:"#f38ba8", skill:"#cba6f7" },
    codex:       { accent:"#0169cc", ink:"#fcfcfc", surface:"#111111", green:"#00a240", red:"#e02e2a", skill:"#b06dff" },
    dracula:     { accent:"#ff79c6", ink:"#f8f8f2", surface:"#282a36", green:"#50fa7b", red:"#ff5555", skill:"#ff79c6" },
    everforest:  { accent:"#a7c080", ink:"#d3c6aa", surface:"#2d353b", green:"#a7c080", red:"#e67e80", skill:"#d699b6" },
    github:      { accent:"#1f6feb", ink:"#e6edf3", surface:"#0d1117", green:"#3fb950", red:"#f85149", skill:"#bc8cff" },
    gruvbox:     { accent:"#458588", ink:"#ebdbb2", surface:"#282828", green:"#ebdbb2", red:"#cc241d", skill:"#b16286" },
    linear:      { accent:"#606acc", ink:"#e3e4e6", surface:"#0f0f11", green:"#69c967", red:"#ff7e78", skill:"#c2a1ff" },
    lobster:     { accent:"#ff5c5c", ink:"#e4e4e7", surface:"#111827", green:"#22c55e", red:"#ff5c5c", skill:"#3b82f6" },
    material:    { accent:"#80cbc4", ink:"#eeffff", surface:"#212121", green:"#c3e88d", red:"#f07178", skill:"#c792ea" },
    matrix:      { accent:"#1eff5a", ink:"#b8ffca", surface:"#040805", green:"#1eff5a", red:"#fa423e", skill:"#1eff5a" },
    monokai:     { accent:"#99947c", ink:"#f8f8f2", surface:"#272822", green:"#86b42b", red:"#c4265e", skill:"#8c6bc8" },
    "night-owl": { accent:"#44596b", ink:"#d6deeb", surface:"#011627", green:"#c5e478", red:"#ef5350", skill:"#c792ea" },
    nord:        { accent:"#88c0d0", ink:"#d8dee9", surface:"#2e3440", green:"#a3be8c", red:"#bf616a", skill:"#b48ead" },
    notion:      { accent:"#3183d8", ink:"#d9d9d8", surface:"#191919", green:"#4ec9b0", red:"#fa423e", skill:"#3183d8" },
    one:         { accent:"#4d78cc", ink:"#abb2bf", surface:"#282c34", green:"#8cc265", red:"#e05561", skill:"#c162de" },
    oscurange:   { accent:"#f9b98c", ink:"#e6e6e6", surface:"#0b0b0f", green:"#40c977", red:"#fa423e", skill:"#479ffa" },
    raycast:     { accent:"#ff6363", ink:"#fefefe", surface:"#101010", green:"#59d499", red:"#ff6363", skill:"#cf2f98" },
    "rose-pine": { accent:"#ea9a97", ink:"#e0def4", surface:"#232136", green:"#9ccfd8", red:"#908caa", skill:"#c4a7e7" },
    sentry:      { accent:"#7055f6", ink:"#e6dff9", surface:"#2d2935", green:"#8ee6d7", red:"#fa423e", skill:"#7055f6" },
    solarized:   { accent:"#d30102", ink:"#839496", surface:"#002b36", green:"#859900", red:"#dc322f", skill:"#d33682" },
    temple:      { accent:"#e4f222", ink:"#c7e6da", surface:"#02120c", green:"#40c977", red:"#fa423e", skill:"#e4f222" },
    "tokyo-night":{ accent:"#3d59a1", ink:"#a9b1d6", surface:"#1a1b26", green:"#449dab", red:"#914c54", skill:"#9d7cd8" },
    vercel:      { accent:"#006efe", ink:"#ededed", surface:"#000000", green:"#00AD3A", red:"#F13342", skill:"#9540D5" },
    "vscode-plus":{ accent:"#007acc", ink:"#d4d4d4", surface:"#1e1e1e", green:"#369432", red:"#f44747", skill:"#000080" },
  };

  /* ── Derive file-type colors from theme base ────────────────── */

  function deriveFileColors(base, isDark) {
    var accentRgb = hexToRgb(base.accent);
    var accentHsl = rgbToHsl(accentRgb.r, accentRgb.g, accentRgb.b);
    var surfRgb = hexToRgb(base.surface);
    // relative luminance (ITU-R BT.601) — 0 = darkest, 1 = brightest
    var surfLum = (surfRgb.r * 0.299 + surfRgb.g * 0.587 + surfRgb.b * 0.114) / 255;

    var result = {};
    var keys = Object.keys(FILE_HUES);
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var hue = FILE_HUES[key];

      // push away from accent if too close (minimum 25° separation)
      // rotate the file's own hue rather than snapping to accent+25
      // so different file types stay visually distinct
      var dist = Math.abs(hue - accentHsl.h);
      if (dist < 25 || dist > 335) {
        hue = (hue + 35) % 360;
      }

      // saturation: moderate, slightly higher on light backgrounds
      var s = isDark ? 0.50 : 0.58;

      // lightness: ensure ≥ 4.5:1 contrast ratio against surface
      // dark surface → lighter file colors; light surface → darker file colors
      var l = isDark
        ? 0.60 + (1 - surfLum) * 0.16   // range ~0.60–0.76
        : 0.36 + surfLum * 0.08;        // range ~0.36–0.44

      var rgb = hslToRgb(hue, s, l);
      result["--file-" + key] = rgbToHex(rgb.r, rgb.g, rgb.b);
    }
    return result;
  }

  /* ── Derive full CSS variable set from base colors ──────────── */

  function deriveTheme(base, isDark) {
    const { accent, ink, surface, green, red, skill } = base;
    const s = surface;
    const t = ink;

    if (isDark) {
      return Object.assign({
        "--bg": s,
        "--panel": mixColors(s, t, 0.06),
        "--panel-2": mixColors(s, t, 0.12),
        "--panel-3": mixColors(s, "#000000", -0.02),
        "--line": mixColors(s, t, 0.18),
        "--line-strong": mixColors(s, t, 0.30),
        "--text": t,
        "--brand-mark": t,
        "--muted": mixColors(s, t, 0.58),
        "--faint": mixColors(s, t, 0.34),
        "--accent": accent,
        "--accent-bg": alphaStr(accent, 0.12),
        "--green": green,
        "--green-bg": alphaStr(green, 0.12),
        "--red": red,
        "--red-bg": alphaStr(red, 0.12),
        "--code-bg": mixColors(s, t, 0.08),
        "--user-bubble-bg": mixColors(s, t, 0.07),
        "--shadow": "0 18px 42px rgba(0,0,0,.28)",
        "--sidebar-scroll-thumb": alphaStr(t, 0.14),
        "--sidebar-scroll-thumb-hover": alphaStr(t, 0.30),
        "--yellow": "#f6c453",
      }, deriveFileColors(base, isDark));
    }

    return Object.assign({
      "--bg": s,
      "--panel": mixColors(s, t, 0.04),
      "--panel-2": mixColors(s, t, 0.08),
      "--panel-3": "#ffffff",
      "--line": mixColors(s, t, 0.12),
      "--line-strong": mixColors(s, t, 0.22),
      "--text": t,
      "--brand-mark": "#000000",
      "--muted": mixColors(s, t, 0.50),
      "--faint": mixColors(s, t, 0.35),
      "--accent": accent,
      "--accent-bg": alphaStr(accent, 0.08),
      "--green": green,
      "--green-bg": alphaStr(green, 0.08),
      "--red": red,
      "--red-bg": alphaStr(red, 0.08),
      "--code-bg": mixColors(s, t, 0.03),
      "--user-bubble-bg": mixColors(s, t, 0.04),
      "--shadow": "0 14px 34px rgba(31,40,55,.10)",
      "--sidebar-scroll-thumb": alphaStr(t, 0.20),
      "--sidebar-scroll-thumb-hover": alphaStr(t, 0.38),
      "--yellow": "#b7791f",
    }, deriveFileColors(base, isDark));
  }

  function applyColors(root, vars) {
    Object.entries(vars).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
  }

  /* ── Apply a specific theme variant ─────────────────────────── */

  function activateTheme(mode, lightVariant, darkVariant) {
    const root = global.document.documentElement;
    const systemDark = global.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
    const isDark = mode === "dark" || (mode === "system" && systemDark);
    const variant = isDark ? (darkVariant || "codex") : (lightVariant || "codex");
    const registry = isDark ? DARK_THEMES : LIGHT_THEMES;
    const base = registry[variant] || registry["codex"];

    root.setAttribute("data-theme-mode", isDark ? "dark" : "light");
    root.setAttribute("data-theme-variant", variant);
    root.style.colorScheme = isDark ? "dark" : "light";
    applyColors(root, deriveTheme(base, isDark));
  }

  /* ── Exports ────────────────────────────────────────────────── */

  Code.core.theme = Object.freeze({
    LIGHT_THEMES,
    DARK_THEMES,
    activateTheme,
    deriveTheme,
    mixColors,
    /* debug helpers */
    __hexToRgb: hexToRgb,
    __rgbToHex: rgbToHex,
  });

})(window);
