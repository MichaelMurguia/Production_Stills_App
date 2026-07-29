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
  ov.innerHTML = `
    <div class="crop-head">
      <span class="row" style="margin:0;flex:1">
        <input type="text" data-f="instr" placeholder="what should change in the painted region…" style="flex:1;max-width:520px" title="The repair instruction — e.g. 'make the car an exact 1966 Ford GT40 Mk II rear: twin raised intakes, four round tail lights'">
        <label class="mini" style="display:flex;align-items:center;gap:6px;margin:0">brush
          <input type="range" data-f="brush" min="8" max="140" value="46" style="width:110px">
        </label>
        <select data-f="prov" title="GPT Image 2 does a true masked edit — pixels outside your paint cannot change. Gemini has no mask API: it gets the source plus a highlighted guide copy and strict region-only instructions, so it may drift slightly outside the region — but it is a different painter when one engine keeps failing.">
          <option value="openai">GPT Image 2 — true masked edit</option>
          <option value="gemini">Gemini (Nano Banana Pro) — guided edit</option>
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

  const close = () => { window.removeEventListener("resize", sizeCanvas); ov.remove(); };
  $("[data-f=cancel]", ov).onclick = close;
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
    const prov = $("[data-f=prov]", ov);
    const busy = startBusy($("[data-f=busy]", ov),
      `Repairing the painted region with ${prov.options[prov.selectedIndex].text}…`,
      "typically 30–120 seconds; the result lands in the gallery as a new candidate");
    try {
      await onSubmit(blob, instr.value.trim(), prov.value);
      busy.done();
      close();
    } catch (err) {
      busy.done();
      toast(err.message, true);
      goBtn.disabled = false;
    }
  };
}

async function cropToReference(source, imgUrl) {
  openCropper(imgUrl, async (rect) => {
    const role = prompt("Role for the cropped reference (what does this cell control?):", "PROP_REFERENCE");
    if (role === null || !role.trim()) return;
    try {
      const ref = await api("/api/references/crop", {
        method: "POST", json: { source, rect, role: role.trim() } });
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
                assembly: renderAssembly, settings: renderSettings };
const STAGE_ORDER = ["screenplay", "wizard", "specs", "boards", "assembly"];
let activeView = "status";

for (const navSel of ["#nav", "#tools-nav"]) {
  $(navSel).addEventListener("click", e => {
    const btn = e.target.closest("button[data-view]");
    if (btn) showView(btn.dataset.view);
  });
}

function useTemplate(id) {
  const main = $("#main");
  main.replaceChildren($(`#${id}`).content.cloneNode(true));
  return main;
}

async function showView(name) {
  activeView = name;
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

  const eng = settings.engines || {};
  $("#engine-dots").innerHTML = ["gemini", "openai"].map(k => {
    const src = (eng[k] || {}).source;
    return `<span class="edot ${src === "settings" ? "ok" : src === "env" ? "env" : "none"}"><i></i>${k.toUpperCase()}</span>`;
  }).join("");

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
  const blocked = new Set((state.blocking || []).map(b =>
    b.kind === "CITE" ? "screenplay" : BLOCK_STAGE[b.action] || "specs"));
  const frontier = STAGE_ORDER.find(s => !complete[s]) || "assembly";

  for (const stage of STAGE_ORDER) {
    const btn = $(`#nav button[data-view="${stage}"]`);
    if (!btn) continue;
    $(".stage-sub", btn).textContent = subs[stage] || "";
    const isHere = activeView === stage;
    const isCurrent = isHere || (!STAGE_ORDER.includes(activeView) && stage === frontier && !isHere);
    btn.classList.toggle("here", isHere);
    btn.classList.toggle("s-cur", isCurrent);
    btn.classList.toggle("s-bad", !isCurrent && blocked.has(stage));
    btn.classList.toggle("s-ok", !isCurrent && !blocked.has(stage) && complete[stage]);
  }
}

/* -------------------------------------------------------------- dashboard */

const BLOCK_VERBS = { HOLD: "Review", GAP: "Add", SIZE: "Regenerate", CITE: "Review" };
const BLOCK_SUPPORT = {
  HOLD: "Held rows on required objects block the lock — read each cited source, then pass or cut the row.",
  GAP: "A missing input upstream stops generation downstream.",
  SIZE: "Nothing is ever blown up — regenerate the panel at a larger size.",
  CITE: "The current draft no longer contains quotes this sheet cites — review the flagged rows.",
};

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

  // The lead is a presentation of blocking[0] — never a second list. With
  // nothing blocking, it carries the next stage verb instead.
  const first = state.blocking[0];
  const next = state.next || { text: "Upload the screenplay", action: "screenplay" };
  const action = next.action === "dashboard" ? "screenplay" : next.action;
  const lead = $("#dash-next");
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

  // Everything that stops the next render, as structured rows (kind badge,
  // text, resolving jump). The panel hides entirely when nothing blocks.
  const blocking = $("#dash-missing");
  if (state.blocking.length) {
    blocking.classList.remove("hidden");
    blocking.innerHTML =
      `<h2>Blocking — ${state.blocking.length} <span class="hint">everything that stops the next render</span></h2>` +
      state.blocking.map((b, i) => `
        <div class="block-row">
          <span class="block-kind ${esc(b.kind)}">${esc(b.kind)}</span>
          <span class="block-text" title="${esc(b.detail || "")}">${monoIds(esc(b.text))}</span>
          <button class="block-act" data-block="${i}">${esc(BLOCK_VERBS[b.kind] || "Open")}</button>
        </div>`).join("");
    $$("[data-block]", blocking).forEach(btn => {
      btn.onclick = () => {
        const a = state.blocking[+btn.dataset.block].action;
        showView(a === "dashboard" ? "screenplay" : a || "status");
      };
    });
  } else {
    blocking.classList.add("hidden");
  }

  $("#dash-recent").innerHTML = recent.length
    ? recent.map(e => `
        <div class="recent-row${e.kind === "error" ? " error" : ""}">
          <span class="recent-ts">${esc((e.ts || "").slice(11, 16))}</span>
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
  if (sp) {
    const up = (sp.uploaded_at || "").slice(0, 16).replace("T", " ");
    $("#dash-screenplay").innerHTML = `
      <p style="margin-top:0"><span class="badge APPROVED">CURRENT</span></p>
      <p class="scr-file">${esc(sp.file)}</p>
      <div class="fact"><span>SIZE</span><b>${(sp.size / 1048576).toFixed(2)} MB</b></div>
      <div class="fact"><span>SHA256</span><b>${esc((sp.sha256 || "").slice(0, 8))}</b></div>
      <div class="fact"><span>UPLOADED</span><b>${esc(up)}</b></div>
      <div class="fact" data-f="read"><span>READ</span><b>—</b></div>`;
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

  $("#screenplay-form").addEventListener("submit", async e => {
    e.preventDefault();
    const file = $("#screenplay-file").files[0];
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
  const sheetCell = l => {
    if (!l.sheet) return `<button class="block-act loc-draft" data-loc="${esc(l.location)}">Draft a sheet</button>`;
    const held = heldBySpec[l.sheet.spec_id];
    return `<span class="loc-sheet">
      <span class="badge ${l.sheet.locked ? "LOCKED" : "DRAFT"}">${l.sheet.locked ? "LOCKED" : esc(l.sheet.status)}</span>
      <button class="loc-open${held ? " held" : ""}" data-open="${esc(l.sheet.spec_id)}">${held ? `${held} held row${held > 1 ? "s" : ""}` : "Open sheet"}</button>
    </span>`;
  };

  const rows = data.locations.slice(0, 12);
  host.innerHTML = `
    <div class="loc-head">
      <span class="f-label">Locations · ${data.locations.length}</span>
      <span class="hint">${data.scene_count} scenes · sorted by scene count</span></div>
    <div class="loc-row loc-headrow"><span>SLUGLINE</span><span>SCENES</span><span>DETAIL</span><span>SHEET</span></div>
    ${rows.map(l => `
      <div class="loc-row">
        <span class="loc-slug">${esc(l.int_ext)}. ${esc(l.location)}</span>
        <span class="loc-scenes">${l.scenes}</span>
        ${meter(l.detail)}
        ${sheetCell(l)}
      </div>`).join("")}
    ${data.locations.length > rows.length ? `<p class="mini">+ ${data.locations.length - rows.length} more location(s) with fewer scenes</p>` : ""}
    <p class="mini"><span class="f-label" style="font-size:10px">DETAIL</span> how much the script describes — thin coverage spends inference budget faster</p>`;
  $$(".loc-draft", host).forEach(btn => {
    btn.onclick = () => {
      sessionStorage.setItem("draftLocationHint", btn.dataset.loc);
      showView("specs");
    };
  });
  $$("[data-open]", host).forEach(btn => {
    btn.onclick = () => openSheet(btn.dataset.open);
  });
}

/* --------------------------------------------------------------- settings */

async function renderSettings() {
  useTemplate("tpl-settings");

  $("#settings-subnav").addEventListener("click", e => {
    const btn = e.target.closest("button[data-sub]");
    if (!btn) return;
    $$("#settings-subnav button").forEach(b => b.classList.toggle("active", b === btn));
    $$("[data-subview]").forEach(v =>
      v.classList.toggle("hidden", v.dataset.subview !== btn.dataset.sub));
  });

  const settings = await api("/api/settings");
  const pref = $("#pref-provider");
  pref.innerHTML = Object.entries(settings.providers).map(([v, label]) =>
    `<option value="${esc(v)}" ${v === settings.preferred_provider ? "selected" : ""}>${esc(label)}</option>`).join("");
  pref.onchange = async () => {
    try {
      await api("/api/settings", { method: "POST", json: { preferred_provider: pref.value } });
      toast(`Preferred image model: ${pref.options[pref.selectedIndex].text}.`);
    } catch (err) { toast(err.message, true); }
  };
  // Honest connection state: key source, plus the persisted outcome of the
  // user's own last Test click — never a fake CONNECTED.
  const lastTest = provider => {
    const t = (settings.engines || {})[provider]?.last_test;
    if (!t) return "";
    return ` · last test <span class="badge ${t.ok ? "APPROVED" : "REJECTED"}">${t.ok ? "PASS" : "FAIL"}</span> <span class="mini">${esc((t.at || "").slice(0, 16).replace("T", " "))}</span>`;
  };
  $("#dash-keystate").innerHTML = (settings.gemini_api_key_set
    ? `<span class="badge APPROVED">KEY SET</span> ${esc(settings.gemini_api_key_hint)} — image model ${esc(settings.model)}`
    : `<span class="badge REJECTED">NO KEY</span> generation and auto-fill disabled until a key is saved`)
    + lastTest("gemini");
  $("#openai-keystate").innerHTML = (settings.openai_api_key_set
    ? `<span class="badge APPROVED">KEY SET</span> ${esc(settings.openai_api_key_hint)} — image model ${esc(settings.openai_model)}`
    : settings.openai_env_key_hint
      ? `<span class="badge PROVISIONAL">ENV VAR</span> no key saved here — falling back to OPENAI_API_KEY (${esc(settings.openai_env_key_hint)}) from your system environment. Save a key below to override it.`
      : `<span class="badge REJECTED">NO KEY</span> optional — only needed to generate with GPT Image 2`)
    + lastTest("openai");

  const keyForm = (formSel, inputSel, field, label) => {
    $(formSel).addEventListener("submit", async e => {
      e.preventDefault();
      const key = $(inputSel).value.trim();
      if (!key) return;
      try {
        await api("/api/settings", { method: "POST", json: { [field]: key } });
        toast(`${label} key saved.`);
        renderSettings();
      } catch (err) { toast(err.message, true); }
    });
  };
  keyForm("#settings-form", "#gemini-key", "gemini_api_key", "Gemini");
  keyForm("#openai-settings-form", "#openai-key", "openai_api_key", "OpenAI");

  const keyTest = (btnSel, outSel, inputSel, field, provider, label) => {
    $(btnSel).addEventListener("click", async (e) => {
      const btn = e.target, out = $(outSel);
      btn.disabled = true;
      out.innerHTML = `<span class="badge PROVISIONAL">TESTING…</span> contacting ${esc(label)}`;
      try {
        // If a key is sitting in the input box, save it first — Test always
        // exercises the key the app will actually use.
        const typed = $(inputSel).value.trim();
        if (typed) {
          await api("/api/settings", { method: "POST", json: { [field]: typed } });
          $(inputSel).value = "";
          toast(`${label} key saved.`);
        }
        const r = await api("/api/settings/test", { method: "POST", json: { provider } });
        out.innerHTML = `<span class="badge APPROVED">PASS</span> connected — ${esc(r.model)}`;
        toast(`${label} connection OK — ${r.model}`);
      } catch (err) {
        out.innerHTML = `<span class="badge REJECTED">FAIL</span> ${esc(err.message)}`;
        toast(err.message, true);
      } finally { btn.disabled = false; }
    });
  };
  keyTest("#test-key", "#test-key-result", "#gemini-key", "gemini_api_key", "gemini", "Gemini");
  keyTest("#test-openai-key", "#test-openai-key-result", "#openai-key", "openai_api_key", "openai", "OpenAI");

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
  const localAnalysis = JSON.parse(localStorage.getItem("wizardAnalysis") || "null");
  if (!wizAnalysis && localAnalysis) {
    wizAnalysis = localAnalysis;
    api("/api/wizard/analysis", { method: "PUT", json: localAnalysis }).catch(() => {});
  }
  if (wizAnalysis) localStorage.setItem("wizardAnalysis", JSON.stringify(wizAnalysis));
  $("#wiz-screenplay").innerHTML = state.screenplay
    ? `<span class="badge APPROVED">SCREENPLAY</span> ${esc(state.screenplay.file)} — uploaded ${esc(state.screenplay.uploaded_at || "")}`
    : `<span class="badge REJECTED">NO SCREENPLAY</span> upload it on the Dashboard first — analysis and drafting need it`;

  // ---- Engines & API keys ----
  const refreshEngineState = async () => {
    const s = await api("/api/settings");
    $("#wiz-gem-state").innerHTML = s.gemini_api_key_set
      ? `<span class="badge APPROVED">SET</span>` : `<span class="badge REJECTED">NO KEY</span>`;
    $("#wiz-oai-state").innerHTML = s.openai_api_key_set
      ? `<span class="badge APPROVED">SET</span>` : `<span class="badge REJECTED">NO KEY</span>`;
    return s;
  };
  const wireKeySave = (btnId, inputId, field, label) => {
    $(btnId).onclick = async () => {
      const key = $(inputId).value.trim();
      if (!key) return toast(`Paste the ${label} key first.`, true);
      try {
        await api("/api/settings", { method: "POST", json: { [field]: key } });
        $(inputId).value = "";
        toast(`${label} key saved.`);
        refreshEngineState();
      } catch (err) { toast(err.message, true); }
    };
  };
  wireKeySave("#wiz-gem-save", "#wiz-gem-key", "gemini_api_key", "Gemini");
  wireKeySave("#wiz-oai-save", "#wiz-oai-key", "openai_api_key", "OpenAI");

  // ---- Step 6: model bake-off (after the production design is set) ----
  // Every engine renders the same screenplay location; suggestions come from
  // the Step 2 analysis's recurring locations.
  const locInput = $("#wiz-sample-loc");
  const sampleLocs = JSON.parse(localStorage.getItem("wizardAnalysis") || "null")?.key_locations || [];
  $("#wiz-sample-locs").innerHTML = sampleLocs.map(l => `<option value="${esc(l)}"></option>`).join("");
  locInput.value = localStorage.getItem("wizardSampleLoc") || sampleLocs[0] || "";
  locInput.oninput = () => localStorage.setItem("wizardSampleLoc", locInput.value);
  const sampleSubject = () => locInput.value.trim();

  const renderSamples = async () => {
    const [samples, s] = await Promise.all([api("/api/wizard/samples"), api("/api/settings")]);
    const host = $("#wiz-samples");
    host.innerHTML = "";
    for (const smp of samples) {
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
  await refreshEngineState();
  renderSamples();

  $("#wiz-samples-go").onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    const s = await api("/api/settings");
    const avail = [
      ...(s.gemini_api_key_set ? ["gemini"] : []),
      ...(s.openai_api_key_set ? ["openai", "openai-chat"] : []),
    ];
    if (!avail.length) {
      btn.disabled = false;
      return toast("Save at least one API key first.", true);
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

  const refreshRefs = async () => {
    const refs = (await api("/api/references")).filter(r => r.status !== "REJECTED");
    for (const col of $$(".wiz-col[data-role]")) {
      const role = col.dataset.role;
      const mine = refs.filter(r => roleHead(r.role) === role);
      const badge = $("[data-f=state]", col);
      badge.className = `badge ${mine.length ? "APPROVED" : "REJECTED"}`;
      badge.textContent = mine.length ? `${mine.length} SET` : "NONE";
      const list = $("[data-f=list]", col);
      list.innerHTML = "";
      const lbItems = mine.map(r => ({
        src: `/api/references/${r.id}/image`, caption: `${r.id} — ${r.role}` }));
      mine.forEach((r, i) => {
        const item = document.createElement("div");
        item.className = "wiz-thumb";
        item.innerHTML = `
          <img src="/api/references/${esc(r.id)}/image?thumb=1" loading="lazy" alt="${esc(r.id)}">
          <span class="meta mini">${esc(r.id)}
            <label class="mini check" style="margin:0;display:flex" title="Checked images are attached to the bible draft so the model can study them.">
              <input type="checkbox" class="wiz-ref-use" value="${esc(r.id)}" checked> use in draft
            </label>
          </span>
          <button class="danger" data-f="del" title="Permanently delete this image">×</button>`;
        $("img", item).onclick = () => openLightbox(lbItems, i);
        $("[data-f=del]", item).onclick = async () => {
          if (!confirm(`Permanently delete ${r.id}? It is removed from the reference library and future generations. This cannot be undone.`)) return;
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

  // ---- cast & key subjects (Step 3) ----
  const renderSubjectTags = () => {
    const host = $("#wiz-subj-tags");
    const analysis = JSON.parse(localStorage.getItem("wizardAnalysis") || "null");
    const recs = analysis?.subjects || [];
    api("/api/subjects").then(existing => {
      const have = new Set(existing.map(s => s.name.toLowerCase()));
      const fresh = recs.filter(r => r.name && !have.has(String(r.name).toLowerCase()));
      host.innerHTML = fresh.length
        ? `<span class="f-label" style="margin-right:6px">Recommended from the screenplay:</span>`
        : (recs.length ? `<span class="mini">all recommendations added</span>`
                       : `<span class="mini">run Step 2 to get recommendations</span>`);
      for (const r of fresh) {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.title = `${r.kind || "CHARACTER"} — ${r.subtitle || ""}\nClick to add this title card.`;
        chip.style.cursor = "pointer";
        chip.textContent = `+ ${r.name}`;
        chip.onclick = async () => {
          try {
            const subj = await api("/api/subjects", { method: "POST", json: {
              name: r.name, kind: r.kind || "CHARACTER",
              subtitle: r.subtitle || "", traits: r.traits || [],
              source: "screenplay analysis" } });
            toast(`${r.name} added — choose its reference photos.`);
            renderSubjectTags();
            await renderSubjectGrid();
            // The next action is always adding reference photos — open the
            // chooser for the new card immediately.
            $(`.subj-card[data-sid="${subj.id}"] [data-f=up]`)?.click();
          } catch (err) { toast(err.message, true); }
        };
        host.append(chip);
      }
    });
  };

  const renderSubjectGrid = async () => {
    const grid = $("#wiz-subj-grid");
    const [subjects, refs] = await Promise.all([api("/api/subjects"), api("/api/references")]);
    const refById = Object.fromEntries(refs.map(r => [r.id, r]));
    grid.innerHTML = subjects.length ? "" :
      `<p class="mini" style="grid-column:1/-1">No subjects yet — click a recommended tag above or add one manually.</p>`;
    for (const s of subjects) {
      const imgs = (s.ref_ids || []).map(id => refById[id]).filter(Boolean)
        .filter(r => r.status !== "REJECTED");
      const lbItems = imgs.map(r => ({
        src: `/api/references/${r.id}/image`, caption: `${s.name} — ${r.id}` }));
      const card = document.createElement("div");
      card.className = "subj-card";
      card.dataset.sid = s.id;
      card.innerHTML = `
        <div class="subj-head">
          <span class="subj-name">${esc(s.name.toUpperCase())}</span>
          <span class="subj-sub">— ${esc(s.subtitle || s.kind)}</span>
          <span class="badge ${imgs.length ? "APPROVED" : "PROVISIONAL"}" style="margin-left:auto">${imgs.length ? `${imgs.length} REF` : "NO REF"}</span>
          <button class="danger" data-f="del" title="Remove this title card (its reference images stay in the library)">×</button>
        </div>
        <div class="subj-imgs" data-f="imgs"></div>
        <div class="subj-traits mini">${esc((s.traits || []).join(" "))}</div>
        <label class="subj-add" title="Upload reference photos into this card — each becomes an approved ${esc(store_role(s.kind))} — ${esc(s.name.toUpperCase())} reference.">
          + Add reference photos <input type="file" accept="image/*" multiple data-f="up" class="hidden">
        </label>`;
      const imgHost = $("[data-f=imgs]", card);
      imgs.forEach((r, i) => {
        const wrap = document.createElement("span");
        wrap.className = "subj-img";
        wrap.innerHTML = `<img src="/api/references/${esc(r.id)}/image?thumb=1" loading="lazy" alt="${esc(r.id)}">
          <button class="danger" title="Permanently delete ${esc(r.id)}">×</button>`;
        $("img", wrap).onclick = () => openLightbox(lbItems, i);
        $("button", wrap).onclick = async () => {
          if (!confirm(`Permanently delete ${r.id}? This cannot be undone.`)) return;
          try {
            await api(`/api/references/${r.id}`, { method: "DELETE" });
            toast(`${r.id} deleted.`); renderSubjectGrid();
          } catch (err) { toast(err.message, true); }
        };
        imgHost.append(wrap);
      });
      $("[data-f=up]", card).addEventListener("change", async (e) => {
        try {
          for (const f of e.target.files) {
            const fd = new FormData();
            fd.append("file", f);
            await api(`/api/subjects/${s.id}/reference`, { method: "POST", body: fd });
          }
          toast(`${e.target.files.length} reference(s) added to ${s.name}.`);
          renderSubjectGrid();
        } catch (err) { toast(err.message, true); }
      });
      $("[data-f=del]", card).onclick = async () => {
        if (!confirm(`Remove ${s.name}'s title card? Its reference images stay in the library.`)) return;
        try {
          await api(`/api/subjects/${s.id}`, { method: "DELETE" });
          toast(`${s.name} removed.`); renderSubjectTags(); renderSubjectGrid();
        } catch (err) { toast(err.message, true); }
      };
      grid.append(card);
    }
  };
  const store_role = k => ({ CHARACTER: "CHARACTER_LIKENESS", VEHICLE: "VEHICLE_GEOMETRY", PROP: "PROP_REFERENCE" }[k] || "REFERENCE");

  $("#wiz-subj-add").onclick = async () => {
    const name = $("#wiz-subj-name").value.trim();
    if (!name) return toast("Give the subject a name first.", true);
    try {
      const subj = await api("/api/subjects", { method: "POST", json: {
        name, kind: $("#wiz-subj-kind").value, source: "manual" } });
      $("#wiz-subj-name").value = "";
      toast(`${name} added — choose its reference photos.`);
      renderSubjectTags();
      await renderSubjectGrid();
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
    localStorage.setItem("wizardAnalysis", JSON.stringify(a));
    api("/api/wizard/analysis", { method: "PUT", json: a }).catch(() => {});
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
    $("#wiz-analyze-unlock").onclick = () => {
      if (!confirm("Unlock the screenplay analysis? Re-running replaces the design languages and subject recommendations with a fresh read. The current analysis is kept until the re-run succeeds.")) return;
      $("#wiz-provider").disabled = false;
      $("#wiz-analyze").classList.remove("hidden");
      lockHost.innerHTML = `<span class="mini">unlocked — pick a model and re-run; the previous analysis stands until then</span>`;
    };
  };

  const expandedWorlds = new Set();
  const renderWorlds = () => {
    const analysis = getAnalysis();
    const host = $("#wiz-analysis");
    if (!analysis) { host.innerHTML = ""; return; }
    const worlds = analysis.design_worlds || [];
    host.innerHTML = `
      ${analysis.logline ? `<div class="report" style="margin-top:14px"><b>Logline:</b> ${esc(analysis.logline)}</div>` : ""}
      <div class="fgroup" style="margin-top:14px"><span class="f-label">Design languages — click one to review or edit</span>
        <div id="wiz-world-tags" class="chips" style="margin-bottom:8px"></div>
        <div id="wiz-worlds"></div>
      </div>
      ${(analysis.key_locations || []).length ? `<p class="mini" style="margin-top:10px"><b>Recurring locations:</b> ${esc(analysis.key_locations.join(" · "))}</p>` : ""}
      ${(analysis.unresolved || []).length ? `<p class="mini"><b>Open visual questions:</b> ${esc(analysis.unresolved.join(" · "))}</p>` : ""}`;
    const tagHost = $("#wiz-world-tags", host);
    const wHost = $("#wiz-worlds", host);
    if (!worlds.length) tagHost.innerHTML = `<span class="mini">none — every board will use only the global sections of the Bible</span>`;
    worlds.forEach((w, i) => {
      const open = expandedWorlds.has(i);
      const chip = document.createElement("span");
      chip.className = "chip" + (open ? " open" : "");
      chip.style.cursor = "pointer";
      chip.textContent = w.name || "(unnamed)";
      chip.title = `${w.description || ""}\nClick to ${open ? "collapse" : "expand"}.`;
      chip.onclick = () => {
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
        <div class="fgroup" title="Lowercase trigger words used to auto-match this design language to board content."><span class="f-label">Keywords</span>
          <input type="text" data-f="keywords" value="${esc((w.keywords || []).join(", "))}" disabled></div>`;
      const editBtn = $("[data-f=edit]", row);
      editBtn.onclick = () => {
        if (editBtn.textContent === "Edit") {
          $$("input[data-f]", row).forEach(x => x.disabled = false);
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
        saveAnalysis(a);
        toast(`${a.design_worlds[i].name} saved.`);
        renderWorlds();
      };
      $("[data-f=del]", row).onclick = () => {
        if (!confirm(`Delete the design language "${w.name}"? It will be left out of the Bible draft. (Re-running the analysis can propose it again.)`)) return;
        const a = getAnalysis();
        a.design_worlds.splice(i, 1);
        saveAnalysis(a);
        expandedWorlds.clear();
        renderWorlds();
        toast(`"${w.name}" deleted.`);
      };
      wHost.append(row);
    });
  };

  $("#wiz-analyze").onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true;
    const busy = startBusy($("#wiz-analyze-busy"),
      "Reading the screenplay and identifying visual story elements and scenes…", "a minute or two");
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
      "Drafting the Art Direction Bible from screenplay, worlds, interview, and reference photos…",
      "this is the big one — a few minutes is normal");
    try {
      const chosenWorlds = (getAnalysis()?.design_worlds || [])
        .map(w => ({
          name: (w.name || "").trim(),
          notes: (w.description || "").trim(),
          keywords: w.keywords || [],
        })).filter(w => w.name);
      const answers = {
        worlds: chosenWorlds,
        touchstones: $("#wiz-touchstones").value.trim(),
        medium: $("#wiz-medium").value.trim(),
        palette: $("#wiz-palette").value.trim(),
        never: $("#wiz-never").value.trim(),
        notes: $("#wiz-notes").value.trim(),
        ref_ids: $$(".wiz-ref-use:checked").map(x => x.value),
      };
      const r = await api("/api/wizard/draft-bible", {
        method: "POST", json: { answers, provider: $("#wiz-provider").value } });
      $("#wiz-bible-wrap").classList.remove("hidden");
      $("#wiz-bible").value = r.markdown;
      toast(`Bible drafted by ${r.model} — review, edit, then save. Search for (PROPOSED) to find its guesses.`);
    } catch (err) { toast(err.message, true); }
    finally { busy.done(); btn.disabled = false; }
  };

  $("#wiz-save").onclick = async () => {
    const text = $("#wiz-bible").value.trim();
    if (!text) return;
    if (!confirm("Save this as the project's Art Direction Bible? It replaces the current bible and every future prompt uses it immediately.")) return;
    try {
      await api("/api/style-bible", { method: "PUT", json: { text } });
      toast("Art Direction Bible saved — it now governs every render.");
      loadBibleEditor();
    } catch (err) { toast(err.message, true); }
  };

  // ---- the Bible itself + project-wide lessons (the PD's living documents) ----
  const loadBibleEditor = async () => {
    const bible = await api("/api/style-bible");
    $("#style-bible").value = bible.text;
    $("#style-status").textContent = bible.is_default
      ? "showing built-in default — save to make it yours"
      : (bible.rev ? `REV ${bible.rev} — every future prompt uses this` : "");
  };
  await loadBibleEditor();
  $("#style-save").onclick = async () => {
    try {
      const r = await api("/api/style-bible", { method: "PUT", json: { text: $("#style-bible").value } });
      $("#style-status").textContent = `REV ${r.rev} — saved; every future prompt uses this`;
      toast("Art Direction Bible saved.");
    } catch (err) { toast(err.message, true); }
  };
  renderLessons();
}

/* ------------------------------------------------------------- references */

async function renderReferences() {
  useTemplate("tpl-references");
  const state = await api("/api/state");
  $("#role-list").innerHTML =
    state.suggested_roles.map(r => `<option value="${esc(r)}">`).join("");

  $("#ref-form").addEventListener("submit", async e => {
    e.preventDefault();
    const file = $("#ref-file").files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("role", $("#ref-role").value);
    fd.append("controls", $("#ref-controls").value);
    fd.append("does_not_control", $("#ref-nocontrols").value);
    fd.append("notes", $("#ref-notes").value);
    try {
      const ref = await api("/api/references", { method: "POST", body: fd });
      toast(`${ref.id} added as ${ref.role} (provisional).`);
      renderReferences();
    } catch (err) { toast(err.message, true); }
  });

  const refs = await api("/api/references");
  const grid = $("#ref-grid");
  grid.innerHTML = refs.length ? "" :
    `<div class="panel mini">No references yet. Start with a Board rendering style image — the painting-style anchor attached to every generation.</div>`;

  const isStyle = r => ["BOARD_RENDERING_STYLE", "CINEMATOGRAPHY_STYLE", "BOARD_LAYOUT_STYLE"].includes(roleHead(r.role));
  const newestFirst = refs.slice().reverse();
  const ordered = [...newestFirst.filter(isStyle), ...newestFirst.filter(r => !isStyle(r))];
  const lbItems = ordered.map(r => ({
    src: `/api/references/${r.id}/image`,
    caption: `${r.id} — ${r.role} (${r.status})`,
  }));

  let lastGroup = null;
  const groupHeader = (label, hint) => {
    const h = document.createElement("div");
    h.style.gridColumn = "1 / -1";
    h.innerHTML = `<span class="f-label">${esc(label)}</span> <span class="hint">${esc(hint)}</span>`;
    grid.append(h);
  };

  ordered.forEach((r, i) => {
    const group = isStyle(r) ? "style" : "subject";
    if (group !== lastGroup) {
      groupHeader(
        group === "style" ? "Lookbook — style anchors" : "Research — subject references",
        group === "style"
          ? "how it is painted and photographed — applies to everything; rendering/cinematography styles attach to every generation automatically"
          : "what things are — likenesses, geometry, props, environments; attached per panel");
      lastGroup = group;
    }
    const card = document.createElement("div");
    card.className = `ref-card ${r.status}`;
    card.innerHTML = `
      <img src="/api/references/${r.id}/image?thumb=true" alt="${esc(r.id)}" loading="lazy">
      <div class="body">
        <div><span class="badge ${r.status}">${r.status}</span> <b>${esc(r.id)}</b></div>
        <div class="role">${esc(r.role)}</div>
        <div class="meta">controls: ${esc(r.controls.join(", ") || "—")}</div>
        <div class="meta">does not control: ${esc(r.does_not_control.join(", ") || "—")}</div>
        ${r.notes ? `<div class="meta">${esc(r.notes)}</div>` : ""}
        <div class="meta">${r.used_in ? `used in ${r.used_in} render${r.used_in > 1 ? "s" : ""}` : "not used in a render yet"}</div>
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
      b.onclick = () => {
        const reason = prompt(`Reject ${r.id} — reason (recorded, quarantines the file):`);
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
      if (!confirm(`Permanently delete ${r.id} (${r.role})? It is removed from the library and from future generations — past candidates keep their own records. This cannot be undone.`)) return;
      try {
        await api(`/api/references/${r.id}`, { method: "DELETE" });
        toast(`${r.id} permanently deleted.`);
        renderReferences();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(del);
    grid.append(card);
  });
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
  persistForm("blankSpecDraft", ["spec-new-id", "spec-new-subject", "spec-new-mode"]);

  // Arriving from the dashboard's location map: seed the draft subject.
  const locHint = sessionStorage.getItem("draftLocationHint");
  if (locHint) {
    sessionStorage.removeItem("draftLocationHint");
    const promptEl = $("#spec-auto-prompt");
    if (promptEl && !promptEl.value.trim()) promptEl.value = locHint;
  }

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
          specification_id: $("#spec-auto-id").value,
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
          specification_id: $("#spec-new-id").value,
          subject: $("#spec-new-subject").value,
          mode: $("#spec-new-mode").value,
        },
      });
      toast(`${spec.specification_id} created.`);
      localStorage.removeItem("blankSpecDraft");
      renderSpecs(spec.specification_id);
    } catch (err) { toast(err.message, true); }
  });

  const specs = await api("/api/specs");
  const tbody = $("#spec-table tbody");
  tbody.innerHTML = specs.length ? "" :
    `<tr><td colspan="6" class="mini">No breakdown sheets yet.</td></tr>`;
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
        <button class="danger" data-f="del" title="Permanently delete this breakdown sheet and its candidates">Delete</button>
      </td>`;
    $("[data-f=open]", tr).onclick = () => openSpecEditor(s.specification_id);
    $("[data-f=del]", tr).onclick = async () => {
      const warn = s.locked
        ? `${s.specification_id} is APPROVED and LOCKED. Permanently delete it anyway, along with all its candidate images?\n\n(Refused automatically if it has any approved candidates or boards.)`
        : `Permanently delete ${s.specification_id} and all its candidate images? This cannot be undone.`;
      if (!confirm(warn)) return;
      try {
        const r = await api(`/api/specs/${s.specification_id}`, { method: "DELETE" });
        toast(`${r.deleted} deleted — ${r.candidates_removed} candidate record(s), ${r.images_removed} image(s) removed.`);
        renderSpecs();
      } catch (err) { toast(err.message, true); }
    };
    tbody.append(tr);
  }

  if (openId) openSpecEditor(openId);
}

async function openSpecEditor(specId) {
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
  const host = $("#spec-editor");
  host.innerHTML = "";
  const panel = document.createElement("div");
  panel.className = "panel spec-editor";
  panel.innerHTML = `
    <h3>${esc(spec.specification_id)}
      <span class="badge ${spec.status}">${spec.status}</span>
      ${locked ? '<span class="badge LOCKED">LOCKED</span>' : ""}
      ${spec.autofilled ? '<span class="badge PROVISIONAL">AUTO-FILLED — REVIEW BEFORE APPROVING</span>' : ""}
    </h3>
    ${spec.autofill ? `<p class="mini">Drafted by ${esc(spec.autofill.model)} from: “${esc(spec.autofill.prompt)}”</p>` : ""}
    <div id="sp-gate"></div>
    ${(spec.unresolved_questions || []).length ? `
      <div class="report" style="margin-bottom:12px"><b>Unresolved design questions</b> — the screenplay does not answer these; decide them yourself or run a DESIGN_EXPLORATION board:
        <ul>${spec.unresolved_questions.map(q => `<li>${esc(q)}</li>`).join("")}</ul>
      </div>` : ""}
    <div class="spec-section" style="margin-top:14px;border-top:none;padding-top:0">
      <h4>Identity <span class="hint">(what this sheet is)</span></h4>
      <div class="grid-form">
      <label title="What this board is about — a short human-readable name for the location, scene, prop, or character (e.g. Charlie's Cabin and GT40 Workshop). It appears in prompts and the spec list.">Subject <input type="text" id="sp-subject" value="${esc(spec.subject)}" ${locked ? "disabled" : ""}></label>
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
      <label class="setf" data-setf="location" title="The location as the screenplay names it — the middle of the slugline.">Location <input type="text" id="sp-location" placeholder="e.g. CHARLIE'S CABIN" value="${esc(spec.setting?.location || "")}" ${locked ? "disabled" : ""}></label>
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
      <label title="How many objects on this board may rest on WEAK evidence — things the screenplay only hints at rather than states (WEAK_INFERENCE rows in the evidence ledger). 0 means every object must be solidly supported. This budgets honest guesses; unsupported inventions are always forbidden regardless (their budget is pinned to 0).">Weak-inference budget <input type="number" id="sp-weak" min="0" value="${spec.canon_budget?.weak_inference_max ?? 2}" ${locked ? "disabled" : ""}></label>
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
        <div class="fgroup" title="Scene-locked lessons are the Bible's accumulated rules for specific scenes/subjects. Check the ones that apply to this board.">
          <span class="f-label">Scene lessons</span>
          <div id="sp-lessons">${bible_catalog.scene_lessons.map(n => {
            const sel = spec.scene_lessons ?? bible_inferred.scene_lessons;
            return `<label class="mini check"><input type="checkbox" value="${esc(n)}" ${sel.includes(n) ? "checked" : ""} ${locked ? "disabled" : ""}> ${esc(n)}</label>`;
          }).join("") || '<span class="mini">none recorded yet</span>'}</div>
        </div>
      </div>
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

  const allocById = {};
  (spec.layout?.panels || []).forEach(p => { allocById[p.id] = p.allocation_percent; });

  const panelsHost = $("#sp-panels", panel);
  const ledgerHost = $("#sp-ledger", panel);

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
  $("#sp-btype", panel).onchange = updateSettingVis;

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
          ${locked ? "" : `
          <div class="chip-add">
            <input type="text" data-f="req-new" placeholder="add a required object…">
            <button type="button" class="ghost" data-f="req-add" title="Add this required object (also creates its evidence-ledger row)">+ Object</button>
            ${subjects.length ? `
            <select data-f="subj-pick" title="Add a cast member or key subject from the Production Design collection as a required object. Green chips have reference material ready to attach at generation.">
              <option value="">+ cast &amp; subjects…</option>
              ${subjects.map(s => `<option value="${esc(s.name)}">${esc(s.name)} (${esc(s.kind)}${(s.ref_ids || []).length ? ` · ${s.ref_ids.length} ref` : " · no ref"})</option>`).join("")}
            </select>` : ""}
          </div>`}
        </div>
        <div class="fgroup" title="Objects that must NOT appear in this panel, comma-separated. Merged with the board-wide forbidden elements and project lessons in the prompt.">
          <span class="f-label">Forbidden objects</span>
          <input type="text" data-f="forbidden" placeholder="comma-separated…" value="${esc((p.forbidden_objects || []).join(", "))}" ${locked ? "disabled" : ""}>
        </div>
      </div>`;

    const chips = $("[data-f=chips]", row);
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
        x.onclick = () => { chip.remove(); dropLedgerRows(row.dataset.pid, obj); };
        chip.append(x);
      }
      chips.append(chip);
      if (syncLedger) ensureLedgerRow(row.dataset.pid, obj);
    };
    (p.required_objects || []).forEach(o => addChip(String(o), false));

    if (!locked) {
      const inp = $("[data-f=req-new]", row);
      const doAdd = () => {
        const v = inp.value.trim();
        inp.value = "";
        if (!v) return;
        if ($$(".chip", chips).some(c => c.dataset.obj.toLowerCase() === v.toLowerCase())) return;
        addChip(v, true);
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
      });
      $("[data-f=del-panel]", row).onclick = () => row.remove();
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

  (spec.panels || []).forEach(addPanelRow);
  (spec.evidence_ledger || []).forEach(addLedgerRow);
  updateSettingVis();

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
      out.panels.push({
        id,
        title: v("title").trim(),
        purpose: v("purpose").trim(),
        required_objects: $$(".chip", row).map(c => c.dataset.obj),
        forbidden_objects: split(v("forbidden")),
        evidence: ["USER_DIRECTED"],
        scale: "WIDE",
        composition_role: out.panels.length === 0 ? "hero" : "support",
        time_of_day: v("ptod"),
      });
      layoutPanels.push({ id, allocation_percent: parseFloat(v("alloc")) || 0 });
    }
    out.layout = { canvas: $("#sp-canvas", panel).value.trim(), panels: layoutPanels };

    out.evidence_ledger = [];
    let n = 0;
    for (const row of $$(".ledger-row", ledgerHost)) {
      const v = f => $(`[data-f=${f}]`, row).value;
      if (!v("object").trim()) continue;
      n += 1;
      out.evidence_ledger.push({
        object_id: `OBJ-${String(n).padStart(3, "0")}`,
        panel_id: v("panel_id").trim(),
        object: v("object").trim(),
        evidence_class: v("evidence_class"),
        source: v("source").trim(),
        confidence: 1.0,
        status: v("status"),
        rationale: "",
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
      if (!confirm(`Approve and LOCK ${specId}? Locked specs cannot be edited — only revised.`)) return;
      try {
        await api(`/api/specs/${specId}`, { method: "PUT", json: collect() });
        await api(`/api/specs/${specId}/approve`, { method: "POST" });
        toast(`${specId} approved and locked.`);
        renderSpecs(specId);
      } catch (err) { toast(err.message, true); }
    };
  } else {
    $("#sp-revise", panel).onclick = async () => {
      try {
        const clone = await api(`/api/specs/${specId}/revise`, { method: "POST" });
        toast(`Revision ${clone.specification_id} created.`);
        renderSpecs(clone.specification_id);
      } catch (err) { toast(err.message, true); }
    };
    $("#sp-unlock", panel).onclick = async () => {
      if (!confirm(`Unlock ${specId} for editing?\n\nThis VOIDS its approval (journaled in the approval log) and returns it to DRAFT — it disappears from the Boards tab until you approve it again, and re-approving mints a new spec hash. Unapproved candidates keep the hash they were generated against.\n\nRefused automatically if any APPROVED candidate or board depends on this spec — approved canon can never change out from under what it was approved against.\n\nIf you want to keep the approved version as history instead, use Create revision.`)) return;
      try {
        await api(`/api/specs/${specId}/unlock`, { method: "POST" });
        toast(`${specId} unlocked — now an editable DRAFT. Approve again when done.`);
        renderSpecs(specId);
      } catch (err) { toast(err.message, true); }
    };
  }
}

/* ----------------------------------------------------------------- boards */

const IMAGE_SIZES = ["1K", "2K", "4K"];
const ASPECTS = ["21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"];
const BOARD_TYPES = [
  { value: "SCENE", label: "SCENE — one screenplay scene, slugline-bound" },
  { value: "LOCATION", label: "LOCATION — a place across times" },
  { value: "ASSET", label: "ASSET — prop / vehicle / character" },
  { value: "LIGHTING_STUDY", label: "LIGHTING STUDY — derived, geometry-locked" },
  { value: "MASTER", label: "MASTER — presentation grammar" },
];
const TIMES_OF_DAY = ["DAWN", "MORNING", "DAY", "AFTERNOON", "DUSK", "EVENING", "NIGHT"];

const MODEL_PROVIDERS = [
  { value: "gemini", label: "Gemini (Nano Banana Pro)" },
  { value: "openai", label: "GPT Image 2 (direct)" },
  { value: "openai-chat", label: "ChatGPT pipeline (GPT-5.6 + image)" },
];

async function renderBoards() {
  useTemplate("tpl-boards");
  const specs = (await api("/api/specs")).filter(s => s.locked);
  const sel = $("#board-spec");
  sel.innerHTML = `<option value="">— select a signed-off breakdown —</option>` +
    specs.map(s => `<option value="${esc(s.specification_id)}">${esc(s.specification_id)} — ${esc(s.subject)}</option>`).join("");
  sel.onchange = () => sel.value && renderBoardPanels(sel.value);
  if (specs.length === 1) { sel.value = specs[0].specification_id; renderBoardPanels(sel.value); }
  if (!specs.length) {
    $("#board-panels").innerHTML =
      `<div class="panel mini">No signed-off breakdowns yet. Approve one on the Breakdowns tab first.</div>`;
  }
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
      ${(c.warnings || []).map(w => `<div class="meta" style="color:var(--warn)">⚠ ${esc(w)}</div>`).join("")}
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
        if (!confirm(`Create a lighting study from ${c.candidate_id}?\n\nThis panel is promoted to a LOCATION_GEOMETRY anchor, and a new draft board is created with one panel per approved atmosphere from the Bible. Review and approve the draft on the Breakdowns tab, then generate.`)) return;
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
    b.onclick = async () => {
      const role = prompt("Reference role for this render:", "SCENE_REFERENCE");
      if (role === null || !role.trim()) return;
      const notes = prompt("Notes (e.g. which screenplay scene this anchors):", "") ?? "";
      const controls = prompt("Controls (comma-separated, optional):", "") ?? "";
      try {
        const ref = await post(`/api/specs/${specId}/candidates/${c.candidate_id}/promote`,
          { role, notes, controls });
        toast(`${c.candidate_id} promoted to ${ref.id} (${ref.role}), approved as canon anchor.`);
      } catch (err) { toast(err.message, true); }
    };
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
      const reason = prompt(`Reject ${c.candidate_id} — reason:`);
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
      if (!confirm(`Permanently delete ${c.candidate_id}? The image file is removed from disk and cannot be recovered. Its rejection reason stays in the lessons list and rejection history.`)) return;
      try {
        await api(`/api/specs/${specId}/candidates/${c.candidate_id}`, { method: "DELETE" });
        toast(`${c.candidate_id} permanently deleted.`); refresh();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(b);
  }
  return cc;
}

const boardRoomSel = {};  // per-sheet: which panel is on the stage, which take is shown

async function renderBoardPanels(specId) {
  const host = $("#board-panels");
  host.innerHTML = `<div class="panel mini">Loading…</div>`;
  const [{ spec }, refs, candidates, appSettings, slotMap] = await Promise.all([
    api(`/api/specs/${specId}`),
    api("/api/references"),
    api(`/api/specs/${specId}/candidates`),
    api("/api/settings"),
    api(`/api/specs/${specId}/slot-map`).catch(() => null),
  ]);
  const prefProvider = appSettings.preferred_provider || "gemini";
  const isAutoStyle = r => ["BOARD_RENDERING_STYLE", "CINEMATOGRAPHY_STYLE"]
    .includes(roleHead(r.role));
  const styleAnchors = refs.filter(r => r.status === "APPROVED" && isAutoStyle(r));
  const approvedRefs = refs.filter(r => r.status === "APPROVED" && !isAutoStyle(r));
  host.innerHTML = "";

  function buildWorkbench(p) {
    const alloc = (spec.layout?.panels || []).find(x => x.id === p.id)?.allocation_percent;
    const panelCands = candidates.filter(c => c.panel_id === p.id).reverse();
    const roomSel = boardRoomSel[specId];
    roomSel.staged ??= {};
    let staged = panelCands.find(c => c.candidate_id === roomSel.staged[p.id]) || panelCands[0] || null;
    const role = p.composition_role === "hero" ? "HERO" : "STRIP";
    const takeItems = panelCands.map(c => ({
      src: `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
      caption: `${c.candidate_id} — ${p.id} (${c.status}) ${c.width}×${c.height}`,
    }));

    const stagedHtml = !staged ? `
      <div class="stage-shot empty"><span class="mini">No takes yet — set the model below and generate the first candidate.</span></div>` : `
      <div class="stage-shot" title="Click to open at full size">
        <img src="/api/specs/${specId}/candidates/${staged.candidate_id}/image" alt="${esc(staged.candidate_id)}" data-f="shot-img">
      </div>
      <div class="shot-under">
        <span class="shot-status ${esc(staged.status)}">${staged.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : esc(staged.status)}</span>
        <span class="shot-actions" data-f="primary-actions"></span>
      </div>
      <div class="shot-ghost-row" data-f="ghost-actions"></div>
      ${(staged.warnings || []).map(w => `<div class="meta" style="color:var(--warn)">⚠ ${esc(w)}</div>`).join("")}
      ${staged.status === "REJECTED" && staged.status_reason ? `<div class="meta" style="color:var(--bad)">rejected — ${esc(staged.status_reason)}</div>` : ""}
      ${staged.model_notes || staged.render_prompt ? `<details class="meta"><summary>${staged.prompt_source === "edited" ? "edited render prompt" : "model notes / rewritten prompt"}</summary><pre style="white-space:pre-wrap;font-size:11px;max-height:200px;overflow:auto">${esc(staged.render_prompt ? `RENDER PROMPT (user-edited):\n${staged.render_prompt}${staged.model_notes ? "\n\n" + staged.model_notes : ""}` : staged.model_notes)}</pre></details>` : ""}`;

    const takesHtml = `
      <div class="takes">
        <div class="takes-head">
          <span class="f-label">Takes · ${panelCands.length}</span>
          <span class="hint">rejected takes stay as a record</span>
        </div>
        <div class="takes-row">
          ${panelCands.map(c => `
            <button class="take${staged && c.candidate_id === staged.candidate_id ? " shown" : ""}${c.status === "REJECTED" ? " rejected" : ""}"
                    data-take="${esc(c.candidate_id)}"
                    title="${esc(c.candidate_id)} (${esc(c.status)})${c.status_reason ? ` — ${esc(c.status_reason)}` : ""}">
              <img src="/api/specs/${specId}/candidates/${c.candidate_id}/image" loading="lazy" alt="">
              <span class="take-label">${esc(c.candidate_id)}${c.status === "REJECTED" ? " REJECTED" : (staged && c.candidate_id === staged.candidate_id ? " SHOWN" : "")}</span>
            </button>`).join("")}
        </div>
      </div>`;

    const card = document.createElement("div");
    card.className = "panel";
    card.innerHTML = `
      <h2><span class="pid-badge">${esc(p.id)}</span> ${esc(p.title || p.purpose)}
        <span class="hint" style="float:right">${alloc ? alloc + "%" : ""} · ${role}${staged ? ` · ${esc(staged.aspect_ratio || "")}` : ""}</span></h2>
      <p class="mini">${esc(p.purpose)}</p>
      <p class="mini">required: ${esc((p.required_objects || []).join(", ") || "—")}
        &nbsp;·&nbsp; forbidden: ${esc((p.forbidden_objects || []).join(", ") || "—")}</p>
      ${stagedHtml}
      ${takesHtml}
      <div class="spec-section">
        <h4>Style anchors <span class="hint">(art direction — attached to every generation automatically)</span></h4>
        <div class="mini" style="margin-bottom:10px">${styleAnchors.map(r =>
          `<span class="badge LOCKED" title="Auto-attached — controls style only, never content">${esc(r.id)} ${esc(r.role)}</span>`).join(" ")
          || 'none yet — upload a Board rendering style or Cinematography style image on the Production Design tab'}
        </div>
        <h4>Attach subject references <span class="hint">(grouped by subject — ✓ green groups match this panel's required objects and are pre-checked)</span></h4>
        <div class="ref-groups">${(() => {
          const groups = {};
          for (const r of approvedRefs) {
            const suffix = String(r.role).split("—")[1]?.trim();
            const key = (suffix || String(r.role).trim()).toUpperCase();
            (groups[key] ??= { name: suffix || r.role, head: roleHead(r.role), ids: [] }).ids.push(r.id);
          }
          const matches = (obj, name) => {
            const o = String(obj).toLowerCase(), n = String(name).toLowerCase();
            return o.includes(n) || n.includes(o);
          };
          return Object.values(groups).map(g => {
            const matched = (p.required_objects || []).some(o => matches(o, g.name));
            return `<label class="check ref-group ${matched ? "has-ref" : ""}"
              title="${esc(g.ids.join(", "))}${matched ? " — matches a required object of this panel; pre-checked" : ""}">
              <input type="checkbox" data-ids="${esc(JSON.stringify(g.ids))}" ${matched ? "checked" : ""}>
              ${esc(g.name)} <span class="mini">${esc(g.head.replaceAll("_", " ").toLowerCase())} · ${g.ids.length}</span>
            </label>`;
          }).join("") || '<span class="mini">no approved subject references yet — add them via the cast & subjects cards on Production Design</span>';
        })()}
        </div>
        <div class="mini" data-f="ref-count" style="margin-top:6px"></div>
      </div>
      <div class="gen-row">
        <div class="fgroup" title="Which image engine renders this candidate. Gemini (Nano Banana Pro) — direct, supports native 4K. GPT Image 2 (direct) — OpenAI's image model given the compiled spec as-is. ChatGPT pipeline — GPT-5.6 first rewrites the spec into render prose (zero-invention rules), then calls the same image model ChatGPT uses. All three get identical spec, style, and references.">
          <span class="f-label">Model</span>
          <select data-f="model">${MODEL_PROVIDERS.map(m => `<option value="${m.value}" ${m.value === prefProvider ? "selected" : ""}>${m.label}</option>`).join("")}</select>
        </div>
        <div class="fgroup" title="Output resolution class: 1K for quick drafts, 2K for review candidates, 4K for finals. Always native resolution — never upscaled. (OpenAI flags output above 2560×1440 as experimental; prefer Gemini for 4K.)">
          <span class="f-label">Size</span>
          <select data-f="size">${IMAGE_SIZES.map(s => `<option ${s === "2K" ? "selected" : ""}>${s}</option>`).join("")}</select>
        </div>
        <div class="fgroup" title="Width-to-height shape of the panel image (16:9 wide, 21:9 ultrawide, 1:1 square, 9:16 tall…). Match it to the panel's role in the board layout.">
          <span class="f-label">Aspect</span>
          <select data-f="aspect">${ASPECTS.map(a => `<option ${a === "16:9" ? "selected" : ""}>${a}</option>`).join("")}</select>
        </div>
        <div class="gen-actions">
          <button class="ghost" data-f="preview" title="Show the exact compiled prompt this panel would send — free, no generation">Preview prompt</button>
          <button class="ghost" data-f="prose" title="Have GPT-5.6 rewrite the compiled spec into editable render prose without generating an image">Draft prose</button>
          <button class="primary" data-f="generate">Generate candidate</button>
        </div>
      </div>
      <div data-f="busy"></div>
      <div data-f="report"></div>`;

    const checkedRefs = () =>
      $$(".ref-groups input:checked", card).flatMap(x => JSON.parse(x.dataset.ids));
    const report = $("[data-f=report]", card);
    const busyHost = $("[data-f=busy]", card);

    const refCount = $("[data-f=ref-count]", card);
    const updateRefCount = () => {
      const n = checkedRefs().length;
      const total = n + styleAnchors.length;
      refCount.textContent = n
        ? `${n} subject image(s) + ${styleAnchors.length} style anchor(s) = ${total} attached` +
          (total > 14 ? " — over the 14-image limit; uncheck a group" : "")
        : "";
      refCount.style.color = total > 14 ? "var(--bad)" : "";
    };
    $(".ref-groups", card).addEventListener("change", updateRefCount);
    updateRefCount();

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
        "typically 30–120 seconds; the result appears in the gallery below",
        () => ctrl.abort());
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
        report.innerHTML = `<div class="report fail"><b>Generation failed</b> — ${esc(err.message)}
          <button class="ghost" style="float:right" onclick="this.parentElement.remove()">Dismiss</button></div>`;
      }
    };

    $("[data-f=generate]", card).onclick = (e) =>
      runGenerate(e.target, "Generate candidate");

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
            <button class="primary" data-f="generate-prose">Generate from this prose</button>
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
        renderBoardPanels(specId);
      };
    });

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
      const prim = $("[data-f=primary-actions]", card);
      const ghost = $("[data-f=ghost-actions]", card);

      if (c.status !== "REJECTED") prim.append(mk("Reject", "danger", async () => {
        const reason = prompt(`Reject ${c.candidate_id} — reason:`);
        if (reason === null) return;
        try {
          await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "REJECTED", reason });
          toast(`${c.candidate_id} rejected.`); refresh();
        } catch (err) { toast(err.message, true); }
      }));
      prim.append(mk("→ Reference", "ghost", async () => {
        const role = prompt("Reference role for this render:", "SCENE_REFERENCE");
        if (role === null || !role.trim()) return;
        const notes = prompt("Notes (e.g. which screenplay scene this anchors):", "") ?? "";
        const controls = prompt("Controls (comma-separated, optional):", "") ?? "";
        try {
          const ref = await post(`/api/specs/${specId}/candidates/${c.candidate_id}/promote`, { role, notes, controls });
          toast(`${c.candidate_id} promoted to ${ref.id} (${ref.role}), approved as canon anchor.`);
        } catch (err) { toast(err.message, true); }
      }, c.status !== "APPROVED"
        ? { disabled: true, title: "Approve this take first — only approved renders become canon anchors" }
        : { title: "Promote this approved render into the reference library" }));
      if (c.status !== "APPROVED") prim.append(mk("Approve panel", "primary", async () => {
        try {
          await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "APPROVED" });
          toast(`${c.candidate_id} approved.`); refresh();
        } catch (err) { toast(err.message, true); }
      }));

      if (c.kind !== "derived_palette") ghost.append(mk("Repair region", "ghost", () =>
        openRepair(`/api/specs/${specId}/candidates/${c.candidate_id}/image`,
          async (mask, instruction, provider) => {
            const fd = new FormData();
            fd.append("mask", mask, "mask.png");
            fd.append("instruction", instruction);
            fd.append("ref_ids", JSON.stringify(checkedRefs()));
            const rec = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/repair?provider=${encodeURIComponent(provider)}`,
              { method: "POST", body: fd });
            toast(`${rec.candidate_id} — repaired region of ${c.candidate_id}. It joins the takes strip.`);
            refresh();
          }),
        { title: "Paint over the area to fix, describe the change, pick the engine, and regenerate ONLY that region. The result is a new take; this one is untouched." }));
      ghost.append(mk("Crop → reference", "ghost", () =>
        cropToReference({ type: "candidate", spec_id: specId, id: c.candidate_id },
          `/api/specs/${specId}/candidates/${c.candidate_id}/image`),
        c.status !== "APPROVED"
          ? { disabled: true, title: "Approve this take first — crops enter the library as approved canon" }
          : { title: "Harvest a region of this image as a new reference with its own narrow role" }));
      ghost.append(mk("→ Light study", "ghost", async () => {
        if (!confirm(`Create a lighting study from ${c.candidate_id}?\n\nThis panel is promoted to a LOCATION_GEOMETRY anchor, and a new draft board is created with one panel per approved atmosphere from the Bible. Review and approve the draft on the Breakdowns tab, then generate.`)) return;
        try {
          const study = await api(`/api/specs/${specId}/candidates/${c.candidate_id}/lighting-study`, { method: "POST", json: {} });
          toast(`${study.specification_id} created with ${study.panels.length} atmosphere panels — review it on the Breakdowns tab, trim any you don't want, then approve.`);
        } catch (err) { toast(err.message, true); }
      }, c.status !== "APPROVED"
        ? { disabled: true, title: "Approve this take first — the study locks this panel's geometry" }
        : { title: "Derive a lighting-study board: this panel becomes the geometry anchor, and each new panel renders the same place under one approved atmosphere" }));
      if (c.status === "REJECTED") ghost.append(mk("Delete forever", "danger", async () => {
        if (!confirm(`Permanently delete ${c.candidate_id}? The image file is removed from disk and cannot be recovered. Its rejection reason stays in the lessons list and rejection history.`)) return;
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
        <select id="der-model">${MODEL_PROVIDERS.map(m => `<option value="${m.value}" ${m.value === prefProvider ? "selected" : ""}>${m.label}</option>`).join("")}</select>
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
  const roomSel = boardRoomSel[specId] ??= {};
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
      <div class="rail-label">PANELS <span>${approvedCount}/${pids.length}</span></div>
      ${spec.panels.map(p => `
        <button class="rail-panel${roomSel.panel === p.id ? " sel" : ""}" data-pid="${esc(p.id)}"
                title="${esc(p.title || p.purpose || "")}">
          <span class="rail-thumb${latestThumb(p.id) ? "" : " empty"}">${latestThumb(p.id)}</span>
          <span class="rail-pid">${esc(p.id)}</span>
          ${railMark(p.id)}
        </button>`).join("")}
    </div>
    <div class="rail-block rail-tail">
      <div class="rail-label">DERIVED</div>
      <button class="rail-panel${roomSel.panel === "__derived" ? " sel" : ""}" data-pid="__derived"
              title="Palette and materials built FROM this board's approved panels">
        <span class="rail-pid">PALETTE · MATERIALS</span>
        <span class="rail-mark ${derivedCands.length ? "okdot" : "none"}">${derivedCands.length ? "" : "—"}</span>
      </button>
      <div class="rail-note">ASSEMBLY LIVES IN <button class="block-act" data-f="to-assembly" style="font-size:11px;font-family:var(--mono)">05 BOARDS</button></div>
    </div>`;
  $("[data-f=to-assembly]", rail).onclick = () => showView("assembly");
  $$(".rail-panel", rail).forEach(btn => {
    btn.onclick = () => {
      roomSel.panel = btn.dataset.pid;
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

  const rejected = candidates.filter(c => c.status === "REJECTED");
  if (rejected.length) {
    const purge = document.createElement("div");
    purge.className = "panel mini";
    purge.innerHTML = `<button class="danger" data-f="purge">Delete all ${rejected.length} rejected candidate${rejected.length > 1 ? "s" : ""} permanently</button>
      <span class="hint">removes the image files from disk — rejection reasons stay in the lessons list and rejection history</span>`;
    stage.append(purge);
    $("[data-f=purge]", purge).onclick = async () => {
      if (!confirm(`Permanently delete ${rejected.length} rejected candidate image(s) for ${specId}? This cannot be undone.`)) return;
      try {
        const r = await api(`/api/specs/${specId}/candidates/purge-rejected`, { method: "POST" });
        toast(`${r.count} rejected candidate(s) permanently deleted.`);
        renderBoardPanels(specId);
      } catch (err) { toast(err.message, true); }
    };
  }

  const room = document.createElement("div");
  room.className = "board-room";
  room.append(rail, stage);
  host.append(room);
}

/* --------------------------------------------------- assembly (stage 05) */

async function renderAssembly() {
  useTemplate("tpl-assembly");
  const specs = (await api("/api/specs")).filter(s => s.locked);
  const sel = $("#asm-spec");
  sel.innerHTML = `<option value="">— select a signed-off breakdown —</option>` +
    specs.map(s => `<option value="${esc(s.specification_id)}">${esc(s.specification_id)} — ${esc(s.subject)}</option>`).join("");
  sel.onchange = () => sel.value && renderAssemblyFor(sel.value);
  if (specs.length === 1) { sel.value = specs[0].specification_id; renderAssemblyFor(sel.value); }
  if (!specs.length) {
    $("#assembly-host").innerHTML =
      `<div class="panel mini">No signed-off breakdowns yet. Approve one on the Breakdowns tab first.</div>`;
  }
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

  const approvedByPanel = {};
  for (const c of candidates) {
    if (c.status === "APPROVED") approvedByPanel[c.panel_id] = c.candidate_id;
  }
  const ready = spec.panels.every(p => approvedByPanel[p.id]);

  // The slot map makes the never-upscaled rule visible BEFORE a render is
  // spent: exact assembler geometry, one verdict per slot (design mock 4b).
  // Layout is presentation grammar, not canon — the variant picker rearranges
  // how approved work hangs on the canvas and is recorded on the board record.
  const slotHtml = sm => {
    const VERDICT = { OK: "OK", UNAPPROVED: "UNAPPROVED",
                      TOO_SMALL: "TOO SMALL", NO_CANDIDATE: "NO CANDIDATE" };
    const notReady = sm.slots.filter(s => s.status !== "OK");
    return `
      ${notReady.length ? `<div class="slot-alert">${notReady.length} SLOT${notReady.length > 1 ? "S" : ""} NOT READY —
        ${esc(notReady.map(s => `${s.panel_id} ${VERDICT[s.status].toLowerCase()}`).join(" · "))}
        — nothing is ever blown up${notReady.some(s => s.status === "TOO_SMALL") ? "; regenerate the small panel larger" : ""}</div>` : ""}
      <div class="slot-caption"><span class="f-label">Slot map</span>
        <span class="hint">true ${sm.canvas.width} × ${sm.canvas.height} canvas — all board typography is drawn by the app, never by the model</span></div>
      <div class="slotmap" style="aspect-ratio:${sm.canvas.width}/${sm.canvas.height}">
        ${sm.slots.map(s => `
          <div class="slot ${esc(s.status)}" style="left:${(s.x * 100).toFixed(2)}%;top:${(s.y * 100).toFixed(2)}%;width:${(s.w * 100).toFixed(2)}%;height:${(s.h * 100).toFixed(2)}%"
               title="${esc(s.title)} — slot ${s.slot_width}×${s.slot_height}px${s.candidate_id ? ` · ${s.candidate_id}${s.candidate_width ? ` ${s.candidate_width}×${s.candidate_height}px` : ""}` : ""}">
            <span class="slot-id">${esc(s.panel_id)}${s.allocation_percent ? ` · ${s.allocation_percent}%` : ""}</span>
            <span class="slot-verdict ${esc(s.status)}">${VERDICT[s.status]}</span>
            ${s.status === "TOO_SMALL" ? `<span class="slot-dims">${s.candidate_width}×${s.candidate_height} INTO ${s.slot_width}×${s.slot_height}</span>` : ""}
          </div>`).join("")}
      </div>`;
  };
  let slotMapHtml = "";
  try {
    slotMapHtml = slotHtml(await api(`/api/specs/${specId}/slot-map`));
  } catch { /* the map is a preview; assembly still states its own errors */ }

  const isStudy = String(spec.board_type || "").toUpperCase() === "LIGHTING_STUDY";
  const layoutOptions = `
    <option value="default">Sheet allocation — largest leads</option>
    <option value="grid">Grid — all panels equal</option>
    ${spec.panels.map(p => `<option value="hero:${esc(p.id)}">Hero: ${esc(p.id)} — ${esc((p.title || p.purpose || "").slice(0, 40))}</option>`).join("")}`;

  const asm = document.createElement("div");
  asm.className = "panel";
  asm.innerHTML = `
    <h2>Assemble board <span class="hint">(composes the latest approved candidate of every panel onto a 4K canvas with board typography — no upscaling)</span></h2>
    <div data-f="slot-wrap">${slotMapHtml}</div>
    <div class="row">
      ${isStudy ? "" : `<label class="mini" title="Presentation only — rearranges how the approved panels hang on the canvas. The sheet is untouched; the chosen layout is recorded on the board record, and the board still needs your approval.">Layout <select id="asm-layout">${layoutOptions}</select></label>`}
      <label class="mini" title="Pixel dimensions of the final assembled board. Panels are composed at native resolution — never upscaled — so every panel needs enough source resolution for its allocation.">Canvas <select id="asm-size">
        <option value="3840x2160" selected>3840 × 2160 (4K UHD)</option>
        <option value="4096x2304">4096 × 2304 (DCI-flavor wide)</option>
        <option value="4500x2400">4500 × 2400 (print-leaning)</option>
      </select></label>
      <button class="primary" id="asm-go" ${ready ? "" : "disabled"}>Assemble 4K board</button>
      ${ready ? "" : '<span class="mini">approve one candidate per panel to enable</span>'}
    </div>
    <div id="asm-busy"></div>
    <div class="ref-grid" id="asm-gallery" style="margin-top:12px"></div>`;
  host.append(asm);

  const layoutSel = $("#asm-layout", asm);
  if (layoutSel) {
    layoutSel.onchange = async () => {
      try {
        const sm = await api(`/api/specs/${specId}/slot-map?variant=${encodeURIComponent(layoutSel.value)}`);
        $("[data-f=slot-wrap]", asm).innerHTML = slotHtml(sm);
      } catch (err) { toast(err.message, true); }
    };
  }

  $("#asm-go", asm).onclick = async (e) => {
    const btn = e.target;
    btn.disabled = true; btn.textContent = "Assembling…";
    const [w, h] = $("#asm-size", asm).value.split("x").map(Number);
    const variant = layoutSel ? layoutSel.value : "default";
    const busy = startBusy($("#asm-busy", asm),
      `Assembling ${w}×${h} board from approved panels…`,
      "composing panels and typography onto the canvas");
    try {
      const b = await api(`/api/specs/${specId}/assemble`, { method: "POST", json: { width: w, height: h, variant } });
      toast(`${b.candidate_id} assembled (${b.width}×${b.height}, ${variant} layout) — BOARD CANDIDATE, unapproved.`);
      renderAssemblyFor(specId);
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

initLightbox();
// Deep-link support: #screenplay, #boards, … land on that view directly.
showView(views[location.hash.slice(1)] ? location.hash.slice(1) : "status");
