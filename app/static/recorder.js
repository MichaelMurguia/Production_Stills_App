/* recorder.js — dev-only fixture recorder (HARNESS tooling, 2026-08-13).
 *
 * Loaded by index.html ONLY when ?record=1 is in the URL, and loaded
 * BEFORE app.js so window.fetch is wrapped before boot() runs. A normal
 * session never loads this file — no DOM, network, or console trace.
 *
 * The rule the whole harness rests on: fixtures are RECORDED, never
 * authored. Every byte this file captures came off a real production;
 * the replay harness (tools/build_harness.py) serves it back verbatim.
 *
 * Only /api/ traffic that flows through fetch is captured. Images load
 * via <img> tags and never pass through here — the harness substitutes
 * a placeholder for those by design.
 */
(() => {
  "use strict";

  const real = window.fetch.bind(window);
  const log = [];          // ordered — repeated GETs of a mutating resource replay in sequence
  const seen = new Map();  // "GET /api/projects" -> count

  let appSha = "unknown";
  // Straight through `real`, so the probe itself is never recorded.
  real("/api/healthz").then(r => r.json())
    .then(h => { appSha = h.app_sha || "unknown"; })
    .catch(() => {});

  window.fetch = async (input, init = {}) => {
    const url = typeof input === "string" ? input : input.url;
    const method = ((init && init.method) ||
                    (typeof input === "object" && input.method) ||
                    "GET").toUpperCase();
    const res = await real(input, init);

    // Only record app traffic. Fonts, icons and the like are left alone.
    if (url.startsWith("/api/")) {
      const ctype = (res.headers.get("Content-Type") || "").toLowerCase();
      let body = null, kind = "json";
      if (ctype.includes("json") || ctype === "") {
        try { body = await res.clone().json(); }
        catch { kind = "text"; try { body = await res.clone().text(); } catch { body = null; } }
      } else if (ctype.startsWith("text/")) {
        kind = "text";
        try { body = await res.clone().text(); } catch { body = null; }
      } else {
        // Binary (an image served under /api/, a zip). Recording the
        // bytes would balloon the bundle; the harness placeholders it.
        kind = "binary";
      }
      const key = `${method} ${url}`;
      const n = seen.get(key) || 0;
      seen.set(key, n + 1);
      log.push({ key, method, url, seq: n, status: res.status, kind, body });
      paint();
    }
    return res;
  };

  // ---------------------------------------------------------------- chip
  // Fixed, bottom-left, Courier, --hold border (HARNESS_AUDIT R16:
  // "this session is being captured" is attention-not-blocking, an
  // operator state — dev tooling may not borrow amber). Click downloads
  // the bundle. Styles are inline (tokens via var()) because this file
  // must leave styles.css untouched — it never ships to a normal session.
  const chip = document.createElement("button");
  chip.id = "rec-chip";
  chip.type = "button";
  chip.title = "Recording API fixtures — click to download the bundle";
  chip.style.cssText = [
    "position:fixed", "left:14px", "bottom:14px", "z-index:99999",
    "font-family:var(--mono)", "font-size:12px", "letter-spacing:.4px",
    "color:var(--ink)", "background:var(--panel)",
    "border:1px solid var(--hold)", "border-radius:0",
    "padding:7px 12px", "cursor:pointer",
  ].join(";");

  const paint = () => {
    chip.textContent = `REC ● ${log.length} CAPTURED — DOWNLOAD`;
  };

  chip.onclick = () => {
    // The active production, read from what the session itself recorded —
    // never authored here.
    let slug = "";
    const proj = log.find(e => e.key === "GET /api/projects" && e.kind === "json");
    if (proj && proj.body && typeof proj.body.active === "string") slug = proj.body.active;

    const bundle = {
      recorded_at: new Date().toISOString(),
      app_sha: appSha,
      project_slug: slug,
      entries: log,
    };
    const blob = new Blob([JSON.stringify(bundle, null, 1)],
                          { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `fixtures-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const mount = () => { paint(); document.body.appendChild(chip); };
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
