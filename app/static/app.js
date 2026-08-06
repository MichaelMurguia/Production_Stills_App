"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

const EVIDENCE_CLASSES = [
  "SCRIPT_EXPLICIT", "SCRIPT_NECESSARY_INFERENCE", "VISUAL_CANON_LOCKED",
  "USER_DIRECTED", "STRONG_INFERENCE", "WEAK_INFERENCE",
  "PROPOSED_NOT_CANON", "UNSUPPORTED",
];
const LEDGER_STATUSES = ["PASS", "HOLD", "REMOVE"];

let toastTimer = null;
function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 4200);
}

function startBusy(host, label, hint = "", onCancel = null) {
  const el = document.createElement("div");
  el.className = "busy wrap";
  el.innerHTML = `
    <div class="spinner"></div>
    <span class="busy-label">${esc(label)}</span>
    ${hint ? `<span class="busy-hint">${esc(hint)}</span>` : ""}
    <span class="elapsed">0:00</span>
    ${onCancel ? '<button class="ghost busy-cancel" title="Cancel — stops waiting for the result">Cancel</button>' : ""}
    <div class="busy-bar"></div>`;
  host.innerHTML = "";
  host.append(el);
  if (onCancel) $(".busy-cancel", el).onclick = onCancel;
  const t0 = Date.now();
  const tick = () => {
    const s = Math.floor((Date.now() - t0) / 1000);
    $(".elapsed", el).textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  };
  const timer = setInterval(tick, 1000);
  return {
    label(msg) { $(".busy-label", el).textContent = msg; },
    done() { clearInterval(timer); el.remove(); },
  };
}

async function api(path, opts = {}) {
  if (opts.json !== undefined) {
    opts.body = JSON.stringify(opts.json);
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    delete opts.json;
  }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON */ }
  if (!res.ok) {
    throw new Error((data && data.detail) || `${res.status} ${res.statusText}`);
  }
  return data;
}

function openCropper(imgUrl, onDone) {
  const ov = document.createElement("div");
  ov.className = "cropper";
  ov.innerHTML = `
    <div class="crop-head">
      <span>Drag a rectangle over the region to harvest as a reference</span>
      <span class="row" style="margin:0">
        <button class="primary" data-f="save" disabled>Save crop → Reference</button>
        <button class="ghost" data-f="cancel">Cancel</button>
      </span>
    </div>
    <div class="crop-stage">
      <div class="crop-wrap">
        <img src="${imgUrl}" alt="crop source" draggable="false">
        <div class="crop-box hidden"></div>
      </div>
    </div>`;
  document.body.append(ov);
  const img = $("img", ov), box = $(".crop-box", ov), wrap = $(".crop-wrap", ov);
  const saveBtn = $("[data-f=save]", ov);
  let rect = null, start = null;

  const rel = (e) => {
    const r = img.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)),
      y: Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)),
    };
  };
  const paint = () => {
    if (!rect) return;
    const r = img.getBoundingClientRect(), w = wrap.getBoundingClientRect();
    box.classList.remove("hidden");
    box.style.left = `${r.left - w.left + rect.x * r.width}px`;
    box.style.top = `${r.top - w.top + rect.y * r.height}px`;
    box.style.width = `${rect.w * r.width}px`;
    box.style.height = `${rect.h * r.height}px`;
  };
  wrap.addEventListener("mousedown", e => { e.preventDefault(); start = rel(e); });
  window.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
  function onMove(e) {
    if (!start) return;
    const p = rel(e);
    rect = { x: Math.min(start.x, p.x), y: Math.min(start.y, p.y),
             w: Math.abs(p.x - start.x), h: Math.abs(p.y - start.y) };
    paint();
  }
  function onUp() {
    if (start && rect && rect.w > 0.02 && rect.h > 0.02) saveBtn.disabled = false;
    start = null;
  }
  const close = () => {
    window.removeEventListener("mousemove", onMove);
    window.removeEventListener("mouseup", onUp);
    document.removeEventListener("keydown", onKey);
    ov.remove();
  };
  function onKey(e) { if (e.key === "Escape") close(); }
  document.addEventListener("keydown", onKey);
  $("[data-f=cancel]", ov).onclick = close;
  saveBtn.onclick = () => { const r = rect; close(); onDone(r); };
}

function openRepair(imgUrl, onSubmit) {
  const ov = document.createElement("div");
  ov.className = "cropper";
  setTimeout(() => fillProviderSelect($("[data-f=prov]", ov), {
    openai: "GPT Image 2 — masked patch",
    gemini: "Gemini (Nano Banana Pro) — guided patch",
  }).then(ok => {
    if (!ok) {
      const go = $("[data-f=go]", ov);
      if (go) { go.disabled = true; go.title = "No usable engine — add or retest a key in Settings."; }
    }
  }));
  ov.innerHTML = `
    <div class="crop-head">
      <span class="row" style="margin:0;flex:1">
        <input type="text" data-f="instr" placeholder="what should change in the painted region…" style="flex:1;max-width:520px" title="The repair instruction — name exactly what changes inside the painted region, e.g. 'a fitted canvas cover following the shape beneath it'">
        <label class="mini" style="display:flex;align-items:center;gap:6px;margin:0">brush
          <input type="range" data-f="brush" min="8" max="140" value="46" style="width:110px">
        </label>
        <select data-f="prov" title="Either engine paints only your painted region — the app composites the result into the original, so every pixel outside your paint is carried over from the source unchanged (no re-encode noise, ever). They are simply different painters for the patch: GPT Image 2 works from a true mask; Gemini from a highlighted guide copy.">
          <option value="openai">GPT Image 2 — masked patch</option>
          <option value="gemini">Gemini (Nano Banana Pro) — guided patch</option>
        </select>
        <button class="ghost" data-f="clear">Clear</button>
      </span>
      <span class="row" style="margin:0">
        <button class="primary" data-f="go" disabled>Repair region</button>
        <button class="ghost" data-f="cancel">Cancel</button>
      </span>
    </div>
    <div data-f="busy" style="padding:0 14px"></div>
    <div class="crop-stage">
      <div class="crop-wrap" style="cursor:crosshair">
        <img src="${imgUrl}" draggable="false" alt="repair source">
        <canvas class="repair-canvas"></canvas>
      </div>
    </div>`;
  document.body.append(ov);
  const img = $("img", ov), canvas = $(".repair-canvas", ov);
  const instr = $("[data-f=instr]", ov), goBtn = $("[data-f=go]", ov);
  const ctx = canvas.getContext("2d");
  let strokes = [];   // natural-resolution coordinates
  let drawing = null;

  const redraw = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "rgba(216,162,74,.55)";
    ctx.lineCap = ctx.lineJoin = "round";
    const k = img.clientWidth / img.naturalWidth;
    for (const st of strokes) {
      ctx.lineWidth = st.r * 2 * k;
      ctx.beginPath();
      st.pts.forEach((p, i) => i ? ctx.lineTo(p.x * k, p.y * k) : ctx.moveTo(p.x * k, p.y * k));
      if (st.pts.length === 1) ctx.lineTo(st.pts[0].x * k + 0.01, st.pts[0].y * k);
      ctx.stroke();
    }
  };
  const sizeCanvas = () => {
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    redraw();
  };
  if (img.complete) sizeCanvas(); else img.onload = sizeCanvas;
  window.addEventListener("resize", sizeCanvas);

  const toNat = (e) => {
    const r = img.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (img.naturalWidth / r.width),
             y: (e.clientY - r.top) * (img.naturalHeight / r.height) };
  };
  const update = () => { goBtn.disabled = !(strokes.length && instr.value.trim()); };
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    const r = (+$("[data-f=brush]", ov).value) * (img.naturalWidth / img.clientWidth) / 2;
    drawing = { r, pts: [toNat(e)] };
    strokes.push(drawing);
    redraw(); update();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (drawing) { drawing.pts.push(toNat(e)); redraw(); }
  });
  canvas.addEventListener("pointerup", () => { drawing = null; });
  $("[data-f=clear]", ov).onclick = () => { strokes = []; redraw(); update(); };
  instr.addEventListener("input", update);

  const close = () => {
    window.removeEventListener("resize", sizeCanvas);
    document.removeEventListener("keydown", onEsc);
    ov.remove();
  };
  const onEsc = e => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onEsc);
  const cancelBtn = $("[data-f=cancel]", ov);
  cancelBtn.onclick = close;
  goBtn.onclick = async () => {
    // Mask at natural resolution: opaque everywhere, transparent where painted.
    const m = document.createElement("canvas");
    m.width = img.naturalWidth; m.height = img.naturalHeight;
    const mc = m.getContext("2d");
    mc.fillStyle = "#000";
    mc.fillRect(0, 0, m.width, m.height);
    mc.globalCompositeOperation = "destination-out";
    mc.strokeStyle = "#fff";
    mc.lineCap = mc.lineJoin = "round";
    for (const st of strokes) {
      mc.lineWidth = st.r * 2;
      mc.beginPath();
      st.pts.forEach((p, i) => i ? mc.lineTo(p.x, p.y) : mc.moveTo(p.x, p.y));
      if (st.pts.length === 1) mc.lineTo(st.pts[0].x + 0.01, st.pts[0].y);
      mc.stroke();
    }
    const blob = await new Promise(res => m.toBlob(res, "image/png"));
    goBtn.disabled = true;
    // The render runs server-side either way — closing this screen doesn't
    // cancel it, so say so and let the user leave.
    cancelBtn.textContent = "Close — render continues";
    cancelBtn.title = "The repair keeps painting in the background; the new take lands in the takes strip when it finishes.";
    const prov = $("[data-f=prov]", ov);
    const busy = startBusy($("[data-f=busy]", ov),
      `Repairing the painted region with ${prov.options[prov.selectedIndex].text}…`,
      "typically 30–120 seconds — Close or Esc to leave; the result still lands in the takes strip");
    try {
      await onSubmit(blob, instr.value.trim(), prov.value);
      busy.done();
      close();
    } catch (err) {
      busy.done();
      toast(err.message, true);
      cancelBtn.textContent = "Cancel";
      cancelBtn.title = "";
      goBtn.disabled = false;
    }
  };
}

async function cropToReference(source, imgUrl) {
  openCropper(imgUrl, async (rect) => {
    const r = await roleDialog({
      title: "Crop → reference",
      body: "The crop enters the library approved, with this single jurisdiction.",
      prefillHead: "PROP_REFERENCE",
      confirmLabel: "Create reference",
    });
    if (r === null || !r.role) return;
    try {
      const ref = await api("/api/references/crop", {
        method: "POST", json: { source, rect, role: r.role } });
      toast(`${ref.id} created from crop — approved as ${ref.role}.`);
    } catch (err) { toast(err.message, true); }
  });
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Role family name, tolerant of legacy underscore-sanitized records
// ("CHARACTER_LIKENESS_—_JOHN" → "CHARACTER_LIKENESS").
function roleHead(role) {
  return String(role || "").split("—")[0].replace(/[\s_-]+$/, "").trim().toUpperCase();
}

// Roles auto-attached to every render — the four-anchor shelf (ruled
// 2026-08-03): three movie parameters + the board presentation parameter.
// BOARD_LAYOUT_STYLE governs assembly only — it never enters a panel render.
const AUTO_ATTACH_HEADS = ["WORLD_TEXTURE", "COLOR_PALETTE",
                           "CINEMATOGRAPHY_STYLE", "BOARD_RENDERING_STYLE"];

/* The app's own dialog (plan v3 C15) — replaces every browser prompt()/
   confirm(). Resolves to an object of field values on confirm, null on
   cancel/Escape/scrim click. Same endpoints, same rules — only the box
   belongs to the app now. */
const HEXOK = /^#[0-9a-fA-F]{6}$/;

function modal({ title, body = "", fields = [], confirmLabel = "Confirm", danger = false }) {
  return new Promise(resolve => {
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    ov.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-title">${esc(title)}</div>
        ${body ? `<p class="modal-body">${esc(body)}</p>` : ""}
        ${fields.map((f, i) => `
          <label class="modal-field">${esc(f.label)}
            ${f.textarea
              ? `<textarea data-mf="${i}" placeholder="${esc(f.placeholder || "")}">${esc(f.value || "")}</textarea>`
              : f.color
              ? `<span class="mf-color${HEXOK.test((f.value || "").trim()) ? "" : " is-unset"}">
                   <input type="text" data-mf="${i}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}">
                   <input type="color" data-mfc="${i}" value="${HEXOK.test((f.value || "").trim()) ? esc(f.value.trim()) : "#000000"}"
                          title="Pick a colour — the hex beside it follows" aria-label="${esc(f.label)} picker">
                 </span>`
              : `<input type="text" data-mf="${i}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}">`}
            ${f.hint ? `<span class="hint">${esc(f.hint)}</span>` : ""}
          </label>`).join("")}
        <div class="modal-actions">
          <button class="ghost" data-mf="cancel">Cancel</button>
          <button class="${danger ? "danger" : "primary"}" data-mf="ok">${esc(confirmLabel)}</button>
        </div>
      </div>`;
    document.body.append(ov);
    const done = val => { window.removeEventListener("keydown", onKey, true); ov.remove(); resolve(val); };
    const collect = () => Object.fromEntries(
      fields.map((f, i) => [f.name, $(`[data-mf="${i}"]`, ov).value.trim()]));
    // A colour field is two views of ONE value: the hex is what gets
    // collected, the picker is a way to reach it (user 2026-08-06). Each
    // follows the other, and a half-typed hex never resets the picker.
    $$("[data-mfc]", ov).forEach(pick => {
      const txt = $(`[data-mf="${pick.dataset.mfc}"]`, ov);
      const mark = () => pick.closest(".mf-color")
        .classList.toggle("is-unset", !HEXOK.test(txt.value.trim()));
      pick.oninput = () => { txt.value = pick.value.toUpperCase(); mark(); };
      txt.oninput = () => {
        const v = txt.value.trim();
        if (HEXOK.test(v)) pick.value = v;
        mark();
      };
    });
    const onKey = e => {
      if (e.key === "Escape") { e.stopPropagation(); done(null); }
      else if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") { e.preventDefault(); done(collect()); }
    };
    window.addEventListener("keydown", onKey, true);
    ov.addEventListener("mousedown", e => { if (e.target === ov) done(null); });
    $("[data-mf=cancel]", ov).onclick = () => done(null);
    $("[data-mf=ok]", ov).onclick = () => done(collect());
    const first = $("input, textarea", ov);
    (first || $("[data-mf=ok]", ov)).focus();
  });
}
const askConfirm = async (title, body, confirmLabel = "Confirm", danger = false) =>
  (await modal({ title, body, confirmLabel, danger })) !== null;

/* F5 (SETTINGS_FIRST_RUN_PLAN) — the Authenticate modal: icon, name, one
   key field, Test & save, and a deep link to the provider's key page.
   Pasted keys live here now. */
const AUTH_PROVIDERS = {
  openai: { name: "OpenAI", icon: "openai", field: "openai_api_key", test: "openai",
            link: "https://platform.openai.com/api-keys", linkText: "platform.openai.com/api-keys" },
  gemini: { name: "Google Gemini", icon: "gemini-color", field: "gemini_api_key", test: "gemini",
            link: "https://aistudio.google.com/apikey", linkText: "aistudio.google.com/apikey" },
  anthropic: { name: "Anthropic Claude", icon: "claude-color", field: "anthropic_api_key", test: "anthropic",
               link: "https://console.anthropic.com/settings/keys", linkText: "console.anthropic.com/settings/keys" },
  // fal has no dark mark in the icon set — the Courier initials tile is
  // the stated fallback (P3). Its key lands at the connector endpoint,
  // which syncs the catalog as its own proof-of-key.
  fal: { name: "fal.ai", icon: null, connector: "fal",
         link: "https://fal.ai/dashboard/keys", linkText: "fal.ai/dashboard/keys" },
};

function authModal(key) {
  const P = AUTH_PROVIDERS[key];
  if (!P) return;
  // Connector-grammar modal (user ruling 2026-08-04): the modal is the
  // anchor — it never auto-opens anything (the focus-stealing tab read
  // as "no modal appeared"). The provider's console CANNOT be iframed
  // (frame-ancestors DENY on every auth page, by design) and none of
  // these providers offer OAuth-for-API-keys, so the chain states the
  // real steps and the user opens the key page when ready. Save/Test
  // re-render in place — no page reload, ever.
  return new Promise(resolve => {
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    ov.innerHTML = `
      <div class="modal auth-modal" role="dialog" aria-modal="true">
        <div class="auth-head">
          <span class="cred-tile">${P.icon
            ? `<img class="prov-ico" src="/provider-icons/${P.icon}.png" alt="" onerror="this.parentNode.textContent='${esc(P.name.slice(0, 3).toUpperCase())}'">`
            : esc(P.name.slice(0, 3).toUpperCase())}</span>
          <div class="modal-title" style="margin:0">${esc(P.name)}</div>
        </div>
        <div class="fr-chain" style="margin:0 0 14px">
          <span class="fr-chip">OPEN THE KEY PAGE</span><span class="fr-arrow">&rarr;</span>
          <span class="fr-chip">SIGN IN &amp; CREATE A KEY</span><span class="fr-arrow">&rarr;</span>
          <span class="fr-chip">PASTE IT HERE</span>
        </div>
        <p style="margin:0 0 14px"><button class="ghost" data-mf="console">Open ${esc(P.name)}'s key page &nbsp;&#8599;</button></p>
        <label class="modal-field">API key
          <input type="password" data-mf="key" placeholder="paste the key">
        </label>
        ${P.note ? `<p class="wv-tag" style="margin:0 0 12px">${esc(P.note)}</p>` : ""}
        <p class="cred-form-foot" style="margin:0 0 14px">SAVES TO THIS STUDIO ONLY · ${P.test ? "TESTED BEFORE IT COUNTS · " : ""}THE PAGE UPDATES IN PLACE — NO RELOAD</p>
        <div class="modal-actions">
          <button class="ghost" data-mf="cancel">Cancel</button>
          <button class="primary" data-mf="ok">${P.test ? "Test &amp; save" : "Save"}</button>
        </div>
      </div>`;
    document.body.append(ov);
    const done = v => { ov.remove(); resolve(v); };
    $("[data-mf=cancel]", ov).onclick = () => done(null);
    // User-initiated only — the modal keeps focus until YOU reach for
    // the console.
    $("[data-mf=console]", ov).onclick = () =>
      window.open(P.link, "_blank", "noopener");
    ov.addEventListener("mousedown", e => { if (e.target === ov) done(null); });
    $("[data-mf=ok]", ov).onclick = async () => {
      const k = $("[data-mf=key]", ov).value.trim();
      if (!k) return toast("Paste the key first.", true);
      try {
        if (P.connector) {
          const pub = await api(`/api/connectors/${P.connector}/key`, { method: "POST", json: { key: k } });
          toast(pub.status === "SYNCED"
            ? `${pub.label}: ${pub.model_count} models synced.`
            : `${pub.label}: ${pub.status} — ${pub.last_error?.detail || "see the row"}`,
            pub.status !== "SYNCED");
        } else {
          await api("/api/settings", { method: "POST", json: { [P.field]: k } });
          if (P.test) {
            await api("/api/settings/test", { method: "POST", json: { provider: P.test } });
            toast(`${P.name} key saved and tested.`);
          } else {
            toast(`${P.name} key stored.`);
          }
        }
        done(true);
        renderSettings();
      } catch (err) { toast(err.message, true); }
    };
    $("[data-mf=key]", ov).focus();
  });
}

async function addCustomEngineModal() {
  const r = await modal({
    title: "Add your own image engine",
    body: "The endpoint must speak the OpenAI Images API (images.generate / images.edit). The key is stored in settings.json and leaves this machine only to call this endpoint.",
    fields: [
      { name: "label", label: "Name", placeholder: "e.g. local SDXL, studio ComfyUI" },
      { name: "base_url", label: "Base URL", placeholder: "https://api.example.com/v1" },
      { name: "model", label: "Model", placeholder: "the model id this endpoint expects" },
      { name: "api_key", label: "API key" },
    ],
    confirmLabel: "Add engine",
  });
  if (r === null) return;
  try {
    await api("/api/settings/engines", { method: "POST", json: r });
    toast(`${r.label} added — it now appears in every Model dropdown.`);
    renderSettings();
  } catch (err) { toast(err.message, true); }
}

/* F4 — the provider marquee: ~16 tiles, duplicated for a seamless ~36s
   loop, mask-faded at the edges. Icons are the LobeHub static set served
   locally from /provider-icons/ — never hotlinked. */
const MARQUEE_PROVIDERS = [
  // Tile names follow mock 18a (re-exported with SETTINGS_CONTROL_PANEL,
  // 2026-08-05): the developer's name, not the product's.
  ["openai", "OpenAI"], ["claude-color", "Anthropic"], ["gemini-color", "Google"],
  ["meta-color", "Meta"], ["mistral-color", "Mistral"], ["deepseek-color", "DeepSeek"],
  ["qwen-color", "Qwen"], ["xai", "xAI"], ["nvidia-color", "NVIDIA"],
  ["aws-color", "Amazon"], ["cohere-color", "Cohere"], ["perplexity-color", "Perplexity"],
  ["minimax-color", "MiniMax"], ["moonshot", "Moonshot"], ["nousresearch", "Nous"],
  ["liquid", "Liquid"],
];

function buildProviderMarquee(host) {
  if (!host) return;
  const tile = ([slug, name]) =>
    `<span class="mq-tile"><img src="/provider-icons/${slug}.png" alt="" onerror="this.remove()">${esc(name)}</span>`;
  const seq = MARQUEE_PROVIDERS.map(tile).join("");
  host.innerHTML = `<div class="mq-track">${seq}${seq}</div>`;
}

/* Inline rename (PRODUCTIONS_PLAN A5, canonical): a label the user owns is
   renamed in place — the label becomes an input at the same position and
   type size, pre-filled and selected; Enter commits, Esc reverts, blur
   commits. Never a dialog, never a separate edit screen. `save(name)`
   persists and may return the canonical name. */
function inlineRename(el, save) {
  if (el.querySelector("input")) return;
  const current = el.textContent.trim();
  const input = document.createElement("input");
  input.type = "text";
  input.className = "inline-rename";
  input.value = /untitled/i.test(current) ? "" : current;
  input.placeholder = "name this production…";
  el.textContent = "";
  el.append(input);
  input.focus();
  input.select();
  let settled = false;
  const finish = text => {
    if (settled) return;
    settled = true;
    el.textContent = text;
  };
  const commit = async () => {
    const name = input.value.trim();
    if (!name || name === current) return finish(current);
    try { finish((await save(name)) || name); }
    catch (err) { toast(err.message, true); finish(current); }
  };
  input.onkeydown = e => {
    if (e.key === "Escape") finish(current);
    else if (e.key === "Enter") { e.preventDefault(); commit(); }
  };
  input.onblur = commit;
}
async function copyText(text, what = "Prompt") {
  try {
    await navigator.clipboard.writeText(text);
    toast(`${what} copied — ${text.length.toLocaleString()} chars.`);
  } catch {
    toast("Clipboard unavailable — select the text and copy manually.", true);
  }
}

// Reading view (canonical, design review 2026-07-30): the app dialog holding
// one scrollable Courier document with an identity line — a copied prompt
// must not lose its context. For prompts, logs, raw JSON; never for forms.
function promptOverlay(title, text, identity = "") {
  const ov = document.createElement("div");
  ov.className = "modal-scrim";
  ov.innerHTML = `
    <div class="modal prompt-full" role="dialog" aria-modal="true">
      <div class="modal-title">${esc(title)}</div>
      ${identity ? `<div class="reading-id">${esc(identity)}</div>` : ""}
      <pre class="prompt-full-pre">${esc(text)}</pre>
      <div class="modal-actions">
        <button class="ghost" data-mf="copy">Copy</button>
        <button class="primary" data-mf="ok">Close</button>
      </div>
    </div>`;
  document.body.append(ov);
  const done = () => { window.removeEventListener("keydown", onKey, true); ov.remove(); };
  const onKey = e => { if (e.key === "Escape") { e.stopPropagation(); done(); } };
  window.addEventListener("keydown", onKey, true);
  ov.addEventListener("mousedown", e => { if (e.target === ov) done(); });
  $("[data-mf=copy]", ov).onclick = () => copyText(text);
  $("[data-mf=ok]", ov).onclick = done;
  $("[data-mf=ok]", ov).focus();
}

/* Role picker (planning session 2026-07-30): the role vocabulary is finite
   and load-bearing, and every title the user could want already exists in a
   list the app maintains — so the picker offers both instead of a blank box. */
const ROLE_FAMILIES = [
  { head: "SCENE_REFERENCE", desc: "anchors a whole scene or composition — what promotion usually creates", kind: "scene", titled: true },
  { head: "LOCATION_GEOMETRY", desc: "a place's geometry and camera, light excluded — light studies anchor to these", kind: "scene", titled: true },
  { head: "CHARACTER_LIKENESS", desc: "a named character's face and build — never costume or lighting", kind: "CHARACTER", titled: true },
  { head: "VEHICLE_GEOMETRY", desc: "exact vehicle geometry", kind: "VEHICLE", titled: true },
  { head: "PROP_REFERENCE", desc: "a prop or device", kind: "PROP", titled: true },
  { head: "WORLD_TEXTURE", desc: "the world's condition — wear, patina, entropy; auto-attached to every render", kind: "style", titled: false },
  { head: "COLOR_PALETTE", desc: "the film's color language — hue, value key, saturation; auto-attached to every render", kind: "style", titled: false },
  { head: "CINEMATOGRAPHY_STYLE", desc: "light behaviour, lens and framing — never palette; auto-attached to every render", kind: "style", titled: false },
  { head: "BOARD_RENDERING_STYLE", desc: "how boards are PRESENTED — medium and finish only, nothing about the film; auto-attached to every render", kind: "style", titled: false },
  { head: "BOARD_LAYOUT_STYLE", desc: "board assembly grammar — gates Assembly, never enters a panel render", kind: "style", titled: false },
];

// Controls facets are semi-finite per family: seeded as toggle chips,
// free-typing stays possible for odd cases. Notes stay free text — they
// are provenance prose, not vocabulary.
const CONTROL_SUGGESTIONS = {
  CHARACTER_LIKENESS: ["face", "hair", "build", "age"],
  VEHICLE_GEOMETRY: ["proportions", "panels", "stance", "details"],
  PROP_REFERENCE: ["form", "scale", "materials"],
  SCENE_REFERENCE: ["composition", "content", "light", "palette"],
  LOCATION_GEOMETRY: ["geometry", "layout", "camera"],
};

let _roleCtx = null;  // {refs, subjects, locations} — fetched once per session view
async function roleContext() {
  if (_roleCtx) return _roleCtx;
  const [refs, subjects, locs] = await Promise.all([
    api("/api/references").catch(() => []),
    api("/api/subjects").catch(() => []),
    api("/api/screenplay/locations").catch(() => ({ locations: [] })),
  ]);
  return _roleCtx = { refs, subjects, locations: (locs.locations || []).map(l => l.location) };
}

// Suggestions per family: existing groups first (same title = same bench
// checkbox), then canonical names from cast cards / screenplay locations.
function titleSuggestions(head, ctx, extras = []) {
  const fam = ROLE_FAMILIES.find(f => f.head === head);
  const out = [];
  const seen = new Set();
  const add = (value, note) => {
    const v = String(value || "").trim().toUpperCase();
    if (v && !seen.has(v)) { seen.add(v); out.push({ value: v, note }); }
  };
  const groups = {};
  for (const r of ctx.refs) {
    if (roleHead(r.role) !== head) continue;
    const suffix = String(r.role).split("—")[1]?.trim();
    if (suffix) groups[suffix.toUpperCase()] = (groups[suffix.toUpperCase()] || 0) + 1;
  }
  Object.entries(groups).forEach(([t, n]) =>
    add(t, `joins existing group (${n} image${n > 1 ? "s" : ""})`));
  extras.forEach(x => add(x, "from this panel"));
  if (fam && ["CHARACTER", "VEHICLE", "PROP"].includes(fam.kind)) {
    ctx.subjects.filter(s => s.kind === fam.kind)
      .forEach(s => add(s.name, "from cast & subjects"));
  }
  if (fam && fam.kind === "scene") {
    ctx.locations.slice(0, 10).forEach(l => add(l, "from the screenplay"));
  }
  return out.slice(0, 10);
}

/* The role dialog: family dropdown with plain-language jobs, title with
   click-to-fill sourced suggestions, live uppercase, assembled preview.
   Resolves {role, title, ...extra field values} or null. */
function roleDialog({ title, body = "", prefillHead = "SCENE_REFERENCE",
                      prefillTitle = "", extras = [], fields = [],
                      confirmLabel = "Confirm" }) {
  return new Promise(async resolve => {
    const ctx = await roleContext();
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    ov.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-title">${esc(title)}</div>
        ${body ? `<p class="modal-body">${esc(body)}</p>` : ""}
        <label class="modal-field">Role — the single job this image does
          <select data-rf="head">
            ${ROLE_FAMILIES.map(f => `<option value="${f.head}" ${f.head === prefillHead ? "selected" : ""} title="${esc(f.desc)}">${f.head} — ${esc(f.desc.split("—")[0].trim())}</option>`).join("")}
          </select>
        </label>
        <label class="modal-field" data-rf="title-wrap">Title
          <input type="text" data-rf="title" value="${esc(prefillTitle.toUpperCase())}" placeholder="name it after the subject or object so panels pre-check it">
          <span class="role-suggest" data-rf="suggest"></span>
        </label>
        ${fields.map((f, i) => `
          <label class="modal-field">${esc(f.label)}
            ${f.type === "file"
              ? `<input type="file" data-mf="${i}" accept="image/*">`
              : `<input type="text" data-mf="${i}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}">`}
            ${f.name === "controls" ? `<span class="role-suggest" data-rf="ctl-chips"></span>` : ""}
            ${f.hint ? `<span class="hint">${esc(f.hint)}</span>` : ""}
          </label>`).join("")}
        <div class="role-preview" data-rf="preview"></div>
        <div class="modal-actions">
          <button class="ghost" data-mf="cancel">Cancel</button>
          <button class="primary" data-mf="ok">${esc(confirmLabel)}</button>
        </div>
      </div>`;
    document.body.append(ov);
    const headSel = $("[data-rf=head]", ov);
    const titleIn = $("[data-rf=title]", ov);
    const famOf = () => ROLE_FAMILIES.find(f => f.head === headSel.value);
    const assembled = () => {
      const fam = famOf();
      const t = titleIn.value.trim();
      return fam.titled && t ? `${headSel.value} — ${t}` : headSel.value;
    };
    const ctlIdx = fields.findIndex(f => f.name === "controls");
    const syncCtlChips = () => {
      const host = $("[data-rf=ctl-chips]", ov);
      if (!host || ctlIdx < 0) return;
      const input = $(`[data-mf="${ctlIdx}"]`, ov);
      const current = input.value.split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
      // Multi-select facets are .set, never .on — amber fill is reserved
      // for single-choice chips (design review 2026-07-30b).
      host.innerHTML = (CONTROL_SUGGESTIONS[headSel.value] || []).map(cName =>
        `<button type="button" class="vchip${current.includes(cName) ? " set" : ""}" data-ctl="${cName}">${cName}</button>`).join("");
      $$("[data-ctl]", host).forEach(b => {
        b.onclick = () => {
          const tokens = input.value.split(",").map(s => s.trim()).filter(Boolean);
          const i = tokens.findIndex(t => t.toLowerCase() === b.dataset.ctl);
          if (i >= 0) tokens.splice(i, 1); else tokens.push(b.dataset.ctl);
          input.value = tokens.join(", ");
          syncCtlChips();
        };
      });
    };
    const sync = () => {
      const fam = famOf();
      $("[data-rf=title-wrap]", ov).classList.toggle("hidden", !fam.titled);
      $("[data-rf=suggest]", ov).innerHTML = fam.titled
        ? titleSuggestions(headSel.value, ctx, extras).map(s =>
            `<button type="button" class="vchip" data-fill="${esc(s.value)}" title="${esc(s.note)}">${esc(s.value)}</button>`).join("")
        : "";
      $$("[data-fill]", ov).forEach(b => {
        b.onclick = () => { titleIn.value = b.dataset.fill; sync(); };
      });
      syncCtlChips();
      syncPreview();
    };
    // The preview earns its place only when it differs from what was typed —
    // a preview that repeats the input is noise (design review 2026-07-30b).
    const syncPreview = () => {
      const show = famOf().titled && titleIn.value.trim();
      const pv = $("[data-rf=preview]", ov);
      pv.classList.toggle("hidden", !show);
      pv.textContent = show ? assembled() : "";
    };
    if (ctlIdx >= 0) $(`[data-mf="${ctlIdx}"]`, ov)?.addEventListener("input", syncCtlChips);
    titleIn.addEventListener("input", () => {
      const pos = titleIn.selectionStart;
      titleIn.value = titleIn.value.toUpperCase();
      titleIn.setSelectionRange(pos, pos);
      syncPreview();
    });
    headSel.addEventListener("change", sync);
    sync();
    const done = val => { window.removeEventListener("keydown", onKey, true); ov.remove(); resolve(val); };
    const collect = () => {
      const fam = famOf();
      if (fam.titled && !titleIn.value.trim()) { titleIn.focus(); return undefined; }
      const out = { role: assembled(), title: titleIn.value.trim() };
      fields.forEach((f, i) => {
        const el = $(`[data-mf="${i}"]`, ov);
        out[f.name] = f.type === "file" ? (el.files[0] || null) : el.value.trim();
      });
      return out;
    };
    const onKey = e => {
      if (e.key === "Escape") { e.stopPropagation(); done(null); }
      else if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
        e.preventDefault();
        const v = collect(); if (v !== undefined) done(v);
      }
    };
    window.addEventListener("keydown", onKey, true);
    ov.addEventListener("mousedown", e => { if (e.target === ov) done(null); });
    $("[data-mf=cancel]", ov).onclick = () => done(null);
    $("[data-mf=ok]", ov).onclick = () => { const v = collect(); if (v !== undefined) done(v); };
    (famOf().titled ? titleIn : $("[data-mf=ok]", ov)).focus();
  });
}

const askText = async (title, label, opts = {}) => {
  const r = await modal({
    title, body: opts.body || "",
    fields: [{ name: "v", label, value: opts.value || "",
               placeholder: opts.placeholder || "", hint: opts.hint || "" }],
    confirmLabel: opts.confirmLabel || "Confirm", danger: !!opts.danger,
  });
  return r === null ? null : r.v;
};

/* --------------------------------------------------------------- lightbox */

const lb = {
  items: [], index: 0, zoomed: false,
  panX: 0, panY: 0, dragging: false, startX: 0, startY: 0,
};

function openLightbox(items, index = 0) {
  lb.items = items;
  lb.index = index;
  $("#lightbox").classList.remove("hidden");
  lbShow();
}

function closeLightbox() {
  $("#lightbox").classList.add("hidden");
  lb.items = [];
}

function lbShow() {
  const item = lb.items[lb.index];
  if (!item) return;
  lb.zoomed = false; lb.panX = lb.panY = 0;
  const img = $("#lb-img");
  const stage = $(".lb-stage");
  stage.classList.remove("zoomed");
  img.style.transform = "";
  img.src = item.src;
  $("#lb-caption").textContent = `${item.caption}  ·  ${lb.index + 1}/${lb.items.length}`;
  const setZoomLabel = () => {
    $("#lb-zoom").textContent = img.naturalWidth
      ? `${img.naturalWidth}×${img.naturalHeight} — fit (click for 100%)`
      : "";
  };
  img.complete ? setZoomLabel() : (img.onload = setZoomLabel);
  $(".lb-prev").style.visibility = lb.items.length > 1 ? "visible" : "hidden";
  $(".lb-next").style.visibility = lb.items.length > 1 ? "visible" : "hidden";
}

function lbStep(delta) {
  if (lb.items.length < 2) return;
  lb.index = (lb.index + delta + lb.items.length) % lb.items.length;
  lbShow();
}

function lbApplyPan() {
  $("#lb-img").style.transform = `translate(${lb.panX}px, ${lb.panY}px)`;
}

function initLightbox() {
  const box = $("#lightbox");
  const stage = $(".lb-stage", box);
  const img = $("#lb-img");

  $(".lb-close", box).onclick = closeLightbox;
  $(".lb-prev", box).onclick = () => lbStep(-1);
  $(".lb-next", box).onclick = () => lbStep(1);
  box.addEventListener("click", e => { if (e.target === stage) closeLightbox(); });

  img.addEventListener("click", () => {
    if (lb.moved) { lb.moved = false; return; }
    lb.zoomed = !lb.zoomed;
    stage.classList.toggle("zoomed", lb.zoomed);
    if (lb.zoomed) {
      // center the 100% view on the stage
      lb.panX = Math.min(0, (stage.clientWidth - img.naturalWidth) / 2);
      lb.panY = Math.min(0, (stage.clientHeight - img.naturalHeight) / 2);
      lbApplyPan();
      $("#lb-zoom").textContent = `${img.naturalWidth}×${img.naturalHeight} — 100% (drag to pan, click to fit)`;
    } else {
      img.style.transform = "";
      $("#lb-zoom").textContent = `${img.naturalWidth}×${img.naturalHeight} — fit (click for 100%)`;
    }
  });

  img.addEventListener("mousedown", e => {
    if (!lb.zoomed) return;
    e.preventDefault();
    lb.dragging = true;
    lb.moved = false;
    lb.startX = e.clientX - lb.panX;
    lb.startY = e.clientY - lb.panY;
    stage.classList.add("panning");
  });
  window.addEventListener("mousemove", e => {
    if (!lb.dragging) return;
    const nx = e.clientX - lb.startX, ny = e.clientY - lb.startY;
    if (Math.abs(nx - lb.panX) + Math.abs(ny - lb.panY) > 3) lb.moved = true;
    lb.panX = nx; lb.panY = ny;
    lbApplyPan();
  });
  window.addEventListener("mouseup", () => {
    lb.dragging = false;
    stage.classList.remove("panning");
  });

  window.addEventListener("keydown", e => {
    if (box.classList.contains("hidden")) return;
    if (e.key === "Escape") closeLightbox();
    else if (e.key === "ArrowLeft") lbStep(-1);
    else if (e.key === "ArrowRight") lbStep(1);
  });
}

/* ------------------------------------------------------------- navigation */

const views = { status: renderStatus, screenplay: renderScreenplay, wizard: renderWizard,
                references: renderReferences, specs: renderSpecs, boards: renderBoards,
                assembly: renderAssembly, projects: renderProjectsView,
                settings: renderSettings };
const STAGE_ORDER = ["screenplay", "wizard", "specs", "boards", "assembly"];
let activeView = "status";

// A locked stage is a condition, not a destination (LOCKED_STAGE_PLAN
// L1): its cell is inert — no navigation, no view change, no history.
// Clicking it explains in place (L2). Membership is recomputed by
// updateBand on every navigation.
let lockedStages = new Set();
let _bandState = null;  // last /api/state — feeds the popover's gate chain

/* Persistent UI state (user ruling 2026-08-02): every toggle and
   selection survives refresh and view switches. Namespaced per
   production so switching productions keeps each one's workbench as it
   was left. localStorage — device-local working state, not canon. */
let _activeSlug = "";
let _uiState = {};
const _uiKey = () => `sbUI:${_activeSlug}`;
function uiLoad(slug) {
  _activeSlug = slug || "";
  try { _uiState = JSON.parse(localStorage.getItem(_uiKey()) || "{}"); }
  catch { _uiState = {}; }
}
const uiGet = (k, d) => (k in _uiState ? _uiState[k] : d);
function uiSet(k, v) {
  _uiState[k] = v;
  try { localStorage.setItem(_uiKey(), JSON.stringify(_uiState)); } catch { /* full/blocked */ }
}

/* The cached Scene Scan follows the same per-production rule — an
   un-namespaced copy once leaked one film's locations and cast into
   another's Locations table and casting chips. */
function wizACache() {
  try { return JSON.parse(localStorage.getItem(`wizardAnalysis:${_activeSlug}`) || "null"); }
  catch { return null; }
}
function wizACacheSet(a) {
  try { localStorage.setItem(`wizardAnalysis:${_activeSlug}`, JSON.stringify(a)); }
  catch { /* full/blocked */ }
}

/* Page-text overrides (debug tool, user request 2026-08-03): exact-text →
   replacement pairs, install-level on the server, applied to every render.
   Alt-click in text-edit mode rewrites the clicked text via the standard
   modal; "clear" in Settings → Debug tools removes everything. */
let _textOverrides = {};
let _toRaf = 0;
// Server-declared (owner installs only). Until /api/settings has been
// seen this stays false, so nothing debug-shaped ever flashes for
// customers.
let _debugTools = false;
const textEditMode = () =>
  _debugTools && localStorage.getItem("sbTextEdit") === "1";

async function loadTextOverrides() {
  try { _textOverrides = (await api("/api/debug/text-overrides")).overrides || {}; }
  catch { _textOverrides = {}; }
}

function applyTextOverrides(root) {
  if (!Object.keys(_textOverrides).length) return;
  const w = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const trimmed = n.textContent.trim();
    if (trimmed && Object.prototype.hasOwnProperty.call(_textOverrides, trimmed)
        && _textOverrides[trimmed] !== trimmed) {
      n.textContent = n.textContent.replace(trimmed, _textOverrides[trimmed]);
    }
  }
}

// Re-renders happen constantly; re-apply after DOM changes, debounced to a
// frame. Replaced text no longer matches any key, so this cannot loop.
new MutationObserver(() => {
  if (_toRaf) return;
  _toRaf = requestAnimationFrame(() => { _toRaf = 0; applyTextOverrides(); });
}).observe(document.documentElement, { childList: true, subtree: true });

function updateTextEditChip() {
  let chip = document.getElementById("text-edit-chip");
  if (!textEditMode()) { chip?.remove(); return; }
  if (!chip) {
    chip = document.createElement("div");
    chip.id = "text-edit-chip";
    chip.className = "text-edit-chip mono";
    chip.textContent =
      "TEXT EDIT ON — ALT-CLICK ANY TEXT TO REWRITE IT · EXIT IN SETTINGS → DEBUG TOOLS";
    document.body.append(chip);
  }
}

document.addEventListener("click", async e => {
  if (!textEditMode() || !e.altKey) return;
  e.preventDefault();
  e.stopPropagation();
  let node = null;
  const range = document.caretRangeFromPoint?.(e.clientX, e.clientY);
  if (range?.startContainer?.nodeType === Node.TEXT_NODE) node = range.startContainer;
  if (!node?.textContent?.trim()) {
    node = [...(e.target.childNodes || [])]
      .find(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
  }
  const current = node?.textContent.trim();
  if (!current) return toast("No editable text there — Alt-click directly on words.", true);
  // If this text is already a rewrite, edit against its ORIGINAL so one
  // key per string exists and "clear" restores cleanly.
  const key = Object.keys(_textOverrides)
    .find(k => _textOverrides[k] === current) || current;
  const vals = await modal({
    title: "Rewrite page text",
    body: "Applies everywhere this exact text appears and survives refresh. "
          + "Workbench copy on this install only — never production data.",
    fields: [{ name: "text", label: "Text", textarea: true, value: current }],
    confirmLabel: "Rewrite",
  });
  if (vals === null) return;
  const next = vals.text;
  if (!next || next === key) delete _textOverrides[key];
  else _textOverrides[key] = next;
  try {
    await api("/api/debug/text-overrides", { method: "PUT",
      json: { overrides: _textOverrides } });
    if (node && node.textContent.trim() === current) {
      node.textContent = node.textContent.replace(current, next || key);
    }
    applyTextOverrides();
    toast(next && next !== key ? "Text rewritten — applies everywhere it appears."
                               : "Rewrite removed — original text restored on next render.");
  } catch (err) { toast(err.message, true); }
}, true);

for (const navSel of ["#nav", "#tools-nav"]) {
  $(navSel).addEventListener("click", e => {
    const btn = e.target.closest("button[data-view]");
    if (!btn) return;
    const view = btn.dataset.view;
    if (lockedStages.has(view)) {
      // Never refuse on a stale lock (user-caught 2026-08-01: approve
      // didn't refresh the band, and inert clicks could never heal it).
      updateBand().then(() => {
        if (lockedStages.has(view)) lockPopover(view);
        else showView(view);
      });
      return;
    }
    showView(view);
  });
}

/* The gate chain (LOCKED_STAGE_PLAN L2/L3): every step between here and a
   stage unlocking, driven from real state so completed steps drop off as
   they are done. One model feeds the band popover and the stage
   checklist. The look interview leaves no server trace until the bible
   is drafted, so it completes with the bible — the movable steps (scan,
   anchors, bible) all track live state. */
function gateChain(state) {
  const ss = state.stage_summary || {};
  const pd = ss.production_design || {};
  return [
    { label: "UPLOAD THE SCREENPLAY", verb: "Upload the screenplay", done: !!ss.screenplay, stage: "screenplay",
      sub: "The read starts here — everything downstream derives from the draft" },
    { label: "RUN THE SCRIPT SCAN", verb: "Run the script scan", done: !!pd.scan_done, stage: "wizard",
      sub: "Reads the draft for design languages, environments, locations and cast" },
    { label: "ADD STYLE REFERENCE", verb: "Add style reference", done: (pd.style_anchors || 0) > 0, stage: "wizard",
      sub: "Board layout, cinematography and rendering plates — the three anchors" },
    { label: "COMPLETE THE LOOK INTERVIEW", verb: "Complete the look interview",
      done: (pd.interview_answered || 0) > 0 || !!pd.bible_saved,
      optional: true, stage: "wizard",
      sub: "Optional — touchstones, medium, palette; blanks come back marked PROPOSED" },
    { label: "DRAFT THE ART DIRECTION BIBLE", verb: "Draft the Art Direction Bible", done: !!pd.bible_saved, stage: "wizard",
      sub: "Everything above becomes the document every render obeys" },
    { label: "DRAFT & LOCK A BREAKDOWN", verb: "Draft & lock a breakdown", done: (ss.breakdowns?.locked || 0) > 0, stage: "specs",
      sub: "Only a locked sheet can render" },
    { label: "RENDER AND APPROVE PANELS", verb: "Render and approve panels", done: (ss.panels?.approved || 0) > 0, stage: "boards",
      sub: "Takes are judged full-size, one at a time" },
  ];
}

const STAGE_NUM = { screenplay: "01", wizard: "02", specs: "03", boards: "04", assembly: "05" };
// How much of the chain each stage's gate requires.
const UNLOCK_NEED = { specs: 5, boards: 6, assembly: 7 };
const UNLOCK_LINE = { specs: "THE MOMENT THE BIBLE IS SAVED",
                     boards: "THE MOMENT A SHEET LOCKS",
                     assembly: "THE MOMENT A PANEL IS APPROVED" };
const NEED_SENTENCE = { specs: "Breakdowns need the Art Direction Bible.",
                       boards: "Panels need a locked breakdown sheet.",
                       assembly: "Boards need approved panels." };
const COUNT_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven"];

/* Clicking a locked stage explains, in place (L2): a popover anchored
   under the FIRST UNMET stage's cell — the cell the user actually needs —
   while the view behind stays exactly where it was. */
function lockPopover(stage) {
  $$(".band-pop").forEach(p => p.remove());
  if (!_bandState) return;
  const chain = gateChain(_bandState).slice(0, UNLOCK_NEED[stage] || 5);
  const remaining = chain.filter(s => !s.done);
  const required = remaining.filter(s => !s.optional);
  if (!required.length) { updateBand(); showView(stage); return; }  // stale — heal and go
  const cell = $(`#nav button[data-view="${remaining[0].stage}"]`)
            || $(`#nav button[data-view="${stage}"]`);
  const nav = $("#nav");
  const pop = document.createElement("div");
  pop.className = "band-pop";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", `Stage ${STAGE_NUM[stage]} is locked`);
  const n = required.length;
  pop.innerHTML = `
    <div class="bp-head">
      <span class="bp-chip mono">${STAGE_NUM[stage]} IS LOCKED</span>
      <button class="bp-x" title="Dismiss (Esc)">×</button>
    </div>
    <p class="bp-sent">${esc(NEED_SENTENCE[stage] || "This stage's gate is upstream.")}
      <b>${COUNT_WORDS[n] || n} step${n === 1 ? "" : "s"} first.</b></p>
    <div class="bp-steps mono">
      ${remaining.map(s => `
        <div class="bp-step ${s === required[0] ? "cur" : ""}">
          <span class="bp-mark">${s === required[0] ? "→" : "·"}</span>
          <span>${esc(s.label)}${s.optional ? " · OPTIONAL" : ""}</span>
        </div>`).join("")}
    </div>
    <div class="bp-foot mono">${STAGE_NUM[stage]} UNLOCKS ITSELF ${UNLOCK_LINE[stage] || ""}</div>`;
  // Fixed positioning: the band is sticky, so the popover pins to the
  // viewport and stays attached through scrolling.
  const nr = nav.getBoundingClientRect(), cr = cell.getBoundingClientRect();
  pop.style.left = `${Math.round(cr.left)}px`;
  pop.style.top = `${Math.round(nr.bottom)}px`;
  pop.style.width = `${Math.round(Math.min(cr.width * 2, window.innerWidth - cr.left - 24))}px`;
  document.body.appendChild(pop);
  const close = () => {
    pop.remove();
    window.removeEventListener("keydown", onKey, true);
    document.removeEventListener("mousedown", onOut, true);
  };
  const onKey = e => { if (e.key === "Escape") { e.stopPropagation(); close(); } };
  const onOut = e => { if (!e.target.closest(".band-pop")) close(); };
  window.addEventListener("keydown", onKey, true);
  setTimeout(() => document.addEventListener("mousedown", onOut, true));
  $(".bp-x", pop).onclick = close;
}

/* The stage checklist (LOCKED_STAGE_PLAN L4, mock 12c): one bordered
   list where each unfinished row IS the link — its verb, what it does,
   and its address. Done rows collapse to a ✓ line; the current row gets
   the amber border. No generic navigation button anywhere — the rows
   are the navigation. One component for any stage's empty state. */
function stageChecklist({ kicker, headline, rows, footnote }) {
  return `
    <div class="stage-check">
      <div class="fact-head">${esc(kicker)}</div>
      <h2 class="sc-headline">${headline}</h2>
      <div class="sc-list">
        ${rows.map(r => {
          if (r.state === "done") return `
            <div class="sc-row done"><span class="sc-mark">✓</span>
              <span class="sc-label">${esc(r.verb || r.label)}</span>
              <span class="sc-addr mono">${esc(r.addr || "")} · DONE</span></div>`;
          if (r.state === "info") return `
            <div class="sc-row info"><span class="sc-mark">·</span>
              <span class="sc-label">${esc(r.verb || r.label)}</span>
              <span class="sc-addr mono">NO ACTION NEEDED</span></div>`;
          return `
            <button class="sc-row ${r.state}" data-stage="${esc(r.stage || "")}">
              <span class="sc-mark">${r.state === "cur" ? "→" : "·"}</span>
              <span class="sc-main"><span class="sc-label">${esc(r.verb || r.label)}</span>
                ${r.sub ? `<span class="sc-sub">${esc(r.sub)}</span>` : ""}</span>
              <span class="sc-addr mono">${esc(r.addr || "")} ↗</span>
            </button>`;
        }).join("")}
      </div>
      ${footnote ? `<div class="sc-foot mono">${esc(footnote)}</div>` : ""}
    </div>`;
}

function checklistRows(state, upTo) {
  const chain = gateChain(state).slice(0, upTo);
  // The pointer lands on the first REQUIRED undone step — optional ones
  // (the interview) list plainly but never read as the blocker.
  const cur = chain.findIndex(s => !s.done && !s.optional);
  return chain.map((s, i) => ({
    ...s, addr: `STAGE ${STAGE_NUM[s.stage]}${s.optional && !s.done ? " · OPTIONAL" : ""}`,
    state: s.done ? "done" : i === cur ? "cur" : "todo",
  }));
}

function bindStageChecklist(host) {
  $$(".sc-row[data-stage]", host).forEach(b => {
    if (b.dataset.stage) b.onclick = () => showView(b.dataset.stage);
  });
}

function useTemplate(id) {
  const main = $("#main");
  main.replaceChildren($(`#${id}`).content.cloneNode(true));
  return main;
}

/* Model selectors state their gate (user ruling 2026-08-01): only engines
   with a configured key are listed; with none, the selector itself says
   so instead of offering models that cannot run. Returns whether any
   engine is ready.

   C7 (CONNECTORS_UI_PLAN): enabled connector models join every selector,
   grouped by capability (never by seller); each option states refs,
   ceiling and price — a name is not enough. A failing connector's models
   STAY listed and fail loudly at render — never a silent substitution.
   A search button beside the select opens the picker (search the enabled
   set first, escalate the same query to the full catalog). */

// Per-engine facts for the point of choice. Built-ins are known; the
// rest reads from provider_meta. Nothing invented: unknown ceiling reads
// as nothing rather than a guess.
function engineFacts(pid, s) {
  const m = s.provider_meta?.[pid] || {};
  if (pid === "gemini") return { refs: true, maxPx: 3840, price: null, facts: "REFS ≤14 · 4K NATIVE" };
  if (pid === "openai") return { refs: true, maxPx: 2560, price: null, facts: "REFS ≤14 · 2.5K MAX" };
  if (pid === "openai-chat") return { refs: true, maxPx: 1536, price: null, facts: "REFS ≤14 · 1.5K PRESET CAP" };
  if (pid === "mock") return { refs: true, maxPx: 3840, price: "0", facts: "DEBUG DRY-RUN · NO COST" };
  if (pid.startsWith("custom:")) return { refs: true, maxPx: null, price: null, facts: "YOUR ENDPOINT" };
  const bits = [m.refs ? "REFS ≤14" : "NO REFERENCES"];
  if ((m.max_px || 0) >= 3840) bits.push("4K NATIVE");
  else if (m.max_px) bits.push(`${m.max_px >= 2048 ? "2K" : "1K"} MAX`);
  if (m.price) bits.push(`$${m.price}/IMG`);
  else bits.push("PRICE NOT PUBLISHED");
  bits.push(`VIA ${(m.connector || "").toUpperCase()}`);
  return { refs: !!m.refs, maxPx: m.max_px || null, price: m.price || null,
           facts: bits.join(" · ") };
}

/* R16 (CANONIZATION_PASS): the mock engine is reachable but never a
   peer of a paid engine — in every dropdown it renders LAST, after a
   disabled Courier divider, in --ink-faint. */
const MOCK_OPT = s => (s.engines || {}).mock?.configured
  ? `<option disabled class="opt-debug">&mdash; DEBUG &mdash;</option>`
    + `<option value="mock" class="opt-debug">MOCK ENGINE &middot; no cost</option>`
  : "";

/* Research passes (Scene Scan, breakdown draft, bible draft) list
   NARRATIVE homes only — never image engines. The connectors rewrite let
   or:/fal: image ids leak into these selects, where every pick was a
   server-side 422 (F6 fix, 2026-08-04). */
async function fillNarrativeSelect(sel) {
  if (!sel) return false;
  let s = {};
  try { s = await api("/api/settings"); } catch { /* stated below */ }
  const eng = s.engines || {};
  const usable = [], failed = [];
  const put = (id, label) =>
    (eng[id]?.last_test?.ok === false ? failed : usable).push([id, label]);
  if (eng.gemini?.configured) put("gemini", "Gemini (research pass)");
  if (eng.openai?.configured)
    put("openai", `ChatGPT — ${s.openai_chat_model || s.openai_chat_model_default || "gpt-5.6"}`);
  if (eng.anthropic?.configured)
    put("anthropic", `Anthropic — ${s.anthropic_model || "Claude"}`);
  if (s.openrouter_narrative_ready)
    usable.push(["openrouter", `OpenRouter — ${s.openrouter_narrative_model}`]);
  if (!usable.length && eng.mock?.configured) {
    // Only the debug engine exists: it may serve, quarantined, alone.
    sel.disabled = false;
    sel.innerHTML = MOCK_OPT(s);
    sel.value = "mock";
    return true;
  }
  if (!usable.length) {
    sel.innerHTML = failed.length
      ? `<option value="">KEY FAILED ITS TEST — RETEST IN SETTINGS</option>`
      : `<option value="">NO NARRATIVE MODEL — ADD A KEY OR CONNECT OPENROUTER</option>`;
    sel.disabled = true;
    sel.title = failed.length
      ? "Every configured key failed its last test — retest or replace it in Settings."
      : "Narrative passes need an OpenAI, Gemini or Anthropic key, or the OpenRouter connection.";
    return false;
  }
  const prev = sel.value;
  sel.disabled = false;
  sel.innerHTML = usable.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("")
    + failed.map(([v, l]) =>
      `<option value="${esc(v)}" disabled>${esc(l)} — KEY FAILED ITS TEST</option>`).join("")
    + MOCK_OPT(s);
  if (prev && (usable.some(([v]) => v === prev) || prev === "mock")) sel.value = prev;
  else if (usable.some(([v]) => v === s.narrative_provider))
    sel.value = s.narrative_provider;  // the Settings role is the default
  return true;
}

async function fillProviderSelect(sel, labels) {
  if (!sel) return false;
  let s = {};
  try { s = await api("/api/settings"); } catch { /* stated below */ }
  const eng = s.engines || {};
  const usable = [], failed = [];
  for (const pid of Object.keys(s.providers || {})) {
    if (pid === "mock") continue;  // R16: quarantined to the debug tail
    if (pid.startsWith("or:") || pid.startsWith("fal:")) {
      usable.push(pid);  // stays listed; a dead key fails loudly at render
      continue;
    }
    const e = eng[pid];
    if (!e?.configured) continue;
    (e.last_test?.ok === false ? failed : usable).push(pid);
  }
  if (!usable.length && eng.mock?.configured) {
    sel.disabled = false;
    sel.innerHTML = MOCK_OPT(s);
    sel.value = "mock";
    return true;
  }
  if (!usable.length) {
    sel.innerHTML = failed.length
      ? `<option value="">KEY FAILED ITS TEST — RETEST IN SETTINGS</option>`
      : `<option value="">NO ENGINE CONFIGURED — ADD A KEY IN SETTINGS</option>`;
    sel.disabled = true;
    sel.title = failed.length
      ? "Every configured key failed its last test — retest or replace it in Settings."
      : "Every model action needs a key or connector — add one in Settings.";
    return false;
  }
  const prev = sel.value;
  sel.disabled = false;
  const opt = pid => {
    const f = engineFacts(pid, s);
    return `<option value="${esc(pid)}">${esc(s.providers[pid])} — ${esc(f.facts)}</option>`;
  };
  const anchors = usable.filter(pid => engineFacts(pid, s).refs);
  const styleOnly = usable.filter(pid => !engineFacts(pid, s).refs);
  sel.innerHTML =
    (anchors.length ? `<optgroup label="ANCHORS REFERENCES">${anchors.map(opt).join("")}</optgroup>` : "")
    + (styleOnly.length ? `<optgroup label="STYLE STUDIES ONLY">${styleOnly.map(opt).join("")}</optgroup>` : "")
    + failed.map(pid =>
      `<option value="${esc(pid)}" disabled>${esc(s.providers[pid])} — KEY FAILED ITS TEST</option>`).join("")
    + MOCK_OPT(s);
  if (prev && (usable.includes(prev) || prev === "mock")) sel.value = prev;
  else if (usable.includes(s.preferred_provider)) sel.value = s.preferred_provider;
  else if (s.preferred_provider === "mock" && (s.engines || {}).mock?.configured)
    sel.value = "mock";
  // The picker button rides beside every model select, once.
  if (!sel._sbPicker) {
    sel._sbPicker = true;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "picker-open";
    btn.title = "Search engines — the enabled set first, then the full catalog";
    btn.textContent = "⌕";
    sel.after(btn);
    btn.onclick = () => openEnginePicker(sel, s);
  }
  return true;
}

/* The engine picker (mock 16e): search at the top, capability on every
   row, escalation to the full catalog as the last row. Three rules: a
   name is not enough; the limit that bites is amber at the point of
   choice; never a silent substitution. */
async function openEnginePicker(sel, s) {
  document.getElementById("engine-picker")?.remove();
  const enabled = Array.from(sel.options).filter(o => !o.disabled && o.value)
    .map(o => o.value);
  const panel = document.createElement("div");
  panel.id = "engine-picker";
  const r = sel.getBoundingClientRect();
  panel.style.left = `${Math.max(8, Math.min(r.left, innerWidth - 420))}px`;
  panel.style.top = `${Math.min(r.bottom + 6, innerHeight - 440)}px`;
  document.body.append(panel);
  const state = { q: "", refs: false, fourk: false, cheap: false, server: null };

  const rowHtml = (pid, label, f, fromCatalog) => `
    <button class="pick-row${sel.value === pid ? " cur" : ""}" data-pid="${esc(pid)}"${fromCatalog ? ` data-cat="1"` : ""}>
      <span class="pick-name">${esc(label)}</span>
      <span class="pick-facts">${f.facts.split(" · ").map(x =>
        /MAX|PRESET CAP/.test(x) && !/4K/.test(x)
          ? `<i class="pf-amber">${esc(x)}</i>` : esc(x)).join(" · ")}</span>
    </button>`;

  const draw = async () => {
    let list = enabled.filter(pid => {
      const f = engineFacts(pid, s);
      if (state.refs && !f.refs) return false;
      if (state.fourk && (f.maxPx || 0) < 3840) return false;
      if (state.q && !`${s.providers[pid]} ${pid}`.toLowerCase().includes(state.q.toLowerCase())) return false;
      return true;
    });
    if (state.cheap) list = [...list].sort((a, b) => {
      const pa = parseFloat(engineFacts(a, s).price ?? "999"),
            pb = parseFloat(engineFacts(b, s).price ?? "999");
      return pa - pb;
    });
    const groups = [
      ["ANCHORS REFERENCES", list.filter(p => engineFacts(p, s).refs)],
      ["STYLE STUDIES ONLY", list.filter(p => !engineFacts(p, s).refs)],
    ];
    let serverRows = "";
    if (state.server?.length) {
      serverRows = `<p class="pick-group">FROM THE FULL CATALOG · ${state.server.length}</p>`
        + state.server.map(m => {
          const f = { facts: [m.refs ? `REFS ≤${m.max_refs}` : "NO REFERENCES",
                              m.price_per_image ? `$${m.price_per_image}/IMG` : "PRICE NOT PUBLISHED",
                              `VIA ${m.connector.toUpperCase()}`].join(" · ") };
          return rowHtml(m.id, m.label, f, true);
        }).join("");
    }
    panel.innerHTML = `
      <div class="pick-search">
        <input id="pick-q" placeholder="Search engines…" value="${esc(state.q)}">
        <span class="pick-count">${list.length} OF ${enabled.length}</span>
      </div>
      <div class="pick-chips">
        <button class="pchip${state.refs ? " on" : ""}" data-c="refs">ANCHORS REFS</button>
        <button class="pchip${state.fourk ? " on" : ""}" data-c="fourk">4K</button>
        <button class="pchip${state.cheap ? " on" : ""}" data-c="cheap">CHEAPEST</button>
      </div>
      <div class="pick-list">
        ${groups.map(([t, rows]) => rows.length
          ? `<p class="pick-group">${t} · ${rows.length}</p>`
            + rows.map(pid => rowHtml(pid, s.providers[pid], engineFacts(pid, s), false)).join("")
          : "").join("")}
        ${serverRows}
        ${!list.length && !state.server?.length
          ? `<p class="pick-none">Nothing in your enabled set matches.</p>` : ""}
      </div>
      <div class="pick-foot">
        <span class="pick-scope">${state.server ? "SEARCHED ENABLED + FULL CATALOG" : "SEARCHING ENABLED MODELS"}</span>
        ${state.q && !state.server ? `<button class="text-act" id="pick-all">Search the full catalog</button>` : ""}
      </div>`;
    const q = panel.querySelector("#pick-q");
    q.focus(); q.setSelectionRange(q.value.length, q.value.length);
    q.oninput = e => { state.q = e.target.value; state.server = null; draw(); };
    panel.querySelectorAll(".pchip").forEach(c => {
      c.onclick = () => { state[c.dataset.c] = !state[c.dataset.c]; draw(); };
    });
    panel.querySelector("#pick-all")?.addEventListener("click", async () => {
      try {
        const out = await api(`/api/connectors/catalog?q=${encodeURIComponent(state.q)}&scope=all`);
        const have = new Set(enabled);
        state.server = out.records.filter(m => !have.has(m.id) && m.supported);
        state._searched = out.searched;
      } catch (err) { toast(err.message, true); state.server = []; }
      draw();
    });
    panel.querySelectorAll(".pick-row").forEach(rowBtn => {
      rowBtn.onclick = async () => {
        const pid = rowBtn.dataset.pid;
        if (rowBtn.dataset.cat) {
          // Enable-and-select without leaving the panel.
          const m = state.server.find(x => x.id === pid);
          try {
            await api("/api/connectors/enable", { method: "POST",
              json: { id: pid, on: true, record: m } });
            const o = document.createElement("option");
            o.value = pid; o.textContent = `${m.label} — via ${m.connector}`;
            sel.append(o);
            toast(`${m.label} enabled and selected.`);
          } catch (err) { toast(err.message, true); return; }
        }
        sel.value = pid;
        sel.dispatchEvent(new Event("change", { bubbles: true }));
        panel.remove();
      };
    });
  };
  await draw();
  setTimeout(() => document.addEventListener("click", e => {
    if (!panel.contains(e.target)) panel.remove();
  }, { once: true, capture: true }));
}

// The selector's visible label — busy meters say which model is running.
const selectedModelLabel = sel =>
  sel?.selectedOptions?.[0]?.textContent?.trim() || "the selected model";

async function showView(name) {
  // Own keys only — #toString would otherwise "exist" via the prototype,
  // dispatch garbage, and persist a view name that renders nothing.
  if (!Object.hasOwn(views, name)) name = "status";
  // BAND_CONDENSE B2: tools are not stages — the band condenses while a
  // tool view is open. Keyed here in the one router chokepoint, so boot
  // restores (persistent UI state) and both nav bars stay in sync free.
  document.body.classList.toggle("tool-mode",
    ["status", "references", "projects", "settings"].includes(name));
  activeView = name;
  uiSet("view", name);
  _roleCtx = null;  // suggestion sources refresh per navigation
  $$("#tools-nav button").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  updateBand();  // fire and forget — the band must never block the view
  try { await views[name](); }
  catch (err) { toast(err.message, true); }
}

/* The band is the pipeline's state, refreshed on every navigation:
   subline per stage from stage_summary, top border --ok complete /
   --accent current / --bad blocked / --line not reached, HERE on the
   viewed stage, engine dots from credentials. */
async function updateBand() {
  let state, settings;
  try {
    [state, settings] = await Promise.all([api("/api/state"), api("/api/settings")]);
  } catch { return; }

  $("#brand-project").textContent = (state.project || "").toUpperCase();

  _debugTools = !!settings.debug_tools;
  updateTextEditChip();

  // A long-lived tab is a time capsule: the SPA re-renders from in-memory
  // JS while the studio updates beneath it (user-hit three times,
  // 2026-08-05). Every navigation compares the server's version to the
  // one this tab booted with; a mismatch is STATED, never auto-reloaded —
  // reloading is the user's act, mid-work.
  api("/api/healthz").then(h => {
    const boot = window.SB_BOOT_VERSION;
    const stale = boot && h.version && h.version !== boot;
    let bar = document.getElementById("update-bar");
    if (!stale) { bar?.remove(); return; }
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "update-bar";
      bar.className = "update-bar mono";
      bar.innerHTML = `THIS TAB IS ON ${esc(boot)} — THE STUDIO NOW SERVES ${esc(h.version)}. `
        + `<button class="text-act mono" onclick="location.reload()">RELOAD TO GET IT</button>`;
      // D8 ruling: below the band — the product's map is not pushed down
      // for a condition that is not about the production.
      const nav = document.querySelector("nav#nav");
      if (nav) {
        nav.insertAdjacentElement("afterend", bar);
        bar.style.top = `${nav.offsetHeight}px`;
      } else {
        document.body.prepend(bar);
      }
    }
  }).catch(() => {});

  // C8 — one square per ROLE, not per provider: can this app do its two
  // jobs right now? Worst state among everything each role needs.
  const roles = settings.roles || {};
  const ROLE_TITLES = {
    ok: "OK", warn: "DEGRADED — STILL RUNS",
    bad: "BLOCKED", none: "NOT CONFIGURED",
  };
  $("#engine-dots").innerHTML = [
    ["narrative", "NARRATIVE", "Narrative & content evaluation"],
    ["image", "IMAGE", "Image generation"],
  ].map(([k, lab, full]) => {
    const st = roles[k] || "none";
    return `<span class="edot ${st}" title="${esc(full)} — ${ROLE_TITLES[st]}. Configure in Settings → AI & engines."><i></i>${lab}</span>`;
  }).join("");

  // R7 (CANONIZATION_PASS): notification = ONE filled square dot in the
  // severity color — --bad for errors, --hold for holds. Two conditions
  // never stack; the worse one wins.
  api("/api/activity?limit=10").then(rows => {
    const btn = $('#tools-nav button[data-view="status"]');
    if (!btn) return;
    const err = rows.some(r => r.kind === "error");
    const hold = (state.blocking || []).some(b => b.kind === "HOLD");
    btn.classList.toggle("has-err", err);
    btn.classList.toggle("has-hold", !err && hold);
  }).catch(() => {});

  const ss = state.stage_summary || {};
  const pd = ss.production_design || {}, bd = ss.breakdowns || {},
        pn = ss.panels || {}, bo = ss.boards || {};
  const subs = {
    screenplay: ss.screenplay ? ss.screenplay.file : "not uploaded",
    wizard: pd.bible_saved
      ? `Bible rev ${pd.bible_rev} · ${pd.style_anchors} anchor${pd.style_anchors === 1 ? "" : "s"}`
      : "no bible yet",
    specs: (bd.locked || bd.drafts)
      ? `${bd.locked} locked · ${bd.drafts} draft${bd.drafts === 1 ? "" : "s"}${bd.blocked ? ` · ${bd.blocked} blocked` : ""}`
      : "no sheets yet",
    boards: pn.candidates ? `${pn.approved} approved of ${pn.candidates}` : "no candidates yet",
    assembly: bo.assembled
      ? `${bo.assembled} assembled${bo.approved ? ` · ${bo.approved} approved` : ""}`
      : "none assembled",
  };
  const complete = {
    screenplay: !!ss.screenplay,
    wizard: !!pd.bible_saved,
    specs: (bd.locked || 0) > 0,
    boards: (bo.assembled || 0) > 0,
    assembly: (bo.approved || 0) > 0,
  };
  const BLOCK_STAGE = { dashboard: "screenplay", references: "wizard", wizard: "wizard",
                        specs: "specs", boards: "boards" };
  const blocked = new Set((state.blocking || [])
    .filter(b => b.kind !== "CARE")  // advisories never mark a stage blocked
    .map(b => b.kind === "CITE" ? "screenplay" : BLOCK_STAGE[b.action] || "specs"));
  const frontier = STAGE_ORDER.find(s => !complete[s]) || "assembly";

  // Everything past the frontier has an unmet gate and is inert (L1) —
  // 04 and 05 lock just like 03; the frontier itself is where you work.
  _bandState = state;
  const frontierIdx = STAGE_ORDER.indexOf(frontier);
  lockedStages = new Set(STAGE_ORDER.filter((s, i) => i > frontierIdx));

  for (const stage of STAGE_ORDER) {
    const btn = $(`#nav button[data-view="${stage}"]`);
    if (!btn) continue;
    $(".stage-sub", btn).textContent = subs[stage] || "";
    const isHere = activeView === stage;
    const isCurrent = isHere || (!STAGE_ORDER.includes(activeView) && stage === frontier && !isHere);
    const isLocked = lockedStages.has(stage);
    btn.classList.toggle("here", isHere);
    btn.classList.toggle("s-cur", isCurrent);
    btn.classList.toggle("s-bad", !isCurrent && blocked.has(stage));
    btn.classList.toggle("s-ok", !isCurrent && !blocked.has(stage) && complete[stage]);
    btn.classList.toggle("s-locked", isLocked);
    // Focusable stays true — keyboard users get the same explanation.
    btn.setAttribute("aria-disabled", isLocked ? "true" : "false");
  }
}

/* -------------------------------------------------------------- dashboard */

const BLOCK_VERBS = { HOLD: "Review", GAP: "Add", SIZE: "Regenerate", CITE: "Review", CARE: "Backup" };
const BLOCK_SUPPORT = {
  HOLD: "Held rows on required objects block the lock — read each cited source, then pass or cut the row.",
  GAP: "A missing input upstream stops generation downstream.",
  SIZE: "Nothing is ever blown up — regenerate the panel at a larger size.",
  CITE: "The current draft no longer contains quotes this sheet cites — review the flagged rows.",
};

// Gate stated before it is hit (user ruling 2026-08-01): a breakdown draws
// its rendering language, environments and subjects from the bible, so
// Create Breakdown never appears before Production Design is complete —
// a de-emphasized tag states the unmet condition instead.
const PD_LOCK_TAG = `<span class="pd-lock mono" title="Breakdowns draw their rendering language, environments and subjects from the Art Direction Bible — complete Production Design first.">COMPLETE PRODUCTION DESIGN</span>`;

// Machine IDs inside prose render in Courier (design system: data vs voice).
const monoIds = safeText => safeText.replace(
  /\b((?:CAND|REF|BOARD|OBJ)-\d+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|P\d{2})\b/g,
  '<span class="mono-id">$1</span>');

async function renderStatus() {
  useTemplate("tpl-status");
  const [state, recent] = await Promise.all([
    api("/api/state"),
    api("/api/activity?limit=8").catch(() => []),
  ]);

  const specCounts = { APPROVED: 0, DRAFT: 0, REVIEWED: 0, REJECTED: 0 };
  state.specs.forEach(s => { specCounts[s.status] = (specCounts[s.status] || 0) + 1; });

  $("#dash-cards").innerHTML = [
    ["Approved references", state.references.approved],
    ["Provisional references", state.references.provisional],
    ["Approved specs", specCounts.APPROVED],
    ["Draft specs", specCounts.DRAFT + (specCounts.REVIEWED || 0)],
  ].map(([lbl, num]) => `<div class="card"><div class="num">${num}</div><div class="lbl">${lbl}</div></div>`).join("");

  // The lead is a presentation of the first BLOCKER — advisories are never
  // promoted (review 2026-08-01 §9). With nothing blocking, it carries the
  // next stage verb instead.
  const blockers = state.blocking.filter(b => b.kind !== "CARE");
  const advisories = state.blocking.filter(b => b.kind === "CARE");
  const first = blockers[0];
  const next = state.next || { text: "Upload the screenplay", action: "screenplay" };
  const action = next.action === "dashboard" ? "screenplay" : next.action;
  const lead = $("#dash-next");
  if (!state.screenplay) {
    // The verb IS the form (user ruling 2026-08-01): never a button whose
    // only job is to reach another button. The upload happens right here;
    // the side column and the blocking list stay untouched.
    lead.innerHTML = `
      <div class="next-label">DO THIS NEXT</div>
      <div class="next-text">Upload the screenplay</div>
      <p class="next-support">The read starts here: every location, cast
      member, design language and open question comes out of this one
      file. Nothing downstream unlocks without it.</p>
      <form id="status-screenplay-form" class="row" style="margin-top:10px">
        <input type="file" accept=".pdf,.fdx,.txt,.fountain" required>
        <button type="submit" class="primary">Upload &amp; start the read</button>
      </form>
      <p class="mini">PDF · FDX · FOUNTAIN · TXT</p>`;
    bindScreenplayUpload($("#status-screenplay-form"));
  } else {
    lead.innerHTML = `
      <div class="next-label">DO THIS NEXT</div>
      <div class="next-row">
        <div style="flex:1;min-width:0">
          <div class="next-text">${monoIds(esc(next.text))}</div>
          <p class="next-support">${esc(first ? BLOCK_SUPPORT[first.kind] || "" :
            "Everything upstream is satisfied.")}</p>
        </div>
        <button class="primary" data-f="go">${esc(first ? BLOCK_VERBS[first.kind] || "Open" : "Open")}</button>
      </div>`;
    $("[data-f=go]", lead).onclick = () => showView(action);
  }

  // Everything that stops the next render, as structured rows (kind badge,
  // text, resolving jump). The panel hides entirely when nothing blocks.
  const blocking = $("#dash-missing");
  if (state.blocking.length) {
    blocking.classList.remove("hidden");
    const row = b => {
      const i = state.blocking.indexOf(b);
      return `
        <div class="block-row">
          <span class="block-kind ${esc(b.kind)}">${esc(b.kind)}</span>
          <span class="block-text" title="${esc(b.detail || "")}">${monoIds(esc(b.text))}</span>
          <button class="block-act" data-block="${i}">${esc(BLOCK_VERBS[b.kind] || "Open")}</button>
        </div>`;
    };
    blocking.innerHTML =
      (blockers.length
        ? `<h2>Blocking — ${blockers.length} <span class="hint">everything that stops the next render</span></h2>`
          + blockers.map(row).join("")
        : `<h2>Advisory <span class="hint">care of existing work — nothing blocks the next render</span></h2>`)
      + (advisories.length && blockers.length
        ? `<div class="advisory-label">ADVISORY</div>` : "")
      + advisories.map(row).join("");
    $$("[data-block]", blocking).forEach(btn => {
      btn.onclick = () => {
        const a = state.blocking[+btn.dataset.block].action;
        showView(a === "dashboard" ? "screenplay" : a || "status");
      };
    });
  } else {
    blocking.classList.add("hidden");
  }

  // Timestamps in the viewer's own timezone (user ruling 2026-08-01) —
  // the log records UTC; the reader lives somewhere.
  const localTime = ts => {
    const d = new Date(ts);
    return isNaN(d) ? (ts || "").slice(11, 16)
      : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  };
  $("#dash-recent").innerHTML = recent.length
    ? recent.map(e => `
        <div class="recent-row${e.kind === "error" ? " error" : ""}">
          <span class="recent-ts" title="${esc(e.ts || "")}">${esc(localTime(e.ts))}</span>
          <span class="recent-text">${monoIds(esc(e.text))}</span>
        </div>`).join("")
    : `<p class="mini">No activity recorded yet.</p>`;

  $("#dash-prohibited").innerHTML =
    state.prohibited_inventions.map(p => `<li>${esc(p)}</li>`).join("") ||
    `<li class="mini">none recorded</li>`;
}

function openSheet(specId) {
  activeView = "specs";
  $$("#tools-nav button").forEach(b => b.classList.remove("active"));
  updateBand();
  renderSpecs(specId);
}

async function renderScreenplay() {
  useTemplate("tpl-screenplay");
  const [state, analysis, citations] = await Promise.all([
    api("/api/state"),
    api("/api/wizard/analysis").catch(() => ({})),
    api("/api/screenplay/citation-report").catch(() => ({ missing: [] })),
  ]);

  const sp = state.screenplay;

  if (!sp) {
    // No screenplay is not a blank page (bug 2026-08-01: arriving here
    // from Status's Add button found a headline over nothing and an
    // upload buried in a side panel called "Replace"). The main column
    // becomes the upload, and Replace hides — nothing exists to replace.
    const mainPanel = $("#dash-locations").closest(".panel");
    mainPanel.innerHTML = `
      <div class="stage-kicker">STAGE 01 OF 5</div>
      <h3 class="stage-headline">Upload the screenplay</h3>
      <p class="hint">The read starts here: every location, cast member,
      design language and open question comes out of this one file.
      Nothing downstream unlocks without it.</p>
      <form id="screenplay-form-main" class="row">
        <input type="file" accept=".pdf,.fdx,.txt,.fountain" required>
        <button type="submit" class="primary">Upload &amp; start the read</button>
      </form>
      <p class="mini">PDF · FDX · FOUNTAIN · TXT</p>`;
    bindScreenplayUpload($("#screenplay-form-main"));
    $("#screenplay-form").closest(".panel").classList.add("hidden");
  }

  if (sp) {
    const up = (sp.uploaded_at || "").slice(0, 16).replace("T", " ");
    $("#dash-screenplay").innerHTML = `
      <p style="margin-top:0"><span class="badge APPROVED">CURRENT</span></p>
      <p class="scr-file">${esc(sp.file)}</p>
      <div class="fact"><span>SIZE</span><b>${(sp.size / 1048576).toFixed(2)} MB</b></div>
      <div class="fact"><span>SHA256</span><b>${esc((sp.sha256 || "").slice(0, 8))}</b></div>
      <div class="fact"><span>UPLOADED</span><b>${esc(up)}</b></div>
      <div class="fact" data-f="read"><span>READ</span><b>—</b></div>
      <div class="row" style="margin-top:10px">
        <button class="ghost" data-f="read-script" title="Open the original uploaded file in a new tab — the app itself works from the extracted text">Read the screenplay</button>
      </div>`;
    $("[data-f=read-script]").onclick = () =>
      window.open("/api/screenplay/file", "_blank");
  } else {
    $("#dash-screenplay").innerHTML = `<p class="mini">No screenplay uploaded yet — upload it to unlock every stage downstream.</p>`;
  }

  // Downstream counts: everything hanging off this file. Cited evidence rows
  // are summed from the sheets themselves (a handful of small fetches).
  const specMetas = state.specs || [];
  const fullSpecs = await Promise.all(specMetas.map(s =>
    api(`/api/specs/${s.specification_id}`).catch(() => null)));
  const citedRows = fullSpecs.filter(Boolean).reduce((n, r) =>
    n + ((r.spec.evidence_ledger || []).length), 0);
  const langs = (analysis.design_worlds || []).length;
  $("#scr-downstream").innerHTML = sp ? `
    <div class="fact-head">DOWNSTREAM OF THIS FILE</div>
    <div class="dsrow"><span>Design languages</span><b>${langs}</b></div>
    <div class="dsrow"><span>Breakdown sheets</span><b>${specMetas.length}</b></div>
    <div class="dsrow"><span>Cited evidence rows</span><b>${citedRows}</b></div>
    <div class="dsrow"><span>Approved panels</span><b>${(state.stage_summary?.panels || {}).approved ?? 0}</b></div>` : "";

  if (sp) renderLocations(state, langs);

  // Citation report — report-only by canon rule: broken citations are
  // presented for the director's review, never auto-resolved.
  const missing = citations.missing || [];
  const cit = $("#scr-citations");
  if (missing.length) {
    cit.classList.remove("hidden");
    cit.innerHTML = `
      <h2>Broken citations — ${missing.length} <span class="hint">quotes these sheets cite that the current draft no longer contains — nothing is changed automatically; review each row on its sheet</span></h2>
      ${missing.map(m => `
        <div class="block-row">
          <span class="block-kind CITE">CITE</span>
          <span class="block-text"><span class="mono-id">${esc(m.spec_id)}</span> ${esc(m.panel_id)}/${esc(m.object_id)} — ${esc(m.object)} · <span class="mini">"${esc(m.quote.slice(0, 90))}${m.quote.length > 90 ? "…" : ""}"</span></span>
          <button class="block-act" data-spec="${esc(m.spec_id)}">Review</button>
        </div>`).join("")}`;
    $$("[data-spec]", cit).forEach(btn => { btn.onclick = () => openSheet(btn.dataset.spec); });
  }

  bindScreenplayUpload($("#screenplay-form"));
}

// One upload path for every screenplay form (Status lead, the stage's
// empty state, and Replace). Success lands on the Screenplay stage to
// show what the read found.
function bindScreenplayUpload(form) {
  // Gate readable as state: the verb stays disabled, with the condition
  // stated, until a file is actually chosen.
  const input = $('input[type="file"]', form);
  const submit = $('button[type="submit"]', form);
  const sync = () => {
    submit.disabled = !input.files.length;
    submit.title = input.files.length ? "" : "Choose a screenplay file first";
  };
  input.addEventListener("change", sync);
  sync();
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const file = $('input[type="file"]', form).files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const rec = await api("/api/screenplay", { method: "POST", body: fd });
      const cc = rec.citation_check;
      toast(cc && cc.missing
        ? `Draft uploaded — ${cc.missing} of ${cc.quotes_checked} cited quote(s) no longer found; review below.`
        : "Draft uploaded." + (cc ? ` All ${cc.quotes_checked} cited quotes still present.` : ""));
      showView("screenplay");
    } catch (err) { toast(err.message, true); }
  });
}

// One finder-list scaffold (plan P4/R2): the screenplay coverage table and
// the wizard's read-locations list render through this single code path —
// Courier search over a scrolling row host, plus the shared verbs (Draft a
// Breakdown prefills the breakdown prompt; Open Breakdown jumps to it).
function buildLocFinder(host, cfg) {
  host.innerHTML = `
    ${cfg.head || ""}
    <input type="text" data-f="loc-search" class="loc-search" placeholder="${cfg.placeholder || "search locations…"}">
    <div class="loc-scroll"${cfg.maxHeight ? ` style="max-height:${cfg.maxHeight}px"` : ""}>
      ${cfg.headRow || ""}
      <div data-f="loc-list"></div>
    </div>
    ${cfg.footer || ""}`;
  const draw = () => {
    const q = $("[data-f=loc-search]", host).value;
    $("[data-f=loc-list]", host).innerHTML = cfg.rows(q.trim().toUpperCase(), q);
    $$(".loc-draft", host).forEach(btn => {
      btn.onclick = () => {
        sessionStorage.setItem("draftLocationHint", btn.dataset.loc);
        showView("specs");
      };
    });
    $$("[data-open]", host).forEach(btn => {
      btn.onclick = () => openSheet(btn.dataset.open);
    });
    cfg.onDraw?.(draw);
  };
  $("[data-f=loc-search]", host).addEventListener("input", draw);
  draw();
}

async function renderLocations(state = null, langs = 0) {
  const host = $("#dash-locations");
  if (!host) return;
  let data;
  try { data = await api("/api/screenplay/locations"); }
  catch { return; }
  if (!data.available) {
    host.innerHTML = `<p class="mini">${esc(data.reason || "location map unavailable")}</p>`;
    return;
  }
  const readFact = $("[data-f=read] b");
  if (readFact) readFact.textContent =
    `${langs} LANGUAGE${langs === 1 ? "" : "S"} · ${data.locations.length} LOCS`;

  // Canonical coverage meter (plan v3 Part A.3): 4 segments; filled = --ok;
  // a single amber first segment means thin — inference will be spent here.
  const meter = d => `<span class="loc-meter${d === 1 ? " thin" : ""}" title="how much the script describes — thin coverage spends inference budget faster">`
    + [1, 2, 3, 4].map(i => `<i class="${i <= d ? "on" : ""}"></i>`).join("") + `</span>`;

  const heldBySpec = {};
  for (const b of (state?.blocking || [])) {
    if (b.kind === "HOLD" && b.spec_id) {
      const m = b.text.match(/^(\d+)/);
      heldBySpec[b.spec_id] = m ? +m[1] : 1;
    }
  }
  const pdReady = !!state?.stage_summary?.production_design?.bible_saved;
  const sheetCell = l => {
    if (!l.sheet) return pdReady
      ? `<button class="block-act loc-draft" data-loc="${esc(l.location)}">Create Breakdown</button>`
      : PD_LOCK_TAG;
    const held = heldBySpec[l.sheet.spec_id];
    return `<span class="loc-sheet">
      <span class="badge ${l.sheet.locked ? "LOCKED" : "DRAFT"}">${l.sheet.locked ? "LOCKED" : esc(l.sheet.status)}</span>
      <button class="loc-open${held ? " held" : ""}" data-open="${esc(l.sheet.spec_id)}">${held ? `${held} held row${held > 1 ? "s" : ""}` : "Open Breakdown"}</button>
    </span>`;
  };

  // Scrollable, searchable, expandable: every location, every scene under
  // it, each scene draftable as its own SCENE breakdown.
  const expanded = new Set();
  buildLocFinder(host, {
    head: `<div class="loc-head">
      <span class="f-label">Locations · ${data.locations.length}</span>
      <span class="hint">${data.scene_count} scenes · sorted by scene count · click a location to list its scenes</span></div>`,
    headRow: `<div class="loc-row loc-headrow"><span>SLUGLINE</span><span>SCENES</span><span>DETAIL</span><span>SHEET</span></div>`,
    placeholder: "search locations and scenes…",
    footer: `<p class="mini"><span class="f-label" style="font-size:10px">DETAIL</span> how much the script describes — thin coverage spends inference budget faster</p>`,
    rows: (needle, q) => {
      const list = data.locations.filter(l =>
        !needle || l.location.includes(needle) ||
        (l.scene_list || []).some(s => s.heading.toUpperCase().includes(needle)));
      const rowHtml = l => {
        const open = expanded.has(l.location) ||
          (needle && !l.location.includes(needle));  // scene-only hits auto-expand
        const sceneRows = open ? (l.scene_list || [])
          .filter(s => !needle || s.heading.toUpperCase().includes(needle) || l.location.includes(needle))
          .map(s => `
            <div class="scene-row">
              <span class="loc-slug" style="color:var(--ink-dim)">${esc(s.heading)}</span>
              ${pdReady ? `<button class="block-act loc-draft" data-loc="${esc(s.heading)}">Create Breakdown</button>` : PD_LOCK_TAG}
            </div>`).join("") : "";
        return `
          <div class="loc-row" data-exp="${esc(l.location)}" style="cursor:pointer" title="click to ${open ? "collapse" : "list"} this location's scenes">
            <span class="loc-slug">${open ? "▾" : "▸"} ${esc(l.int_ext)}. ${esc(l.location)}</span>
            <span class="loc-scenes">${l.scenes}</span>
            ${meter(l.detail)}
            ${sheetCell(l)}
          </div>${sceneRows}`;
      };
      const empty = `<p class="mini">nothing matches "${esc(q)}"</p>`;
      // Environment grouping (plan P7): the read's verbatim slugline
      // assignments — the same buckets as the wizard's finder list, zero
      // fuzzy matching. No environments = the flat table it always was.
      const envs = (wizACache()
        ?.environments || []).filter(e => (e.name || "").trim());
      if (!envs.length) return list.map(rowHtml).join("") || empty;
      const assignedTo = {};
      envs.forEach(e => (e.locations || []).forEach(l => { assignedTo[l] = e.name; }));
      const buckets = [
        ...envs.map(e => ({ name: e.name, rows: list.filter(l => assignedTo[l.location] === e.name) })),
        { name: "UNASSIGNED", rows: list.filter(l => !assignedTo[l.location]) },
      ].filter(b => b.rows.length);
      return buckets.map(b =>
        `<div class="loc-group">${esc(b.name.toUpperCase())} — ${b.rows.length}</div>`
        + b.rows.map(rowHtml).join("")).join("") || empty;
    },
    onDraw: draw => {
      $$("[data-exp]", host).forEach(row => {
        row.onclick = (e) => {
          if (e.target.closest("button")) return;  // actions win over expand
          const key = row.dataset.exp;
          expanded.has(key) ? expanded.delete(key) : expanded.add(key);
          draw();
        };
      });
    },
  });
}

/* ---------------------------------------------------- productions library */

// The Screenboard Library (PRODUCTIONS_PLAN A2): a production is the top
// of the content hierarchy, so it gets its own view — Settings keeps only
// install-level configuration. Switching reloads so every view re-reads
// the newly active production. '' is the legacy root layout.
async function renderProjectsView() {
  useTemplate("tpl-projects");

  // Care line escalation (PRODUCTIONS_PLAN A4): faint under 14 days,
  // --hold to 29, --bad at 30+ — and never a blocker anywhere.
  const careLine = p => {
    if (!p.last_backup_at) return { text: "NEVER BACKED UP", cls: "" };
    const d = p.days_since_backup ?? 0;
    const text = d === 0 ? "BACKED UP TODAY"
      : `BACKED UP ${d} DAY${d === 1 ? "" : "S"} AGO`;
    return { text, cls: d >= 30 ? "care-bad" : d >= 14 ? "care-hold" : "" };
  };

  const mbs = n => n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB`
    : `${Math.max(1, Math.round(n / 1024))} KB`;

  const renderCards = async () => {
    const pr = await api("/api/projects/summary");
    $("#prod-count").textContent =
      `${pr.projects.length} PRODUCTION${pr.projects.length === 1 ? "" : "S"} · 1 OPEN`;
    $("#prod-cards").innerHTML = pr.projects.map(p => {
      const care = careLine(p);
      const stale = (p.days_since_backup ?? -1) >= 30;
      const clear = p.next?.kicker === "ALL STAGES CLEAR";
      return `
      <div class="panel prod-card ${p.active ? "open" : ""}" data-card="${esc(p.slug)}">
        <div class="prod-card-head">
          <span class="prod-name" data-name="${esc(p.slug)}">${esc(p.name)}</span>
          ${p.active ? '<span class="prod-open mono">OPEN</span>' : ""}
          <span class="prod-slug mono">${p.slug ? esc(p.slug) : "root layout"}</span>
        </div>
        <div class="prod-band">${(p.reach || []).map(r =>
          `<span class="${r.state === "ok" ? "r-ok" : r.state === "bad" ? "r-bad" : ""}">${esc(r.label)}</span>`).join("")}
        </div>
        <div class="prod-counts">${esc(p.counts || "")}</div>
        <div>
          <div class="prod-next-k ${clear ? "clear" : ""}">${esc(p.next?.kicker || "DO THIS NEXT")}</div>
          <div class="prod-next ${clear ? "prod-next-clear mono" : ""}">${monoIds(esc(p.next?.text || ""))}</div>
        </div>
        <div class="prod-foot">
          <span class="prod-care mono ${care.cls}">${esc(care.text)}</span>
          <span class="prod-actions">
            <button class="ghost ${stale ? "urgent" : ""}" data-backup="${esc(p.slug)}" title="Download this production as one zip — screenplay, bible, references, sheets, boards, approvals. API keys are never included.">${stale ? "Back up now" : "Back up"}</button>
            ${p.active ? "" : `<button class="ghost" data-slug="${esc(p.slug)}" title="Open this production — the current one keeps everything and stays on the shelf.">Open</button>`}
            <button class="ghost" data-rename="${esc(p.slug)}" title="Renames in place — Enter commits, Esc reverts.">Rename</button>
            <button class="ghost" data-more="${esc(p.slug)}" title="Duplicate or delete this production">&hellip;</button>
          </span>
        </div>
        <div data-busy="${esc(p.slug)}"></div>
      </div>`;
    }).join("");

    $$("#prod-cards [data-slug]").forEach(b => b.onclick = async () => {
      try {
        await api("/api/projects/activate", { method: "POST", json: { slug: b.dataset.slug } });
        location.reload();
      } catch (err) { toast(err.message, true); }
    });
    // A backup is a server-side zip of a whole production, and on a large
    // one the wait is real — it used to be a bare location.href with nothing
    // on screen (user 2026-08-06). Streaming it through fetch lets the wait
    // state itself in the canon .busy vocabulary and counts the bytes.
    $$("#prod-cards [data-backup]").forEach(b => b.onclick = async () => {
      const slug = b.dataset.backup;
      const card = b.closest(".prod-card");
      const busy = startBusy($("[data-busy]", card), "Packing the backup…",
        "API keys are never included.");
      $$(".prod-actions button", card).forEach(x => x.disabled = true);
      try {
        const res = await fetch(`/api/projects/backup?slug=${encodeURIComponent(slug)}`);
        if (!res.ok) throw new Error((await res.text()) || `backup failed (${res.status})`);
        const total = Number(res.headers.get("Content-Length") || 0);
        const fname = /filename="([^"]+)"/.exec(
          res.headers.get("Content-Disposition") || "")?.[1] || "screenboard-backup.zip";
        const chunks = [];
        let got = 0;
        const reader = res.body.getReader();
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value);
          got += value.length;
          busy.label(total ? `Downloading — ${mbs(got)} of ${mbs(total)}`
                           : `Downloading — ${mbs(got)}`);
        }
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(chunks, { type: "application/zip" }));
        a.download = fname;
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
        toast(`${fname} downloaded — ${mbs(got)}.`);
      } catch (err) {
        toast(err.message, true);
      } finally {
        busy.done();
        renderCards();  // pick up the fresh last-backup stamp
      }
    });
    $$("#prod-cards [data-rename]").forEach(b => b.onclick = () => {
      const slug = b.dataset.rename;
      const nameEl = $(`#prod-cards [data-name="${CSS.escape(slug)}"]`);
      const isOpen = !!nameEl?.closest(".prod-card.open");
      if (nameEl) inlineRename(nameEl, async name => {
        const r = await api("/api/projects/rename", { method: "POST", json: { name, slug } });
        toast(`Production named "${r.name}".`);
        if (isOpen) $("#brand-project").textContent = r.name.toUpperCase();
        return r.name;
      });
    });
    $$("#prod-cards [data-more]").forEach(b => b.onclick = e => {
      e.stopPropagation();
      cardMenu(b, pr.projects.find(p => p.slug === b.dataset.more), renderCards);
    });
  };

  // The ⋯ menu: duplicate and delete. Delete is typed-name confirmed —
  // it destroys a screenplay, a library and every board.
  const cardMenu = (btn, p, refresh) => {
    $$(".card-menu").forEach(m => m.remove());
    const menu = document.createElement("div");
    menu.className = "card-menu";
    menu.innerHTML = `
      <button class="proj-item" data-act="dup">Duplicate</button>
      <button class="proj-item" data-act="imp">Import backup&hellip;</button>
      <button class="proj-item danger-act" data-act="del" ${p.active ? "disabled" : ""}
        ${p.active ? 'title="The open production cannot be deleted — open another first."' : ""}>Delete&hellip;</button>`;
    btn.closest(".prod-actions").appendChild(menu);
    const close = () => menu.remove();
    setTimeout(() => document.addEventListener("click", close, { once: true }));
    $('[data-act="dup"]', menu).onclick = async () => {
      try {
        const r = await api("/api/projects/duplicate", { method: "POST", json: { slug: p.slug } });
        toast(`"${r.name}" added to the shelf.`);
        refresh();
      } catch (err) { toast(err.message, true); }
    };
    // Import sets an existing production to the version in a zip — the
    // destructive twin of restore, which only ever made a NEW production
    // (user 2026-08-06). The zip is read before the warning is written, so
    // the modal names what is actually in it rather than guessing.
    $('[data-act="imp"]', menu).onclick = () => {
      const inp = document.createElement("input");
      inp.type = "file";
      inp.accept = ".zip,application/zip";
      // The input MUST be in the document before click(): a DETACHED file
      // input's click() is silently ignored — no picker, no error, no
      // feedback of any kind (user 2026-08-06). Every other file field in
      // this app is markup that already lives in the page, which is why
      // this was the first place it bit.
      inp.className = "hidden";
      document.body.append(inp);
      inp.oncancel = () => inp.remove();
      inp.onchange = async () => {
        const f = inp.files[0];
        inp.remove();
        if (!f) return;
        const look = new FormData();
        look.append("file", f);
        let info;
        try {
          info = await api("/api/projects/import/inspect", { method: "POST", body: look });
        } catch (err) { return toast(err.message, true); }
        const when = (info.backed_up_at || "").slice(0, 10);
        const vals = await modal({
          title: `Import a backup into "${p.name}"?`,
          body: `That zip holds "${info.name}" — ${info.files} files, `
            + `${mbs(info.bytes)}${when ? `, backed up ${when}` : ""}. `
            + "Importing replaces this production's screenplay, bible, reference "
            + "library, breakdown sheets, boards and approval log with what the zip "
            + "carries; anything here that the zip does not contain is removed. "
            + `"${p.name}" keeps its own name and its place on the shelf. A safety `
            + "copy of the current state is saved beside the production first, but "
            + "it is not a download — back up now if you want one in hand. Type the "
            + "production's name to confirm.",
          fields: [{ name: "confirm", label: "Production name", placeholder: p.name }],
          confirmLabel: "Import and replace", danger: true,
        });
        if (vals === null) return;
        const card = $(`#prod-cards [data-card="${CSS.escape(p.slug)}"]`);
        const busy = startBusy($("[data-busy]", card), "Importing the backup…",
          "A safety copy is packed first.");
        const fd = new FormData();
        fd.append("file", f);
        fd.append("slug", p.slug);
        fd.append("confirm_name", vals.confirm);
        try {
          const r = await api("/api/projects/import", { method: "POST", body: fd });
          toast(`"${r.name}" set to the version from "${r.imported_from}" — `
                + `${r.files} files. Back it up when you are happy with it.`);
          if (r.was_active) return location.reload();
          refresh();
        } catch (err) {
          toast(err.message, true);
        } finally { busy.done(); }
      };
      inp.click();
    };
    $('[data-act="del"]', menu).onclick = async () => {
      if (p.active) return;
      const vals = await modal({
        title: `Delete "${p.name}"?`,
        body: "This destroys its screenplay, reference library, breakdowns and every board. There is no undo — a backup zip is the only way back. Type the production's name to confirm.",
        fields: [{ name: "confirm", label: "Production name", placeholder: p.name }],
        confirmLabel: "Delete production", danger: true,
      });
      if (vals === null) return;
      try {
        await api("/api/projects/delete", { method: "POST",
          json: { slug: p.slug, confirm_name: vals.confirm } });
        toast(`"${p.name}" deleted.`);
        refresh();
      } catch (err) { toast(err.message, true); }
    };
  };

  $("#proj-restore").addEventListener("submit", async e => {
    e.preventDefault();
    const f = $("#proj-zip").files[0];
    if (!f) return toast("Choose a backup zip first.", true);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await api("/api/projects/restore", { method: "POST", body: fd });
      toast(`"${r.name}" restored as a new production (${r.slug}) — open it from the shelf.`);
      $("#proj-zip").value = "";
      renderCards();
    } catch (err) { toast(err.message, true); }
  });
  $("#proj-new").addEventListener("submit", async e => {
    e.preventDefault();
    const name = $("#proj-name").value.trim();
    if (!name) return toast("Give the production a name first.", true);
    try {
      await api("/api/projects", { method: "POST", json: { name } });
      toast(`${name} created — switching…`);
      location.reload();
    } catch (err) { toast(err.message, true); }
  });
  await renderCards();
}

/* --------------------------------------------------------------- settings */

async function renderSettings() {
  useTemplate("tpl-settings");
  $("#goto-productions").onclick = () => showView("projects");

  const rememberedTab0 = uiGet("settingsTab", "");
  const rememberedTab = rememberedTab0 === "debug" && !_debugTools
    ? "" : rememberedTab0;
  if (rememberedTab) {
    const btn = $(`#settings-subnav button[data-sub="${CSS.escape(rememberedTab)}"]`);
    if (btn) {
      $$("#settings-subnav button").forEach(b => b.classList.toggle("active", b === btn));
      $$("[data-subview]").forEach(v =>
        v.classList.toggle("hidden", v.dataset.subview !== rememberedTab));
    }
  }
  $("#settings-subnav").addEventListener("click", e => {
    const btn = e.target.closest("button[data-sub]");
    if (!btn) return;
    uiSet("settingsTab", btn.dataset.sub);
    $$("#settings-subnav button").forEach(b => b.classList.toggle("active", b === btn));
    $$("[data-subview]").forEach(v =>
      v.classList.toggle("hidden", v.dataset.subview !== btn.dataset.sub));
  });

  const settings = await api("/api/settings");
  _debugTools = !!settings.debug_tools;
  if (!_debugTools) {
    // Debug tools exist only on the owner's installs — the tab and its
    // subview are removed outright, never merely hidden.
    $('#settings-subnav button[data-sub="debug"]')?.remove();
    $('[data-subview="debug"]')?.remove();
  }

  // User-added engines render inside the §02 credential list (C2).
  const customs = settings.custom_engines || [];

  // C1 (CONNECTORS_UI_PLAN) — §01, the two AI roles. The recommendation
  // is a bordered ink-dim Courier chip plus one sentence of reason —
  // never amber, never unexplained. With no key it renders as the gate
  // grammar, never a preselected broken default.
  const engAll = settings.engines || {};
  let cxRows = [], cxStats = { total: 0, enabled: 0 }, catalogAll = [];
  try {
    const cxState = await api("/api/connectors");
    cxRows = cxState.connectors; cxStats = cxState.stats;
    catalogAll = (await api("/api/connectors/catalog?scope=all")).records;
  } catch { /* rows render NOT CONNECTED */ }

  // F1 (SETTINGS_FIRST_RUN_PLAN) — the two lives. Before a credential
  // exists the page is a setup form; after one exists it is a control
  // panel. A dropdown is never an error message.
  const anyCred = !!(engAll.openai?.configured || engAll.gemini?.configured
    || customs.length || settings.anthropic_api_key_set
    || cxRows.some(r => r.status !== "NOT_CONNECTED"));
  $("#settings-firstrun").classList.toggle("hidden", anyCred);
  $("#settings-steady").classList.toggle("hidden", !anyCred);
  // MOCK_PARITY D7: first-run users have no productions to manage — the
  // PRODUCTIONS MOVED pointer renders only in the configured state.
  $(".subnav-end")?.classList.toggle("hidden", !anyCred);
  if (!anyCred) renderFirstRun();

  function renderFirstRun() {
    $("#fr-connect").onclick = async () => {
      try {
        const { url } = await api("/api/connectors/openrouter/auth");
        location.href = url;
      } catch (err) { toast(err.message, true); }
    };
    buildProviderMarquee($("#fr-marquee"));
    const ACCOUNTS = [
      { key: "openai", name: "OpenAI", icon: "openai" },
      { key: "gemini", name: "Google Gemini", icon: "gemini-color" },
      { key: "anthropic", name: "Anthropic Claude", icon: "claude-color" },
    ];
    $("#fr-accounts").innerHTML = ACCOUNTS.map(a => `
      <div class="cred-row fr-row">
        <span class="cred-tile"><img class="prov-ico" src="/provider-icons/${a.icon}.png" alt="" onerror="this.parentNode.textContent='${esc(a.name.slice(0, 3).toUpperCase())}'"></span>
        <span class="cred-id"><span class="cred-name">${esc(a.name)}</span></span>
        <span class="cred-acts"><button class="ghost" data-auth="${a.key}">Authenticate</button></span>
      </div>`).join("") + `
      <div class="cred-row fr-row">
        <span class="cred-tile plus">+</span>
        <span class="cred-id"><span class="cred-name">Your own endpoints</span>
          <span class="cred-meta">ADD ANY API KEY</span></span>
        <span class="cred-acts"><button class="text-act" data-auth="custom">Add model</button></span>
      </div>`;
    $$("#fr-accounts [data-auth]").forEach(b => {
      b.onclick = () => b.dataset.auth === "custom"
        ? addCustomEngineModal() : authModal(b.dataset.auth);
    });
  }

  if (anyCred) {
  const cxStatus = Object.fromEntries(cxRows.map(r => [r.id, r.status]));
  const usableProvider = pid => {
    if (pid.startsWith("or:")) return cxStatus.openrouter === "SYNCED";
    if (pid.startsWith("fal:")) return cxStatus.fal === "SYNCED";
    const e = engAll[pid];
    return !!(e?.configured && e?.last_test?.ok !== false);
  };
  // Role 01 — narrative & content evaluation. Four possible homes now
  // (F6 backend, 2026-08-04): the OpenAI key (default), the Gemini key,
  // the Anthropic key, or the OpenRouter connector.
  const nSel = $("#role-narrative");
  const nDefault = settings.openai_chat_model_default;
  const nCur = settings.openai_chat_model || nDefault;
  const oaiConfigured = !!engAll.openai?.configured;
  const nUsable = [];
  if (oaiConfigured) {
    nUsable.push(["openai", `ChatGPT — ${nCur}`]);
    nUsable.push(["openai:__custom", "ChatGPT — custom model id…"]);
  }
  if (engAll.gemini?.configured) nUsable.push(["gemini", "Gemini (research pass)"]);
  if (engAll.anthropic?.configured && engAll.anthropic?.last_test?.ok !== false)
    nUsable.push(["anthropic", `Anthropic — ${settings.anthropic_model}`]);
  if (settings.openrouter_narrative_ready)
    nUsable.push(["openrouter", `OpenRouter — ${settings.openrouter_narrative_model}`]);
  if (!nUsable.length) {
    // F1: a dropdown is never an error message — the withheld-verb tag
    // states the unmet condition instead of a disabled control.
    nSel.closest(".role-sel").innerHTML =
      `<p class="wv-tag">NEEDS A KEY OR THE OPENROUTER CONNECTION</p>`;
  } else {
    nSel.innerHTML = nUsable.map(([v, l]) =>
      `<option value="${esc(v)}">${esc(l)}</option>`).join("");
    nSel.value = nUsable.some(([v]) => v === settings.narrative_provider)
      ? settings.narrative_provider : nUsable[0][0];
    // P1 — a live role wears one --ok square inside the field; the words
    // about what runs where belong to first run and the modal.
    nSel.closest(".role-sel").classList.add("live");
    nSel.onchange = async () => {
      let v = nSel.value;
      const json = {};
      if (v === "openai:__custom") {
        const r = await modal({
          title: "Narrative model id",
          body: "The exact OpenAI model id this install should use for every screenplay read, draft and rewrite.",
          fields: [{ name: "id", label: "Model id", placeholder: nDefault }],
          confirmLabel: "Use this model",
        });
        if (r === null || !r.id.trim()) { nSel.value = settings.narrative_provider || "openai"; return; }
        json.openai_chat_model = r.id.trim() === nDefault ? "" : r.id.trim();
        v = "openai";
      }
      json.narrative_provider = v;
      try {
        await api("/api/settings", { method: "POST", json });
        toast(`Narrative runs on ${nSel.options[nSel.selectedIndex]?.textContent || v}.`);
        renderSettings();
      } catch (err) { toast(err.message, true); }
    };
  }

  // Role 02 — image generation: the STARTING engine (preferred_provider).
  const iSel = $("#role-image");
  const usableProviders = Object.keys(settings.providers).filter(usableProvider);
  if (!usableProviders.length) {
    iSel.closest(".role-sel").innerHTML =
      `<p class="wv-tag">WILL RUN ON THE FIRST ENGINE YOU ADD</p>`;
  } else {
    iSel.innerHTML = usableProviders.map(v =>
      `<option value="${esc(v)}">${esc(settings.providers[v])}</option>`).join("");
    iSel.value = usableProviders.includes(settings.preferred_provider)
      ? settings.preferred_provider : usableProviders[0];
    iSel.closest(".role-sel").classList.add("live");
    iSel.onchange = async () => {
      try {
        await api("/api/settings", { method: "POST", json: { preferred_provider: iSel.value } });
        toast(`Starting engine: ${settings.providers[iSel.value]}.`);
      } catch (err) { toast(err.message, true); }
    };
  }

  // SETTINGS_CONTROL_PANEL P1 — one credential list, all rows equal. A
  // connected row carries Courier machine facts, its state square and
  // text acts; a row that isn't connected carries nothing but its name
  // and Authenticate — no status chip for something that hasn't
  // happened. Failing states stay: they are machine facts.
  const stamp = t => (t || "").slice(0, 16).replace("T", " ");
  const mark = kind => `<span class="cred-mark ${kind}"></span>`;
  const keyState = pid => {
    const e = engAll[pid] || {};
    if (e.last_test?.ok) return ["ok", "SYNCED"];
    if (e.last_test && !e.last_test.ok) return ["bad", `KEY FAILED ${stamp(e.last_test.at)}`];
    if (e.source === "env") return ["hold", "ENV VAR — UNTESTED"];
    return ["hold", "KEY SET — UNTESTED"];
  };
  const keyActs = pid => [["Replace", "replace"],
    ...((engAll[pid] || {}).source === "env" ? [] : [["Disconnect", "disconnect-key"]])];
  const cxState = r => ({
    SYNCED: ["ok", "SYNCED"],
    REJECTED: ["bad", `401 — REJECTED ${stamp(r.last_error?.at)}`],
    NO_NETWORK: ["hold", "NO NETWORK"],
  })[r.status];
  const cxActs = st => ({
    SYNCED: [["Refresh", "refresh"], ["Disconnect", "disconnect"]],
    REJECTED: [["Reconnect", "auth"], ["Disable models", "disable-all"]],
    NO_NETWORK: [],
  })[st] || [];

  const orRow = cxRows.find(r => r.id === "openrouter") || { status: "NOT_CONNECTED" };
  const falRow = cxRows.find(r => r.id === "fal") || { status: "NOT_CONNECTED" };
  const credRows = [
    { key: "openrouter", tile: "ORT", name: "OpenRouter",
      connected: orRow.status !== "NOT_CONNECTED",
      facts: (orRow.identity ? `${esc(orRow.identity)} · ` : "")
        + "SCOPED KEY — REVOKE FROM THEIR DASHBOARD",
      state: cxState(orRow), actions: cxActs(orRow.status) },
    { key: "openai", tile: "OAI", icon: "openai", name: "OpenAI",
      connected: !!engAll.openai?.configured,
      facts: esc(settings.openai_api_key_hint || settings.openai_env_key_hint || ""),
      state: keyState("openai"), actions: keyActs("openai") },
    { key: "gemini", tile: "GGL", icon: "gemini-color", name: "Google Gemini",
      connected: !!engAll.gemini?.configured,
      facts: esc(settings.gemini_api_key_hint || ""),
      state: keyState("gemini"), actions: keyActs("gemini") },
    { key: "anthropic", tile: "ANT", icon: "claude-color", name: "Anthropic Claude",
      connected: !!settings.anthropic_api_key_set,
      facts: esc(settings.anthropic_api_key_hint || ""),
      state: keyState("anthropic"), actions: keyActs("anthropic") },
    { key: "fal", tile: "FAL", name: "fal.ai",
      connected: falRow.status !== "NOT_CONNECTED",
      facts: esc(falRow.key_hint || ""),
      state: cxState(falRow), actions: cxActs(falRow.status) },
    { key: "custom", tile: "+", name: "Your own endpoints", custom: true,
      facts: "ADD ANY API KEY", actions: [["Add model", "add-custom"]] },
  ];

  $("#cred-list").innerHTML = credRows.map(r => {
    // P3 — a third-party service rides its real brand icon; Courier
    // initials are the stated fallback (and ORT stands: no dark mark).
    const tileHtml = r.custom
      ? `<span class="cred-tile plus">+</span>`
      : r.icon
        ? `<span class="cred-tile"><img class="prov-ico" src="/provider-icons/${r.icon}.png" alt="" onerror="this.parentNode.textContent='${esc(r.tile)}'"></span>`
        : `<span class="cred-tile">${esc(r.tile)}</span>`;
    if (!r.connected && !r.custom) return `
    <div class="cred-row bare" data-cred="${esc(r.key)}">
      ${tileHtml}
      <span class="cred-id"><span class="cred-name">${esc(r.name)}</span></span>
      <span class="cred-state"></span>
      <span class="cred-acts"><button class="ghost" data-act="auth">Authenticate</button></span>
    </div>
    <div class="cred-expand hidden" data-expand="${esc(r.key)}"></div>`;
    const chips = r.custom ? customs.map(e =>
      `<button class="cchip" data-cid="${esc(e.id)}">${esc((e.label || e.id).toUpperCase().slice(0, 14))}</button>`).join(" ") : "";
    return `
    <div class="cred-row" data-cred="${esc(r.key)}">
      ${tileHtml}
      <span class="cred-id">
        <span class="cred-name">${esc(r.name)}</span>
        ${r.facts || chips ? `<span class="cred-meta">${r.facts}${chips ? " " + chips : ""}</span>` : ""}
      </span>
      <span class="cred-state">${r.state ? mark(r.state[0]) + esc(r.state[1]) : ""}</span>
      <span class="cred-acts">${(r.actions || []).map(([l, a]) =>
        `<button class="text-act" data-act="${esc(a)}">${esc(l)}</button>`).join(" ")}</span>
    </div>
    <div class="cred-expand hidden" data-expand="${esc(r.key)}"></div>`;
  }).join("");
  $$("#cred-list .cred-row").forEach(row => {
    const key = row.dataset.cred;
    $$("button[data-act]", row).forEach(btn => {
      btn.onclick = () => credAction(key, btn.dataset.act, row);
    });
    $$("button.cchip", row).forEach(ch => {
      ch.onclick = () => expandCustomChip(ch.dataset.cid, row);
    });
  });

  async function credAction(key, act, row) {
    if (act === "auth" || act === "replace") {
      // One grammar for every credential: OpenRouter's true OAuth goes
      // straight to their authorisation page; everyone else gets the
      // connector-grammar Authenticate modal.
      if (key === "openrouter") {
        try {
          const { url } = await api("/api/connectors/openrouter/auth");
          location.href = url;
        } catch (err) { toast(err.message, true); }
      } else authModal(key);
    } else if (act === "disconnect-key") {
      const field = { openai: "openai_api_key", gemini: "gemini_api_key",
                      anthropic: "anthropic_api_key" }[key];
      if (!field || !(await askConfirm(`Disconnect ${key}`,
        "The key is deleted from settings.json on this machine. Work it generated keeps its records.",
        "Disconnect", true))) return;
      try { await api("/api/settings", { method: "POST", json: { [field]: "" } }); }
      catch (err) { toast(err.message, true); }
      renderSettings();
    } else if (act === "add-custom") {
      addCustomEngineModal();
    } else if (act === "refresh") {
      try {
        const r = await api(`/api/connectors/${key}/refresh`, { method: "POST" });
        toast(`${r.label}: ${r.model_count} models synced.`);
      } catch (err) { toast(err.message, true); }
      renderSettings();
    } else if (act === "disconnect") {
      if (!(await askConfirm(`Disconnect ${key}`,
        "The credential is forgotten. Your synced catalog and enabled models are kept — they render again when you reconnect.",
        "Disconnect", true))) return;
      try { await api(`/api/connectors/${key}/disconnect`, { method: "POST" }); }
      catch (err) { toast(err.message, true); }
      renderSettings();
    } else if (act === "disable-all") {
      const mine = catalogAll.filter(m => m.connector === key && m.enabled);
      for (const m of mine) {
        try { await api("/api/connectors/enable", { method: "POST", json: { id: m.id, on: false } }); }
        catch { /* stated on rerender */ }
      }
      toast(`${mine.length} model${mine.length === 1 ? "" : "s"} disabled for now.`);
      renderSettings();
    }
  }

  // SETTINGS_CONTROL_PANEL P1 — the catalog is one line of counts. The
  // stat tiles were furniture; the counts are the required information.
  // A deprecated-but-enabled count is a failing state and stays, in
  // --bad, only when it is nonzero.
  const lastSync = cxRows.map(r => r.last_sync).filter(Boolean).sort().pop();
  const ago = t => {
    const m = Math.max(1, Math.round((Date.now() - Date.parse(t)) / 60000));
    if (m < 60) return `${m} MIN AGO`;
    const h = Math.round(m / 60);
    return h < 48 ? `${h} H AGO` : `${Math.round(h / 24)} D AGO`;
  };
  $("#models-facts").innerHTML =
    `${cxStats.enabled || 0} ENABLED · ${cxStats.total || 0} IN CATALOG · `
    + (lastSync ? `SYNCED ${esc(ago(lastSync))}` : "NO CATALOG SYNCED")
    + (cxStats.deprecated_enabled
      ? ` · <span class="m-bad">${cxStats.deprecated_enabled} ENABLED BUT DEPRECATED UPSTREAM</span>`
      : "");
  const catBtn = $("#open-catalog");
  if (cxStats.total) {
    catBtn.classList.remove("hidden");
    catBtn.onclick = () => renderCatalogBrowser();
  }

  // C5 — the model browser: grouped by what they can do, not by who
  // sells them. Reference capability is the product's first hard filter,
  // so it is the first thing the layout expresses. C6 — imagery is the
  // typographic tile plus the witnessed test frame, never vendor samples.
  const DEVTILES = { "openai": "OAI", "google": "GGL", "black forest labs": "BFL",
    "bytedance": "BDN", "ideogram": "IDG", "recraft": "RCF", "stability": "STB",
    "higgsfield": "HGS", "qwen": "QWN", "krea": "KRA", "microsoft": "MSF",
    "x-ai": "XAI", "xai": "XAI", "nvidia": "NVD", "hidream": "HDR" };
  const devTile = d => DEVTILES[(d || "").toLowerCase()]
    || ((d || "").split(/[\s-]+/).filter(Boolean).map(w => w[0]).join("").slice(0, 3).toUpperCase() || "???");
  // P3 (SETTINGS_CONTROL_PANEL) — wherever a third-party service appears
  // it rides its real brand icon; Courier initials are the stated
  // fallback for developers with no dark mark in the local set.
  const PROV_ICONS = { openai: "openai", google: "gemini-color",
    anthropic: "claude-color", qwen: "qwen-color", "x-ai": "xai", xai: "xai",
    nvidia: "nvidia-color", meta: "meta-color", deepseek: "deepseek-color",
    mistral: "mistral-color", moonshot: "moonshot", minimax: "minimax-color",
    cohere: "cohere-color", perplexity: "perplexity-color",
    nousresearch: "nousresearch", "liquid ai": "liquid", amazon: "aws-color" };
  const devTileHtml = d => {
    const ico = PROV_ICONS[(d || "").toLowerCase()];
    return ico
      ? `<img class="prov-ico" src="/provider-icons/${ico}.png" alt="" onerror="this.parentNode.textContent='${esc(devTile(d))}'">`
      : esc(devTile(d));
  };
  const badges = m => {
    const b = [];
    if (m.status !== "active") b.push(`<span class="cbadge bad">DEPRECATED UPSTREAM</span>`);
    if (!m.supported) b.push(`<span class="cbadge dhold">UNSUPPORTED SHAPE</span>`);
    if (m.supported && m.status === "active") {
      b.push(m.refs ? `<span class="cbadge ok">REFS ≤${m.max_refs}</span>`
                    : `<span class="cbadge hold">NO REFERENCES</span>`);
      if ((m.max_px || 0) >= 3840) b.push(`<span class="cbadge dim">4K NATIVE</span>`);
      else if (m.max_px) b.push(`<span class="cbadge accent">${m.max_px >= 2048 ? "2K" : "1K"} MAX</span>`);
      if (m.price_per_image) b.push(`<span class="cbadge dim">$${esc(m.price_per_image)}/IMG</span>`);
      else b.push(`<span class="cbadge dline">NO PRICE</span>`);
    }
    return b.join("");
  };
  const catState = uiGet("catalogFilters", null) || { q: "", refs: true, fourk: false, priced: false };

  function renderCatalogBrowser() {
    const host = $("#catalog-host");
    const f = catState;
    const hits = catalogAll.filter(m =>
      (!f.refs || m.refs)
      && (!f.fourk || (m.max_px || 0) >= 3840)
      && (!f.priced || m.price_per_image)
      && (!f.q || `${m.label} ${m.developer} ${m.provider_model_id}`.toLowerCase().includes(f.q.toLowerCase())));
    const groups = [
      ["ANCHORS REFERENCES", "Takes your approved reference images as input — the only kind that can hold a face, a vehicle or a location on model.", hits.filter(m => m.refs)],
      ["STYLE STUDIES ONLY", "Text-only input. Cannot hold a subject on model — use these for look development, never for a canon panel.", hits.filter(m => !m.refs)],
    ];
    const row = m => `
      <div class="cat-row${m.status !== "active" && m.enabled ? " dep-on" : ""}${!m.supported ? " unsup" : ""}">
        ${m.preview
          ? `<img class="cat-thumb" src="${esc(m.preview)}" alt="" title="Witnessed test frame — rendered through your key">`
          : m.enabled && m.supported
            ? `<button class="cred-tile cat-prevbtn" data-prev="${esc(m.id)}" title="Render a test frame — ${m.price_per_image ? `~$${esc(m.price_per_image)}` : "engine rate"}, billed to your key">${devTileHtml(m.developer)}</button>`
            : `<span class="cred-tile">${devTileHtml(m.developer)}</span>`}
        <span class="cat-id">
          <span class="cat-name">${esc(m.label)}</span>
          <span class="cat-meta">${esc((m.developer || "").toUpperCase())} · VIA ${esc(m.connector.toUpperCase())} · ${esc(m.provider_model_id)}${!m.supported ? " · PARAMETER SHAPE NOT YET MAPPED" : ""}</span>
        </span>
        <span class="cat-badges">${badges(m)}</span>
        <span class="cat-enable">${!m.supported
          ? `<span class="cat-noten">NOT ENABLEABLE</span>`
          : `<button class="cat-en${m.enabled ? " on" : ""}" data-mid="${esc(m.id)}">${m.enabled ? "✓ ENABLED" : "ENABLE"}</button>`}</span>
      </div>`;
    host.innerHTML = `
      <div class="cat-wrap">
        <div class="cat-bar">
          <input id="cat-q" placeholder="Search ${cxStats.total} models…" value="${esc(f.q)}">
          <label class="cat-f${f.refs ? " on" : ""}"><input type="checkbox" id="cat-refs"${f.refs ? " checked" : ""}> Anchors references</label>
          <label class="cat-f${f.fourk ? " on" : ""}"><input type="checkbox" id="cat-4k"${f.fourk ? " checked" : ""}> 4K native only</label>
          <label class="cat-f${f.priced ? " on" : ""}"><input type="checkbox" id="cat-pr"${f.priced ? " checked" : ""}> Price published</label>
          <span class="cat-showing">SHOWING ${hits.length}</span>
          <button class="text-act" id="cat-close">Close</button>
        </div>
        ${groups.map(([title, sub, rows]) => rows.length ? `
          <div class="cat-group-head"><span class="cat-group-title">${title}</span>
          <span class="cat-group-sub">${sub}</span></div>
          ${rows.map(row).join("")}` : "").join("")}
        ${!hits.length ? `<p class="mini" style="padding:16px 4px">Nothing matches in ${cxStats.total} synced models — loosen a filter. The per-panel picker can also search fal's live catalog.</p>` : ""}
        <div class="cat-strip">
          <span class="cred-tile">NO<br>PRV</span>
          <span class="cat-strip-txt"><b>Render a test frame</b> — click an enabled model's tile.
          One standardised in-house prompt through your own key; the result becomes that
          model's preview — our witnessed output, not the vendor's marketing sample.</span>
          <span class="cat-strip-cost">BILLED TO YOUR KEY AT THE ENGINE'S RATE</span>
        </div>
      </div>`;
    $("#cat-q").oninput = e => {
      f.q = e.target.value; uiSet("catalogFilters", f); renderCatalogBrowser();
      const q = $("#cat-q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length);
    };
    $("#cat-refs").onchange = e => { f.refs = e.target.checked; uiSet("catalogFilters", f); renderCatalogBrowser(); };
    $("#cat-4k").onchange = e => { f.fourk = e.target.checked; uiSet("catalogFilters", f); renderCatalogBrowser(); };
    $("#cat-pr").onchange = e => { f.priced = e.target.checked; uiSet("catalogFilters", f); renderCatalogBrowser(); };
    $("#cat-close").onclick = () => { $("#catalog-host").innerHTML = ""; };
    $$(".cat-prevbtn", host).forEach(btn => {
      btn.onclick = async () => {
        const m = catalogAll.find(x => x.id === btn.dataset.prev);
        const cost = m.price_per_image ? `~$${m.price_per_image}` : "the engine's rate";
        if (!(await askConfirm(`Render a test frame with ${m.label}`,
          `One standardised prompt through your own key (${cost} — billed to you). The result becomes this model's preview.`,
          "Render"))) return;
        btn.textContent = "…";
        btn.disabled = true;
        try {
          const r = await api("/api/connectors/preview", { method: "POST", json: { id: m.id } });
          m.preview = r.preview;
          toast(`${m.label}: test frame witnessed — it is the preview now.`);
        } catch (err) { toast(err.message, true); }
        renderCatalogBrowser();
      };
    });
    $$(".cat-en", host).forEach(btn => {
      btn.onclick = async () => {
        const m = catalogAll.find(x => x.id === btn.dataset.mid);
        try {
          await api("/api/connectors/enable", { method: "POST",
            json: { id: m.id, on: !m.enabled } });
          m.enabled = !m.enabled;
          const st = await api("/api/connectors");
          cxStats = st.stats;
          toast(m.enabled
            ? `${m.label} enabled — it now appears in every Model dropdown.`
            : `${m.label} disabled — it leaves the dropdowns; its takes keep their records.`);
        } catch (err) { toast(err.message, true); }
        renderCatalogBrowser();
      };
    });
  }

  function expandCustomChip(cid, row) {
    const e = customs.find(x => x.id === cid);
    if (!e) return;
    const box = $(`.cred-expand[data-expand="custom"]`);
    box.classList.remove("hidden");
    const t = engAll[`custom:${cid}`]?.last_test;
    box.innerHTML = `
      <div class="cred-form">
        <p class="cred-form-kicker">${esc((e.label || e.id).toUpperCase())} — YOUR ENDPOINT</p>
        <p class="mini">${esc(e.model)} · ${esc(e.base_url)} · key ${esc(e.key_hint)}${t ? ` · LAST TEST ${t.ok ? "PASS" : "FAIL"} ${esc(stamp(t.at))}` : ""}</p>
        <div class="row" style="margin-top:8px">
          <button class="ghost" data-f="t">Test</button>
          <button class="danger" data-f="d">Remove</button>
          <button class="ghost" data-f="x">Close</button>
        </div>
      </div>`;
    $("[data-f=t]", box).onclick = async () => {
      try {
        const r = await api("/api/settings/test", { method: "POST", json: { provider: `custom:${cid}` } });
        toast(`${cid} connection OK — ${r.model}`);
      } catch (err) { toast(err.message, true); }
      renderSettings();
    };
    $("[data-f=d]", box).onclick = async () => {
      if (!(await askConfirm(`Remove engine ${cid}`,
        "Its key is deleted from settings and it leaves every Model dropdown. Candidates it generated keep their records.",
        "Remove", true))) return;
      try {
        await api(`/api/settings/engines/${encodeURIComponent(cid)}`, { method: "DELETE" });
        toast(`${cid} removed.`);
      } catch (err) { toast(err.message, true); }
      renderSettings();
    };
    $("[data-f=x]", box).onclick = () => box.classList.add("hidden");
  }

  }  // end steady-state wiring (F1)

  // Debug tools (user request 2026-08-03): the mock engine and page-text
  // edit mode. Both state exactly what they are; neither touches canon.
  const mockBox = $("#dbg-mock");
  if (mockBox) {
    mockBox.checked = !!settings.engines?.mock?.configured;
    const mockState = () => {
      $("#dbg-mock-state").textContent = mockBox.checked
        ? "ON — MOCK ENGINE listed in every model dropdown" : "";
    };
    mockState();
    mockBox.onchange = async () => {
      try {
        await api("/api/settings", { method: "POST",
                                     json: { debug_mock: mockBox.checked } });
        mockState();
        toast(mockBox.checked
          ? "Mock engine ON — pick MOCK ENGINE in any model dropdown; nothing will be billed."
          : "Mock engine OFF — dropdowns show real engines only.");
      } catch (err) { mockBox.checked = !mockBox.checked; toast(err.message, true); }
    };
    const te = $("#dbg-textedit");
    te.checked = textEditMode();
    te.onchange = () => {
      localStorage.setItem("sbTextEdit", te.checked ? "1" : "0");
      updateTextEditChip();
      toast(te.checked ? "Text edit mode ON — Alt-click any text to rewrite it."
                       : "Text edit mode OFF — your rewrites stay until cleared.");
    };
    const count = () => {
      const n = Object.keys(_textOverrides).length;
      $("#dbg-text-count").textContent =
        n ? `${n} REWRITE${n > 1 ? "S" : ""} ACTIVE` : "NO REWRITES YET";
    };
    count();
    $("#dbg-text-clear").onclick = async () => {
      if (!(await askConfirm("Clear all text edits",
          "Every rewritten string on this install returns to its original text.",
          "Clear edits", true))) return;
      try {
        await api("/api/debug/text-overrides", { method: "DELETE" });
        _textOverrides = {};
        count();
        toast("Text edits cleared — originals are back.");
        showView("settings");
      } catch (err) { toast(err.message, true); }
    };
  }
}

async function renderLessons() {
  const host = $("#lessons-list");
  if (!host) return;
  const lessons = await api("/api/lessons");
  host.innerHTML = "";

  const addRow = document.createElement("div");
  addRow.className = "row";
  addRow.innerHTML = `
    <input type="text" id="lesson-new" placeholder="new project-wide rule…" style="flex:1"
      title="A standing rule injected into every future prompt (all boards, all panels). Name unwanted content to exclude it, or state a directive to follow.">
    <button class="ghost" id="lesson-add">+ Add rule</button>`;
  host.append(addRow);
  const doAdd = async () => {
    const reason = $("#lesson-new").value.trim();
    if (!reason) return;
    try {
      await api("/api/lessons", { method: "POST", json: { reason } });
      toast("Rule added — every future prompt includes it.");
      renderLessons();
    } catch (err) { toast(err.message, true); }
  };
  $("#lesson-add", addRow).onclick = doAdd;
  $("#lesson-new", addRow).addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); doAdd(); }
  });

  if (!lessons.length) {
    host.append(Object.assign(document.createElement("p"), {
      className: "mini",
      textContent: "No standing rules yet. Add one above — rejection reasons now feed the panel's own REJECTION FEEDBACK automatically instead of landing here.",
    }));
  }
  for (const l of lessons) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <span style="flex:1">✕ ${esc(l.reason)} <span class="mini">(${esc(l.source)}, ${esc(l.added_at)})</span></span>
      <button class="ghost">Remove</button>`;
    $("button", row).onclick = async () => {
      try {
        await api("/api/lessons/remove", { method: "POST", json: { reason: l.reason } });
        toast("Lesson removed.");
        renderLessons();
      } catch (err) { toast(err.message, true); }
    };
    host.append(row);
  }
}

/* ----------------------------------------------------------- setup wizard */

async function renderWizard() {
  useTemplate("tpl-wizard");
  const state = await api("/api/state");

  // The screenplay analysis is stored server-side (data/wizard_analysis.json)
  // so design languages survive browser storage. Older sessions kept it only
  // in localStorage — migrate that copy up once, and mirror the authoritative
  // copy back down for the localStorage readers below.
  let wizAnalysis = null;
  try {
    const srv = await api("/api/wizard/analysis");
    wizAnalysis = srv && Object.keys(srv).length ? srv : null;
  } catch { /* server copy unavailable; fall back to local */ }
  const localAnalysis = wizACache();
  if (!wizAnalysis && localAnalysis) {
    wizAnalysis = localAnalysis;
    api("/api/wizard/analysis", { method: "PUT", json: localAnalysis }).catch(() => {});
  }
  if (wizAnalysis) wizACacheSet(wizAnalysis);
  $("#wiz-screenplay").innerHTML = state.screenplay
    ? `<span class="badge APPROVED">SCREENPLAY</span> ${esc(state.screenplay.file)} — uploaded ${esc(state.screenplay.uploaded_at || "")}`
    : `<span class="badge REJECTED">NO SCREENPLAY</span> upload it on the Dashboard first — analysis and drafting need it`;

  // Engine state (user ruling 2026-08-01): keys live in Settings only —
  // the wizard's model selector states the gate when none are configured
  // and lists only engines that actually have a key.
  const engReady = await fillNarrativeSelect($("#wiz-provider"));
  if (!engReady) {
    $("#wiz-analyze").disabled = true;
    $("#wiz-analyze").title = "Add a Gemini or OpenAI key in Settings first.";
    $("#wiz-draft").disabled = true;
    $("#wiz-draft").title = "Add a Gemini or OpenAI key in Settings first.";
    $("#wiz-analyze-lock").textContent =
      "NO ENGINE CONFIGURED — ADD A GEMINI OR OPENAI KEY IN SETTINGS";
  }

  // ---- Color swatches (NON-CANON, user-directed 2026-08-05) ----
  // The one action glyph in the app: everything else states its verb in
  // words. A pencil sits ON the colour because that is the thing being
  // edited, and a word there would cover it (user 2026-08-06).
  const PENCIL = `<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">`
    + `<path d="M2 12.6V14h1.4l7.9-7.9-1.4-1.4L2 12.6Z" fill="currentColor"/>`
    + `<path d="m13.1 4.2-1.3-1.3.9-.9a.6.6 0 0 1 .9 0l.4.4a.6.6 0 0 1 0 .9l-.9.9Z" fill="currentColor"/>`
    + `</svg>`;
  // A swatch is an ordinary COLOR_PALETTE reference: pure solid pixels
  // (engines study these images — name/hex live in the notes, never the
  // pixels). Manual add is the user's act and lands approved; generated
  // proposals are grounded in the saved Bible, grouped by its Design
  // Languages, and stay client-side until each approval creates the
  // reference.
  let syncSwatchGen = () => {};
  {
    const col = $('.wiz-col[data-role="COLOR_PALETTE"]');
    const colorIn = $("[data-f=sw-color]", col);
    const hexIn = $("[data-f=sw-hex]", col);
    colorIn.oninput = () => { hexIn.value = colorIn.value; };
    hexIn.oninput = () => {
      if (HEXOK.test(hexIn.value.trim())) colorIn.value = hexIn.value.trim();
    };
    $("[data-f=sw-add]", col).onclick = async () => {
      const hex = hexIn.value.trim();
      if (!HEXOK.test(hex)) return toast("A swatch needs a full hex — like #8A4B2E.", true);
      const name = $("[data-f=sw-name]", col).value.trim();
      try {
        const ref = await api("/api/references/swatch",
          { method: "POST", json: { hex, name: name || undefined, approve: true } });
        toast(`${ref.id} — ${name ? name.toUpperCase() + " " : ""}${hex.toUpperCase()} added as an approved palette swatch.`);
        $("[data-f=sw-name]", col).value = "";
        refreshRefs();
      } catch (err) { toast(err.message, true); }
    };

    const genHost = $("#swatch-gen");
    const strip = $("#swatch-strip");

    // The colour block itself, without the card chrome — rebuilt in place
    // by a recolour so the edit does not cost a re-render of the strip.
    const swBlock = (hex, pair) => pair
      ? `<span class="sw-pair"><i style="background:${esc(hex)}"></i><i style="background:${esc(pair)}"></i></span>`
      : `<span class="sw-tile" style="background:${esc(hex)}"></span>`;
    const paintCard = (card, hex, pair) => {
      ($(".sw-tile", card) || $(".sw-pair", card)).outerHTML = swBlock(hex, pair);
      $(".sw-hex", card).textContent = hex + (pair ? " · " + pair : "");
      card.dataset.hex = hex;
      card.dataset.pair = pair || "";
    };

    const renderSwatchStrip = r => {
      const total = r.groups.reduce((n, g) => n + g.swatches.length, 0);
      if (!total) { strip.innerHTML = ""; return; }
      const tile = sw => swBlock(sw.hex, sw.pair_hex)
        + `<button class="sw-edit" data-f="ed" title="Edit this colour — repaints the swatch in place, keeping its name and its place in this review">${PENCIL}</button>`;
      const headTxt = n =>
        `${n} PROPOSED${r.model ? ` BY ${(r.model || "").toUpperCase()}` : ""} — NOT CANON UNTIL APPROVED`;
      // A hero is the colour a designer splashes through that faction's
      // sets so the area reads on sight (user 2026-08-06) — stated on the
      // group so it can be found without reading every card.
      const heroOf = g => g.swatches.find(sw => sw.hero);
      strip.innerHTML = `
        <p class="prop-head">${esc(headTxt(total))}</p>
        ${r.groups.map(g => `
          <p class="lang-label">${esc(g.language.toUpperCase())} — ${g.swatches.length}${
            heroOf(g) ? `<span class="sw-hero">HERO ${esc(heroOf(g).hex)}</span>` : ""}</p>
          <div class="sw-grid">${g.swatches.map(sw => `
            <div class="sw-card${sw.hero ? " is-hero" : ""}" data-ref="${esc(sw.ref_id)}"
                 data-hex="${esc(sw.hex)}" data-pair="${esc(sw.pair_hex || "")}">
              ${tile(sw)}
              <span class="sw-name">${esc(sw.name)}${sw.hero ? '<span class="sw-hero">HERO</span>' : ""}</span>
              <span class="sw-hex">${esc(sw.hex)}${sw.pair_hex ? " · " + esc(sw.pair_hex) : ""}</span>
              ${sw.cite ? `<span class="sw-cite">${esc(sw.cite)}</span>` : ""}
              <span class="sw-acts">
                <button class="text-act ok-act" data-f="ap">Approve</button>
                <button class="text-act" data-f="rj">Reject</button>
              </span>
            </div>`).join("")}</div>`).join("")}
        <div class="sw-bar">
          <button class="ghost" data-f="ap-all">Approve all ${total}</button>
          <button class="text-act" data-f="discard">Discard the rest</button>
        </div>`;
      // D8 ruling: a verdict is a reference-status record — approvals and
      // rejections both land in the approval log, never in thin air.
      const verdict = (card, status) =>
        api(`/api/references/${card.dataset.ref}/status`, { method: "POST",
          json: { status, reason: status === "REJECTED"
            ? "swatch proposal rejected in review" : "" } })
          .then(() => card.remove());
      const tidy = () => {
        $$(".lang-label", strip).forEach(l => {
          const grid = l.nextElementSibling;
          if (grid && grid.classList.contains("sw-grid") && !grid.children.length) {
            grid.remove(); l.remove();
          }
        });
        const left = $$(".sw-card", strip).length;
        if (!left) { strip.innerHTML = ""; return; }
        $(".prop-head", strip).textContent = headTxt(left);
        $("[data-f=ap-all]", strip).textContent = `Approve all ${left}`;
      };
      $$(".sw-card", strip).forEach(card => {
        $("[data-f=ap]", card).onclick = async () => {
          try { await verdict(card, "APPROVED"); } catch (err) { toast(err.message, true); }
          refreshRefs(); tidy();
        };
        $("[data-f=rj]", card).onclick = async () => {
          try { await verdict(card, "REJECTED"); } catch (err) { toast(err.message, true); }
          tidy();
        };
        // Recolour in place: the reference keeps its id, so approvals
        // already recorded against it are not orphaned by an edit.
        $("[data-f=ed]", card).onclick = async () => {
          const vals = await modal({
            title: "Edit this swatch colour",
            body: "Repaints the swatch where it stands — it keeps its id, its name "
              + "and its place in this review, and only its pixels change.",
            fields: [
              { name: "hex", label: "Colour", value: card.dataset.hex,
                placeholder: "#8A4B2E", color: true },
              { name: "pair", label: "Value-key pair", value: card.dataset.pair || "",
                placeholder: "leave empty for one flat colour", color: true,
                hint: "The same hue at the opposite value key — renders as two halves." },
            ],
            confirmLabel: "Repaint swatch",
          });
          if (vals === null) return;
          try {
            const rec = await api(`/api/references/${card.dataset.ref}/swatch`,
              { method: "POST", json: { hex: vals.hex, pair_hex: vals.pair } });
            paintCard(card, rec.hex, rec.pair_hex);
            toast(`${card.dataset.ref} repainted ${rec.hex}.`);
            refreshRefs();
          } catch (err) { toast(err.message, true); }
        };
      });
      $("[data-f=ap-all]", strip).onclick = async () => {
        for (const card of $$(".sw-card", strip)) {
          try { await verdict(card, "APPROVED"); }
          catch (err) { toast(err.message, true); break; }
        }
        refreshRefs(); tidy();
      };
      $("[data-f=discard]", strip).onclick = async () => {
        for (const card of $$(".sw-card", strip)) {
          try { await verdict(card, "REJECTED"); }
          catch (err) { toast(err.message, true); break; }
        }
        tidy();
      };
    };

    // Pending proposals from an earlier run survive reload — rebuild the
    // strip from the persisted PROVISIONAL refs.
    const restoreStrip = async () => {
      const pend = (await api("/api/references").catch(() => []))
        .filter(x => x.source === "swatch-proposal" && x.status === "PROVISIONAL");
      if (!pend.length) return;
      const groups = {};
      pend.forEach(x => {
        const parts = (x.notes || "").split(" · ");
        // wizard.HERO_MARK rides as the last segment — pop it before the
        // rest is read positionally, or it lands in the citation.
        const hero = parts[parts.length - 1] === "HERO";
        if (hero) parts.pop();
        const [hex, pair] = (parts[2] || "").split(" / ");
        (groups[parts[0] || "PALETTE"] ||= []).push({
          ref_id: x.id, name: parts[1] || hex || x.id,
          hex: hex || "#000000", pair_hex: pair || null, hero,
          cite: parts.slice(3).join(" · ") });
      });
      renderSwatchStrip({ groups: Object.entries(groups)
        .map(([language, swatches]) => ({ language, swatches })) });
    };
    restoreStrip();

    // SWATCH_GENERATE_RULING (2026-08-06): the act moved to step 5, where
    // its precondition — a SAVED Bible — is met. Before a save exists the
    // row does not render at all: step 5's own gate already explains the
    // situation two lines above.
    syncSwatchGen = async () => {
      const bible = await api("/api/style-bible").catch(() => ({ text: "" }));
      if (!genHost?.isConnected) return;
      if (!engReady || !bible.text.trim()) { genHost.innerHTML = ""; return; }
      genHost.innerHTML = `
        <button class="ghost" data-f="sw-go">Generate palette swatches</button>
        <span class="swatch-note" data-f="sw-result">FROM THE SAVED BIBLE · LANDS IN STEP 1 / COLOR PALETTE</span>
        <div data-f="sw-busy"></div>`;
      const go = $("[data-f=sw-go]", genHost);
      go.onclick = async () => {
        go.disabled = true;
        // A model call over a whole Bible is a real wait, and swapping the
        // button's label said almost nothing (user 2026-08-06). The canon
        // .busy strip states it, with the elapsed clock.
        const busy = startBusy($("[data-f=sw-busy]", genHost), "Reading the Bible…",
          "Proposing only colours it can ground in your saved Bible.");
        try {
          const r = await api("/api/wizard/swatches", { method: "POST",
            json: { provider: $("#wiz-provider").value } });
          renderSwatchStrip(r);
          // The result is stated where the act was taken, and links to
          // where the output actually landed.
          const n = r.groups.reduce((t, g) => t + g.swatches.length, 0);
          $("[data-f=sw-result]", genHost).innerHTML =
            `${n} SWATCH${n === 1 ? "" : "ES"} PROPOSED IN COLOR PALETTE · `
            + `<button class="text-act" data-f="sw-goto">REVIEW THEM</button>`;
          $("[data-f=sw-goto]", genHost).onclick = () => {
            const el = $('.wiz-col[data-role="COLOR_PALETTE"]');
            if (el) window.scrollTo({
              top: el.getBoundingClientRect().top + window.scrollY - 80,
              behavior: "smooth" });
          };
        } catch (err) { toast(err.message, true); }
        busy.done();
        go.disabled = false;
      };
    };
    await syncSwatchGen();
  }

  // D2 (PRODUCTION_DESIGN_V3) — the six-step rail: numbered chips in the
  // header strip; done numbers go --ok (same truth as the step badges),
  // the current chip is bordered; clicking scrolls with the band offset.
  const RAIL = [[1, "Anchors"], [2, "Scan"], [3, "Interview"],
                [4, "Cast"], [5, "Bible"], [6, "Bake-off"]];
  const rail = $("#wiz-rail");
  rail.innerHTML = RAIL.map(([n, l]) =>
    `<button class="rail-chip" data-goto-step="${n}"><span class="rail-num">${n}</span> ${esc(l)}</button>`).join("");
  const railCurrent = () => {
    let cur = 1;
    for (const [n] of RAIL) {
      const el = $(`.panel.step[data-step="${n}"]`);
      if (el && el.getBoundingClientRect().top <= 140) cur = n;
    }
    $$(".rail-chip", rail).forEach(c =>
      c.classList.toggle("current", +c.dataset.gotoStep === cur));
  };
  rail.onclick = e => {
    const chip = e.target.closest(".rail-chip");
    if (!chip) return;
    const el = $(`.panel.step[data-step="${chip.dataset.gotoStep}"]`);
    if (el) window.scrollTo({
      top: el.getBoundingClientRect().top + window.scrollY - 80,
      behavior: "smooth" });
  };
  const onRailScroll = () => {
    if (!rail.isConnected)
      return window.removeEventListener("scroll", onRailScroll);
    railCurrent();
  };
  window.addEventListener("scroll", onRailScroll, { passive: true });
  railCurrent();

  // ---- Step 6: model bake-off (after the production design is set) ----
  // Every engine renders the same screenplay location; suggestions come from
  // the Step 2 analysis's recurring locations.
  const locInput = $("#wiz-sample-loc");
  const sampleLocs = wizACache()?.key_locations || [];
  $("#wiz-sample-locs").innerHTML = sampleLocs.map(l => `<option value="${esc(l)}"></option>`).join("");
  locInput.value = localStorage.getItem("wizardSampleLoc") || sampleLocs[0] || "";
  locInput.oninput = () => localStorage.setItem("wizardSampleLoc", locInput.value);
  const sampleSubject = () => locInput.value.trim();

  const renderSamples = async () => {
    const [samples, s] = await Promise.all([api("/api/wizard/samples"), api("/api/settings")]);
    const host = $("#wiz-samples");
    host.innerHTML = "";
    // Only engines with a configured key compete (user ruling
    // 2026-08-01). With none, the three slots stay — nameless — and
    // state how they earn a name.
    const eng = s.engines || {};
    const keyFor = p => p === "gemini" ? s.gemini_api_key_set : s.openai_api_key_set;
    const failedP = p => keyFor(p) && eng[p]?.last_test?.ok === false;
    const avail = ["gemini", "openai", "openai-chat"]
      .filter(p => keyFor(p) && !failedP(p));
    if (eng.mock?.configured) avail.push("mock");  // debug dry-run engine
    const failedList = ["gemini", "openai", "openai-chat"].filter(failedP);
    for (const p of failedList) {
      const smp = samples.find(x => x.provider === p);
      const col = document.createElement("div");
      col.className = "wiz-col";
      col.innerHTML = `
        <div class="wiz-col-head"><span class="f-label">${esc(smp?.label || p)}</span></div>
        <p class="mini" style="color:var(--bad)">KEY FAILED ITS TEST &mdash;
        retest or replace it in Settings before this engine competes.</p>`;
      host.append(col);
    }
    if (!avail.length && !failedList.length) {
      host.innerHTML = [1, 2, 3].map(() => `
        <div class="wiz-col">
          <div class="wiz-col-head"><span class="f-label">&mdash;</span></div>
          <p class="mini">NO ENGINE CONFIGURED &mdash; add a Gemini or
          OpenAI key in Settings and this slot names itself.</p>
        </div>`).join("");
      return;
    }
    for (const smp of samples.filter(x => avail.includes(x.provider))) {
      const isPref = smp.provider === s.preferred_provider;
      const col = document.createElement("div");
      col.className = "wiz-col";
      col.innerHTML = `
        <div class="wiz-col-head">
          <span class="f-label">${esc(smp.label)}</span>
          ${isPref ? '<span class="badge APPROVED">DEFAULT</span>' : ""}
        </div>
        ${smp.subject ? `<p class="mini" style="margin:2px 0 6px" title="The screenplay location this sample rendered.">${esc(smp.subject)}</p>` : ""}
        ${smp.has_image
          ? `<img class="wiz-sample" src="/api/wizard/samples/${esc(smp.provider)}/image?t=${Date.now()}" alt="${esc(smp.provider)} sample">`
          : '<p class="mini">no sample yet</p>'}
        <div class="row" style="margin-top:auto">
          ${smp.has_image && !isPref ? `<button class="primary" data-f="pick">Make default</button>` : ""}
          <button class="ghost" data-f="regen" title="Regenerate this engine's sample">${smp.has_image ? "Regenerate" : "Generate"}</button>
        </div>`;
      const img = $("img.wiz-sample", col);
      if (img) img.onclick = () => openLightbox(
        [{ src: img.src, caption: `${smp.label} — ${smp.subject || "style sample"}` }], 0);
      const pick = $("[data-f=pick]", col);
      if (pick) pick.onclick = async () => {
        try {
          await api("/api/settings", { method: "POST", json: { preferred_provider: smp.provider } });
          toast(`${smp.label} is now the default image model everywhere.`);
          renderSamples();
        } catch (err) { toast(err.message, true); }
      };
      $("[data-f=regen]", col).onclick = async (e) => {
        e.target.disabled = true;
        const subject = sampleSubject();
        const busy = startBusy($("#wiz-samples-busy"),
          `Rendering ${subject || "the fallback test scene"} with ${smp.label}…`, "~30–90 s");
        try {
          await api(`/api/wizard/samples/${smp.provider}`, { method: "POST", json: { subject } });
          renderSamples();
        } catch (err) { toast(err.message, true); e.target.disabled = false; }
        finally { busy.done(); }
      };
      host.append(col);
    }
  };
  renderSamples();

  $("#wiz-samples-go").onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    const s = await api("/api/settings");
    const eng = s.engines || {};
    const keyFor = p => p === "gemini" ? s.gemini_api_key_set : s.openai_api_key_set;
    const failedP = p => keyFor(p) && eng[p]?.last_test?.ok === false;
    const avail = ["gemini", "openai", "openai-chat"]
      .filter(p => keyFor(p) && !failedP(p));
    if (eng.mock?.configured) avail.push("mock");  // debug dry-run engine
    const failedList = ["gemini", "openai", "openai-chat"].filter(failedP);
    // Failed-key columns are renderSamples' job — this handler only
    // decides whether anything can run.
    if (!avail.length) {
      btn.disabled = false;
      return toast(failedList.length
        ? "Every configured key failed its test — retest or replace in Settings."
        : "Save at least one API key first.", true);
    }
    const subject = sampleSubject();
    const busy = startBusy($("#wiz-samples-busy"),
      `Rendering ${subject || "the fallback test scene"} with ${avail.length} engine(s)…`,
      "one 1K render each; they appear below as they finish");
    try {
      for (const p of avail) {
        busy.label(`Rendering ${subject || "the fallback test scene"} with ${p}…`);
        try { await api(`/api/wizard/samples/${p}`, { method: "POST", json: { subject } }); }
        catch (err) { toast(`${p}: ${err.message}`, true); }
        renderSamples();
      }
      toast("Samples ready — compare and click “Make default” on the winner.");
    } finally { busy.done(); btn.disabled = false; }
  };

  let wizAnchorIds = [];
  const refreshRefs = async () => {
    // Pending swatch proposals live in the review strip, not the anchor
    // rows (D8: they persist as PROVISIONAL refs so verdicts are records).
    const refs = (await api("/api/references")).filter(r =>
      r.status !== "REJECTED"
      && !(r.source === "swatch-proposal" && r.status === "PROVISIONAL"));
    // Every anchor in a column rides the bible draft (user ruling
    // 2026-08-05: inclusion IS the selection — no per-row checkbox).
    wizAnchorIds = refs.filter(r =>
      $(`.wiz-col[data-role="${CSS.escape(roleHead(r.role))}"]`)).map(r => r.id);
    for (const col of $$(".wiz-col[data-role]")) {
      const role = col.dataset.role;
      const mine = refs.filter(r => roleHead(r.role) === role);
      const badge = $("[data-f=state]", col);
      badge.className = `badge ${mine.length ? "APPROVED" : "LOCKED"}`;  // audit #4: unmet is a gate, not a failure
      badge.textContent = mine.length ? `${mine.length}` : "NONE";
      const list = $("[data-f=list]", col);
      list.innerHTML = "";
      const lbItems = mine.map(r => ({
        src: `/api/references/${r.id}/image`, caption: `${r.id} — ${r.role}` }));
      mine.forEach((r, i) => {
        const item = document.createElement("div");
        item.className = "wiz-thumb";
        // No use-in-draft checkbox (user ruling 2026-08-05): if an anchor
        // is in the column, it is used — inclusion IS the selection.
        item.innerHTML = `
          <img src="/api/references/${esc(r.id)}/image?thumb=1" loading="lazy" alt="${esc(r.id)}">
          <span class="meta mini">${esc(r.id)}${r.notes && r.role === "COLOR_PALETTE"
            ? `<span class="wiz-thumb-note">${esc(r.notes.split(" · ").slice(0, 2).join(" · "))}</span>` : ""}
          </span>
          <button class="danger" data-f="del" title="Permanently delete this image">×</button>`;
        $("img", item).onclick = () => openLightbox(lbItems, i);
        $("[data-f=del]", item).onclick = async () => {
          if (!(await askConfirm(`Delete ${r.id} forever`,
            "It is removed from the reference library and future generations. This cannot be undone.",
            "Delete forever", true))) return;
          try {
            await api(`/api/references/${r.id}`, { method: "DELETE" });
            toast(`${r.id} permanently deleted.`);
            refreshRefs();
          } catch (err) { toast(err.message, true); }
        };
        list.append(item);
      });
    }
  };
  await refreshRefs();

  for (const col of $$(".wiz-col[data-role]")) {
    // D1 — the raw file input hides behind a styled Add images act.
    const addBtn = $("[data-f=addbtn]", col);
    if (addBtn) addBtn.onclick = () => $("[data-f=files]", col).click();
    $("[data-f=files]", col).addEventListener("change", async (e) => {
      const files = e.target.files;
      if (!files.length) return;
      const role = col.dataset.role;
      try {
        for (const f of files) {
          const fd = new FormData();
          fd.append("file", f);
          fd.append("role", role);
          fd.append("controls", "");
          fd.append("does_not_control", "");
          fd.append("notes", "style anchor added via setup wizard");
          const ref = await api("/api/references", { method: "POST", body: fd });
          await api(`/api/references/${ref.id}/status`, { method: "POST", json: { status: "APPROVED" } });
        }
        toast(`${files.length} image(s) added as approved ${role.replaceAll("_", " ").toLowerCase()} anchor(s).`);
        e.target.value = "";
        refreshRefs();
      } catch (err) { toast(err.message, true); }
    });
  }

  // ---- Cast the film (Step 3, mock 5b) ----
  // A door into the Reference SUBJECTS shelf: the uncast block lists what
  // the screenplay read found, grouped by kind. Casting a chip creates the
  // library card and opens its photo chooser.
  const uncastExpanded = new Set();
  const renderSubjectTags = () => {
    const host = $("#wiz-subj-tags");
    api("/api/subjects").then(existing => {
      const fresh = uncastRecommendations(existing);
      // Scoped to the cast step — the step-2 section labels share the
      // class now (D3), and a global query grabbed the wrong one.
      const label = $('.panel.step[data-step="4"] .uncast-label');
      if (label) label.textContent = fresh.length
        ? `FOUND IN THE SCREENPLAY — ${fresh.length} UNCAST`
        : "FOUND IN THE SCREENPLAY — UNCAST";
      if (!fresh.length) {
        const ran = !!wizACache();
        host.innerHTML = `<span class="mini">${ran
          ? "everything the read found is cast" : "run Step 2 to get casting proposals"}</span>`;
        return;
      }
      host.innerHTML = "";
      const CAP = 8;
      const castOne = r => api("/api/subjects", { method: "POST", json: {
        name: r.name, kind: r.kind || "CHARACTER",
        subtitle: r.subtitle || "", traits: r.traits || [],
        source: "screenplay analysis" } });
      const refreshAll = async () => {
        renderSubjectTags();
        await renderSubjectGrid();
        wizardStepBadges();
      };
      for (const kind of ["CHARACTER", "VEHICLE", "PROP"]) {
        // TODO(prominence): when the extraction emits mention counts, split
        // PRINCIPALS/SUPPORTING here. Until then rows keep payload order —
        // the read lists principals first in practice; never re-sort.
        const recs = fresh.filter(r => (r.kind || "CHARACTER").toUpperCase() === kind);
        if (!recs.length) continue;
        const open = uncastExpanded.has(kind);
        const shown = open ? recs : recs.slice(0, CAP);
        const row = document.createElement("div");
        row.className = "uncast-row";
        row.innerHTML = `<span class="uncast-kind">${kind}S</span><span class="chips" data-f="chips"></span>
          <button class="ghost uncast-bulk" data-f="bulk"
            title="Casts each of these with the single-cast path — cards appear in the library ready for photos.">${
            recs.length <= CAP ? `Cast these ${recs.length}` : `Cast first ${CAP}`}</button>`;
        const chips = $("[data-f=chips]", row);
        for (const r of shown) {
          const chip = document.createElement("span");
          chip.className = "chip";
          chip.title = `${r.subtitle ? r.subtitle + "\n" : ""}Cast this subject — creates its card in the library.`;
          chip.style.cursor = "pointer";
          const n = r.mentions ?? r.prominence;
          chip.innerHTML = `+ ${esc(r.name)}${n ? ` <span class="suffix">·${n}</span>` : ""}`;
          chip.onclick = async () => {
            try {
              const subj = await castOne(r);
              toast(`${r.name} cast — add its reference photos.`);
              await refreshAll();
              // The next action is always adding reference photos — open the
              // chooser for the new card immediately.
              $(`.subj-card[data-sid="${subj.id}"] [data-f=up]`)?.click();
            } catch (err) { toast(err.message, true); }
          };
          chips.append(chip);
        }
        if (recs.length > CAP || open) {
          const more = document.createElement("span");
          more.className = "chip more";
          more.style.cursor = "pointer";
          more.textContent = open ? "▴ fewer" : `▾ ${recs.length - CAP} more`;
          more.onclick = () => {
            open ? uncastExpanded.delete(kind) : uncastExpanded.add(kind);
            renderSubjectTags();
          };
          chips.append(more);
        }
        $("[data-f=bulk]", row).onclick = async e => {
          e.target.disabled = true;
          let ok = 0, failed = 0;
          for (const r of recs.slice(0, CAP)) {
            try { await castOne(r); ok++; } catch { failed++; }
          }
          toast(`${ok} cast${failed ? ` — ${failed} failed` : ""}.`, !!failed);
          refreshAll();
        };
        host.append(row);
      }
    });
  };

  // The card component lives with the SUBJECTS shelf (buildSubjectCard) —
  // this grid is just its second host (one component, two hosts; plan D3).
  const renderSubjectGrid = async () => {
    const grid = $("#wiz-subj-grid");
    const [subjects, refs] = await Promise.all([api("/api/subjects"), api("/api/references")]);
    grid.innerHTML = subjects.length ? "" :
      `<p class="mini" style="grid-column:1/-1">No subjects yet — click a recommended tag above or add one manually.</p>`;
    for (const s of subjects)
      grid.append(buildSubjectCard(s, refs,
        () => { renderSubjectTags(); renderSubjectGrid(); wizardStepBadges(); },
        { viewLink: true }));
  };

  $("#wiz-subj-add").onclick = async () => {
    const name = $("#wiz-subj-name").value.trim();
    if (!name) return toast("Give the subject a name first.", true);
    try {
      const subj = await api("/api/subjects", { method: "POST", json: {
        name, kind: $("#wiz-subj-kind").value, source: "manual" } });
      $("#wiz-subj-name").value = "";
      toast(`${name} cast — add its reference photos.`);
      renderSubjectTags();
      await renderSubjectGrid();
      wizardStepBadges();
      $(`.subj-card[data-sid="${subj.id}"] [data-f=up]`)?.click();
    } catch (err) { toast(err.message, true); }
  };
  renderSubjectTags();
  renderSubjectGrid();

  // ---- Step 2: screenplay analysis ----
  // The stored analysis is the source of truth for design languages; cards
  // edit it in place. Model choice locks after a read.
  const getAnalysis = () => wizAnalysis;
  const saveAnalysis = a => {
    wizAnalysis = a;
    wizACacheSet(a);
    api("/api/wizard/analysis", { method: "PUT", json: a }).catch(() => {});
    wizardStepBadges();  // confirmations/drops move the step-2 badge
  };

  const renderAnalyzeLock = () => {
    const a = getAnalysis();
    const lockHost = $("#wiz-analyze-lock");
    $("#wiz-provider").disabled = !!a;
    $("#wiz-analyze").classList.toggle("hidden", !!a);
    if (!a) { lockHost.innerHTML = ""; return; }
    const sp = state.screenplay;
    const bits = [
      esc(sp?.file || a.screenplay || "screenplay"),
      sp?.uploaded_at ? `uploaded ${esc(sp.uploaded_at)}` : "",
      a.analyzed_at ? `read ${esc(a.analyzed_at)}` : "",
      a.model ? `by ${esc(a.model)}` : "",
    ].filter(Boolean).join(" — ");
    lockHost.innerHTML = `<span class="badge APPROVED">READ</span> ${bits}
      <button class="ghost" id="wiz-analyze-unlock" style="margin-left:8px" title="Re-enable the model picker and re-run the analysis. The current one is kept until a re-run succeeds.">Unlock &amp; re-run</button>`;
    $("#wiz-analyze-unlock").onclick = async () => {
      if (!(await askConfirm("Unlock the screenplay analysis",
        "Re-running the read keeps everything you've confirmed — design languages, environments, and their location assignments survive by name. New finds arrive as PROPOSED for your review. Answered questions and cast subjects are never touched.",
        "Unlock"))) return;
      $("#wiz-provider").disabled = false;
      $("#wiz-analyze").classList.remove("hidden");
      lockHost.innerHTML = `<span class="mini">unlocked — pick a model and re-run; the previous analysis stands until then</span>`;
    };
  };

  const expandedWorlds = new Set();
  let qShowAll = false;

  // ---- read locations as a finder list (plan P4 / R2) ----
  // Flat, screenplay order, rendered through the shared buildLocFinder code
  // path. Sheet state uses the coverage table's own match semantics:
  // normalized whole-word containment either direction against the slugline
  // groups, then the group's server-computed sheet match is inherited.
  let wizCov;
  const normLoc = s => String(s).replace(/[’‘]/g, "'").replace(/[“”]/g, '"')
    .replace(/[—–−]/g, "-").replace(/\s+/g, " ").toLowerCase().trim();
  const wordIn = (needle, hay) => !!needle && new RegExp(
    `(?<![a-z0-9])${needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![a-z0-9])`).test(hay);
  // D4 (PRODUCTION_DESIGN_V3) — labelled columns, fixed tracks; the gate
  // is a withheld verb (NEEDS THE BIBLE), never a button; once the Bible
  // exists the cell is the real verb.
  const wizLocRow = (name, sheet, extraCell = "") => `
    <div class="loc-row wiz-loc-row">
      <span class="loc-slug" title="${esc(name)}">${esc(name)}</span>
      ${extraCell || `<span class="loc-env-blank">&mdash;</span>`}
      <span class="loc-state">${sheet ? esc(sheet.spec_id) : "NONE"}</span>
      ${sheet
        ? `<button class="loc-open" data-open="${esc(sheet.spec_id)}">Open sheet</button>`
        : state.stage_summary?.production_design?.bible_saved
          ? `<button class="block-act loc-draft" data-loc="${esc(name)}">Make sheet</button>`
          : `<span class="wv-tag loc-gate">NEEDS THE BIBLE</span>`}
    </div>`;
  const WIZ_LOC_THEAD = `
    <div class="loc-thead">
      <span>LOCATION</span>
      <span>ENVIRONMENT — ITS VISUAL RULES</span>
      <span>SHEET</span>
      <span></span>
    </div>`;
  const renderWizLocs = async () => {
    const secHost = $("#wiz-locs-sec");
    if (!secHost) return;
    const keyLocs = getAnalysis()?.key_locations || [];
    const envs = (getAnalysis()?.environments || []).filter(e => (e.name || "").trim());
    if (!keyLocs.length && !envs.length) return;
    if (wizCov === undefined) {
      try { wizCov = await api("/api/screenplay/locations"); } catch { wizCov = null; }
      if (!$("#wiz-locs-sec")) return;  // view moved on while fetching
    }
    const groups = wizCov?.available ? wizCov.locations : [];

    if (envs.length) {
      // Grouped (plan P7): rows are the slugline locations, grouped by the
      // read's verbatim assignments — zero fuzzy matching. Anything the
      // read didn't place lands under UNASSIGNED; every row can reassign
      // through the analysis save path.
      const byLoc = Object.fromEntries(groups.map(g => [g.location, g]));
      const assignedTo = {};
      envs.forEach(e => (e.locations || []).forEach(l => { assignedTo[l] = e.name; }));
      const grouped = envs.map(e => ({ name: e.name, locs: e.locations || [] }));
      const unassigned = groups.map(g => g.location).filter(l => !assignedTo[l]);
      if (unassigned.length) grouped.push({ name: "UNASSIGNED", locs: unassigned });
      const total = grouped.reduce((n, g) => n + g.locs.length, 0);
      const envNames = envs.map(e => e.name);
      buildLocFinder(secHost, {
        head: `<div class="loc-head"><span class="uncast-label">LOCATIONS — ${total} · EACH BECOMES ONE BREAKDOWN SHEET</span></div>`,
        headRow: WIZ_LOC_THEAD,
        placeholder: "find a location…",
        rows: (needle, q) => grouped.map(g => {
          const locs = g.locs.filter(n => !needle || n.toUpperCase().includes(needle));
          if (!locs.length) return "";
          return `<div class="loc-group">${esc(g.name.toUpperCase())} — ${locs.length}</div>`
            + locs.map(n => wizLocRow(n, byLoc[n]?.sheet, `
              <select class="loc-reassign" data-loc="${esc(n)}" title="Move this location to another environment — saved to the analysis immediately.">
                ${["UNASSIGNED", ...envNames].map(en =>
                  `<option${(assignedTo[n] || "UNASSIGNED") === en ? " selected" : ""}>${esc(en)}</option>`).join("")}
              </select>`)).join("");
        }).join("") || `<p class="mini">nothing matches "${esc(q)}"</p>`,
        onDraw: () => {
          $$(".loc-reassign", secHost).forEach(sel => sel.onchange = () => {
            const loc = sel.dataset.loc, to = sel.value;
            const a = getAnalysis();
            (a.environments || []).forEach(e => {
              e.locations = (e.locations || []).filter(l => l !== loc);
            });
            if (to !== "UNASSIGNED") {
              const e = (a.environments || []).find(x => x.name === to);
              if (e) e.locations = [...(e.locations || []), loc];
            }
            saveAnalysis(a);
            toast(`${loc} → ${to === "UNASSIGNED" ? "unassigned" : to}.`);
            renderWorlds();
          });
        },
      });
      return;
    }

    // Flat (plan P4): key_locations in screenplay order. Sheet state uses
    // the coverage table's match semantics against the slugline groups and
    // inherits the group's server-computed sheet.
    const matchOf = name => {
      const n = normLoc(name);
      return groups.find(g => {
        const gl = normLoc(g.location);
        return wordIn(gl, n) || wordIn(n, gl);
      }) || null;
    };
    buildLocFinder(secHost, {
      head: `<div class="loc-head"><span class="uncast-label">LOCATIONS — ${keyLocs.length} · EACH BECOMES ONE BREAKDOWN SHEET</span></div>`,
      headRow: WIZ_LOC_THEAD,
      placeholder: "find a location…",
      rows: (needle, q) => keyLocs
        .filter(n => !needle || n.toUpperCase().includes(needle))
        .map(n => wizLocRow(n, matchOf(n)?.sheet))
        .join("") || `<p class="mini">nothing matches "${esc(q)}"</p>`,
    });
  };

  const renderWorlds = () => {
    const analysis = getAnalysis();
    const host = $("#wiz-analysis");
    if (!analysis) { host.innerHTML = ""; return; }
    const worlds = analysis.design_worlds || [];
    // The reveal strip (plan P1 / R1): the read presents as a summary, not a
    // wall. Counts link to their sections; segments render only when their
    // data exists (no "0 ENVIRONMENTS", no "0 ANSWERED").
    const proposedN = worlds.filter(w => w.status === "PROPOSED").length;
    const envN = (analysis.environments || []).length;
    const qN = (analysis.unresolved || []).length;
    const answeredN = (analysis.unresolved || [])
      .filter(q => analysis.question_answers?.[q]?.answer).length;
    // D3 (PRODUCTION_DESIGN_V3) — the read presents as five stat tiles
    // plus the logline in its own accent-ruled column; one box made the
    // logline read as a footnote to the counts. Open questions carry the
    // only colored number: --accent while any remain.
    const tile = (goto, n, label, cls = "") =>
      `<a class="read-tile" data-goto="${goto}"><b class="read-num ${cls}">${n}</b>
       <span class="read-lab">${label}</span></a>`;
    const tiles = [
      tile("langs", worlds.length, `DESIGN LANGUAGE${worlds.length === 1 ? "" : "S"}`),
      tile("envs", envN, `ENVIRONMENT${envN === 1 ? "" : "S"}`),
      tile("locs", (analysis.key_locations || []).length, "LOCATIONS"),
      tile("subjects", (analysis.subjects || []).length, "SUBJECTS"),
      tile("questions", qN, "OPEN QUESTIONS", qN - answeredN > 0 ? "attn" : ""),
    ].join("");
    host.innerHTML = `
      <div class="read-strip">
        <div class="read-tiles">${tiles}</div>
        ${analysis.logline ? `<div class="read-logline">
          <span class="read-log-kicker">LOGLINE</span>
          <p>${esc(analysis.logline)}</p></div>` : ""}
      </div>
      <div class="fgroup" id="wiz-langs-sec" style="margin-top:16px">
        <span class="uncast-label">DESIGN LANGUAGES — EACH BECOMES A BIBLE SECTION</span>
        <div id="wiz-world-tags" class="chips" style="margin-bottom:8px"></div>
        <div id="wiz-worlds"></div>
      </div>
      <div id="wiz-envs-sec" style="margin-top:16px">
        <div class="uncast-label">ENVIRONMENTS — THE VISUAL RULES A PLACE INHERITS</div>
        <div id="wiz-envs"></div>
      </div>
      ${(analysis.key_locations || []).length || (analysis.environments || []).length ? `<div id="wiz-locs-sec" style="margin-top:16px"></div>` : ""}
      ${qN ? `<div id="wiz-questions-sec" style="margin-top:16px">
        <div class="uncast-label">OPEN QUESTIONS — ${answeredN} OF ${qN} ANSWERED · ANSWERS RIDE THE BIBLE DRAFT</div>
        <div id="wiz-questions" class="q-grid"></div>
      </div>` : ""}`;
    const GOTO = {
      langs: () => $("#wiz-langs-sec"), envs: () => $("#wiz-envs-sec"),
      locs: () => $("#wiz-locs-sec"), questions: () => $("#wiz-questions-sec"),
      subjects: () => $('.panel.step[data-step="3"]'),
    };
    $$(".read-tile", host).forEach(a => a.onclick = () => {
      const el = GOTO[a.dataset.goto]?.();
      if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 80,
                                behavior: "smooth" });
    });
    const tagHost = $("#wiz-world-tags", host);
    const wHost = $("#wiz-worlds", host);
    if (!worlds.length) tagHost.innerHTML = `<span class="mini">none — every board will use only the global sections of the Bible</span>`;
    worlds.forEach((w, i) => {
      const open = expandedWorlds.has(i);
      const proposed = w.status === "PROPOSED";
      const chip = document.createElement("span");
      chip.className = "chip" + (open ? " open" : "") + (proposed ? " proposed" : "");
      chip.style.cursor = "pointer";
      // PROPOSED chip vocabulary (Gap 5 ruling §1): dashed --hold, suffixed
      // CONFIRM / DROP in place. Confirmation is the default state — a
      // confirmed chip is exactly the plain chip, no badge.
      if (proposed) {
        chip.innerHTML = `${esc(w.name || "(unnamed)")}<span class="prop-tail"> · PROPOSED — </span>` +
          `<button class="prop-act" data-f="confirm" title="Keep this design language — it becomes a Bible section on the next draft.">CONFIRM</button>` +
          `<span class="prop-tail"> / </span>` +
          `<button class="prop-act" data-f="drop" title="Remove this proposal — re-running the read can propose it again.">DROP</button>`;
        $("[data-f=confirm]", chip).onclick = e => {
          e.stopPropagation();
          const a = getAnalysis();
          delete a.design_worlds[i].status;
          saveAnalysis(a);
          renderWorlds();
          toast(`${w.name} confirmed — it becomes a Bible section on the next draft.`);
        };
        $("[data-f=drop]", chip).onclick = e => {
          e.stopPropagation();
          const a = getAnalysis();
          a.design_worlds.splice(i, 1);
          saveAnalysis(a);
          expandedWorlds.clear();
          renderWorlds();
          toast(`"${w.name}" dropped — re-running the read can propose it again.`);
        };
      } else {
        chip.textContent = w.name || "(unnamed)";
      }
      chip.title = `${w.description || ""}\nClick to ${open ? "collapse" : "expand"}.`;
      chip.onclick = e => {
        if (e.target.closest(".prop-act")) return;
        open ? expandedWorlds.delete(i) : expandedWorlds.add(i);
        renderWorlds();
      };
      tagHost.append(chip);
    });
    const addChip = document.createElement("span");
    addChip.className = "chip";
    addChip.style.cursor = "pointer";
    addChip.textContent = "+ Add design language";
    addChip.title = "Add a design language the analysis missed — opens ready to edit.";
    addChip.onclick = () => {
      const a = getAnalysis();
      a.design_worlds = a.design_worlds || [];
      a.design_worlds.push({ name: "", description: "", keywords: [] });
      saveAnalysis(a);
      expandedWorlds.add(a.design_worlds.length - 1);
      renderWorlds();
      const rows = $$("#wiz-worlds .panel-card");
      $("[data-f=edit]", rows[rows.length - 1])?.click();
    };
    tagHost.append(addChip);
    if (proposedN) tagHost.insertAdjacentHTML("afterend",
      `<p class="mini">The self-check found ${proposedN === 1 ? "a named group" : `${proposedN} named groups`} no language covers. Confirming writes its Bible section; the read never adds one itself.</p>`);
    worlds.forEach((w, i) => {
      if (!expandedWorlds.has(i)) return;
      const row = document.createElement("div");
      row.className = "panel-card";
      row.style.marginBottom = "10px";
      row.innerHTML = `
        <div class="head">
          <span class="pid">${esc(w.name || "(unnamed)")}</span>
          <span style="margin-left:auto"></span>
          <button class="ghost" data-f="edit" title="Edit this design language, then Save.">Edit</button>
          <button class="danger" data-f="del" title="Delete this design language — it will be left out of the Bible draft.">Delete</button>
        </div>
        <div class="fgroup"><span class="f-label">Name</span>
          <input type="text" data-f="name" value="${esc(w.name || "")}" disabled title="Section name in the Bible — one design language per visual culture."></div>
        <div class="fgroup"><span class="f-label">What defines its look</span>
          <input type="text" data-f="notes" value="${esc(w.description || "")}" disabled></div>
        <div class="fgroup" title="Lowercase trigger words used to auto-match this design language to board content.">
          <span class="f-label" style="display:flex;align-items:center;gap:10px">Keywords
            <button class="ghost" data-f="derive" disabled style="margin-left:auto;font-size:11px;padding:3px 9px">Derive from screenplay</button>
          </span>
          <input type="text" data-f="keywords" value="${esc((w.keywords || []).join(", "))}" disabled></div>`;
      const editBtn = $("[data-f=edit]", row);
      const nameInput = $("[data-f=name]", row);
      const deriveBtn = $("[data-f=derive]", row);
      // Derive is gated on a name, and the gate reads as state: the button
      // stays visible-disabled with its unmet condition in the tooltip.
      const syncDerive = () => {
        const named = !!nameInput.value.trim();
        deriveBtn.disabled = nameInput.disabled || !named;
        deriveBtn.title = named
          ? "Scan the screenplay for mentions of this name and fill up to 20 trigger words that travel with them. Deterministic — no model call; review before saving."
          : "Enter a name first — the scan looks for its words in the screenplay.";
      };
      syncDerive();
      nameInput.addEventListener("input", syncDerive);
      deriveBtn.onclick = async () => {
        const name = nameInput.value.trim();
        deriveBtn.disabled = true;
        try {
          const r = await api(`/api/screenplay/keywords?name=${encodeURIComponent(name)}`);
          if (!r.available) return toast("No screenplay text to scan — upload the screenplay first.", true);
          if (!r.hits) return toast(`The screenplay never mentions "${name}" — nothing to derive.`, true);
          $("[data-f=keywords]", row).value = r.keywords.join(", ");
          toast(`${r.keywords.length} keywords from ${r.hits} mentions — review, then Save.`);
        } catch (err) { toast(err.message, true); }
        finally { syncDerive(); }
      };
      editBtn.onclick = () => {
        if (editBtn.textContent === "Edit") {
          $$("input[data-f]", row).forEach(x => x.disabled = false);
          syncDerive();
          editBtn.textContent = "Save";
          editBtn.className = "primary";
          $("[data-f=name]", row).focus();
          return;
        }
        const a = getAnalysis();
        a.design_worlds[i] = {
          ...a.design_worlds[i],
          name: $("[data-f=name]", row).value.trim() || w.name,
          description: $("[data-f=notes]", row).value.trim(),
          keywords: $("[data-f=keywords]", row).value.split(",").map(s => s.trim()).filter(Boolean),
        };
        // Editing-and-saving a proposed world is an implicit confirm
        // (Gap 5 ruling §1) — flip the visual immediately.
        if (a.design_worlds[i].status === "PROPOSED") delete a.design_worlds[i].status;
        saveAnalysis(a);
        toast(`${a.design_worlds[i].name} saved.`);
        renderWorlds();
      };
      $("[data-f=del]", row).onclick = async () => {
        if (!(await askConfirm(`Delete design language "${w.name}"`,
          "It will be left out of the Bible draft. Re-running the analysis can propose it again.",
          "Delete", true))) return;
        const a = getAnalysis();
        a.design_worlds.splice(i, 1);
        saveAnalysis(a);
        expandedWorlds.clear();
        renderWorlds();
        toast(`"${w.name}" deleted.`);
      };
      wHost.append(row);
    });

    // ---- open questions as the interview (plan P2 / R3) ----
    // One answerable row per question; state lives in the analysis payload
    // (question_answers, keyed by question text) via the existing save path.
    const qHost = $("#wiz-questions", host);
    if (qHost) {
      const qs = analysis.unresolved || [];
      const Q_CAP = 4;  // D5 — four visible, two columns
      const shown = qShowAll ? qs : qs.slice(0, Q_CAP);
      shown.forEach(q => {
        const st = (analysis.question_answers || {})[q] || {};
        const i = qs.indexOf(q);
        const row = document.createElement("div");
        row.className = "q-row" + (st.answer ? " answered" : "") + (st.deferred ? " deferred" : "");
        row.innerHTML = `
          <span class="q-idx">Q${String(i + 1).padStart(2, "0")}</span>
          <div class="q-main">
            <p class="q-text">${esc(q)}</p>
            ${st.answer ? `<p class="q-answer">A — ${esc(st.answer)}</p>` : ""}
          </div>
          <span class="q-actions">
            ${st.answer
              ? `<button class="text-act" data-f="answer">Edit</button>`
              : `<button class="ghost" data-f="answer">Answer</button>
                 <button class="text-act" data-f="defer">${st.deferred ? "Reconsider" : "Decide later"}</button>`}
          </span>`;
        const patch = updates => {
          const a = getAnalysis();
          a.question_answers = a.question_answers || {};
          a.question_answers[q] = { ...(a.question_answers[q] || {}), ...updates };
          saveAnalysis(a);
          renderWorlds();
        };
        $("[data-f=answer]", row).onclick = () => {
          const main = $(".q-main", row);
          if ($("input", main)) return;
          const input = document.createElement("input");
          input.type = "text";
          input.value = st.answer || "";
          input.placeholder = "your answer — Enter saves, Esc cancels";
          input.title = "Appended to the interview as a Q/A pair and honored by the Bible draft.";
          main.append(input);
          input.focus();
          input.onkeydown = e => {
            if (e.key === "Escape") renderWorlds();
            if (e.key !== "Enter") return;
            const v = input.value.trim();
            patch({ answer: v, deferred: false });
            if (v) toast("Answer saved — it rides into the Bible draft.");
          };
        };
        const defer = $("[data-f=defer]", row);
        if (defer) defer.onclick = () => patch({ deferred: !st.deferred });
        qHost.append(row);
      });
      if (qs.length > shown.length || qShowAll) {
        const more = document.createElement("button");
        more.className = "text-act q-more";
        more.textContent = qShowAll ? "▴ SHOW FEWER" : `▾ ${qs.length - shown.length} MORE`;
        more.onclick = () => { qShowAll = !qShowAll; renderWorlds(); };
        qHost.append(more);
      }
    }

    // ---- environment cards (mock 6a) — plan P7 / Gap 6 ----
    // Same governance as languages: PROPOSED until confirmed, edit-and-save
    // implicitly confirms, and a manual + Environment door.
    const envHost = $("#wiz-envs", host);
    if (envHost) {
      const envs = analysis.environments || [];
      envHost.innerHTML = `
        ${envs.length ? `<div class="env-grid"></div>`
          : `<div class="env-empty">NO ENVIRONMENTS IN THIS READ — RE-RUN TO EXTRACT THEM</div>`}
        <div class="row" style="margin-top:8px">
          <input type="text" data-f="env-name" placeholder="add manually — name…" style="max-width:200px" title="An environment the read missed — the biome or world panels live in, e.g. FOREST.">
          <input type="text" data-f="env-notes" placeholder="palette, light, atmosphere…" style="max-width:320px" title="One line on what this world looks like — becomes its Bible entry on the next draft.">
          <button class="ghost" data-f="env-add">+ Environment</button>
        </div>`;
      const patchEnvs = (fn) => {
        const a = getAnalysis();
        a.environments = a.environments || [];
        fn(a.environments);
        saveAnalysis(a);
        renderWorlds();
      };
      const grid = $(".env-grid", envHost);
      if (grid) envs.forEach((env, i) => {
        const proposed = env.status === "PROPOSED";
        const card = document.createElement("div");
        card.className = "env-card" + (proposed ? " proposed" : "");
        card.innerHTML = `
          <div class="env-name">${esc(env.name || "(unnamed)")}</div>
          <p class="env-notes">${esc(env.notes || "")}</p>
          <div class="env-facts">${(env.locations || []).length} LOCATIONS
            <button class="text-act" data-f="edit" style="float:right">Edit</button></div>
          ${proposed ? `<div class="env-facts prop-tail" style="margin-top:4px">· PROPOSED —
            <button class="prop-act" data-f="confirm" title="Keep this environment — it becomes a Bible entry on the next draft.">CONFIRM</button> /
            <button class="prop-act" data-f="drop" title="Remove this proposal — re-running the read can propose it again.">DROP</button></div>` : ""}`;
        $("[data-f=edit]", card).onclick = () => {
          card.innerHTML = `
            <input type="text" data-f="name" value="${esc(env.name || "")}" style="margin-bottom:6px" title="Environment name — its Bible entry heading.">
            <input type="text" data-f="notes" value="${esc(env.notes || "")}" placeholder="palette, light, atmosphere…" style="margin-bottom:6px">
            <button class="primary" data-f="save">Save</button>`;
          $("[data-f=save]", card).onclick = () => patchEnvs(list => {
            list[i] = { ...list[i],
              name: $("[data-f=name]", card).value.trim() || env.name,
              notes: $("[data-f=notes]", card).value.trim() };
            // Editing-and-saving a proposed environment = implicit confirm.
            if (list[i].status === "PROPOSED") delete list[i].status;
          });
        };
        $("[data-f=confirm]", card)?.addEventListener("click", () => {
          patchEnvs(list => { delete list[i].status; });
          toast(`${env.name} confirmed — it becomes a Bible entry on the next draft.`);
        });
        $("[data-f=drop]", card)?.addEventListener("click", () => {
          patchEnvs(list => list.splice(i, 1));
          toast(`"${env.name}" dropped — re-running the read can propose it again.`);
        });
        grid.append(card);
      });
      $("[data-f=env-add]", envHost).onclick = () => {
        const name = $("[data-f=env-name]", envHost).value.trim().toUpperCase();
        if (!name) return toast("Give the environment a name first.", true);
        patchEnvs(list => list.push({
          name, notes: $("[data-f=env-notes]", envHost).value.trim(),
          keywords: [], locations: [] }));
        toast(`${name} added — assign its locations below.`);
      };
    }

    renderWizLocs();
  };

  $("#wiz-analyze").onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    const busy = startBusy($("#wiz-analyze-busy"),
      `Reading the screenplay and identifying visual story elements and scenes — ${selectedModelLabel($("#wiz-provider"))}…`,
      "a minute or two");
    try {
      const analysis = await api("/api/wizard/analyze", {
        method: "POST", json: { provider: $("#wiz-provider").value } });
      saveAnalysis(analysis);
      expandedWorlds.clear();
      renderWorlds();
      renderAnalyzeLock();
      renderSubjectTags();
      toast(`Found ${(analysis.design_worlds || []).length} design language(s) and ${(analysis.subjects || []).length} subject(s) — review below.`);
    } catch (err) { toast(err.message, true); }
    finally { busy.done(); btn.disabled = false; }
  };

  renderWorlds();
  renderAnalyzeLock();

  $("#wiz-draft").onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    const busy = startBusy($("#wiz-draft-busy"),
      `Drafting the Art Direction Bible from screenplay, worlds, interview, and reference photos — ${selectedModelLabel($("#wiz-provider"))}…`,
      "this is the big one — a few minutes is normal");
    try {
      // PROPOSED worlds stay out of the draft — confirming is what writes a
      // Bible section (Gap 5 ruling §1).
      const chosenWorlds = (getAnalysis()?.design_worlds || [])
        .filter(w => w.status !== "PROPOSED")
        .map(w => ({
          name: (w.name || "").trim(),
          notes: (w.description || "").trim(),
          keywords: w.keywords || [],
        })).filter(w => w.name);
      // Answered step-2 questions ride into the notes field the drafter
      // already reads — no new payload field (plan P2 / R3).
      const qaLines = (getAnalysis()?.unresolved || [])
        .filter(q => getAnalysis()?.question_answers?.[q]?.answer)
        .map(q => `Q: ${q} / A: ${getAnalysis().question_answers[q].answer}`);
      const chosenEnvs = (getAnalysis()?.environments || [])
        .filter(e => e.status !== "PROPOSED" && (e.name || "").trim())
        .map(e => ({ name: e.name.trim(), notes: (e.notes || "").trim() }));
      const answers = {
        worlds: chosenWorlds,
        environments: chosenEnvs,
        touchstones: $("#wiz-touchstones").value.trim(),
        medium: $("#wiz-medium").value.trim(),
        palette: $("#wiz-palette").value.trim(),
        never: $("#wiz-never").value.trim(),
        notes: [$("#wiz-notes").value.trim(), ...qaLines].filter(Boolean).join("\n"),
        ref_ids: wizAnchorIds,
      };
      const r = await api("/api/wizard/draft-bible", {
        method: "POST", json: { answers, provider: $("#wiz-provider").value } });
      // One bible surface (user-flagged 2026-08-01): the draft lands in
      // the editor it will be saved from. Unsaved prior content is never
      // silently replaced.
      const editor = $("#style-bible");
      if (editor.value.trim() && editor.value.trim() !== r.markdown.trim()) {
        if (!(await askConfirm("Replace the editor content?",
          "The Art Direction Bible editor already holds text. Load the new draft over it? (Nothing is saved until you press Save.)",
          "Load the draft"))) {
          toast(`Draft ready but not loaded — the editor kept your text.`, true);
          return;
        }
      }
      editor.value = r.markdown;
      syncBibleSave();
      $("#style-status").innerHTML =
        `DRAFTED BY ${esc(r.model || "the model").toUpperCase()} — REVIEW, EDIT, THEN SAVE`;
      toast(`Bible drafted by ${r.model} — review below, then save. Search for (PROPOSED) to find its guesses.`);
    } catch (err) { toast(err.message, true); }
    finally { busy.done(); btn.disabled = false; }
  };

  // ---- the Bible itself + project-wide lessons (the PD's living documents) ----
  // Save is disabled while the editor is empty (user-directed 2026-08-05):
  // the gate is readable as state — disabled control + the stated
  // condition beside it — instead of a 422 after the click.
  const syncBibleSave = () => {
    const empty = !$("#style-bible").value.trim();
    $("#style-save").disabled = empty;
    // D8 ruling: the disabled control stays, its condition is the dashed
    // withheld tag beside it — a tag, not a sentence.
    $("#style-save-gate").classList.toggle("hidden", !empty);
  };
  $("#style-bible").addEventListener("input", syncBibleSave);
  const loadBibleEditor = async () => {
    const bible = await api("/api/style-bible");
    $("#style-bible").value = bible.text;
    // No template default exists (director's ruling 2026-08-01) — empty
    // means not yet drafted, and says so.
    $("#style-status").innerHTML = !bible.text.trim()
      ? ""
      : (bible.rev ? `<span class="badge LOCKED">REV ${bible.rev}</span> every future prompt uses this` : "");
    syncBibleSave();
    return bible;
  };
  // Step-state badges (plan v3 C13): each step's h2 states where it stands,
  // from data already fetched or one cheap read. Existing badge classes only.
  const wizardStepBadges = async () => {
    const setB = (n, cls, text) => {
      const h = $(`.panel.step[data-step="${n}"] h2`);
      if (!h) return;
      $(".step-badge", h)?.remove();
      h.insertAdjacentHTML("beforeend",
        ` <span class="badge ${cls} step-badge">${esc(text)}</span>`);
      // D2 — the rail's done mark is the badge's truth, never its own.
      $(`#wiz-rail .rail-chip[data-goto-step="${n}"]`)
        ?.classList.toggle("done", cls === "APPROVED");
    };
    try {
      const [refs, subjects, samples, bible] = await Promise.all([
        api("/api/references"), api("/api/subjects"),
        api("/api/wizard/samples").catch(() => []), api("/api/style-bible"),
      ]);
      const roles = AUTO_ATTACH_HEADS;  // the four-anchor shelf
      const set = roles.filter(role => refs.some(r =>
        r.status === "APPROVED" && roleHead(r.role) === role)).length;
      setB(1, set === roles.length ? "APPROVED" : "PROVISIONAL",
        `${set} OF ${roles.length} SET`);
      // Step 2 reflects review debt: proposed languages AND environments
      // hold the badge at PROVISIONAL until confirmed or dropped (plan P9).
      const proposedN =
        (wizAnalysis?.design_worlds || []).filter(w => w.status === "PROPOSED").length +
        (wizAnalysis?.environments || []).filter(e => e.status === "PROPOSED").length;
      setB(2, !wizAnalysis ? "LOCKED" : proposedN ? "PROVISIONAL" : "APPROVED",
        !wizAnalysis ? "NOT RUN"
          : `${(wizAnalysis.design_worlds || []).length} DESIGN LANGUAGES`
            + (proposedN ? ` · ${proposedN} PROPOSED` : " FOUND"));
      // Step 3 counts the interview itself (mock 2a; swapped ahead of
      // casting per LOCKED_STAGE_PLAN L3) — answered = non-blank.
      const ivFields = ["#wiz-touchstones", "#wiz-medium", "#wiz-palette", "#wiz-never", "#wiz-notes"];
      const ivDone = ivFields.filter(id => $(id)?.value.trim()).length;
      setB(3, ivDone === ivFields.length ? "APPROVED" : "PROVISIONAL",
        `${ivDone} OF ${ivFields.length} ANSWERED`);
      // Cast the film: --hold border while anything stays uncast, --ok when
      // the whole read is cast (plan D4; existing badge classes carry it).
      const uncastN = uncastRecommendations(subjects).length;
      setB(4, !subjects.length && !uncastN ? "LOCKED"
        : uncastN ? "PROVISIONAL" : "APPROVED",
        !subjects.length && !uncastN ? "NONE YET"
        : `${subjects.length} CAST · ${uncastN} UNCAST`);
      setB(5, bible.is_default ? "LOCKED" : "APPROVED",
        bible.is_default ? "NOT DRAFTED" : `SAVED · REV ${bible.rev || 0}`);
      setB(6, samples.length ? "APPROVED" : "LOCKED",
        samples.length ? `${samples.length} SAMPLE${samples.length > 1 ? "S" : ""}`
                       : "NEEDS A SAVED BIBLE");
    } catch { /* badges are commentary — never block the wizard */ }
  };
  wizardStepBadges();

  // The look interview persists per production (user ruling 2026-08-01:
  // a refresh must never lose it): fields load from the server and every
  // change saves back — its answers then bind every bible draft.
  const IV = { "#wiz-touchstones": "touchstones", "#wiz-medium": "medium",
               "#wiz-palette": "palette", "#wiz-never": "never",
               "#wiz-notes": "notes" };
  try {
    const saved = await api("/api/wizard/interview");
    for (const [sel, key] of Object.entries(IV))
      if ($(sel) && !$(sel).value) $(sel).value = saved[key] || "";
    wizardStepBadges();
  } catch { /* first run — nothing saved yet */ }
  const saveInterview = async () => {
    try {
      await api("/api/wizard/interview", { method: "PUT",
        json: Object.fromEntries(Object.entries(IV)
          .map(([sel, key]) => [key, $(sel)?.value.trim() || ""])) });
      $("#wiz-iv-state").textContent =
        "SAVED — THESE ANSWERS BIND EVERY BIBLE DRAFT";
    } catch (err) {
      $("#wiz-iv-state").textContent = `NOT SAVED — ${err.message}`;
    }
  };
  for (const id of Object.keys(IV))
    $(id)?.addEventListener("change", () => { saveInterview(); wizardStepBadges(); });

  await loadBibleEditor();
  $("#style-save").onclick = async () => {
    try {
      const text = $("#style-bible").value.trim();
      if (!text) return toast("The bible is empty — draft it in step 5 (or paste content) before saving.", true);
      const r = await api("/api/style-bible", { method: "PUT", json: { text } });
      $("#style-status").innerHTML = `<span class="badge LOCKED">REV ${r.rev}</span> saved — every future prompt uses this`;
      updateBand();  // Breakdowns unlock themselves right now, visibly
      syncSwatchGen();  // the step-1 swatch gate arms itself right now too
      toast(`Art Direction Bible saved — Breakdowns are open.`);
    } catch (err) { toast(err.message, true); }
  };
  renderLessons();
}

/* ------------------------------------------------------------- references */

// Role → shelf mapping: STYLE rides on every render; SCENES ride when a
// board covers their scene; SUBJECTS ride when their subject is on a panel.
const STYLE_HEADS = ["WORLD_TEXTURE", "COLOR_PALETTE", "CINEMATOGRAPHY_STYLE",
                     "BOARD_RENDERING_STYLE", "BOARD_LAYOUT_STYLE"];
const SCENE_HEADS = ["SCENE_REFERENCE", "LOCATION_GEOMETRY"];
const bucketOfRef = r => STYLE_HEADS.includes(roleHead(r.role)) ? "STYLE"
  : SCENE_HEADS.includes(roleHead(r.role)) ? "SCENE" : "SUBJECT";

// One ref-card, used by every shelf (anatomy per mock 4c).
function buildRefCard(r, lbItems, i) {
  const isAutoAttach = AUTO_ATTACH_HEADS.includes(roleHead(r.role));
  const card = document.createElement("div");
  card.className = `ref-card ${r.status}`;
  const usage = r.status === "REJECTED"
    ? `<div class="juris bad">REJECTED ${esc((r.rejected_at || r.added_at || "").slice(5, 10).replace("-", " "))}${r.status_reason ? ` — ${esc(r.status_reason.toUpperCase())}` : ""}</div>
       <div class="meta">THE PIPELINE CANNOT ATTACH THIS</div>`
    : isAutoAttach
      ? `<div class="meta">AUTO-ATTACHED · ALL RENDERS</div>`
      : (r.used_in ? `<div class="meta">USED IN ${r.used_in} RENDER${r.used_in > 1 ? "S" : ""}</div>` : "");
  card.innerHTML = `
    <img src="/api/references/${r.id}/image?thumb=true" alt="${esc(r.id)}" loading="lazy">
    <div class="body">
      <div><span class="badge ${r.status}">${r.status}</span> <b>${esc(r.id)}</b></div>
      <div class="role">${esc(r.role)}</div>
      <div class="juris ok">CONTROLS ${esc(r.controls.join(" · ") || "—")}</div>
      <div class="juris bad">NOT ${esc(r.does_not_control.join(" · ") || "—")}</div>
      ${r.notes ? `<div class="meta">${esc(r.notes)}</div>` : ""}
      ${usage}
    </div>
    <div class="actions"></div>`;
  $("img", card).onclick = () => openLightbox(lbItems, i);
  const actions = $(".actions", card);
  if (r.status !== "APPROVED") {
    const b = document.createElement("button");
    b.className = "primary"; b.textContent = "Approve";
    b.onclick = () => setRefStatus(r.id, "APPROVED");
    actions.append(b);
  } else {
    const cr = document.createElement("button");
    cr.className = "ghost"; cr.textContent = "Crop";
    cr.title = "Harvest a region of this image (e.g. one cell of a master board) as a new reference with its own narrow role";
    cr.onclick = () => cropToReference(
      { type: "reference", id: r.id }, `/api/references/${r.id}/image`);
    actions.append(cr);
  }
  if (r.status !== "REJECTED") {
    const b = document.createElement("button");
    b.className = "danger"; b.textContent = "Reject";
    b.onclick = async () => {
      const reason = await askText(`Reject ${r.id}`, "Reason",
        { hint: "recorded on the card and in the rejection history; the file is quarantined from the pipeline — Reinstate undoes it",
          confirmLabel: "Reject", danger: true });
      if (reason !== null) setRefStatus(r.id, "REJECTED", reason);
    };
    actions.append(b);
  } else {
    const b = document.createElement("button");
    b.className = "ghost"; b.textContent = "Reinstate as provisional";
    b.onclick = () => setRefStatus(r.id, "PROVISIONAL");
    actions.append(b);
  }
  const del = document.createElement("button");
  del.className = "danger"; del.textContent = "Delete";
  del.title = "Permanently delete this image and its record — journaled in the approval log";
  del.onclick = async () => {
    if (!(await askConfirm(`Delete ${r.id} forever`,
      `${r.role}\nRemoved from the library and from future generations — past candidates keep their own records. This cannot be undone.`,
      "Delete forever", true))) return;
    try {
      await api(`/api/references/${r.id}`, { method: "DELETE" });
      toast(`${r.id} permanently deleted.`);
      renderReferences();
    } catch (err) { toast(err.message, true); }
  };
  actions.append(del);
  return card;
}

/* ---------------------------------------------- subject cards (the shelf) */

const SUBJECT_ROLE_OF = {
  CHARACTER: "CHARACTER_LIKENESS", VEHICLE: "VEHICLE_GEOMETRY", PROP: "PROP_REFERENCE" };

// Screenplay-read recommendations not yet cast — shared by the SUBJECTS
// shelf and wizard step 4 (casting is a door into the same shelf).
function uncastRecommendations(subjects) {
  const analysis = wizACache();
  const have = new Set(subjects.map(s => s.name.toLowerCase()));
  return (analysis?.subjects || [])
    .filter(r => r.name && !have.has(String(r.name).toLowerCase()));
}

// One subject card, two hosts (SUBJECTS shelf + wizard step 4). Anatomy per
// mock 5a: Courier name · bordered kind badge · CAST badge · editable
// identity text · photo mosaic with a + drop slot · Courier facts line.
function buildSubjectCard(s, refs, onChange, opts = {}) {
  const refById = Object.fromEntries(refs.map(r => [r.id, r]));
  const imgs = (s.ref_ids || []).map(id => refById[id]).filter(Boolean)
    .filter(r => r.status !== "REJECTED");
  const lbItems = imgs.map(r => ({
    src: `/api/references/${r.id}/image`, caption: `${s.name} — ${r.id}` }));
  const role = SUBJECT_ROLE_OF[s.kind] || "REFERENCE";
  const used = imgs.reduce((n, r) => Math.max(n, r.used_in || 0), 0);
  const card = document.createElement("div");
  card.className = "subj-card";
  card.dataset.sid = s.id;
  card.innerHTML = `
    <div class="subj-head">
      <span class="subj-name">${esc(s.name.toUpperCase())}</span>
      <span class="kind-badge">${esc(s.kind)}</span>
      <span class="cast-badge cast">CAST</span>
      <button class="danger" data-f="del" title="Remove this title card (its reference images stay in the library)">×</button>
    </div>
    <div class="subj-identity" data-f="identity" title="Identity text — rides in every prompt this subject appears in. Click to edit.">${
      s.subtitle ? esc(s.subtitle) : `<span class="mini">add identity text — it rides in every prompt</span>`}</div>
    ${(s.traits || []).length ? `<div class="subj-traits mini">${esc(s.traits.join(" "))}</div>` : ""}
    <div class="subj-imgs" data-f="imgs"><label class="subj-slot" title="Upload reference photos into this card — each becomes an approved ${esc(role)} — ${esc(s.name.toUpperCase())} reference, grouped under this exact name.">+<input type="file" accept="image/*" multiple data-f="up" class="hidden"></label></div>
    <div class="subj-facts">${imgs.length} PHOTO${imgs.length === 1 ? "" : "S"} · ${esc(role)} — ${esc(s.name.toUpperCase())}${
      used ? ` · USED IN ${used} RENDER${used === 1 ? "" : "S"}` : ""}${
      opts.viewLink ? ` · <button type="button" class="text-act" data-f="view">VIEW IN REFERENCE</button>` : ""}</div>`;
  const imgHost = $("[data-f=imgs]", card);
  const slot = $(".subj-slot", card);
  imgs.forEach((r, i) => {
    const wrap = document.createElement("span");
    wrap.className = "subj-img";
    wrap.innerHTML = `<img src="/api/references/${esc(r.id)}/image?thumb=1" loading="lazy" alt="${esc(r.id)}">
      <button title="Permanently delete ${esc(r.id)}">×</button>`;
    $("img", wrap).onclick = () => openLightbox(lbItems, i);
    $("button", wrap).onclick = async () => {
      if (!(await askConfirm(`Delete ${r.id} forever`,
        "This cannot be undone.", "Delete forever", true))) return;
      try {
        await api(`/api/references/${r.id}`, { method: "DELETE" });
        toast(`${r.id} deleted.`);
        onChange?.();
      } catch (err) { toast(err.message, true); }
    };
    imgHost.insertBefore(wrap, slot);
  });
  $("[data-f=up]", card).addEventListener("change", async e => {
    try {
      for (const f of e.target.files) {
        const fd = new FormData();
        fd.append("file", f);
        await api(`/api/subjects/${s.id}/reference`, { method: "POST", body: fd });
      }
      toast(`${e.target.files.length} reference(s) added to ${s.name}.`);
      onChange?.();
    } catch (err) { toast(err.message, true); }
  });
  $("[data-f=identity]", card).onclick = async () => {
    const v = await askText(`Identity — ${s.name.toUpperCase()}`, "Identity text",
      { value: s.subtitle || "",
        hint: "one line of who or what this is — it rides in every prompt this subject appears in",
        confirmLabel: "Save" });
    if (v === null || v === (s.subtitle || "")) return;
    try {
      await api(`/api/subjects/${s.id}`, { method: "PUT", json: { subtitle: v } });
      toast(`${s.name} identity updated.`);
      onChange?.();
    } catch (err) { toast(err.message, true); }
  };
  $("[data-f=del]", card).onclick = async () => {
    if (!(await askConfirm(`Remove ${s.name}'s title card`,
      "Its reference images stay in the library.", "Remove card", true))) return;
    try {
      await api(`/api/subjects/${s.id}`, { method: "DELETE" });
      toast(`${s.name} removed.`);
      onChange?.();
    } catch (err) { toast(err.message, true); }
  };
  if (opts.viewLink) $("[data-f=view]", card).onclick = () => showView("references");
  return card;
}

// An uncast recommendation: dashed card, no photos yet — casting it creates
// the library card (the only write path, same as the wizard's).
function buildUncastCard(rec, onChange) {
  const card = document.createElement("div");
  card.className = "subj-card uncast";
  card.innerHTML = `
    <div class="subj-head">
      <span class="subj-name">${esc(String(rec.name || "").toUpperCase())}</span>
      <span class="kind-badge">${esc(rec.kind || "CHARACTER")}</span>
      <span class="cast-badge uncast">UNCAST</span>
    </div>
    <div class="subj-identity">${esc(rec.subtitle
      || "Found by the screenplay read — no card yet. Casting it creates the card and carries its screenplay identity into prompts.")}</div>
    <div><button type="button" class="ghost" data-f="cast">Cast this subject</button></div>`;
  $("[data-f=cast]", card).onclick = async () => {
    try {
      await api("/api/subjects", { method: "POST", json: {
        name: rec.name, kind: rec.kind || "CHARACTER",
        subtitle: rec.subtitle || "", traits: rec.traits || [],
        source: "screenplay analysis" } });
      toast(`${rec.name} cast — its card is in the library.`);
      onChange?.();
    } catch (err) { toast(err.message, true); }
  };
  return card;
}

// Adding to the library is a dialog now (the intake row moved behind the
// button per ONE_LIBRARY_PLAN D2) — the vocabulary picker plus a file field.
async function addReferenceDialog() {
  const r = await roleDialog({
    title: "Add reference",
    body: "One image, one job. It enters the library provisional; approve it to make it a canon anchor.",
    prefillHead: "CHARACTER_LIKENESS",
    fields: [
      { name: "file", label: "Image", type: "file" },
      { name: "controls", label: "Controls", placeholder: "comma-separated — or click the chips" },
      { name: "does_not_control", label: "Does not control", placeholder: "e.g. costume, lighting, camera angle" },
      { name: "notes", label: "Notes", placeholder: "provenance — where it came from, what it anchors" },
    ],
    confirmLabel: "Add to library",
  });
  if (r === null) return;
  if (!r.file) { toast("Pick an image file.", true); return; }
  const fd = new FormData();
  fd.append("file", r.file);
  fd.append("role", r.role);
  fd.append("controls", r.controls || "");
  fd.append("does_not_control", r.does_not_control || "");
  fd.append("notes", r.notes || "");
  try {
    const ref = await api("/api/references", { method: "POST", body: fd });
    toast(`${ref.id} added as ${ref.role} (provisional).`);
    renderReferences();
  } catch (err) { toast(err.message, true); }
}

const SHELVES = [
  { key: "STYLE", name: "STYLE", ride: "RIDES ALONG — EVERY RENDER, AUTOMATICALLY",
    note: "", count: n => `${n.total} ANCHOR${n.total === 1 ? "" : "S"} · ${n.roles} ROLE${n.roles === 1 ? "" : "S"}` },
  { key: "SUBJECT", name: "SUBJECTS", ride: "RIDES ALONG — WHEN ITS SUBJECT APPEARS ON A PANEL",
    note: "cast in Production Design step 4 — same cards, this is where they live",
    count: n => `${n.cast} CAST · ${n.uncast} UNCAST` },
  { key: "SCENE", name: "SCENES", ride: "RIDES ALONG — WHEN A BOARD COVERS ITS SCENE",
    note: "promoted takes, light studies, crops of environments",
    count: n => `${n.total} ANCHOR${n.total === 1 ? "" : "S"}` },
];

async function renderReferences() {
  useTemplate("tpl-references");
  _roleCtx = null;  // fresh groups after every library change
  const [refs, subjects] = await Promise.all([
    api("/api/references"), api("/api/subjects")]);

  const st = { APPROVED: 0, PROVISIONAL: 0, REJECTED: 0 };
  refs.forEach(r => { st[r.status] = (st[r.status] || 0) + 1; });
  $("#ref-counts").innerHTML = `
    <span class="stat ok"><i></i>${st.APPROVED} APPROVED</span>
    <span class="stat hold"><i></i>${st.PROVISIONAL} PROVISIONAL</span>
    <span class="stat bad"><i></i>${st.REJECTED} QUARANTINED</span>`;

  $("#ref-add-btn").onclick = addReferenceDialog;

  const q = renderReferences.q ??= { v: "" };
  const search = $("#ref-search");
  search.value = q.v;
  search.addEventListener("input", () => { q.v = search.value; drawShelves(); });

  const matches = r => {
    const needle = q.v.trim().toUpperCase();
    if (!needle) return true;
    return [r.id, r.role, r.notes || "", (r.controls || []).join(" ")]
      .some(x => String(x).toUpperCase().includes(needle));
  };
  const matchesSubj = s => {
    const needle = q.v.trim().toUpperCase();
    if (!needle) return true;
    return [s.name, s.kind || "", s.subtitle || "", (s.traits || []).join(" ")]
      .some(x => String(x).toUpperCase().includes(needle));
  };

  const drawShelves = () => {
    const host = $("#ref-shelves");
    host.innerHTML = "";
    for (const shelf of SHELVES) {
      const section = document.createElement("div");
      section.className = "shelf";
      let countText, fill;
      if (shelf.key === "SUBJECT") {
        // Subject cards ARE this shelf. Subject-role refs not linked to a
        // card — and quarantined ones the mosaic hides — keep the ref-card
        // presentation so their governance stays visible.
        const cast = subjects.filter(matchesSubj);
        const uncast = uncastRecommendations(subjects).filter(matchesSubj);
        const linked = new Set(subjects.flatMap(s => s.ref_ids || []));
        const loose = refs.slice().reverse().filter(r =>
          bucketOfRef(r) === "SUBJECT" && matches(r) &&
          (!linked.has(r.id) || r.status === "REJECTED"));
        countText = shelf.count({ cast: cast.length, uncast: uncast.length });
        fill = grid => {
          grid.classList.add("subj-grid");
          cast.forEach(s => grid.append(buildSubjectCard(s, refs, renderReferences)));
          uncast.forEach(rec => grid.append(buildUncastCard(rec, renderReferences)));
          const lb = loose.map(r => ({
            src: `/api/references/${r.id}/image`,
            caption: `${r.id} — ${r.role} (${r.status})` }));
          loose.forEach((r, i) => grid.append(buildRefCard(r, lb, i)));
        };
      } else {
        const shelfRefs = refs.slice().reverse()
          .filter(r => bucketOfRef(r) === shelf.key && matches(r));
        const roleCount = new Set(shelfRefs.map(r => roleHead(r.role))).size;
        countText = shelf.count({ total: shelfRefs.length, roles: roleCount });
        fill = grid => {
          const lb = shelfRefs.map(r => ({
            src: `/api/references/${r.id}/image`,
            caption: `${r.id} — ${r.role} (${r.status})` }));
          shelfRefs.forEach((r, i) => grid.append(buildRefCard(r, lb, i)));
        };
      }
      section.innerHTML = `
        <div class="shelf-head">
          <span class="shelf-name">${shelf.name}</span>
          <span class="shelf-ride">${esc(shelf.ride)}</span>
          ${shelf.note ? `<span class="hint">${esc(shelf.note)}</span>` : ""}
          <span class="shelf-count">${countText}</span>
        </div>
        <div class="ref-grid" data-f="shelf-grid"></div>`;
      const grid = $("[data-f=shelf-grid]", section);
      fill(grid);
      if (!grid.children.length)
        grid.innerHTML = `<p class="mini" style="grid-column:1/-1">${q.v ? "nothing on this shelf matches" : "nothing on this shelf yet"}</p>`;
      host.append(section);
    }
  };
  drawShelves();
}

async function setRefStatus(id, status, reason = "") {
  try {
    await api(`/api/references/${id}/status`, { method: "POST", json: { status, reason } });
    toast(`${id} → ${status}${status === "REJECTED" ? " (quarantined)" : ""}.`);
    renderReferences();
  } catch (err) { toast(err.message, true); }
}

/* ------------------------------------------------------------------ specs */

async function renderSpecs(openId = null) {
  useTemplate("tpl-specs");

  // The stage locks until Production Design is complete (user ruling
  // 2026-08-01; presentation per LOCKED_STAGE_PLAN L4): normally the
  // band's inert cell keeps you out — this branch answers deep links and
  // stale tabs with the checklist page. Server enforces the same gate on
  // creation (423).
  try {
    const gateState = await api("/api/state");
    if (!gateState.stage_summary?.production_design?.bible_saved) {
      const rows = [...checklistRows(gateState, UNLOCK_NEED.specs),
                    { verb: "Breakdowns unlock automatically", state: "info" }];
      const left = rows.filter(r => r.state === "cur" || r.state === "todo").length;
      $("#main").innerHTML = `<section class="view">` + stageChecklist({
        kicker: `BREAKDOWNS ARE LOCKED — ${left} STEP${left === 1 ? "" : "S"} LEFT`,
        headline: "A sheet draws its language, environments and<br>subjects from the bible. There isn't one yet.",
        rows,
        footnote: "NOTHING HERE IS BLOCKED BY US — EVERY STEP IS YOURS TO MAKE",
      }) + `</section>`;
      bindStageChecklist($("#main"));
      return;
    }
  } catch { /* state unavailable — let the stage render; the server gate holds */ }

  // Work-in-progress survives re-renders, errors, and tab switches: both forms
  // auto-save to localStorage on every keystroke and restore here; the
  // breakdown draft clears only after a successful run.
  const persistForm = (key, ids) => {
    const saved = JSON.parse(localStorage.getItem(key) || "null");
    for (const id of ids) {
      const el = $("#" + id);
      if (!el) continue;
      if (saved && saved[id] !== undefined) el.value = saved[id];
      el.addEventListener("input", () => localStorage.setItem(key, JSON.stringify(
        Object.fromEntries(ids.map(i => [i, $("#" + i)?.value ?? ""])))));
    }
  };
  persistForm("breakdownDraft", ["spec-auto-id", "spec-auto-prompt", "spec-auto-mode", "spec-auto-provider"]);
  persistForm("blankSpecDraft", ["spec-new-id", "spec-new-subject", "spec-new-mode", "spec-new-btype"]);

  await fillNarrativeSelect($("#spec-auto-provider"));

  // The instruction example speaks this production's screenplay, never a
  // hardcoded film's (user ruling 2026-08-01); the same fetch powers the
  // Create Breakdown pre-population.
  Promise.all([api("/api/screenplay/locations"), api("/api/specs")])
    .then(([d, allSpecs]) => {
      const locs = d.locations || [];
      const titleCase = t => String(t).toLowerCase()
        .replace(/(^|[\s/#-])([a-z])/g, (m, a, b) => a + b.toUpperCase());
      const top = locs[0]?.location;
      if (top) {
        const t = titleCase(top);
        // B2: the example IS the placeholder — a trailing italic
        // sentence is prose the field can carry itself.
        const ex = $("#spec-auto-example");
        if (ex) ex.textContent = `"${t} — the scenes the script sets there"`;
        const ta0 = $("#spec-auto-prompt");
        if (ta0 && !ta0.value) ta0.placeholder = `${t} — the scenes the script sets there`;
      }
      if (!locHint) return;
      const norm = x => String(x).toUpperCase().trim();
      let rec = locs.find(l => norm(l.location) === norm(locHint));
      let scene = null;
      if (!rec) {
        for (const l of locs) {
          const hit = (l.scene_list || []).find(s2 => norm(s2.heading) === norm(locHint));
          if (hit) { rec = l; scene = hit; break; }
        }
      }
      const idEl = $("#spec-auto-id");
      if (idEl && !idEl.value.trim()) {
        const base = slugSpecId(rec?.location || locHint)
          .replace(/^_+|_+$/g, "").slice(0, 40) || "BOARD";
        const taken = new Set(allSpecs.map(x => x.specification_id));
        let n = 1, id = `${base}_V001`;
        while (taken.has(id)) { n += 1; id = `${base}_V${String(n).padStart(3, "0")}`; }
        idEl.value = id;
      }
      const promptEl = $("#spec-auto-prompt");
      if (!promptEl || promptEl.value.trim()) return;
      if (scene) {
        promptEl.value = `${scene.heading} — a scene board for this single scene at `
          + `${titleCase(rec.location)}. Extract the set, dressing, props and `
          + `atmosphere the script gives this scene.`;
      } else if (rec) {
        const heads = (rec.scene_list || []).map(s2 => s2.heading);
        promptEl.value = `${titleCase(rec.location)} — a `
          + `${rec.int_ext ? rec.int_ext + " " : ""}location board covering the `
          + `${rec.scenes} scene${rec.scenes === 1 ? "" : "s"} the script sets there`
          + (heads.length ? `: ${heads.slice(0, 4).join("; ")}`
            + (heads.length > 4 ? ` (+${heads.length - 4} more)` : "") : "")
          + `. Focus on the location itself — its set, dressing and atmosphere `
          + `as the script establishes them.`;
      } else {
        promptEl.value = `${titleCase(locHint)} — the scenes the script sets `
          + `there. Focus on the location's set, dressing and atmosphere as established.`;
      }
    }).catch(() => { /* the neutral example stands */ });

  // Sheet IDs are CAPS_WITH_UNDERSCORES — enforce as you type, spaces become
  // underscores.
  for (const idSel of ["#spec-auto-id", "#spec-new-id"]) {
    const el = $(idSel);
    if (el) el.addEventListener("input", () => {
      const pos = el.selectionStart;
      el.value = el.value.toUpperCase().replace(/ /g, "_");
      el.setSelectionRange(pos, pos);
    });
  }

  // Blank sheets seed their board grammar (panel count + allocations only).
  const btypeSel = $("#spec-new-btype");
  if (btypeSel && !btypeSel.options.length) {
    btypeSel.innerHTML = BOARD_TYPES.map(t =>
      `<option value="${t.value}">${esc(t.value)}</option>`).join("");
  }

  // Arriving from the dashboard's location map: seed the draft subject.
  // Create Breakdown arrives with a real pre-population (user ruling
  // 2026-08-02): a deduped Spec ID and a genuine brief composed from
  // what the read already knows about the location — never just the raw
  // hint string. Filled by the locations fetch below.
  const locHint = sessionStorage.getItem("draftLocationHint");
  if (locHint) sessionStorage.removeItem("draftLocationHint");

  // Spec IDs must match the backend's [A-Za-z0-9._-] and by convention are
  // CAPS_WITH_UNDERSCORES. The tooltip states this, but a tooltip is invisible
  // at the moment of choice — the field itself turns whatever is typed into a
  // legal ID as it is typed ("Charlie's cabin v1" → CHARLIES_CABIN_V1).
  const slugSpecId = raw => raw.toUpperCase().replace(/\s+/g, "_")
    .replace(/[^A-Z0-9._-]/g, "").replace(/_{2,}/g, "_");
  // B3 (BREAKDOWN_INTAKE) — the Spec ID help. The copy leads with the
  // reassurance and then states the permanence: users were stalling on a
  // pure-bookkeeping field because the old text opened with "used in
  // filenames, prompts, and the audit trail", which reads as though it
  // steers the render. It does not — the brief and the anchors do.
  //
  // Deviation from mock 13a, reported: the mock's card ends "Auto-filled
  // from the subject if left blank." This install only auto-fills the id
  // from a LOCATION hint (arriving via a location's Create Breakdown),
  // never from the subject field — so that sentence would be false here
  // and is left out rather than shipped as a promise.
  const HELP_TEXT = {
    "spec-id": "<b>Just a name. Does not affect generation.</b> The filing "
      + "label this sheet, its panels, and its boards sort under — pick "
      + "something you'll recognise in a list. CAPS_WITH_UNDERSCORES, "
      + "versioned. It cannot be renamed later.",
  };
  const closeHelp = () => {
    $$(".q-card").forEach(c => c.remove());
    $$(".q-help[aria-expanded=true]").forEach(b => b.setAttribute("aria-expanded", "false"));
  };
  $$(".q-help").forEach(btn => {
    btn.setAttribute("aria-expanded", "false");
    btn.onclick = e => {
      e.preventDefault();
      e.stopPropagation();
      const open = btn.getAttribute("aria-expanded") === "true";
      closeHelp();
      if (open) return;
      const card = document.createElement("div");
      card.className = "q-card";
      card.innerHTML = HELP_TEXT[btn.dataset.help] || "";
      document.body.append(card);
      const r = btn.getBoundingClientRect();
      card.style.top = `${r.bottom + window.scrollY + 8}px`;
      card.style.left =
        `${Math.min(r.left + window.scrollX, window.innerWidth - card.offsetWidth - 16)}px`;
      btn.setAttribute("aria-expanded", "true");
    };
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".q-card") && !e.target.closest(".q-help")) closeHelp();
  });
  window.addEventListener("keydown", e => { if (e.key === "Escape") closeHelp(); });

  const bindSpecIdField = el => el && el.addEventListener("input", () => {
    const slug = slugSpecId(el.value);
    if (slug === el.value) return;
    const caret = slugSpecId(el.value.slice(0, el.selectionStart)).length;
    el.value = slug;
    el.setSelectionRange(caret, caret);
  });
  bindSpecIdField($("#spec-auto-id"));
  bindSpecIdField($("#spec-new-id"));

  $("#spec-auto-form").addEventListener("submit", async e => {
    e.preventDefault();
    const btn = $("#spec-auto-go"), status = $("#spec-auto-status");
    btn.disabled = true;
    const providerSel = $("#spec-auto-provider");
    const busy = startBusy(status,
      `Reading the screenplay and drafting the breakdown sheet with ${providerSel.options[providerSel.selectedIndex].text}…`,
      "this can take a minute or two");
    try {
      const spec = await api("/api/specs/autofill", {
        method: "POST",
        json: {
          specification_id: slugSpecId($("#spec-auto-id").value),
          prompt: $("#spec-auto-prompt").value,
          mode: $("#spec-auto-mode").value,
          provider: $("#spec-auto-provider").value,
        },
      });
      const holds = spec.evidence_ledger.filter(r => r.status === "HOLD").length;
      const qs = (spec.unresolved_questions || []).length;
      toast(`${spec.specification_id} drafted: ${spec.panels.length} panels, ` +
            `${spec.evidence_ledger.length} evidence rows` +
            (holds ? `, ${holds} on HOLD for your review` : "") +
            (qs ? `, ${qs} unresolved questions` : "") + ".");
      localStorage.removeItem("breakdownDraft");
      renderSpecs(spec.specification_id);
    } catch (err) {
      busy.done();
      status.innerHTML = `<span class="badge REJECTED">FAIL</span> ${esc(err.message)}`;
      toast(err.message, true);
      btn.disabled = false;
    }
  });

  $("#spec-new-form").addEventListener("submit", async e => {
    e.preventDefault();
    try {
      const spec = await api("/api/specs", {
        method: "POST",
        json: {
          specification_id: slugSpecId($("#spec-new-id").value),
          subject: $("#spec-new-subject").value,
          mode: $("#spec-new-mode").value,
          board_type: $("#spec-new-btype")?.value || "LOCATION",
        },
      });
      toast(`${spec.specification_id} created.`);
      localStorage.removeItem("blankSpecDraft");
      renderSpecs(spec.specification_id);
    } catch (err) { toast(err.message, true); }
  });

  const specs = await api("/api/specs");
  const tbody = $("#spec-table tbody");
  const countEl = $("#spec-count");
  if (countEl) countEl.textContent = specs.length || "";
  tbody.innerHTML = specs.length ? "" :
    `<tr><td colspan="6" class="mini">NO BREAKDOWN SHEETS YET — RUN A BREAKDOWN ABOVE</td></tr>`;
  for (const s of specs) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><b>${esc(s.specification_id)}</b></td>
      <td>${esc(s.subject)}</td>
      <td class="mini">${esc(s.mode)}</td>
      <td>${s.panel_count}</td>
      <td><span class="badge ${s.status}">${s.status}</span>${s.locked ? ' <span class="badge LOCKED">LOCKED</span>' : ""}</td>
      <td style="white-space:nowrap">
        <button class="ghost" data-f="open">Open</button>
        <!-- B4: Delete is not this row's primary verb — the confirm dialog
           carries the danger at length. -->
        <button class="ghost" data-f="del" title="Permanently delete this breakdown sheet and its candidates">Delete</button>
      </td>`;
    $("[data-f=open]", tr).onclick = () => openSpecEditor(s.specification_id);
    $("[data-f=del]", tr).onclick = async () => {
      const warn = s.locked
        ? `${s.specification_id} is APPROVED and LOCKED. Deleting it anyway removes all its candidate images. Refused automatically if it has any approved candidates or boards.`
        : `All of ${s.specification_id}'s candidate images are removed with it. This cannot be undone.`;
      if (!(await askConfirm(`Delete ${s.specification_id} forever`, warn,
        "Delete forever", true))) return;
      try {
        const r = await api(`/api/specs/${s.specification_id}`, { method: "DELETE" });
        toast(`${r.deleted} deleted — ${r.candidates_removed} candidate record(s), ${r.images_removed} image(s) removed.`);
        renderSpecs();
      } catch (err) { toast(err.message, true); }
    };
    tbody.append(tr);
  }

  const remembered = openId || uiGet("openSpec", null);
  if (remembered && specs.some(x => x.specification_id === remembered))
    openSpecEditor(remembered);
}

async function openSpecEditor(specId) {
  uiSet("openSpec", specId);
  const [{ spec, locked, bible_catalog, bible_inferred }, subjects, allRefs] = await Promise.all([
    api(`/api/specs/${specId}`), api("/api/subjects"), api("/api/references")]);

  // An object "has reference material" when it matches a cast/subject card
  // with linked images, or an approved reference's role suffix.
  const approvedRefs = allRefs.filter(r => r.status === "APPROVED");
  const refInfoFor = (obj) => {
    const o = String(obj).toLowerCase();
    const subj = subjects.find(s => (s.ref_ids || []).length &&
      (o.includes(s.name.toLowerCase()) || s.name.toLowerCase().includes(o)));
    if (subj) return `${subj.name}: ${subj.ref_ids.length} image(s) in the cast & subjects collection`;
    const ref = approvedRefs.find(r => {
      const suffix = String(r.role).split("—")[1]?.trim().toLowerCase();
      return suffix && (o.includes(suffix) || suffix.includes(o));
    });
    return ref ? `${ref.id} (${ref.role})` : null;
  };

  // The library's vocabulary for the object picker (plan D5, mock 5c):
  // existing reference group titles first, then cast card names with photos.
  // Every entry here is guaranteed to match refInfoFor — same strings.
  const librarySuggestions = () => {
    const seen = new Set();
    const out = [];
    const add = (title, suffix) => {
      const k = title.toUpperCase();
      if (!k || seen.has(k)) return;
      seen.add(k);
      out.push({ title: k, suffix });
    };
    for (const r of approvedRefs) {
      const suffix = String(r.role).split("—")[1]?.trim();
      if (!suffix) continue;
      const head = roleHead(r.role);
      add(suffix, head === "SCENE_REFERENCE" ? "SCENE"
        : head === "LOCATION_GEOMETRY" ? "GEOMETRY" : "");
    }
    subjects.filter(s => (s.ref_ids || []).length).forEach(s => add(s.name, ""));
    return out;
  };

  // Scene-paragraph nouns, the dumb way (plan D5): runs of two-plus
  // capitalized words minus leading stopwords — no NLP, no new endpoint.
  const sceneNouns = text => {
    const stop = new Set(["The", "A", "An", "It", "In", "On", "At", "And",
      "But", "Then", "This", "That", "Its", "His", "Her", "Their", "Int", "Ext"]);
    const out = [];
    for (const m of String(text || "").matchAll(/[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+/g)) {
      const words = m[0].split(/\s+/);
      while (words.length && stop.has(words[0])) words.shift();
      if (words.length >= 2) out.push(words.join(" "));
    }
    return [...new Set(out)];
  };
  const host = $("#spec-editor");
  host.innerHTML = "";
  // Environment scope (plan P8, mock 6c). Options come from the Bible's
  // Environments section; analysis-only names stay selectable but say so —
  // the gate readable before it's hit (their entry lands on the next
  // Bible draft). The suggestion is the read's own verbatim location
  // assignment, never a fuzzy guess.
  const wizA = wizACache();
  const envNotes = Object.fromEntries((wizA?.environments || [])
    .filter(e => e.name).map(e => [String(e.name), e.notes || ""]));
  const envAssigned = Object.fromEntries((wizA?.environments || [])
    .filter(e => e.name)
    .flatMap(e => (e.locations || []).map(l => [String(l).toLowerCase(), e.name])));
  const envOptions = [...(bible_catalog?.environments || [])];
  for (const n of Object.keys(envNotes))
    if (!envOptions.some(o => o.toLowerCase() === n.toLowerCase())) envOptions.push(n);
  const specLoc = String((spec.setting || {}).location || "").toLowerCase().trim();
  const envInferred = !specLoc ? "" : envAssigned[specLoc]
    || Object.entries(envAssigned).find(([l]) => l.includes(specLoc) || specLoc.includes(l))?.[1]
    || "";
  const envCurrent = spec.environments?.[0] ?? envInferred;
  let updateCarry = () => {};  // real implementation assigned after markup
  const panel = document.createElement("div");
  panel.className = "panel spec-editor";
  panel.innerHTML = `
    <h3>${esc(spec.specification_id)}
      <span class="badge ${spec.status}">${spec.status}</span>
      ${locked ? '<span class="badge LOCKED">LOCKED</span>' : ""}
      ${spec.autofilled ? '<span class="badge PROVISIONAL">AUTO-FILLED — REVIEW BEFORE APPROVING</span>' : ""}
    </h3>
    ${spec.autofill ? `<p class="mini">Drafted by ${esc(spec.autofill.model)} from: “${esc(spec.autofill.prompt)}”</p>` : ""}
    ${locked ? `
    <div class="gate-strip lock-strip">
      <span class="gate-label" style="color:var(--ink-dim)">LOCKED</span>
      <span class="gate-text">Approved and read-only — objects, panels, and the ledger cannot change here. To edit:</span>
      <button class="block-act" data-f="lock-revise">Create revision</button>
      <button class="block-act" data-f="lock-unlock">Unlock &amp; edit</button>
    </div>` : ""}
    <div id="sp-gate"></div>
    ${(spec.unresolved_questions || []).length ? `
      <div class="report" style="margin-bottom:12px"><b>Unresolved design questions</b> — the screenplay does not answer these; decide them yourself or run a DESIGN_EXPLORATION board:
        <ul>${spec.unresolved_questions.map(q => `<li>${esc(q)}</li>`).join("")}</ul>
      </div>` : ""}
    <div class="spec-section" style="margin-top:14px;border-top:none;padding-top:0">
      <h4>Identity <span class="hint">(what this sheet is)</span></h4>
      <div class="grid-form">
      <label title="What this board is about — a short human-readable name for the location, scene, prop, or character. It appears in prompts and the spec list.">Subject <input type="text" id="sp-subject" value="${esc(spec.subject)}" ${locked ? "disabled" : ""}></label>
      <label title="CANON_EXTRACTION: an official board — only what the screenplay actually supports, tight budget for guesses. DESIGN_EXPLORATION: you are deciding new visual canon — looser budget for inferences, but unsupported inventions are still zero.">Mode
        <select id="sp-mode" ${locked ? "disabled" : ""}>
          <option ${spec.mode === "CANON_EXTRACTION" ? "selected" : ""}>CANON_EXTRACTION</option>
          <option ${spec.mode === "DESIGN_EXPLORATION" ? "selected" : ""}>DESIGN_EXPLORATION</option>
        </select>
      </label>
      <label title="What kind of board this is — it governs slugline behavior. SCENE: one screenplay scene, one time of day for all panels. LOCATION: a place across times — time of day is chosen per panel. ASSET: neutral subject presentation, no slugline. LIGHTING STUDY: derived from an approved panel, geometry locked. MASTER: presentation grammar.">Board type
        <select id="sp-btype" ${locked ? "disabled" : ""}>
          ${BOARD_TYPES.map(t => `<option value="${t.value}" ${(spec.board_type || "LOCATION") === t.value ? "selected" : ""}>${t.label}</option>`).join("")}
        </select>
      </label>
      <label title="The overall board format the approved panels get assembled onto (e.g. wide cinematic production board). Descriptive — the pixel canvas is chosen at assembly time.">Canvas <input type="text" id="sp-canvas" value="${esc(spec.layout?.canvas || "")}" ${locked ? "disabled" : ""}></label>
      </div>
    </div>
    <div class="spec-section">
      <h4>Setting <span class="hint">(the slugline — fields follow the board type)</span></h4>
      <div class="grid-form">
      <label class="setf" data-setf="intext" title="Interior or exterior — the first half of the slugline; it decides the lighting logic (practicals and openings vs sky and sun).">INT / EXT
        <select id="sp-intext" ${locked ? "disabled" : ""}>
          ${["", "INT", "EXT", "INT/EXT"].map(v => `<option value="${v}" ${(spec.setting?.int_ext || "") === v ? "selected" : ""}>${v || "—"}</option>`).join("")}
        </select>
      </label>
      <label class="setf" data-setf="location" title="The location as the screenplay names it — the middle of the slugline.">Location <input type="text" id="sp-location" placeholder="as the slugline names it…" value="${esc(spec.setting?.location || "")}" ${locked ? "disabled" : ""}></label>
      <label class="setf" data-setf="tod" title="Scene boards only: the slugline time of day, exactly as the script's scene heading says it (DAY, NIGHT, DUSK…). All panels of a scene board share it — it overrides any style image's hour or hue.">Time of day <input type="text" id="sp-tod" list="tod-list" placeholder="DAY, DUSK, NIGHT…" value="${esc(spec.setting?.time_of_day || "")}" ${locked ? "disabled" : ""}>
        <datalist id="tod-list">${[...TIMES_OF_DAY, "MAGIC HOUR"].map(t => `<option value="${esc(t)}">`).join("")}</datalist>
      </label>
      <label class="setf" data-setf="atmo" title="Optional weather / light character layered on the hour — one of the Bible's approved atmosphere studies (or your own words). DUSK is the hour; 'dusk and lanterns' is the atmosphere.">Atmosphere <input type="text" id="sp-atmo" list="atmo-list" placeholder="e.g. dusk and lanterns, storm approach…" value="${esc(spec.setting?.atmosphere || "")}" ${locked ? "disabled" : ""}>
        <datalist id="atmo-list">${(bible_catalog?.atmospheres || []).map(t => `<option value="${esc(t)}">`).join("")}</datalist>
      </label>
      </div>
    </div>
    <div class="spec-section">
      <h4>Direction <span class="hint">(what the panels are told)</span></h4>
      <div class="grid-form">
      <label class="wide" title="One flowing paragraph describing the scene this board depicts — location and structure, time of day and light, atmosphere, key contents and their arrangement. Auto-fill drafts it from screenplay evidence; edit it freely. Injected into every panel prompt as THE SCENE, right before the panel's purpose.">The Scene <textarea id="sp-scene" ${locked ? "disabled" : ""} placeholder="One paragraph describing the scene — drafted by auto-fill, or write your own">${esc(spec.scene || "")}</textarea></label>
      <label class="wide" title="One or two sentences of board-specific art direction layered on top of the Art Direction Bible — how THIS board should feel. Goes into every panel prompt as BOARD-SPECIFIC TREATMENT.">Render intent <textarea id="sp-intent" ${locked ? "disabled" : ""}>${esc(spec.render_intent || "")}</textarea></label>
      <label class="wide" title="Board-wide never-include list, one item per line. Merged with each panel's forbidden objects and the project lessons-learned into every render prompt.">Forbidden elements <span class="hint">(one per line — seeded from the rejection history on the dashboard)</span>
        <textarea id="sp-forbidden" ${locked ? "disabled" : ""}>${esc((spec.forbidden_elements || []).join("\n"))}</textarea>
      </label>
      <label title="How many objects on this board may rest on WEAK evidence — things the screenplay only hints at rather than states (WEAK_INFERENCE rows in the evidence ledger). 0 means every object must be solidly supported. This budgets honest guesses; unsupported inventions are always forbidden regardless (their budget is pinned to 0).">Weak-inference budget <input type="number" id="sp-weak" min="0" value="${esc(String(spec.canon_budget?.weak_inference_max ?? 2))}" ${locked ? "disabled" : ""}></label>
      </div>
    </div>

    ${bible_catalog?.exists ? `
    <div class="spec-section">
      <h4>Art direction scope <span class="hint">(which Bible sections apply to this board — the global rendering language is always included)</span></h4>
      <div class="scope-cols">
        <div class="fgroup" title="Design languages are the Bible's per-faction / per-world / per-technology look sections. Check the ones whose content appears on this board — their design and material language go into every panel prompt.">
          <span class="f-label">Design languages</span>
          <div id="sp-design">${bible_catalog.design_languages.map(n => {
            const sel = spec.design_languages ?? bible_inferred.design_languages;
            return `<label class="mini check"><input type="checkbox" value="${esc(n)}" ${sel.includes(n) ? "checked" : ""} ${locked ? "disabled" : ""}> ${esc(n)}</label>`;
          }).join("") || '<span class="mini">none defined in the Bible</span>'}</div>
        </div>
        <div class="fgroup" title="The physical world this board lives in. Its Bible entry (palette, light, atmosphere) is injected between the design languages and the scene lessons.">
          <span class="f-label">Environment</span>
          <select id="sp-environment" ${locked ? "disabled" : ""}>
            <option value="">— none —</option>
            ${envOptions.map(n => `<option value="${esc(n)}"${envCurrent && envCurrent.toLowerCase() === n.toLowerCase() ? " selected" : ""}>${esc(n)}${envNotes[n] ? ` — ${esc(envNotes[n].slice(0, 44))}` : ""}${(bible_catalog.environments || []).includes(n) ? "" : " (not in Bible yet)"}</option>`).join("")}
          </select>
          <p class="mini" style="margin:6px 0 0">One per sheet — a board lives somewhere.${!spec.environments && envCurrent ? ` Inferred ${esc(envCurrent)} from the location; change it if the read guessed wrong.` : ""}</p>
          <p class="mini" style="margin:4px 0 0">Environment sets the biome's palette and light. ATMOSPHERE is this sheet's weather and mood — it wins where they overlap.</p>
        </div>
        <div class="fgroup" title="Scene-locked lessons are the Bible's accumulated rules for specific scenes/subjects. Check the ones that apply to this board.">
          <span class="f-label">Scene lessons</span>
          <div id="sp-lessons">${bible_catalog.scene_lessons.map(n => {
            const sel = spec.scene_lessons ?? bible_inferred.scene_lessons;
            return `<label class="mini check"><input type="checkbox" value="${esc(n)}" ${sel.includes(n) ? "checked" : ""} ${locked ? "disabled" : ""}> ${esc(n)}</label>`;
          }).join("") || '<span class="mini">none recorded yet</span>'}</div>
        </div>
      </div>
      <div class="scope-carry" id="sp-carry"></div>
      ${spec.design_languages ? "" : '<p class="mini" style="margin:8px 0 0">Pre-checked from keyword inference — save the spec to make this selection explicit and governed.</p>'}
    </div>` : ""}

    <div class="spec-section">
      <h4>Panels <span class="hint">(allocation must total 100%)</span></h4>
      <div id="sp-panels"></div>
      ${locked ? "" : '<button class="ghost" id="sp-add-panel">+ Add panel</button>'}
    </div>

    <div class="spec-section">
      <h4>Evidence ledger <span class="hint">(every required object needs a PASS row — added automatically when you add an object)</span></h4>
      <div class="ledger-row grid-head">
        <span title="Which panel this evidence row belongs to (its Panel ID, e.g. P01).">ID</span>
        <span title="The visible object this row justifies.">Object</span>
        <span title="How strongly the canon supports this object — the evidence class.">Source</span>
        <span title="The citation itself — an exact quote or scene reference; free text for the human audit trail, never sent to the image model.">Cited evidence</span>
        <span title="PASS renders; HOLD blocks approval until you resolve it; REMOVE marks for removal.">State</span>
        <span></span>
      </div>
      <div id="sp-ledger"></div>
      ${locked ? "" : '<button class="ghost" id="sp-add-ledger">+ Add evidence row</button>'}
    </div>

    <div class="spec-section row">
      ${locked ? "" : `
        <button class="primary" id="sp-save">Save</button>
        <button class="ghost" id="sp-validate">Validate</button>
        <button class="ghost" id="sp-approve">Approve &amp; lock</button>`}
      ${locked ? `
        <button class="ghost" id="sp-revise">Create revision</button>
        <button class="danger" id="sp-unlock" title="Void the approval and edit this spec in place — refused if approved candidates or boards depend on it">Unlock &amp; edit</button>
        <span class="hint">revision keeps the approved version as history; unlock voids it and edits in place (refused while approved candidates/boards depend on this spec)</span>` : ""}
    </div>
    <div id="sp-report"></div>`;
  host.append(panel);
  window.scrollTo({ top: panel.getBoundingClientRect().top + window.scrollY - 80,
                    behavior: "smooth" });

  // The scope receipt (review 2026-08-01 §3+4): one line while every panel
  // inherits; with exceptions it tells the truth in two parts — the board's
  // baseline, then one override line per diverging panel. Also refreshes
  // every inheriting panel's quiet SCOPE line.
  updateCarry = () => {
    const carry = $("#sp-carry", panel);
    if (!carry) return;
    const langs = $$("#sp-design input:checked", panel).map(x => x.value.toUpperCase());
    const env = $("#sp-environment", panel)?.value;
    const nl = $$("#sp-lessons input:checked", panel).length;
    const baseline = [...langs,
      ...(env ? [`ENV: ${env.toUpperCase()}`] : []),
      ...(nl ? [`${nl} SCENE LESSON${nl === 1 ? "" : "S"}`] : [])];
    const overrides = [];
    for (const row of $$(".panel-card", panelsHost)) {
      const pid = row.dataset.pid;
      if (!pid) continue;
      const ovLangs = $$(".vchip.set[data-plang]", row).map(c => c.dataset.plang.toUpperCase());
      const ovEnv = $("[data-f=penv]", row)?.value;
      if (ovLangs.length || ovEnv)
        overrides.push(`${pid} OVERRIDES — ${[...ovLangs,
          ...(ovEnv ? [`ENV: ${ovEnv.toUpperCase()}`] : [])].join(" · ")}`);
    }
    const head = overrides.length ? "BOARD CARRIES" : "PROMPT WILL CARRY";
    carry.innerHTML = [
      `<div>${esc([`${head} — RENDERING LANGUAGE (ALWAYS)`, ...baseline].join(" · "))}</div>`,
      ...overrides.map(o => `<div class="carry-ovr">${esc(o)}</div>`),
    ].join("");
    const inherit = ["RENDERING LANGUAGE", ...langs,
      ...(env ? [`ENV: ${env.toUpperCase()}`] : [])].join(" · ");
    $$(".pscope-line", panel).forEach(el => {
      el.textContent = `SCOPE — INHERITS BOARD · ${inherit}`;
    });
  };
  // Hosts are declared BEFORE the first updateCarry() call — it iterates
  // panelsHost, and a const in its temporal dead zone threw here and
  // silently blanked every sheet's panels and ledger (user-caught
  // 2026-08-01, reproduced with the live production's data).
  const panelsHost = $("#sp-panels", panel);
  const ledgerHost = $("#sp-ledger", panel);

  if ($("#sp-carry", panel)) {
    updateCarry();
    for (const id of ["#sp-design", "#sp-lessons", "#sp-environment"])
      $(id, panel)?.addEventListener("change", updateCarry);
  }

  const allocById = {};
  (spec.layout?.panels || []).forEach(p => { allocById[p.id] = p.allocation_percent; });

  const updateSettingVis = () => {
    const t = $("#sp-btype", panel).value;
    const show = {
      intext: ["SCENE", "LOCATION", "LIGHTING_STUDY"].includes(t),
      location: ["SCENE", "LOCATION", "LIGHTING_STUDY"].includes(t),
      tod: t === "SCENE",
      atmo: ["SCENE", "LOCATION", "LIGHTING_STUDY"].includes(t),
    };
    $$(".setf", panel).forEach(l => l.classList.toggle("hidden", !show[l.dataset.setf]));
    $$(".ptod-wrap", panel).forEach(el =>
      el.classList.toggle("hidden", !["LOCATION", "LIGHTING_STUDY"].includes(t)));
  };
  $("#sp-btype", panel).onchange = async () => {
    updateSettingVis();
    if (locked) return;
    // Re-template on type change, but ONLY a sheet that is still empty —
    // a panel with any purpose, object, or ledger row is user content.
    const untouched =
      $$("[data-f=purpose]", panelsHost).every(i => !i.value.trim()) &&
      !$$(".chip", panelsHost).length && !ledgerHost.children.length;
    if (!untouched) return;
    const t = $("#sp-btype", panel).value;
    try {
      const tmpl = (await api("/api/settings")).board_templates?.[t];
      if (!tmpl) return;
      if (!(await askConfirm(`Apply the ${t} board grammar?`,
        `The empty panels are replaced by the ${t} template: ${tmpl.length} panel${tmpl.length > 1 ? "s" : ""} (hero ${tmpl[0]}%${tmpl.length > 1 ? ` + supports ${tmpl.slice(1).join("/")}%` : ""}). Structure only — purposes and objects stay yours to write.`,
        "Apply grammar"))) return;
      panelsHost.innerHTML = "";
      tmpl.forEach((a, i) => {
        const pid = `P${String(i + 1).padStart(2, "0")}`;
        allocById[pid] = a;
        addPanelRow({ id: pid, title: i === 0 ? "Hero" : `Support ${i}`,
                      composition_role: i === 0 ? "hero" : "support" });
      });
    } catch (err) { toast(err.message, true); }
  };

  function nextPanelId() {
    const used = $$(".panel-card[data-pid]", panelsHost).map(r => r.dataset.pid);
    let n = 1;
    while (used.includes(`P${String(n).padStart(2, "0")}`)) n += 1;
    return `P${String(n).padStart(2, "0")}`;
  }

  const rowMatches = (row, pid, obj) =>
    $("[data-f=panel_id]", row).value.trim().toUpperCase() === pid &&
    $("[data-f=object]", row).value.trim().toLowerCase() === obj.toLowerCase();

  function ensureLedgerRow(pid, obj) {
    if ($$(".ledger-row", ledgerHost).some(r => rowMatches(r, pid, obj))) return;
    addLedgerRow({ panel_id: pid, object: obj, evidence_class: "USER_DIRECTED",
                   source: "User direction", status: "PASS" });
  }

  function dropLedgerRows(pid, obj) {
    $$(".ledger-row", ledgerHost).forEach(r => { if (rowMatches(r, pid, obj)) r.remove(); });
  }

  function addPanelRow(p = {}) {
    const pid = String(p.id || nextPanelId()).toUpperCase();
    const row = document.createElement("div");
    row.className = "panel-card";
    row.dataset.pid = pid;
    row.innerHTML = `
      <div class="head">
        <span class="pid-badge" title="Panel ID — assigned automatically; the evidence ledger and layout refer to it.">${esc(pid)}</span>
        <input type="text" data-f="title" placeholder="Panel title — e.g. The Pioneer's Workshop" value="${esc(p.title || "")}" ${locked ? "disabled" : ""} title="Short display name for this panel.">
        <span class="alloc ptod-wrap" title="Light for THIS panel — location and lighting-study boards choose it per panel. Pick a time of day (the hour) or one of the Bible's atmosphere studies (hour + weather + light character). Overrides any style image's hour or hue.">
          <select data-f="ptod" ${locked ? "disabled" : ""}>
            <option value="">— light —</option>
            <optgroup label="Time of day">
              ${TIMES_OF_DAY.map(t =>
                `<option value="${esc(t)}" ${p.time_of_day === t ? "selected" : ""}>${esc(t)}</option>`).join("")}
            </optgroup>
            <optgroup label="Atmosphere studies (Bible)">
              ${[...new Set([...(bible_catalog?.atmospheres || []),
                             ...(p.time_of_day && !TIMES_OF_DAY.includes(p.time_of_day) ? [p.time_of_day] : [])])].map(t =>
                `<option value="${esc(t)}" ${p.time_of_day === t ? "selected" : ""}>${esc(t)}</option>`).join("")}
            </optgroup>
          </select>
        </span>
        <span class="scope-flag hidden" data-f="scope-flag" title="This panel deliberately diverges from the board's scope — see its override below.">SCOPE OVERRIDE</span>
        <span class="alloc" title="Share of the assembled board this panel occupies, in percent. All panels together should total 100.">
          <input type="number" data-f="alloc" placeholder="—" min="1" max="100" value="${esc(allocById[p.id] ?? "")}" ${locked ? "disabled" : ""}>
          <span class="unit">%</span>
        </span>
        ${locked ? "" : '<button class="danger" data-f="del-panel" title="Remove panel">×</button>'}
      </div>
      <div class="fgroup" title="The production question this panel answers. Becomes PANEL PURPOSE in the render prompt — the model's main steer for what the image is about. If no required objects are added, the model composes the panel from this alone (within canon).">
        <span class="f-label">Purpose</span>
        <input type="text" data-f="purpose" placeholder="The production question this panel answers" value="${esc(p.purpose || "")}" ${locked ? "disabled" : ""}>
      </div>
      <div class="two-col">
        <div class="fgroup" title="Objects that MUST appear. Each added object automatically gets a USER_DIRECTED / PASS evidence-ledger row. Optional — leave empty to let the model compose from the purpose.">
          <span class="f-label">Required objects</span>
          <div class="chips" data-f="chips"></div>
        </div>
        <div class="fgroup" title="Objects that must NOT appear in this panel, comma-separated. Merged with the board-wide forbidden elements and project lessons in the prompt.">
          <span class="f-label">Forbidden objects</span>
          <input type="text" data-f="forbidden" placeholder="comma-separated…" value="${esc((p.forbidden_objects || []).join(", "))}" ${locked ? "disabled" : ""}>
        </div>
      </div>
      ${bible_catalog?.exists ? `<div class="pscope" data-f="pscope"></div>` : ""}
      ${locked ? "" : `
      <div class="obj-suggest" data-f="suggest"></div>
      <div class="chip-add">
        <input type="text" data-f="req-new" placeholder="or type an object — it also gets its evidence-ledger row…">
        <button type="button" class="ghost" data-f="req-add" title="Add this required object (also creates its evidence-ledger row)">+ Object</button>
        ${subjects.length ? `
        <select data-f="subj-pick" title="Add a cast member or key subject from the Production Design collection as a required object. Green chips have reference material ready to attach at generation.">
          <option value="">+ cast &amp; subjects…</option>
          ${subjects.map(s => `<option value="${esc(s.name)}">${esc(s.name)} (${esc(s.kind)}${(s.ref_ids || []).length ? ` · ${s.ref_ids.length} ref` : " · no ref"})</option>`).join("")}
        </select>` : ""}
      </div>`}`;

    const chips = $("[data-f=chips]", row);
    let syncSuggest = () => {};  // assigned below when the row is editable
    const addChip = (obj, syncLedger) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.dataset.obj = obj;
      const refInfo = refInfoFor(obj);
      if (refInfo) {
        chip.classList.add("has-ref");
        chip.title = `Reference material available — ${refInfo}. Attach it on the Boards tab when generating.`;
      }
      chip.append(document.createTextNode(obj));
      if (!locked) {
        const x = document.createElement("button");
        x.type = "button"; x.textContent = "×";
        x.title = "Remove this required object (also removes its matching evidence row)";
        x.onclick = () => { chip.remove(); dropLedgerRows(row.dataset.pid, obj); syncSuggest(); };
        chip.append(x);
      }
      chips.append(chip);
      if (syncLedger) ensureLedgerRow(row.dataset.pid, obj);
    };
    (p.required_objects || []).forEach(o => addChip(String(o), false));

    // Scope inheritance (design review 2026-08-01 §3+4): the sheet is the
    // baseline; a panel either quietly states that it inherits, or
    // declares an exception — visible as one, reversible to inheritance.
    const pscopeHost = $("[data-f=pscope]", row);
    if (pscopeHost) {
      let overriding = !!((p.design_languages || []).length || p.environment);
      const renderPScope = () => {
        $("[data-f=scope-flag]", row).classList.toggle("hidden", !overriding);
        pscopeHost.classList.toggle("ovr", overriding);
        if (!overriding) {
          pscopeHost.innerHTML = `
            <span class="pscope-line"></span>
            ${locked ? "" : `<button class="text-act" data-f="ovr" title="Give this panel its own design languages and environment — a declared exception to the board's scope.">Override</button>`}`;
          const b = $("[data-f=ovr]", pscopeHost);
          if (b) b.onclick = () => { overriding = true; renderPScope(); };
        } else {
          pscopeHost.innerHTML = `
            <div class="fgroup" title="This panel's own visual cultures — its prompt carries these instead of the board's languages.">
              <span class="f-label" style="display:flex;align-items:center;gap:10px">Panel design languages
                ${locked ? "" : `<button class="text-act" data-f="revert" style="margin-left:auto" title="Clear the exception — this panel goes back to inheriting the board's scope.">Revert to board</button>`}</span>
              <div class="chips" style="margin-top:4px">
                ${bible_catalog.design_languages.map(n =>
                  `<button type="button" class="vchip${(p.design_languages || []).includes(n) ? " set" : ""}" data-plang="${esc(n)}" ${locked ? "disabled" : ""}>${esc(n)}</button>`).join("")}
              </div>
            </div>
            <div class="fgroup" title="The one place THIS panel lives — replaces the board's environment in this panel's prompt.">
              <span class="f-label">Panel environment</span>
              <select data-f="penv" ${locked ? "disabled" : ""}>
                <option value="">— board's environment —</option>
                ${[...new Set([...envOptions, ...(p.environment ? [p.environment] : [])])].map(n =>
                  `<option value="${esc(n)}"${(p.environment || "") === n ? " selected" : ""}>${esc(n)}</option>`).join("")}
              </select>
            </div>`;
          if (!locked) {
            $$("[data-plang]", pscopeHost).forEach(ch =>
              ch.onclick = () => { ch.classList.toggle("set"); updateCarry(); });
            $("[data-f=penv]", pscopeHost).onchange = updateCarry;
            $("[data-f=revert]", pscopeHost).onclick = () => {
              p.design_languages = [];
              p.environment = "";
              overriding = false;
              renderPScope();
            };
          }
        }
        updateCarry();
      };
      renderPScope();
    }

    if (!locked) {
      const inp = $("[data-f=req-new]", row);
      const doAdd = () => {
        const v = inp.value.trim();
        inp.value = "";
        if (!v) return;
        if ($$(".chip", chips).some(c => c.dataset.obj.toLowerCase() === v.toLowerCase())) return;
        addChip(v, true);
        syncSuggest();
        inp.focus();
      };
      $("[data-f=req-add]", row).onclick = doAdd;
      inp.addEventListener("keydown", e => {
        if (e.key === "Enter") { e.preventDefault(); doAdd(); }
      });
      const pick = $("[data-f=subj-pick]", row);
      if (pick) pick.addEventListener("change", () => {
        const v = pick.value;
        pick.value = "";
        if (!v) return;
        if ($$(".chip", chips).some(c => c.dataset.obj.toLowerCase() === v.toLowerCase())) return;
        addChip(v, true);
        syncSuggest();
      });
      $("[data-f=del-panel]", row).onclick = () => row.remove();

      // Suggestion chips (plan D5, mock 5c) — the vocabulary-picker grammar:
      // stateless, never amber. Solid border = in the library, the exact
      // title guarantees the match; dashed = a scene-paragraph noun that
      // will need evidence like any free-typed object.
      const suggestHost = $("[data-f=suggest]", row);
      syncSuggest = () => {
        const have = new Set($$(".chip", chips).map(c => c.dataset.obj.toUpperCase()));
        const lib = librarySuggestions().filter(s => !have.has(s.title));
        const libTitles = new Set(lib.map(s => s.title));
        const scene = sceneNouns($("#sp-scene", panel)?.value)
          .filter(t => !have.has(t.toUpperCase()) && !libTitles.has(t.toUpperCase()))
          .slice(0, 8);
        suggestHost.innerHTML = (lib.length ? `
          <div class="suggest-group">
            <div class="suggest-label">IN THE LIBRARY — PICKING ONE GUARANTEES THE MATCH</div>
            <div class="chips">${lib.map(s =>
              `<button type="button" class="vchip" data-add="${esc(s.title)}" title="Adds the object with this exact title — the reference group attaches at generation">+ ${esc(s.title)}${
                s.suffix ? `<span class="suffix">· ${s.suffix}</span>` : ""}</button>`).join("")}</div>
          </div>` : "") + (scene.length ? `
          <div class="suggest-group">
            <div class="suggest-label">IN THE SCENE PARAGRAPH — WILL NEED EVIDENCE</div>
            <div class="chips">${scene.map(t =>
              `<button type="button" class="vchip loose" data-add="${esc(t)}" title="A noun from this sheet's scene paragraph — added un-matched, like free-typing it">+ ${esc(t)}</button>`).join("")}</div>
          </div>` : "");
        $$("[data-add]", suggestHost).forEach(b => {
          b.onclick = () => { addChip(b.dataset.add, true); syncSuggest(); };
        });
      };
      $("#sp-scene", panel)?.addEventListener("input", syncSuggest);
      syncSuggest();
    }
    panelsHost.append(row);
    updateSettingVis();
  }

  function addLedgerRow(r = {}) {
    const row = document.createElement("div");
    row.className = "ledger-row";
    row.innerHTML = `
      <input type="text" data-f="panel_id" placeholder="P01" value="${esc(r.panel_id || "")}" ${locked ? "disabled" : ""} title="Which panel this evidence row belongs to (its Panel ID, e.g. P01).">
      <input type="text" data-f="object" placeholder="Visible object" value="${esc(r.object || "")}" ${locked ? "disabled" : ""} title="The visible object this row justifies — should match one of the panel's required objects. Every required object needs a PASS row.">
      <select data-f="evidence_class" ${locked ? "disabled" : ""} title="How strongly the canon supports this object:
SCRIPT_EXPLICIT — the screenplay states it outright.
SCRIPT_NECESSARY_INFERENCE — must exist for the scene to work.
VISUAL_CANON_LOCKED — locked by an approved board/reference.
USER_DIRECTED — your explicit call as writer/director.
STRONG_INFERENCE — well supported by context.
WEAK_INFERENCE — plausible but thin; counts against the weak-inference budget.
PROPOSED_NOT_CANON — a pitch, not canon yet.
UNSUPPORTED — no basis; never passes (budget pinned to 0).">
        ${EVIDENCE_CLASSES.map(c => `<option ${r.evidence_class === c ? "selected" : ""}>${c}</option>`).join("")}
      </select>
      <input type="text" data-f="source" placeholder="Source citation / reference ID" value="${esc(r.source || "")}" ${locked ? "disabled" : ""} title="Where the evidence comes from — a screenplay page/line quote, an approved reference ID, or your directive. Free text for the human audit trail: validation only requires it to be non-empty, nothing looks it up, and it is never sent to the image model. (Typing a reference ID here does NOT attach that reference to generations — use the checkboxes on the Boards tab.)">
      <select data-f="status" ${locked ? "disabled" : ""} title="PASS — evidence accepted, the object may render.
HOLD — needs your review; blocks approval until resolved.
REMOVE — marked for removal from the board.">
        ${LEDGER_STATUSES.map(s => `<option ${r.status === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${locked ? "<span></span>" : '<button class="danger" title="Remove row">×</button>'}`;
    if (!locked) $("button.danger", row).onclick = () => row.remove();
    // Non-PASS rows read at a glance: status colors the row's left border
    // and tints its ground. Inline style so it beats the zebra rule.
    const paint = () => {
      const st = $("[data-f=status]", row).value;
      row.style.borderLeftColor =
        st === "HOLD" ? "var(--hold)" : st === "REMOVE" ? "var(--bad)" : "transparent";
      row.style.background = st === "PASS" ? "" : "var(--panel)";
    };
    $("[data-f=status]", row).addEventListener("change", paint);
    paint();
    ledgerHost.append(row);
  }

  // Population failures are STATED, never a silent blank sheet — the
  // server's data is fine; the reader must know the editor broke.
  try {
    (spec.panels || []).forEach(addPanelRow);
    (spec.evidence_ledger || []).forEach(addLedgerRow);
    updateSettingVis();
  } catch (err) {
    $("#sp-gate", panel).innerHTML =
      `<div class="report" style="border-left:2px solid var(--bad)"><b>The editor
      failed to render this sheet's ${panelsHost.children.length ? "ledger" : "panels"}</b>
      — the sheet itself is intact on the server (${(spec.panels || []).length} panels,
      ${(spec.evidence_ledger || []).length} evidence rows).
      <span class="mono">${esc(String(err.message || err))}</span> —
      reload to retry; if it persists this is an app bug worth reporting.</div>`;
    throw err;
  }

  // The lock gate, run continuously from the DOM — the same rules approval
  // enforces server-side (validate_spec.py), so CANNOT-LOCK is never a
  // surprise on the button. Each failing condition gets its own line.
  const gateHost = $("#sp-gate", panel);
  const computeGate = () => {
    if (locked) return;
    const reasons = [];
    const passSet = new Set($$(".ledger-row", ledgerHost)
      .filter(r => $("[data-f=status]", r).value === "PASS")
      .map(r => `${$("[data-f=panel_id]", r).value.trim().toUpperCase()}|` +
                $("[data-f=object]", r).value.trim().toLowerCase()));
    const gaps = [];
    $$(".panel-card", panelsHost).forEach(pc => {
      $$(".chip", pc).forEach(ch => {
        if (!passSet.has(`${pc.dataset.pid}|${ch.dataset.obj.toLowerCase()}`))
          gaps.push({ pid: pc.dataset.pid, obj: ch.dataset.obj });
      });
    });
    if (gaps.length) reasons.push({
      text: `${gaps.length} required object(s) lack a PASS evidence row — pass them or cut the object; the model can't promote its own guesses.`,
      jump: gaps[0],
    });
    const panelCards = $$(".panel-card", panelsHost);
    const alloc = $$("[data-f=alloc]", panelsHost).reduce((n, i) => n + (+i.value || 0), 0);
    if (panelCards.length && (alloc < 99 || alloc > 101))
      reasons.push({ text: `layout allocation totals ${alloc}% — panels must total 100%.` });
    const noSrc = $$(".ledger-row", ledgerHost)
      .filter(r => !$("[data-f=source]", r).value.trim()).length;
    if (noSrc) reasons.push({
      text: `${noSrc} evidence row(s) have no citation — every row needs a source.` });
    const weakMax = +$("#sp-weak", panel).value || 0;
    const weak = $$(".ledger-row", ledgerHost).filter(r =>
      $("[data-f=evidence_class]", r).value === "WEAK_INFERENCE" &&
      $("[data-f=status]", r).value === "PASS").length;
    if (weak > weakMax) reasons.push({
      text: `weak-inference budget exceeded — ${weak} PASS row(s) on weak evidence, ${weakMax} allowed.` });

    const approveBtn = $("#sp-approve", panel);
    if (approveBtn) approveBtn.disabled = !!reasons.length;
    if (!reasons.length) { gateHost.innerHTML = ""; return; }
    gateHost.innerHTML = `
      <div class="gate-strip">
        ${reasons.map((r, i) => `
          <div class="gate-row">
            ${i === 0 ? '<span class="gate-label">CANNOT LOCK</span>' : '<span class="gate-label gate-cont"></span>'}
            <span class="gate-text">${esc(r.text)}</span>
            ${r.jump ? '<button class="block-act" data-f="gate-jump">Jump to first ↓</button>' : ""}
          </div>`).join("")}
      </div>`;
    const jump = $("[data-f=gate-jump]", gateHost);
    if (jump) jump.onclick = () => {
      const g = reasons.find(r => r.jump).jump;
      const target = $$(".ledger-row", ledgerHost).find(r => rowMatches(r, g.pid, g.obj))
        || $$(".panel-card", panelsHost).find(pc => pc.dataset.pid === g.pid) || panel;
      window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 80,
                        behavior: "smooth" });
    };
  };
  panel.addEventListener("input", computeGate);
  panel.addEventListener("change", computeGate);
  // Row/chip additions and removals are DOM mutations, not input events.
  new MutationObserver(computeGate).observe(panelsHost, { childList: true, subtree: true });
  new MutationObserver(computeGate).observe(ledgerHost, { childList: true });
  computeGate();

  if (!locked) {
    $("#sp-add-panel", panel).onclick = () => addPanelRow();
    $("#sp-add-ledger", panel).onclick = () => addLedgerRow();
  }

  function collect() {
    const out = JSON.parse(JSON.stringify(spec));
    out.subject = $("#sp-subject", panel).value.trim();
    out.mode = $("#sp-mode", panel).value;
    out.board_type = $("#sp-btype", panel).value;
    out.setting = {
      int_ext: $("#sp-intext", panel).value,
      location: $("#sp-location", panel).value.trim(),
      time_of_day: $("#sp-tod", panel).value.trim(),
      atmosphere: $("#sp-atmo", panel).value.trim(),
    };
    out.scene = $("#sp-scene", panel).value.trim();
    out.render_intent = $("#sp-intent", panel).value.trim();
    if ($("#sp-design", panel)) {
      out.design_languages = $$("#sp-design input:checked", panel).map(x => x.value);
      out.scene_lessons = $$("#sp-lessons input:checked", panel).map(x => x.value);
      const envSel = $("#sp-environment", panel);
      if (envSel) out.environments = envSel.value ? [envSel.value] : [];
    }
    out.canon_budget = {
      weak_inference_max: parseInt($("#sp-weak", panel).value || "0", 10),
      unsupported_max: 0,
    };
    out.forbidden_elements = $("#sp-forbidden", panel).value
      .split("\n").map(s => s.trim()).filter(Boolean);

    const split = s => s.split(",").map(x => x.trim()).filter(Boolean);
    out.panels = [];
    const layoutPanels = [];
    for (const row of $$(".panel-card", panelsHost)) {
      const v = f => $(`[data-f=${f}]`, row).value;
      const id = row.dataset.pid;
      if (!id) continue;
      // Fields the editor doesn't surface (scale, evidence, per-row
      // confidence/rationale below) must survive a Save — hardcoding
      // them here once silently wiped autofill's work on every save.
      const orig = (spec.panels || []).find(x => x.id === id) || {};
      const p = {
        ...orig,
        id,
        title: v("title").trim(),
        purpose: v("purpose").trim(),
        required_objects: $$(".chip", row).map(c => c.dataset.obj),
        forbidden_objects: split(v("forbidden")),
        evidence: Array.isArray(orig.evidence) && orig.evidence.length
          ? orig.evidence : ["USER_DIRECTED"],
        scale: orig.scale || "WIDE",
        composition_role: orig.composition_role
          || (out.panels.length === 0 ? "hero" : "support"),
        time_of_day: v("ptod"),
      };
      // An exception exists only when something is chosen — empty
      // override controls collapse back to inheritance (review §3+4).
      delete p.environment;
      delete p.design_languages;
      if ($("[data-f=penv]", row)?.value)
        p.environment = $("[data-f=penv]", row).value;
      const plangs = $$(".vchip.set[data-plang]", row).map(c => c.dataset.plang);
      if (plangs.length) p.design_languages = plangs;
      out.panels.push(p);
      layoutPanels.push({ id, allocation_percent: parseFloat(v("alloc")) || 0 });
    }
    out.layout = { canvas: $("#sp-canvas", panel).value.trim(), panels: layoutPanels };

    out.evidence_ledger = [];
    let n = 0;
    for (const row of $$(".ledger-row", ledgerHost)) {
      const v = f => $(`[data-f=${f}]`, row).value;
      if (!v("object").trim()) continue;
      n += 1;
      const pid = v("panel_id").trim();
      const obj = v("object").trim();
      const origRow = (spec.evidence_ledger || []).find(e =>
        (e.panel_id || "") === pid
        && (e.object || "").toLowerCase() === obj.toLowerCase()) || {};
      out.evidence_ledger.push({
        ...origRow,
        object_id: `OBJ-${String(n).padStart(3, "0")}`,
        panel_id: pid,
        object: obj,
        evidence_class: v("evidence_class"),
        source: v("source").trim(),
        confidence: typeof origRow.confidence === "number"
          ? origRow.confidence : 1.0,
        status: v("status"),
        rationale: origRow.rationale || "",
      });
    }
    return out;
  }

  function showReport(r) {
    const el = $("#sp-report", panel);
    const ok = r.valid && r.audit_decision !== "FAIL";
    const items = [
      ...r.errors.map(e => `validator: ${e}`),
      ...r.audit_findings.map(f => `${f.severity} ${f.type}: ${f.message}`),
    ];
    el.innerHTML = `<div class="report ${ok ? "pass" : "fail"}">
      <b>${ok ? "SPEC_PASS" : "SPEC_FAIL"}</b> — audit: ${esc(r.audit_decision)}
      ${items.length ? "<ul>" + items.map(i => `<li>${esc(i)}</li>`).join("") + "</ul>" : ""}
    </div>`;
  }

  if (!locked) {
    $("#sp-save", panel).onclick = async () => {
      try {
        await api(`/api/specs/${specId}`, { method: "PUT", json: collect() });
        toast(`${specId} saved.`);
      } catch (err) { toast(err.message, true); }
    };
    $("#sp-validate", panel).onclick = async () => {
      try {
        await api(`/api/specs/${specId}`, { method: "PUT", json: collect() });
        showReport(await api(`/api/specs/${specId}/validate`, { method: "POST" }));
      } catch (err) { toast(err.message, true); }
    };
    $("#sp-approve", panel).onclick = async () => {
      if (!(await askConfirm(`Approve & lock ${specId}`,
        "Locked sheets cannot be edited — only revised. Locking mints the spec hash every candidate is judged against.",
        "Approve & lock"))) return;
      try {
        await api(`/api/specs/${specId}`, { method: "PUT", json: collect() });
        await api(`/api/specs/${specId}/approve`, { method: "POST" });
        updateBand();  // Panels unlocks itself right now, visibly
        toast(`${specId} approved and locked — Panels is open.`);
        renderSpecs(specId);
      } catch (err) { toast(err.message, true); }
    };
  } else {
    const doRevise = async () => {
      try {
        const clone = await api(`/api/specs/${specId}/revise`, { method: "POST" });
        toast(`Revision ${clone.specification_id} created.`);
        renderSpecs(clone.specification_id);
      } catch (err) { toast(err.message, true); }
    };
    $("#sp-revise", panel).onclick = doRevise;
    $("[data-f=lock-revise]", panel).onclick = doRevise;
    const doUnlock = async () => {
      if (!(await askConfirm(`Unlock ${specId} for editing`,
        "This VOIDS its approval (journaled in the approval log) and returns it to DRAFT — it disappears from Panels until you approve it again, and re-approving mints a new spec hash. Unapproved candidates keep the hash they were generated against.\n\nRefused automatically if any APPROVED candidate or board depends on this sheet — approved canon can never change out from under what it was approved against.\n\nTo keep the approved version as history instead, use Create revision.",
        "Unlock & edit", true))) return;
      try {
        await api(`/api/specs/${specId}/unlock`, { method: "POST" });
        toast(`${specId} unlocked — now an editable DRAFT. Approve again when done.`);
        renderSpecs(specId);
      } catch (err) { toast(err.message, true); }
    };
    $("#sp-unlock", panel).onclick = doUnlock;
    $("[data-f=lock-unlock]", panel).onclick = async () => { await doUnlock(); updateBand(); };
  }
}

/* ----------------------------------------------------------------- boards */

const IMAGE_SIZES = ["1K", "2K", "4K"];
// Aspect catalog comes from settings (film-format names + per-engine
// support); this is only the offline fallback if the payload is missing.
const ASPECT_FALLBACK = ["21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"]
  .map(id => ({ id, label: id, value: (([w, h]) => w / h)(id.split(":").map(Number)), engines: [] }));
const BOARD_TYPES = [
  { value: "SCENE", label: "SCENE — one screenplay scene, slugline-bound" },
  { value: "LOCATION", label: "LOCATION — a place across times" },
  { value: "ASSET", label: "ASSET — prop / vehicle / character" },
  { value: "LIGHTING_STUDY", label: "LIGHTING STUDY — derived, geometry-locked" },
  { value: "MASTER", label: "MASTER — presentation grammar" },
];
const TIMES_OF_DAY = ["DAWN", "MORNING", "DAY", "AFTERNOON", "DUSK", "EVENING", "NIGHT"];

// Engine options come from settings (built-ins plus user-added custom
// engines) so every Model dropdown stays in sync with Settings.
// Engine dropdowns offer only what can actually run (user rulings
// 2026-08-02): unconfigured engines are omitted entirely; a configured
// key that FAILED its test lists disabled with the reason; with nothing
// usable the select itself states the fix.
const providerUsable = (settings, v) => {
  const e = settings.engines?.[v];
  return !!e?.configured && e.last_test?.ok !== false;
};
const providerOptions = (settings, selected) => {
  const entries = Object.entries(settings.providers || {})
    .filter(([v]) => v !== "mock");  // R16: quarantined to the debug tail
  const usable = entries.filter(([v]) => providerUsable(settings, v));
  if (!usable.length && settings.engines?.mock?.configured) {
    return `<option disabled class="opt-debug">&mdash; DEBUG &mdash;</option>`
      + `<option value="mock" class="opt-debug" selected>MOCK ENGINE &middot; no cost</option>`;
  }
  const failed = entries.filter(([v]) => settings.engines?.[v]?.configured
    && settings.engines?.[v]?.last_test?.ok === false);
  if (!usable.length) {
    return `<option value="">${failed.length
      ? "KEY FAILED ITS TEST — RETEST IN SETTINGS"
      : "NO ENGINE CONFIGURED — ADD A KEY IN SETTINGS"}</option>`;
  }
  const sel = (selected === "mock" && settings.engines?.mock?.configured) ? "mock"
    : usable.some(([v]) => v === selected) ? selected : usable[0][0];
  return usable.map(([v, label]) =>
    `<option value="${esc(v)}" ${v === sel ? "selected" : ""}>${esc(label)}</option>`).join("")
    + failed.map(([v, label]) =>
      `<option value="${esc(v)}" disabled>${esc(label)} — KEY FAILED ITS TEST</option>`).join("")
    + (settings.engines?.mock?.configured
      ? `<option disabled class="opt-debug">&mdash; DEBUG &mdash;</option>`
        + `<option value="mock" class="opt-debug" ${sel === "mock" ? "selected" : ""}>MOCK ENGINE &middot; no cost</option>`
      : "");
};

async function renderBoards() {
  useTemplate("tpl-boards");
  const specs = (await api("/api/specs")).filter(s => s.locked);
  const sel = $("#board-spec");
  sel.innerHTML = `<option value="">— select a signed-off breakdown —</option>` +
    specs.map(s => `<option value="${esc(s.specification_id)}">${esc(s.specification_id)} — ${esc(s.subject)}</option>`).join("");
  sel.onchange = () => { uiSet("boardSpec", sel.value); sel.value && renderBoardPanels(sel.value); };
  const rememberedB = uiGet("boardSpec", "");
  if (rememberedB && specs.some(s2 => s2.specification_id === rememberedB)) {
    sel.value = rememberedB; renderBoardPanels(rememberedB);
  } else if (specs.length === 1) { sel.value = specs[0].specification_id; renderBoardPanels(sel.value); }
  if (!specs.length) {
    $("#board-panels").innerHTML =
      `<div class="panel mini">No signed-off breakdowns yet. Approve one on the Breakdowns tab first.</div>`;
  }
}

// Promote an approved render into the reference library. The dialog knows
// where the take came from: role prefilled, title suggested from the panel
// context and its required objects — most promotions are confirm-and-done.
async function promoteDialog(specId, c) {
  let panel = null;
  try { panel = (await api(`/api/specs/${specId}`)).spec.panels
    .find(p => p.id === c.panel_id) || null; } catch { /* prefill only */ }
  const prefillTitle = [c.panel_id, panel?.title || panel?.purpose || ""]
    .filter(Boolean).join(" ").replace(/[^\w\s-]/g, "").trim().slice(0, 48);
  const r = await roleDialog({
    title: `Promote ${c.candidate_id} to reference`,
    body: "The render enters the library approved — a canon anchor future generations attach to. Same title = same group on the generation bench.",
    prefillHead: "SCENE_REFERENCE",
    prefillTitle,
    extras: panel ? (panel.required_objects || []).slice(0, 4) : [],
    fields: [
      { name: "notes", label: "Notes", placeholder: "e.g. which screenplay scene this anchors" },
      { name: "controls", label: "Controls", placeholder: "comma-separated, optional" },
    ],
    confirmLabel: "Promote",
  });
  if (r === null || !r.role) return;
  try {
    const ref = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/promote`,
      { method: "POST", json: { role: r.role, notes: r.notes, controls: r.controls } });
    toast(`${c.candidate_id} promoted to ${ref.id} (${ref.role}), approved as canon anchor.`);
    // If the title names a cast/subject card, link the reference to it so
    // the card mosaic and the library stay one view of the same canon.
    try {
      const subjects = await api("/api/subjects");
      const match = subjects.find(s => s.name.toUpperCase() === r.title.toUpperCase());
      if (match) {
        await api(`/api/subjects/${match.id}/link`, { method: "POST", json: { ref_id: ref.id } });
        toast(`${ref.id} also linked to ${match.name}'s card.`);
      }
    } catch { /* the promotion itself already succeeded */ }
  } catch (err) { toast(err.message, true); }
}

function renderCard(specId, c, refresh, lbItems = null, lbIndex = 0, getRefs = null) {
  const cc = document.createElement("div");
  cc.className = `ref-card ${c.status === "REJECTED" ? "REJECTED" : ""}`;
  const label = c.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : c.status;
  const meta = c.kind === "assembled_board"
    ? `${c.width}×${c.height} 4K board${c.layout_variant && c.layout_variant !== "default" ? ` · ${esc(c.layout_variant)} layout` : ""} · panels: ${esc(Object.values(c.panels_used || {}).join(", "))}`
    : `${c.width}×${c.height} · ${esc(c.image_size || "")} ${esc(c.aspect_ratio || "")} · ${esc(c.model || "")} · refs: ${esc((c.references || []).map(r => r.id).join(", ") || "none")}`;
  cc.innerHTML = `
    <img src="/api/specs/${specId}/candidates/${c.candidate_id}/image" loading="lazy" alt="${esc(c.candidate_id)}">
    <div class="body">
      <div><span class="badge ${c.status}">${esc(label)}</span> <b>${esc(c.candidate_id)}</b></div>
      <div class="meta">${meta}</div>
      ${(c.warnings || []).map(w => `<div class="meta" style="color:var(--hold)">⚠ ${esc(w)}</div>`).join("")}
      ${c.model_notes || c.render_prompt ? `<details class="meta"><summary>${c.prompt_source === "edited" ? "edited render prompt" : "model notes / rewritten prompt"}</summary><pre style="white-space:pre-wrap;font-size:11px;max-height:200px;overflow:auto">${esc(c.render_prompt ? `RENDER PROMPT (user-edited):\n${c.render_prompt}${c.model_notes ? "\n\n" + c.model_notes : ""}` : c.model_notes)}</pre></details>` : ""}
      <div class="meta">${esc(c.created_at)}</div>
    </div>
    <div class="actions"></div>`;
  $("img", cc).onclick = () => openLightbox(
    lbItems || [{ src: `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
                  caption: `${c.candidate_id} (${label})` }], lbIndex);
  const actions = $(".actions", cc);
  const post = (path, json) => api(path, { method: "POST", json });

  if (c.status !== "APPROVED") {
    const b = document.createElement("button");
    b.className = "primary"; b.textContent = "Approve";
    b.onclick = async () => {
      try {
        await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "APPROVED" });
        toast(`${c.candidate_id} approved.`); refresh();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(b);
  } else {
    if (c.kind !== "assembled_board" && !String(c.kind || "").startsWith("derived")) {
      const ls = document.createElement("button");
      ls.className = "ghost"; ls.textContent = "→ Light study";
      ls.title = "Derive a lighting-study board: this panel becomes the geometry anchor, and each new panel renders the same place under one approved atmosphere";
      ls.onclick = async () => {
        if (!(await askConfirm(`Create a lighting study from ${c.candidate_id}`,
          "This panel is promoted to a LOCATION_GEOMETRY anchor, and a new draft board is created with one panel per approved atmosphere from the Bible. Review and approve the draft on the Breakdowns tab, then generate.",
          "Create study"))) return;
        try {
          const study = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/lighting-study`, { method: "POST", json: {} });
          toast(`${study.specification_id} created with ${study.panels.length} atmosphere panels — review it on the Breakdowns tab, trim any you don't want, then approve.`);
        } catch (err) { toast(err.message, true); }
      };
      actions.append(ls);
    }
    const cr = document.createElement("button");
    cr.className = "ghost"; cr.textContent = "Crop";
    cr.title = "Harvest a region of this image as a new reference with its own narrow role";
    cr.onclick = () => cropToReference(
      { type: "candidate", spec_id: specId, id: c.candidate_id },
      `/api/specs/${specId}/candidates/${c.candidate_id}/image`);
    actions.append(cr);
    const b = document.createElement("button");
    b.className = "ghost"; b.textContent = "→ Reference";
    b.title = "Promote this approved render into the reference library";
    b.onclick = () => promoteDialog(specId, c);
    actions.append(b);
  }
  if (c.kind !== "derived_palette") {
    const rp = document.createElement("button");
    rp.className = "ghost"; rp.textContent = "Repair";
    rp.title = "Paint over the area to fix, describe the change, pick the engine, and regenerate ONLY that region. The result is a new candidate; this one is untouched.";
    rp.onclick = () => openRepair(
      `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
      async (mask, instruction, provider) => {
        const fd = new FormData();
        fd.append("mask", mask, "mask.png");
        fd.append("instruction", instruction);
        fd.append("ref_ids", JSON.stringify(getRefs ? getRefs() : []));
        const rec = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/repair?provider=${encodeURIComponent(provider)}`,
          { method: "POST", body: fd });
        toast(`${rec.candidate_id} — repaired region of ${c.candidate_id}. Review it in the gallery.`);
        refresh();
      });
    actions.append(rp);
  }
  if (c.status !== "REJECTED") {
    const b = document.createElement("button");
    b.className = "danger"; b.textContent = "Reject";
    b.onclick = async () => {
      const reason = await askText(`Reject ${c.candidate_id}`, "Reason",
        { hint: "recorded verbatim, carried into this panel's future prompts as rejection feedback",
          confirmLabel: "Reject", danger: true });
      if (reason === null) return;
      try {
        await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "REJECTED", reason });
        toast(`${c.candidate_id} rejected.`); refresh();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(b);
  } else {
    const b = document.createElement("button");
    b.className = "danger"; b.textContent = "Delete forever";
    b.title = "Permanently remove this rejected image and its record from disk";
    b.onclick = async () => {
      if (!(await askConfirm(`Delete ${c.candidate_id} forever`,
        "The image file is removed from disk and cannot be recovered. Its rejection reason stays in the lessons list and rejection history.",
        "Delete forever", true))) return;
      try {
        await api(`/api/specs/${specId}/candidates/${c.candidate_id}`, { method: "DELETE" });
        toast(`${c.candidate_id} permanently deleted.`); refresh();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(b);
  }
  return cc;
}

// Per-sheet: which panel is on the stage, which take is shown. Loaded
// from and mirrored to the persistent UI state (survives refresh).
const boardRoomSel = {};
const persistRoomSel = () => uiSet("roomSel", boardRoomSel);

// In-flight renders show as pending tiles in the takes filmstrip — closing
// the repair screen (or navigating within the room) never loses sight of a
// render that is still painting.
let _pendingSeq = 0;
const pendingTakes = {};  // specId → panelId → [{id, label}]
const pendingTileHtml = t => `
  <span class="take pending" data-pend="${t.id}" title="Painting now — the take appears here when the engine finishes (30–120s)">
    <span class="take-spin hatch"><i></i></span>
    <span class="take-label">${esc(t.label)}</span>
  </span>`;
function addPendingTake(specId, panelId, label) {
  const t = { id: ++_pendingSeq, label };
  ((pendingTakes[specId] ??= {})[panelId] ??= []).push(t);
  // Splice into the live strip (full refreshes rebuild it from the registry) —
  // no room re-render, so busy indicators and button locks stay alive.
  $(".takes-row")?.insertAdjacentHTML("afterbegin", pendingTileHtml(t));
  return t.id;
}
function removePendingTake(specId, panelId, id) {
  const list = pendingTakes[specId]?.[panelId];
  if (list) pendingTakes[specId][panelId] = list.filter(t => t.id !== id);
  $(`[data-pend="${id}"]`)?.remove();
}

async function renderBoardPanels(specId) {
  const host = $("#board-panels");
  host.innerHTML = `<div class="panel mini">Loading…</div>`;
  const [{ spec, lock_hash: lockHash }, refs, candidates, appSettings, slotMap, boards] = await Promise.all([
    api(`/api/specs/${specId}`),
    api("/api/references"),
    api(`/api/specs/${specId}/candidates`),
    api("/api/settings"),
    api(`/api/specs/${specId}/slot-map`).catch(() => null),
    api(`/api/specs/${specId}/boards`).catch(() => []),
  ]);
  const prefProvider = appSettings.preferred_provider || "gemini";
  const prefKeyFailed =
    appSettings.engines?.[prefProvider]?.last_test?.ok === false;
  const genGateTitle = prefKeyFailed
    ? "The default engine's key failed its last test — retest it in Settings or pick another default in the bake-off."
    : "";
  const isAutoStyle = r => ["BOARD_RENDERING_STYLE", "CINEMATOGRAPHY_STYLE"]
    .includes(roleHead(r.role));
  const styleAnchors = refs.filter(r => r.status === "APPROVED" && isAutoStyle(r));
  const approvedRefs = refs.filter(r => r.status === "APPROVED" && !isAutoStyle(r));
  host.innerHTML = "";

  function buildWorkbench(p) {
    const alloc = (spec.layout?.panels || []).find(x => x.id === p.id)?.allocation_percent;
    const panelCands = candidates.filter(c => c.panel_id === p.id).reverse();
    // PANEL_CARD_PLAN ruling: two lives, one component. Before its first
    // take the card is a WORK ORDER (spec is the content); after, a light
    // table (image is the content, spec is context).
    const workOrder = panelCands.length === 0;

    // Reference groups + the two-way substring match are shared between
    // the required-content marks (P2), the zero-match notice (P5) and the
    // checkbox list — one source, so the spec visibly CAUSES the selection.
    const refGroups = {};
    for (const r of approvedRefs) {
      const suffix = String(r.role).split("—")[1]?.trim();
      const key = (suffix || String(r.role).trim()).toUpperCase();
      (refGroups[key] ??= { name: suffix || r.role, head: roleHead(r.role), ids: [] }).ids.push(r.id);
    }
    const groupList = Object.values(refGroups);
    const matches = (obj, name) => {
      const o = String(obj).toLowerCase(), n = String(name).toLowerCase();
      return o.includes(n) || n.includes(o);
    };
    const objHasRef = obj => groupList.some(g => matches(obj, g.name));
    const reqObjs = p.required_objects || [];
    const evidenceOf = obj => (spec.evidence_ledger || []).find(r =>
      String(r.panel_id).toUpperCase() === p.id
      && String(r.object).toLowerCase() === String(obj).toLowerCase());

    // P2: the work order's largest block — required content as a numbered
    // table (Courier ordinal, Archivo object), each row marked from state:
    // ✓ REF when a library group matches, HOLD when its evidence row is
    // not PASS. Twelve objects in a comma run cannot be read or counted.
    const withRef = reqObjs.filter(objHasRef).length;
    const reqTableHtml = `
      <div class="req-head"><span class="f-label">Required content</span>
        <span class="mini mono">${reqObjs.length} OBJECT${reqObjs.length === 1 ? "" : "S"} · ${withRef} WITH A REFERENCE</span></div>
      <div class="req-table">${reqObjs.map((o, i) => {
        const ev = evidenceOf(o);
        const mark = objHasRef(o) ? '<span class="req-mark ok">✓ REF</span>'
          : ev && ev.status !== "PASS" ? '<span class="req-mark hold">HOLD</span>' : "";
        return `<div class="req-row"><span class="req-ord">${String(i + 1).padStart(2, "0")}</span><span class="req-obj">${esc(o)}</span>${mark}</div>`;
      }).join("") || '<div class="req-row"><span class="req-obj mini">none — this panel is steered by its purpose alone</span></div>'}</div>`;
    // Light-table state: the spec is context — compact bordered chips.
    const reqChipsHtml = `
      <div class="spec-chips"><span class="f-label">Required · ${reqObjs.length}</span>
        ${reqObjs.map(o => `<span class="req-chip">${esc(o)}</span>`).join("")
          || '<span class="mini">none</span>'}</div>`;

    // P3: the user is about to spend a render — everything the render
    // obeys goes on the card. Forbidden states its provenance (panel vs
    // inherited from the board); SCOPE carries the languages, environment
    // and slugline the prompt will actually use.
    const ownForbid = p.forbidden_objects || [];
    const boardForbid = (spec.forbidden_elements || [])
      .filter(f => !ownForbid.some(o => String(o).toLowerCase() === String(f).toLowerCase()));
    const forbidChips = [...ownForbid, ...boardForbid].map(f =>
      `<span class="forbid-chip">${esc(String(f).toUpperCase())}</span>`).join("");
    const forbidHead =
      `${ownForbid.length ? `${ownForbid.length} ON THIS PANEL` : "NOTHING ON THIS PANEL"}`
      + ` · ${boardForbid.length} INHERITED FROM THE BOARD`;
    const forbiddenHtml = `
      <div class="req-head"><span class="f-label">Forbidden</span>
        <span class="mini mono">${forbidHead}</span></div>
      ${forbidChips ? `<div class="spec-chips">${forbidChips}</div>`
        : '<p class="mini">nothing forbidden anywhere — the drift rule still applies</p>'}`;

    const scopeLangs = p.design_languages?.length ? p.design_languages
      : (spec.design_languages || []);
    const scopeOverride = !!(p.design_languages?.length || p.environment);
    const scopeEnv = p.environment || (spec.environments || [])[0] || "";
    const setting = spec.setting || {};
    const scopeBits = [
      ...scopeLangs.map(l => String(l).toUpperCase()),
      scopeEnv ? `ENV: ${String(scopeEnv).toUpperCase()}` : "",
      String(setting.int_ext || "").toUpperCase(),
      String(p.time_of_day || setting.time_of_day || "").toUpperCase(),
    ].filter(Boolean);
    const scopeHtml = scopeBits.length ? `
      <div class="req-head"><span class="f-label">Scope</span>
        <span class="mini mono">${scopeOverride ? "PANEL OVERRIDE" : "INHERITED FROM THE BOARD"}</span></div>
      <p class="scope-line mono">${esc(scopeBits.join("  ·  "))}</p>` : "";
    const roomSel = boardRoomSel[specId];
    roomSel.staged ??= {};
    let staged = panelCands.find(c => c.candidate_id === roomSel.staged[p.id]) || panelCands[0] || null;
    const role = p.composition_role === "hero" ? "HERO" : "STRIP";
    const takeItems = panelCands.map(c => ({
      src: `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
      caption: `${c.candidate_id} — ${p.id} (${c.status}) ${c.width}×${c.height}`,
    }));

    // A promoted take carries its reference id — back-linked on promote,
    // with a legacy fallback matching the promotion note.
    const promotedRefOf = c => c.promoted_ref ||
      refs.find(r => (r.notes || "").includes(`promoted from ${c.candidate_id} of`))?.id || null;

    const stagedRef = staged ? promotedRefOf(staged) : null;
    // PANEL_CARD_PLAN P1: an empty state never reserves the shape of the
    // missing thing — before its first take the card is a WORK ORDER (the
    // spec is the content); no hatched placeholder, no "nothing here" line.
    const stagedHtml = !staged ? "" : `
      <div class="stage-shot" title="Click to open at full size">
        <img src="/api/specs/${specId}/candidates/${staged.candidate_id}/image" alt="${esc(staged.candidate_id)}" data-f="shot-img">
        <!-- T1 (TAKE_ACTIONS): state and identity ride the image so the
             row beneath carries verbs only and can fit. A chip swallows
             its own click; the picture opens the lightbox. -->
        <span class="shot-tag shot-tag-state shot-status ${esc(staged.status)}">${staged.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : esc(staged.status)}</span>
        <span class="shot-tag shot-tag-id">${esc(staged.candidate_id)}${stagedRef ? ` · REF ${esc(stagedRef)}` : ""}</span>
      </div>
      <div class="act-bar">
        <span class="act-zone act-left">
          <span data-f="act-approve"></span>
        </span>
        <span class="act-zone act-use" data-f="act-use"></span>
        <span class="act-rule" aria-hidden="true"></span>
        <span class="act-zone act-derive" data-f="act-derive"></span>
        <span class="act-zone act-right" data-f="act-danger"></span>
      </div>
      <div data-f="shot-busy"></div>
      ${(staged.warnings || []).map(w => `<div class="meta" style="color:var(--hold)">⚠ ${esc(w)}</div>`).join("")}
      ${staged.status === "REJECTED" && staged.status_reason ? `<div class="meta" style="color:var(--bad)">rejected — ${esc(staged.status_reason)}</div>` : ""}
`;

    const sheetRejected = candidates.filter(c => c.status === "REJECTED").length;
    const pending = pendingTakes[specId]?.[p.id] || [];
    // Work-order state: no takes strip either — unless a render is already
    // painting, whose pending tile must never disappear.
    const takesHtml = !panelCands.length && !pending.length ? "" : `
      <div class="takes">
        <div class="takes-head">
          <span class="f-label">Takes · ${panelCands.length}${pending.length ? ` <span style="color:var(--accent)">· ${pending.length} painting</span>` : ""}</span>
          <span class="hint">rejected takes stay as a record</span>
          ${staged && (staged.model_notes || staged.render_prompt) ? `<button class="text-act" data-f="notes">${staged.prompt_source === "edited" ? "Edited render prompt" : "Model notes / rewritten prompt"}</button>` : ""}
          ${sheetRejected ? `<button class="danger" data-f="purge" title="Removes the image files from disk — rejection reasons stay in the lessons list and rejection history">Delete ${sheetRejected} rejected forever</button>` : ""}
        </div>
        <div class="takes-row">
          ${pending.map(pendingTileHtml).join("")}
          ${panelCands.map(c => {
            const pr = promotedRefOf(c);
            const isShown = staged && c.candidate_id === staged.candidate_id;
            const word = isShown ? "SHOWN"
              : c.status === "REJECTED" ? "REJECTED"
              : c.status === "APPROVED" ? "APPROVED" : "";
            return `
            <button class="take${isShown ? " shown" : ""}${c.status === "REJECTED" ? " rejected" : ""}${c.status === "APPROVED" ? " approved" : ""}"
                    data-take="${esc(c.candidate_id)}"
                    title="${esc(c.candidate_id)} (${esc(c.status)})${pr ? ` — promoted to ${esc(pr)}` : ""}${c.status_reason ? ` — ${esc(c.status_reason)}` : ""}">
              <img src="/api/specs/${specId}/candidates/${c.candidate_id}/image" loading="lazy" alt="">
              <span class="take-cap">${esc(c.candidate_id)}${word ? ` · ${word}` : ""}${pr ? " · REF" : ""}</span>
            </button>`;
          }).join("")}
        </div>
      </div>`;

    const card = document.createElement("div");
    card.className = "panel";
    card.innerHTML = `
      <h2><span class="pid-badge">${esc(p.id)}</span> ${esc(p.title || p.purpose)}
        <span class="hint" style="float:right">${alloc ? alloc + "%" : ""} · ${role}${staged ? ` · ${esc(((appSettings.aspects || []).find(x => x.id === staged.aspect_ratio) || {}).label || staged.aspect_ratio || "")}` : ""}</span></h2>
      <p class="mini">${esc(p.purpose)}</p>
      ${workOrder ? reqTableHtml + forbiddenHtml + scopeHtml : reqChipsHtml + `
      <div class="spec-chips"><span class="f-label">Forbidden · ${ownForbid.length + boardForbid.length}</span>
        ${forbidChips || '<span class="mini">nothing</span>'}</div>`}
      ${stagedHtml}
      ${takesHtml}
      <div class="spec-section">
        <div class="bench-head">
          <span class="f-label">Generate next take</span>
          <span class="bench-count" data-f="ref-count"></span>
        </div>
        <h4>Style anchors
          ${styleAnchors.length ? '<span class="always-on" title="Auto-attached to every render on this board — they control style only, never content">ALWAYS ON</span>' : ""}
        </h4>
        ${(() => {
          // P4: auto-attached and un-uncheckable — a wall of full-size
          // badges spends the card's best space on data the user can only
          // read. One row per role with a plate count; IDs behind a
          // disclosure, unchanged.
          if (!styleAnchors.length)
            return '<div class="mini" style="margin-bottom:10px">none yet — upload a Board rendering style or Cinematography style image on the Production Design tab</div>';
          const heads = {};
          for (const r of styleAnchors) (heads[roleHead(r.role)] ??= []).push(r);
          const pretty = h => {
            const t = h.replace(/_STYLE$/, "").replaceAll("_", " ").toLowerCase();
            return t.charAt(0).toUpperCase() + t.slice(1);
          };
          const ids = styleAnchors.map(r => r.id);
          const range = ids.length > 2 ? `${ids[0]} … ${ids[ids.length - 1]}` : ids.join(" · ");
          return `
            <p class="mini" style="margin:2px 0 8px">Set on Production Design. Attached to every render on this board — they control style only, never content.</p>
            <div class="anchor-sum">${Object.entries(heads).map(([h, rs]) => `
              <div class="anchor-sum-row"><span>${esc(pretty(h))}</span>
                <span class="mono">${rs.length} PLATE${rs.length === 1 ? "" : "S"}</span></div>`).join("")}
            </div>
            <div class="mini mono" style="margin:6px 0 10px">${esc(range)}
              <button class="text-act mono" data-f="show-ids" style="font-size:10.5px;letter-spacing:.08em">SHOW IDS</button></div>
            <div class="mini hidden" data-f="anchor-ids" style="margin-bottom:10px">${styleAnchors.map(r =>
              `<span class="badge LOCKED" title="Auto-attached — controls style only, never content">${esc(r.id)} ${esc(r.role)}</span>`).join(" ")}
            </div>`;
        })()}
        <h4>Attach subject references
          <span class="mini mono" style="float:right">${groupList.filter(g => reqObjs.some(o => matches(o, g.name))).length} / ${groupList.length}</span>
          <span class="hint">(grouped by subject — ✓ green groups match this panel's required objects and are pre-checked)</span></h4>
        ${(() => {
          // P5: four unchecked boxes read as a choice not yet made; in
          // fact the app decided and the answer was NOTHING MATCHED. Say
          // so before a 4K spend — this is a quality warning.
          if (!groupList.length || groupList.some(g => reqObjs.some(o => matches(o, g.name))))
            return "";
          const kindName = { CHARACTER_LIKENESS: "cast likeness",
                             VEHICLE_GEOMETRY: "vehicle reference",
                             PROP_REFERENCE: "prop reference" };
          const kinds = [...new Set(groupList.map(g =>
            kindName[g.head] || g.head.replaceAll("_", " ").toLowerCase()))];
          const kindPhrase = kinds.length === 1 ? `a ${kinds[0]}`
            : `a ${kinds.slice(0, -1).join(", ")} or ${kinds.at(-1)}`;
          return `<div class="nomatch">
            <b class="mono">NO MATCHES</b>
            <p>Every group in the library is ${esc(kindPhrase)}; this panel
            requires places and objects. It will render from text and style
            alone.</p></div>`;
        })()}
        <div class="ref-groups">${groupList.map(g => {
            const matched = reqObjs.some(o => matches(o, g.name));
            return `<label class="check ref-group ${matched ? "has-ref" : ""}"
              title="${esc(g.ids.join(", "))}${matched ? " — matches a required object of this panel; pre-checked" : ""}">
              <input type="checkbox" data-ids="${esc(JSON.stringify(g.ids))}" ${matched ? "checked" : ""}>
              ${esc(g.name)} <span class="mini">${esc(g.head.replaceAll("_", " ").toLowerCase())} · ${g.ids.length}</span>
            </label>`;
          }).join("") || '<span class="mini">no approved subject references yet — add them via the cast & subjects cards on Production Design</span>'}
        </div>
      </div>
      <div class="gen-row">
        <div class="fgroup" title="Which image engine renders this candidate. Gemini (Nano Banana Pro) — direct, supports native 4K. GPT Image 2 (direct) — OpenAI's image model given the compiled spec as-is. ChatGPT pipeline — GPT-5.6 first rewrites the spec into render prose (zero-invention rules), then calls the same image model ChatGPT uses; its image tool only accepts preset sizes, so pipeline output caps near 1.5K whatever Size says. All engines get identical spec, style, and references.">
          <span class="f-label">Model</span>
          <select data-f="model">${providerOptions(appSettings, prefProvider)}</select>
        </div>
        <div class="fgroup" title="Output resolution class: 1K for quick drafts, 2K for review candidates, 4K for finals. Always native resolution — never upscaled. (OpenAI flags output above 2560×1440 as experimental; prefer Gemini for 4K.)">
          <span class="f-label">Size</span>
          <select data-f="size">${IMAGE_SIZES.map(s => `<option ${s === "2K" ? "selected" : ""}>${s}</option>`).join("")}</select>
          <span class="eng-note warn size-cap hidden" data-f="size-cap">PIPELINE CAP — RENDERS AT ≈1.5K PRESET</span>
        </div>
        <div class="fgroup" title="Width-to-height shape of the panel image. Film formats carry their names (CinemaScope 2.55:1, Scope 2.39:1, VistaVision 3:2, Academy 1.37:1). Ratios the selected engine cannot genuinely render are greyed — Gemini has a fixed set, the ChatGPT pipeline only 1:1 / 3:2 / 2:3, GPT Image 2 and custom engines render everything. Nothing is ever approximated.">
          <span class="f-label">Aspect</span>
          <select data-f="aspect">${(appSettings.aspects || ASPECT_FALLBACK).map(a =>
            `<option value="${esc(a.id)}" ${a.id === "16:9" ? "selected" : ""}>${esc(a.label)}</option>`).join("")}</select>
        </div>
        <div class="dispatch-facts mono" data-f="dispatch-facts"></div>
        <div class="gen-actions">
          <button class="text-act" data-f="preview" title="Show the exact compiled prompt this panel would send — free, no generation">Preview prompt</button>
          <button class="text-act" data-f="prose" title="Have GPT-5.6 rewrite the compiled spec into editable render prose without generating an image">Draft prose</button>
          <button class="${workOrder ? "primary" : "ghost gen-go"}" data-f="generate" ${prefKeyFailed ? "disabled" : ""} title="${prefKeyFailed ? genGateTitle : workOrder ? "Render this panel's first take — the one action that fills the card" : "Render the next take with the model, size, aspect, and references above — not amber after the first take; nothing here is the one thing to do"}">${workOrder ? "Generate first take" : "Generate candidate"}</button>
        </div>
      </div>
      <div data-f="busy"></div>
      <div data-f="report"></div>`;

    const checkedRefs = () =>
      $$(".ref-groups input:checked", card).flatMap(x => JSON.parse(x.dataset.ids));
    const report = $("[data-f=report]", card);
    const busyHost = $("[data-f=busy]", card);

    const refCount = $("[data-f=ref-count]", card);
    const dispatchFacts = $("[data-f=dispatch-facts]", card);
    const updateRefCount = () => {
      const n = checkedRefs().length;
      const total = n + styleAnchors.length;
      refCount.textContent =
        `${n} SUBJECT + ${styleAnchors.length} STYLE = ${total} OF 14 ATTACHED` +
        (total > 14 ? " — OVER LIMIT, UNCHECK A GROUP" : "");
      refCount.style.color = total > 14 ? "var(--bad)" : "";
      // P6: what is about to be sent, legible at the moment of sending.
      dispatchFacts.innerHTML =
        `${styleAnchors.length} STYLE · ${n} SUBJECT · ${total} IMAGE${total === 1 ? "" : "S"} ATTACHED<br>`
        + `${lockHash ? `SPEC ${esc(lockHash.slice(0, 8).toUpperCase())} · ` : ""}NATIVE RENDER, NEVER UPSCALED`;
    };
    $(".ref-groups", card).addEventListener("change", updateRefCount);
    updateRefCount();

    // P4 disclosure: the full anchor badge list, unchanged, on demand.
    const showIds = $("[data-f=show-ids]", card);
    if (showIds) showIds.onclick = () => {
      const list = $("[data-f=anchor-ids]", card);
      const open = list.classList.toggle("hidden");
      showIds.textContent = open ? "SHOW IDS" : "HIDE IDS";
    };

    // Ratios grey per the selected engine's real contract; switching models
    // snaps an unsupported selection to the nearest ratio and says so.
    const aspects = appSettings.aspects || ASPECT_FALLBACK;
    const aspectById = Object.fromEntries(aspects.map(a => [a.id, a]));
    const modelSel = $("[data-f=model]", card);
    const aspectSel = $("[data-f=aspect]", card);
    const sizeSel = $("[data-f=size]", card);
    // Restore the last-used generation settings (per production); every
    // change persists — refresh and view switches keep them.
    const gen = uiGet("gen", {});
    for (const [selEl, k] of [[modelSel, "model"], [sizeSel, "size"], [aspectSel, "aspect"]]) {
      if (gen[k] && [...selEl.options].some(o => o.value === gen[k] && !o.disabled))
        selEl.value = gen[k];
      selEl.addEventListener("change", () =>
        uiSet("gen", { ...uiGet("gen", {}), [k]: selEl.value }));
    }
    if (!modelSel.value) {
      for (const f of ["generate", "prose"]) {
        const b = $(`[data-f=${f}]`, card);
        if (b) { b.disabled = true; b.title = modelSel.options[0]?.textContent || "No usable engine."; }
      }
    }
    const supportsRatio = (a, prov) => !a.engines.length || a.engines.includes(prov);
    const syncAspects = (quiet) => {
      const prov = modelSel.value;
      // A tooltip is invisible at the moment of choice: the size cap is a
      // quiet standing fact whenever the pipeline is the selected engine.
      $("[data-f=size-cap]", card).classList.toggle("hidden", prov !== "openai-chat");
      $$("option", aspectSel).forEach(o => {
        const a = aspectById[o.value];
        o.disabled = a ? !supportsRatio(a, prov) : false;
      });
      const cur = aspectById[aspectSel.value];
      if (cur && !supportsRatio(cur, prov)) {
        const usable = aspects.filter(a => supportsRatio(a, prov));
        if (usable.length) {
          const nearest = usable.reduce((b, a) =>
            Math.abs(a.value - cur.value) < Math.abs(b.value - cur.value) ? a : b);
          aspectSel.value = nearest.id;
          if (!quiet) toast(`${cur.label} isn't available on ${modelSel.options[modelSel.selectedIndex].text} — snapped to ${nearest.label}, the nearest shape it can genuinely render.`);
        }
      }
    };
    modelSel.addEventListener("change", () => syncAspects(false));
    syncAspects(true);

    $("[data-f=preview]", card).onclick = async () => {
      try {
        const r = await api(`/api/specs/${specId}/panels/${p.id}/prompt?refs=${checkedRefs().join(",")}`);
        report.innerHTML = `<div class="report">
          <div class="report-head"><b>Compiled prompt — ${esc(p.id)}</b>
            <button class="ghost" data-f="close-report">Close</button></div>
          <pre style="white-space:pre-wrap;margin:0">${esc(r.prompt)}</pre></div>`;
        $("[data-f=close-report]", report).onclick = () => { report.innerHTML = ""; };
      } catch (err) { toast(err.message, true); }
    };

    const runGenerate = async (btn, idleLabel, renderPrompt = "") => {
      btn.disabled = true;
      btn.textContent = "Generating…";
      const modelSel = $("[data-f=model]", card);
      const modelLabel = modelSel.options[modelSel.selectedIndex].text;
      const size = $("[data-f=size]", card).value;
      const aspect = $("[data-f=aspect]", card).value;
      const ctrl = new AbortController();
      const busy = startBusy(busyHost,
        `Generating ${p.id} with ${modelLabel} — ${size} ${aspect}` +
        `${renderPrompt ? " from your edited prose" : ""}…`,
        "typically 30–120 seconds; the take appears in the strip above",
        () => ctrl.abort());
      const pendId = addPendingTake(specId, p.id, `PAINTING — NEW TAKE · ${size}`);
      try {
        const cand = await api(`/api/specs/${specId}/panels/${p.id}/generate`, {
          method: "POST",
          signal: ctrl.signal,
          json: {
            ref_ids: checkedRefs(),
            image_size: size,
            aspect_ratio: aspect,
            provider: modelSel.value,
            render_prompt: renderPrompt,
          },
        });
        toast(`${cand.candidate_id} generated (${cand.width}×${cand.height}) — CANDIDATE, unapproved.`);
        renderBoardPanels(specId);
      } catch (err) {
        busy.done();
        btn.disabled = false;
        btn.textContent = idleLabel;
        if (err.name === "AbortError") {
          toast("Canceled. Note: if the model had already started painting, the candidate may still arrive — check the gallery in a minute.");
          return;
        }
        toast(err.message, true);
        // A content-policy refusal reads as a stated condition — the
        // engine's decision, the reason, and the craft options — never a
        // raw 400 (user ruling 2026-08-02).
        if (err.message.startsWith("ENGINE REFUSED — CONTENT POLICY")) {
          const detail = err.message.split("Provider said:")[1]?.trim() || "";
          report.innerHTML = `<div class="report" style="border-left:2px solid var(--hold)">
            <b class="mono" style="color:var(--hold);letter-spacing:.08em">ENGINE REFUSED — CONTENT POLICY</b>
            <p style="margin:6px 0 4px">The engine's safety system declined this panel's
            content. Nothing is broken and nothing was billed — but this exact staging
            will not render on this engine.</p>
            <p style="margin:0 0 4px"><b>The craft answer:</b> restage the panel to imply
            the sensitive element rather than inventory it (edit the sheet's required
            objects), or try a different engine — policy lines differ.</p>
            ${detail ? `<p class="mini mono" style="margin-top:6px">PROVIDER — ${esc(detail)}</p>` : ""}
            <button class="ghost" style="float:right" onclick="this.parentElement.remove()">Dismiss</button></div>`;
        } else {
          report.innerHTML = `<div class="report fail"><b>Generation failed</b> — ${esc(err.message)}
            <button class="ghost" style="float:right" onclick="this.parentElement.remove()">Dismiss</button></div>`;
        }
      } finally {
        removePendingTake(specId, p.id, pendId);
      }
    };

    $("[data-f=generate]", card).onclick = (e) =>
      runGenerate(e.target, workOrder ? "Generate first take" : "Generate candidate");

    $("[data-f=prose]", card).onclick = async (e) => {
      const btn = e.target;
      btn.disabled = true;
      btn.textContent = "Drafting…";
      const busy = startBusy(busyHost,
        `Drafting render prose for ${p.id} with GPT-5.6…`,
        "usually 10–30 seconds; no image is generated yet");
      try {
        const r = await api(`/api/specs/${specId}/panels/${p.id}/draft-prose`, {
          method: "POST", json: { ref_ids: checkedRefs() },
        });
        report.innerHTML = "";
        const box = document.createElement("div");
        box.className = "report";
        box.innerHTML = `
          <p class="mini">Render prose drafted by ${esc(r.chat_model)} from the locked spec.
          Edit it freely — the exact text below is what the image model receives, and it is
          archived with the candidate. Works with any model in the dropdown.</p>
          <textarea data-f="prose-text" style="width:100%;min-height:240px;font-family:Consolas,monospace;font-size:12px"></textarea>
          <div class="row" style="margin-top:8px">
            <button class="ghost gen-go" data-f="generate-prose" ${prefKeyFailed ? "disabled" : ""} ${prefKeyFailed ? `title="${genGateTitle}"` : ""}>Generate from this prose</button>
            <button class="ghost" data-f="close-prose">Close</button>
          </div>`;
        report.append(box);
        $("[data-f=close-prose]", box).onclick = () => { report.innerHTML = ""; };
        $("[data-f=prose-text]", box).value = r.prose;
        $("[data-f=generate-prose]", box).onclick = (e2) =>
          runGenerate(e2.target, "Generate from this prose",
                      $("[data-f=prose-text]", box).value.trim());
      } catch (err) { toast(err.message, true); }
      finally {
        busy.done();
        btn.disabled = false;
        btn.textContent = "Draft prose";
      }
    };

    // Takes filmstrip: clicking a thumb stages that candidate.
    $$("[data-take]", card).forEach(btn => {
      btn.onclick = () => {
        roomSel.staged[p.id] = btn.dataset.take;
        persistRoomSel();
        renderBoardPanels(specId);
      };
    });
    const purgeBtn = $("[data-f=purge]", card);
    if (purgeBtn) purgeBtn.onclick = async () => {
      if (!(await askConfirm(`Delete ${sheetRejected} rejected take(s) forever`,
        `Every rejected candidate image for ${specId} is removed from disk. Rejection reasons stay in the lessons list and rejection history. This cannot be undone.`,
        "Delete forever", true))) return;
      try {
        const r = await api(`/api/specs/${specId}/candidates/purge-rejected`, { method: "POST" });
        toast(`${r.count} rejected candidate(s) permanently deleted.`);
        renderBoardPanels(specId);
      } catch (err) { toast(err.message, true); }
    };

    // Staged-candidate actions (plan v3 B4): primary = Approve panel (the
    // screen's only amber) · Reject · → Reference; ghost secondary row =
    // Repair region · Crop → reference · → Light study; Delete forever only
    // when the staged take is REJECTED. Gates read as disabled state, never
    // as a surprise error.
    if (staged) {
      const c = staged;
      const refresh = () => renderBoardPanels(specId);
      const post = (path, json) => api(path, { method: "POST", json });
      $("[data-f=shot-img]", card).onclick = () =>
        openLightbox(takeItems, panelCands.indexOf(c));
      const mk = (label, cls, fn, opts = {}) => {
        const b = document.createElement("button");
        b.className = cls; b.textContent = label;
        if (opts.title) b.title = opts.title;
        if (opts.disabled) b.disabled = true;
        b.onclick = fn;
        return b;
      };
      // P7: one bordered bar — status (left, divided) · use this take ·
      // derive from it · Reject (right, fenced off). A destructive action
      // never sits adjacent to a promotion.
      const actApprove = $("[data-f=act-approve]", card);
      const actUse = $("[data-f=act-use]", card);
      const actDerive = $("[data-f=act-derive]", card);
      const actDanger = $("[data-f=act-danger]", card);

      const notesBtn = $("[data-f=notes]", card);
      if (notesBtn) notesBtn.onclick = () => promptOverlay(
        c.prompt_source === "edited" ? "EDITED RENDER PROMPT" : "MODEL NOTES / REWRITTEN PROMPT",
        c.render_prompt
          ? "RENDER PROMPT (user-edited):" + String.fromCharCode(10) + c.render_prompt
            + (c.model_notes ? String.fromCharCode(10, 10) + c.model_notes : "")
          : (c.model_notes || ""),
        [p.id, c.candidate_id].join(" · "));

      if (c.status !== "REJECTED") actDanger.append(mk("Reject", "danger", async () => {
        const reason = await askText(`Reject ${c.candidate_id}`, "Reason",
          { hint: "recorded verbatim, carried into this panel's future prompts as rejection feedback",
            confirmLabel: "Reject", danger: true });
        if (reason === null) return;
        try {
          await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "REJECTED", reason });
          toast(`${c.candidate_id} rejected.`); refresh();
        } catch (err) { toast(err.message, true); }
      }));
      actDerive.append(mk("→ Reference", "ghost", () => promoteDialog(specId, c),
        c.status !== "APPROVED"
        ? { disabled: true, title: "Approve this take first — only approved renders become canon anchors" }
        : { title: "Promote this approved render into the reference library" }));
      if (c.status !== "APPROVED") actApprove.append(mk("Approve panel", "ghost act-approve-btn", async () => {
        try {
          await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "APPROVED" });
          toast(`${c.candidate_id} approved.`); refresh();
        } catch (err) { toast(err.message, true); }
      }));

      // Re-performance for resolution (never interpolation): the take
      // anchors itself; a locked reproduce-exactly instruction renders it
      // at full size. The answer to a good take trapped in a small file.
      if (c.kind !== "derived_palette") actUse.append(mk("→ Full-size take", "ghost", () => {
        const ov = document.createElement("div");
        ov.className = "modal-scrim";
        ov.innerHTML = `
          <div class="modal" role="dialog" aria-modal="true">
            <div class="modal-title">New full-size take from ${esc(c.candidate_id)}</div>
            <p class="modal-body">What happens: the engine repaints this exact take at the chosen size, anchored to itself — detail is re-synthesized, never interpolated. A NEW take appears in the takes strip and is staged for judging; ${esc(c.candidate_id)} (${c.width}×${c.height}) is untouched. Takes 30–120 seconds. Expect faithful, not pixel-identical.</p>
            <label class="modal-field">Size
              <select data-rr="size"><option>4K</option><option>2K</option></select>
            </label>
            <label class="modal-field">Engine
              <select data-rr="prov">
                <option value="gemini">Gemini (Nano Banana Pro) — native 4K</option>
                <option value="openai">GPT Image 2 (direct)</option>
              </select>
            </label>
            <div class="modal-actions">
              <button class="ghost" data-rr="cancel">Cancel</button>
              <button class="primary" data-rr="go">Re-render</button>
            </div>
          </div>`;
        document.body.append(ov);
        // Only engines that can run are offered (user-caught 2026-08-02).
        fillProviderSelect($("[data-rr=prov]", ov), {
          gemini: "Gemini (Nano Banana Pro) — native 4K",
          openai: "GPT Image 2 (direct)",
        }).then(ok => {
          if (!ok) {
            const go = $("[data-rr=go]", ov);
            go.disabled = true;
            go.title = "No usable engine — add or retest a key in Settings.";
          }
        });
        const doneRr = () => ov.remove();
        $("[data-rr=cancel]", ov).onclick = doneRr;
        ov.addEventListener("mousedown", ev => { if (ev.target === ov) doneRr(); });
        $("[data-rr=go]", ov).onclick = async () => {
          const size = $("[data-rr=size]", ov).value;
          const prov = $("[data-rr=prov]", ov).value;
          doneRr();
          // Progress lives right under the action that started it, and every
          // staged action locks while the engine paints (only the ones that
          // were live — gate-disabled buttons stay gated on error).
          const lockable = $$(".act-bar button", card).filter(b => !b.disabled);
          lockable.forEach(b => { b.disabled = true; });
          const busy = startBusy($("[data-f=shot-busy]", card),
            `Painting the full-size take from ${c.candidate_id} — ${size} on ${prov === "gemini" ? "Gemini" : "GPT Image 2"}…`,
            "30–120 seconds; the new take will land in the strip and take the stage");
          const pendId = addPendingTake(specId, p.id, `PAINTING — FULL-SIZE OF ${c.candidate_id}`);
          try {
            const rec = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/rerender`,
              { method: "POST", json: { image_size: size, provider: prov } });
            toast(`${rec.candidate_id} — full-size take ready (${rec.width}×${rec.height}). Now staged; judge it against ${c.candidate_id}.`);
            roomSel.staged[p.id] = rec.candidate_id;  // show the result, immediately
            persistRoomSel();
            if ($("#board-panels")) await renderBoardPanels(specId);
          } catch (err) {
            busy.done();
            lockable.forEach(b => { b.disabled = false; });
            toast(err.message, true);
          } finally {
            removePendingTake(specId, p.id, pendId);
          }
        };
      }, { title: "Make a NEW take: repaint this exact image at full resolution, anchored to itself — the sanctioned route out of a low-resolution file (nothing is ever interpolated). This take stays untouched." }));
      if (c.kind !== "derived_palette") actUse.append(mk("Repair region", "ghost", () =>
        openRepair(`/api/specs/${specId}/candidates/${c.candidate_id}/image`,
          async (mask, instruction, provider) => {
            const pendId = addPendingTake(specId, p.id, `PAINTING — REPAIR OF ${c.candidate_id}`);
            try {
              const fd = new FormData();
              fd.append("mask", mask, "mask.png");
              fd.append("instruction", instruction);
              fd.append("ref_ids", JSON.stringify(checkedRefs()));
              const rec = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/repair?provider=${encodeURIComponent(provider)}`,
                { method: "POST", body: fd });
              toast(`${rec.candidate_id} — repaired region of ${c.candidate_id}. It joins the takes strip.`);
              if ($("#board-panels")) await renderBoardPanels(specId);
            } finally {
              removePendingTake(specId, p.id, pendId);
            }
          }),
        { title: "Paint over the area to fix, describe the change, pick the engine, and regenerate ONLY that region — the app composites the patch, so nothing outside your paint can change. The result is a new take; this one is untouched. You can close the paint screen while it renders — a pending tile holds its place in the strip." }));
      actDerive.append(mk("Crop → reference", "ghost", () =>
        cropToReference({ type: "candidate", spec_id: specId, id: c.candidate_id },
          `/api/specs/${specId}/candidates/${c.candidate_id}/image`),
        c.status !== "APPROVED"
          ? { disabled: true, title: "Approve this take first — crops enter the library as approved canon" }
          : { title: "Harvest a region of this image as a new reference with its own narrow role" }));
      actDerive.append(mk("→ Light study", "ghost", async () => {
        if (!(await askConfirm(`Create a lighting study from ${c.candidate_id}`,
          "This panel is promoted to a LOCATION_GEOMETRY anchor, and a new draft board is created with one panel per approved atmosphere from the Bible. Review and approve the draft on the Breakdowns tab, then generate.",
          "Create study"))) return;
        try {
          const study = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/lighting-study`, { method: "POST", json: {} });
          toast(`${study.specification_id} created with ${study.panels.length} atmosphere panels — review it on the Breakdowns tab, trim any you don't want, then approve.`);
        } catch (err) { toast(err.message, true); }
      }, c.status !== "APPROVED"
        ? { disabled: true, title: "Approve this take first — the study locks this panel's geometry" }
        : { title: "Derive a lighting-study board: this panel becomes the geometry anchor, and each new panel renders the same place under one approved atmosphere" }));
      if (c.status === "REJECTED") actDanger.append(mk("Delete forever", "danger", async () => {
        if (!(await askConfirm(`Delete ${c.candidate_id} forever`,
          "The image file is removed from disk and cannot be recovered. Its rejection reason stays in the lessons list and rejection history.",
          "Delete forever", true))) return;
        try {
          await api(`/api/specs/${specId}/candidates/${c.candidate_id}`, { method: "DELETE" });
          delete roomSel.staged[p.id];
          toast(`${c.candidate_id} permanently deleted.`); refresh();
        } catch (err) { toast(err.message, true); }
      }, { title: "Permanently remove this rejected image and its record from disk" }));
    }
    return card;
  }

  // -------- derived panels: palette & materials from the board's own art ----
  const DERIVED_IDS = ["PALETTE", "MATERIALS"];
  const approvedPanelCands = candidates.filter(c =>
    c.status === "APPROVED" && !DERIVED_IDS.includes(c.panel_id) && c.kind !== "assembled_board");
  const derivedCands = candidates.filter(c => DERIVED_IDS.includes(c.panel_id)).reverse();

  function buildDerived() {
  const der = document.createElement("div");
  der.className = "panel";
  der.innerHTML = `
    <h2>Derived panels <span class="hint">(materials &amp; palette built FROM this board's approved panels — the board cannot disagree with itself)</span></h2>
    <div class="gen-row" style="border-top:none;padding-top:0;margin-top:0">
      <div class="fgroup" title="Which model paints the materials strip. The palette needs no model — it is measured, not generated.">
        <span class="f-label">Model (materials)</span>
        <select id="der-model">${providerOptions(appSettings, prefProvider)}</select>
      </div>
      <div class="gen-actions">
        <button class="ghost" id="der-palette" ${approvedPanelCands.length ? "" : "disabled"} title="Deterministic: dominant colors sampled straight from the approved panels' pixels — a measurement, no AI, no drift">Derive palette</button>
        <button class="primary" id="der-materials" ${approvedPanelCands.length ? "" : "disabled"} title="Generated: close-up studies of materials VISIBLE in the approved panels — this cabin's timber, not generic timber">Derive materials</button>
      </div>
    </div>
    ${approvedPanelCands.length ? "" : '<p class="mini">Approve at least one panel candidate to enable derivation.</p>'}
    <div id="der-busy"></div>
    <div class="ref-grid" id="der-gallery" style="margin-top:12px"></div>`;

  $("#der-palette", der).onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    try {
      const c = await api(`/api/specs/${specId}/derive/palette`, { method: "POST" });
      toast(`${c.candidate_id} — palette sampled from ${(c.references || []).length} approved panel(s).`);
      renderBoardPanels(specId);
    } catch (err) { toast(err.message, true); btn.disabled = false; }
  };
  $("#der-materials", der).onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    const busy = startBusy($("#der-busy", der),
      "Deriving materials strip from the board's approved panels…",
      "the approved panels are attached as the only allowed material sources");
    try {
      const c = await api(`/api/specs/${specId}/derive/materials`, {
        method: "POST", json: { provider: $("#der-model", der).value } });
      toast(`${c.candidate_id} — materials strip derived (${c.width}×${c.height}).`);
      renderBoardPanels(specId);
    } catch (err) {
      busy.done();
      toast(err.message, true);
      btn.disabled = false;
    }
  };
  const derGallery = $("#der-gallery", der);
  const derItems = derivedCands.map(c => ({
    src: `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
    caption: `${c.candidate_id} — ${c.panel_id} (${c.status})`,
  }));
  derivedCands.forEach((c, i) =>
    derGallery.append(renderCard(specId, c, () => renderBoardPanels(specId), derItems, i)));
  return der;
  }

  // ---------------- the judging room: rail · stage · provenance (mock 3b) ---
  const roomSel = boardRoomSel[specId] ??=
    (uiGet("roomSel", {})[specId] || {});
  const pids = spec.panels.map(p => p.id);
  if (roomSel.panel !== "__derived" && !pids.includes(roomSel.panel))
    roomSel.panel = pids[0] || "__derived";

  const slotStatus = {};
  (slotMap?.slots || []).forEach(s => { slotStatus[s.panel_id] = s.status; });
  const approvedCount = pids.filter(pid =>
    candidates.some(c => c.panel_id === pid && c.status === "APPROVED")).length;

  const railMark = pid => {
    const st = slotStatus[pid];
    const n = candidates.filter(c => c.panel_id === pid).length;
    if (st === "TOO_SMALL") return '<span class="rail-mark bad">SIZE</span>';
    if (st === "OK") return '<span class="rail-mark okdot" title="approved candidate ready"></span>';
    if (n) return `<span class="rail-mark warn" title="${n} take(s), none approved">${n}</span>`;
    return '<span class="rail-mark none">—</span>';
  };
  const latestThumb = pid => {
    const last = candidates.filter(c => c.panel_id === pid).slice(-1)[0];
    return last ? `<img src="/api/specs/${specId}/candidates/${last.candidate_id}/image" loading="lazy" alt="">` : "";
  };

  const rail = document.createElement("aside");
  rail.className = "board-rail";
  rail.innerHTML = `
    <div class="rail-block">
      <div class="rail-label">SHEET</div>
      <div class="rail-sheet">${esc(specId)}</div>
      <div class="rail-state"><i></i>LOCKED · CAN GENERATE</div>
    </div>
    <div class="rail-block">
      <div class="rail-label">PANELS <span>· ${approvedCount} APPROVED</span></div>
      ${spec.panels.map(p => `
        <button class="rail-panel${roomSel.panel === p.id ? " sel" : ""}" data-pid="${esc(p.id)}"
                title="${esc(p.title || p.purpose || "")}">
          <span class="rail-thumb${latestThumb(p.id) ? "" : " empty hatch-fine"}">${latestThumb(p.id)}</span>
          <span class="rail-meta"><span class="rail-pid">${esc(p.id)}</span>
            <span class="rail-title">${esc(p.title || p.purpose || "")}</span></span>
          ${railMark(p.id)}
        </button>`).join("")}
      <div class="rail-legend mono">
        <span><i class="dot ok"></i>APPROVED</span>
        <span><i class="dot warn"></i>TAKES, NONE APPROVED</span>
        <span><i class="dot none"></i>NO TAKES</span>
      </div>
    </div>
    <div class="rail-block rail-tail">
      <div class="rail-label">DERIVED PANELS</div>
      <button class="rail-panel rail-derived${roomSel.panel === "__derived" ? " sel" : ""}" data-pid="__derived"
              title="Palette and materials built FROM this board's approved panels">
        <span class="drow"><span>Palette</span><span class="mono">${derivedCands.some(c => c.panel_id === "PALETTE") ? "SAMPLED" : "NOT SAMPLED"}</span></span>
        <span class="drow"><span>Materials</span><span class="mono">${derivedCands.some(c => c.panel_id === "MATERIALS") ? "DERIVED" : "NOT DERIVED"}</span></span>
      </button>
      <div class="rail-note">Both are measured from this sheet's approved panels at assembly.</div>
      <div class="rail-note">${boards.length
        ? `This sheet is assembled in <button class="text-act" data-f="to-assembly">${boards.length} board${boards.length === 1 ? "" : "s"}</button>.`
        : `Not assembled yet — <button class="text-act" data-f="to-assembly">05 Boards</button> is where that happens.`}</div>
    </div>`;
  $("[data-f=to-assembly]", rail).onclick = () => showView("assembly");
  $$(".rail-panel", rail).forEach(btn => {
    btn.onclick = () => {
      roomSel.panel = btn.dataset.pid;
      persistRoomSel();
      renderBoardPanels(specId);
    };
  });

  const stage = document.createElement("div");
  stage.className = "board-stage";
  if (roomSel.panel === "__derived") {
    stage.append(buildDerived());
  } else {
    stage.append(buildWorkbench(spec.panels.find(p => p.id === roomSel.panel)));
  }

  // Provenance rail (plan v3 C9): everything about the staged render, all
  // Courier, from fields already on the candidate — no new data.
  function buildSide(c, panelCands) {
    const promptText = c.render_prompt
      ? `RENDER PROMPT (user-edited):\n${c.render_prompt}` : (c.prompt || "");
    const rejectedTakes = panelCands.filter(t =>
      t.status === "REJECTED" && (t.status_reason || "").trim());
    // P8: one bordered panel with rules between sections — the rail was
    // ~60% empty while the prompt was a five-line peephole.
    const shapeClass = Math.max(c.width || 0, c.height || 0) >= 3200 ? "4K"
      : Math.max(c.width || 0, c.height || 0) >= 1920 ? "2K" : "1K";
    const allRefs = c.references || [];
    const AUTO_HEADS = ["BOARD_RENDERING_STYLE", "CINEMATOGRAPHY_STYLE"];
    const subjRefs = allRefs.filter(r => !AUTO_HEADS.includes(roleHead(r.role)));
    const styleCount = allRefs.length - subjRefs.length;
    const el = document.createElement("aside");
    el.className = "board-side";
    el.innerHTML = `
      <div class="rail-block side-dossier">
      <div class="side-sec">
        <div class="rail-label">THIS RENDER</div>
        <div class="fact"><span>MODEL</span><b>${esc(c.model || "—")}</b></div>
        <div class="fact"><span>RENDERED</span><b>${c.width} × ${c.height}</b></div>
        <div class="fact"><span>SHAPE</span><b>${esc(c.aspect_ratio || "—")} · ${shapeClass}</b></div>
        <div class="fact"><span>RUN</span><b>${esc((c.created_at || "").slice(0, 16).replace("T", " "))}</b></div>
        <div class="fact"><span>SPEC HASH</span><b>${esc((c.spec_hash || "").slice(0, 8) || "—")}</b></div>
        <div class="mini mono" style="margin-top:6px;color:var(--ink-faint)">NATIVE RENDER · NEVER UPSCALED</div>
      </div>
      <div class="side-sec">
        <div class="rail-label">ANCHORED TO · ${allRefs.length}</div>
        ${subjRefs.length === 0 ? `
          <div class="nomatch" style="margin:6px 0 2px">
            <b class="mono">NO SUBJECT REFERENCES</b>
            <p>This take was painted from the written spec${styleCount ? ` and the ${styleCount} style plate${styleCount === 1 ? "" : "s"} only` : " alone"}.</p>
          </div>` : ""}
        ${allRefs.map(r => `
          <div class="anchor-row" title="${esc(r.role)}">
            <span class="rail-thumb"><img src="/api/references/${esc(r.id)}/image?thumb=true" loading="lazy" alt="" onerror="this.remove()"></span>
            <span class="anchor-meta"><b>${esc(roleHead(r.role))}</b><i>${esc(r.id)}</i></span>
          </div>`).join("")}
      </div>
      ${promptText ? `
      <div class="side-sec">
        <div class="rail-label">COMPILED PROMPT
          <span style="display:inline-flex;gap:10px">
            <button class="block-act" data-f="copy" style="font-size:11px;padding:0" title="Copy the full prompt to the clipboard">Copy</button>
            <button class="block-act" data-f="detach" style="font-size:11px;padding:0" title="Open the full prompt in a reading view">Expand</button>
            <button class="block-act" data-f="dl" style="font-size:11px;padding:0" title="Download this prompt as a .md file — the exact text this take was rendered from, with its conditions in the header">Download</button>
            <button class="block-act" data-f="full" style="font-size:11px;padding:0">Full</button>
          </span>
        </div>
        <pre class="side-prompt side-prompt-tall" data-f="ppre">${esc(promptText)}</pre>
      </div>` : ""}
      ${rejectedTakes.length ? `
      <div class="side-sec">
        <div class="rail-label bad">CARRIED REJECTIONS · ${rejectedTakes.length}</div>
        ${rejectedTakes.map(t => `<div class="carried">${esc(t.candidate_id)} — ${esc(t.status_reason.toUpperCase())}</div>`).join("")}
      </div>` : ""}
      </div>`;
    const fullBtn = $("[data-f=full]", el);
    if (fullBtn) {
      fullBtn.onclick = () => {
        const pre = $("[data-f=ppre]", el);
        const capped = pre.classList.toggle("side-prompt-tall");
        fullBtn.textContent = capped ? "Full" : "Less";
      };
      $("[data-f=copy]", el).onclick = () => copyText(promptText, "Compiled prompt");
      // A 16k-character prompt is a file, not a clipboard payload (user
      // 2026-08-06). The header carries what the prompt text itself does
      // not: the engine, the size, and WHICH references were actually
      // attached — the first thing to check when a render appears to
      // ignore a reference.
      $("[data-f=dl]", el).onclick = () => {
        const attached = c.references || [];
        const lines = [
          `# ${c.candidate_id} — compiled prompt`,
          "",
          `- **Panel** — ${c.panel_id}`,
          `- **Sheet** — ${specId}`,
          `- **Engine** — ${c.model || "unrecorded"}`,
          `- **Size** — ${c.image_size || "unrecorded"}${c.aspect_ratio ? " · " + c.aspect_ratio : ""}`,
          `- **Rendered** — ${c.created_at || "unrecorded"}`,
          `- **Status** — ${c.status || "unrecorded"}`,
          "",
        ];
        if (attached.length) {
          lines.push(`## Attached references — ${attached.length}`, "");
          attached.forEach(r => lines.push(
            `- ${r.id} — ${r.role || "role unrecorded"}`));
        } else {
          lines.push("## Attached references — none", "",
                     "This take rendered from the written spec and the style",
                     "anchors alone. No subject reference was attached.");
        }
        lines.push("", "---", "", "```text", promptText, "```", "");
        const blob = new Blob([lines.join("\n")],
                              { type: "text/markdown;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${c.candidate_id || "prompt"}.md`;
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
        toast(`${a.download} downloaded.`);
      };
      $("[data-f=detach]", el).onclick = () => promptOverlay(
        "COMPILED PROMPT", promptText,
        [c.panel_id, c.candidate_id, (c.model || "").toUpperCase(),
         c.image_size].filter(Boolean).join(" · "));
    }
    return el;
  }

  let side = null;
  if (roomSel.panel !== "__derived") {
    const pc = candidates.filter(c => c.panel_id === roomSel.panel).reverse();
    const staged = pc.find(c => c.candidate_id === roomSel.staged?.[roomSel.panel]) || pc[0];
    if (staged) side = buildSide(staged, pc);
  }

  const room = document.createElement("div");
  room.className = "board-room";
  room.append(rail, stage);
  if (side) room.append(side);
  host.append(room);
}

/* --------------------------------------------------- assembly (stage 05) */

async function renderAssembly() {
  useTemplate("tpl-assembly");
  const specs = (await api("/api/specs")).filter(s => s.locked);
  const sel = $("#asm-spec");
  sel.innerHTML = `<option value="">— select a signed-off breakdown —</option>` +
    specs.map(s => `<option value="${esc(s.specification_id)}">${esc(s.specification_id)} — ${esc(s.subject)}</option>`).join("");
  sel.onchange = () => { uiSet("asmSpec", sel.value); sel.value ? renderAssemblyFor(sel.value) : renderAssembly(); };

  const host = $("#assembly-host");
  if (!specs.length) {
    // LOCKED_STAGE_PLAN L4: the checklist IS the page — each unfinished
    // step is the link, with its verb, what it does, and its address.
    // No generic navigation button anywhere; the rows are the navigation.
    let gateState = {};
    try { gateState = await api("/api/state"); } catch { /* stateless fallback */ }
    const rows = [...checklistRows(gateState, UNLOCK_NEED.assembly),
                  { verb: "Boards assemble here", state: "info" }];
    const left = rows.filter(r => r.state === "cur" || r.state === "todo").length;
    host.innerHTML = stageChecklist({
      kicker: `NO BOARDS YET — ${left} STEP${left === 1 ? "" : "S"} LEFT`,
      headline: "A board starts life<br>as a breakdown.",
      rows,
      footnote: "NOTHING HERE IS BLOCKED BY US — EVERY STEP IS YOURS TO MAKE",
    });
    bindStageChecklist(host);
    return;
  }

  // The stage lands on the completed boards (user request 2026-07-31):
  // every assembled wall under the sheet picker, newest first. Clicking
  // one replaces the grid with that board full-width; the picker above
  // still opens a sheet's assembly bench.
  const all = (await Promise.all(specs.map(s =>
    api(`/api/specs/${s.specification_id}/boards`)
      .then(bs => bs.map(b => ({ ...b, _spec: s })))
      .catch(() => []))))
    .flat()
    .sort((a, b) => String(b.candidate_id).localeCompare(String(a.candidate_id)));

  if (!all.length) {
    // C2 (ratified 2026-08-01): the middle state gets one line, not the
    // checklist — the picker and bench already state the path by being
    // present. The line disappears the moment a board exists.
    const note = `<div class="mini mono asm-none">NO BOARDS YET &mdash; APPROVE EVERY PANEL IN A SHEET, THEN ASSEMBLE</div>`;
    const rememberedA = uiGet("asmSpec", "");
    if (rememberedA && specs.some(s2 => s2.specification_id === rememberedA)) {
      sel.value = rememberedA;
      await renderAssemblyFor(rememberedA);
      host.insertAdjacentHTML("afterbegin", note);
      return;
    }
    if (specs.length === 1) {
      sel.value = specs[0].specification_id;
      await renderAssemblyFor(sel.value);
      host.insertAdjacentHTML("afterbegin", note);
      return;
    }
    host.innerHTML = note;
    return;
  }

  const lbItems = all.map(b => ({
    src: `/api/specs/${b._spec.specification_id}/candidates/${b.candidate_id}/image`,
    caption: `${b.candidate_id} — ${b._spec.subject || b._spec.specification_id} (${b.status}) ${b.width}×${b.height}`,
  }));

  const showGrid = () => {
    host.innerHTML = "";
    const p = document.createElement("div");
    p.className = "panel";
    p.innerHTML = `
      <h2>Completed boards <span class="hint">(every assembled wall, newest first — click one to view and judge it; pick a sheet above to assemble more)</span></h2>
      <div class="ref-grid" data-f="grid" style="margin-top:10px"></div>`;
    const grid = $("[data-f=grid]", p);
    all.forEach((b, i) => {
      const card = document.createElement("div");
      card.className = "ref-card";
      card.style.cursor = "pointer";
      card.title = "Open this board — it replaces the grid; judge it there.";
      card.innerHTML = `
        <img src="${lbItems[i].src}" loading="lazy" alt="${esc(b.candidate_id)}">
        <div class="body">
          <div><span class="badge ${esc(b.status)}">${esc(b.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : b.status)}</span> <b>${esc(b.candidate_id)}</b></div>
          <div class="meta">${esc(b._spec.subject || b._spec.specification_id)}</div>
          <div class="meta">${b.width}×${b.height}${b.layout_variant ? ` · ${esc(b.layout_variant)} layout` : ""} · ${esc((b.created_at || "").slice(0, 16).replace("T", " "))}</div>
        </div>`;
      card.onclick = () => showBoard(b, i);
      grid.append(card);
    });
    host.append(p);
  };

  const showBoard = (b, i) => {
    host.innerHTML = "";
    const p = document.createElement("div");
    p.className = "panel";
    p.innerHTML = `
      <div class="row" style="margin-top:0;align-items:center">
        <button class="ghost" data-f="back">← All boards</button>
        <span class="mini">${esc(b._spec.specification_id)} — ${esc(b._spec.subject || "")}</span>
      </div>
      <div data-f="board-host" style="margin-top:12px"></div>`;
    $("[data-f=back]", p).onclick = showGrid;
    const bh = $("[data-f=board-host]", p);
    if (b.rects && Object.keys(b.rects).length) {
      // Structural board (user ruling 2026-08-02): the layout frames hold
      // the individual panel images — click one to see the full-sized,
      // uncropped take. The composite single image is the EXPORT.
      const sid = b._spec.specification_id;
      const takeOf = pid => b.panels_used?.[pid];
      const takeItems = Object.keys(b.rects)
        .filter(pid => takeOf(pid))
        .map(pid => ({
          src: `/api/specs/${sid}/candidates/${takeOf(pid)}/image`,
          caption: `${takeOf(pid)} — ${pid} · full uncropped take`,
        }));
      bh.innerHTML = `
        <div class="board-frame" style="aspect-ratio:${b.width}/${b.height}">
          <div class="bf-head">
            <div class="bf-title">${esc((b._spec.subject || sid).toUpperCase())}</div>
            <div class="bf-sub mono">${esc(sid)} · ${esc(b._spec.mode || "")} · ${esc(b.status === "CANDIDATE" ? "BOARD CANDIDATE — UNAPPROVED" : b.status)}</div>
            <div class="bf-rule"></div>
          </div>
          ${Object.entries(b.rects).map(([pid, r]) => `
            <div class="bf-slot" style="left:${(r[0] / b.width * 100).toFixed(2)}%;top:${(r[1] / b.height * 100).toFixed(2)}%;width:${(r[2] / b.width * 100).toFixed(2)}%;height:${(r[3] / b.height * 100).toFixed(2)}%">
              ${takeOf(pid) ? `<img src="/api/specs/${sid}/candidates/${esc(takeOf(pid))}/image" loading="lazy" alt="${esc(pid)}" data-bfp="${esc(pid)}" title="Click for the full-sized, uncropped take (${esc(takeOf(pid))})">` : ""}
              <span class="bf-pid mono">${esc(pid)}</span>
            </div>`).join("")}
        </div>
        <div class="row" style="margin-top:12px;align-items:center">
          <span class="badge ${esc(b.status)}">${esc(b.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : b.status)}</span>
          <span class="mini mono">${b.width}×${b.height} · ${esc(b.layout_variant || "aspect")} LAYOUT · CLICK ANY FRAME FOR THE FULL TAKE</span>
          <span style="flex:1"></span>
          ${b.status !== "APPROVED" ? `<button class="primary" data-bf="approve">Approve board</button>` : ""}
          ${b.status !== "REJECTED" ? `<button class="ghost" data-bf="reject">Reject</button>` : ""}
          <a class="ghost" style="text-decoration:none" href="/api/specs/${sid}/candidates/${esc(b.candidate_id)}/image" download="${esc(b.candidate_id)}.png" title="Download the composite: one flat 4K image of this board, typography drawn in">Export board</a>
        </div>`;
      $$("[data-bfp]", bh).forEach(img => {
        img.onclick = () => {
          const idx = takeItems.findIndex(t => t.caption.includes(`— ${img.dataset.bfp} `));
          openLightbox(takeItems, Math.max(0, idx));
        };
      });
      const post = (path, json) => api(path, { method: "POST", json });
      $("[data-bf=approve]", bh)?.addEventListener("click", async () => {
        try {
          await post(`/api/specs/${sid}/candidates/${b.candidate_id}/status`, { status: "APPROVED" });
          toast(`${b.candidate_id} approved.`); renderAssembly();
        } catch (err) { toast(err.message, true); }
      });
      $("[data-bf=reject]", bh)?.addEventListener("click", async () => {
        const vals = await modal({ title: `Reject ${b.candidate_id}`,
          fields: [{ name: "reason", label: "Why (rides into lessons)", textarea: true }],
          confirmLabel: "Reject board", danger: true });
        if (vals === null) return;
        try {
          await post(`/api/specs/${sid}/candidates/${b.candidate_id}/status`, { status: "REJECTED", reason: vals.reason || "" });
          toast(`${b.candidate_id} rejected.`); renderAssembly();
        } catch (err) { toast(err.message, true); }
      });
    } else {
      // Legacy boards (pre-structural) keep the canonical composite card.
      const card = renderCard(b._spec.specification_id, b, () => renderAssembly(), lbItems, i);
      card.classList.add("board-solo");
      bh.append(card);
    }
    host.append(p);
  };

  const pendingOpen = uiGet("openBoard", "");
  if (pendingOpen) {
    uiSet("openBoard", "");
    const idx = all.findIndex(x => x.candidate_id === pendingOpen);
    if (idx >= 0) { showBoard(all[idx], idx); return; }
  }
  showGrid();
}

async function renderAssemblyFor(specId) {
  const host = $("#assembly-host");
  host.innerHTML = `<div class="panel mini">Loading…</div>`;
  const [{ spec }, candidates, boards] = await Promise.all([
    api(`/api/specs/${specId}`),
    api(`/api/specs/${specId}/candidates`),
    api(`/api/specs/${specId}/boards`),
  ]);
  host.innerHTML = "";

  // The slot map makes the never-upscaled rule visible BEFORE a render is
  // spent: exact assembler geometry, one verdict per slot (Part A.4 canonical:
  // ID chip top-left, verdict chip bottom-right, APP-DRAWN title block).
  // Layout is presentation grammar, not canon — the variant chips rearrange
  // how approved work hangs on the canvas and are recorded on the board.
  const VERDICT = { OK: "OK", UNAPPROVED: "UNAPPROVED",
                    TOO_SMALL: "TOO SMALL", NO_CANDIDATE: "NO CANDIDATE" };
  const slotHtml = sm => {
    const notReady = sm.slots.filter(s => s.status !== "OK");
    const minY = Math.min(1, ...sm.slots.map(s => s.y));
    return `
      ${notReady.length ? `<div class="slot-alert">${notReady.length} SLOT${notReady.length > 1 ? "S" : ""} NOT READY —
        ${esc(notReady.map(s => `${s.panel_id} ${VERDICT[s.status].toLowerCase()}`).join(" · "))}
        — nothing is ever blown up${notReady.some(s => s.status === "TOO_SMALL") ? "; regenerate the small panel larger" : ""}</div>` : ""}
      <div class="slotmap" style="aspect-ratio:${sm.canvas.width}/${sm.canvas.height}">
        <div class="slot apdrawn" style="left:1.7%;top:3%;width:96.6%;height:${Math.max(4, (minY - 0.05) * 100).toFixed(1)}%">
          <span class="slot-id">${esc((_bandState?.project || spec.project || "").toUpperCase())} — ${esc((spec.subject || specId).toUpperCase())}</span>
          <span class="slot-id">TITLE BLOCK · APP-DRAWN</span>
        </div>
        ${sm.slots.map(s => `
          <div class="slot ${s.status === "TOO_SMALL" ? "hatch-bad" : "hatch"} ${esc(s.status)}" style="left:${(s.x * 100).toFixed(2)}%;top:${(s.y * 100).toFixed(2)}%;width:${(s.w * 100).toFixed(2)}%;height:${(s.h * 100).toFixed(2)}%"
               title="${esc(s.title)} — slot ${s.slot_width}×${s.slot_height}px${s.candidate_id ? ` · ${s.candidate_id}${s.candidate_width ? ` ${s.candidate_width}×${s.candidate_height}px` : ""}` : ""}">
            <span class="slot-id">${esc(s.panel_id)}${s.allocation_percent ? ` · ${s.allocation_percent}%` : ""}${s.status === "TOO_SMALL" ? ` · ${s.candidate_width} PX` : ""}</span>
            <span class="slot-verdict ${esc(s.status)}">${VERDICT[s.status]}</span>
          </div>`).join("")}
      </div>`;
  };

  let sm = null;
  try { sm = await api(`/api/specs/${specId}/slot-map`); }
  catch { /* the map is a preview; assembly still states its own errors */ }

  const isStudy = String(spec.board_type || "").toUpperCase() === "LIGHTING_STUDY";
  // "Aspect" is the default grammar (director's ruling 2026-07-31): slots
  // derive from the takes' own aspect ratios; "Allocation" is the old
  // sheet-allocation hero grammar, kept selectable.
  const variants = isStudy ? [] : [
    { value: "aspect", label: "ASPECT" },
    { value: "allocation", label: "ALLOCATION" },
    { value: "grid", label: "GRID" },
    ...spec.panels.map(p => ({ value: `hero:${p.id}`, label: `HERO ${p.id}` })),
  ];
  let variant = "aspect";
  const boardsCount = boards.length;
  // Same takes + same layout = the board that already exists; assembling
  // again would mint a duplicate (user ruling 2026-08-02).
  const currentTakes = Object.fromEntries((sm?.slots || [])
    .filter(sl => sl.candidate_id).map(sl => [sl.panel_id, sl.candidate_id]));
  const dupBoard = boards.find(b =>
    (b.layout_variant || "aspect") === variant &&
    JSON.stringify(b.panels_used || {}) === JSON.stringify(currentTakes));

  const asm = document.createElement("div");
  asm.className = "panel";
  asm.innerHTML = `
    <div class="asm-head">
      <div style="flex:1;min-width:0">
        <p style="margin:0 0 6px"><span class="badge ${boardsCount ? "PROVISIONAL" : "LOCKED"}">${boardsCount ? `${boardsCount} BOARD${boardsCount > 1 ? "S" : ""} ASSEMBLED` : "NOT ASSEMBLED"}</span>
          <span class="badge LOCKED" data-f="canvas-chip">3840 × 2160</span></p>
        <div class="rail-sheet" style="font-size:16px">${esc(specId)}</div>
        <p class="mini" style="margin:4px 0 0">${esc(spec.subject || "")} · ${spec.panels.length} slot${spec.panels.length > 1 ? "s" : ""}</p>
      </div>
      <button class="primary" id="asm-go" ${sm?.ready && !dupBoard ? "" : "disabled"} title="${dupBoard ? `Already assembled as ${dupBoard.candidate_id} with these exact takes and this layout — approve a new take or pick another variant to assemble again` : sm?.ready ? "Compose the latest approved candidate of every panel onto the canvas with board typography — no upscaling" : "Enabled when every slot reads OK — approve a candidate per panel at sufficient size first"}">${dupBoard ? "Assembled" : "Assemble 4K board"}</button>
    </div>
    <div class="slot-caption" style="margin-top:14px">
      <span class="f-label">Slot map · true 4K canvas</span>
      <span class="variant-chips" data-f="variants">
        ${variants.map(v => `<button class="vchip${v.value === variant ? " on" : ""}" data-v="${esc(v.value)}">${esc(v.label)}</button>`).join("")}
      </span>
      <span class="hint">presentation only — recorded on the board, the locked sheet is never touched</span>
    </div>
    <div data-f="slot-wrap">${sm ? slotHtml(sm) : ""}</div>
    <div class="row">
      <label class="mini" title="Pixel dimensions of the final assembled board. Panels are composed at native resolution — never upscaled — so every panel needs enough source resolution for its allocation.">Canvas <select id="asm-size">
        <option value="3840x2160" selected>3840 × 2160 (4K UHD)</option>
        <option value="4096x2304">4096 × 2304 (DCI-flavor wide)</option>
        <option value="4500x2400">4500 × 2400 (print-leaning)</option>
      </select></label>
    </div>
    <div id="asm-busy"></div>
    <div class="ref-grid" id="asm-gallery" style="margin-top:12px"></div>`;
  host.append(asm);

  const refreshMap = async () => {
    const [w, h] = $("#asm-size", asm).value.split("x").map(Number);
    try {
      sm = await api(`/api/specs/${specId}/slot-map?variant=${encodeURIComponent(variant)}&width=${w}&height=${h}`);
      $("[data-f=slot-wrap]", asm).innerHTML = slotHtml(sm);
      $("[data-f=canvas-chip]", asm).textContent = `${w} × ${h}`;
      // The duplicate guard must follow the variant — switching away and
      // back once re-enabled Assemble for an already-minted board.
      const takes = Object.fromEntries((sm?.slots || [])
        .filter(sl => sl.candidate_id).map(sl => [sl.panel_id, sl.candidate_id]));
      const dup = boards.find(b =>
        (b.layout_variant || "aspect") === variant &&
        JSON.stringify(b.panels_used || {}) === JSON.stringify(takes));
      const go = $("#asm-go", asm);
      go.disabled = !sm.ready || !!dup;
      go.textContent = dup ? "Assembled" : "Assemble 4K board";
      go.title = dup
        ? `Already assembled as ${dup.candidate_id} with these exact takes and this layout — approve a new take or pick another variant to assemble again`
        : sm.ready
          ? "Compose the latest approved candidate of every panel onto the canvas with board typography — no upscaling"
          : "Enabled when every slot reads OK — approve a candidate per panel at sufficient size first";
    } catch (err) { toast(err.message, true); }
  };
  $$(".vchip", asm).forEach(ch => {
    ch.onclick = () => {
      variant = ch.dataset.v;
      $$(".vchip", asm).forEach(x => x.classList.toggle("on", x === ch));
      refreshMap();
    };
  });
  $("#asm-size", asm).onchange = refreshMap;

  $("#asm-go", asm).onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true; btn.textContent = "Assembling…";
    const [w, h] = $("#asm-size", asm).value.split("x").map(Number);
    const busy = startBusy($("#asm-busy", asm),
      `Assembling ${w}×${h} board from approved panels…`,
      "composing panels and typography onto the canvas");
    try {
      const b = await api(`/api/specs/${specId}/assemble`, { method: "POST", json: { width: w, height: h, variant } });
      toast(`${b.candidate_id} assembled (${b.width}×${b.height}, ${variant} layout) — BOARD CANDIDATE, unapproved.`);
      // The finished board is the point — land ON it, full size
      // (user ruling 2026-08-02).
      uiSet("asmSpec", "");
      uiSet("openBoard", b.candidate_id);
      renderAssembly();
    } catch (err) {
      busy.done();
      toast(err.message, true);
      btn.disabled = false; btn.textContent = "Assemble 4K board";
    }
  };

  const asmGallery = $("#asm-gallery", asm);
  const orderedBoards = boards.slice().reverse();
  const boardItems = orderedBoards.map(b => ({
    src: `/api/specs/${specId}/candidates/${b.candidate_id}/image`,
    caption: `${b.candidate_id} — assembled board (${b.status}) ${b.width}×${b.height}`,
  }));
  orderedBoards.forEach((b, i) => {
    asmGallery.append(renderCard(specId, b, () => renderAssemblyFor(specId), boardItems, i));
  });
}

/* ------------------------------------------------------------------ start */

// Production switcher (PRODUCTIONS_PLAN M4): switching is navigation, so
// it lives on the production name itself. Every row previews where that
// production stands — switching is an informed move — and the create gap
// closes here: + New production is always one click away.
(() => {
  const sub = $("#brand-project");
  sub.classList.add("brand-switch");
  sub.title = "Switch production";
  let menu = null;
  const close = () => { menu?.remove(); menu = null; };
  document.addEventListener("click", e => {
    if (menu && !e.target.closest(".proj-menu") && e.target !== sub) close();
  });
  sub.onclick = async () => {
    if (sub.querySelector("input")) return;  // mid-rename
    if (menu) { close(); return; }
    const pr = await api("/api/projects/summary");
    menu = document.createElement("div");
    menu.className = "proj-menu";
    menu.innerHTML = `<div class="pm-head mono">SWITCH PRODUCTION</div>`
      + pr.projects.map(p => `
      <button class="proj-item ${p.active ? "open" : ""}" data-slug="${esc(p.slug)}" ${p.active ? "disabled" : ""}>
        <span class="pm-row">
          <span class="pm-name">${esc(p.name.toUpperCase())}</span>
          ${p.active ? '<span class="pm-chip open mono">OPEN</span>'
            : p.backup_chip ? `<span class="pm-chip stale mono">${esc(p.backup_chip)}</span>` : ""}
        </span>
        <span class="pm-sub mono">${esc(p.preview || "")}</span>
      </button>`).join("")
      + `<div class="pm-div"></div>
         <button class="text-act pm-new">+ New production</button>
         <button class="text-act proj-manage">Manage productions…</button>
         <div class="pm-foot mono">SWITCHING RELOADS THE STUDIO. UNSAVED FORM TEXT IS NOT CARRIED OVER.</div>`;
    $(".brand").appendChild(menu);
    $$(".proj-item:not([disabled])", menu).forEach(b => b.onclick = async () => {
      try {
        await api("/api/projects/activate", { method: "POST", json: { slug: b.dataset.slug } });
        location.reload();
      } catch (err) { toast(err.message, true); }
    });
    // Never a form in the menu — navigate to the library with the name
    // field ready to type into.
    $(".pm-new", menu).onclick = async () => {
      close();
      await showView("projects");
      $("#proj-name")?.focus();
    };
    $(".proj-manage", menu).onclick = () => { close(); showView("projects"); };
  };
})();

// Header rename (PRODUCTIONS_PLAN M5): the canonical inline rename —
// the same helper as the library cards. The pencil reveals on hover but
// stays in the accessibility tree for keyboard and touch.
$("#brand-rename").onclick = () =>
  inlineRename($("#brand-project"), async name => {
    const r = await api("/api/projects/rename", { method: "POST", json: { name } });
    toast(`Production named "${r.name}".`);
    return r.name.toUpperCase();
  });

initLightbox();

// First run (PRODUCTIONS_PLAN M6): with no productions and nothing in the
// root layout, the app opens on naming the show — the pipeline band waits
// until there is a production to stand in.
async function boot() {
  // Debug page-text rewrites load first so the first render is already
  // corrected; fire-and-forget chip for text-edit mode.
  loadTextOverrides().then(() => applyTextOverrides());
  updateTextEditChip();
  let first = false;
  try {
    const pr = await api("/api/projects");
    first = pr.first_run;
    uiLoad(pr.active || "");
  } catch { uiLoad(""); /* boot anyway */ }
  if (!first) {
    // Deep-link support: #screenplay, #boards, … land on that view
    // directly; otherwise the app reopens exactly where it was left.
    const stored = uiGet("view", "status");
    const hashView = location.hash.slice(1);
    showView(Object.hasOwn(views, hashView) ? hashView
      : Object.hasOwn(views, stored) ? stored : "status");
    return;
  }
  $("#nav").classList.add("hidden");
  useTemplate("tpl-firstrun");
  $("#firstrun-form").addEventListener("submit", async e => {
    e.preventDefault();
    const name = $("#firstrun-name").value.trim();
    if (!name) return toast("Give the production a name first.", true);
    try {
      await api("/api/projects", { method: "POST", json: { name } });
      location.reload();
    } catch (err) { toast(err.message, true); }
  });
  $("#firstrun-restore").onclick = () => $("#firstrun-zip").click();
  $("#firstrun-zip").addEventListener("change", async () => {
    const f = $("#firstrun-zip").files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await api("/api/projects/restore", { method: "POST", body: fd });
      await api("/api/projects/activate", { method: "POST", json: { slug: r.slug } });
      location.reload();
    } catch (err) { toast(err.message, true); }
  });
  $("#firstrun-name").focus();
}
boot();
