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
    <span class="busy-prog mono"></span>
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
    // NON_CANON_REVIEW R1: the phase is a sentence, the progress is
    // Courier beneath it — never one sentence carrying both.
    progress(msg) {
      const p = $(".busy-prog", el);
      p.textContent = msg || "";
      p.classList.toggle("hidden", !msg);
    },
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
    const err = new Error((data && data.detail) || `${res.status} ${res.statusText}`);
    err.status = res.status;
    // A gateway/proxy error (Railway "Application failed to respond", a 502/504
    // on a long render) carries no app JSON detail — the app never saw it. That
    // distinguishes "the connection was cut" from a real app failure.
    err.gateway = !(data && data.detail);
    throw err;
  }
  // The one chokepoint every call passes through, so the tutorial engine
  // can know the user actually did the thing a step asked for without a
  // hook at fifty call sites (tutorial.js). Successful calls only — a
  // step waits for the act to land, not for it to be attempted.
  document.dispatchEvent(new CustomEvent("sb:api", { detail: {
    method: String(opts.method || "GET").toUpperCase(),
    path: String(path).split("?")[0],
  } }));
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
        <button type="button" class="vchip on" data-f="mode-paint" title="Paint the region to repair">Paint</button>
        <button type="button" class="vchip" data-f="mode-erase" title="Erase painted area — fix an overshoot without starting over">Erase</button>
        <select data-f="prov" title="Either engine paints only your painted region — the app composites the result into the original, so every pixel outside your paint is carried over from the source unchanged (no re-encode noise, ever). They are simply different painters for the patch: GPT Image 2 works from a true mask; Gemini from a highlighted guide copy.">
          <option value="openai">GPT Image 2 — masked patch</option>
          <option value="gemini">Gemini (Nano Banana Pro) — guided patch</option>
        </select>
        <button class="ghost" data-f="clear">Clear</button>
      </span>
      <span class="row" style="margin:0">
        <span class="repair-gate mono" data-f="gate" role="status"></span>
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
      // Strokes replay in order: an eraser stroke un-paints whatever
      // earlier paint it crosses (user 2026-08-13).
      ctx.globalCompositeOperation = st.erase ? "destination-out" : "source-over";
      ctx.lineWidth = st.r * 2 * k;
      ctx.beginPath();
      st.pts.forEach((p, i) => i ? ctx.lineTo(p.x * k, p.y * k) : ctx.moveTo(p.x * k, p.y * k));
      if (st.pts.length === 1) ctx.lineTo(st.pts[0].x * k + 0.01, st.pts[0].y * k);
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
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
  const gate = $("[data-f=gate]", ov);
  // User-caught 2026-08-23, and the author could not diagnose it live —
  // "why isn't it allowing you to repair region. I don't know why that's a
  // bug." It was not a bug: Repair needs BOTH paint and an instruction, and
  // said neither. A disabled control has to state its unmet condition
  // beside it (product rule: gates are readable as state before they are
  // hit, never surfaced only as a refusal after the user acts).
  const update = () => {
    const painted = strokes.some(s => !s.erase);
    const said = !!instr.value.trim();
    goBtn.disabled = !(painted && said);
    gate.classList.toggle("hidden", painted && said);
    gate.textContent = painted && said ? ""
      : !painted && !said ? "PAINT THE REGION, THEN SAY WHAT CHANGES"
      : !painted ? "NOTHING PAINTED YET — PAINT THE REGION TO REPAIR"
      : "SAY WHAT SHOULD CHANGE IN THE PAINTED REGION";
    goBtn.title = goBtn.disabled ? gate.textContent : "";
  };
  let erasing = false;
  const modeP = $("[data-f=mode-paint]", ov), modeE = $("[data-f=mode-erase]", ov);
  const setMode = wantErase => {
    erasing = wantErase;
    modeP.classList.toggle("on", !wantErase);
    modeE.classList.toggle("on", wantErase);
  };
  modeP.onclick = () => setMode(false);
  modeE.onclick = () => setMode(true);
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    const r = (+$("[data-f=brush]", ov).value) * (img.naturalWidth / img.clientWidth) / 2;
    drawing = { r, pts: [toNat(e)], erase: erasing };
    strokes.push(drawing);
    redraw(); update();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (drawing) { drawing.pts.push(toNat(e)); redraw(); }
  });
  canvas.addEventListener("pointerup", () => { drawing = null; });
  $("[data-f=clear]", ov).onclick = () => { strokes = []; redraw(); update(); };
  instr.addEventListener("input", update);
  update();  // the gate must read before the first stroke, not after it

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
    mc.lineCap = mc.lineJoin = "round";
    for (const st of strokes) {
      // Paint punches transparency into the mask; an eraser stroke lays
      // opacity back — replayed in order, the mask matches the preview.
      mc.globalCompositeOperation = st.erase ? "source-over" : "destination-out";
      mc.strokeStyle = st.erase ? "#000" : "#fff";
      mc.lineWidth = st.r * 2;
      mc.beginPath();
      st.pts.forEach((p, i) => i ? mc.lineTo(p.x, p.y) : mc.moveTo(p.x, p.y));
      if (st.pts.length === 1) mc.lineTo(st.pts[0].x + 0.01, st.pts[0].y);
      mc.stroke();
    }
    mc.globalCompositeOperation = "source-over";
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
      // The crop lands in the library, but the view that asked for it is
      // holding the reference list IT fetched, so the new plate could not
      // be ticked until you navigated away and back (user-caught
      // 2026-08-16: "I saved a crop reference of Sal's cryochamber. It did
      // not appear in the references section for me to select"). A thing
      // made to be used has to be usable where it was made.
      refreshAfterReferenceChange();
    } catch (err) { toast(err.message, true); }
  });
}

// One redraw for "the reference library changed underneath this view".
// Crop is not the only door — anything that mints a reference while a
// working view is open leaves that view's own copy of the list stale.
function refreshAfterReferenceChange() {
  if ($("#board-panels") && $("#board-spec")?.value) {
    renderBoardPanels($("#board-spec").value);
  }
  if ($("#ref-counts")) renderReferences();
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Role family name, tolerant of legacy underscore-sanitized records.
// The em-dash split handles "CHARACTER_LIKENESS_—_JOHN"; the family-prefix
// pass handles the fully sanitized form "CHARACTER_LIKENESS_JOHN", where
// the dash itself was replaced. Without it a person's name became a role
// FAMILY and got enumerated as a kind of reference (user 2026-08-07:
// "Every group in the library is … character likeness john").
function roleHead(role) {
  const raw = String(role || "").split("—")[0].replace(/[\s_-]+$/, "").trim().toUpperCase();
  const fams = (typeof ROLE_FAMILIES !== "undefined" ? ROLE_FAMILIES : [])
    .map(f => f.head)
    .filter(h => raw === h || raw.startsWith(h + "_"))
    .sort((a, b) => b.length - a.length);
  return fams[0] || raw;
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

/* PALETTE_GROUPS_PLAN — swatch helpers, module scope because both the
   review strip and the step-1 column draw ramps from the same facts. */
// Relative luminance on the sRGB values. Ties break on the hex string
// so a ramp's order never shuffles between renders.
const lumaOf = hex => {
  const h = String(hex || "").replace("#", "");
  const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) || 0);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const rampOrder = sws => [...sws].sort((a, b) =>
  (b.hero ? 1 : 0) - (a.hero ? 1 : 0)
  || lumaOf(b.hex) - lumaOf(a.hex)
  || (a.hex < b.hex ? -1 : a.hex > b.hex ? 1 : 0));

// A pair is ONE swatch, so it gets one band's width — split into two
// half-height stripes rather than two bands.
const bandStyle = sw => sw.pair_hex
  ? `background:linear-gradient(${esc(sw.hex)} 0 50%, ${esc(sw.pair_hex)} 50% 100%)`
  : `background:${esc(sw.hex)}`;
const band = sw =>
  `<i data-ref="${esc(sw.ref_id)}" style="flex:${sw.hero ? 2 : 1};${bandStyle(sw)}"></i>`;

// The JS twin of wizard.parse_swatch_notes: proposals write
// LANGUAGE · NAME · HEX · CITE, manual swatches write NAME · HEX · CITE,
// so the hex is found by SHAPE and the rest placed around it.
function swatchNotes(notes) {
  let parts = String(notes || "").split(" · ").map(x => x.trim());
  const hero = parts[parts.length - 1] === "HERO";
  if (hero) parts = parts.slice(0, -1);
  const hx = parts.findIndex(x => HEXOK.test(x.split(" / ")[0].trim()));
  if (hx < 0) return { language: "", name: parts[0] || "", hex: "",
                       pair_hex: null, cite: "", hero };
  const hexes = parts[hx].split(" / ").map(x => x.trim());
  return {
    language: hx >= 2 ? parts[0] : "",
    name: hx >= 1 ? parts[hx - 1] : "",
    hex: hexes[0], pair_hex: hexes[1] || null,
    cite: parts.slice(hx + 1).join(" · "), hero,
  };
}


// A set of plate ids, stated compactly: a consecutive run collapses to
// its ends so eleven plates read as four facts. Used by the workbench's
// reference rows and by the take's provenance rail — one rendering, so
// the two can never disagree about what rode a render.
function idSpan(ids) {
  if (!ids || !ids.length) return "";
  const n = ids.map(i => +String(i).replace(/\D/g, ""));
  const run = n.length > 2 && n.every((x, i) => i === 0 || x === n[i - 1] + 1);
  return run ? `${esc(ids[0])} → ${esc(ids[ids.length - 1])}`
             : ids.map(esc).join(" · ");
}


// Drag-to-scroll with momentum, for a strip you read along rather than
// page through (user 2026-08-15). Pointer events so pen and touch behave
// like a mouse; the flick decays on a fixed per-frame factor so a long
// strip and a short one feel the same. Momentum is motion, so
// prefers-reduced-motion gets the drag without the glide.
// C4 (RULE_PASS 2026-08-16): the hidden scrollbar is allowed — drag and
// wheel both work and the contents are visible at rest — on condition the
// strip gains the last standard control it lacks. Arrow keys step it when
// it has focus, which closes the honesty gap hiding the bar opened.
function stripKeys(el) {
  if (!el) return;
  el.tabIndex = 0;
  el.addEventListener("keydown", e => {
    const step = el.clientWidth * 0.6;
    const by = e.key === "ArrowRight" ? step
      : e.key === "ArrowLeft" ? -step
      : e.key === "Home" ? -el.scrollLeft
      : e.key === "End" ? el.scrollWidth
      : 0;
    if (!by) return;
    e.preventDefault();
    el.scrollBy({ left: by, behavior: "smooth" });
  });
}

function dragScroll(el) {
  let down = false, startX = 0, startLeft = 0, lastX = 0, lastT = 0;
  let vel = 0, raf = 0, moved = 0, swallow = false;
  // A strip you drag is also a strip you click. The pointerup that ends a
  // drag would otherwise land as a click on whatever is under it, so a
  // real drag swallows exactly one click.
  el.addEventListener("click", e => {
    if (!swallow) return;
    swallow = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const glide = () => {
    el.scrollLeft -= vel;
    vel *= 0.94;
    // stop at rest, and at either end — coasting into a wall reads broken
    const atEnd = el.scrollLeft <= 0
      || el.scrollLeft >= el.scrollWidth - el.clientWidth - 1;
    if (Math.abs(vel) > 0.4 && !atEnd) raf = requestAnimationFrame(glide);
  };
  el.addEventListener("pointerdown", e => {
    if (e.button !== 0) return;
    down = true;
    cancelAnimationFrame(raf);
    startX = lastX = e.clientX;
    startLeft = el.scrollLeft;
    moved = 0;
    lastT = performance.now();
    vel = 0;
    el.classList.add("dragging");
  });
  el.addEventListener("pointermove", e => {
    if (!down) return;
    el.scrollLeft = startLeft - (e.clientX - startX);
    moved = Math.max(moved, Math.abs(e.clientX - startX));
    const now = performance.now();
    const dt = now - lastT;
    // px per frame at 60Hz, so the glide matches the hand that threw it
    if (dt > 0) { vel = ((e.clientX - lastX) / dt) * 16; lastX = e.clientX; lastT = now; }
  });
  const release = () => {
    if (!down) return;
    down = false;
    el.classList.remove("dragging");
    swallow = moved > 5;
    if (!reduce && Math.abs(vel) > 0.4) raf = requestAnimationFrame(glide);
  };
  el.addEventListener("pointerup", release);
  el.addEventListener("pointercancel", release);
  el.addEventListener("pointerleave", release);
}


/* STEP_SEQUENCE_SPEC §1.6/§1.7 — the step renderer, shared by every
   surface whose job is a sequence. A 46px gutter holds a two-digit Courier
   number: a label gutter says what KIND of thing a row is, a number says
   where you are in the work. Two states only, and a confirmed step dims
   but stays fully legible — it is evidence the user already ruled.
   Each surface owns where `done` is stored; the drawing is one thing. */
function seqStep({ n, id = "", label, meta = "", verbs = "", body = "",
                   done = false, frozen = false, frozenWhy = "" }) {
  // Two ways a step is done. A TICK is advisory — the user saying "I have
  // read this" — and is theirs to take back. FROZEN is the app stating a
  // fact: an approved take was rendered from this, so it is settled and
  // cannot be edited (user ruling 2026-08-16). A frozen step therefore
  // offers no Confirm and no way to unconfirm — the way back is
  // withdrawing the approval, which is an act on the take, not the step.
  done = done || frozen;
  return `
  <section class="step${+n % 2 === 0 ? " step-band" : ""}${done ? " step-done" : ""}"
           data-step="${esc(id || n)}">
    <span class="step-num mono">${n}</span>
    <div class="step-main">
      <div class="step-head">
        <span class="step-label mono">${label}</span>
        ${meta ? `<span class="step-meta mono">${meta}</span>` : ""}
        <span class="step-acts">
          ${frozen && id ? `<span class="step-confirmed step-settled mono" title="${esc(frozenWhy
             || "Settled by an approved take — withdraw the approval to change it")}">✓ SETTLED</span>` : ""}
          ${done && id && !frozen ? `<button type="button" class="step-confirmed mono" data-unconfirm="${esc(id)}"
             title="Unconfirm — this step needs you again">✓ CONFIRMED</button>` : ""}
          ${verbs}
          ${id && !done ? `<button type="button" class="verb" data-confirm="${esc(id)}"
             title="Mark this step confirmed. Advisory — it never blocks the act.">Confirm</button>` : ""}
        </span>
      </div>
      ${frozen && id ? `<div class="step-frozen mono">${esc(frozenWhy
         || "Settled by an approved take — withdraw the approval to change it")}</div>` : ""}
      ${body ? `<div class="step-content">${body}</div>` : ""}
    </div>
  </section>`;
}


function modal({ title, body = "", fields = [], confirmLabel = "Confirm",
                danger = false, custom = "", mount = null,
                extraLabel = "", extraDanger = false }) {
  return new Promise(resolve => {
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    ov.innerHTML = `
      <div class="modal${custom ? " modal-custom" : ""}" role="dialog" aria-modal="true">
        ${custom || `<div class="modal-title">${esc(title)}</div>`}
        ${custom ? "" : body ? `<p class="modal-body">${esc(body)}</p>` : ""}
        ${fields.map((f, i) => `
          <label class="modal-field">${esc(f.label)}
            ${f.textarea
              ? `<textarea data-mf="${i}" placeholder="${esc(f.placeholder || "")}">${esc(f.value || "")}</textarea>`
              : f.color
              ? `<span class="mf-color${HEXOK.test((f.value || "").trim()) ? "" : " is-unset"}">
                   <input type="text" data-mf="${i}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}">
                   <input type="color" data-mfc="${i}" value="${HEXOK.test((f.value || "").trim()) ? esc(f.value.trim()) : "#000000"}"
                          title="Pick a color — the hex beside it follows" aria-label="${esc(f.label)} picker">
                 </span>`
              : `<input type="text" data-mf="${i}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}">`}
            ${f.hint ? `<span class="hint">${esc(f.hint)}</span>` : ""}
            ${(f.recall || []).length ? `<span class="mf-recall">${
              f.recall.map(rc => `<button type="button" class="text-act" data-mfr="${i}"
                title="Use this brief again">${esc(rc)}</button>`).join("")}</span>` : ""}
          </label>`).join("")}
        ${custom ? "" : `<div class="modal-actions">
          ${extraLabel ? `<button class="${extraDanger ? "danger" : "ghost"}"
            data-mf="extra" style="margin-right:auto">${esc(extraLabel)}</button>` : ""}
          <button class="ghost" data-mf="cancel">Cancel</button>
          <button class="${danger ? "danger" : "primary"}" data-mf="ok">${esc(confirmLabel)}</button>
        </div>`}
      </div>`;
    document.body.append(ov);
    const done = val => { window.removeEventListener("keydown", onKey, true); ov.remove(); resolve(val); };
    const collect = () => Object.fromEntries(
      fields.map((f, i) => [f.name, $(`[data-mf="${i}"]`, ov).value.trim()]));
    // A recalled value fills its own field — recall, never constraint (R3).
    $$("[data-mfr]", ov).forEach(b => b.onclick = () => {
      const t = $(`[data-mf="${b.dataset.mfr}"]`, ov);
      t.value = b.textContent.trim();
      t.focus();
    });
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
      else if (!custom && e.key === "Enter" && e.target.tagName !== "TEXTAREA") { e.preventDefault(); done(collect()); }
    };
    window.addEventListener("keydown", onKey, true);
    ov.addEventListener("mousedown", e => { if (e.target === ov) done(null); });
    if (custom) {
      // A custom body brings its own verbs; the shell supplies only the
      // overlay, Esc and backdrop dismissal (PALETTE_GROUPS_PLAN §2).
      if (mount) mount(ov, done);
      // Focus the dialog itself, not its first button: focusing × paints
      // the amber focus ring on the one control that is not the point.
      const dlg = $(".modal", ov);
      dlg.tabIndex = -1;
      dlg.focus();
      return;
    }
    $("[data-mf=cancel]", ov).onclick = () => done(null);
    $("[data-mf=ok]", ov).onclick = () => done(collect());
    // A destructive act inside an edit modal (R17): resolves with a
    // sentinel; the caller runs its own confirm before acting.
    const extra = $("[data-mf=extra]", ov);
    if (extra) extra.onclick = () => done({ __extra: true });
    const first = $("input, textarea", ov);
    (first || $("[data-mf=ok]", ov)).focus();
  });
}
const askConfirm = async (title, body, confirmLabel = "Confirm", danger = false) =>
  (await modal({ title, body, confirmLabel, danger })) !== null;

// Revision identity (one board per unit, 2026-08-13) — mirrors
// app/revisions.py. Prefer server-sent revision fields when present;
// the regex is the client's fallback.
// Whole-word containment: "shop" must not match "workshop". One copy —
// the locations table and the required-object matcher both need it, and
// two copies of a matching rule is how two surfaces start disagreeing
// about what counts as a match.
const wordIn = (needle, hay) => !!needle && new RegExp(
  `(?<![a-z0-9])${needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![a-z0-9])`).test(hay);

// Words that name nothing. A group really is called "P02 SHACK IN THE
// MEADOW", and "the" clears three letters — without this, every object
// containing the word "the" matches it.
// The server owns this list (app/validation.py) and ships it in
// /api/settings as `name_stopwords` — one stoplist, not two (adversarial
// review F10: the client had a copy and the server had none, and a
// divergence is a panel silently matching or missing a reference). The
// literal below is the boot fallback for the moments before settings land;
// `adoptNameStopwords` replaces it with the server's.
let NAME_STOPWORDS = new Set([
  "the", "and", "for", "with", "from", "into", "its", "his", "her", "their",
  "that", "this", "over", "under", "onto", "off",
]);

function adoptNameStopwords(settings) {
  const list = settings && settings.name_stopwords;
  if (Array.isArray(list) && list.length) NAME_STOPWORDS = new Set(list);
}

// The words of a name worth matching on. Under three letters matches half
// the script. Module scope for the same reason wordIn is: FOUR surfaces
// were asking "does this phrase name that thing" with four different
// rules, and they disagreed (2026-08-16).
// Both sides of a name comparison get the same normalisation, or the
// difference between how a breakdown writes a thing and how its plate is
// filed becomes a missed match. Two real ones from the user's own board:
// "Sal's eyes" vs the card SAL CRAFT (possessive), and "closing
// cryochamber" vs the group SAL'S CRYO-CHAMBER (hyphen).
const normName = s => String(s).toLowerCase()
  .replace(/['’]s\b/g, "")     // possessive: sal's -> sal
  .replace(/['’]/g, "")        // any other apostrophe closes up
  .replace(/-/g, "");          // cryo-chamber -> cryochamber

const nameWords = n => normName(n)
  .split(/[^a-z0-9]+/).filter(w => w.length >= 3 && !NAME_STOPWORDS.has(w));

// Does this phrase name that thing? The whole name wins outright; failing
// that, any of the name's own words appearing whole-word in the phrase.
//
// Deliberately NOT the stricter distinctive-word rule used for SUBJECT
// IDENTITIES in generate.py. There, a shared word must refuse: putting
// one McGuire's traits on the other writes a wrong fact into the prompt.
// Here the answer only decides which plates are OFFERED and pre-ticked,
// where the two failures are not symmetric — an extra plate is visible in
// step 04 and one click to untick, a missing one is invisible and renders
// a stranger's face. "Sal's eyes" matched nothing because "sal" is shared
// by SAL CRAFT and SAL'S CRYO-CHAMBER, which are a person and his prop,
// not two people (user-caught 2026-08-16).
const namesPhrase = (obj, name) => {
  const o = normName(obj), n = normName(name);
  if (!o || !n) return false;
  // Word-bounded BOTH ways. A bare substring test let the group "SOD"
  // match the object "sodium vapour lamp" — the same failure wordIn was
  // written for ("shop" must not match "workshop"), reintroduced by the
  // whole-name shortcut sitting in front of it.
  if (wordIn(n, o) || wordIn(o, n)) return true;
  return nameWords(n).some(w => wordIn(w, o));
};

const baseOf = id => String(id).replace(/_R\d+$/, "");
const revOf = s => Number(s?.revision || 1);

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
    // User 2026-08-20: "Test & save" was one button doing two things and
    // it read as a single confusing act. Two acts now — Test answers and
    // stays open, Save closes.
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
        <p class="cred-form-foot" style="margin:0 0 14px">SAVES TO THIS STUDIO ONLY${P.test ? ` · TEST CALLS ${esc(P.name.toUpperCase())} AND STORES NOTHING` : ""} · THE PAGE UPDATES IN PLACE — NO RELOAD</p>
        <div class="busy busy-inline" data-mf="state" aria-live="polite"></div>
        <div class="modal-actions">
          <button class="ghost" data-mf="cancel">Cancel</button>
          ${P.test ? `<button class="ghost" data-mf="test">Test</button>` : ""}
          <button class="primary" data-mf="ok">${P.connector ? "Connect" : "Save"}</button>
        </div>
      </div>`;
    document.body.append(ov);
    const done = v => { ov.remove(); resolve(v); };
    // User-initiated only — the modal keeps focus until YOU reach for
    // the console.
    $("[data-mf=console]", ov).onclick = () =>
      window.open(P.link, "_blank", "noopener");
    ov.addEventListener("mousedown", e => { if (e.target === ov) done(null); });
    // The act takes seconds — it saves, then calls the provider for real
    // — and it used to give nothing back: no disabled state, no label
    // change, no line of text (user-caught 2026-08-16: "you click the
    // button, long delay, no feedback"). It also stayed clickable, so a
    // second click fired the whole pair again.
    const ok = $("[data-mf=ok]", ov), cancel = $("[data-mf=cancel]", ov);
    const stateEl = $("[data-mf=state]", ov);
    const okLabel = ok.innerHTML;
    let busy = false;
    // A3: `.busy` inline — same spinner, same phase-as-a-sentence, same
    // Courier progress as the block form, rendered under the act that
    // fired it. Elapsed appears only AFTER three seconds: before that it
    // is noise, and the whole reason it exists is telling a slow call
    // from a hung one.
    const say = (msg, kind = "") => {
      stateEl.className = `busy busy-inline${kind ? " " + kind : ""}`;
      stateEl.innerHTML = kind === "work"
        ? `<span class="spinner"></span><span class="busy-label">${esc(msg)}</span>`
          + `<span class="elapsed"></span>`
        : `<span class="busy-label">${esc(msg)}</span>`;
    };
    // Elapsed seconds, because a provider call that takes eight seconds
    // and one that has hung look identical without them.
    let tick = null, t0 = 0;
    // `which` is the button actually doing the work — without it a Test
    // relabelled SAVE to "Testing…", which is the wrong button entirely
    // (found in use, 2026-08-20).
    const setBusy = (on, label, which = null) => {
      const btn = which || ok;
      busy = on;
      ok.disabled = on;
      // Cancel stays LIVE. Disabling it locked the modal whenever the
      // provider was slow — worse than the silence it replaced. The key
      // is already saved by the time the test runs, so leaving mid-test
      // costs nothing but the verification.
      if (which) btn.disabled = on;
      btn.innerHTML = on ? esc(label) : (which ? "Test" : okLabel);
      clearInterval(tick);
      if (!on) { tick = null; return; }
      t0 = Date.now();
      tick = setInterval(() => {
        const el = $(".elapsed", stateEl);
        const secs = Math.round((Date.now() - t0) / 1000);
        if (el) el.textContent = secs >= 3 ? `${secs}s` : "";
      }, 1000);
    };
    // The scrim will not dismiss mid-flight — an accidental click should
    // not end an act you are waiting on. Cancel still will, deliberately.
    ov.addEventListener("mousedown", e => {
      if (e.target === ov && !busy) done(null);
    }, true);
    cancel.onclick = () => {
      if (busy) toast("Stopped waiting — nothing was saved.");
      clearInterval(tick);
      done(null);
    };
    // Test needs the key stored to call with it, so it saves first and
    // the foot line says so. It never closes: the whole point is to read
    // the answer and then decide.
    const testBtn = $("[data-mf=test]", ov);
    if (testBtn) testBtn.onclick = async () => {
      if (busy) return;
      const k = $("[data-mf=key]", ov).value.trim();
      if (!k) { say("Paste the key first.", "bad"); return; }
      const label = testBtn.innerHTML;
      testBtn.disabled = true;
      try {
        setBusy(true, "Testing…", testBtn);
        say(`A live call to ${P.name} — a few seconds.`, "work");
        // Nothing is stored. Testing used to save first, which made a
        // credential EXIST before the user agreed to keep it: the
        // first-run walkthrough advanced on Test, and Cancel left the key
        // behind (user 2026-08-20).
        await api("/api/settings/test", {
          method: "POST", json: { provider: P.test, key: k } });
        setBusy(false, "", testBtn);
        // What Test proves and what it does not (user, 2026-08-21). The
        // test is deliberately a models call, so it spends nothing — but
        // that means it passes on an account with no credit, and this
        // said "the key works" three seconds before the read died on
        // 429/insufficient_quota. Claiming more than was measured is the
        // one thing this product does not do.
        say(`${P.name} accepted the key — it is authentic. This does not `
            + `prove the account has credit; a run is what proves that. `
            + `Save to close.`, "ok");
      } catch (err) {
        setBusy(false, "", testBtn);
        say(`${P.name} refused it: ${err.message}`, "bad");
      } finally {
        testBtn.disabled = false;
        clearInterval(tick);
      }
    };

    $("[data-mf=ok]", ov).onclick = async () => {
      if (busy) return;
      const k = $("[data-mf=key]", ov).value.trim();      if (!k) { say("Paste the key first.", "bad"); return; }
      try {
        if (P.connector) {
          setBusy(true, "Syncing…");
          say(`Sending the key to ${P.name} and syncing its models…`, "work");
          const pub = await api(`/api/connectors/${P.connector}/key`, { method: "POST", json: { key: k } });
          if (pub.status !== "SYNCED") {
            setBusy(false);
            say(`${pub.label}: ${pub.status} — ${pub.last_error?.detail || "see the row"}`, "bad");
            return;
          }
          toast(`${pub.label}: ${pub.model_count} models synced.`);
        } else {
          // Save is a local write and nothing else — it is fast, and it
          // closes. Testing is the other button, by choice.
          setBusy(true, "Saving…");
          say("Saving the key to this studio…", "work");
          await api("/api/settings", { method: "POST", json: { [P.field]: k } });
          toast(`${P.name} key saved.`);
        }
        say("Done.", "ok");
        clearInterval(tick);
        done(true);
        renderSettings();
      } catch (err) {
        // In the modal, not only a toast: the toast can be missed and the
        // user is looking here.
        setBusy(false);
        say(err.message, "bad");
      }
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
      // C9 — an endpoint you host is the only one whose prompt limit
      // anyone here knows. Stated, it becomes a gate readable before a
      // render; unstated, nothing is checked, which is the honest
      // default because nobody has said.
      { name: "prompt_limit", label: "Prompt limit (characters)",
        placeholder: "leave blank if it has none, or you do not know" },
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

// The lightbox opens at the md tier (a few hundred KB) for a fast fit-view and
// pulls the raw 20–40 MB full image only when the user zooms to 100% (user
// 2026-08-09: loading full on open was slow and sometimes stalled). Only our
// image endpoints take ?size=; anything else loads unchanged.
const lbSize = (s, sz) => /\/image$/.test(String(s || "")) ? `${s}?size=${sz}` : s;

function lbShow() {
  const item = lb.items[lb.index];
  if (!item) return;
  lb.zoomed = false; lb.panX = lb.panY = 0; lb.atFull = false;
  lb.full = item.src;
  const img = $("#lb-img");
  const stage = $(".lb-stage");
  stage.classList.remove("zoomed");
  img.style.transform = "";
  img.onload = null;
  img.src = lbSize(item.src, "md");
  // B10: the same fact travels with the picture into the lightbox.
  $("#lb-caption").textContent = `${item.caption}${
    item.grammar ? `  ·  GRAMMAR — ${item.grammar}` : ""}  ·  ${
    lb.index + 1}/${lb.items.length}`;
  const setZoomLabel = () => {
    $("#lb-zoom").textContent = img.naturalWidth
      ? `${img.naturalWidth}×${img.naturalHeight} — fit (click for 100%)`
      : "";
  };
  img.complete ? setZoomLabel() : (img.onload = setZoomLabel);
  // The md tier paints immediately (2026-08-09: loading the raw 20-40MB
  // file on open was slow and sometimes stalled), and then the FULL image
  // is fetched behind it and swapped in when it has decoded — so the
  // lightbox always ends at full size without ever waiting to open
  // (user 2026-08-15: "I do not get the full sized image"). Zoom no
  // longer has to be the way you reach it.
  const full = lb.full;
  if (full && lbSize(full, "md") !== full) {
    const pre = new Image();
    pre.onload = () => {
      // the viewer may have stepped to another take while this loaded
      if (lb.full !== full) return;
      img.src = full;
      lb.atFull = true;
      setZoomLabel();
    };
    pre.src = full;
  }
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
      const zoomIn = () => {
        lb.panX = Math.min(0, (stage.clientWidth - img.naturalWidth) / 2);
        lb.panY = Math.min(0, (stage.clientHeight - img.naturalHeight) / 2);
        lbApplyPan();
        $("#lb-zoom").textContent = `${img.naturalWidth}×${img.naturalHeight} — 100% (drag to pan, click to fit)`;
      };
      // Pull the real pixels only now — the fit view was the md tier.
      if (!lb.atFull && lb.full && lbSize(lb.full, "md") !== lb.full) {
        lb.atFull = true;
        $("#lb-zoom").textContent = "loading full resolution…";
        img.onload = () => { img.onload = null; if (lb.zoomed) zoomIn(); };
        img.src = lb.full;
      } else zoomIn();
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
                assembly: renderAssembly,
                projects: () => renderSettings("productions"),
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
    // User ruling 2026-08-18: nothing runs without a model, so it is the
    // first link — not a separate mechanism bolted on beside the chain.
    // Settings stays reachable (it is the remedy) and so does Status (it
    // states the blocker); every stage waits.
    { label: "CONNECT AN AI MODEL", verb: "Connect a model",
      done: !!(state.capability && state.capability.any_credential),
      stage: "settings",
      sub: "Every stage runs on a model you connect — your key, your bill" },
    { label: "UPLOAD THE SCREENPLAY", verb: "Upload the screenplay", done: !!ss.screenplay, stage: "screenplay",
      sub: "The read starts here — everything downstream derives from the draft" },
    { label: "RUN THE SCRIPT SCAN", verb: "Run the script scan", done: !!pd.scan_done, stage: "wizard",
      sub: "Reads the draft for design languages, environments, locations and cast" },
    // "What is style reference?" (user, 2026-08-22, looking at stage 03's
    // gate). It was jargon, and its sub-line was wrong twice over: it named
    // Board layout, which is not one of these anchors, and said three when
    // there are four. It also counted approved IMAGES only, so a look
    // stated entirely in words — including one chosen from the style
    // pickers, which write words — never satisfied it.
    { label: "DESCRIBE THE LOOK", verb: "Describe the look",
      done: (pd.anchors_stated || 0) > 0, stage: "wizard",
      sub: "Any one of the four anchors — world texture, colour, "
         + "cinematography, rendering style — in words or a picture" },
    { label: "COMPLETE THE LOOK INTERVIEW", verb: "Complete the look interview",
      done: (pd.interview_answered || 0) > 0 || !!pd.bible_saved,
      optional: true, stage: "wizard",
      sub: "Optional — touchstones, medium, palette; blanks come back marked PROPOSED" },
    { label: "DRAFT THE ART DIRECTION BIBLE", verb: "Draft the Art Direction Bible", done: !!pd.bible_saved, stage: "wizard",
      sub: "Everything above becomes the document every render obeys" },
    { label: "DRAFT & LOCK A BREAKDOWN", verb: "Draft & lock a breakdown", done: (ss.breakdowns?.locked || 0) > 0, stage: "specs",
      tally: (ss.breakdowns?.locked || 0) > 0 ? "" : `${ss.breakdowns?.drafts || 0} DRAFTED · NONE LOCKED`,
      sub: "Only a locked breakdown can render" },
    // The tally answers the question the label raises. User-caught
    // 2026-08-23: "the board is still locked. Maybe it's not a bug. You
    // might have to generate three panels" — even the author could not tell
    // from the popover HOW MANY approvals the gate wanted, and guessed the
    // wrong rule about his own app. It wants one.
    { label: "RENDER AND APPROVE PANELS", verb: "Render and approve panels", done: (ss.panels?.approved || 0) > 0, stage: "boards",
      tally: (ss.panels?.approved || 0) > 0 ? ""
        : `${ss.panels?.candidates || 0} TAKE${(ss.panels?.candidates || 0) === 1 ? "" : "S"} RENDERED · NONE APPROVED YET · ONE IS ENOUGH`,
      sub: "Takes are judged full-size, one at a time" },
  ];
}

const STAGE_NUM = { screenplay: "01", wizard: "02", specs: "03", boards: "04", assembly: "05" };
// How much of the chain each stage's gate requires.
const UNLOCK_NEED = { specs: 6, boards: 7, assembly: 8 };
const UNLOCK_LINE = { specs: "THE MOMENT THE BIBLE IS SAVED",
                     boards: "THE MOMENT A SHEET LOCKS",
                     assembly: "THE MOMENT A PANEL IS APPROVED" };
const NO_MODEL_SENTENCE = "Every stage runs on an AI model, and none is "
  + "connected yet.";
const NEED_SENTENCE = { specs: "Breakdowns need the Art Direction Bible.",
                       boards: "Panels need a locked breakdown.",
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
    <p class="bp-sent">${esc(
      required[0]?.stage === "settings" ? NO_MODEL_SENTENCE
        : NEED_SENTENCE[stage] || "This stage's gate is upstream.")}
      <b>${COUNT_WORDS[n] || n} step${n === 1 ? "" : "s"} first.</b></p>
    <div class="bp-steps mono">
      ${remaining.map(s => `
        <div class="bp-step ${s === required[0] ? "cur" : ""}">
          <span class="bp-mark">${s === required[0] ? "→" : "·"}</span>
          <span>${esc(s.label)}${s.optional ? " · OPTIONAL" : ""}${
            s.tally ? `<br><span class="bp-tally">${esc(s.tally)}</span>` : ""}</span>
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
    /* Not every link is a numbered stage. "Connect a model" points at
       Settings, which has no number, and this read `STAGE undefined` from
       the day that link was added (2026-08-18) until it was seen on
       screen 2026-08-22. A place without a number says its own name. */
    ...s, addr: (STAGE_NUM[s.stage] ? `STAGE ${STAGE_NUM[s.stage]}`
                                    : String(s.stage || "").toUpperCase())
      + (s.optional && !s.done ? " · OPTIONAL" : ""),
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

/* Deep links (user 2026-08-12): every stage AND its selection is a plain
   shareable path — /panels/SPEC-0001, /boards/SPEC-0001/BOARD-0002,
   /boards/SPEC-0001/arrange, /panels/SPEC-0001/P03. Internal view names
   predate the stage renames; the URL speaks the product's words and
   these tables translate. The server serves index.html for any non-API
   path, so a pasted link boots straight into the addressed room. */
const VIEW_PATH = { status: "status", screenplay: "screenplay",
  wizard: "production-design", specs: "breakdowns", boards: "panels",
  assembly: "boards", references: "reference", projects: "productions",
  settings: "settings" };
const PATH_VIEW = Object.fromEntries(
  Object.entries(VIEW_PATH).map(([v, p]) => [p, v]));

let _routePanel = "";  // /panels/<spec>/<panel> — scroll target, one shot

function applyRoute(pathname) {
  const segs = pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const view = PATH_VIEW[segs[0] || ""];
  if (!view) return null;
  const sel = segs[1] || "";
  const sub = segs[2] || "";
  if (view === "specs" && sel) uiSet("openSpec", sel);
  if (view === "boards" && sel) {
    uiSet("boardSpec", sel);
    _routePanel = sub;
  }
  if (view === "assembly" && sel) {
    uiSet("asmSpec", sel);
    if (sub === "arrange") uiSet("asm.room", sel);
    else if (sub) uiSet("openBoard", sub);
  }
  return view;
}

function currentPath() {
  const enc = encodeURIComponent;
  let path = "/" + (VIEW_PATH[activeView] || "status");
  const sel = activeView === "specs" ? uiGet("openSpec", "")
    : activeView === "boards" ? uiGet("boardSpec", "")
    : activeView === "assembly" ? uiGet("asmSpec", "") : "";
  if (sel) {
    path += "/" + enc(sel);
    if (activeView === "assembly" && uiGet("asm.room", "") === sel) {
      path += "/arrange";
    }
  }
  return path;
}

// Keep the address honest after any selection change. replace by default
// (selection refinement); push for a genuine navigation step.
function syncUrl(push = false) {
  const p = currentPath();
  if (location.pathname === p) return;
  history[push ? "pushState" : "replaceState"](null, "", p);
}

window.addEventListener("popstate", () => {
  const v = applyRoute(location.pathname);
  if (v) showView(v, { push: false });
});

async function showView(name, { push = true } = {}) {
  // Own keys only — #toString would otherwise "exist" via the prototype,
  // dispatch garbage, and persist a view name that renders nothing.
  if (!Object.hasOwn(views, name)) name = "status";
  // BAND_CONDENSE B2: tools are not stages — the band condenses while a
  // tool view is open. Keyed here in the one router chokepoint, so boot
  // restores (persistent UI state) and both nav bars stay in sync free.
  document.body.classList.toggle("tool-mode",
    ["status", "references", "projects", "settings"].includes(name));
  // The active view is addressable from CSS so a surface can own its
  // measure (§1.11: the workbench is authored at 1920 with fixed rails;
  // every other view keeps the standing 1560px measure).
  document.body.dataset.view = name;
  activeView = name;
  uiSet("view", name);
  syncUrl(push);
  _roleCtx = null;  // suggestion sources refresh per navigation
  $$("#tools-nav button").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  updateBand();  // fire and forget — the band must never block the view
  try { await views[name](); }
  catch (err) { toast(err.message, true); }
  // Navigation is the other half of the tutorial engine's event surface
  // (tutorial.js): a step can wait for the user to reach a view, and a
  // trigger can fire on arrival. Emitted after the render, so anything
  // the step anchors to already exists.
  document.dispatchEvent(new CustomEvent("sb:view", { detail: { view: name } }));
}

/* The band is the pipeline's state, refreshed on every navigation:
   subline per stage from stage_summary, top border --ok complete /
   --accent current / --bad blocked / --line not reached, HERE on the
   viewed stage, engine dots from credentials. */
/* A long-lived tab is a time capsule: the SPA re-renders from in-memory
   JS while the studio updates beneath it (user-hit three times 2026-08-05,
   and again on 2026-08-15 — "it says live but there are no changes
   live"). A mismatch is STATED, never auto-reloaded: reloading is the
   user's act, mid-work. */
function showUpdateBarIfStale(h) {
  const boot = window.SB_BOOT_VERSION;
  const stale = boot && h && h.version && h.version !== boot;
  let bar = document.getElementById("update-bar");
  if (!stale) { bar?.remove(); return; }
  if (bar) return;
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

/* The check used to ride on navigation alone, so a tab parked on one
   panel never noticed a release — which is precisely the tab someone has
   open while a fix is being shipped for them. It now also runs on a timer
   and whenever the tab is brought back to the front, which is when a
   long-lived tab is most likely to be out of date. */
function watchForUpdates() {
  const check = () => api("/api/healthz").then(showUpdateBarIfStale).catch(() => {});
  setInterval(check, 60000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) check();
  });
  check();
}


async function updateBand() {
  let state, settings;
  try {
    [state, settings] = await Promise.all([api("/api/state"), api("/api/settings")]);
  } catch { return; }

  $("#brand-project").textContent = (state.project || "").toUpperCase();

  adoptNameStopwords(settings);
  _debugTools = !!settings.debug_tools;
  updateTextEditChip();

  // A long-lived tab is a time capsule: the SPA re-renders from in-memory
  // JS while the studio updates beneath it (user-hit three times,
  // 2026-08-05). Every navigation compares the server's version to the
  // one this tab booted with; a mismatch is STATED, never auto-reloaded —
  // reloading is the user's act, mid-work.
  api("/api/healthz").then(showUpdateBarIfStale).catch(() => {});

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
  // The view named "boards" is STAGE 04, Panels. The view named "assembly"
  // is stage 05, Boards. That collision produced a real deadlock, found in
  // the first user test (2026-08-23: "Approved a panel, 5 did not unlock"):
  // stage 04 read `bo.assembled` — the count of assembled BOARDS, which is
  // stage 05's OUTPUT — so 04 was never complete, the frontier never
  // advanced past it, and 05 rendered LOCKED however many panels were
  // approved. The only way out was to click the locked cell, whose
  // popover finds nothing outstanding and quietly lets you through.
  //
  // Stage 04 is complete when a PANEL is approved. `pn`, not `bo`.
  const complete = {
    screenplay: !!ss.screenplay,
    wizard: !!pd.bible_saved,
    specs: (bd.locked || 0) > 0,
    boards: (pn.approved || 0) > 0,
    assembly: (bo.approved || 0) > 0,
  };
  const BLOCK_STAGE = { dashboard: "screenplay", references: "wizard", wizard: "wizard",
                        specs: "specs", boards: "boards" };
  const blocked = new Set((state.blocking || [])
    .filter(b => b.kind !== "CARE")  // advisories never mark a stage blocked
    // A row may NAME the stage it blocks (server `stage`). Needed since
    // the KEY row: its action is "settings", which no stage maps to, and
    // the `|| "specs"` fallback would have painted stage 03 red for a
    // missing credential.
    .flatMap(b => b.stages?.length ? b.stages
      : [b.stage
        || (b.kind === "CITE" ? "screenplay" : BLOCK_STAGE[b.action] || "specs")]));
  // TRIAGE §2 Q3: the same two words in both cells, because it is the same
  // missing thing — that repetition is the point.
  const noEngine = new Set((state.blocking || [])
    .filter(b => b.kind === "KEY").flatMap(b => b.stages || []));
  const frontier = STAGE_ORDER.find(s => !complete[s]) || "assembly";

  // Everything past the frontier has an unmet gate and is inert (L1) —
  // 04 and 05 lock just like 03; the frontier itself is where you work.
  _bandState = state;
  const frontierIdx = STAGE_ORDER.indexOf(frontier);
  lockedStages = new Set(STAGE_ORDER.filter((s, i) => i > frontierIdx));
  // User ruling 2026-08-18: with no model connected the whole pipeline
  // waits. This is the APP's gate, not the walkthrough's — someone who
  // skips the tour meets exactly the same wall, and the lock popover
  // already explains itself and points at the remedy.
  if (state.capability && !state.capability.any_credential) {
    STAGE_ORDER.forEach(s2 => lockedStages.add(s2));
  }

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
    // TRIAGE §2 Q3 (2026-08-18): a red cell with no reason is exactly the
    // defect gate-readable-as-state exists to prevent. Two words in the
    // chip slot that already exists — no new colour.
    let why = $(".no-engine-chip", btn);
    if (noEngine.has(stage)) {
      if (!why) {
        why = document.createElement("span");
        why.className = "no-engine-chip mono";
        why.textContent = "NO ENGINE";
        $(".stage-top", btn)?.append(why);
      }
    } else why?.remove();
    // Focusable stays true — keyboard users get the same explanation.
    btn.setAttribute("aria-disabled", isLocked ? "true" : "false");
  }
}

/* -------------------------------------------------------------- dashboard */

const BLOCK_VERBS = { HOLD: "Review", GAP: "Add", KEY: "Connect",
                      SIZE: "Regenerate", CITE: "Review", CARE: "Backup" };
const BLOCK_SUPPORT = {
  HOLD: "Held rows on required objects block the lock — read each cited source, then pass or cut the row.",
  GAP: "A missing input upstream stops generation downstream.",
  SIZE: "Nothing is ever blown up — regenerate the panel at a larger size.",
  CITE: "The current draft no longer contains quotes this breakdown cites — review the flagged rows.",
  KEY: "The app calls models on your own key — without one, the roles that need it cannot run at all.",
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
  // U2 (HARNESS_AUDIT): the lead is a promotion, not a copy. The
  // promoted blocker leaves the list below and the count excludes it —
  // one fact, one place, one act. (The upload lead promotes the
  // screenplay blocker the same way.)
  const rest = first ? blockers.slice(1) : blockers;
  const next = state.next || { text: "Upload the screenplay", action: "screenplay" };
  const action = next.action === "dashboard" ? "screenplay" : next.action;
  const lead = $("#dash-next");
  // The verb IS the form — but only where the form can be used. Since the
  // user's 2026-08-18 ruling the upload is locked until a model is
  // connected, so a lead reading "Upload the screenplay" above a disabled
  // control would be naming an act the studio refuses. With no engine the
  // lead falls through to the promoted blocker, which is the credential.
  const canUpload = state.capability ? !!state.capability.any_credential : true;
  if (!state.screenplay && canUpload) {
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
    bindScreenplayUpload($("#status-screenplay-form"), state.capability);
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
  if (rest.length || advisories.length) {
    blocking.classList.remove("hidden");
    const row = b => {
      const i = state.blocking.indexOf(b);
      return `
        <div class="block-row">
          <span class="block-kind ${esc(b.kind)}">${esc(b.kind)}</span>
          <span class="block-text" title="${esc(b.detail || "")}">${monoIds(esc(b.text))}${
            b.sub ? `<span class="block-sub mono">${esc(b.sub)}</span>` : ""}</span>
          <button class="block-act" data-block="${i}">${esc(BLOCK_VERBS[b.kind] || "Open")}</button>
        </div>`;
    };
    // TRIAGE §2 Q1 (2026-08-18): one row survives a production switch, and
    // a reader who fixes it once must never see it filed as this
    // production's fault. One scope needs no label, so a normal install's
    // list is unchanged — the production head is drawn only when an
    // install row is present.
    const scoped = rows => {
      const inst = rows.filter(b => b.scope === "install");
      const prod = rows.filter(b => b.scope !== "install");
      if (!inst.length) return prod.map(row).join("");
      return `<div class="block-scope mono">THIS STUDIO — TRUE IN EVERY PRODUCTION</div>`
        + inst.map(row).join("")
        + (prod.length
          ? `<div class="block-scope mono">${esc((state.project || "THIS PRODUCTION").toUpperCase())}</div>`
            + prod.map(row).join("")
          : "");
    };
    blocking.innerHTML =
      (rest.length
        ? `<h2>Blocking — ${rest.length} more <span class="hint">beyond the one stated above</span></h2>`
          + scoped(rest)
        : `<h2>Advisory <span class="hint">${first
            ? "care of existing work — the one blocker is stated above"
            : "care of existing work — nothing blocks the next render"}</span></h2>`)
      + (advisories.length && rest.length
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
    bindScreenplayUpload($("#screenplay-form-main"), state.capability);
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
        <button class="ghost" data-f="read-script" title="Open the original uploaded file in a new tab — yours to read, never sent to a model">Read the screenplay</button>
        <button class="ghost" data-f="read-extract" title="Open the extracted text — this is the copy every model reads, and the only one they are ever sent. Two copies exist deliberately: sending the raw upload would cost tokens on every pass.">Read what the models read</button>
      </div>`;
    $("[data-f=read-script]").onclick = () =>
      window.open("/api/screenplay/file", "_blank");
    // The two-copies rule is the app's biggest standing token saving, and
    // until now the copy it saves on had no reader in the product — the
    // endpoint existed and nothing called it (adversarial review F9). A
    // rule the user cannot see is a rule they cannot trust.
    $("[data-f=read-extract]").onclick = () =>
      window.open("/api/screenplay/text", "_blank", "noopener");
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
    <div class="dsrow"><span>Breakdowns</span><b>${specMetas.length}</b></div>
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

  /* Inventory Script — the deterministic read, made visible.

     Every phase here is real and every number is one the parse actually
     returned. That matters more than usual on this button: the whole act
     takes a few hundred milliseconds, so a progress bar would be pure
     theatre. What it shows instead is the inventory BUILDING — scenes,
     then locations, then how many are thin, then broken citations — which
     is worth reading after it finishes as well as during. */
  const inventoryBtn = $("#scr-inventory");
  if (inventoryBtn) inventoryBtn.onclick = async () => {
    inventoryBtn.disabled = true;
    const lad = runLadder.create($("#scr-inventory-busy"), {
      title: "Inventorying the script",
      phases: [{ key: "read", label: "READ" }, { key: "scenes", label: "SCENES" },
               { key: "places", label: "LOCATIONS" }, { key: "cites", label: "CITATIONS" }],
      rows: [{ key: "chars", label: "Characters of extracted text" },
             { key: "scenes", label: "Scene headings" },
             { key: "locs", label: "Locations" },
             { key: "thin", label: "Thin coverage — leans on inference" },
             { key: "broken", label: "Broken citations" }],
    });
    try {
      lad.phase("read", "Reading the extracted text — the copy every model reads.");
      // Already on the screenplay record; a second endpoint to re-count
      // characters the app has known since upload would be a new route
      // answering a question already answered.
      lad.set("chars", (sp?.text_chars || 0).toLocaleString());

      lad.phase("scenes", "Finding scene headings by slugline. No model involved.");
      const locs = await api("/api/screenplay/locations");
      const rows = locs.locations || [];
      lad.set("scenes", rows.reduce((n, r) => n + (r.scenes || 0), 0));

      lad.phase("places", "Grouping locations and scoring how much the script says about each.");
      lad.set("locs", rows.length);
      lad.set("thin", rows.filter(r => (r.detail ?? 4) <= 1).length);

      lad.phase("cites", "Re-checking every quote the breakdowns cite against this draft.");
      const cr = await api("/api/screenplay/citation-report").catch(() => ({ missing: [] }));
      lad.set("broken", (cr.missing || []).length);

      lad.done(rows.length
        ? `Inventory complete — ${rows.length} location${rows.length === 1 ? "" : "s"} below.`
        : "No scene headings found — is this an image-only PDF?");
      /* The ladder STAYS. The Bible's panel dismisses itself when it
         finishes, and that is right for a minute-long act you watched —
         "once nothing is happening it is a spent receipt on the stage".
         This act takes a few hundred milliseconds, so the same rule
         inverts: nobody watches it, and the ladder is not a progress
         display but the inventory itself. Re-rendering the whole stage
         here wiped it before it could be read.

         So only the locations table below is redrawn. */
      const fresh = await api("/api/state").catch(() => null);
      if (fresh) renderLocations(fresh, langs);
      inventoryBtn.disabled = false;
    } catch (err) {
      lad.fail(err.message);
      inventoryBtn.disabled = false;
    }
  };

  bindScreenplayUpload($("#screenplay-form"), state.capability);

  // A read in flight survives leaving the view and coming back — it is
  // the longest thing the app does, and losing sight of it is the whole
  // complaint this surface answers.
  if (theRead.on) theRead.mount();
}

// One upload path for every screenplay form (Status lead, the stage's
// empty state, and Replace). Success lands on the Screenplay stage to
// show what the read found.
/* The button says "Upload & start the read" and, until 2026-08-20, only
   uploaded (user-caught). The read IS the Scene Scan — the pass that
   finds design languages, environments, locations and cast — so the verb
   now performs it.

   Two guards, both deliberate:

   - **Only a FIRST read.** A production that already has an analysis is
     not re-scanned, because a re-run overwrites curated design languages,
     environments and subjects — the same reason `Name the acts` is not a
     re-scan. Replacing a draft therefore uploads and stops, which is what
     `Upload a new draft` says it does.
   - **Only with an engine.** The read is a model call; with none it is
     not attempted, and the upload is gated on a credential anyway. */
/* A run ladder — phases across the top, results filling in beneath.

   Built 2026-08-28 so two acts that had nothing (the script inventory)
   or one spinner (the design plan) get the treatment the Bible draft
   already had: you can see what is being done and what came back.

   The rule it inherits from `theBible`, and the reason that one is worth
   copying: it NEVER invents progress. Where a phase is one model call,
   its comment says so — "one call. No per-section progress exists, so
   none is shown" — and the ladder shows a clock rather than a bar
   creeping toward a number nobody measured. A fake progress bar is a
   record describing an intention, which is the fault this project has
   spent a week removing from three other surfaces.

   So: a row fills when its REAL value lands, and a phase nobody can see
   inside says so in words. */
const runLadder = {
  create(host, { title, phases, rows }) {
    if (!host) return null;
    const t0 = Date.now();
    host.innerHTML = `<div class="rd rl">
      <div class="rd-head">
        <h3 class="stage-headline">${esc(title)}</h3>
        <span class="rd-meta mono"><span data-f="clock">00:00</span></span>
      </div>
      <div class="rd-phase mono">${phases.map(p =>
        `<span data-p="${esc(p.key)}">${esc(p.label)}</span>`).join("")}</div>
      <p class="rd-note mono" data-f="note"></p>
      <div class="rl-rows">${rows.map(r =>
        `<div class="rl-row" data-r="${esc(r.key)}">
           <span class="rl-lab">${esc(r.label)}</span>
           <span class="rl-val mono">—</span>
         </div>`).join("")}</div>
    </div>`;
    const el = host.firstElementChild;
    const order = phases.map(p => p.key);
    const clock = setInterval(() => {
      const s = Math.round((Date.now() - t0) / 1000);
      const c = $("[data-f=clock]", el);
      if (c) c.textContent = String(Math.floor(s / 60)).padStart(2, "0")
        + ":" + String(s % 60).padStart(2, "0");
    }, 1000);
    return {
      phase(key, note = "") {
        const at = order.indexOf(key);
        $$(".rd-phase span", el).forEach((s, i) => {
          s.classList.toggle("done", i < at);
          s.classList.toggle("now", i === at);
        });
        const n = $("[data-f=note]", el);
        n.textContent = note;
        n.classList.toggle("hidden", !note);
      },
      /* A row's value is whatever actually came back. `null` leaves it at
         the em dash — a phase that produced nothing says nothing rather
         than claiming a zero it did not measure. */
      set(key, value) {
        const r = $(`.rl-row[data-r="${key}"] .rl-val`, el);
        if (r && value !== null && value !== undefined) {
          r.textContent = String(value);
          r.closest(".rl-row").classList.add("in");
        }
      },
      done(note = "") {
        clearInterval(clock);
        $$(".rd-phase span", el).forEach(s => {
          s.classList.add("done"); s.classList.remove("now");
        });
        const n = $("[data-f=note]", el);
        n.textContent = note;
        n.classList.toggle("hidden", !note);
      },
      fail(msg) {
        clearInterval(clock);
        $$(".rd-phase span", el).forEach(s => s.classList.remove("now"));
        const n = $("[data-f=note]", el);
        n.textContent = msg;
        n.classList.remove("hidden");
        el.classList.add("rl-failed");
      },
      dismiss() { clearInterval(clock); host.innerHTML = ""; },
    };
  },
};


/* ============================================ the bible, as it is written
   One act (user, 2026-08-22: "generating the art direction bible and
   swatches should happen in a single step ... same razzle-dazzle feedback
   as the screenplay read"). It was two: write the bible, then find the
   swatch control, then run a second pass that read the bible again.

   Same honesty rule as theRead. Two of the four phases are single opaque
   model calls and say so; the two that surround them are real local work
   and carry the feedback:

     ASSEMBLE  what is actually being sent — every design language, the
               anchors in words, the cast count. Local, paced.
     WRITE     one call. No per-section progress exists, so none is shown.
     SECTIONS  the returned bible's OWN sections, walked as they are
               parsed — including whether each design language got the
               `Color identity` line that keeps its palette its own.
     COLOUR    one call, then the real proposed ramps.

   The ladder is one row per design language the whole way through, and
   the row's right-hand cell evolves: what we sent, then what came back,
   then the colours that language actually owns. */
const theBible = {
  on: false, phase: "", langs: [], anchors: [], subjects: 0,
  t0: 0, at: -1, said: [], sections: [], ramps: {}, identity: {},
  error: "", walk: null, clock: null, dwell: 700,

  begin(inputs) {
    Object.assign(this, {
      on: true, phase: "assemble", t0: Date.now(), at: -1, said: [],
      sections: [], ramps: {}, identity: {}, error: "",
      langs: inputs.langs || [], anchors: inputs.anchors || [],
      subjects: inputs.subjects || 0,
    });
    this.dwell = Math.max(320, Math.min(1100, 4200 / Math.max(1, this.langs.length)));
    this.mount();
    this.clock = setInterval(() => {
      const el = $("#bb-clock");
      if (el) el.textContent = this.elapsed();
    }, 1000);
    this.step();
  },

  elapsed() {
    const s = Math.max(0, Math.round((Date.now() - this.t0) / 1000));
    return String(Math.floor(s / 60)).padStart(2, "0") + ":"
      + String(s % 60).padStart(2, "0");
  },

  step() {
    if (!this.on || this.phase !== "assemble") return;
    this.at += 1;
    if (this.at >= this.langs.length) return this.writing();
    const l = this.langs[this.at];
    this.say(`${l} — sending its section of the read`);
    this.paint();
    this.walk = setTimeout(() => this.step(), this.dwell);
  },

  say(line) {
    this.said.push(line);
    if (this.said.length > 4) this.said.shift();
  },

  writing() {
    this.phase = "writing";
    clearTimeout(this.walk);
    this.say(`${this.langs.length} design languages · ${this.subjects} cast `
             + `· ${this.anchors.length} anchors stated`);
    this.paint();
  },

  /* The bible landed. Walk its real sections, and record which design
     languages were given a colour of their own — the thing whose absence
     made every palette identical. */
  written(markdown) {
    this.phase = "sections";
    this.sections = [...String(markdown || "").matchAll(/^##\s+(.+)$/gm)]
      .map(m => m[1].trim());
    for (const l of this.langs) {
      // To the NEXT heading, not a fixed window. A 1400-character slice ran
      // into the following section, so a language with no colour line
      // borrowed its neighbour's and the count read 4 of 4 when it was 3.
      const md = String(markdown || "");
      const i = md.indexOf(`## ${l}`);
      const next = i < 0 ? -1 : md.indexOf("\n## ", i + 3);
      const body = i < 0 ? "" : md.slice(i, next < 0 ? undefined : next);
      this.identity[l] = /\*\*Colou?r identity:\*\*/i.test(body);
    }
    const withColour = this.langs.filter(l => this.identity[l]).length;
    this.say(`${this.sections.length} sections written`);
    this.say(`${withColour} of ${this.langs.length} languages own a colour identity`);
    this.at = this.langs.length;
    this.paint();
  },

  colouring() { this.phase = "colour"; this.paint(); },

  coloured(res) {
    this.phase = "done";
    this.stopTimers();
    for (const g of (res.groups || [])) {
      this.ramps[g.language] = (g.swatches || []).map(s => s.hex);
    }
    const n = (res.groups || []).reduce((t, g) => t + (g.swatches || []).length, 0);
    this.say(`${n} colours proposed across ${(res.groups || []).length} languages`);
    for (const c of (res.collisions || [])) this.say(c.text);
    this.paint();
  },

  fail(msg) { this.phase = "failed"; this.error = msg || ""; this.stopTimers(); this.paint(); },

  stopTimers() {
    clearTimeout(this.walk); clearInterval(this.clock);
    this.walk = this.clock = null;
  },

  dismiss() {
    this.stopTimers(); this.on = false;
    const h = $("#bible-live"); if (h) h.remove();
  },

  mount() {
    if (!this.on) return;
    const host = $("#wiz-draft-busy");
    if (!host) return;
    host.innerHTML = `<div id="bible-live" class="rd">
      <div class="rd-head">
        <h3 class="stage-headline">Writing the Art Direction Bible</h3>
        <span class="rd-meta mono"><span id="bb-clock">00:00</span></span>
      </div>
      <div class="rd-phase mono">
        <span data-p="assemble">ASSEMBLE</span><span data-p="writing">WRITE</span
        ><span data-p="sections">SECTIONS</span><span data-p="colour">COLOUR</span>
      </div>
      <div id="bb-busy"></div>
      <p class="rd-note mono" id="bb-note"></p>
      <div class="rd-body">
        <div class="rd-ladder" id="bb-ladder"></div>
        <div class="rd-page" id="bb-page"></div>
      </div>
      <div class="rd-ticker" id="bb-ticker"></div>
    </div>`;
    this.paint();
  },

  paint() {
    const host = $("#bible-live");
    if (!host) return;
    const done = { assemble: 1, writing: 2, sections: 3, colour: 4, done: 5, failed: 4 }[this.phase] || 0;
    const order = ["assemble", "writing", "sections", "colour"];
    $$(".rd-phase span", host).forEach(el => {
      const n = order.indexOf(el.dataset.p) + 1;
      el.classList.toggle("done", n < done);
      el.classList.toggle("now", n === done && this.phase !== "done");
    });

    const busy = $("#bb-busy", host);
    const spin = { writing: "Writing the Art Direction Bible from the anchors, "
                          + "the read and the cast",
                   colour: "Scoping colour — proposing a palette for each "
                         + "design language from the bible just written" }[this.phase];
    busy.innerHTML = spin
      ? `<div class="busy wrap"><span class="spinner"></span>
         <span class="busy-label">${esc(spin)}.</span>
         <span class="busy-bar"></span></div>` : "";

    const note = $("#bb-note", host);
    note.classList.toggle("bad", this.phase === "failed");
    note.textContent = {
      assemble: "ASSEMBLED HERE — NOTHING SENT ANYWHERE YET",
      writing: "",
      sections: "THE BIBLE IS WRITTEN AND SAVED — BREAKDOWNS ARE OPEN",
      colour: "",
      done: "THE BIBLE IS WRITTEN, SAVED, AND ITS COLOUR PROPOSED",
      failed: `IT DID NOT FINISH — ${(this.error || "").toUpperCase()}`,
    }[this.phase] || "";

    $("#bb-ladder", host).innerHTML = this.langs.map((l, i) => {
      const state = this.phase === "assemble"
        ? (i <= this.at ? "done" : "") : "done";
      const now = this.phase === "assemble" && i === this.at;
      const ramp = this.ramps[l];
      const right = ramp
        ? `<span class="bb-ramp">${ramp.slice(0, 8).map(h =>
            `<i style="background:${esc(h)}"></i>`).join("")}</span>`
        : this.phase === "sections" || this.phase === "colour" || this.phase === "done"
          ? `<span class="rd-cast">${this.identity[l] ? "OWNS ITS COLOUR"
              : "NO COLOUR OF ITS OWN"}</span>`
          : `<span class="rd-bar"><i style="width:${now || state ? 100 : 0}%"></i></span>`;
      return `<div class="rd-row ${now ? "now" : state}">
        <span class="rd-n">${String(i + 1).padStart(2, "0")}</span>
        <span class="rd-slug">${esc(l)}</span>${right}</div>`;
    }).join("") || '<p class="hint">No design languages — the bible will derive them.</p>';

    const page = $("#bb-page", host);
    page.innerHTML = this.phase === "assemble" || this.phase === "writing"
      ? `<div class="rd-slugline">THE DIRECTOR'S ANSWERS</div>`
        + this.anchors.map(a =>
            `<span class="rd-action">${esc(a)}</span>`).join("")
      : `<div class="rd-slugline">SECTIONS WRITTEN</div>`
        + this.sections.map(x => `<span class="rd-action">${esc(x)}</span>`).join("");

    $("#bb-ticker", host).innerHTML = this.said.map(o =>
      `<p class="rd-obs mono">${esc(o)}</p>`).join("")
      + (this.phase === "done" || this.phase === "failed"
        ? `<p class="rd-done-row"><button type="button" class="ghost"
             data-f="bb-close">Close</button></p>` : "");
    const x = $("[data-f=bb-close]", host);
    if (x) x.onclick = () => this.dismiss();
  },
};

/* ================================================== the read, as it happens
   The model's read is ONE call. It cannot report per-scene progress, and a
   bar that implied otherwise would be the exact species of confident
   fiction this product exists to prevent.

   So the live feedback is the LOCAL parse — real sluglines, real cue
   lines, real counts, from GET /api/screenplay/digest — walked scene by
   scene while the model works. Every word on this surface is measured
   from the file. The model's own phase says plainly that it has nothing
   to report, because it has nothing to report.

   Amber discipline: exactly one amber in this panel, ever — the bar of
   the scene being read right now. Done bars are --ok, like every other
   meter in the app. */
const theRead = {
  on: false, phase: "", engine: "", t0: 0, scenes: [], obs: [], at: -1,
  said: [], found: null, error: "", walk: null, clock: null, dwell: 900,

  async begin(engine, preview = false) {
    this.on = true; this.phase = "parse"; this.engine = engine || "the model";
    this.preview = !!preview;
    this.t0 = Date.now(); this.at = -1; this.said = []; this.found = null;
    this.error = "";
    const d = await api("/api/screenplay/digest").catch(() => null);
    this.scenes = (d && d.scenes) || [];
    this.obs = (d && d.observations) || [];
    // Spread the walk over about a minute — the shape of a read — but
    // never so fast it cannot be read, nor so slow it feels stuck.
    this.dwell = Math.max(420, Math.min(1700, 60000 / Math.max(1, this.scenes.length)));
    if (activeView === "screenplay") this.mount();
    this.clock = setInterval(() => this.tickClock(), 1000);
    this.step();
  },

  step() {
    if (!this.on || this.phase !== "parse") return;
    this.at += 1;
    if (this.at >= this.scenes.length) {
      // The parse is done. In a real read the model is still working; in a
      // preview there is no model, and saying "MODEL" would be the one
      // thing this surface exists not to do.
      this.phase = this.preview ? "previewed" : "model";
      if (this.preview) { this.said = this.obs.slice(); this.stopTimers(); }
      this.paint();
      return;
    }
    // Reveal an observation as the scenes that prove it go by.
    const due = Math.round((this.at + 1) / Math.max(1, this.scenes.length) * this.obs.length);
    while (this.said.length < Math.min(due, this.obs.length))
      this.said.push(this.obs[this.said.length]);
    this.paint();
    this.walk = setTimeout(() => this.step(), this.dwell);
  },

  tickClock() { const el = $("#rd-clock"); if (el) el.textContent = this.elapsed(); },

  elapsed() {
    const s = Math.max(0, Math.round((Date.now() - this.t0) / 1000));
    return String(Math.floor(s / 60)).padStart(2, "0") + ":"
      + String(s % 60).padStart(2, "0");
  },

  finish(analysis) {
    this.stopTimers();
    this.phase = "found"; this.found = analysis || {};
    this.said = this.obs.slice();      // the rest of what the parse saw
    this.at = this.scenes.length - 1;
    this.paint();
    /* And then it leaves (user, 2026-08-21: "at the end of reading and
       processing, the read-is-in section should go away"). The panel is
       an account of something happening; once nothing is happening it is
       a spent receipt sitting on the stage. It holds long enough to read
       the count, and the toast carries the result durably — so the
       finding survives the panel that announced it. Dismiss still works
       immediately. */
    const langs = (this.found.design_worlds || []).length;
    const subj = (this.found.subjects || []).length;
    toast(`The read found ${langs} design language(s) and ${subj} subject(s) `
          + "— review them on Prod. Design.");
    clearTimeout(this.bye);
    this.bye = setTimeout(() => { if (this.phase === "found") this.dismiss(); },
                          7000);
  },

  fail(msg) { this.stopTimers(); this.phase = "failed"; this.error = msg || ""; this.paint(); },

  /* An engine failure is never just "the read failed" — canon says a
     blocker states its condition and links to where it is resolved, and
     these conditions do not share a resolution.

     Learned the hard way (user, 2026-08-21): a key that authenticated
     fine, on an account with no credit, came back 429/insufficient_quota.
     That matched nothing here, so the panel said "THE READ DID NOT
     FINISH" and stopped — while the app was holding a message that said
     exactly what was wrong and where to fix it. */
  diagnose() {
    const e = this.error || "";
    const E = this.engine.toUpperCase();
    if (/\b401\b|invalid[_ ]?api[_ ]?key|incorrect api key|unauthoriz/i.test(e))
      return { kind: "auth", line: E + " REFUSED THE KEY IT WAS GIVEN" };
    if (/insufficient_quota|credit[_ ]balance|no credits remaining|exceeded your current quota|billing/i.test(e))
      return { kind: "quota",
               line: E + " TOOK THE KEY AND REFUSED THE WORK — THE ACCOUNT "
                 + "HAS NO CREDIT LEFT. THE KEY IS GOOD; THE BALANCE IS NOT" };
    if (/rate[_ ]?limit|\b429\b|too many requests/i.test(e))
      return { kind: "rate",
               line: E + " IS RATE-LIMITING THIS KEY — THE READ CAN BE RUN "
                 + "AGAIN SHORTLY" };
    return { kind: "other", line: "THE READ DID NOT FINISH" };
  },

  refused() { return this.diagnose().kind === "auth"; },

  stopTimers() {
    clearTimeout(this.walk); clearInterval(this.clock);
    this.walk = this.clock = null;
    // A lock that survives its reason is how an app becomes unusable.
    document.body.dataset.readBusy = "0";
  },

  dismiss() {
    this.stopTimers(); clearTimeout(this.bye); this.on = false;
    document.body.dataset.readBusy = "0";
    const h = $("#read-live"); if (h) h.remove();
  },

  /* ---- markup ---------------------------------------------------- */

  mount() {
    if (!this.on) return;
    /* Stage 01 only (user, 2026-08-21: "Reading the Draft panel was
       copied to the Prod Design tab — remove"). Reading the draft is a
       stage 01 fact, and a panel that follows the user to the next stage
       is not progress there, it is a leftover. The Scene Scan reports
       through its own busy line, where it always did. */
    const main = $(".dash-main");
    if (!main) return;
    let host = $("#read-live");
    if (!host) {
      host = document.createElement("div");
      host.id = "read-live"; host.className = "panel rd";
      main.prepend(host);
    }
    host.innerHTML = this.html();
    this.paint();
  },

  html() {
    const rows = this.scenes.map(sc =>
      '<div class="rd-row" data-n="' + sc.n + '">'
      + '<span class="rd-n">' + String(sc.n).padStart(2, "0") + "</span>"
      + '<span class="rd-slug">' + esc(sc.heading) + "</span>"
      + '<span class="rd-bar"><i></i></span>'
      + "</div>").join("");
    return `
      <div class="rd-head">
        <h3 class="stage-headline">Reading the draft</h3>
        <span class="rd-meta mono"><b>${esc(this.engine.toUpperCase())}</b>
          · <span id="rd-clock">00:00</span></span>
      </div>
      <div class="rd-phase mono">
        <span data-p="parse">PARSE</span><span data-p="model">MODEL</span><span data-p="found">FOUND</span>
      </div>
      <div id="rd-busy"></div>
      <p class="rd-note mono" id="rd-note"></p>
      <div class="rd-body">
        <div class="rd-ladder" id="rd-ladder">${rows
          || '<p class="hint">No sluglines parsed — the model is reading the text as a whole.</p>'}</div>
        <div class="rd-page" id="rd-page"></div>
      </div>
      <div class="rd-ticker" id="rd-ticker"></div>`;
  },

  paint() {
    const host = $("#read-live");
    if (!host) return;

    $$(".rd-phase span", host).forEach(el => {
      const p = el.dataset.p;
      el.classList.toggle("now", p === this.phase
        || (this.phase === "failed" && p === "model"));
      el.classList.toggle("done",
        (p === "parse" && this.phase !== "parse")
        || (p === "model" && this.phase === "found"));
    });

    /* The model half is a single call that can run for minutes, and it
       used to be reported by a static line of text — so a surface whose
       whole job is to look alive went still at exactly the point the user
       had least idea what was happening. This is the app's own `.busy`
       component, not a new one. */
    const busy = $("#rd-busy", host);
    if (busy) {
      busy.innerHTML = this.phase === "model"
        // `wrap` is required, not decorative: .busy-bar is flex-basis 100%
        // and without wrapping it squeezes the label to one word per line.
        ? '<div class="busy wrap"><span class="spinner"></span>'
          + '<span class="busy-label">Scoping production needs — '
          + esc(this.engine) + " is reading the whole draft in one call. "
          + "It reports nothing until it is done.</span>"
          + '<span class="busy-bar"></span></div>'
        : "";
    }
    // Nothing else in the app offers to start work while a read is
    // spending money on this one.
    document.body.dataset.readBusy = this.phase === "model" ? "1" : "0";

    const note = $("#rd-note", host);
    if (note) {
      if (this.phase === "parse")
        note.textContent = "PARSED HERE — " + this.scenes.length
          + " SCENES OFF THE PAGE, NOTHING SENT ANYWHERE YET";
      else if (this.phase === "model")
        note.textContent = this.engine.toUpperCase() + " IS READING — ONE CALL, NO "
          + "PER-SCENE PROGRESS TO REPORT. THE PARSE ABOVE IS COMPLETE, AND LOCAL.";
      else if (this.phase === "previewed")
        note.textContent = "PREVIEW ONLY — THE PARSE IS COMPLETE AND REAL. "
          + "NO MODEL WAS CALLED, SO THE READ'S OWN FINDINGS ARE NOT HERE.";
      else if (this.phase === "found") note.textContent = "THE READ IS IN.";
      else {
        // Do NOT shout a provider's error back at the user. Uppercasing a
        // 200-character 401 body — URL, masked key and all — was the first
        // thing this panel did on its first real failure, and it made the
        // one sentence that mattered ("the key was refused") the hardest
        // to find. The verbatim message goes below, in its own voice.
        note.textContent = this.diagnose().line;
      }
      note.classList.toggle("bad", this.phase === "failed");
    }

    $$(".rd-row", host).forEach(row => {
      const n = +row.dataset.n, bar = $("i", row);
      const done = n <= this.at || this.phase === "found" || this.phase === "model";
      const now = n === this.at + 1 && this.phase === "parse";
      row.classList.toggle("done", done && !now);
      row.classList.toggle("now", now);
      if (now) { bar.style.transitionDuration = this.dwell + "ms"; bar.style.width = "100%"; }
      else if (done) { bar.style.transitionDuration = "0ms"; bar.style.width = "100%"; }
      if (now) row.scrollIntoView({ block: "nearest" });
    });

    const page = $("#rd-page", host);
    const sc = this.scenes[Math.max(0, this.at)];
    if (page && sc) {
      // The snapshot is the script's own text, set the way a script is
      // set: cue lines indented, action flush left. Nothing rewritten.
      const lines = (sc.snapshot || []).map(l => {
        const t = l.trim();
        const cue = t && t === t.toUpperCase() && t.length <= 34;
        return '<span class="' + (cue ? "rd-cue" : "rd-action") + '">' + esc(t) + "</span>";
      }).join("");
      const who = (sc.speakers || []).length
        ? '<div class="rd-with">WITH ' + esc(sc.speakers.join(" · ")) + "</div>" : "";
      page.innerHTML = '<div class="rd-slugline">' + esc(sc.heading) + "</div>"
        + who + lines;
    }

    const tick = $("#rd-ticker", host);
    if (tick) {
      tick.innerHTML = this.said.slice(-4).map(o =>
        '<p class="rd-obs mono">' + esc(o) + "</p>").join("");
      if (this.phase === "found" && this.found) {
        const langs = (this.found.design_worlds || [])
          .map(w => w.name || w.title || "").filter(Boolean);
        const subj = (this.found.subjects || []).length;
        tick.insertAdjacentHTML("beforeend",
          '<p class="rd-found mono">' + langs.length + " DESIGN LANGUAGE(S)"
          + (langs.length ? " — " + esc(langs.slice(0, 4).join(" · ")).toUpperCase() : "")
          + " · " + subj + " SUBJECT(S)</p>"
          + '<p class="rd-done-row"><button class="ghost" data-f="rd-dismiss">Dismiss</button>'
          + '<button class="primary" data-f="rd-go">Review on Prod. Design</button></p>');
        const go = $("[data-f=rd-go]", host);
        if (go) go.onclick = () => { this.dismiss(); showView("wizard"); };
      }
      if (this.phase === "previewed") {
        tick.insertAdjacentHTML("beforeend",
          '<p class="rd-done-row"><button class="ghost" data-f="rd-dismiss">Close preview</button></p>');
      }
      if (this.phase === "failed") {
        tick.insertAdjacentHTML("beforeend",
          '<p class="rd-raw">' + esc(this.error || "no reason given") + "</p>"
          + '<p class="rd-done-row">'
          + (this.refused()
              ? '<button class="primary" data-f="rd-settings">Connect a working key</button>'
              : "")
          + '<button class="ghost" data-f="rd-dismiss">Dismiss</button></p>');
        const go = $("[data-f=rd-settings]", host);
        if (go) go.onclick = () => { this.dismiss(); showView("settings"); };
      }
      const x = $("[data-f=rd-dismiss]", host);
      if (x) x.onclick = () => this.dismiss();
    }
  },
};

async function startTheRead() {
  try {
    const have = await api("/api/wizard/analysis").catch(() => ({}));
    if (have && (have.design_worlds || have.subjects || have.analyzed_at)) return;
    const s = await api("/api/settings");
    const cap = s.capability?.narrative;
    if (!cap?.usable) return;
    // The read takes minutes and used to report itself with one toast at
    // each end. Between them the app looked idle over the most expensive
    // thing it does (user, 2026-08-20). theRead runs the local parse as
    // live feedback for the duration.
    const engine = s.narrative_provider || cap.engines?.[0] || "the model";
    await theRead.begin(engine);
    try {
      const a = await api("/api/wizard/analyze", { method: "POST", json: {} });
      theRead.finish(a);
      if (activeView === "wizard") renderWizard();
      updateBand();
    } catch (err) {
      theRead.fail(err.message);
      throw err;
    }
  } catch (err) {
    toast(`The read did not finish: ${err.message} — build the design plan on `
          + "Prod. Design when you are ready.", true);
  }
}

function bindScreenplayUpload(form, cap = null) {
  // Gate readable as state: the verb stays disabled, with the condition
  // stated, until a file is actually chosen — and, since the user's
  // 2026-08-18 ruling, until an AI model is connected. The read starts
  // the moment the draft lands and the read needs an engine, so taking
  // the file first would be accepting work the studio cannot begin.
  const input = $('input[type="file"]', form);
  const submit = $('button[type="submit"]', form);
  const noEngine = cap ? !cap.any_credential : false;
  if (noEngine) {
    input.disabled = true;
    form.insertAdjacentHTML("afterend",
      `<p class="up-gate mono">NO AI MODEL CONNECTED — THE SCREENPLAY IS READ
       THE MOMENT IT LANDS, AND THAT READ NEEDS AN ENGINE
       <button type="button" class="text-act" data-f="up-gate-go">Connect one ↗</button></p>`);
    form.parentElement.querySelector("[data-f=up-gate-go]").onclick =
      () => showView("settings");
  }
  const sync = () => {
    submit.disabled = noEngine || !input.files.length;
    submit.title = noEngine
      ? "Connect an AI model first — Settings → AI & engines"
      : input.files.length ? "" : "Choose a screenplay file first";
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
      startTheRead();
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
    `${langs} LANGUAGE${langs === 1 ? "" : "S"} · ${data.locations.length} `
    + `LOC${data.locations.length === 1 ? "" : "S"}`;

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
      ? `<button class="text-act loc-draft" data-loc="${esc(l.location)}">Create breakdown</button>`
      : PD_LOCK_TAG;
    const held = heldBySpec[l.sheet.spec_id];
    return `<span class="loc-sheet">
      <span class="badge ${l.sheet.locked ? "LOCKED" : "DRAFT"}">${l.sheet.locked ? "LOCKED" : esc(l.sheet.status)}</span>
      <button class="loc-open${held ? " held" : ""}" data-open="${esc(l.sheet.spec_id)}">${held ? `${held} held row${held > 1 ? "s" : ""}` : "Open breakdown"}</button>
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
              ${pdReady ? `<button class="text-act loc-draft" data-loc="${esc(s.heading)}">Create breakdown</button>` : PD_LOCK_TAG}
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
// Productions is a TAB of Settings now (user 2026-08-16), not a view of
// its own: both are "this install", and one of them was in the header
// while the other was a page. This fills the tab; renderSettings calls it.
async function renderProjectsView() {

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
            <button class="ghost" data-safety="${esc(p.slug)}" title="Download the safety copy taken automatically before this production's last import. There is one only if an import has happened; it is how you undo one.">Pre-import copy</button>
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
    // The safety copy taken before an import was written to the volume and
    // was unreachable — the endpoint's own docstring says so, because it
    // was added to fix exactly that and the UI half was never built
    // (adversarial review F9). Insurance you cannot collect is not
    // insurance. Simple download: it is one file that already exists, so
    // there is nothing to pack and nothing to stream.
    $$("#prod-cards [data-safety]").forEach(b => b.onclick = async () => {
      const slug = b.dataset.safety;
      b.disabled = true;
      try {
        const res = await fetch(
          `/api/projects/safety-zip?slug=${encodeURIComponent(slug)}`);
        if (res.status === 404) {
          toast("No safety copy — one is written automatically before each "
                + "import, and this production has not been imported into.");
          return;
        }
        if (!res.ok) throw new Error((await res.text()) || `failed (${res.status})`);
        const fname = /filename="([^"]+)"/.exec(
          res.headers.get("Content-Disposition") || "")?.[1] || "pre-import.zip";
        const url = URL.createObjectURL(await res.blob());
        const a = document.createElement("a");
        a.href = url; a.download = fname;
        document.body.append(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 5000);
        toast(`${fname} downloaded — the production as it was before its last import.`);
      } catch (err) { toast(err.message, true); }
      finally { b.disabled = false; }
    });

    $$("#prod-cards [data-backup]").forEach(b => b.onclick = async () => {
      const slug = b.dataset.backup;
      const card = b.closest(".prod-card");
      const busy = startBusy($("[data-busy]", card), "Packing the production…",
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
          busy.label("Downloading the backup…");
          busy.progress(total ? `${mbs(got)} OF ${mbs(total)}`.toUpperCase()
                              : `${mbs(got)}`.toUpperCase());
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
            + "library, breakdowns, boards and approval log with what the zip "
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

/* What the volume holds (user 2026-08-07, after a studio filled its disk
   and a paid render died mid-write). Two facts in two voices: the phase
   in prose, the measurements in Courier. --hold when it is getting tight,
   --bad when a render would already be refused; otherwise no colour at
   all, because a healthy disk is not news. */
async function renderStorage() {
  const host = $("#storage-body");
  if (!host) return;
  let s;
  try { s = await api("/api/storage"); }
  catch { host.innerHTML = '<p class="mini">storage could not be read</p>'; return; }
  if (!s.total) {
    host.innerHTML = '<p class="mini">this install’s volume cannot be measured</p>';
    $("#storage-cond").textContent = "";
    return;
  }
  const mb = n => n >= (1 << 30) ? `${(n / (1 << 30)).toFixed(1)} GB`
    : n >= (1 << 20) ? `${Math.round(n / (1 << 20))} MB`
    : `${Math.max(1, Math.round(n / (1 << 10)))} KB`;
  const pct = Math.min(100, Math.round((s.used / s.total) * 100));
  // A render is refused below this — the same number the server guards on.
  const tight = s.free < 350 * 1024 * 1024;
  const state = tight ? "bad" : s.low ? "hold" : "";
  $("#storage-cond").textContent = tight
    ? "A RENDER WOULD BE REFUSED — FREE SPACE FIRST"
    : s.low ? "GETTING TIGHT" : "";
  // R6 (canon pass 2026-08-10): the coverage meter is the project's only
  // meter — a capacity is a Courier number line whose colour carries its
  // state. The number a user would read aloud is the thing on screen.
  // DENSITY rule 5 (ruled 2026-08-18): a status word becomes a compound
  // fact where the reader's next question is obvious. Nobody reads
  // "14.2 / 40 GB" and stops there — they are asking how many more takes
  // fit. A 4K take is 20–40 MB; the headroom is stated at the pessimistic
  // end so the number is never a promise the disk cannot keep.
  const takes = Math.floor(s.free / (40 * 1024 * 1024));
  host.innerHTML = `
    <p class="stor-line mono ${state}">FREE ${mb(s.free)} OF ${mb(s.total)} · ${pct}% USED${
      takes > 0 ? ` · ROOM FOR ~${takes} MORE 4K TAKE${takes === 1 ? "" : "S"}`
        : " · NOT ENOUGH FOR ANOTHER 4K TAKE"}</p>
    <div class="stor-rows">${(s.breakdown || []).map(r => `
      <div class="stor-row"><span>${esc(r.kind)}</span>
        <span class="mono">${mb(r.bytes)}</span></div>`).join("")
      || '<p class="mini">nothing stored yet</p>'}</div>
    <p class="mini">Takes are never upscaled, so a 4K take is 20–40 MB and every
    one is kept until it is rejected and deleted. Reject a take, then Delete,
    to reclaim its space.</p>`;
}

/* The tutorial CMS (tutorial-admin.js) is fetched the first time its tab
   is opened and never on a customer's studio — the tab does not exist
   there. The runtime half (tutorial.js) ships to everyone. */
let _tutAdminLoad = null;
function openTutorialAdmin() {
  const host = $("#tut-admin");
  if (!host) return;
  const v = encodeURIComponent(window.SB_BOOT_VERSION || "dev");
  _tutAdminLoad ||= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = `/tutorial-admin.js?v=${v}`;
    s.onload = resolve;
    s.onerror = () => {
      _tutAdminLoad = null;
      reject(new Error("The tutorial editor could not be loaded."));
    };
    document.head.append(s);
  });
  _tutAdminLoad
    .then(() => window.TutorialAdmin.render(host))
    .catch(err => { host.innerHTML = `<p class="mini">${esc(err.message)}</p>`; });
}

async function renderSettings(openTab = "") {
  useTemplate("tpl-settings");
  renderStorage();
  renderProjectsView();

  // FTUE stays put (user 2026-08-16): Productions reads FIRST in the tab
  // strip because it is the widest thing on the page — which production
  // am I in — but a first visit still lands on AI & engines, because with
  // no key nothing else in the app can run. Order and default are two
  // different decisions and this is the one place they meet.
  const rememberedTab0 = openTab || uiGet("settingsTab", "");
  const rememberedTab = ["debug", "tutorials"].includes(rememberedTab0) && !_debugTools
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
    if (btn.dataset.sub === "tutorials") openTutorialAdmin();
  });
  if (rememberedTab === "tutorials") openTutorialAdmin();

  const settings = await api("/api/settings");
  _debugTools = !!settings.debug_tools;
  if (!_debugTools) {
    // Debug tools and the tutorial CMS exist only on the owner's installs
    // — the tabs and their subviews are removed outright, never merely
    // hidden. (The tutorial RUNTIME ships to everyone; only authoring is
    // gated.)
    for (const sub of ["debug", "tutorials"]) {
      $(`#settings-subnav button[data-sub="${sub}"]`)?.remove();
      $(`[data-subview="${sub}"]`)?.remove();
    }
  }

  // User-added engines render inside the §02 credential list (C2).
  const customs = settings.custom_engines || [];
  // C9 — one place the workbench can read an engine's stated limit from,
  // filled wherever settings are already fetched rather than by a second
  // request from the panel.
  for (const e of customs) ENGINE_PROMPT_LIMITS[`custom:${e.id}`] = e.prompt_limit || 0;

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
  // Server-declared (generate.capability, 2026-08-18). This was a fourth
  // copy of "does this install have a credential", and a copy of that
  // question is how a keyless studio showed a control panel here and a
  // setup form elsewhere.
  const anyCred = !!settings.capability?.any_credential;
  $("#settings-firstrun").classList.toggle("hidden", anyCred);
  $("#settings-steady").classList.toggle("hidden", !anyCred);
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
    /* A PASS never outlives the credential it tested (2026-08-26). The
       result is stored and persists; the key can stop being visible to
       this process without the file changing — the dev loop blanks stored
       keys unless `--keys` is passed, and does it by making the process
       unable to see them rather than by editing anything. So this row
       read SYNCED beside an engine holding no key, and every call failed.
       The user read the screen correctly and the screen was wrong. */
    if (e.last_test?.stale) return ["bad", `NO KEY HERE — LAST TEST ${stamp(e.last_test.at)}`];
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
      account: "https://openrouter.ai/settings/keys",
      facts: (orRow.identity ? `${esc(orRow.identity)} · ` : "")
        + "SCOPED KEY — REVOKE FROM THEIR DASHBOARD",
      state: cxState(orRow), actions: cxActs(orRow.status) },
    { key: "openai", tile: "OAI", icon: "openai", name: "OpenAI",
      connected: !!engAll.openai?.configured,
      account: "https://platform.openai.com/api-keys",
      facts: esc(settings.openai_api_key_hint || settings.openai_env_key_hint || ""),
      state: keyState("openai"), actions: keyActs("openai") },
    { key: "gemini", tile: "GGL", icon: "gemini-color", name: "Google Gemini",
      connected: !!engAll.gemini?.configured,
      account: "https://aistudio.google.com/apikey",
      facts: esc(settings.gemini_api_key_hint || ""),
      state: keyState("gemini"), actions: keyActs("gemini") },
    { key: "anthropic", tile: "ANT", icon: "claude-color", name: "Anthropic Claude",
      connected: !!settings.anthropic_api_key_set,
      account: "https://console.anthropic.com/settings/keys",
      facts: esc(settings.anthropic_api_key_hint || ""),
      state: keyState("anthropic"), actions: keyActs("anthropic") },
    { key: "fal", tile: "FAL", name: "fal.ai",
      connected: falRow.status !== "NOT_CONNECTED",
      account: "https://fal.ai/dashboard/keys",
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
      <span class="cred-acts">${r.account ? `<a class="text-act" href="${esc(r.account)}" target="_blank" rel="noopener" title="Open this provider's account — manage the key, usage and billing">Account ↗</a>` : ""}${(r.actions || []).map(([l, a]) =>
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
        <p class="mini">${esc(e.model)} · ${esc(e.base_url)} · key ${esc(e.key_hint)}${
          e.prompt_limit ? ` · PROMPTS UP TO ${e.prompt_limit.toLocaleString()} CHARACTERS`
                         : " · NO STATED PROMPT LIMIT"}${
          t ? ` · LAST TEST ${t.ok ? "PASS" : "FAIL"} ${esc(stamp(t.at))}` : ""}</p>
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
    /* Preview the read (owner tools only). The parse half needs no engine
       — it is the same GET /api/screenplay/digest the real read walks — so
       the animation and the copy can be checked without spending anything.
       It stops where the model would take over rather than faking that
       phase, because a preview that invented the model's half would be a
       lie told by the one surface built to avoid telling them. */
    const rp = $("#dbg-read-preview");
    if (rp) rp.onclick = async () => {
      const st = $("#dbg-read-state");
      const d = await api("/api/screenplay/digest").catch(() => null);
      if (!d || !d.available || !d.scenes.length) {
        st.textContent = "NO SCREENPLAY PARSED — UPLOAD A DRAFT FIRST";
        return;
      }
      st.textContent = "";
      showView("screenplay");
      setTimeout(() => theRead.begin("preview — no model called", true), 400);
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
    // Publishing is what makes an edit real for anyone but this install
    // (user 2026-08-23). The local file is a scratchpad — never in
    // backups, wiped by a volume replacement — so a rewrite that is not
    // published reaches nobody, and the button says which of the two
    // outcomes happened rather than reporting success either way.
    $("#dbg-text-publish").onclick = async () => {
      try {
        const r = await api("/api/debug/text-overrides/publish", { method: "POST" });
        if (r.published) {
          toast(`${r.count} edit(s) written to source. Commit `
                + "app/content/ui_text.json and deploy — then every studio has them.");
        } else {
          // Not a failure: it is the honest answer on a hosted studio, and
          // the payload is what someone commits by hand.
          await promptOverlay(
            "Publish needs a commit — this install cannot write its own source",
            JSON.stringify(r.overrides, null, 2),
            "SAVE AS app/content/ui_text.json, COMMIT, DEPLOY");
        }
      } catch (err) { toast(err.message, true); }
    };

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


/* ----------------------------------------------------------- setup wizard */


/* The swatch viewer and its helpers live at MODULE scope (2026-08-08):
   the Reference page consolidates the same swatches into the same ramps,
   and one viewer serving both pages is the standing contract. The two
   page-specific facts ride opts: `refresh` (which view to re-render) and
   `onRescan` (absent where no engine picker exists — the Rescan act only
   renders where its precondition is met). */
    const swBlock = (hex, pair) => pair
      ? `<span class="sw-pair"><i style="background:${esc(hex)}"></i><i style="background:${esc(pair)}"></i></span>`
      : `<span class="sw-tile" style="background:${esc(hex)}"></span>`;

    // Repaint every element that shows this reference — a colour appears
    // in the strip ramp and, while it is open, in the viewer too.
    const paintSwatch = (refId, hex, pair) => {
      $$(`[data-ref="${CSS.escape(refId)}"]`).forEach(el => {
        if (el.tagName === "I" && el.parentElement.classList.contains("sw-ramp")) {
          el.setAttribute("style", `flex:${el.style.flex || 1};`
            + bandStyle({ hex, pair_hex: pair }));
        }
      });
      $$(`.sv-row[data-ref="${CSS.escape(refId)}"]`).forEach(row => {
        $(".sv-chip", row).outerHTML =
          `<span class="sv-chip">${swBlock(hex, pair)}</span>`;
        $(".sv-hex", row).textContent = hex + (pair ? " · " + pair : "");
        row.dataset.hex = hex;
        row.dataset.pair = pair || "";
      });
    };

    // D8 still holds: a verdict is a per-reference status record with a
    // reason. The group bar and the viewer footer run those records in
    // sequence — they are not a new kind of verdict.
    const verdictFor = (refId, status) =>
      api(`/api/references/${refId}/status`, { method: "POST",
        json: { status, reason: status === "REJECTED"
          ? "swatch proposal rejected in review" : "" } });

    /* ONE statement of what a swatch IS — a name, a colour, and an
       optional value-key pair — shared by adding one and editing one.
       They were two forms: this modal, and an inline row in the palette
       column that could not state a pair at all and left a filled colour
       chip on screen looking like a swatch nobody had added. */
    const swatchFields = ({ name = "", hex = "", pair = "", editing } = {}) => [
      // A colour whose name no longer describes it is worse than an
      // unnamed one (user 2026-08-22), and a repaint is exactly when
      // the name stops being true.
      { name: "name", label: "Name", value: name,
        placeholder: "e.g. oxide rust", maxlength: 48,
        hint: editing ? "Leave it as it is to keep the current name."
                      : "Optional — the hex names it otherwise." },
      { name: "hex", label: "Color", value: hex, placeholder: "#8A4B2E",
        color: true },
      { name: "pair", label: "Value-key pair", value: pair,
        placeholder: "leave empty for one flat color", color: true,
        hint: "The same hue at the opposite value key — renders as two halves." },
    ];

    const recolorSwatch = async (refId, hex, pair, swName = "",
                                refresh = () => {}) => {
      const vals = await modal({
        title: "Edit this swatch",
        body: "Edits the swatch where it stands — it keeps its id, its design "
          + "language and its place in this review.",
        fields: swatchFields({ name: swName, hex, pair: pair || "",
                               editing: true }),
        confirmLabel: "Save swatch",   // not "Repaint" — it renames too
      });
      if (vals === null) return null;
      const rec = await api(`/api/references/${refId}/swatch`,
        { method: "POST", json: { hex: vals.hex, pair_hex: vals.pair,
                                  name: (vals.name || "").trim() } });
      paintSwatch(refId, rec.hex, rec.pair_hex);
      toast(`${refId} is now ${(vals.name || "").trim() || rec.hex} ${rec.hex}.`);
      refresh();
      return rec;
    };

    // ---- the swatch viewer -------------------------------------------
    // Opened from a ramp; holds every per-colour fact and verb. `group` is
    // live — the viewer mutates it and the caller re-renders from it, so
    // the strip and the viewer never disagree about what is left.
    // The viewer takes a LIST of groups: one for a ramp click, all of them
    // for Review all. `approved` swaps the verbs — Approve is meaningless
    // on a swatch that already is, and Reject there means demote out of
    // canon (which is NOT the row's ×: that deletes the reference).
    const openSwatchViewer = (groups, opts = {}) => {
      const { focusRef = null, onChange = () => {}, approved = false,
              refresh = () => {}, onRescan = null } = opts;
      const many = groups.length > 1;
      const count = () => groups.reduce((n, g) => n + g.swatches.length, 0);
      const groupOf = refId => groups.find(g =>
        g.swatches.some(sw => sw.ref_id === refId));

      const rows = g => rampOrder(g.swatches).map(sw => `
        <div class="sv-row${sw.hero ? " is-hero" : ""}" data-ref="${esc(sw.ref_id)}"
             data-hex="${esc(sw.hex)}" data-pair="${esc(sw.pair_hex || "")}"
             data-name="${esc(sw.name || "")}">
          <span class="sv-chip">${swBlock(sw.hex, sw.pair_hex)}</span>
          <span class="sv-id">
            <span class="sv-name">${esc(sw.name)}${
              sw.hero ? '<span class="sw-hero">HERO</span>' : ""}</span>
            <span class="sv-hex mono">${esc(sw.hex)}${
              sw.pair_hex ? " · " + esc(sw.pair_hex) : ""}</span>
            ${sw.cite ? `<span class="sv-cite">&ldquo;${esc(sw.cite)}&rdquo;</span>` : ""}
          </span>
          <span class="sv-acts">
            <button class="text-act" data-f="rc">Edit</button>
            <button class="text-act" data-f="rj"${approved
              ? ' title="Demote out of canon — a status record with a reason, not a deletion"'
              : ' title="Drop this colour from the palette — the rest approve together"'
              }>Reject</button>
          </span>
        </div>`).join("");

      const section = g => {
        const hero = g.swatches.find(sw => sw.hero);
        return `<div class="sv-group">
          ${many ? `<p class="sw-ramp-label sv-grouphead">
            <span class="lang">${esc(g.language.toUpperCase())}</span>
            <span class="n">${g.swatches.length}</span>
            <span class="hero${hero ? "" : " open"}">${
              hero ? `HERO ${esc(hero.hex)}` : "OPEN"}</span></p>` : ""}
          <div class="sv-rampwrap">
            <div class="sw-ramp sv-ramp">${rampOrder(g.swatches).map(sw =>
              `<i data-ref="${esc(sw.ref_id)}" class="${sw.hero ? "is-hero" : ""}"
                  style="flex:${sw.hero ? 2 : 1};${bandStyle(sw)}"
                  title="Make this the hero"></i>`).join("")}</div>
            ${many ? "" : '<p class="sv-note mono">HERO — THE COLOR SPLASHED THROUGH THIS FACTION\u2019S SETS, COSTUMES AND PROPS</p>'}
          </div>
          <div class="sv-rows">${rows(g)}</div>
        </div>`;
      };

      const draw = () => {
        const n = count();
        const state = approved ? "APPROVED" : "PROPOSED, NOT CANON";
        return `<div class="sv${many ? " sv-many" : ""}">
          <div class="sv-head">
            <span class="sv-title">${esc(many
              ? `${groups.length} design languages` : groups[0].language)}</span>
            <span class="sv-sub mono">${n} SWATCH${n === 1 ? "" : "ES"} · ${state}</span>
            ${many || !onRescan ? "" : `<button class="text-act sv-rescan" data-f="rescan"
              title="Ask for the colors this design language is still missing">Rescan this language</button>`}
            <button class="sv-x" data-f="x" title="Close">&times;</button>
          </div>
          ${many ? '<p class="sv-note mono sv-note-top">HERO — THE COLOR SPLASHED THROUGH THAT FACTION\u2019S SETS, COSTUMES AND PROPS</p>' : ""}
          <div class="sv-body">${groups.map(section).join("")}</div>
          <div class="sv-foot">
            ${approved ? "" : `<button class="primary" data-f="ap-all">${
              many ? `Approve all ${groups.length} palettes` : "Approve palette"}</button>
            <button class="text-act" data-f="rj-all">${
              many ? `Reject all ${n}` : "Reject the group"}</button>`}
            <span class="sv-footnote mono">A LANGUAGE'S SWATCHES APPROVE AS ONE PALETTE</span>
            ${approved && !many ? `<button class="text-act sv-remove" data-f="rm-group"
              title="Delete these references for good — the ramp row no longer carries this act">Remove group</button>` : ""}
          </div>
        </div>`;
      };

      return modal({
        custom: draw(),
        mount: (ov, done) => {
          const wire = () => {
            const drop = refId => {
              const g = groupOf(refId);
              if (g) g.swatches = g.swatches.filter(s => s.ref_id !== refId);
              for (let k = groups.length - 1; k >= 0; k--) {
                if (!groups[k].swatches.length) groups.splice(k, 1);
              }
              onChange();
              if (!count()) return done(null);
              // A rejected hero leaves the group OPEN — the user chooses a
              // hero, the app never guesses one after the fact.
              $(".sv", ov).outerHTML = draw();
              wire();
            };
            $("[data-f=x]", ov).onclick = () => done(null);
            $$(".sv-ramp i", ov).forEach(b => b.onclick = async () => {
              const refId = b.dataset.ref;
              const g = groupOf(refId);
              if (!g || g.swatches.find(s => s.ref_id === refId)?.hero) return;
              try {
                await api(`/api/references/${refId}/hero`, { method: "POST" });
              } catch (err) { return toast(err.message, true); }
              // Single-valued within its OWN language only — the server
              // clears the rest of that language, never another's.
              g.swatches.forEach(s => { s.hero = s.ref_id === refId; });
              onChange();
              $(".sv", ov).outerHTML = draw();
              wire();
              refresh();
            });
            $$(".sv-row", ov).forEach(row => {
              const refId = row.dataset.ref;
              $("[data-f=rc]", row).onclick = async () => {
                try {
                  const rec = await recolorSwatch(refId, row.dataset.hex,
                    row.dataset.pair, row.dataset.name, refresh);
                  if (!rec) return;
                  const sw = groupOf(refId)?.swatches.find(s => s.ref_id === refId);
                  if (sw) {
                    sw.hex = rec.hex; sw.pair_hex = rec.pair_hex;
                    if (rec.name) sw.name = rec.name;
                  }
                  onChange();
                } catch (err) { toast(err.message, true); }
              };
              $("[data-f=rj]", row).onclick = async () => {
                try { await verdictFor(refId, "REJECTED"); drop(refId); }
                catch (err) { toast(err.message, true); }
              };
            });
            const sweepAll = async status => {
              for (const g of [...groups]) {
                for (const sw of [...g.swatches]) {
                  try { await verdictFor(sw.ref_id, status); }
                  catch (err) { toast(err.message, true); break; }
                  g.swatches = g.swatches.filter(s => s.ref_id !== sw.ref_id);
                }
              }
              if (status === "APPROVED") refresh();
              onChange();
              done(null);
            };
            // R4 — a destructive act is only offered where its object can
            // be read in full. The ramp row lost its ×; this is the only
            // place the whole group is visible at once.
            const rmBtn = $("[data-f=rm-group]", ov);
            if (rmBtn) rmBtn.onclick = async () => {
              const ids = groups[0].swatches.map(sw => sw.ref_id);
              if (!(await askConfirm(`Remove ${ids.length} reference${
                ids.length === 1 ? "" : "s"}?`,
                `Every swatch in ${groups[0].language} is deleted from the reference `
                + "library and from future generations. Each removal is logged. "
                + "This cannot be undone.", `Remove ${ids.length}`, true))) return;
              try {
                for (const id of ids) await api(`/api/references/${id}`, { method: "DELETE" });
                toast(`${ids.length} references removed.`);
              } catch (err) { return toast(err.message, true); }
              onChange();
              done(null);
            };
            const rescanBtn = $("[data-f=rescan]", ov);
            if (rescanBtn) rescanBtn.onclick = async () => {
              const lang = groups[0].language;
              let r;
              try {
                r = await onRescan(lang, $(".sv-foot", ov));
              } catch (err) { return toast(err.message, true); }
              if (!r) return;
              const found = r.groups.reduce((t, g) => t + g.swatches.length, 0);
              toast(found
                ? `${found} more proposed for ${lang} — review them in the strip.`
                : "Nothing more found.");
              onChange();
              done(null);
            };
            const apAll = $("[data-f=ap-all]", ov);
            if (apAll) apAll.onclick = () => sweepAll("APPROVED");
            const rjAll = $("[data-f=rj-all]", ov);
            if (rjAll) rjAll.onclick = () => sweepAll("REJECTED");
          };
          wire();
          if (focusRef) {
            const row = $(`.sv-row[data-ref="${CSS.escape(focusRef)}"]`, ov);
            if (row) {
              row.classList.add("is-focus");
              row.scrollIntoView({ block: "nearest" });
            }
          }
        },
      });
    };


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
    // The RECOVERY path: this browser holds a read the server does not. If
    // it fails silently the analysis stays trapped in one tab's
    // localStorage — invisible to every other device, and gone with the
    // cache. Same defect as the interview save it sits beside (2026-08-23).
    api("/api/wizard/analysis", { method: "PUT", json: localAnalysis })
      .catch(err => toast(
        `This browser holds a screenplay read the studio does not, and it `
        + `could not be uploaded — ${err.message}. Do not clear site data.`,
        true));
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
  // A swatch is an ordinary COLOR_PALETTE reference: pure solid pixels
  // (engines study these images — name/hex live in the notes, never the
  // pixels). Manual add is the user's act and lands approved; generated
  // proposals are grounded in the saved Bible, grouped by its Design
  // Languages, and stay client-side until each approval creates the
  // reference.
  let syncSwatchGen = () => {};
  // Same reason: the bible's one act renders the strip when its colour
  // pass returns, and that call site is outside this block.
  let renderSwatchStrip = () => {};
  {
    const col = $('.wiz-col[data-role="COLOR_PALETTE"]');
    $("[data-f=sw-add]", col).onclick = async () => {
      const vals = await modal({
        title: "Add a palette swatch",
        body: "Your own colour, stated by hand. It lands approved — a "
          + "swatch you chose is not a proposal to review.",
        fields: swatchFields(),
        confirmLabel: "Add swatch",
      });
      if (vals === null) return;
      const hex = (vals.hex || "").trim();
      if (!HEXOK.test(hex)) return toast("A swatch needs a full hex — like #8A4B2E.", true);
      const name = (vals.name || "").trim();
      try {
        const ref = await api("/api/references/swatch",
          { method: "POST", json: { hex, pair_hex: (vals.pair || "").trim(),
                                    name: name || undefined, approve: true } });
        toast(`${ref.id} — ${name ? name.toUpperCase() + " " : ""}${hex.toUpperCase()} added as an approved palette swatch.`);
        refreshRefs();
      } catch (err) { toast(err.message, true); }
    };

    const genHost = $("#swatch-gen");
    const strip = $("#swatch-strip");

    /* Where the absence is FELT (user, 2026-08-22: "I uploaded my
       screenplay and went to the Production Design panel. No color
       swatches").

       A generated palette does not come from the screenplay. The scene
       scan finds design LANGUAGES; colour is proposed later by a model
       reading the SAVED Bible, one citation per swatch, which is the
       whole reason a swatch can be trusted. Standing in this column with
       nothing in it, none of that was discoverable — step 4's generate
       control simply does not render yet, and its own gate two lines up
       talks about saving a draft, not about colour.

       One line, here, only while the column is empty. It is not the
       verbosity D1 cut: that ruling stopped the same fact being stated
       twice on one screen, and this fact is stated nowhere else. */
    /* The palette column is gated on the Bible (user, 2026-08-22: "it's
       not disabled, totally unclear, I can add swatches — disable this
       section with an obvious callout on why").

       The faint 9.5px line this replaces was a stated gate in principle
       and invisible in practice, sitting under a control that still
       worked. A gate you can act through is not a gate, so the adder is
       genuinely disabled — inputs and verb both — and the reason is said
       at a size that competes with the control it governs.

       The condition is the Bible and nothing else. A first attempt also
       unlocked once the column held any colour, which was both wrong and
       broken: wrong because "you may add more by hand once you have added
       one by hand" is not a rule, and broken because a swatch thumb is a
       coloured block, not an <img>, so the check never saw one anyway. */
    const paletteOrigin = async () => {
      const add = $(".swatch-add", col);
      let gate = $("[data-f=pal-gate]", col);
      const b = await api("/api/style-bible").catch(() => ({ text: "" }));
      const locked = !b.text.trim();

      /* Everything in the column that STATES a palette, locked together:
         the hand-added colour, the words, and the reference images (user,
         2026-08-22, in three passes — each live control left behind read
         as the gate not meaning it). What stays reachable is what only
         reads: the existing thumbs and their viewer. */
      add.classList.toggle("is-locked", locked);
      $$("input, button", add).forEach(el => { el.disabled = locked; });

      const words = $("[data-f=words]", col);
      if (words) {
        words.disabled = locked;
        words.closest(".wiz-words")?.classList.toggle("is-locked", locked);
      }

      const addImgs = $("[data-f=addbtn]", col);
      if (addImgs) {
        addImgs.disabled = locked;
        addImgs.classList.toggle("is-locked", locked);
      }
      const files = $("[data-f=files]", col);
      if (files) files.disabled = locked;

      if (!locked) { if (gate) gate.remove(); return; }
      if (!gate) {
        gate = document.createElement("div");
        gate.className = "pal-gate";
        gate.dataset.f = "pal-gate";
        // Above the first thing it disables, not in the middle of them —
        // a gate under half its own controls explains them too late.
        col.insertBefore(gate, addImgs || add);
      }
      // Copy and shape are the user's, verbatim (2026-08-22). No verb:
      // the step it names is on the same page, and a button that scrolls
      // is not worth the weight of a primary.
      gate.innerHTML = `
        <span class="k">LOCKED — NO ART DIRECTION BIBLE</span>
        <p>Color swatches reference the Art Direction Bible once created.
        <b>Step 4</b></p>`;
    };

    // The colour block itself, without the card chrome — rebuilt in place
    // by a recolour so the edit does not cost a re-render of the strip.
    // PALETTE_GROUPS_PLAN (2026-08-06): a design language renders as ONE
    // contiguous ramp — the group is the swatch, the colour is a detail.
    // Every per-colour fact and verb lives in the viewer, one click away.
    const rampLabel = (g, gi = -1) => {
      const hero = g.swatches.find(s => s.hero);
      // Edit and Approve live ON the row (user, 2026-08-23): the ramp
      // states every colour right here, so a group verdict is a judgment
      // on something fully visible — the acts were a click further away
      // than the thing they act on.
      return `<p class="sw-ramp-label">
        <span class="lang">${esc(g.language.toUpperCase())}</span>
        <span class="n">${g.swatches.length}</span>
        <span class="hero${hero ? "" : " open"}">${
          hero ? `HERO ${esc(hero.hex)}` : "OPEN"}</span>${gi < 0 ? "" : `
        <span class="sw-row-acts">
          <button class="text-act" data-f="g-edit" data-gi="${gi}">Edit</button>
          <button class="text-act ok-act" data-f="g-ap" data-gi="${gi}">Approve</button>
        </span>`}</p>`;
    };

    // Which languages the user has actually looked at. Outside the render
    // so a re-flow does not forget.
    const seen = new Set();
    const unopened = r => r.groups.filter(g => !seen.has(g.language)).length;

    // One place that asks for swatches, however the ask is aimed (user
    // 2026-08-07): the whole Bible, one design language, or a deep pass.
    // The server names what the palette already holds and already refused,
    // so a rescan proposes what is MISSING.
    const runSwatchScan = async (host, opts = {}) => {
      const { languages = null, deep = false, label = "Reading the Bible…" } = opts;
      const ask = await modal({
        title: languages ? `Rescan ${languages.join(", ")}`
          : deep ? "Deep scan the Bible" : "Generate palette swatches",
        body: languages
          ? "Proposes colors this design language is still missing. What the "
            + "palette already holds — and anything already rejected — is named "
            + "to the engine, so it will not offer them again."
          : deep
          ? "A second, wider read: materials and finishes, uniforms and insignia, "
            + "signage, practical light sources, corrosion — the colors the Bible "
            + "names in passing. Existing swatches are excluded."
          : "Reads the saved Bible and proposes colors grouped by design language.",
        // R3 — the brief stays FREE TEXT: a chip list cannot express "no
        // Onyx Unit black, and no reds" — the negation and the proper noun
        // are the whole value. Recall, not constraint.
        fields: [{ name: "note", label: "What is missing?", textarea: true,
                   placeholder: "optional — e.g. no Onyx Unit black, and no reds anywhere",
                   hint: "Rides this pass as the brief; still grounded in the Bible.",
                   recall: uiGet("swatchBriefs", []) }],
        confirmLabel: languages ? "Rescan" : deep ? "Deep scan" : "Generate",
      });
      if (ask === null) return null;
      if (ask.note.trim()) {
        const prior = uiGet("swatchBriefs", []).filter(x => x !== ask.note.trim());
        uiSet("swatchBriefs", [ask.note.trim(), ...prior].slice(0, 3));
      }
      const busy = startBusy(host, label,
        "Proposing only colors it can ground in your saved Bible.");
      try {
        return await api("/api/wizard/swatches", { method: "POST",
          json: { provider: $("#wiz-provider").value, note: ask.note, deep,
                  ...(languages ? { languages } : {}) } });
      } finally { busy.done(); }
    };

    renderSwatchStrip = r => {
      const total = r.groups.reduce((n, g) => n + g.swatches.length, 0);
      if (!total) { strip.innerHTML = ""; return; }
      const headTxt = n =>
        `${n} PROPOSED${r.model ? ` BY ${(r.model || "").toUpperCase()}` : ""} — NOT CANON UNTIL APPROVED`;
      /* What the set repeats, measured (2026-08-22). The user's first
         real run returned four ramps built from one six-slot recipe — 23
         of 27 colours had a near-twin in another design language — and
         every swatch was individually defensible, so nothing on screen
         said the set as a whole was one palette relabelled. */
      const bad = r.collisions || [];
      strip.innerHTML = `
        <p class="prop-head">${esc(headTxt(total))}</p>
        ${bad.length ? `<div class="sw-collide" data-f="collide">
          <button type="button" class="sw-collide-x" data-f="collide-x"
            title="Dismiss — the proposals are unchanged">&times;</button>
          ${bad.map(c => `<p class="mono"><b>${esc(c.kind)}</b> ${esc(c.text)}</p>`).join("")
          }<p class="mini mono">REGENERATE FOR A DIFFERENT READ, OR APPROVE WHAT
           WORKS AND RESCAN THE LANGUAGE THAT DOES NOT</p></div>` : ""}
        ${r.groups.map((g, i) => `
          <div class="sw-ramp" data-lang="${esc(g.language)}" data-gi="${i}">${
            rampOrder(g.swatches).map(band).join("")}</div>
          ${rampLabel(g, i)}`).join("")}
        <div class="sw-bar">
          <button class="ghost" data-f="review">Review all ${total}</button>
          <button class="ghost" data-f="ap-all"${unopened(r) ? " disabled" : ""}>Approve all ${total}</button>
          <button class="text-act" data-f="discard">Discard the rest</button>
          ${unopened(r) ? `<span class="sw-bar-note mono">${unopened(r)} OF ${
            r.groups.length} LANGUAGE${r.groups.length === 1 ? "" : "S"} UNOPENED</span>` : ""}
        </div>`;
      /* Dismissible (user, 2026-08-22). It is a REPORT, not a blocker —
         the proposals below are untouched and still approvable — and a
         verdict you have read and decided about must be closable, or it
         is just noise sitting over the work it is about. */
      const cx = $("[data-f=collide-x]", strip);
      if (cx) cx.onclick = () => $("[data-f=collide]", strip)?.remove();


      const reflow = () => {
        r.groups = r.groups.filter(g => g.swatches.length);
        renderSwatchStrip(r);
        paletteOrigin();
      };

      $$(".sw-ramp", strip).forEach(ramp => {
        const g = r.groups[Number(ramp.dataset.gi)];
        ramp.onclick = e => {
          const hit = e.target.closest("i");
          $$(".sw-ramp", strip).forEach(x => x.classList.remove("is-open"));
          ramp.classList.add("is-open");
          seen.add(g.language);
          openSwatchViewer([g], { focusRef: hit?.dataset.ref, onChange: reflow,
              refresh: refreshRefs,
              onRescan: (lang, host) => runSwatchScan(host,
                { languages: [lang], label: `Rescanning ${lang}…` }) })
            .then(() => { ramp.classList.remove("is-open"); reflow(); });
        };
      });

      const sweep = async status => {
        for (const g of r.groups) {
          for (const sw of [...g.swatches]) {
            try { await verdictFor(sw.ref_id, status); }
            catch (err) { toast(err.message, true); return reflow(); }
            g.swatches = g.swatches.filter(s => s.ref_id !== sw.ref_id);
          }
        }
        if (status === "APPROVED") refreshRefs();
        reflow();
      };
      // R5 — a bulk verdict is WITHHELD until everything it judges has
      // been seen: Approve all is disabled while any language is unopened
      // and the condition line is its explanation. Do not warn about a
      // judgment you are willing to permit anyway. Discard the rest is not
      // withheld — rejecting unread proposals is legitimate, and every one
      // is logged.
      $("[data-f=review]", strip).onclick = () => {
        r.groups.forEach(g => seen.add(g.language));
        openSwatchViewer(r.groups,
          { onChange: reflow, refresh: refreshRefs }).then(reflow);
      };
      $("[data-f=ap-all]", strip).onclick = () => sweep("APPROVED");
      $("[data-f=discard]", strip).onclick = () => sweep("REJECTED");
      // The row's own acts. Edit is the same door the ramp click opens;
      // Approve files the whole language — its colours are all on the row,
      // so this is not a judgment on anything unseen.
      $$("[data-f=g-edit]", strip).forEach(b => b.onclick = () => {
        const g = r.groups[Number(b.dataset.gi)];
        seen.add(g.language);
        openSwatchViewer([g], { onChange: reflow, refresh: refreshRefs,
            onRescan: (lang, host) => runSwatchScan(host,
              { languages: [lang], label: `Rescanning ${lang}…` }) })
          .then(reflow);
      });
      $$("[data-f=g-ap]", strip).forEach(b => b.onclick = async () => {
        const g = r.groups[Number(b.dataset.gi)];
        for (const sw of [...g.swatches]) {
          try { await verdictFor(sw.ref_id, "APPROVED"); }
          catch (err) { toast(err.message, true); return reflow(); }
          g.swatches = g.swatches.filter(x => x.ref_id !== sw.ref_id);
        }
        toast(`${g.language} approved as one palette.`);
        refreshRefs();
        reflow();
      });
    };

    // Pending proposals from an earlier run survive reload — rebuild the
    // strip from the persisted PROVISIONAL refs.
    const restoreStrip = async () => {
      const pend = (await api("/api/references").catch(() => []))
        .filter(x => x.source === "swatch-proposal" && x.status === "PROVISIONAL");
      if (!pend.length) return;
      const groups = {};
      pend.forEach(x => {
        const sw = swatchNotes(x.notes);
        (groups[sw.language || "PALETTE"] ||= []).push({
          ...sw, ref_id: x.id, name: sw.name || sw.hex || x.id,
          hex: sw.hex || "#000000" });
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
      /* Deliberately silent HERE (SWATCH_GENERATE_RULING, D1): this
         control sits two lines under step 4's own save gate, and saying
         it twice on one screen is the verbosity that ruling cut. The
         explanation a user actually needs belongs where the absence is
         FELT — step 1's Color Palette column — not here. */
      if (!engReady || !bible.text.trim()) { genHost.innerHTML = ""; return; }
      genHost.innerHTML = `
        <button class="ghost" data-f="sw-go">Generate palette swatches</button>
        <button class="text-act" data-f="sw-deep"
          title="A second, wider read for the colors the Bible only mentions in passing — existing swatches excluded">Deep scan</button>
        <span class="swatch-note" data-f="sw-result">FROM THE SAVED BIBLE · LANDS IN STEP 1 / COLOR PALETTE</span>
        <div data-f="sw-busy"></div>`;
      const go = $("[data-f=sw-go]", genHost);
      const runGen = async deep => {
        go.disabled = true;
        try {
          const r = await runSwatchScan($("[data-f=sw-busy]", genHost),
            { deep, label: deep ? "Reading the Bible again, deeper…" : "Reading the Bible…" });
          if (!r) return;
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
        go.disabled = false;
      };
      go.onclick = () => runGen(false);
      $("[data-f=sw-deep]", genHost).onclick = () => runGen(true);
    };
    await syncSwatchGen();
    await paletteOrigin();
  }

  // D2 (PRODUCTION_DESIGN_V3) — the six-step rail: numbered chips in the
  // header strip; done numbers go --ok (same truth as the step badges),
  // the current chip is bordered; clicking scrolls with the band offset.
  // Anchors lead (user 2026-08-16, dissolving the interview): the
  // director states the look before the machine reads anything, and the
  // anchor cards ARE that statement now — a picture, words, or both. The
  // separate interview asked the same four questions a second time.
  const RAIL = [[1, "Anchors"], [2, "Design Plan"], [3, "Cast"],
                [4, "Bible"], [5, "Model Test"]];
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

  // ---- Step 6: the model test (after the production design is set) ----
  // Every engine renders the same screenplay location; suggestions come from
  // the Step 2 analysis's recurring locations.
  // First user test, 2026-08-23: "if this is going to be a drop down like
  // give me all my locations because you have the screenplay." It WAS a
  // list — a `datalist`, which shows nothing until you type into it, so a
  // user whose screenplay the app had just read saw an empty box and no
  // sign that his own locations were behind it. A datalist is a
  // convenience for a field you already know how to fill; this is a field
  // whose whole value is that the app knows the answers.
  const locInput = $("#wiz-sample-loc");
  const locPick = $("#wiz-sample-pick");
  const sampleLocs = wizACache()?.key_locations || [];
  // A sentinel no location can collide with. NOT a control byte:
  // the repo forbids C0 characters in source, and a NUL in a value
  // attribute is unreadable in a diff and in a DOM inspector.
  const OTHER = "__type_your_own__";
  const saved = localStorage.getItem("wizardSampleLoc") || "";
  locPick.innerHTML =
    (sampleLocs.length
      ? sampleLocs.map(l => `<option value="${esc(l)}">${esc(l)}</option>`).join("")
      : `<option value="">build the design plan in Step 2 to list your locations</option>`)
    + `<option value="${OTHER}">Somewhere else — type it…</option>`;
  const useOther = on => {
    locInput.classList.toggle("hidden", !on);
    if (on) locInput.focus();
  };
  if (saved && sampleLocs.includes(saved)) {
    locPick.value = saved;
  } else if (saved) {
    locPick.value = OTHER; locInput.value = saved; useOther(true);
  } else {
    locPick.value = sampleLocs[0] || "";
  }
  const remember = () => localStorage.setItem("wizardSampleLoc", sampleSubject());
  locPick.onchange = () => { useOther(locPick.value === OTHER); remember(); };
  locInput.oninput = remember;
  const sampleSubject = () =>
    (locPick.value === OTHER ? locInput.value : locPick.value).trim();

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
        ${/* C6 — a probe renders TWICE and both are shown. Run-to-run
              variance is large enough that one image proves nothing, and
              this card exists to be compared: a single take invites a
              conclusion the sample cannot support. Twenty renders were
              read as evidence about a cinematography grammar over two
              days without anyone ever establishing what two identical
              runs look like. Samples made before this rule have one
              image and say so. */
          smp.has_image
          ? `<div class="wiz-pair">
               <img class="wiz-sample" src="/api/wizard/samples/${esc(smp.provider)}/image?t=${Date.now()}" alt="${esc(smp.provider)} sample, first run">
               ${smp.has_image_b
                 ? `<img class="wiz-sample" src="/api/wizard/samples/${esc(smp.provider)}/image?run=b&t=${Date.now()}" alt="${esc(smp.provider)} sample, second run">`
                 : ""}
             </div>
             <p class="mini wiz-pair-note">${smp.has_image_b
               ? "Two runs of the same prompt. What differs between them is this engine's variance, not a decision it made."
               : "One run — the second did not complete, so nothing here shows this engine's variance."}</p>`
          : '<p class="mini">no sample yet</p>'}
        <div class="row" style="margin-top:auto">
          ${smp.has_image && !isPref ? `<button class="primary" data-f="pick">Make default</button>` : ""}
          <button class="ghost" data-f="regen" title="Render this engine's sample twice from the same prompt — one take cannot show run-to-run variance, and this card exists to be compared">${smp.has_image ? "Regenerate" : "Generate"}</button>
        </div>`;
      // Both runs open in one lightbox, in order, so the comparison
      // survives the click that magnifies it.
      const imgs = $$("img.wiz-sample", col);
      const shots = imgs.map((el, i) => ({
        src: el.src,
        caption: `${smp.label} — ${smp.subject || "style sample"} · RUN ${i + 1} OF ${imgs.length}`,
      }));
      imgs.forEach((el, i) => { el.onclick = () => openLightbox(shots, i); });
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
          `Rendering ${subject || "the fallback test scene"} with ${smp.label} — two runs…`,
          "~60–180 s · two takes of the same prompt, so the variance is visible");
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
  // One ramp row per design language, drawn from notes rather than images.
  const renderPaletteRows = (list, refs) => {
    const rows = [];
    const byLang = new Map();
    refs.forEach(r => {
      const sw = swatchNotes(r.notes);
      sw.ref_id = r.id;
      if (!sw.hex) {                       // not a swatch — an uploaded plate
        rows.push({ label: r.id, single: r, swatches: [] });
        return;
      }
      if (!sw.language) { rows.push({ label: sw.name || r.id, swatches: [sw] }); return; }
      if (!byLang.has(sw.language)) {
        const row = { label: sw.language, swatches: [] };
        byLang.set(sw.language, row);
        rows.push(row);
      }
      byLang.get(sw.language).swatches.push(sw);
    });

    rows.forEach(row => {
      const el = document.createElement("div");
      el.className = "pal-row";
      const grouped = row.swatches.length > 1;
      const hero = row.swatches.find(s => s.hero);
      const ordered = rampOrder(row.swatches);
      const refId = (hero || ordered[0])?.ref_id || row.single?.id || "";
      el.innerHTML = `
        ${row.single
          ? `<div class="sw-ramp pal-plate"><img src="/api/references/${esc(row.single.id)}/image?size=thumb" alt=""></div>`
          : `<div class="sw-ramp">${ordered.map(sw =>
              `<i data-ref="${esc(sw.ref_id)}" style="flex:${sw.hero ? 2 : 1};${bandStyle(sw)}"></i>`).join("")}</div>`}
        <p class="sw-ramp-label">
          <span class="lang">${esc(row.label.toUpperCase())}</span>
          <span class="n">${grouped ? row.swatches.length : esc(ordered[0]?.hex || "")}</span>
          <span class="hero mono">${esc(refId)}</span>

        </p>`;
      // PALETTE_GROUPS_PLAN §2.1 wrote the viewer's "· APPROVED" header but
      // nothing reached it: approved rows were inert, which breaks the rule
      // the ramp itself canonized — the members are one click away.
      if (row.swatches.length) {
        $(".sw-ramp", el).style.cursor = "pointer";
        $(".sw-ramp", el).onclick = e => {
          const hit = e.target.closest("i");
          openSwatchViewer([{ language: row.label, swatches: row.swatches }],
            { focusRef: hit?.dataset.ref, approved: true, refresh: refreshRefs,
              onChange: () => {} }).then(refreshRefs);
        };
      }
      // R4 — no × on the row. A delete-forever control may not be the
      // loudest mark on a row it can destroy; removal lives in the viewer,
      // where the whole group can be read before it goes.
      list.append(el);
    });

    // The proposal bar's Review all disappears with the proposals, and the
    // approved column then had no way to read the whole palette at once
    // (user 2026-08-07) — only one language at a time, a row at a time.
    const groups = rows.filter(r => r.swatches.length)
      .map(r => ({ language: r.label, swatches: r.swatches }));
    const total = groups.reduce((n, g) => n + g.swatches.length, 0);
    // R4 — Review all sits beside the column's COUNT, not under the rows:
    // the count is what the verb acts on, so they belong together.
    const badge = list.closest(".wiz-col")?.querySelector("[data-f=state]");
    badge?.parentElement?.querySelector(".pal-review")?.remove();
    if (groups.length > 1 && badge) {
      const act = document.createElement("button");
      act.className = "text-act pal-review";
      act.textContent = `Review all ${groups.length} palettes`;
      act.onclick = () => openSwatchViewer(groups,
        { approved: true, refresh: refreshRefs, onChange: () => {} })
        .then(refreshRefs);
      badge.after(act);
    }
  };

  const refreshRefs = async () => {
    // Pending swatch proposals live in the review strip, not the anchor
    // rows (D8: they persist as PROVISIONAL refs so verdicts are records).
    const all = (await api("/api/references")).filter(r => r.status !== "REJECTED");
    // Pending proposals stay OUT of the anchor rows (D8: the strip is
    // their review surface) — but the badge must still see them, or a
    // column full of proposed colour reads NONE (user-hit 2026-08-23).
    const pendingPal = all.filter(r =>
      r.source === "swatch-proposal" && r.status === "PROVISIONAL");
    const refs = all.filter(r =>
      !(r.source === "swatch-proposal" && r.status === "PROVISIONAL"));
    // Every anchor in a column rides the bible draft (user ruling
    // 2026-08-05: inclusion IS the selection — no per-row checkbox).
    wizAnchorIds = refs.filter(r =>
      $(`.wiz-col[data-role="${CSS.escape(roleHead(r.role))}"]`)).map(r => r.id);
    for (const col of $$(".wiz-col[data-role]")) {
      const role = col.dataset.role;
      const mine = refs.filter(r => roleHead(r.role) === role);
      const badge = $("[data-f=state]", col);
      // An anchor is answered by a picture OR by words (user 2026-08-16).
      // A card reading NONE with its own answer sitting an inch below it
      // is the badge calling the user a liar — pictures still carry the
      // count, and words say so in their own right.
      const inWords = !!$("[data-f=words]", col)?.value.trim();
      // A design language is ONE palette (user, 2026-08-23: "it should
      // say 4 proposed, not 24"): the badge counts groups, never colours.
      // A swatch with no language is its own group of one, same rule the
      // ramp rows follow.
      const palGroups = rs => {
        const langs = new Set(); let singles = 0;
        rs.forEach(r => {
          const lang = (r.notes || "").split(" · ").length >= 3
            ? (r.notes || "").split(" · ")[0].trim() : "";
          lang ? langs.add(lang) : singles += 1;
        });
        return langs.size + singles;
      };
      const isPal = role === "COLOR_PALETTE";
      const nMine = isPal ? palGroups(mine) : mine.length;
      const nProp = isPal ? palGroups(pendingPal) : 0;
      badge.className = `badge ${nMine || inWords ? "APPROVED"
        : nProp ? "PROVISIONAL" : "LOCKED"}`;  // audit #4: unmet is a gate, not a failure
      badge.textContent = nMine ? `${nMine}`
        : nProp ? `${nProp} PROPOSED`
        : inWords ? "IN WORDS" : "NONE";
      const list = $("[data-f=list]", col);
      list.innerHTML = "";
      // PALETTE_GROUPS_PLAN §3 — the same rule above the review strip: a
      // design language is one object, so approved swatches group into one
      // ramp row per language. Bands come from the PARSED hexes, never the
      // thumbnails. A swatch with no language segment (a manual one, an
      // image-derived palette) is its own one-band row under its own name.
      if (role === "COLOR_PALETTE") {
        renderPaletteRows(list, mine);
        continue;
      }
      const lbItems = mine.map(r => ({
        src: `/api/references/${r.id}/image`, caption: `${r.id} — ${r.role}` }));
      mine.forEach((r, i) => {
        const item = document.createElement("div");
        item.className = "wiz-thumb";
        // No use-in-draft checkbox (user ruling 2026-08-05): if an anchor
        // is in the column, it is used — inclusion IS the selection.
        item.innerHTML = `
          <img src="/api/references/${esc(r.id)}/image?size=thumb" loading="lazy" alt="${esc(r.id)}">
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
      const label = $('.panel.step[data-step="3"] .uncast-label');
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
          // The fourth and last door into casting, and the one most likely
          // to be used: a chip in the uncast row. It wrote the card on
          // click and then fired the file chooser at you — the jarring the
          // user reported — through a selector that had since gone stale,
          // so it silently did nothing instead. One modal, like the rest.
          chip.onclick = () => castModal(r, refreshAll);
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

  // The manual door goes through the same modal (user 2026-08-16). It was
  // the last path that wrote the card on click and then fired the file
  // picker at you — and its picker selector had already gone stale, so it
  // silently did nothing. One way to cast, whichever door you came in by.
  $("#wiz-subj-add").onclick = () => {
    const name = $("#wiz-subj-name").value.trim();
    if (!name) return toast("Give the subject a name first.", true);
    castModal({ name, kind: $("#wiz-subj-kind").value, subtitle: "", traits: [] },
      () => {
        $("#wiz-subj-name").value = "";
        renderSubjectTags();
        renderSubjectGrid();
        wizardStepBadges();
      });
  };
  renderSubjectTags();
  renderSubjectGrid();

  // ---- Step 2: screenplay analysis ----
  // The stored analysis is the source of truth for design languages; cards
  // edit it in place. Model choice locks after a read.
  const getAnalysis = () => wizAnalysis;
  // User-caught 2026-08-23 (first user test): "if I reload the page I can
  // tell you that stuff's going away. I don't know where." This was
  // fire-and-forget with `.catch(() => {})` — the local copy and the
  // localStorage cache updated first, so the answer RENDERED as saved
  // whatever the server did, and a reload showed the truth. An interview
  // answer is the most expensive text in the app to retype; it is the
  // director's own words about their film.
  //
  // Now the write is awaited and a failure is stated. The local copy is
  // still set first — the input must not feel laggy — but a failed save
  // rolls the CACHE back so a reload cannot resurrect an answer the server
  // never took, which would be the same lie one refresh later.
  const saveAnalysis = async a => {
    const prev = wizAnalysis;
    wizAnalysis = a;
    wizACacheSet(a);
    wizardStepBadges();  // confirmations/drops move the step-2 badge
    try {
      await api("/api/wizard/analysis", { method: "PUT", json: a });
      return true;
    } catch (err) {
      wizACacheSet(prev || {});
      toast(`Not saved — ${err.message}. Your answer is still on screen; `
            + "copy it before leaving this page.", true);
      return false;
    }
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
  // SCAN_CONSOLIDATION §3 — a long list shows its head and states its tail.
  // Per-group expansion survives a re-render because the Set lives out here.
  const expandedGroups = new Set();
  const LOC_CAP = 5;

  /* One capping rule for every list that has one (§3): the first n rows,
     then a row that says how many more. `searching` lifts the cap outright
     — a list that hides matches behind an Expand is a list that lies. */
  const capList = (items, key, { cap = LOC_CAP, searching = false } = {}) => {
    if (searching || items.length <= cap || expandedGroups.has(key)) {
      return { shown: items, hidden: 0, expanded: expandedGroups.has(key),
               capped: false };
    }
    return { shown: items.slice(0, cap), hidden: items.length - cap,
             expanded: false, capped: true };
  };
  const capRow = (key, hidden, label = "") => hidden || expandedGroups.has(key)
    ? `<div class="loc-more"><button class="text-act" data-more-key="${esc(key)}">${
        expandedGroups.has(key) ? "Collapse" : `Expand — ${hidden} more`}</button>${
        label ? `<span class="loc-more-lab mono">${esc(label)}</span>` : ""}</div>`
    : "";
  const wireCapRows = (host, redraw) =>
    $$("[data-more-key]", host).forEach(b => b.onclick = () => {
      const k = b.dataset.moreKey;
      expandedGroups.has(k) ? expandedGroups.delete(k) : expandedGroups.add(k);
      redraw();
    });
  let qShowAll = false;

  // ---- read locations as a finder list (plan P4 / R2) ----
  // Flat, screenplay order, rendered through the shared buildLocFinder code
  // path. Sheet state uses the coverage table's own match semantics:
  // normalized whole-word containment either direction against the slugline
  // groups, then the group's server-computed sheet match is inherited.
  let wizCov;
  const normLoc = s => String(s).replace(/[’‘]/g, "'").replace(/[“”]/g, '"')
    .replace(/[—–−]/g, "-").replace(/\s+/g, " ").toLowerCase().trim();
  // D4 (PRODUCTION_DESIGN_V3) — labelled columns, fixed tracks; the gate
  // is a withheld verb (NEEDS THE BIBLE), never a button; once the Bible
  // exists the cell is the real verb.
  const wizLocRow = (name, sheet, extraCell = "") => `
    <div class="loc-row wiz-loc-row">
      <span class="loc-slug" title="${esc(name)}">${esc(name)}</span>
      ${extraCell || `<span class="loc-env-blank">&mdash;</span>`}
      <span class="loc-state">${sheet ? esc(sheet.spec_id) : "NONE"}</span>
      ${sheet
        ? `<button class="loc-open" data-open="${esc(sheet.spec_id)}">Open breakdown</button>`
        : state.stage_summary?.production_design?.bible_saved
          ? `<button class="text-act loc-draft" data-loc="${esc(name)}">Create breakdown</button>`
          : `<span class="wv-tag loc-gate">NEEDS THE BIBLE</span>`}
    </div>`;
  const WIZ_LOC_THEAD = `
    <div class="loc-thead">
      <span>LOCATION</span>
      <span>ENVIRONMENT — ITS VISUAL RULES</span>
      <span>SHEET</span>
      <span></span>
    </div>`;
  /* Which design language a place's palette comes from. There is no stored
     link — environments carry name/notes/keywords, languages carry
     name/keywords — so this is an INFERENCE, scored on shared tokens, and
     the modal says "where its palette comes from" rather than claiming an
     assignment the data does not hold. No match renders a stated blank. */
  const languageFor = (env, worlds) => {
    const hay = `${env.name || ""} ${env.notes || ""} `
      + `${(env.keywords || []).join(" ")}`.toUpperCase();
    let best = null, bestScore = 0;
    for (const w of worlds || []) {
      if (!w.name) continue;
      const toks = w.name.toUpperCase().split(/[^A-Z0-9]+/).filter(t => t.length >= 3);
      let score = toks.filter(t => hay.includes(t)).length * 2;
      score += (w.keywords || []).filter(k => k && hay.includes(String(k).toUpperCase())).length;
      if (score > bestScore) { best = w; bestScore = score; }
    }
    return best;
  };

  async function openEnvModal(env, idx, patchEnvs) {
    const a = getAnalysis() || {};
    const lang = languageFor(env, a.design_worlds || []);
    let swatches = [];
    if (lang) {
      const refs = await api("/api/references").catch(() => []);
      swatches = refs
        .filter(r => roleHead(r.role) === "COLOR_PALETTE" && r.status !== "REJECTED")
        .map(r => ({ ...swatchNotes(r.notes), ref_id: r.id }))
        .filter(sw => sw.hex && sw.language
          && sw.language.toUpperCase() === lang.name.toUpperCase());
    }
    const locs = env.locations || [];
    const KEY = `envmodal:${env.name}`;

    const draw = () => {
      const cut = capList(locs, KEY);
      const ordered = rampOrder(swatches);
      return `<div class="envm">
        <div class="sv-head">
          <span class="sv-title">${esc(env.name || "(unnamed)")}</span>
          <span class="sv-sub mono">ENVIRONMENT · ${locs.length} LOCATION${
            locs.length === 1 ? "" : "S"} INHERIT THESE RULES</span>
          <button class="sv-x" data-f="x" title="Close">&times;</button>
        </div>
        <div class="envm-body">
          <div class="envm-main">
            <label class="envm-f"><span class="envm-lab">NAME</span>
              <input type="text" data-f="name" value="${esc(env.name || "")}"></label>
            <label class="envm-f"><span class="envm-lab">THE VISUAL RULES
              <i>WHAT EVERY PLACE HERE INHERITS — PALETTE, LIGHT, MATERIAL, ATMOSPHERE</i></span>
              <textarea data-f="notes" class="envm-prose">${esc(env.notes || "")}</textarea></label>
            <div class="envm-2up">
              <label class="envm-f"><span class="envm-lab">LIGHT</span>
                <input type="text" data-f="light" value="${esc(env.light || "")}"></label>
              <label class="envm-f"><span class="envm-lab">MATERIAL</span>
                <input type="text" data-f="material" value="${esc(env.material || "")}"></label>
            </div>
            <div class="envm-f">
              <span class="envm-lab">DESIGN LANGUAGE — WHERE ITS PALETTE COMES FROM</span>
              ${lang ? `<div class="envm-lang">
                <button class="vchip" data-f="goto-lang">${esc(lang.name.toUpperCase())}</button>
                ${ordered.length ? `<div class="sw-ramp envm-ramp">${ordered.map(sw =>
                  `<i style="flex:${sw.hero ? 2 : 1};${bandStyle(sw)}"></i>`).join("")}</div>
                <span class="mini mono">${ordered.length} SWATCH${
                  ordered.length === 1 ? "" : "ES"}</span>`
                : `<span class="mini mono">NO SWATCHES YET</span>`}
              </div>` : `<div class="mini mono envm-nolang">— NO DESIGN LANGUAGE ASSIGNED</div>`}
            </div>
          </div>
          <div class="envm-side">
            <p class="envm-lab">LOCATIONS THAT INHERIT THIS — ${locs.length}</p>
            <div class="envm-locs">${cut.shown.map(l =>
              `<span class="envm-loc mono">${esc(l)}</span>`).join("")
              || `<span class="mini">none yet</span>`}</div>
            ${capRow(KEY, cut.hidden)}
            <p class="envm-blast mono">EDITING THE RULES REPAINTS ALL ${locs.length} SHEET${
              locs.length === 1 ? "" : "S"} THAT HAVE NOT BEEN OVERRIDDEN</p>
          </div>
        </div>
        <div class="envm-foot">
          <button class="primary" data-f="save">Save environment</button>
          <button class="ghost" data-f="cancel">Cancel</button>
          <button class="text-act envm-del" data-f="del">Delete environment</button>
        </div>
      </div>`;
    };

    return modal({
      custom: draw(),
      mount: (ov, done) => {
        const wire = () => {
          $("[data-f=x]", ov).onclick = () => done(null);
          $("[data-f=cancel]", ov).onclick = () => done(null);
          wireCapRows(ov, () => { $(".envm", ov).outerHTML = draw(); wire(); });
          $("[data-f=goto-lang]", ov)?.addEventListener("click", () => {
            done(null);
            const el = $("#wiz-langs-sec");
            if (el) window.scrollTo({
              top: el.getBoundingClientRect().top + window.scrollY - 80,
              behavior: "smooth" });
          });
          $("[data-f=save]", ov).onclick = () => {
            const v = f => $(`[data-f=${f}]`, ov).value.trim();
            patchEnvs(list => {
              const next = { ...list[idx], name: v("name") || env.name,
                             notes: v("notes") };
              // Empty is ABSENT, not "" — the Bible draft appends these as
              // their own lines and a blank line is a lie about the world.
              v("light") ? next.light = v("light") : delete next.light;
              v("material") ? next.material = v("material") : delete next.material;
              // Editing-and-saving a proposed environment = implicit confirm.
              if (next.status === "PROPOSED") delete next.status;
              list[idx] = next;
            });
            done(null);
          };
          $("[data-f=del]", ov).onclick = async () => {
            if (!(await askConfirm(`Delete "${env.name}"?`,
              `${locs.length} location${locs.length === 1 ? "" : "s"} inherit these `
              + "rules and will fall back to UNASSIGNED. Sheets already drafted keep "
              + "what they have.", "Delete environment", true))) return;
            patchEnvs(list => list.splice(idx, 1));
            done(null);
          };
        };
        wire();
      },
    });
  }

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
      // Grouped by ACT (user 2026-08-16), chronologically. Environment was
      // the old grouping and it answered "what does this place inherit" —
      // a question the per-row selector still answers. The list itself is
      // asked something else: where does the story GO. Acts come from the
      // screenplay when it marks them, with its own titles; otherwise the
      // standard three-act split, unnamed, because `ACT I` with no title is
      // honest and a title we invented is a claim we cannot support.
      const byLoc = Object.fromEntries(groups.map(g => [g.location, g]));
      const assignedTo = {};
      envs.forEach(e => (e.locations || []).forEach(l => { assignedTo[l] = e.name; }));
      const envNames = envs.map(e => e.name);
      // Names are a READING of the story, so they come from the scan (a
      // model pass over the screenplay), not from the slugline parse.
      // The parse owns the DIVISIONS — where each act starts and ends —
      // because that is arithmetic and must not drift per run. A
      // screenplay that prints its own ACT headings supplies both and
      // neither is inferred (user 2026-08-16: "it is very traditionally
      // formatted, I would expect you to be able to come up with Act
      // Names" — their draft prints none, so the scan names them).
      const scanned = getAnalysis()?.acts || [];
      const acts = (wizCov?.acts || []).map(a => {
        const named = scanned.find(x => Number(x.n) === a.n);
        return (!a.title && named?.title)
          ? { ...a, title: String(named.title), titleFrom: "scan" } : a;
      });
      const placed = new Set();
      const grouped = acts.map(a => {
        const locs = groups.filter(g => g.act === a.n).map(g => g.location);
        locs.forEach(l => placed.add(l));
        const named = scanned.find(x => Number(x.n) === a.n);
        return {
          key: `act-${a.n}`,
          act: a.n,
          titleFrom: a.titleFrom || (named?.title ? "scan" : ""),
          turn: a.turn || named?.turn || "",
          label: `ACT ${a.roman}${a.title ? ` — ${a.title.toUpperCase()}` : ""}`,
          locs,
        };
      });
      // Anything the read named that the slugline parse never saw has no
      // scene, so it has no act — said outright rather than filed into one.
      const actless = (getAnalysis()?.key_locations || [])
        .filter(n => !placed.has(n) && !byLoc[n]);
      // D4 (RULE_PASS_2 D, ruled 2026-08-18): these rows have no scene to
      // break down, so a fourth "act" under a head reading EACH BECOMES ONE
      // BREAKDOWN made the count and the claim disagree. It leaves the act
      // list and becomes a register below it, with its own honest label.
      const register = actless.length
        ? { key: "no-act", register: true,
            label: "NAMED IN THE READ · NOT IN ANY SLUGLINE", locs: actless }
        : null;
      // The head counts only what it claims: placeable locations.
      const total = grouped.reduce((n, g) => n + g.locs.length, 0);
      if (register) grouped.push(register);
      buildLocFinder(secHost, {
        // D1: the provenance moved to the headings it applies to — a
        // string three groups above the thing it describes discloses less
        // than position, and position alone does not disclose.
        head: `<div class="loc-head"><span class="uncast-label">LOCATIONS — ${total} · EACH BECOMES ONE BREAKDOWN <span class="loc-showing">FIVE SHOWN PER ACT</span>${
          wizCov?.acts_derived || acts.some(a => a.title) ? "" :
          ` <button type="button" class="text-act" data-f="name-acts"
              title="One small read of the screenplay that fills the act names only — your design languages, environments and subjects are not touched.">${
                acts.some(a => a.title) ? "Rename the acts" : "Name the acts"}</button>`
        }</span></div>`,
        headRow: WIZ_LOC_THEAD,
        placeholder: "find a location…",
        rows: (needle, q) => grouped.map(g => {
          const locs = g.locs.filter(n => !needle || n.toUpperCase().includes(needle));
          if (!locs.length) return "";
          const cut = capList(locs, g.key, { searching: !!needle });
          // D1: three states, three drawings — printed, READ, unnamed.
          // D2: the beat the act turns on is the evidence that makes an
          // inferred name checkable; it was a bare title on the group.
          // D3: the heading is a heading, and Rename is a visible control.
          const read = g.titleFrom === "scan"
            ? ` <span class="loc-read mono">READ</span>` : "";
          return `<div class="loc-group${g.register ? " loc-register" : ""}">`
            + `<span class="loc-act-head">${esc(g.label)}${read}</span>`
            + ` — ${locs.length}${
              cut.capped ? ` · <span class="loc-showing">SHOWING ${cut.shown.length}</span>` : ""}${
              g.act ? ` <button type="button" class="text-act loc-act-name" data-act="${g.act}"
                title="Rename this act — a reading you disagree with is a reading you can change">Rename</button>` : ""}`
            + (g.turn ? `<span class="loc-turn mono">TURNS ON — ${esc(String(g.turn).toUpperCase())}</span>` : "")
            + `</div>`
            + cut.shown.map(n => wizLocRow(n, byLoc[n]?.sheet, `
              <select class="loc-reassign" data-loc="${esc(n)}" title="The environment this location inherits its palette, light and atmosphere from — saved to the analysis immediately.">
                ${["UNASSIGNED", ...envNames].map(en =>
                  `<option${(assignedTo[n] || "UNASSIGNED") === en ? " selected" : ""}>${esc(en)}</option>`).join("")}
              </select>`)).join("")
            + capRow(g.key, cut.hidden, g.label);
        }).join("") || `<p class="mini">nothing matches "${esc(q)}"</p>`,
        onDraw: (redraw) => {
          // Expanding an act redraws the finder in place — the needle and
          // the scroll position stay where the user left them.
          wireCapRows(secHost, redraw);
          // Naming the acts is its own small call, NOT a re-scan: a
          // re-scan would overwrite curated design languages, environments
          // and subjects to fill one field (user 2026-08-16).
          // A reading you disagree with is a reading you can change.
          $$(".loc-act-name", secHost).forEach(b => b.onclick = async e => {
            e.stopPropagation();
            const n = Number(b.dataset.act);
            const a = getAnalysis() || {};
            const cur = (a.acts || []).find(x => Number(x.n) === n);
            const v = await askText(`Act ${n}`, "Act name",
              { value: cur?.title || "",
                hint: "two or three words, in the screenplay's own vocabulary — "
                    + "leave it empty to go back to an unnamed act",
                confirmLabel: "Save" });
            if (v === null) return;
            a.acts = [...(a.acts || []).filter(x => Number(x.n) !== n),
                      { n, title: v.trim().toUpperCase(),
                        turn: cur?.turn || "" }]
              .filter(x => x.title)
              .sort((x, y) => x.n - y.n);
            saveAnalysis(a);
            renderWorlds();
          });
          const nameBtn = $("[data-f=name-acts]", secHost);
          if (nameBtn) nameBtn.onclick = async () => {
            nameBtn.disabled = true;
            nameBtn.textContent = "Reading the screenplay…";
            try {
              const r = await api("/api/wizard/acts", { method: "POST",
                json: { provider: $("#wiz-provider")?.value || "gemini" } });
              // The server already merged it into the stored analysis;
              // this keeps the in-memory copy in step without a PUT that
              // would race it.
              const a = getAnalysis() || {};
              a.acts = r.acts;
              wizAnalysis = a;
              wizACacheSet(a);
              toast(`Acts named: ${r.acts.map(x => x.title).join(" · ")}.`);
              renderWorlds();
            } catch (err) {
              toast(err.message, true);
              nameBtn.disabled = false;
              nameBtn.textContent = "Name the acts";
            }
          };
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
      head: `<div class="loc-head"><span class="uncast-label">LOCATIONS — ${keyLocs.length} · EACH BECOMES ONE BREAKDOWN</span></div>`,
      headRow: WIZ_LOC_THEAD,
      placeholder: "find a location…",
      rows: (needle, q) => keyLocs
        .filter(n => !needle || n.toUpperCase().includes(needle))
        .map(n => wizLocRow(n, matchOf(n)?.sheet))
        .join("") || `<p class="mini">nothing matches "${esc(q)}"</p>`,
    });
  };

  /* The same words the server treats as "nobody has said" (wizard.py
     `_NO_PERIOD`). The scan is TOLD to answer UNSTATED when the
     screenplay does not fix a period, so printing that back as a result
     would read as something it found. */
  const wizNoPeriod = v =>
    ["", "UNSTATED", "UNKNOWN", "N/A", "NONE"].includes(String(v || "").trim().toUpperCase());

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
    // SCAN_CONSOLIDATION §1 — the logline reads FIRST and full width: it
    // is what the read understood, and the counts are the tally of what
    // that understanding produced. Anchored explanation, doing its job.
    // Open questions carry the only colored number: --accent while any remain.
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
        ${analysis.logline ? `<div class="read-logline">
          <span class="read-log-kicker">LOGLINE</span>
          <p>${esc(analysis.logline)}</p></div>` : ""}
        <div class="read-period">
          <span class="read-log-kicker">PERIOD</span>
          <p><span class="rp-val mono">${esc(analysis.period || "UNSTATED")}</span>
             <button type="button" class="text-act" data-f="edit-period">${
               analysis.period ? "Edit" : "State it"}</button></p>
          <span class="mini">Every render is held to this. An unstated period
            constrains nothing — which is how a WW2 aircraft reached a
            far-future salt pan.</span>
        </div>
        <div class="read-tiles">${tiles}</div>
      </div>
      <div class="fgroup" id="wiz-langs-sec" style="margin-top:16px">
        <span class="uncast-label">DESIGN LANGUAGES — WHAT A PANEL IS ALLOWED TO LOOK LIKE
          <button type="button" class="q-help" data-help="langs" aria-label="What is a design language?">?</button></span>
        <div id="wiz-world-tags" class="chips" style="margin-bottom:8px"></div>
        <div id="wiz-worlds"></div>
      </div>
      <div id="wiz-envs-sec" style="margin-top:16px">
        <div class="uncast-label">ENVIRONMENTS — THE LIGHT AND PALETTE OF A PLACE
          <button type="button" class="q-help" data-help="envs" aria-label="How are environments used?">?</button></div>
        <div id="wiz-envs"></div>
      </div>
      ${(analysis.key_locations || []).length || (analysis.environments || []).length ? `<div id="wiz-locs-sec" style="margin-top:16px"></div>` : ""}
      ${qN ? `<div id="wiz-questions-sec" style="margin-top:16px">
        <div class="uncast-label">OPEN QUESTIONS — ${answeredN} OF ${qN} ANSWERED · ANSWERS RIDE THE BIBLE DRAFT
          <span class="q-optional">OPTIONAL — YOU CAN DO THIS OVER TIME</span></div>
        <div id="wiz-questions" class="q-grid"></div>
      </div>` : ""}`;
    const GOTO = {
      langs: () => $("#wiz-langs-sec"), envs: () => $("#wiz-envs-sec"),
      locs: () => $("#wiz-locs-sec"), questions: () => $("#wiz-questions-sec"),
      // Cast the film, not the interview — this pointed at step 3 from
      // before LOCKED_STAGE_PLAN L3 swapped the two, so the SUBJECTS tile
      // has been scrolling to the wrong panel since (found 2026-08-07).
      subjects: () => $('.panel.step[data-step="3"]'),
    };
    $$(".read-tile", host).forEach(a => a.onclick = () => {
      const el = GOTO[a.dataset.goto]?.();
      if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 80,
                                behavior: "smooth" });
    });
    // The production states WHEN it is set, once, and every render is held
    // to it (first user test, 2026-08-23). Pre-filled by the scan; editable
    // by hand so a production that predates the field can simply say it,
    // without paying for another read.
    const periodBtn = $("[data-f=edit-period]", host);
    if (periodBtn) periodBtn.onclick = async () => {
      const v = await askText("When is this production set?", "Period", {
        value: analysis.period || "",
        placeholder: "e.g. 241 years in the future",
        body: "Every render is held to this. Say it the way you would say it "
            + "to a concept artist — a decade, a century, an era, or a "
            + "distance from now.",
        hint: "Leave empty to constrain nothing.",
        confirmLabel: "Save period",
      });
      if (v === null) return;
      const a = getAnalysis();
      a.period = String(v).trim();
      if (await saveAnalysis(a)) {
        toast(a.period ? `Period set — every render is held to "${a.period}".`
                       : "Period cleared — renders are no longer era-constrained.");
        renderWorlds();
      }
    };
    bindHelpButtons(host, WIZ_HELP);
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
        const patch = async updates => {
          const a = getAnalysis();
          a.question_answers = a.question_answers || {};
          a.question_answers[q] = { ...(a.question_answers[q] || {}), ...updates };
          const ok = await saveAnalysis(a);
          renderWorlds();
          return ok;
        };
        const defer = $("[data-f=defer]", row);
        const answerBtn = $("[data-f=answer]", row);
        answerBtn.onclick = () => {
          const main = $(".q-main", row);
          if ($("input", main)) return;
          // User-caught 2026-08-23, three times before it was right.
          //
          // Ada on the call: "I don't know how to save this answer... there
          // should be a button here like and I'm clicking it." Enter was the
          // ONLY commit, so typing and clicking away discarded the answer
          // with no request and therefore no feedback.
          //
          // The first fix hardened the transport, which was never the
          // problem. The second added a Save button BESIDE the Answer button
          // that opened the field — two controls for one act, with the
          // now-meaningless Answer still sitting there.
          //
          // The button that opens the editor BECOMES the save. One control,
          // one place to look, and its label always names what pressing it
          // does next.
          const input = document.createElement("input");
          input.type = "text";
          input.value = st.answer || "";
          input.placeholder = "your answer…";
          input.title = "Appended to the interview as a Q/A pair and honored by the Bible draft.";
          const hint = document.createElement("span");
          hint.className = "mini mono q-edit-hint";
          hint.textContent = "ENTER SAVES · ESC DISCARDS";
          const wrap = document.createElement("span");
          wrap.className = "q-edit";
          wrap.append(input, hint);
          main.append(wrap);
          input.focus();
          input.select();

          const wasLabel = answerBtn.textContent;
          const wasClass = answerBtn.className;
          answerBtn.textContent = "Save";
          answerBtn.className = "primary";
          if (defer) { defer.textContent = "Cancel"; defer.onclick = () => discard(); }

          let settled = false;   // the button, Enter and blur share one act
          const commit = async () => {
            if (settled) return;
            settled = true;
            const v = input.value.trim();
            if (v === (st.answer || "")) { renderWorlds(); return; }
            answerBtn.disabled = true;
            const ok = await patch({ answer: v, deferred: false });
            if (ok && v) toast("Answer saved — it rides into the Bible draft.");
          };
          const discard = () => {
            if (settled) return;
            settled = true;
            answerBtn.textContent = wasLabel;
            answerBtn.className = wasClass;
            renderWorlds();
          };

          answerBtn.onclick = commit;
          input.onkeydown = e => {
            if (e.key === "Escape") return discard();
            if (e.key === "Enter") return commit();
          };
          // Clicking away saves. Losing an answer to a stray click is the
          // whole reported bug; a surprise save is recoverable, a silent
          // discard is not. The delay lets a click on Save land as Save
          // rather than as a blur.
          input.onblur = () => setTimeout(() => { if (!settled) commit(); }, 150);
        };
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
        // SCAN_CONSOLIDATION §2 — a 30-word paragraph that other records
        // INHERIT is not editable in a 14px field inside a 5-up grid cell.
        // It opens a room that shows the prose, what inherits it, and the
        // blast radius, and states that before the save.
        $("[data-f=edit]", card).onclick = () => openEnvModal(env, i, patchEnvs);
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
    /* The design plan's ladder.

       Same honesty rule as the Bible's: ASSEMBLE is real client-side work
       over inputs already known, READ is ONE model call with no visible
       interior — so it shows a clock and says so rather than a bar
       creeping toward a number nobody measured — and FOUND fills each row
       from the response as it is parsed. */
    const lad = runLadder.create($("#wiz-analyze-busy"), {
      title: "Building the design plan",
      phases: [{ key: "assemble", label: "ASSEMBLE" }, { key: "read", label: "READ" },
               { key: "found", label: "FOUND" }],
      rows: [{ key: "langs", label: "Design languages" },
             { key: "envs", label: "Environments" },
             { key: "locs", label: "Locations" },
             { key: "subjects", label: "Subjects to cast" },
             { key: "questions", label: "Open questions" },
             { key: "period", label: "Period" }],
    });
    lad.phase("assemble", `Sending the screenplay to ${selectedModelLabel($("#wiz-provider"))}.`);
    try {
      lad.phase("read", "One call, and no way to see inside it — the clock "
                       + "is the only honest progress there is. A minute or two.");
      const analysis = await api("/api/wizard/analyze", {
        method: "POST", json: { provider: $("#wiz-provider").value } });
      lad.phase("found", "");
      lad.set("langs", (analysis.design_worlds || []).length);
      lad.set("envs", (analysis.environments || []).length);
      lad.set("locs", (analysis.key_locations || []).length);
      lad.set("subjects", (analysis.subjects || []).length);
      lad.set("questions", (analysis.unresolved || []).length);
      // Blank rather than a claimed answer: the read is told to say
      // UNSTATED when the screenplay does not fix a period, and printing
      // that word as a result would read as something it found.
      lad.set("period", wizNoPeriod(analysis.period) ? null : analysis.period);
      lad.done("Review what it found below, then build the Art Direction Bible.");
      saveAnalysis(analysis);
      expandedWorlds.clear();
      renderWorlds();
      renderAnalyzeLock();
      renderSubjectTags();
      toast(`Found ${(analysis.design_worlds || []).length} design language(s) and ${(analysis.subjects || []).length} subject(s) — review below.`);
    } catch (err) {
      // The ladder keeps its rows and states the failure in place. It
      // used to vanish on error, taking with it the only record of how
      // far the read got.
      lad.fail(err.message);
      toast(err.message, true);
    } finally { btn.disabled = false; }
  };

  renderWorlds();
  renderAnalyzeLock();

  /* The one button. It dispatches on state rather than asking the user to
     pick a verb, which is the whole point of there being one. */
  $("#wiz-draft").onclick = async () => {
    const st = bibleState();
    if (st === "saved") {                       // Edit — unlock, hand over
      bibleEditing = true;
      syncBibleSave();
      const editor = $("#style-bible");
      editor.focus();
      editor.setSelectionRange(editor.value.length, editor.value.length);
      return;
    }
    if (st === "editing" || st === "unsaved") { // Save
      if (!(await saveBible({ quietIfUnchanged: true }))) return;
      bibleEditing = false;
      syncBibleSave();
      return;
    }
    return writeBible();                        // Create
  };

  $("#bible-regen").onclick = async () => {
    if (!(await askConfirm(
      "Regenerate the Art Direction Bible",
      ["The current bible is replaced by a newly written one, from your "
       + "anchors, the scan and the cast as they stand now.",
       "THE TEXT YOU HAVE NOW CANNOT BE RECOVERED. If you have edited it by "
       + "hand, copy what you want to keep before continuing.",
       "Approved work already made under it is untouched."].join(BR + BR),
      "Regenerate it"))) return;
    return writeBible({ replacing: true });
  };

  /* Create and Regenerate are the same act — write from the anchors and
     save — differing only in whether something is being replaced. */
  const writeBible = async ({ replacing = false } = {}) => {
    const btn = $("#wiz-draft");
    btn.disabled = true;
    const regen = $("#bible-regen");
    if (regen) regen.disabled = true;
    theBible.begin({
      langs: (getAnalysis()?.design_worlds || [])
        .filter(w => w.status !== "PROPOSED" && (w.name || "").trim())
        .map(w => w.name.trim()),
      subjects: (getAnalysis()?.subjects || []).length,
      anchors: [["TEXTURE", $("#wiz-texture").value], ["PALETTE", $("#wiz-palette").value],
                ["CINEMATOGRAPHY", $("#wiz-light").value], ["MEDIUM", $("#wiz-medium").value]]
        .filter(([, v]) => (v || "").trim())
        .map(([k, v]) => `${k}: ${v.trim().slice(0, 90)}`),
    });
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
        // The words half of each anchor — collected from the anchor cards
        // themselves since 2026-08-16, not from a second list beside them.
        texture: $("#wiz-texture").value.trim(),
        palette: $("#wiz-palette").value.trim(),
        light: $("#wiz-light").value.trim(),
        medium: $("#wiz-medium").value.trim(),
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
      editor.value = r.markdown;
      /* Create SAVES (user, 2026-08-22: "it should also save it so it
         unlocks breakdown tab"). The old flow drafted into an editor and
         waited for a second, differently-worded button before anything
         downstream opened — so the one gold button on the step produced a
         result that changed nothing until you found the grey one. */
      bibleEditing = false;
      theBible.written(r.markdown);
      const saved = await saveBible();
      syncBibleSave();
      if (saved) {
        /* ONE act (user, 2026-08-22). Colour was a second pass behind a
           second control that read the bible again — and a bible written
           for it is the only thing it can be grounded in, so the two were
           never really separable. */
        theBible.colouring();
        try {
          const sw = await api("/api/wizard/swatches", { method: "POST",
            json: { provider: $("#wiz-provider").value, note: "", deep: false } });
          theBible.coloured(sw);
          renderSwatchStrip(sw);
          refreshRefs();
        } catch (err) {
          theBible.fail(`the bible is saved, but colour failed: ${err.message}`);
        }
      }
      if (saved) {
        $("#style-status").innerHTML =
          `<span class="badge LOCKED">SAVED</span> WRITTEN BY `
          + `${esc(r.model || "the model").toUpperCase()} — BREAKDOWNS ARE OPEN. `
          + `EDIT BELOW TO CHANGE IT`;
        toast(`Art Direction Bible written by ${r.model} and saved — Breakdowns `
              + "are open. Search it for (PROPOSED) to find its guesses.");
      }
    } catch (err) { theBible.fail(err.message); toast(err.message, true); }
    finally { btn.disabled = false; if (regen) regen.disabled = false; }
  };

  // ---- the Bible itself + project-wide lessons (the PD's living documents) ----
  // Save is disabled while the editor is empty (user-directed 2026-08-05):
  // the gate is readable as state — disabled control + the stated
  // condition beside it — instead of a 422 after the click.
  /* ONE primary control, whose verb is always the next true thing (user,
     2026-08-22: "I should not have to detail out how creating, editing and
     saving should work — make it all one button").

       no bible, editor empty      Create Art Direction Bible
       no bible, text pasted       Save Art Direction Bible
       saved                       Edit            + Regenerate
       editing                     Save            (Regenerate hidden)

     Two buttons existed before — a gold one that drafted and stopped, and
     a grey one that was the only thing which actually opened Breakdowns.
     Deciding how those decompose was never the user's job. */
  let bibleEditing = false;
  let bibleSavedText = "";      // what is on disk, for "did anything change"

  const bibleState = () => {
    const text = $("#style-bible").value.trim();
    if (bibleEditing) return "editing";
    if (!bibleSavedText) return text ? "unsaved" : "empty";
    return "saved";
  };

  const syncBibleSave = () => {
    const editor = $("#style-bible");
    const btn = $("#wiz-draft");
    const regen = $("#bible-regen");
    const cond = $("#bible-cond");
    const st = bibleState();

    // Editable whenever there is nothing saved to protect, and while
    // editing. A saved bible is a document, and a document is read-only
    // until you say otherwise.
    editor.readOnly = st === "saved";
    editor.classList.toggle("is-locked", st === "saved");

    const VERB = {
      empty: "Build Art Direction Bible",
      unsaved: "Save Art Direction Bible",
      saved: "Edit",
      editing: "Save Art Direction Bible",
    };
    btn.textContent = VERB[st];
    btn.classList.toggle("primary", st !== "saved");
    btn.classList.toggle("ghost", st === "saved");
    regen.classList.toggle("hidden", st !== "saved");
    // Same condition as Regenerate: there has to BE a saved document to
    // read against itself, and an unsaved edit is not one yet.
    $("#bible-check")?.classList.toggle("hidden", st !== "saved");
    cond.textContent = {
      empty: "FROM THE ANCHORS, THE SCAN AND THE CAST — WRITTEN, SAVED, AND BREAKDOWNS OPEN",
      unsaved: "YOUR OWN TEXT — SAVING IT OPENS BREAKDOWNS",
      // Nothing: the panel heading already carries this fact, and the
      // status chip beside it carries the revision. Saying it a third
      // time on one row is the verbosity the design system cuts.
      saved: "",
      editing: "ESC DISCARDS — NOTHING CHANGES UNTIL YOU SAVE",
    }[st];
  };
  $("#style-bible").addEventListener("input", () => {
    syncBibleSave();
    renderBibleConflicts(null);
  });
  // Escape is the way out of an edit, so Edit is never a trap.
  $("#style-bible").addEventListener("keydown", e => {
    if (e.key !== "Escape" || !bibleEditing) return;
    e.preventDefault();
    $("#style-bible").value = bibleSavedText;
    bibleEditing = false;
    syncBibleSave();
    $("#style-status").innerHTML = "";
  });
  /* R2 — the Bible read against itself (2026-08-25).

     The production this was built from carried, in three different
     places: "use wide or moderate-wide lenses with deep focus" in
     Lighting Language, "readable form over surface" in Rendering
     Language, and legibility everywhere in Composition Rules. Three
     sections independently ruling out selective focus, none aware of the
     others, under a grammar whose whole subject is selective focus. Two
     days of renders came back flat and every part of the plumbing tested
     correct.

     Reports only. The director decides what a contradiction means; the
     app's job is to have READ the thing. Designed contrast — Weathered
     Present against Pristine Future — is the spine of a production and
     never appears here, which is stated in the prompt and is the single
     thing that decides whether this gets turned off. */
  const renderBibleConflicts = (r) => {
    const host = $("#bible-conflicts");
    if (!host) return;
    if (!r) { host.innerHTML = ""; return; }
    if (!r.conflicts?.length) {
      host.innerHTML = `<div class="bc-none mini">Read ${
        (r.checked_chars || 0).toLocaleString()} characters — no two rules that
        cannot both hold in one frame. Deliberate contrast between different
        subjects is not counted, and is not a fault.</div>`;
      return;
    }
    host.innerHTML = `<div class="bc-head mono">${r.conflicts.length} CONFLICT${
      r.conflicts.length === 1 ? "" : "S"} — ADVISORY, NOTHING WAS CHANGED</div>`
      + r.conflicts.map(c => `<div class="bc-row">
          <div class="bc-secs mono">${c.sections.map(esc).join("  ✕  ")}</div>
          ${c.quotes.map(q => `<div class="bc-q">“${esc(q)}”</div>`).join("")}
          <div class="bc-why mini">${esc(c.why)}</div>
        </div>`).join("");
  };
  $("#bible-check")?.addEventListener("click", async () => {
    const btn = $("#bible-check");
    btn.disabled = true;
    const was = btn.textContent;
    btn.textContent = "Reading…";
    try {
      renderBibleConflicts(await api("/api/bible/self-check",
        { method: "POST", json: { provider: $("#wiz-provider")?.value || "gemini" } }));
    } catch (err) {
      /* Never swallowed. "No conflicts" and "the read failed" look
         identical on screen, and one of them means the document has not
         been checked at all. */
      renderBibleConflicts(null);
      toast(`Could not read the bible against itself: ${err.message}`, true);
    } finally {
      btn.disabled = false;
      btn.textContent = was;
    }
  });
  const loadBibleEditor = async () => {
    const bible = await api("/api/style-bible");
    $("#style-bible").value = bible.text;
    // What is on disk. The button's state hangs off this: with nothing
    // saved the editor is yours to paste into, and once something IS
    // saved the button becomes Edit rather than Create.
    bibleSavedText = (bible.text || "").trim();
    bibleEditing = false;
    // No template default exists (director's ruling 2026-08-01) — empty
    // means not yet drafted, and says so.
    // A clash is normally impossible — the interview save and boot both
    // reconcile the section onto the anchor. What reaches here is a bible
    // EDITED BY HAND back onto a different medium, which is the director's
    // right and not something to silently overwrite. So it is stated,
    // where it can be read before a render is paid for.
    const clash = (bible.anchor_conflicts || []).length
      ? `<span class="badge REJECTED">ANCHOR</span> `
        + esc(bible.anchor_conflicts.join("; "))
      : "";
    $("#style-status").innerHTML = (!bible.text.trim()
      ? ""
      : (bible.rev ? `<span class="badge LOCKED">REV ${bible.rev}</span> saved` : ""))
      + (clash ? (bible.text.trim() ? " &middot; " : "") + clash : "");
    // A report describes the text it read. Once the document is reloaded
    // it describes something that may no longer be on screen, and a stale
    // all-clear is worse than no report.
    renderBibleConflicts(null);
    syncBibleSave();
    return bible;
  };
  /* A4 — the production camera card is retired (2026-08-25).

     It set a production-wide `Eye level · 24mm · Level · Wide` and led
     Production Design, so it looked like a decision. It was not one:
     nobody chose those values, they are what a new production starts
     with. And they went into every prompt as directives, where they read
     as deliberate.

     That is not a cosmetic problem. Under a Subjective/Poetic grammar
     asking for isolation and selective focus, a 24mm deep-focus wide is
     a straight contradiction — and it is the contradiction that defeated
     the cinematography axis for two days of renders while every part of
     the plumbing tested correct. A grammar now carries framings that say
     50–100mm at f/1.4–2.8, in optics a model cannot satisfy by doing
     nothing, and a card offering a lens beside them is a second camera
     authority in the same prompt.

     What survives, and why it is enough:
     - camera_defaults.json remains the SILENT fallback. The values still
       exist and still answer the breakdown's "— production default —";
       they are simply no longer presented as a choice anyone made.
     - the panel's own camera axes stay, and beat the framing. That is a
       director disagreeing with the recipe on one shot, which is the
       whole point of keeping them.
     - /api/camera-defaults stays, unread by any screen. Removing an
       endpoint is a separate decision from removing a control, and a
       production that set values before today keeps rendering with them.
  */
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
      // An anchor is SET by a picture OR by words (user 2026-08-16): the
      // interview asked the same four questions in prose, so folding it in
      // means an anchor answered in words is answered.
      const roles = AUTO_ATTACH_HEADS;  // the four-anchor shelf
      const ANCHOR_WORDS = { WORLD_TEXTURE: "#wiz-texture",
                             COLOR_PALETTE: "#wiz-palette",
                             CINEMATOGRAPHY_STYLE: "#wiz-light",
                             BOARD_RENDERING_STYLE: "#wiz-medium" };
      const set = roles.filter(role =>
        refs.some(r => r.status === "APPROVED" && roleHead(r.role) === role)
        || $(ANCHOR_WORDS[role])?.value.trim()).length;
      setB(1, set === roles.length ? "APPROVED" : "PROVISIONAL",
        `${set} OF ${roles.length} SET`);
      // The scan step reflects review debt: proposed languages AND environments
      // hold the badge at PROVISIONAL until confirmed or dropped (plan P9).
      const proposedN =
        (wizAnalysis?.design_worlds || []).filter(w => w.status === "PROPOSED").length +
        (wizAnalysis?.environments || []).filter(e => e.status === "PROPOSED").length;
      setB(2, !wizAnalysis ? "LOCKED" : proposedN ? "PROVISIONAL" : "APPROVED",
        !wizAnalysis ? "NOT RUN"
          : `${(wizAnalysis.design_worlds || []).length} DESIGN LANGUAGES`
            + (proposedN ? ` · ${proposedN} PROPOSED` : " FOUND"));
      // Step 1 counts the interview itself (mock 2a) — answered = non-blank.
      // Cast the film: --hold border while anything stays uncast, --ok when
      // the whole read is cast (plan D4; existing badge classes carry it).
      const uncastN = uncastRecommendations(subjects).length;
      setB(3, !subjects.length && !uncastN ? "LOCKED"
        : uncastN ? "PROVISIONAL" : "APPROVED",
        !subjects.length && !uncastN ? "NONE YET"
        : `${subjects.length} CAST · ${uncastN} UNCAST`);
      setB(4, bible.is_default ? "LOCKED" : "APPROVED",
        bible.is_default ? "NOT DRAFTED" : `SAVED · REV ${bible.rev || 0}`);
      setB(5, samples.length ? "APPROVED" : "LOCKED",
        samples.length ? `${samples.length} SAMPLE${samples.length > 1 ? "S" : ""}`
                       : "NEEDS A SAVED BIBLE");
    } catch { /* badges are commentary — never block the wizard */ }
  };
  wizardStepBadges();

  // The look interview persists per production (user ruling 2026-08-01:
  // a refresh must never lose it): fields load from the server and every
  // change saves back — its answers then bind every bible draft.
  // One question per anchor, plus the three no anchor can hold (user
  // 2026-08-16 — "we now have duplicative entries"). The per-axis fields
  // live ON their anchor card now; the selectors are unchanged so every
  // reader below still finds them by id.
  const IV = { "#wiz-texture": "texture", "#wiz-palette": "palette",
               "#wiz-light": "light", "#wiz-medium": "medium",
               "#wiz-never": "never", "#wiz-notes": "notes" };
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
  // The words arrive after the anchor cards render, so the badge that
  // reads them has to be told. Only the NONE <-> IN WORDS half moves —
  // a card with pictures shows its count whatever the words say.
  const syncAnchorBadges = () => {
    for (const col of $$(".wiz-col[data-role]")) {
      const badge = $("[data-f=state]", col);
      if (!badge || /^\d+$/.test(badge.textContent.trim())) continue;
      const inWords = !!$("[data-f=words]", col)?.value.trim();
      badge.className = `badge ${inWords ? "APPROVED" : "LOCKED"}`;
      badge.textContent = inWords ? "IN WORDS" : "NONE";
    }
  };
  syncAnchorBadges();

  for (const id of Object.keys(IV))
    $(id)?.addEventListener("change", () => {
      saveInterview(); wizardStepBadges(); syncAnchorBadges();
    });

  // Two anchors answer from a known vocabulary rather than a sentence
  // (user-directed 2026-08-16). The input still holds the value — it is
  // hidden, and the button states what it holds. A catalogue NAME reads
  // better on the button than the directive it writes, so the button
  // shows the name on a match and the phrase itself otherwise.
  const bindPicker = (id, styles, opts) => {
    const btn = $(`#${id}-pick`), field = $(`#${id}`);
    if (!btn || !field) return;
    loadPlateShots();
    // A choice you cannot see is a choice you re-open the panel to check
    // (user 2026-08-16: "once a style is selected — show the card on the
    // main tab, under the selection button"). The chosen style reads on
    // the card itself: its plate, its name, its words.
    const sync = () => {
      const v = field.value.trim();
      // Exact match first; then the captured house card by prefix, because
      // its value is re-derived from the bible on every open and a bible
      // that gained a line would otherwise stop recognising its own answer
      // and report it as "In your own words" (user-caught 2026-08-16).
      const head = t => String(t).slice(0, 110);
      const hit = styles.find(x => x.value === v)
        || styles.find(x => x.key === "house" && x.value && v
             && (v.startsWith(head(x.value)) || x.value.startsWith(head(v))));
      btn.textContent = hit ? hit.name : (v ? "Change" : opts.empty);
      btn.classList.toggle("chosen", !!v);
      btn.title = v ? `Rides every render as: ${v}` : "";
      const col = $(`.wiz-col[data-role="${opts.uploadRole}"]`);
      $(".rs-chosen", col)?.remove();
      if (!v) return;
      const box = document.createElement("div");
      box.className = "rs-chosen rs-card" + (hit?.rich ? " rs-rich" : "");
      // B1: the SAME renderer as the catalogue cell, at card scale. If the
      // catalogue gains a field this gains it, or drops it deliberately,
      // in one place.
      box.innerHTML = hit
        ? styleCard(hit, { chosen: true })
        : `<span class="rs-name">In your own words</span>
           <span class="rs-desc">${esc(v)}</span>`;
      box.onclick = () => btn.click();
      // A frame opens full size rather than reopening the panel.
      $$("[data-lb]", box).forEach(img => img.onclick = e => {
        e.stopPropagation();
        const set = $$("[data-lb]", box);
        openLightbox(set.map(x => ({ src: x.dataset.lb, caption: x.alt })),
                     set.indexOf(img));
      });
      btn.after(box);
    };
    sync();
    // All three libraries are read from documents now (2026-08-22), so all
    // three load the same way rather than cinematography being special.
    const load = async () => {
      if (styles === RENDER_STYLES) { await loadRenderStyles(); await adoptHouseStyle(); }
      else if (styles === TEXTURE_STYLES) await loadTextureStyles();
      else if (styles === CINEMA_STYLES) await loadCinemaStyles();
    };
    load().then(sync);
    btn.onclick = async () => {
      await load();
      openStylePicker({
      ...opts, styles, current: field.value.trim(),
      onPick: v => {
        field.value = v; sync();
        saveInterview(); wizardStepBadges(); syncAnchorBadges();
      },
      });
    };
    return sync;
  };
  // Controls that belong to an anchor but are not its style travel into
  // its panel when it opens and go home when it closes (user 2026-08-16:
  // "only have the button on the main page").
  const travels = (sel) => ({
    extra: '<div class="rs-extra" data-f="extra"></div>',
    onOpen: (ov) => $("[data-f=extra]", ov)?.append($(sel)),
    onClose: () => {
      const host = $(sel);
      if (host) $(`.wiz-col[data-role="${host.dataset.home}"]`)?.append(host);
    },
  });
  for (const [sel, role] of [["#wiz-never-row", "BOARD_RENDERING_STYLE"]])
    if ($(sel)) $(sel).dataset.home = role;

  bindPicker("wiz-texture", TEXTURE_STYLES, {
    empty: "Choose a world texture",
    title: "World texture",
    definition: `World texture is <b>how far the world has travelled from
      new</b> — wear, patina, entropy. It is not the palette and not the
      light: those are the anchors either side of it.`,
    uploadRole: "WORLD_TEXTURE", uploadLabel: "World Texture",
    ownPlaceholder: "Describe how worn the world is",
  });
  bindPicker("wiz-medium", RENDER_STYLES, {
    empty: "Choose a rendering style",
    title: "Rendering style",
    definition: `A rendering style is <b>how a panel is drawn</b> — the medium,
      the mark, the finish. It is not mood, not light, not cinematography:
      those are set by the other anchors, and choosing a style here never
      touches them.`,
    uploadRole: "BOARD_RENDERING_STYLE", uploadLabel: "Board Rendering",
    ownPlaceholder: "Describe the medium and finish",
    ...travels("#wiz-never-row"),
  });
  bindPicker("wiz-light", CINEMA_STYLES, {
    empty: "Choose a cinematography look",
    title: "Cinematography",
    definition: `A cinematography grammar is <b>how the camera tells the
      story</b> — camera behaviour, lighting, composition, depth and
      movement. <b>This sets the production default, and it can be changed
      for any single render</b> — a panel can name a different grammar or
      refuse one entirely. It is not genre, and it is not the palette: the
      Color Palette anchor owns colour, and a panel states its own hour.
      Each grammar carries the <b>framings</b> it sanctions — real focal
      lengths and apertures — and a panel picks one of those on the
      breakdown, or overrules it with its own camera. A cinematographer
      picks whatever lens gets the shot.`,
    uploadRole: "CINEMATOGRAPHY_STYLE", uploadLabel: "Cinematography",
    ownPlaceholder: "Describe how the camera should see",
    onPicked: st => saveCineSetting({ key: st?.key || "" }),
  });

  await loadBibleEditor();
    /* One writer, two callers: Create saves the draft it just made, and Save
     writes an edit. A second copy of this is how the two would drift on
     what "saved" means — the band, the swatch gate and the status line all
     hang off it. */
  const saveBible = async ({ quietIfUnchanged = false } = {}) => {
    try {
      const text = $("#style-bible").value.trim();
      if (!text) { toast("The bible is empty — create it above, or paste content, before saving.", true); return false; }
      // Pressing Save having changed nothing is not a save. No revision
      // bump, no journal line, no toast claiming something happened.
      if (quietIfUnchanged && text === bibleSavedText) return true;
      const r = await api("/api/style-bible", { method: "PUT", json: { text } });
      bibleSavedText = text;
      $("#style-status").innerHTML = `<span class="badge LOCKED">REV ${r.rev}</span> saved`;
      updateBand();  // Breakdowns unlock themselves right now, visibly
      syncSwatchGen();  // the step-1 swatch gate arms itself right now too
      toast("Art Direction Bible saved — Breakdowns are open.");
      return true;
    } catch (err) { toast(err.message, true); return false; }
  };
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
/* E0 (RULE_PASS_2 E, ruled 2026-08-18): both rows drew with an em-dash
   and nothing else on every style anchor — two of six text rows saying
   nothing, drawn as structure. Never pad to three: a row with no
   jurisdiction is not drawn, and a plate with neither states it once. */
/* E2: `APPROVED ON SUPPLY` is a different fact from `APPROVED` — a
   captured entry and an authored one must not look identical (B6). */
const statusWord = r => r.status === "APPROVED" && r.status_reason === "ON SUPPLY"
  ? "APPROVED ON SUPPLY" : r.status;

function jurisRows(controls, notControls) {
  const on = (controls || []).filter(Boolean);
  const off = (notControls || []).filter(Boolean);
  if (!on.length && !off.length) {
    return `<div class="juris-none">NO JURISDICTION SET</div>`;
  }
  return (on.length ? `<div class="juris ok">CONTROLS ${esc(on.join(" · "))}</div>` : "")
    + (off.length ? `<div class="juris bad">NOT ${esc(off.join(" · "))}</div>` : "");
}

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
    <img src="/api/references/${r.id}/image?size=thumb" alt="${esc(r.id)}" loading="lazy">
    <div class="body">
      <div><span class="badge ${r.status}">${statusWord(r)}</span> <b>${esc(r.id)}</b></div>
      <div class="role">${esc(r.role)}</div>
      ${jurisRows(r.controls, r.does_not_control)}
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
  // User-caught 2026-08-24: "I cant edit and change Dark Ship refference
  // type." A tester filed a spaceship as CHARACTER_LIKENESS — the role the
  // walkthrough named — and nothing in the app could take it back. The
  // PATCH endpoint existed and no screen had ever called it, so the role
  // chosen at intake was permanent for the life of the reference.
  //
  // Re-scoping is not rejecting. REJECTED is a judgement on the IMAGE, and
  // a misfiled image was never the problem.
  {
    const rs = document.createElement("button");
    rs.className = "text-act"; rs.textContent = "Edit";
    rs.title = "Edit what this image GOVERNS — its role and jurisdiction. "
             + "The picture, its approval and its place in the library are "
             + "untouched.";
    rs.onclick = async () => {
      const res = await roleDialog({
        title: `Edit ${r.id}`,
        body: "The image does not change and its approval stands. What "
            + "changes is the job it does in future renders — a reference "
            + "controls only its own scope, so this is the whole of its "
            + "authority.",
        prefillHead: roleHead(r.role) || "SCENE_REFERENCE",
        prefillTitle: (String(r.role).split("—")[1] || "").trim(),
        confirmLabel: "Change role",
        // Jurisdiction facets belonged to the OLD family — "face, hair,
        // build" makes no sense once this is a vehicle. Shown prefilled
        // rather than silently carried or silently cleared, because both
        // of those are surprises the user finds out about in a render.
        fields: [
          { name: "controls", label: "Controls",
            value: (r.controls || []).join(", "),
            placeholder: "comma-separated — what this image DOES govern" },
          { name: "does_not_control", label: "Does not control",
            value: (r.does_not_control || []).join(", "),
            placeholder: "comma-separated — what it explicitly does not" },
        ],
      });
      if (!res) return;
      const split = v => String(v || "").split(",").map(x => x.trim()).filter(Boolean);
      try {
        await api(`/api/references/${r.id}/rescope`, {
          method: "POST",
          json: { role: res.role, controls: split(res.controls),
                  does_not_control: split(res.does_not_control) },
        });
        toast(`${r.id} now governs ${res.role}.`);
        renderReferences();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(rs);
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
    <div class="subj-imgs" data-f="imgs"><button type="button" class="subj-slot" data-f="add-photos" title="Add reference photos to ${esc(s.name.toUpperCase())} — choose them, look at them, then attach. Each becomes an approved ${esc(role)} — ${esc(s.name.toUpperCase())} reference.">+</button></div>
    <div class="subj-facts">${imgs.length} PHOTO${imgs.length === 1 ? "" : "S"} · ${esc(role)} — ${esc(s.name.toUpperCase())}${
      used ? ` · USED IN ${used} RENDER${used === 1 ? "" : "S"}` : ""}${
      opts.viewLink ? ` · <button type="button" class="text-act" data-f="view">VIEW IN REFERENCE</button>` : ""}</div>`;
  const imgHost = $("[data-f=imgs]", card);
  const slot = $(".subj-slot", card);
  imgs.forEach((r, i) => {
    const wrap = document.createElement("span");
    wrap.className = "subj-img";
    wrap.innerHTML = `<img src="/api/references/${esc(r.id)}/image?size=thumb" loading="lazy" alt="${esc(r.id)}">
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
  // The + used to BE a file input, so the OS picker arrived over the app
  // the instant it was touched — the jarring the user photographed
  // (2026-08-16). It opens the same tray casting uses: choose, look at
  // what you chose, then attach.
  $("[data-f=add-photos]", card).onclick = () => photoTrayModal(s, onChange);
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

// The unanchored register (canon pass R4, mock au-ref-register): a place
// with no reference has nothing to judge, so it is a ROW in a labelled
// table, not a card with an empty well — a card is for a thing with a
// picture. The register is the SCENES shelf's unfinished business and
// sits beneath its card grid. Locations stay DELIBERATELY not castable:
// subjects ride per panel appearance, places ride per scene coverage.
function buildUnanchoredRegister(locs) {
  const envOf = l => {
    const a = wizACache();
    const hit = (a?.environments || []).find(e =>
      (e.locations || []).some(x =>
        String(x).toUpperCase() === String(l.location).toUpperCase()));
    return hit?.name || "";
  };
  const reg = document.createElement("div");
  reg.className = "loc-register";
  reg.innerHTML = `
    <div class="loc-reg-head">
      <span class="mono loc-reg-label">UNANCHORED · FROM THE SCREENPLAY'S SLUGLINES</span>
      <span class="hint">these places are named in the script and have no imagery</span>
    </div>
    <div class="loc-reg-row loc-reg-cols mono">
      <span>PLACE</span><span>SCENES</span><span>ENVIRONMENT</span><span></span>
    </div>
    ${locs.map(l => `
    <div class="loc-reg-row">
      <span class="loc-reg-place">${esc(l.location)}</span>
      <span class="mono">${l.scenes || 0}</span>
      <span class="mono loc-reg-env">${esc(envOf(l).toUpperCase())}</span>
      <span class="loc-reg-act"><button type="button" class="text-act" data-loc="${esc(l.location)}">Add reference</button></span>
    </div>`).join("")}
    <div class="mono loc-reg-foot">ADD REFERENCE PREFILLS LOCATION_GEOMETRY — &lt;NAME&gt; · CASTING STAYS SUBJECTS-ONLY</div>`;
  reg.onclick = e => {
    const b = e.target.closest("[data-loc]");
    if (b) addReferenceDialog({ head: "LOCATION_GEOMETRY", title: b.dataset.loc });
  };
  return reg;
}

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
  $("[data-f=cast]", card).onclick = () => castModal(rec, onChange);
  return card;
}

// The photo tray, shared by casting and by an existing card (user
// 2026-08-16: "finish casting modal"). Files are CHOSEN and shown before
// anything uploads, which is the whole difference from a bare file input:
// the picker becomes something you reached for rather than something that
// happened to you, and what it picked is visible before it is written.
//
// `onAttach(files, say)` is the only thing the two callers disagree
// about — casting creates the card first and then attaches; an existing
// card just attaches.
function photoTray(host, { onPicked = null } = {}) {
  host.innerHTML = `<label class="subj-slot" title="Choose photos — nothing uploads yet">+
      <input type="file" accept="image/*" multiple data-f="files" class="hidden">
    </label>`;
  const fileIn = $("[data-f=files]", host);
  let picked = [];
  fileIn.onchange = () => {
    picked = [...fileIn.files];
    $$(".cast-thumb", host).forEach(t => t.remove());
    picked.forEach(f => {
      const img = document.createElement("img");
      img.className = "cast-thumb";
      img.src = URL.createObjectURL(f);
      img.alt = f.name;
      img.title = f.name;
      host.prepend(img);
    });
    onPicked?.(picked);
  };
  return { files: () => picked };
}

async function photoTrayModal(s, onDone) {
  const role = SUBJECT_ROLE_OF[s.kind] || "REFERENCE";
  const ov = document.createElement("div");
  ov.className = "modal-scrim";
  ov.innerHTML = `
    <div class="modal photos-modal" role="dialog" aria-modal="true">
      <div class="modal-title">Add photos — ${esc(s.name.toUpperCase())}</div>
      <p class="hint">Each becomes an approved
        <span class="mono">${esc(role)} — ${esc(s.name.toUpperCase())}</span>
        reference, grouped under this exact name. Choose them here; nothing
        uploads until you attach.</p>
      <div class="cast-thumbs" data-f="thumbs"></div>
      <div class="busy busy-inline" data-f="state" aria-live="polite"></div>
      <div class="modal-actions">
        <button class="ghost" data-f="cancel">Cancel</button>
        <button class="primary" data-f="ok" disabled>Attach</button>
      </div>
    </div>`;
  document.body.append(ov);
  const ok = $("[data-f=ok]", ov), stateEl = $("[data-f=state]", ov);
  const say = (msg, kind = "") => {
    stateEl.className = `busy busy-inline${kind ? " " + kind : ""}`;
    stateEl.innerHTML = kind === "work"
      ? `<span class="spinner"></span><span class="busy-label">${esc(msg)}</span>`
      : `<span class="busy-label">${esc(msg)}</span>`;
  };
  let busy = false;
  const close = () => ov.remove();
  $("[data-f=cancel]", ov).onclick = close;
  ov.addEventListener("mousedown", e => { if (e.target === ov && !busy) close(); });

  const tray = photoTray($("[data-f=thumbs]", ov), {
    onPicked: fs => {
      ok.disabled = !fs.length;
      ok.textContent = fs.length
        ? `Attach ${fs.length} photo${fs.length === 1 ? "" : "s"}` : "Attach";
    },
  });

  ok.onclick = async () => {
    const files = tray.files();
    if (!files.length || busy) return;
    busy = true; ok.disabled = true;
    try {
      for (let i = 0; i < files.length; i++) {
        say(`Attaching photo ${i + 1} of ${files.length}…`, "work");
        const fd = new FormData();
        fd.append("file", files[i]);
        await api(`/api/subjects/${s.id}/reference`, { method: "POST", body: fd });
      }
      toast(`${files.length} reference${files.length === 1 ? "" : "s"} added to ${s.name}.`);
      close();
      onDone?.();
    } catch (err) {
      // Some may already be in. Say so rather than implying none are.
      busy = false; ok.disabled = false;
      say(err.message, "bad");
    }
  };
}

// Casting opens a MODAL, not a file explorer (user 2026-08-16: "too
// jarring... instead of adding that to the list, it should open in a
// modal. Once you save it, the card goes where it is now").
//
// The old flow did two abrupt things: the button created the card with
// no chance to look at what the read proposed, and the card's `+` tile
// was a bare file input, so the OS picker came up over the app with
// nothing having been confirmed. Both facts belong in one place before
// anything is written: the identity the screenplay gave this subject,
// editable, and the photos, attached deliberately.
//
// Nothing is created until Cast is pressed, and the photos ride the same
// endpoint the card's own slot uses — one upload path, not a second.
/* E5 (RULE_PASS_2 E, ruled 2026-08-18): once the fields are populated,
   nothing distinguished a proposal from the user's own words — so someone
   who edits Identity, comes back and finds Traits untouched cannot tell
   whether they approved them or never looked. The same --ink-faint
   Courier marker Part D gives a read act name, cleared on first edit. */
const READ_MARK = ` <span class="read-mark mono">READ</span>`;

function castModal(rec, onDone) {
  const KINDS = ["CHARACTER", "VEHICLE", "PROP"];
  const kind = (rec.kind || "CHARACTER").toUpperCase();
  const ov = document.createElement("div");
  ov.className = "modal-scrim";
  ov.innerHTML = `
    <div class="modal cast-modal" role="dialog" aria-modal="true">
      <div class="modal-title">Cast ${esc(rec.name)}</div>
      <!-- E4 (RULE_PASS_2 E, ruled 2026-08-18): casting is deciding what
           someone LOOKS LIKE. The photos are the decision and the traits
           qualify it, so the tray leads and Kind — which came from the
           read and is rarely wrong — states itself rather than opening
           the modal with a dropdown. -->
      <div class="cast-kind mono" data-f="kind-line">${esc(kind)} · PROPOSED BY THE READ
        <button type="button" class="text-act" data-f="kind-change">Change</button></div>
      <label class="modal-field hidden" data-f="kind-wrap">Kind
        <select data-f="kind">${KINDS.map(k =>
          `<option${k === kind ? " selected" : ""}>${k}</option>`).join("")}</select>
      </label>

      <p class="hint">What the screenplay read proposed. Edit anything —
        the identity and traits ride in every prompt this subject appears
        in. Nothing is created until you cast it.</p>

      <div class="cast-photos">
        <span class="f-label">Reference photos <span class="hint">optional — each becomes an approved reference under this name</span></span>
        <div class="cast-thumbs" data-f="thumbs"></div>
      </div>

      <label class="modal-field">Identity${rec.subtitle ? READ_MARK : ""}
        <input type="text" data-f="subtitle" value="${esc(rec.subtitle || "")}"
               placeholder="e.g. DRIVER. COWBOY. LOYAL FRIEND.">
      </label>
      <label class="modal-field">Traits <span class="hint">one per line</span>${
        (rec.traits || []).length ? READ_MARK : ""}
        <textarea data-f="traits" rows="4"
          placeholder="20s. Cheerful under pressure.&#10;Scarred since the crash.">${
          esc((rec.traits || []).join(String.fromCharCode(10)))}</textarea>
      </label>

      <div class="busy busy-inline" data-f="state" aria-live="polite"></div>
      <div class="modal-actions">
        <button class="ghost" data-f="cancel">Cancel</button>
        <button class="primary" data-f="ok">Cast ${esc(rec.name)}</button>
      </div>
    </div>`;
  document.body.append(ov);

  const ok = $("[data-f=ok]", ov), cancel = $("[data-f=cancel]", ov);
  const stateEl = $("[data-f=state]", ov), thumbs = $("[data-f=thumbs]", ov);
  // The marker is a claim about THIS value; editing it makes it yours.
  for (const f of ["subtitle", "traits"]) {
    $(`[data-f=${f}]`, ov)?.addEventListener("input", e =>
      e.target.closest("label")?.querySelector(".read-mark")?.remove());
  }
  $("[data-f=kind-change]", ov).onclick = () => {
    $("[data-f=kind-line]", ov).classList.add("hidden");
    $("[data-f=kind-wrap]", ov).classList.remove("hidden");
  };
  let busy = false;
  const say = (msg, kind2 = "") => {
    stateEl.className = `busy busy-inline${kind2 ? " " + kind2 : ""}`;
    stateEl.innerHTML = kind2 === "work"
      ? `<span class="spinner"></span><span class="busy-label">${esc(msg)}</span>`
      : `<span class="busy-label">${esc(msg)}</span>`;
  };
  const close = () => ov.remove();
  cancel.onclick = close;
  ov.addEventListener("mousedown", e => { if (e.target === ov && !busy) close(); });

  // The same tray an existing card uses — one place where a photo is
  // chosen and looked at before it is written.
  const tray = photoTray(thumbs, {
    onPicked: fs => say(fs.length
      ? `${fs.length} photo${fs.length === 1 ? "" : "s"} ready — they upload when you cast.`
      : ""),
  });

  ok.onclick = async () => {
    if (busy) return;
    busy = true; ok.disabled = true;
    say("Creating the card…", "work");
    try {
      const created = await api("/api/subjects", { method: "POST", json: {
        name: rec.name,
        kind: $("[data-f=kind]", ov).value,
        subtitle: $("[data-f=subtitle]", ov).value.trim(),
        traits: $("[data-f=traits]", ov).value.split(String.fromCharCode(10))
          .map(t => t.trim()).filter(Boolean),
        source: "screenplay analysis" } });
      const picked = tray.files();
      for (let i = 0; i < picked.length; i++) {
        say(`Attaching photo ${i + 1} of ${picked.length}…`, "work");
        const fd = new FormData();
        fd.append("file", picked[i]);
        await api(`/api/subjects/${created.id}/reference`, { method: "POST", body: fd });
      }
      toast(`${rec.name} cast${picked.length
        ? ` with ${picked.length} photo${picked.length === 1 ? "" : "s"}` : ""} — its card is in the library.`);
      close();
      onDone?.();
    } catch (err) {
      // The card may already exist while a photo failed — say which half
      // got through rather than implying nothing happened.
      busy = false; ok.disabled = false;
      say(err.message, "bad");
    }
  };
  $("[data-f=subtitle]", ov).focus();
}

// Ask the screenplay something about ONE panel (user 2026-08-16: "a Scan
// Screenplay button that will rescan for information. A modal will pop up
// asking for information to scan for which the AI will use to get better
// info. In that modal, an Open Screenplay button will open the screenplay
// in a new tab").
//
// The ask leads, because a narrow question is the whole point — a second
// full re-draft is what the breakdown already had. Findings come back as a
// proposal: each carries the VERBATIM line it came from, so accepting one
// is reading evidence rather than trusting a model, and nothing changes
// until you accept. Every quote was checked against the text server-side;
// anything the screenplay did not literally say was dropped before it got
// here, and the count of drops is stated rather than hidden.
function scanScreenplayDialog({ specId, panelId, has, accept, acceptBrief = null,
                                brief = "" }) {
  const ov = document.createElement("div");
  ov.className = "modal-scrim";
  ov.innerHTML = `
    <div class="modal scan-modal" role="dialog" aria-modal="true">
      <div class="modal-title">Tell me about ${esc(panelId)}</div>
      <p class="modal-body">Any info provided will be considered during script
      rescan. What comes back is a proposal — the brief, and what the panel must
      show. Nothing changes until you accept it.</p>
      <label class="modal-field">In your own words
        <textarea data-f="ask" rows="5" placeholder="e.g. this should feel like the last moment before a door closes forever — Sal is still talking, the chamber is open, and Tom has just come out of the dark"></textarea>
      </label>
      <div class="modal-actions" style="margin-top:10px">
        <button class="ghost" data-f="open-sp"
          title="Open the screenplay in a new tab to read or copy from it">Open screenplay ↗</button>
        <span style="flex:1"></span>
        <button class="ghost" data-f="cancel">Cancel</button>
        <button class="primary" data-f="go">Consider this</button>
      </div>
      <div data-f="busy"></div>
      <div data-f="out"></div>
    </div>`;
  document.body.append(ov);
  const close = () => { document.removeEventListener("keydown", onKey); ov.remove(); };
  const onKey = e => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  ov.addEventListener("click", e => { if (e.target === ov) close(); });
  $("[data-f=cancel]", ov).onclick = close;
  $("[data-f=open-sp]", ov).onclick = () =>
    window.open("/api/screenplay/file", "_blank", "noopener");
  const ask = $("[data-f=ask]", ov);
  ask.focus();

  const out = $("[data-f=out]", ov);
  const go = $("[data-f=go]", ov);
  go.onclick = async () => {
    go.disabled = true;
    out.innerHTML = "";
    const busy = startBusy($("[data-f=busy]", ov),
      `Re-reading the screenplay for ${panelId}…`,
      "one text call — no image is generated");
    try {
      const r = await api(`/api/specs/${specId}/panels/${panelId}/scan`, {
        method: "POST", json: { ask: ask.value },
      });
      busy.done();
      const src = r.anchor?.matched
        ? `THE SCREENPLAY SCENE${r.anchor.location
            ? ` · ${esc(String(r.anchor.location).toUpperCase())}` : ""}`
        : "THE SHEET&rsquo;S OWN SCENE PROSE — THE SCREENPLAY SCENE WAS NOT LOCATED";
      const head = `<div class="mini mono">READ ${src} · ${esc(r.model || "")}${
        r.unverified_dropped
          ? ` · ${r.unverified_dropped} CLAIMED THE SCRIPT AND COULD NOT SHOW IT` : ""}</div>`;
      // Provenance is the whole trust model, so it is drawn, not implied:
      // a screenplay proposal shows the line it came from, a direction
      // proposal says plainly that it came from you.
      const findHtml = (f, i) => `
        <div class="scan-find" data-i="${i}">
          <span class="scan-from mono ${f.from === "screenplay" ? "sp" : "dir"}">${
            f.from === "screenplay" ? "THE SCREENPLAY SAYS" : "FROM WHAT YOU SAID"}</span>
          <div class="scan-detail">${esc(f.detail)}</div>
          ${f.quote ? `<blockquote class="scan-quote">${esc(f.quote)}</blockquote>` : ""}
          ${f.object ? `<button type="button" class="ghost" data-add="${esc(f.object)}"
            data-quote="${esc(f.quote)}">+ ${esc(f.object)}</button>`
            : `<span class="mini mono">CONTEXT — NOTHING TO ADD</span>`}
        </div>`;
      const briefHtml = (r.brief && acceptBrief && r.brief.trim() !== String(brief).trim())
        ? `<div class="scan-brief">
             <span class="scan-from mono dir">PROPOSED BRIEF</span>
             <div class="scan-detail">${esc(r.brief)}</div>
             ${r.brief_reason ? `<p class="mini">${esc(r.brief_reason)}</p>` : ""}
             <button type="button" class="ghost" data-f="use-brief">Use this brief</button>
           </div>` : "";
      if (!briefHtml && !r.finds.length) {
        out.innerHTML = `<div class="report"><b>Nothing to propose</b>
          <p class="mini">${esc(r.note || "The scene and what you said did not add anything this panel is missing.")}</p>
          ${head}</div>`;
        go.disabled = false;
        return;
      }
      out.innerHTML = `<div class="report">${head}
        ${briefHtml}
        <div class="scan-finds">${r.finds.map(findHtml).join("")}</div>
        ${r.note ? `<p class="mini">${esc(r.note)}</p>` : ""}</div>`;

      const useBrief = $("[data-f=use-brief]", out);
      if (useBrief) useBrief.onclick = async () => {
        useBrief.disabled = true;
        try { await acceptBrief(r.brief); useBrief.textContent = "✓ brief updated"; }
        catch (err) { useBrief.disabled = false; toast(err.message, true); }
      };

      $$("[data-add]", out).forEach(b => b.onclick = async () => {
        b.disabled = true;
        const prev = b.textContent;
        try {
          // The quote travels WITH the object: a screenplay-sourced object
          // is SCRIPT_EXPLICIT evidence against that line, a directed one
          // is USER_DIRECTED. Which it is was decided server-side.
          const added = await accept(b.dataset.add, b.dataset.quote || "");
          b.textContent = added ? `✓ ${b.dataset.add}` : "already required";
        } catch (err) {
          b.textContent = prev;
          b.disabled = false;
          toast(err.message, true);
        }
      });
      const already = has().map(x => String(x).toLowerCase());
      $$("[data-add]", out).forEach(b => {
        if (already.includes(b.dataset.add.toLowerCase())) {
          b.disabled = true;
          b.textContent = `already required · ${b.dataset.add}`;
        }
      });
      go.disabled = false;
      go.textContent = "Consider again";
    } catch (err) {
      busy.done();
      out.innerHTML = `<div class="report fail">${esc(err.message)}</div>`;
      go.disabled = false;
    }
  };
}


// An object with no matching reference has two answers, not one (user
// 2026-08-16: "in this dialogue I need to be able to select existing
// ref"). Uploading was the only door, so a plate the library already held
// had to be photographed again whenever the object's wording did not
// resemble its role. Resolves to a reference record, the string "new", or
// null if the user backed out.
//
// The plates lead, because choosing a reference is a thing you do by
// LOOKING — the same reason the plate viewer shows photographs rather
// than a list of ids.
function pickReferenceSource(obj, refs) {
  return new Promise(resolve => {
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    const cards = refs.map(r => `
      <button type="button" class="ref-pick" data-pick="${esc(r.id)}"
              title="${esc(r.role)}">
        <img src="/api/references/${esc(r.id)}/image?size=thumb" alt="" loading="lazy">
        <span class="ref-pick-id mono">${esc(r.id)}</span>
        <span class="ref-pick-role mono">${esc(String(r.role).toUpperCase())}</span>
      </button>`).join("");
    ov.innerHTML = `
      <div class="modal ref-pick-modal" role="dialog" aria-modal="true">
        <div class="modal-title">A reference for “${esc(obj)}”</div>
        <p class="modal-body">Nothing in the library is named closely enough to
        attach itself. Point this object at a plate you already have, or supply a
        new one.</p>
        <p class="mini mono">${refs.length} APPROVED PLATE${refs.length === 1 ? "" : "S"}
        · THE TICK RIDES THE NEXT TAKE — IT IS NOT A LASTING LINK</p>
        <div class="ref-pick-grid">${cards
          || '<span class="mini">the library has no approved plates yet</span>'}</div>
        <div class="modal-actions">
          <button class="ghost" data-f="new">Upload a new image instead</button>
          <button class="ghost" data-f="cancel">Cancel</button>
        </div>
      </div>`;
    document.body.append(ov);
    const done = v => { ov.remove(); document.removeEventListener("keydown", onKey); resolve(v); };
    const onKey = e => { if (e.key === "Escape") done(null); };
    document.addEventListener("keydown", onKey);
    ov.addEventListener("click", e => { if (e.target === ov) done(null); });
    $("[data-f=cancel]", ov).onclick = () => done(null);
    $("[data-f=new]", ov).onclick = () => done("new");
    $$("[data-pick]", ov).forEach(b => b.onclick = () =>
      done(refs.find(r => r.id === b.dataset.pick)));
  });
}

// Adding to the library is a dialog now (the intake row moved behind the
// button per ONE_LIBRARY_PLAN D2) — the vocabulary picker plus a file field.
// Callable from anywhere (user 2026-08-14: supply a reference right on the
// panels screen): `approve` skips the provisional step — deliberately
// supplying a reference for a named object IS the review — and `onDone`
// lets the calling view refresh itself instead of the library.
async function addReferenceDialog(prefill = {}, { approve = false, onDone = null } = {}) {
  const r = await roleDialog({
    title: "Add reference",
    body: approve
      ? "One image, one job. It enters the library APPROVED — you are supplying it deliberately; reject it later in Reference if it disappoints."
      : "One image, one job. It enters the library provisional; approve it to make it a canon anchor.",
    prefillHead: prefill.head || "CHARACTER_LIKENESS",
    prefillTitle: prefill.title || "",
    fields: [
      { name: "file", label: "Image", type: "file" },
      { name: "controls", label: "Controls", placeholder: "comma-separated — or click the chips" },
      { name: "does_not_control", label: "Does not control", placeholder: "e.g. costume, lighting, camera angle" },
      { name: "notes", label: "Notes", placeholder: "provenance — where it came from, what it anchors" },
    ],
    confirmLabel: approve ? "Add & approve" : "Add to library",
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
    let ref = await api("/api/references", { method: "POST", body: fd });
    if (approve) {
      ref = await api(`/api/references/${ref.id}/status`,
        { method: "POST", json: { status: "APPROVED" } });
    }
    toast(`${ref.id} added as ${ref.role} (${approve ? "approved" : "provisional"}).`);
    if (onDone) onDone(ref); else renderReferences();
  } catch (err) { toast(err.message, true); }
}

// What the render actually sees for one required object (user
// 2026-08-14, after a single rear-view GT40 plate produced weird
// renders): the full library anatomy for EVERY matching plate — role,
// jurisdiction, notes — plus a stated thin-anchor warning when only one
// plate matches, and Add another plate without leaving the view.
// A group of five plates need not ride as five (user ruling 2026-08-15):
// the viewer is where you SEE the photos, so it is where you choose which
// of them the render works from. `pick` is the current subset and
// `onPick` receives the new one; without them the viewer stays read-only.
function viewObjectReferences(obj, recs, addPrefill, onChanged,
                              { pick = null, onPick = null, onDetach = null } = {}) {
  const lbItems = recs.map(r => ({ src: `/api/references/${r.id}/image`,
                                   caption: `${r.id} — ${r.role}` }));
  const chosen = new Set(pick || recs.map(r => r.id));
  // What the selection was when the modal opened — Save has to know
  // whether there is anything to save (user 2026-08-16).
  const opened = [...chosen].sort().join(",");
  // Default to showing ONLY what the render works from (user 2026-08-15:
  // clicking an object's REF should show the plates selected for it, not
  // the whole library group). The rest stay one verb away — a set you
  // cannot see is a set you cannot widen again.
  const narrowed = chosen.size < recs.length;
  return modal({
    custom: `
      <div class="modal-title">Reference — ${esc(obj)}</div>
      <p class="modal-body mini mono">${recs.length} PLATE${recs.length === 1 ? " MATCHES" : "S MATCH"} THIS OBJECT${
        recs.length === 1 ? " · THIN ANCHOR — ONE ANGLE STEERS EVERY RENDER" : ""} · ${onPick
        ? `<span data-f="vr-count">${chosen.size} OF ${recs.length} RIDE THE NEXT RENDER</span> · UNTICK ONE TO SPEND FEWER OF THE FOURTEEN`
        : "ALL ATTACH WHEN ITS GROUP IS CHECKED"}</p>
      <!-- E1 (RULE_PASS_2 E, ruled 2026-08-18): the modal exists to answer
           "do these plates cover the angles?" — a COMPARISON, which is why
           the lightbox does not solve it. The plates are the surface: one
           row at full width, own ratios, md tier. USE is a tick ON the
           plate, because what rides the render is a property of the
           picture. Two Courier roles under each, and notes go behind the
           plate's own click, where the lightbox caption already lives. -->
      <div class="vr-strip${narrowed ? " vr-only" : ""}" data-f="vr-grid">
        ${recs.map((r, i) => `
          <figure class="vr-plate ${esc(r.status)}${onPick && !chosen.has(r.id) ? " vr-off" : ""}" data-card="${esc(r.id)}">
            <span class="vr-frame">
              <img src="/api/references/${esc(r.id)}/image?size=md" data-lb="${i}" alt="${esc(r.id)}" loading="lazy">
              ${onPick ? `<label class="vr-use" title="Attach this plate to the next render">
                <input type="checkbox" data-use="${esc(r.id)}" ${chosen.has(r.id) ? "checked" : ""}></label>` : ""}
            </span>
            <figcaption>
              <div class="vr-id mono">${esc(r.id)} · ${esc(r.role)} · ${esc(r.status)}</div>
              ${jurisRows(r.controls, r.does_not_control)}
            </figcaption>
          </figure>`).join("")}
      </div>
      <div class="modal-actions" style="margin:12px 14px">
        <button class="ghost" data-f="vr-add" title="Opens the add-reference widget prefilled with this group's role and title, so the new plate joins the same group and attaches with it">Add another plate</button>
        ${narrowed ? `<button type="button" class="ghost" data-f="vr-all">Show all ${recs.length}</button>` : ""}
        ${onDetach ? `<button class="ghost" data-f="vr-detach"
          title="Removes the reference FROM THIS OBJECT only. The object goes back to + REF so you can point it somewhere else; the plates themselves are untouched, stay in the library, and stay attached to every other object that names them.">Not this object's reference</button>` : ""}
        <span style="flex:1"></span>
        <button class="ghost" data-f="vr-close">Close</button>
      </div>`,
    mount: (ov, done) => {
      $$("[data-lb]", ov).forEach(img => img.onclick = () =>
        openLightbox(lbItems, +img.dataset.lb));
      const grid = $("[data-f=vr-grid]", ov);
      const allBtn = $("[data-f=vr-all]", ov);
      if (allBtn) allBtn.onclick = () => {
        const only = grid.classList.toggle("vr-only");
        allBtn.textContent = only
          ? `Show all ${recs.length}`
          : `Show only the ${chosen.size} that ride`;
      };
      const closeBtn = $("[data-f=vr-close]", ov);
      let dirty = false;
      if (onPick) {
        const countEl = $("[data-f=vr-count]", ov);
        // The change SHOWS immediately — the count moves and the unpicked
        // card dims, so the choice is visibly working. But it COMMITS on
        // Save (user 2026-08-16: "if I unselect reference in a ref panel
        // ... the close button should turn to Save and saving closes the
        // modal"). Committing on every tick meant the panel behind kept
        // redrawing under an open modal, and there was no moment that felt
        // like a decision.
        const sayDirty = () => {
          dirty = [...chosen].sort().join(",") !== opened;
          closeBtn.textContent = dirty ? "Save" : "Close";
          closeBtn.classList.toggle("primary", dirty);
          closeBtn.classList.toggle("ghost", !dirty);
          closeBtn.title = dirty
            ? "Keep this selection — only the ticked plates ride the next render"
            : "";
        };
        $$("[data-use]", ov).forEach(box => box.onchange = () => {
          box.checked ? chosen.add(box.dataset.use) : chosen.delete(box.dataset.use);
          $(`[data-card="${box.dataset.use}"]`, ov)
            ?.classList.toggle("vr-off", !box.checked);
          if (countEl) countEl.textContent =
            `${chosen.size} OF ${recs.length} RIDE THE NEXT RENDER`;
          sayDirty();
        });
      }
      closeBtn.onclick = () => {
        if (dirty && onPick) onPick([...chosen]);
        done(null);
      };
      $("[data-f=vr-add]", ov).onclick = () => {
        done(null);
        addReferenceDialog(addPrefill, { approve: true, onDone: onChanged });
      };
      // The match is a guess about wording and the production overrules it.
      // Nothing is deleted: the plates stay in the library and stay
      // attached to every other object that really does name them.
      const detach = $("[data-f=vr-detach]", ov);
      if (detach) detach.onclick = () => { done(null); onDetach(); };
    },
  });
}

const SHELVES = [
  { key: "STYLE", name: "STYLE", ride: "RIDES ALONG — EVERY RENDER, AUTOMATICALLY",
    note: "", count: n => `${n.total} ANCHOR${n.total === 1 ? "" : "S"} · ${n.roles} ROLE${n.roles === 1 ? "" : "S"}` },
  { key: "SUBJECT", name: "SUBJECTS", ride: "RIDES ALONG — WHEN ITS SUBJECT APPEARS ON A PANEL",
    note: "cast in Production Design step 3 — same cards, this is where they live",
    count: n => `${n.cast} CAST · ${n.uncast} UNCAST` },
  { key: "SCENE", name: "SCENES", ride: "RIDES ALONG — WHEN A BOARD COVERS ITS SCENE",
    note: "promoted takes, light studies, crops of environments",
    count: n => `${n.total} ANCHOR${n.total === 1 ? "" : "S"}` },
];

async function renderReferences() {
  useTemplate("tpl-references");
  _roleCtx = null;  // fresh groups after every library change
  const [refs, subjects, locData] = await Promise.all([
    api("/api/references"), api("/api/subjects"),
    // The screenplay's own location register — deterministic slugline
    // parse, no model. A place the script names belongs in this library's
    // search even before anyone photographs it (user 2026-08-08).
    api("/api/screenplay/locations").catch(() => ({ locations: [] }))]);
  const screenplayLocs = locData.available ? (locData.locations || []) : [];

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
  const envOfLoc = (() => {
    const a = wizACache();
    const map = {};
    (a?.environments || []).forEach(e =>
      (e.locations || []).forEach(l => { map[String(l).toUpperCase()] = e.name; }));
    return loc => map[String(loc).toUpperCase()] || "";
  })();
  const matchesLoc = l => {
    const needle = q.v.trim().toUpperCase();
    if (!needle) return true;
    return [l.location, envOfLoc(l.location)]
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
        // The SCENES twin of the uncast pattern (user 2026-08-08): the
        // screenplay names places the library holds nothing for, and the
        // search said NOTHING instead of "not yet anchored". A location is
        // anchored when a SCENE-shelf ref's titled-role suffix matches it
        // — the panel matcher's own two-way containment, so this shelf and
        // the panel pre-check can never disagree.
        let unanchored = [];
        if (shelf.key === "SCENE" && screenplayLocs.length) {
          const norm = v => String(v).toUpperCase().trim();
          const twoWay = (a, b) => {
            const x = norm(a), y = norm(b);
            return !!x && !!y && (x.includes(y) || y.includes(x));
          };
          const sceneAnchors = refs.filter(r =>
            bucketOfRef(r) === "SCENE" && r.status !== "REJECTED");
          const anchorNames = sceneAnchors.map(r =>
            String(r.role).split("—")[1]?.trim() || "");
          unanchored = screenplayLocs.filter(l =>
            !anchorNames.some(nm => twoWay(nm, l.location)));
        }
        const shownUnanchored = unanchored.filter(matchesLoc);
        countText = shelf.count({ total: shelfRefs.length, roles: roleCount })
          + (unanchored.length
             ? ` · ${unanchored.length} LOCATION${unanchored.length === 1 ? "" : "S"} UNANCHORED`
             : "");
        // A design language is one swatch (PALETTE_GROUPS, extended to this
        // shelf 2026-08-08): 19 swatch cards said in a wall what three
        // ramps say in a strip. Quarantined swatches keep the card, like
        // the SUBJECTS shelf's rule — governance stays visible.
        const isSwatch = r => roleHead(r.role) === "COLOR_PALETTE"
          && !!swatchNotes(r.notes).hex && r.status !== "REJECTED";
        const swatchRefs = shelf.key === "STYLE" ? shelfRefs.filter(isSwatch) : [];
        const cardRefs = shelfRefs.filter(r => !swatchRefs.includes(r));
        if (swatchRefs.length) {
          // R5: the shelf states groups and swatches (mock au-ref-style-shelf).
          const langs = new Set(swatchRefs.map(r => swatchNotes(r.notes).language)
            .filter(Boolean));
          countText = `${langs.size || 1} GROUP${langs.size === 1 ? "" : "S"} · `
            + `${swatchRefs.length} SWATCHES`
            + (cardRefs.length ? ` · ${cardRefs.length} PLATES` : "");
        }
        fill = grid => {
          if (swatchRefs.length) {
            const byLang = new Map();
            const rows = [];
            for (const r of swatchRefs) {
              const sw = { ...swatchNotes(r.notes), ref_id: r.id,
                           approved: r.status === "APPROVED" };
              if (!sw.language) {
                rows.push({ label: sw.name || r.id, swatches: [sw] });
                continue;
              }
              if (!byLang.has(sw.language)) {
                const row = { label: sw.language, swatches: [] };
                byLang.set(sw.language, row);
                rows.push(row);
              }
              byLang.get(sw.language).swatches.push(sw);
            }
            // R5 (canon pass, mock au-ref-style-shelf): the ramps ARE the
            // shelf — name and count above, Open group beneath; plates
            // live behind the viewer each group already opens.
            const strip = document.createElement("div");
            strip.className = "pal-shelf pal-shelf-is-shelf";
            rows.forEach(row => {
              const ordered = rampOrder(row.swatches);
              const pend = row.swatches.filter(sw => !sw.approved).length;
              const el = document.createElement("div");
              el.className = "pal-row";
              el.innerHTML = `
                <p class="sw-ramp-label">
                  <span class="lang">${esc(row.label.toUpperCase())}</span>
                  <span class="hero mono${pend ? " prov" : ""}">${pend
                    ? `${pend} PROVISIONAL` : row.swatches.length}</span>
                </p>
                <div class="sw-ramp">${ordered.map(sw =>
                  `<i data-ref="${esc(sw.ref_id)}" style="flex:${sw.hero ? 2 : 1};${bandStyle(sw)}"></i>`).join("")}</div>
                <button type="button" class="text-act pal-open">Open group</button>`;
              const open = e => {
                const hit = e.target.closest?.("i");
                openSwatchViewer([{ language: row.label, swatches: row.swatches }],
                  { focusRef: hit?.dataset.ref,
                    approved: row.swatches.every(sw => sw.approved),
                    refresh: renderReferences, onChange: () => {} })
                  .then(renderReferences);
              };
              $(".sw-ramp", el).style.cursor = "pointer";
              $(".sw-ramp", el).onclick = open;
              $(".pal-open", el).onclick = open;
              strip.append(el);
            });
            grid.before(strip);
          }
          // Quarantined swatches keep their cards, below, under a stated
          // label — a verdict happens where the proposal is.
          const isQuarantinedSwatch = r => roleHead(r.role) === "COLOR_PALETTE"
            && !!swatchNotes(r.notes).hex && r.status === "REJECTED";
          const qRefs = shelf.key === "STYLE"
            ? cardRefs.filter(isQuarantinedSwatch) : [];
          const plainRefs = cardRefs.filter(r => !qRefs.includes(r));
          const lb = plainRefs.map(r => ({
            src: `/api/references/${r.id}/image`,
            caption: `${r.id} — ${r.role} (${r.status})` }));
          plainRefs.forEach((r, i) => grid.append(buildRefCard(r, lb, i)));
          if (qRefs.length) {
            const q_ = document.createElement("div");
            q_.className = "shelf-quarantine";
            q_.innerHTML = `<div class="mono loc-reg-label">QUARANTINED · AWAITING A VERDICT</div>
              <div class="ref-grid" data-f="qgrid"></div>
              <div class="mono loc-reg-foot">A VERDICT HAPPENS WHERE THE PROPOSAL IS — THESE KEEP THEIR CARDS UNTIL RULED</div>`;
            const qlb = qRefs.map(r => ({
              src: `/api/references/${r.id}/image`,
              caption: `${r.id} — ${r.role} (${r.status})` }));
            qRefs.forEach((r, i) => $("[data-f=qgrid]", q_).append(buildRefCard(r, qlb, i)));
            grid.after(q_);
          }
          if (shownUnanchored.length)
            grid.after(buildUnanchoredRegister(shownUnanchored));
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
      if (!grid.children.length && !$(".pal-shelf", section))
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

const WIZ_HELP = {
  // User 2026-08-16: "'Each becomes a bible section' — who cares. What
  // does it affect in panel generation?" So both answer that, from what
  // the code actually does: bible.render_context() selects these
  // sections and generate._style_context() puts them in the prompt.
  langs: "<b>A named visual world, and the rules for drawing it.</b> "
    + "GRM Order, the Resistance, Terra Nova — each one collects the "
    + "materials, shapes, wear and design intent that belong to it.<br><br>"
    + "<b>What it does to a render:</b> a breakdown ticks the languages "
    + "that apply to it, and those sections are pasted into the prompt of "
    + "every panel on that sheet. A panel can override the sheet and take "
    + "a different one. Nothing else in the bible rides — an unticked "
    + "language is invisible to the render.<br><br>"
    + "That is why they are worth naming carefully: a panel can only look "
    + "like the languages it was given.",
  envs: "<b>The palette, light and atmosphere a place carries</b> — and "
    + "only those. Not its culture, not its props: those are the design "
    + "language's job.<br><br>"
    + "<b>What it does to a render:</b> a breakdown names its environment "
    + "and that entry rides every panel on the sheet, or a panel names its "
    + "own and overrides it. Unlike design languages, <b>environments never "
    + "infer</b> — one you do not select is simply not carried, so a "
    + "breakdown with no environment gets none.<br><br>"
    + "Locations map to environments: each location inherits its "
    + "environment's rules, which is how twenty locations stay consistent "
    + "without twenty descriptions.",
};


// The `?` card, bound wherever a surface renders one. The stage-03 editor
// has its own copy of this from before there was a second caller; this is
// the shared one, and a third surface should use it rather than grow a
// third.
function bindHelpButtons(root, texts) {
  const close = () => {
    $$(".q-card").forEach(c => c.remove());
    $$(".q-help[aria-expanded=true]").forEach(
      b => b.setAttribute("aria-expanded", "false"));
  };
  $$(".q-help", root).forEach(btn => {
    if (!texts[btn.dataset.help]) return;
    btn.setAttribute("aria-expanded", "false");
    btn.onclick = e => {
      e.preventDefault();
      e.stopPropagation();
      const open = btn.getAttribute("aria-expanded") === "true";
      close();
      if (open) return;
      const card = document.createElement("div");
      card.className = "q-card";
      card.innerHTML = texts[btn.dataset.help];
      document.body.append(card);
      const r = btn.getBoundingClientRect();
      card.style.top = `${r.bottom + window.scrollY + 8}px`;
      card.style.left = `${Math.min(r.left + window.scrollX,
        window.innerWidth - card.offsetWidth - 16)}px`;
      btn.setAttribute("aria-expanded", "true");
    };
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".q-card") && !e.target.closest(".q-help")) close();
  });
  window.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
}

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
  // The board's shape is a STATED input, from the same vocabulary the
  // blank-sheet form offers (user-hit 2026-08-07).
  // C1 (RULE_PASS_2 C): one door. The board's shape is a STATED input
  // (user-hit 2026-08-07).
  const autoBtype = $("#spec-auto-btype");
  /* THE DOOR'S SOURCE, in one variable rather than inferred in three
     places. It is exactly one of: a picked scene or location, a pasted
     section, or free text in the brief field — and every control that
     cares (the two rows, the disable state, the verb, the submit) reads
     these. `pasting` is explicit because the search list can now switch
     the door into paste mode while the box is still empty, and "has text"
     could not tell that apart from "not chosen yet". */
  let scenePick = null;        // {kind, label, brief, heading?, line?, scenes?}
  let pasting = false;
  let clearPick = () => {};    // wired by the search block below
  window.__scenePick = () => scenePick;
  // One draft per door — the two hold different fields, and a single key
  // would restore half a form into the wrong one.
  persistForm("autoSpecDraft", ["spec-auto-id", "spec-auto-subject",
                                "spec-auto-source", "spec-auto-panels",
                                "spec-auto-mode", "spec-auto-btype",
                                "spec-auto-provider"]);
  persistForm("blankSpecDraft", ["spec-new-id", "spec-new-subject",
                                 "spec-new-mode", "spec-new-btype"]);

  await fillNarrativeSelect($("#spec-auto-provider"));

  // The instruction example speaks this production's screenplay, never a
  // hardcoded film's (user ruling 2026-08-01); the same fetch powers the
  // Create Breakdown pre-population.
  /* One composer per kind of board, shared by the deep link from the
     coverage map and by the scene search below it. Two copies of this
     drifted once already — the search wrote its own scene sentence while
     the deep link wrote another, and a brief is not decoration: it is what
     the deterministic scene anchor matches on. */
  const titleCaseName = t => String(t).toLowerCase()
    .replace(/(^|[\s/#-])([a-z])/g, (m, a, b) => a + b.toUpperCase());
  const sceneBrief = (rec, scene) =>
    `${scene.heading} — a scene board for this single scene at `
    + `${titleCaseName(rec?.location || scene.location || "")}. Extract the `
    + "set, dressing, props and atmosphere the script gives this scene.";
  const locationBrief = rec => {
    const heads = (rec.scene_list || []).map(x => x.heading);
    const n = rec.scenes ?? heads.length;
    return `${titleCaseName(rec.location)} — `
      + `${rec.int_ext ? "an " + rec.int_ext + " " : "a "}location board covering `
      + `the ${n} scene${n === 1 ? "" : "s"} the script sets there`
      + (heads.length ? `: ${heads.slice(0, 4).join("; ")}`
        + (heads.length > 4 ? ` (+${heads.length - 4} more)` : "") : "")
      + ". Focus on the location itself — its set, dressing and atmosphere "
      + "as the script establishes them.";
  };

  Promise.all([api("/api/screenplay/locations"), api("/api/specs")])
    .then(([d, allSpecs]) => {
      const locs = d.locations || [];
      const titleCase = t => String(t).toLowerCase()
        .replace(/(^|[\s/#-])([a-z])/g, (m, a, b) => a + b.toUpperCase());

      /* FIND A SCENE — a real search, not a datalist (user, 2026-08-22:
         "Find a scene needs to be GOOD. If I type in Terra Nova, or Terra,
         it will return all scenes with the name Terra in it").

         A native <datalist> filters however the browser feels like it —
         prefix in some, substring in others — cannot rank, and cannot show
         that TERRA NOVA is a location holding nine scenes. So the matching
         is ours: every typed word must appear somewhere in the heading or
         its location, in any order, so "terra bridge" finds
         "INT. TERRA NOVA BRIDGE - NIGHT".

         LOCATIONS lead the results, because "Terra Nova" is usually a
         request for the place rather than one scene in it — and picking a
         location composes a location board over all of its scenes, while
         picking a scene composes a single-scene board. Both write the
         brief, which is what the scene anchor matches on. */
      const sceneIn = $("#spec-auto-subject");   // the brief IS the search
      const hits = $("#spec-auto-scene-hits");
      const note = $("#spec-auto-scene-note");

      const seenHead = new Set();
      const scenes = locs.flatMap(l => (l.scene_list || []).map(sc => ({
        heading: String(sc.heading || "").replace(/\s+/g, " ").trim(),
        line: sc.line, loc: l })))
        .filter(x => x.heading && !seenHead.has(x.heading)
                     && seenHead.add(x.heading));

      const lc = t => String(t || "").toLowerCase();
      const search = q => {
        const words = lc(q).split(/\s+/).filter(Boolean);
        if (!words.length) return [];
        const hitsAll = words.every.bind(words);
        const out = [];
        for (const l of locs) {
          const hay = lc(l.location);
          if (hitsAll(w => hay.includes(w))) {
            out.push({ kind: "loc", loc: l, label: l.location,
                       sub: `${l.scenes} scene${l.scenes === 1 ? "" : "s"}` });
          }
        }
        for (const sc of scenes) {
          const hay = lc(sc.heading + " " + sc.loc.location);
          if (hitsAll(w => hay.includes(w))) {
            out.push({ kind: "scene", loc: sc.loc, scene: sc,
                       label: sc.heading, sub: "one scene" });
          }
        }
        return out;
      };

      let marked = -1;
      const closeHits = () => {
        if (hits) { hits.hidden = true; hits.innerHTML = ""; }
        marked = -1;
      };
      /* What the pick SAVES (user, 2026-08-22: "a reference is saved to
         that page and section including the scene name"). A scene carries
         the line its slugline sits on, so Scan Screenplay goes straight
         there instead of working out which scene the brief meant — which
         has landed on the wrong one twice. A location has no single line,
         so it keeps the matched-by-name path, which is what a location
         board wants anyway. */
      const showPick = () => {
        if (note) {
          note.textContent = !scenePick
            ? (scenes.length
               ? `${scenes.length} SLUGLINES ACROSS ${locs.length} LOCATIONS`
               : "NO SLUGLINES — UPLOAD A SCREENPLAY, OR DESCRIBE THE BOARD")
            : scenePick.kind === "scene"
              ? `SCENE SAVED · LINE ${scenePick.line + 1}`
              : `LOCATION SAVED · ${scenePick.scenes} SCENE`
                + (scenePick.scenes === 1 ? "" : "S");
          note.classList.toggle("scene-ref", !!scenePick);
        }
        // The heading is IN the field now, so the row below states only
        // what the field cannot: where the scan lands, and how exactly.
        const lab = $("#spec-auto-picked-lab");
        const pnote = $("#spec-auto-picked-note");
        if (scenePick && lab && pnote) {
          lab.firstChild.nodeValue = scenePick.kind === "scene"
            ? "The scene\n                " : "The location\n                ";
          pnote.textContent = scenePick.kind === "scene"
            ? `READ EXACTLY — LINE ${scenePick.line + 1}`
            : `MATCHED BY NAME — ${scenePick.scenes} SCENE`
              + (scenePick.scenes === 1 ? "" : "S");
        }
        syncAlternatives();
      };
      // Two questions, two functions: typing over the title DROPS the
      // pointer and leaves the words alone, while removing the selection
      // empties the field as well. Conflating them meant the field kept a
      // title that was no longer selected.
      const dropPick = () => {
        scenePick = null;
        // The brief belongs to the selection: a hand-edited one that
        // outlived its scene would be sent, unseen, with the next pick.
        const box = $("#spec-auto-brief");
        if (box) box.value = "";
        showPick();
      };
      clearPick = () => {
        dropPick();
        if (sceneIn) { sceneIn.value = ""; sceneIn.focus(); }
        closeHits();
        syncAlternatives();
      };

      const choose = row => {
        /* The two standing rows at the head of the list are the door's
           source switch (user, 2026-08-22) — with a selection made, the
           paste row is not on screen, so this list is the only way to
           reach it. */
        if (row.kind === "none") { clearPick(); return; }
        if (row.kind === "paste") {
          dropPick();
          if (sceneIn) sceneIn.value = "";
          pasting = true;
          closeHits();
          syncAlternatives();
          $("#spec-auto-source")?.focus();
          return;
        }
        /* Only the TITLE lands in the field (user, 2026-08-22: "whatever
           lands in that What should I get field is awkward — just put the
           scene title in there"). The composed brief is still what the
           scan asks for and what the anchor matches on, so it moves to
           the row below, where it is editable and visibly attached to the
           scene it came from. */
        scenePick = row.kind === "scene"
          ? { kind: "scene", label: row.scene.heading,
              heading: row.scene.heading, line: row.scene.line,
              brief: sceneBrief(row.loc, row.scene) }
          : { kind: "loc", label: row.loc.location,
              scenes: row.loc.scenes ?? (row.loc.scene_list || []).length,
              brief: locationBrief(row.loc) };
        if (sceneIn) sceneIn.value = scenePick.label;
        const box = $("#spec-auto-brief");
        if (box) box.value = scenePick.brief;
        showPick();
        const bt = $("#spec-auto-btype");
        if (bt && !bt.dataset.touched) {
          bt.value = row.kind === "scene" ? "SCENE" : "LOCATION";
        }
        const id = $("#spec-auto-id");
        if (id && !id.value.trim()) {
          const base = slugSpecId(row.loc?.location || row.label)
            .replace(/^_+|_+$/g, "").slice(0, 40) || "BOARD";
          id.value = `${base}_V001`;
        }
        closeHits();
      };

      /* A composed brief is not a query (user, 2026-08-22: "if I pick a
         scene and then click into the field I get strange text"). Picking
         writes a 150-character sentence into this field; focusing it then
         searched for that sentence, found nothing, and shouted the whole
         brief back in caps.

         Length is the honest test rather than a "was picked" flag: a
         search query is short, and the moment the field holds a written
         brief — picked or typed — there is nothing to look up. Clearing
         it and typing `terra` searches again. */
      const QUERY_MAX = 80;
      const isQuery = v => {
        const t = String(v || "").trim();
        return t.length > 0 && t.length <= QUERY_MAX;
      };

      /* The head of the list is the door's SOURCE SWITCH (user,
         2026-08-22). `None` drops the selection; `Paste a section` turns
         the door over to the paste box and takes the search out of play.
         They stand above the matches because with a selection made the
         paste row is off screen, and a switch you cannot reach is not
         one. */
      const STANDING = [
        { kind: "none", label: "None",
          sub: "describe the board yourself" },
        { kind: "paste", label: "Paste a section",
          sub: "the screenplay is not read" },
      ];

      let found = [];
      const draw = () => {
        if (!hits || !sceneIn) return;
        if (!isQuery(sceneIn.value)) { closeHits(); return; }
        const matches = search(sceneIn.value).slice(0, 40);
        // Nothing to show and nothing selected is the no-match case, which
        // says nothing at all. With a selection made, the list opens even
        // on no matches — it is the only way back out of the selection.
        if (!matches.length && !scenePick) { closeHits(); return; }
        found = STANDING.concat(matches);
        const row = (r, i) => `
          <button type="button" class="scene-hit${
            r.kind === "loc" ? " is-loc" : ""}${
            r.kind === "none" || r.kind === "paste" ? " is-act" : ""}"
            data-i="${i}" role="option">
            <span class="scene-hit-label">${esc(r.label)}</span>
            <span class="scene-hit-sub mono">${esc(r.sub)}</span>
          </button>`;
        // The count line sits BELOW the two switches and above the
        // matches, because it describes the matches and neither switch is
        // in the screenplay.
        hits.innerHTML = STANDING.map(row).join("")
          + (matches.length
             ? `<p class="scene-ask mono">${matches.length} IN THE
                SCREENPLAY — PICKING ONE SAVES ITS PLACE FOR THE SCAN</p>`
             : "")
          + matches.map((r, i) => row(r, i + STANDING.length)).join("");
        hits.hidden = false;
        marked = -1;
        $$(".scene-hit", hits).forEach(b =>
          b.onclick = () => choose(found[+b.dataset.i]));
      };

      /* The search runs when the SUBMIT is pressed, not while typing (user,
         2026-08-22). Results appearing under the caret interrupted writing
         a brief, which is the commoner act — so the door asks the question
         at the moment it is about to spend money instead: "you typed
         `terra`, and the screenplay has seven places called that — did you
         mean one of them?"

         Pressing it again drafts. So does choosing a result, or saying use
         what I typed: the question is asked once per brief, never as a
         gate you have to argue with. */
      /* The pointer may not outlive the TITLE it came from: type over
         the field and the saved scene goes with it, rather than quietly
         aiming the scan somewhere else. Editing the brief below is not
         that — the brief is the ask, the title is the reference, and they
         are two fields now precisely so one can change without the
         other. */
      showPick();

      if (sceneIn) {
        sceneIn.addEventListener("input", () => {
          if (scenePick) dropPick();
          draw();
          syncAlternatives();
        });
        sceneIn.addEventListener("focus", draw);
        sceneIn.addEventListener("keydown", e => {
          if (hits?.hidden || !found.length) return;
          const rows = $$(".scene-hit", hits);
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            marked = (marked + (e.key === "ArrowDown" ? 1 : -1) + rows.length)
                     % rows.length;
            rows.forEach((r, i) => r.classList.toggle("on", i === marked));
            rows[marked]?.scrollIntoView({ block: "nearest" });
          } else if (e.key === "Enter" && marked >= 0) {
            e.preventDefault();
            choose(found[marked]);
          } else if (e.key === "Escape") {
            closeHits();
          }
        });
        document.addEventListener("click", e => {
          if (!hits?.contains(e.target) && e.target !== sceneIn) closeHits();
        });
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
      // The same branch that writes the brief knows which it is, so the
      // control arrives already saying what the click meant.
      if (autoBtype && !autoBtype.dataset.touched) {
        autoBtype.value = scene ? "SCENE" : "LOCATION";
      }
      const promptEl = $("#spec-auto-subject");
      if (!promptEl || promptEl.value.trim()) return;
      promptEl.value = scene ? sceneBrief(rec, scene)
        : rec ? locationBrief(rec)
        : `${titleCase(locHint)} — the scenes the script sets there. Focus on `
          + "the location's set, dressing and atmosphere as established.";
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
  // Both doors carry a board type — it is a property of the SHEET, not of
  // how the sheet was made — so both get filled. Filling only one left the
  // blank door's select empty and its sheets untyped.
  for (const sel of ["#spec-auto-btype", "#spec-new-btype"]) {
    const el = $(sel);
    if (el && !el.options.length) {
      // The LABEL, not the value: `LIGHTING_STUDY` put a machine token in
      // front of the user, which was ruled out on 2026-08-22 ("that
      // underscore is not for end users, has no meaning"). The list has
      // carried the label all along — this select was the one rendering
      // around it.
      el.innerHTML = BOARD_TYPES.map(t =>
        `<option value="${t.value}">${esc(t.label)}</option>`).join("");
      el.title = boardTypeTitle("What kind of board this is — it governs the "
        + "slugline, the panel template and how the scenes are read. Your "
        + "choice, not the model's: it is sent as an absolute rule.");
    }
  }
  const btypeSel = $("#spec-auto-btype");

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
      + "label this breakdown, its panels, and its boards sort under — pick "
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
  // Once the user has chosen, the hint never overwrites them.
  $("#spec-auto-btype")?.addEventListener("change", e => {
    e.target.dataset.touched = "1";
  });
  bindSpecIdField($("#spec-auto-id"));
  bindSpecIdField($("#spec-new-id"));

  // Three fields, three ways to fill them (user 2026-08-16). A brief means
  // "read the screenplay for it"; a pasted section means "this IS the
  // material, do not go looking"; typed panels pin the panels, and an
  // empty panels box means the model decides what the content needs.
  // Nothing typed at all still makes a genuinely blank sheet, which is
  // what this door used to be and is still worth having.
  $("#spec-auto-open-screenplay").onclick = () =>
    window.open("/api/screenplay/file", "_blank", "noopener");

  /* The brief and the pasted section are ALTERNATIVES (user, 2026-08-22:
     "should act as radio buttons — you can't do both"). Not literal radio
     buttons: the choice is made by typing, so the one you are not using
     goes unavailable and says so through the verb rather than asking you
     to declare an intent first.

     They are genuinely exclusive downstream — `source_text` REPLACES the
     screenplay, so a brief alongside it would name material the model has
     been told not to look at. */
  const syncAlternatives = () => {
    const brief = $("#spec-auto-subject");
    const paste = $("#spec-auto-source");
    if (!brief || !paste) return;
    const usingPaste = pasting || !!paste.value.trim();
    const usingBrief = !usingPaste && (!!scenePick || !!brief.value.trim());
    // One slot, two occupants: a selection states itself where the paste
    // box would be, and the paste box comes back the moment it is cleared.
    const pasteRow = paste.closest(".door-row");
    const pickRow = $("#spec-auto-picked-row");
    if (pickRow) pickRow.hidden = !scenePick;
    if (pasteRow) pasteRow.hidden = !!scenePick;
    brief.closest(".door-row")?.classList.toggle("is-off", usingPaste);
    pasteRow?.classList.toggle("is-off", usingBrief);
    brief.disabled = usingPaste;
    paste.disabled = usingBrief;
    const go = $("#spec-auto-go");
    if (go) {
      go.textContent = usingPaste ? "Break down the pasted section"
                                  : "Scan Screenplay";
    }
  };
  $("#spec-auto-source")?.addEventListener("input", () => {
    // Emptying the box is how you leave paste mode. The row that put you
    // in it lives in the search list, and this is the only way back —
    // one rule, so there is nothing to keep in step.
    if (!$("#spec-auto-source").value.trim()) pasting = false;
    syncAlternatives();
  });
  $("#spec-auto-unpick")?.addEventListener("click", () => clearPick());
  syncAlternatives();


  /* TWO handlers, because there are two acts and they call different
     endpoints. The merged form branched on which boxes were empty; the
     doors make that branch visible before it is committed, which is what
     the user asked for by asking for two columns. */
  $("#spec-auto-form").addEventListener("submit", async e => {
    e.preventDefault();
    const btn = $("#spec-auto-go");
    // The brief is the picked row's box when something is picked, and the
    // field itself when nothing is — one question, answered once.
    const pick = window.__scenePick?.() || null;
    const brief = pick
      ? ($("#spec-auto-brief")?.value.trim() || pick.brief)
      : $("#spec-auto-subject").value.trim();
    const source = $("#spec-auto-source")?.value.trim() || "";
    const panels = $("#spec-auto-panels")?.value.trim() || "";
    if (!brief && !source) {
      toast("Say what this board should get, or paste a section. To make an "
            + "empty sheet, use Blank sheet beside it.", true);
      return;
    }
    // Only a scene carries a line to point at; a location board wants all
    // of its scenes, which is the matched-by-name path.
    const ref = pick && pick.kind === "scene" ? pick : null;
    btn.disabled = true;
    const status = $("#spec-auto-status");
    const busy = status && startBusy(status,
      source ? "Breaking down the section you pasted…"
             : pick ? `Reading ${pick.label} and drafting the breakdown…`
             : "Reading the screenplay and drafting the breakdown…",
      panels ? "building the panels you named" : "deciding the panels it needs");
    try {
      const spec = await api("/api/specs/autofill", { method: "POST", json: {
        specification_id: slugSpecId($("#spec-auto-id").value),
        mode: $("#spec-auto-mode").value,
        board_type: $("#spec-auto-btype")?.value || "LOCATION",
        prompt: brief,
        source_text: source,
        panels,
        // The saved pointer, when the brief came from a picked scene.
        scene_line: ref ? ref.line : "",
        scene_heading: ref ? ref.heading : "",
        provider: $("#spec-auto-provider")?.value || "gemini",
      } });
      busy?.done();
      toast(`${spec.specification_id} drafted: ${spec.panels.length} panels, `
            + `${spec.evidence_ledger.length} evidence rows`
            + (source ? " — from the section you pasted." : "."));
      localStorage.removeItem("autoSpecDraft");
      renderSpecs(spec.specification_id);
    } catch (err) {
      busy?.done();
      toast(err.message, true);
      btn.disabled = false;
    }
  });

  $("#spec-new-form").addEventListener("submit", async e => {
    e.preventDefault();
    try {
      const id = slugSpecId($("#spec-new-id").value);
      const spec = await api("/api/specs", { method: "POST", json: {
        specification_id: id,
        mode: $("#spec-new-mode").value,
        board_type: $("#spec-new-btype")?.value || "LOCATION",
        subject: $("#spec-new-subject").value.trim() || id,
      } });
      toast(`${spec.specification_id} created — an empty sheet to fill.`);
      localStorage.removeItem("blankSpecDraft");
      renderSpecs(spec.specification_id);
    } catch (err) { toast(err.message, true); }
  });

  const specs = await api("/api/specs");
  const tbody = $("#spec-table tbody");
  const countEl = $("#spec-count");
  if (countEl) countEl.textContent = specs.length || "";
  tbody.innerHTML = specs.length ? "" :
    `<tr><td colspan="6" class="mini">NO BREAKDOWNS YET — RUN ONE ABOVE</td></tr>`;
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
        <button class="ghost" data-f="del" title="Permanently delete this breakdown and its candidates">Delete</button>
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
  syncUrl(true);
  // §3.15: the breakdown opens on what it has MADE. Reviewing a
  // specification without seeing the pictures it produced is reviewing it
  // blind, and this surface's whole job is describing two pictures.
  const [{ spec, locked, bible_catalog, bible_inferred }, subjects, allRefs,
         specCands] = await Promise.all([
    api(`/api/specs/${specId}`), api("/api/subjects"), api("/api/references"),
    api(`/api/specs/${specId}/candidates`).catch(() => []),
    // The breakdown row carries the same grammar and framing selects the
    // panel workbench does — A2's point is that the framing is chosen HERE,
    // before the spend, not at compile time.
    loadCinemaStyles(), loadCameraRecipes()]);
  // The slot map is the authority on WHY a slot is not ready. Without it
  // the frame can only say a take is missing — which is what it shows.
  const slotMap = await api(`/api/specs/${specId}/slot-map`).catch(() => null);

  // Carried panels of a scoped draft revision are read-only rows (one
  // board per unit, 2026-08-13): their approvals keep feeding the board,
  // so the declaration must stay provably true. Server enforces too.
  const carriedSet = new Set(
    !locked && spec.status === "DRAFT"
      ? (spec.revision_scope?.carried || []) : []);

  // An object "has reference material" when it matches a cast/subject card
  // with linked images, or an approved reference's role suffix.
  const approvedRefs = allRefs.filter(r => r.status === "APPROVED");
  // A required object names a subject the way the SCRIPT does, not the way
  // the cast card is filed (user-caught 2026-08-16: "the script
  // specifically mentions Sal — why would the required objects not pick up
  // Sal Craft? I had to add manually").
  //
  // The old test asked whether the phrase contained the card's WHOLE name.
  // "Sal inside the cryochamber" contains "Sal" and not "Sal Craft", so it
  // failed — and so did every other multi-word character in the
  // production: Kyra McGuire, Tom McGuire, Charlie Stanner. Only a card
  // named with a single token, like GT40, ever matched. The failure was
  // silent: no REF marker, and nothing saying why.
  //
  // A card's name matches on any of its own words, whole-word, and
  // AMBIGUITY REFUSES rather than guesses — "McGuire" alone belongs to two
  // characters, and picking one would attach the wrong face to a panel.
  // (`nameWords` is the module-scope one; this had its own copy without
  // the possessive/hyphen normalisation or the stoplist, so this surface
  // and the REF marker answered the same question differently.)
  const subjectFor = (o) => {
    const withRefs = subjects.filter(s => (s.ref_ids || []).length);
    // The whole name is still the strongest signal and wins outright.
    const exact = withRefs.find(s => wordIn(s.name.toLowerCase(), o)
                                  || s.name.toLowerCase().includes(o));
    if (exact) return exact;
    // Ambiguity is judged over the WHOLE cast, not just the cards that
    // happen to have photos: "McGuire" belongs to two characters whether
    // or not both have been photographed, and which one is meant is the
    // question. Attaching the wrong face is worse than no marker.
    const named = subjects.filter(s => nameWords(s.name).some(w => wordIn(w, o)));
    if (named.length !== 1) return null;
    return (named[0].ref_ids || []).length ? named[0] : null;
  };

  const refInfoFor = (obj) => {
    const o = String(obj).toLowerCase();
    const subj = subjectFor(o);
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

  // ---- the step sequence's supporting facts (STEP_SEQUENCE_SPEC Part 3)
  // Confirmations are advisory here exactly as on stage 04 (§2.4): a draft
  // with twelve open questions CAN be approved, so nothing here gates —
  // the step count and the gate line simply state where the work stands.
  const SPEC_STEPS = ["identity", "direction", "questions", "scope",
                      "panels", "evidence"];
  const confKeySpec = `spconf.${specId}`;
  const confAllSpec = () => uiGet(confKeySpec, {});
  const confIs = s => !!confAllSpec()[s];
  const confSetSpec = (s, on) => {
    const c = { ...confAllSpec() };
    if (on) c[s] = 1; else delete c[s];
    uiSet(confKeySpec, c);
  };
  // Board-level fields freeze on the first approval (user ruling
  // 2026-08-16), so the steps that hold them are settled, not pending.
  const approvedCands = (Array.isArray(specCands) ? specCands : [])
    .filter(c => c.status === "APPROVED");
  const boardFrozen = approvedCands.length > 0;
  // A LOCK is not a FREEZE (user 2026-08-16: "if I have not generated a
  // panel, and I edit a breakdown, I need to be able to edit that panel...
  // If it has an approved panel rendered then I should be blocked and
  // informed why, but NOT if there is no approved panel").
  //
  // The server has always worked this way — save_spec on a locked sheet
  // calls _refuse_frozen_edits, which refuses a panel's own fields only
  // when THAT panel has an approved take, and the board-level fields only
  // when some panel does. The UI disabled everything the moment the sheet
  // locked, so a locked sheet with nothing approved was read-only for no
  // reason the server would have enforced.
  const approvedPanelIds = new Set(approvedCands.map(c => c.panel_id));
  const panelFrozen = pid => approvedPanelIds.has(String(pid).toUpperCase());
  const allFrozen = boardFrozen
    && (spec.panels || []).every(p => panelFrozen(p.id));
  const BOARD_STEPS = ["identity", "direction", "scope"];
  const frozenWhyBoard = boardFrozen
    ? `Board-level and settled by ${approvedCands.map(c => c.candidate_id).join(", ")}`
      + " — withdraw that approval to change it"
    : "";
  const isFrozenStep = id => boardFrozen && BOARD_STEPS.includes(id);
  const confCountSpec = SPEC_STEPS
    .filter(s => confIs(s) || isFrozenStep(s)).length;
  const allocTotal = (spec.panels || [])
    .reduce((n, p) => n + (+p.allocation_percent || 0), 0);

  // §3.2 — Approve states its gate and does not lie.
  const qAll = spec.unresolved_questions || [];
  const qAns = spec.question_answers || {};
  const qOpen = qAll.filter(q => !String(qAns[q] || "").trim());
  const stepsLeft = SPEC_STEPS.length - confCountSpec;
  const approveGate = locked
    ? "LOCKED — APPROVED AND READ-ONLY"
    : [qOpen.length ? `${qOpen.length} QUESTION${qOpen.length === 1 ? "" : "S"} OPEN` : "",
       stepsLeft ? `${stepsLeft} STEP${stepsLeft === 1 ? "" : "S"} UNCONFIRMED` : "",
      ].filter(Boolean).join(" AND ") +
      (qOpen.length || stepsLeft ? " — YOU CAN STILL APPROVE"
                                 : "EVERY STEP CONFIRMED, EVERY QUESTION ANSWERED");

  // §3.15 — the breakdown opens on what it has made. The empty frame is
  // the valuable half: it is the only place a blocker reads as a
  // CONSEQUENCE (the picture that does not exist because of it) rather
  // than as a red tag in a rail. Sanctioned exception to "never reserve
  // the shape of the missing thing" — the shape is the panel's own ratio
  // and the frame states its blocker, so it is a report, not a
  // placeholder.
  const boardMadeHtml = (() => {
    const panels = spec.panels || [];
    if (!panels.length) return "";
    // Say the true thing or say nothing. Every empty frame used to carry
    // a hardcoded "SIZE —", which named a blocker the panel did not have:
    // a panel that has simply never been rendered has no size problem
    // (user-caught 2026-08-15). The slot map knows the real verdict.
    const slotBy = {};
    for (const s of (slotMap?.slots || [])) slotBy[s.panel_id] = s;
    // A SLOT verdict is a board problem, not a breakdown problem (user
    // 2026-08-16: "I dont like seeing the red on the approved panel in the
    // breakdown page. Save the error messages for the board tab"). Here,
    // an approved take IS the work finished — the panel did what this page
    // asked of it. Whether the resulting pixels fill a particular slot in a
    // particular layout is a question the board asks, and stage 05 already
    // answers it in three places: the rail mark, the readiness list, and
    // the hatched slot on the map. Two surfaces reporting one fault only
    // made the finished thing look broken.
    //
    // UNAPPROVED stays: it is not a slot verdict, it is this page's own
    // work still outstanding, and it names where to go and do it.
    const VERDICT_LINE = {
      TOO_SMALL: () => "",
      UNAPPROVED: () => "NO APPROVED TAKE — APPROVE ONE ON THE WORKBENCH",
      NO_CANDIDATE: () => "",
      STALE_APPROVAL: () => "",
    };
    const verdictOf = pid => {
      const s = slotBy[pid];
      if (!s || s.status === "OK") return "";
      const line = (VERDICT_LINE[s.status] || (() => ""))(s);
      return line ? `<span class="made-blocker mono">${esc(line)}</span>` : "";
    };
    const cands = Array.isArray(specCands) ? specCands : [];
    const forPanel = pid => cands.filter(c => c.panel_id === pid);
    const approvedN = panels.filter(p =>
      forPanel(p.id).some(c => c.status === "APPROVED")).length;
    const frames = panels.map(p => {
      const list = forPanel(p.id);
      const shown = list.find(c => c.status === "APPROVED") || list[0] || null;

      if (!shown) {
        return `<div class="made-item">
        <div class="made-frame made-empty">
          <span class="made-id mono">${esc(p.id)}</span>
          <span class="made-none mono">NO TAKE YET</span>
          <span class="made-foot">${verdictOf(p.id)}</span>
        </div>
        <div class="made-cap"><span>${esc(p.title || p.purpose || "")}</span>
          <span class="mono">${p.allocation_percent ? `${p.allocation_percent}%` : ""}</span></div>
        </div>`;
      }
      const ok = shown.status === "APPROVED";
      return `<div class="made-item">
      <div class="made-frame">
        <img src="/api/specs/${specId}/candidates/${esc(shown.candidate_id)}/image?size=thumb"
             loading="lazy" alt="${esc(p.id)}">
        <span class="made-id mono">${esc(p.id)} · ${esc(shown.candidate_id)}</span>
        <span class="made-foot">
          ${ok ? verdictOf(p.id) : ""}
          <span class="made-state mono ${ok ? "ok" : "hold"}">${
            ok ? "APPROVED" : esc(shown.status)} · ${shown.width} × ${shown.height}</span>
        </span>
      </div>
      <div class="made-cap"><span>${esc(p.title || p.purpose || "")}</span>
        <span class="mono">${p.allocation_percent ? `${p.allocation_percent}%` : ""}</span></div>
      </div>`;
    }).join("");
    const stake = approvedN === panels.length
      ? `Every panel approved. This board can be assembled.`
      : `${approvedN === 0 ? "No panels" : `${approvedN} panel${approvedN === 1 ? "" : "s"}`} approved of ${panels.length}. The board cannot be assembled until ${
          panels.length - approvedN === 1 ? "the last one has" : "each of the rest has"} an approved take.`;
    return `
      <div class="made">
        <div class="made-grid filmroll">${frames}</div>
        <div class="made-stake">
          <div class="rail-label">WHAT THIS BOARD HAS MADE</div>
          <p class="step-prose">${esc(stake)}</p>
          <button type="button" class="verb" data-f="to-panels">04 Panels</button>
        </div>
      </div>`;
  })();

  // §3.2 — open questions are a step, not a bullet under the header. They
  // are the highest-leverage thing on the page: each answer becomes canon
  // for every future render, and each blank one is a licence to invent.
  const qStepHtml = !qAll.length ? "" : seqStep({
    n: "03", id: "questions", label: "OPEN QUESTIONS",
    meta: `${qAll.length - qOpen.length} OF ${qAll.length} ANSWERED`,
    done: confIs("questions"),
    frozen: isFrozenStep("questions"), frozenWhy: frozenWhyBoard,
    verbs: `<button type="button" class="verb" data-f="answer-qs"${locked ? " disabled" : ""}>${
      qOpen.length === qAll.length ? "Answer these" : "Edit answers"}</button>`,
    body: `
      <div class="step-note mono">${spec.mode === "DESIGN_EXPLORATION"
        ? "THESE DO NOT NEED ANSWERS ON A DESIGN EXPLORATION — EXPLORING IS HOW YOU DECIDE THEM"
        : "THE SCREENPLAY DOES NOT ANSWER THESE · ANSWER ONE AND IT BECOMES CANON FOR THIS BOARD · LEAVE IT OPEN AND EVERY RENDER IS TOLD NOT TO INVENT ONE"}</div>
      <ul class="q-list">${qAll.slice(0, 4).map(q => `
        <li${qAns[q] ? ' class="answered"' : ""}>${esc(q)}${
          String(qAns[q] || "").trim() ? `<span class="q-ans">${esc(qAns[q])}</span>` : ""}</li>`).join("")}
      </ul>
      ${qAll.length > 4 ? `<div class="step-note mono">+ ${qAll.length - 4} MORE</div>` : ""}`,
  });
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
  panel.className = "panel spec-editor seq";
  panel.innerHTML = `
    <div class="seq-head">
      <span class="pid-badge">${esc(spec.specification_id)}</span>
      <h2 class="seq-subject">${esc(spec.subject || spec.specification_id)}</h2>
      <span class="seq-progress mono">${[
        esc(spec.status), locked ? "LOCKED" : "", `R${spec.revision || 1}`,
      ].filter(Boolean).join("  ·  ")}  ·  ${confCountSpec} OF ${SPEC_STEPS.length} ${
        boardFrozen ? "SETTLED" : "CONFIRMED"}</span>
    </div>
    ${spec.autofilled ? '<div class="step-note mono seq-autofill">AUTO-FILLED — REVIEW BEFORE APPROVING</div>' : ""}
    ${spec.autofill ? `<p class="mini">Drafted by ${esc(spec.autofill.model)} from: “${esc(spec.autofill.prompt)}”</p>` : ""}
    ${!locked && spec.status === "DRAFT" && spec.revision_scope ? `
      <p class="mini mono">REVISES ${spec.revision_scope.revised.length} OF ${(spec.panels || []).length} PANELS · ${spec.revision_scope.carried.length} CARRIED FROM ${esc(spec.revised_from?.specification_id || "")}</p>` : ""}
    ${locked ? `
    <div class="gate-strip lock-strip">
      <span class="gate-label" style="color:var(--ink-dim)">LOCKED</span>
      <span class="gate-text">${allFrozen
        ? `Every panel has an approved take, so this breakdown is settled — objects,
           panels and the ledger are what those renders were approved against.`
        : boardFrozen
          ? `${approvedPanelIds.size} of ${(spec.panels || []).length} panels have an
             approved take. <b>Those panels are frozen</b>; the rest, and any panel you
             add, stay editable. Board-level fields are settled because a take was
             approved against them.`
          : `Locked, but nothing has been rendered from it yet — <b>everything here is
             still editable</b> and saving re-stamps the lock. A panel freezes when one
             of its takes is approved.`}
        ${allFrozen ? "To edit:" : "To change a frozen part:"}</span>
      <button class="block-act" data-f="lock-revise">Create revision</button>
      <button class="block-act" data-f="lock-unlock">Unlock &amp; edit</button>
    </div>` : ""}
    <div id="sp-gate"></div>

    ${boardMadeHtml}
    <div class="steps">
        ${seqStep({ n: "01", id: "identity", label: "IDENTITY",
          meta: "WHAT THIS BREAKDOWN IS",
          verbs: `<button type="button" class="verb" data-f="focus-identity">Edit</button>`,
          done: confIs("identity"),
          frozen: isFrozenStep("identity"), frozenWhy: frozenWhyBoard,
          body: `      <div class="grid-form">
      <label title="What this board is about — a short human-readable name for the location, scene, prop, or character. It appears in prompts and the spec list.">Subject <input type="text" id="sp-subject" value="${esc(spec.subject)}" ${boardFrozen ? "disabled" : ""}></label>
      <label title="CANON_EXTRACTION: an official board — only what the screenplay actually supports, tight budget for guesses. DESIGN_EXPLORATION: you are deciding new visual canon — looser budget for inferences, but unsupported inventions are still zero.">Mode
        <select id="sp-mode" ${boardFrozen ? "disabled" : ""}>
          <option ${spec.mode === "CANON_EXTRACTION" ? "selected" : ""}>CANON_EXTRACTION</option>
          <option ${spec.mode === "DESIGN_EXPLORATION" ? "selected" : ""}>DESIGN_EXPLORATION</option>
        </select>
      </label>
      <label title="${esc(boardTypeTitle("What kind of board this is — it governs slugline behavior."))}">Board type
        <select id="sp-btype" ${boardFrozen ? "disabled" : ""}>
          ${BOARD_TYPES.map(t => `<option value="${t.value}" ${(spec.board_type || "LOCATION") === t.value ? "selected" : ""}>${t.label}</option>`).join("")}
        </select>
      </label>
      <label title="The overall board format the approved panels get assembled onto (e.g. wide cinematic production board). Descriptive — the pixel canvas is chosen at assembly time.">Canvas <input type="text" id="sp-canvas" value="${esc(spec.layout?.canvas || "")}" ${boardFrozen ? "disabled" : ""}></label>
      </div>
      <div class="grid-form">
      <label class="setf" data-setf="intext" title="Interior or exterior — the first half of the slugline; it decides the lighting logic (practicals and openings vs sky and sun).">INT / EXT
        <select id="sp-intext" ${boardFrozen ? "disabled" : ""}>
          ${["", "INT", "EXT", "INT/EXT"].map(v => `<option value="${v}" ${(spec.setting?.int_ext || "") === v ? "selected" : ""}>${v || "—"}</option>`).join("")}
        </select>
      </label>
      <label class="setf" data-setf="location" title="The location as the screenplay names it — the middle of the slugline.">Location <input type="text" id="sp-location" placeholder="as the slugline names it…" value="${esc(spec.setting?.location || "")}" ${boardFrozen ? "disabled" : ""}></label>
      <label class="setf" data-setf="tod" title="Scene boards only: the slugline time of day (DAY, NIGHT, DUSK…). All panels of a scene board share it — it overrides any style image's hour or hue. A screenplay continuity marker (SAME, CONTINUOUS) is not an hour: pick the real one.">Time of day
        <select id="sp-tod" ${boardFrozen ? "disabled" : ""}>
          ${[...new Set(["", ...TIMES_OF_DAY, "MAGIC HOUR",
                         ...(bible_catalog?.atmospheres || []),
                         ...(spec.setting?.time_of_day ? [spec.setting.time_of_day] : [])])]
            .map(t => `<option value="${esc(t)}"${
              (spec.setting?.time_of_day || "") === t ? " selected" : ""}>${esc(t) || "—"}</option>`).join("")}
        </select>
      </label>
      <label class="setf" data-setf="atmo" title="Optional weather / light character layered on the hour — one of the Bible's approved atmosphere studies (or your own words). DUSK is the hour; 'dusk and lanterns' is the atmosphere.">Atmosphere <input type="text" id="sp-atmo" list="atmo-list" placeholder="e.g. dusk and lanterns, storm approach…" value="${esc(spec.setting?.atmosphere || "")}" ${boardFrozen ? "disabled" : ""}>
        <datalist id="atmo-list">${(bible_catalog?.atmospheres || []).map(t => `<option value="${esc(t)}">`).join("")}</datalist>
      </label>
      </div>` })}

        ${seqStep({ n: "02", id: "direction", label: "DIRECTION",
          meta: "WHAT THE PANELS ARE TOLD",
          verbs: "",
          done: confIs("direction"),
          frozen: isFrozenStep("direction"), frozenWhy: frozenWhyBoard,
          body: `      <div class="grid-form">
      <label class="wide" title="One flowing paragraph describing the scene this board depicts — location and structure, time of day and light, atmosphere, key contents and their arrangement. Auto-fill drafts it from screenplay evidence; edit it freely. Injected into every panel prompt as THE SCENE, right before the panel's purpose.">The Scene <textarea id="sp-scene" ${boardFrozen ? "disabled" : ""} placeholder="One paragraph describing the scene — drafted by auto-fill, or write your own">${esc(spec.scene || "")}</textarea></label>
      <label class="wide" title="One or two sentences of board-specific art direction layered on top of the Art Direction Bible — how THIS board should feel. Goes into every panel prompt as BOARD-SPECIFIC TREATMENT.">Render intent <textarea id="sp-intent" ${boardFrozen ? "disabled" : ""}>${esc(spec.render_intent || "")}</textarea></label>
      <label class="wide" title="Board-wide never-include list, one item per line. Merged with each panel's forbidden objects into every render prompt on this board.">Forbidden elements <span class="hint">(one per line)</span>
        <textarea id="sp-forbidden" ${boardFrozen ? "disabled" : ""}>${esc((spec.forbidden_elements || []).join("\n"))}</textarea>
      </label>
      <label title="How many objects on this board may rest on WEAK evidence — things the screenplay only hints at rather than states (WEAK_INFERENCE rows in the evidence ledger). 0 means every object must be solidly supported. This budgets honest guesses; unsupported inventions are always forbidden regardless (their budget is pinned to 0).">Weak-inference budget <input type="number" id="sp-weak" min="0" value="${esc(String(spec.canon_budget?.weak_inference_max ?? 2))}" ${boardFrozen ? "disabled" : ""}></label>
      </div>` })}

        ${qStepHtml}

        ${bible_catalog?.exists ? seqStep({ n: "04", id: "scope", label: "SCOPE",
          meta: "WHICH BIBLE SECTIONS REACH THIS BOARD",
          done: confIs("scope"),
          frozen: isFrozenStep("scope"), frozenWhy: frozenWhyBoard,
          body: `      <div class="scope-cols">
        <div class="fgroup" title="Design languages are the Bible's per-faction / per-world / per-technology look sections. Check the ones whose content appears on this board — their design and material language go into every panel prompt.">
          <span class="f-label">Design languages</span>
          <div id="sp-design">${bible_catalog.design_languages.map(n => {
            const sel = spec.design_languages ?? bible_inferred.design_languages;
            return `<label class="mini check"><input type="checkbox" value="${esc(n)}" ${sel.includes(n) ? "checked" : ""} ${boardFrozen ? "disabled" : ""}> ${esc(n)}</label>`;
          }).join("") || '<span class="mini">none defined in the Bible</span>'}</div>
        </div>
        <div class="fgroup" title="The physical world this board lives in. Its Bible entry (palette, light, atmosphere) is injected between the design languages and the scene lessons.">
          <span class="f-label">Environment</span>
          <select id="sp-environment" ${boardFrozen ? "disabled" : ""}>
            <option value="">— none —</option>
            ${envOptions.map(n => `<option value="${esc(n)}"${envCurrent && envCurrent.toLowerCase() === n.toLowerCase() ? " selected" : ""}>${esc(n)}${envNotes[n] ? ` — ${esc(envNotes[n].slice(0, 44))}` : ""}${(bible_catalog.environments || []).includes(n) ? "" : " (not in Bible yet)"}</option>`).join("")}
          </select>
          <p class="mini" style="margin:6px 0 0">One per sheet — a board lives somewhere.${!spec.environments && envCurrent ? ` Inferred ${esc(envCurrent)} from the location; change it if the read guessed wrong.` : ""}</p>
          <p class="mini" style="margin:4px 0 0">Environment sets the biome's palette and light. ATMOSPHERE is this breakdown's weather and mood — it wins where they overlap.</p>
        </div>
        <div class="fgroup" title="Scene-locked lessons are the Bible's accumulated rules for specific scenes/subjects. Check the ones that apply to this board.">
          <span class="f-label">Scene lessons</span>
          <div id="sp-lessons">${bible_catalog.scene_lessons.map(n => {
            const sel = spec.scene_lessons ?? bible_inferred.scene_lessons;
            return `<label class="mini check"><input type="checkbox" value="${esc(n)}" ${sel.includes(n) ? "checked" : ""} ${boardFrozen ? "disabled" : ""}> ${esc(n)}</label>`;
          }).join("") || '<span class="mini">none recorded yet</span>'}</div>
        </div>
      </div>
      <div class="scope-carry" id="sp-carry"></div>
      ${spec.design_languages ? "" : '<p class="mini" style="margin:8px 0 0">Pre-checked from keyword inference — save the spec to make this selection explicit and governed.</p>'}` }) : ""}

        ${seqStep({ n: "05", id: "panels", label: "PANELS",
          meta: `${(spec.panels || []).length} · ALLOCATION ${allocTotal}%`,
          verbs: "",
          done: confIs("panels"),
          frozen: isFrozenStep("panels"), frozenWhy: frozenWhyBoard,
          body: `      <div id="sp-panels"></div>
      ${allFrozen ? "" : '<button class="ghost" id="sp-add-panel">+ Add panel</button>'}` })}

        ${seqStep({ n: "06", id: "evidence", label: "EVIDENCE",
          // A citation the screenplay does not contain is demoted at the
          // write (adversarial review F21), which means a draft can arrive
          // with rows at HOLD the user did not put there. The count is the
          // fact they need BEFORE reading the ledger: how much of what the
          // model claimed as the screenplay's word actually was. Amber,
          // because it is the state the reviewer has to act on.
          meta: `${(spec.evidence_ledger || []).length} ROWS · ${
            spec.citations?.demoted
              ? `<span class="step-meta-alert">${spec.citations.demoted} OF ${
                  spec.citations.claimed} CITATIONS NOT FOUND IN THE SCREENPLAY —
                 THOSE ROWS ARE HELD</span>`
              : spec.citations?.claimed
                ? `ALL ${spec.citations.claimed} CITATIONS FOUND IN THE SCREENPLAY`
                : "EVERY REQUIRED OBJECT HAS A PASS ROW"}`,
          verbs: "",
          done: confIs("evidence"),
          frozen: isFrozenStep("evidence"), frozenWhy: frozenWhyBoard,
          body: `      <div class="ledger-row grid-head">
        <span title="Which panel this evidence row belongs to (its Panel ID, e.g. P01).">ID</span>
        <span title="The visible object this row justifies.">Object</span>
        <span title="How strongly the canon supports this object — the evidence class.">Source</span>
        <span title="The citation itself — an exact quote or scene reference; free text for the human audit trail, never sent to the image model.">Cited evidence</span>
        <span title="PASS renders; HOLD blocks approval until you resolve it; REMOVE marks for removal.">State</span>
        <span></span>
      </div>
      <div id="sp-ledger"></div>
      ${allFrozen ? "" : '<button class="ghost" id="sp-add-ledger">+ Add evidence row</button>'}` })}

        ${seqStep({ n: "07", label: "APPROVE & LOCK",
          meta: "APPROVING LOCKS THE OBJECTS, PANELS AND LEDGER · ONLY THEN CAN STAGE 04 GENERATE",
          verbs: `${allFrozen ? "" : `
        <button class="primary" id="sp-save">Save</button>
        <button class="ghost" id="sp-validate">Validate</button>`}
      ${locked ? "" : `<button class="ghost" id="sp-approve">Approve &amp; lock</button>`}
      ${locked ? `
        <button class="ghost" id="sp-revise">Create revision</button>
        <button class="danger" id="sp-unlock" title="Void the approval and edit this spec in place — refused if approved candidates or boards depend on it">Unlock &amp; edit</button>
        <span class="hint">revision keeps the approved version as history; unlock voids it and edits in place (refused while approved candidates/boards depend on this spec)</span>` : ""}`,
          body: `<div class="gen-gate mono">${approveGate}</div>` })}
      </div>

    <div id="sp-report"></div>`;
  host.append(panel);

  // The editor renders BELOW the breakdown list, so opening one left its
  // head ~1500px down the page and the lock strip — the only place that
  // offers Unlock & edit — off-screen (user 2026-08-16: "'Unlock and Edit'
  // needs to appear at the top"). Opening a breakdown should put you at
  // the top of it. A re-render from a step confirmation must NOT scroll,
  // or every tick throws the reader back up.
  if (openSpecEditor._last !== specId) {
    openSpecEditor._last = specId;
    requestAnimationFrame(() => panel.scrollIntoView({ block: "start" }));
  }

  // Step confirmations — same two-state model as stage 04, same advisory
  // rule: repainting is what re-reads the state, so the head count, the
  // step's dimming and the approve gate stay one fact.
  $$("[data-confirm]", panel).forEach(b => b.onclick = () => {
    confSetSpec(b.dataset.confirm, true); openSpecEditor(specId);
  });
  $$("[data-unconfirm]", panel).forEach(b => b.onclick = () => {
    confSetSpec(b.dataset.unconfirm, false); openSpecEditor(specId);
  });
  // A confirmed ledger is a record, so the act that grows it steps aside
  // with the controls (the step's own Unconfirm brings both back).
  const addLedgerBtn = $("#sp-add-ledger", panel);
  // C3: the add act follows the ledger, and the ledger follows the lock.
  if (addLedgerBtn) addLedgerBtn.classList.toggle("hidden", !!locked);

  const focusIdentity = $("[data-f=focus-identity]", panel);
  if (focusIdentity) focusIdentity.onclick = () => $("#sp-subject", panel)?.focus();
  const madeStrip = $(".made-grid", panel);
  if (madeStrip) {
    dragScroll(madeStrip); stripKeys(madeStrip);
    // The frames are 35mm windows with the panel fitted into them, so they
    // show less than the take — clicking one opens it full size, the same
    // bargain the takes strip makes (user 2026-08-15).
    const shots = (spec.panels || [])
      .map(pn => ({ pn, c: (Array.isArray(specCands) ? specCands : [])
        .filter(c => c.panel_id === pn.id)
        .find(c => c.status === "APPROVED")
        || (Array.isArray(specCands) ? specCands : [])
             .find(c => c.panel_id === pn.id) }))
      .filter(x => x.c);
    const items = shots.map(({ pn, c }) => ({
      src: `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
      caption: `${c.candidate_id} — ${pn.id} (${c.status}) ${c.width}×${c.height}`,
      grammar: c.cinematography?.rides
        ? String(c.cinematography.name || "").toUpperCase() : "",
    }));
    // Selecting a panel on the workbench is roomSel.panel — the route's
    // one-shot scroll target only finds a card that is already rendered,
    // and this surface renders one panel at a time.
    const goToPanel = pid => {
      boardRoomSel[specId] = {
        ...(boardRoomSel[specId] || uiGet("roomSel", {})[specId] || {}),
        panel: pid,
      };
      persistRoomSel();
      uiSet("boardSpec", specId);
      showView("boards");
    };

    $$(".made-item", madeStrip).forEach((item, i) => {
      const frame = $(".made-frame", item);
      if (!frame) return;
      const pn = (spec.panels || [])[i];
      if (frame.classList.contains("made-empty")) {
        // An empty frame has no picture to open, so its click goes where
        // the picture gets MADE — stage 04, with this panel active (user
        // 2026-08-15). The frame states a consequence; this is the act
        // that resolves it.
        if (!pn) return;
        // Stage 04 lists SIGNED-OFF breakdowns only, so on a draft this
        // click would land on whatever sheet stage 04 falls back to.
        // State the gate instead of moving somewhere that ignores you.
        if (!locked) {
          frame.title = `${pn.id} cannot render yet — approve & lock this `
            + `breakdown first (step 07 below)`;
          frame.classList.add("made-gated");
          return;
        }
        frame.style.cursor = "pointer";
        frame.title = `Render ${pn.id} — opens the panels workbench with it active`;
        frame.onclick = () => goToPanel(pn.id);
        return;
      }
      const id = ($(".made-id", frame)?.textContent || "").split("·").pop().trim();
      const idx = shots.findIndex(s => s.c.candidate_id === id);
      frame.style.cursor = "zoom-in";
      frame.title = "Open this take at full size";
      frame.onclick = () => { if (idx >= 0) openLightbox(items, idx); };
    });
  }

  const toPanels = $("[data-f=to-panels]", panel);
  if (toPanels) toPanels.onclick = () => {
    uiSet("boardSpec", specId);
    showView("boards");
  };
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
    // Per-row editability (2026-08-13): a carried panel of a scoped
    // draft revision is read-only exactly like a locked sheet's row —
    // the sheet-wide flag stays `locked`; this row's is `ro`.
    // Per PANEL, not per sheet: only an approved take freezes its own row.
    const ro = panelFrozen(pid) || carriedSet.has(pid);
    const row = document.createElement("div");
    row.className = "panel-card";
    row.dataset.pid = pid;
    row.innerHTML = `
      <div class="head">
        <button type="button" class="text-act mono" data-f="pc-toggle" title="Collapse panel details">−</button>
        <span class="pid-badge" title="Panel ID — assigned automatically; the evidence ledger and layout refer to it.">${esc(pid)}</span>
        ${!locked && carriedSet.has(pid) ? `
          <span class="mini mono" title="Carried from the locked revision — this panel is not being revised here. Its approved take keeps flowing to the board.">CARRIED</span>
          <button type="button" class="text-act" data-f="also-revise" title="Upgrade this panel into the revision — editable here from now on, and the board will ask for a new take for its slot. Journaled.">Also revise</button>` : ""}
        <input type="text" data-f="title" placeholder="Panel title — e.g. The Pioneer's Workshop" value="${esc(p.title || "")}" ${ro ? "disabled" : ""} title="Short display name for this panel.">
        <span class="alloc ptod-wrap" title="Light for THIS panel — location and lighting-study boards choose it per panel. Pick a time of day (the hour) or one of the Bible's atmosphere studies (hour + weather + light character). Overrides any style image's hour or hue.">
          <select data-f="ptod" ${ro ? "disabled" : ""}>
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
          <input type="number" data-f="alloc" placeholder="—" min="1" max="100" value="${esc(allocById[p.id] ?? "")}" ${ro ? "disabled" : ""}>
          <span class="unit">%</span>
        </span>
        ${ro ? "" : '<button class="danger" data-f="del-panel" title="Remove panel">×</button>'}
      </div>
      <div class="fgroup" title="The production question this panel answers. Becomes PANEL PURPOSE in the render prompt — the model's main steer for what the image is about. If no required objects are added, the model composes the panel from this alone (within canon).">
        <span class="f-label" style="display:flex;align-items:center;gap:10px">Purpose
          ${ro ? "" : `<button type="button" class="text-act" data-f="scan-scene"
            title="Say anything about this panel — a question, a correction, a feeling, a paste from elsewhere — and the screenplay scene behind it is read again against what you said. One text call, no render; nothing changes until you accept a proposal.">Tell me about this panel</button>`}</span>
        <input type="text" data-f="purpose" placeholder="The production question this panel answers" value="${esc(p.purpose || "")}" ${ro ? "disabled" : ""}>
      </div>
      <div class="fgroup" title="Camera and composition for this panel. Each axis falls back to the production's Art Direction Bible camera default when blank, and overrides it when set. The app writes the professional directive into the render prompt.">
        <span class="f-label">Camera <span class="hint">(blank = the bible default)</span></span>
        ${cameraRow("pcam", p, "— production default —", ro)}
      </div>
      <div class="two-col">
        <div class="fgroup" title="Objects that MUST appear. Each added object automatically gets a USER_DIRECTED / PASS evidence-ledger row. Optional — leave empty to let the model compose from the purpose.">
          <span class="f-label">Required objects</span>
          <div class="chips" data-f="chips"></div>
        </div>
        <div class="fgroup" title="Objects that must NOT appear in this panel, comma-separated. Merged with the board-wide forbidden elements, and with any project-wide prohibited inventions, in the prompt.">
          <span class="f-label">Forbidden objects</span>
          <input type="text" data-f="forbidden" placeholder="comma-separated…" value="${esc((p.forbidden_objects || []).join(", "))}" ${ro ? "disabled" : ""}>
        </div>
      </div>
      ${bible_catalog?.exists ? `<div class="pscope" data-f="pscope"></div>` : ""}
      ${ro ? "" : `
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
      if (!ro) {
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
            ${ro ? "" : `<button class="text-act" data-f="ovr" title="Give this panel its own design languages and environment — a declared exception to the board's scope.">Override</button>`}`;
          const b = $("[data-f=ovr]", pscopeHost);
          if (b) b.onclick = () => { overriding = true; renderPScope(); };
        } else {
          pscopeHost.innerHTML = `
            <div class="fgroup" title="This panel's own visual cultures — its prompt carries these instead of the board's languages.">
              <span class="f-label" style="display:flex;align-items:center;gap:10px">Panel design languages
                ${ro ? "" : `<button class="text-act" data-f="revert" style="margin-left:auto" title="Clear the exception — this panel goes back to inheriting the board's scope.">Revert to board</button>`}</span>
              <div class="chips" style="margin-top:4px">
                ${bible_catalog.design_languages.map(n =>
                  `<button type="button" class="vchip${(p.design_languages || []).includes(n) ? " set" : ""}" data-plang="${esc(n)}" ${ro ? "disabled" : ""}>${esc(n)}</button>`).join("")}
              </div>
            </div>
            <div class="fgroup" title="The one place THIS panel lives — replaces the board's environment in this panel's prompt.">
              <span class="f-label">Panel environment</span>
              <select data-f="penv" ${ro ? "disabled" : ""}>
                <option value="">— board's environment —</option>
                ${[...new Set([...envOptions, ...(p.environment ? [p.environment] : [])])].map(n =>
                  `<option value="${esc(n)}"${(p.environment || "") === n ? " selected" : ""}>${esc(n)}</option>`).join("")}
              </select>
            </div>`;
          if (!ro) {
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

    if (!ro) {
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

      // Scan the screenplay again, for something the user names (2026-08-16).
      // A breakdown is drafted once from a brief, and the draft summarises:
      // it captured "airlock hatch behind Sal" and lost that the hatch
      // irises. Nothing in the app could go back and ask. Findings arrive as
      // a PROPOSAL — accepting one adds the chip, which the existing chip
      // path then journals as USER_DIRECTED like any hand-typed object.
      const scanBtn = $("[data-f=scan-scene]", row);
      if (scanBtn) scanBtn.onclick = () => scanScreenplayDialog({
        specId, panelId: pid,
        brief: $("[data-f=purpose]", row).value,
        // On the breakdown nothing is saved until the sheet is saved, so an
        // accepted brief fills the field and rides that Save — the same
        // path a typed brief takes.
        acceptBrief: text => { $("[data-f=purpose]", row).value = text; },
        has: () => $$(".chip", chips).map(c => c.dataset.obj),
        accept: (obj) => {
          if ($$(".chip", chips).some(c => c.dataset.obj.toLowerCase() === obj.toLowerCase()))
            return false;
          // On the breakdown the object is not saved yet — it becomes a
          // chip and rides the sheet's own Save, which writes its ledger
          // row exactly as a hand-typed object does.
          addChip(obj, true);
          syncSuggest();
          return true;
        },
      });

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
    // Collapsible rows (user 2026-08-13): every panel can fold to its
    // head line; carried panels of a scoped revision open COLLAPSED —
    // present (the sheet stays whole) but not in the way. Collapse only
    // hides; every input stays in the DOM, so collect() reads unchanged.
    const tog = $("[data-f=pc-toggle]", row);
    const setCollapsed = c => {
      row.classList.toggle("pc-collapsed", c);
      // R13 (HARNESS_AUDIT): open/closed is the app's density vocabulary
      // — minus/plus, Courier-safe at small sizes. Never persisted: a
      // fold is a reading posture, not a setting.
      tog.textContent = c ? "+" : "−";
      tog.title = c ? "Expand panel details" : "Collapse panel details";
    };
    tog.onclick = () => setCollapsed(!row.classList.contains("pc-collapsed"));
    if (carriedSet.has(pid)) setCollapsed(true);

    // Also revise (2026-08-13): the one-way upgrade — the carried row
    // joins the revision. In-flight edits to OTHER rows are saved first
    // so the re-render loses nothing.
    $("[data-f=also-revise]", row)?.addEventListener("click", async () => {
      if (!(await askConfirm(`Revise ${pid} in this revision`,
        "This panel joins the revision — editable here from now on, and the board will ask for a new take for its slot. Recorded in the revision's journal.",
        "Also revise"))) return;
      try {
        await api(`/api/specs/${specId}`, { method: "PUT", json: collect() });
        await api(`/api/specs/${specId}/revision-scope`,
          { method: "POST", json: { panel_id: pid } });
        toast(`${pid} joined the revision — it is editable now.`);
        openSpecEditor(specId);
      } catch (err) { toast(err.message, true); }
    });
    panelsHost.append(row);
    wireCameraRow("pcam", row);  // reveal the custom focal-length input on demand
    updateSettingVis();
  }

  function addLedgerRow(r = {}) {
    const row = document.createElement("div");
    row.className = "ledger-row";
    // §3.35 as the user ruled it (2026-08-14): a CONFIRMED ledger reads as
    // a provenance record — 21 rows of five selects is 105 controls on a
    // page whose best content is the citations themselves. Drafting keeps
    // the selects the user directed on 2026-08-13; editing is behind the
    // step's own Unconfirm, and locking keeps it read-only for good.
    // C3 (RULE_PASS 2026-08-16), CORRECTED: the trigger is the LOCK, not
    // the confirmation. A confirmation is advisory — §2.4 and C1 both say
    // it never gates — and a control that loses its affordance when you
    // confirm a step is a confirmation that gated something. Two rules
    // cannot both be true. Confirming step 06 changes the step; editing
    // after the lock goes through the withdraw path.
    const ro = locked;
    // Selectable, not typed (user 2026-08-13): the panel is one of the
    // sheet's own ids; the object is one of that panel's required objects
    // that does not have a row yet. The citation stays typeable but gains
    // reference-library type-ahead via a shared datalist.
    const pids = $$(".panel-card", panelsHost).map(x => x.dataset.pid);
    if (r.panel_id && !pids.includes(r.panel_id)) pids.unshift(r.panel_id);
    row.innerHTML = `
      <select data-f="panel_id" ${ro ? "disabled" : ""} title="Which panel this evidence row belongs to.">
        ${pids.map(p => `<option ${r.panel_id === p ? "selected" : ""}>${esc(p)}</option>`).join("") || '<option value=""></option>'}
      </select>
      <select data-f="object" ${ro ? "disabled" : ""} title="The visible object this row justifies — offered from the chosen panel's required objects that do not have an evidence row yet. Every required object needs a PASS row."></select>
      <select data-f="evidence_class" ${ro ? "disabled" : ""} title="How strongly the canon supports this object:
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
      <input type="text" data-f="source" placeholder="Source citation — type, or search the reference library" value="${esc(r.source || "")}" ${ro ? "disabled" : ""} title="Where the evidence comes from — a screenplay page/line quote, an approved reference (start typing to search the library), or your directive. Free text for the human audit trail: validation only requires it to be non-empty, nothing looks it up, and it is never sent to the image model. (Citing a reference here does NOT attach it to generations — use the checkboxes on the Panels tab.)">
      <select data-f="status" ${ro ? "disabled" : ""} title="PASS — evidence accepted, the object may render.
HOLD — needs your review; blocks approval until resolved.
REMOVE — marked for removal from the board.">
        ${LEDGER_STATUSES.map(s => `<option ${r.status === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${locked ? "<span></span>" : '<button class="danger" title="Remove row">×</button>'}`;
    // The object select follows the chosen panel: required objects of
    // that panel that no OTHER row already covers; a stored value always
    // stays offered so existing rows round-trip untouched.
    const pidSel = $("[data-f=panel_id]", row);
    const objSel = $("[data-f=object]", row);
    const syncObjects = keep => {
      const pid = (pidSel.value || "").trim().toUpperCase();
      const card = $$(".panel-card", panelsHost).find(x => x.dataset.pid === pid);
      const objs = card ? $$(".chip", card).map(c => c.dataset.obj) : [];
      const rowed = $$(".ledger-row", ledgerHost).filter(x => x !== row)
        .filter(x => ($("[data-f=panel_id]", x).value || "").trim().toUpperCase() === pid)
        .map(x => ($("[data-f=object]", x).value || "").trim().toLowerCase());
      const open = objs.filter(o => !rowed.includes(o.toLowerCase())
                                    && o.toLowerCase() !== String(keep).toLowerCase());
      objSel.innerHTML = (keep ? `<option selected>${esc(keep)}</option>`
          : `<option value="">${open.length ? "— object —" : "— every required object has a row —"}</option>`)
        + open.map(o => `<option>${esc(o)}</option>`).join("");
    };
    syncObjects(r.object || "");
    if (!locked) {
      pidSel.addEventListener("change", () => syncObjects(""));
      // Recompute the offer EVERY time the select opens — rows created
      // earlier could only see the rows that existed before them, and
      // add/remove elsewhere goes stale otherwise (user-hit 2026-08-13).
      objSel.addEventListener("mousedown", () => syncObjects(objSel.value));
      $("button.danger", row).onclick = () => row.remove();

      // Citation search — a real, visible suggestion list over the
      // approved reference library (the native datalist proved inert,
      // user-hit 2026-08-13). Free typing stays; a pick fills the field.
      const srcInput = $("[data-f=source]", row);
      row.style.position = "relative";
      const sug = document.createElement("div");
      sug.className = "hidden";
      sug.style.cssText = "position:absolute;z-index:40;background:var(--panel2);border:1px solid var(--line);max-height:220px;overflow:auto;min-width:340px";
      row.append(sug);
      const lib = allRefs.filter(x => x.status === "APPROVED");
      const paintSug = () => {
        const t = srcInput.value.trim().toLowerCase();
        const hits = t ? lib.filter(x =>
          `${x.id} ${x.role} ${x.notes || ""}`.toLowerCase().includes(t))
          .slice(0, 8) : [];
        if (!hits.length) { sug.classList.add("hidden"); return; }
        sug.style.left = srcInput.offsetLeft + "px";
        sug.style.top = (srcInput.offsetTop + srcInput.offsetHeight + 2) + "px";
        sug.innerHTML = hits.map(x =>
          `<button type="button" class="text-act" style="display:block;width:100%;text-align:left;padding:6px 10px" data-v="${esc(`${x.id} — ${x.role}`)}">
             <span class="mono">${esc(x.id)}</span> ${esc(String(x.role).slice(0, 48))}</button>`).join("");
        $$("button", sug).forEach(b => b.onmousedown = e => {
          e.preventDefault();
          srcInput.value = b.dataset.v;
          sug.classList.add("hidden");
        });
        sug.classList.remove("hidden");
      };
      srcInput.addEventListener("input", paintSug);
      srcInput.addEventListener("focus", paintSug);
      srcInput.addEventListener("blur", () =>
        setTimeout(() => sug.classList.add("hidden"), 150));
    }
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
      failed to render this breakdown's ${panelsHost.children.length ? "ledger" : "panels"}</b>
      — the breakdown itself is intact on the server (${(spec.panels || []).length} panels,
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
      if (carriedSet.has(id)) {
        // Carried rows pass through VERBATIM — the read-only promise the
        // revision scope makes; the server deep-compares and refuses any
        // drift too.
        out.panels.push(orig);
        layoutPanels.push({ id,
          allocation_percent: parseFloat($("[data-f=alloc]", row).value) || 0 });
        continue;
      }
      const p = {
        ...orig,
        id,
        title: v("title").trim(),
        purpose: v("purpose").trim(),
        required_objects: $$(".chip", row).map(c => c.dataset.obj),
        forbidden_objects: split(v("forbidden")),
        evidence: Array.isArray(orig.evidence) && orig.evidence.length
          ? orig.evidence : ["USER_DIRECTED"],
        ...readCameraFields("pcam", row),
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
    // The revise-scope modal (one board per unit, 2026-08-13): the user
    // declares WHICH panels the revision changes. Checked = revised
    // (editable in the draft; their board slots re-gate). Unchecked =
    // carried (read-only; approvals keep flowing to the board). Nothing
    // pre-checked and Confirm disabled at 0 — a revision that revises
    // nothing is ledger noise; the explicit choice IS the feature.
    const reviseScopeDialog = () => modal({
      custom: `
        <div class="modal-title">What panels would you like to include in revision</div>
        <p class="modal-body">Checked panels are REVISED — editable in the new
        draft, and their board slots will ask for a new take. Unchecked panels
        are CARRIED — read-only in the draft; their approved takes keep flowing
        to the board. A carried panel can join later with its Also revise act.</p>
        <div style="max-height:300px;overflow:auto;margin:10px 14px">
          ${(spec.panels || []).map(p => `
            <div><label class="check"><input type="checkbox" value="${esc(p.id)}">
              <span class="mono">${esc(p.id)}</span> ${esc(p.title || p.purpose || "")}</label></div>`).join("")}
        </div>
        <div class="mini mono" data-f="rev-count" style="margin:0 14px">NOTHING REVISED YET — CHECK AT LEAST ONE PANEL</div>
        <div class="modal-actions" style="margin:12px 14px">
          <button type="button" class="text-act" data-f="rev-all">Select all</button>
          <span style="flex:1"></span>
          <button class="ghost" data-f="rev-cancel">Cancel</button>
          <button class="primary" data-f="rev-ok" disabled>Create revision</button>
        </div>`,
      mount: (ov, done) => {
        const picked = () => $$("input[type=checkbox]:checked", ov).map(x => x.value);
        const recount = () => {
          const n = picked().length, total = (spec.panels || []).length;
          $("[data-f=rev-count]", ov).textContent = n
            ? `${n} OF ${total} PANELS REVISED · ${total - n} CARRIED`
            : "NOTHING REVISED YET — CHECK AT LEAST ONE PANEL";
          $("[data-f=rev-ok]", ov).disabled = n === 0;
        };
        ov.addEventListener("change", recount);
        $("[data-f=rev-all]", ov).onclick = () => {
          $$("input[type=checkbox]", ov).forEach(x => { x.checked = true; });
          recount();
        };
        $("[data-f=rev-cancel]", ov).onclick = () => done(null);
        $("[data-f=rev-ok]", ov).onclick = () => done(picked());
      },
    });
    const doRevise = async () => {
      const ids = await reviseScopeDialog();
      if (ids === null) return;
      try {
        const clone = await api(`/api/specs/${specId}/revise`,
          { method: "POST", json: { revise_panels: ids } });
        toast(`Revision ${clone.specification_id} created — ${ids.length} of ${(spec.panels || []).length} panel(s) revised.`);
        renderSpecs(clone.specification_id);
      } catch (err) { toast(err.message, true); }
    };
    $("#sp-revise", panel).onclick = doRevise;
    $("[data-f=lock-revise]", panel).onclick = doRevise;
    const doUnlock = async () => {
      if (!(await askConfirm(`Unlock ${specId} for editing`,
        "This VOIDS its approval (journaled in the approval log) and returns it to DRAFT — it disappears from Panels until you approve it again, and re-approving mints a new spec hash. Unapproved candidates keep the hash they were generated against.\n\nRefused automatically if any APPROVED candidate or board depends on this breakdown — approved canon can never change out from under what it was approved against.\n\nTo keep the approved version as history instead, use Create revision.",
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

  // Answering a design question is a DECISION that reaches the image
  // prompt (user 2026-08-07). Wired at the tail, NOT inside either lock
  // branch: the button renders in both states (disabled when locked), and
  // it first went into the locked-only branch, where it could never fire.
  const answerBtn = $("[data-f=answer-qs]", panel);
  if (answerBtn) answerBtn.onclick = async () => {
    const qs = spec.unresolved_questions || [];
    const have = spec.question_answers || {};
    const vals = await modal({
      title: "Answer the design questions",
      body: spec.mode === "DESIGN_EXPLORATION"
        ? "A design exploration is where these get decided, so none is required. "
          + "Anything you answer becomes canon for this board and rides every "
          + "panel's prompt; anything left blank stays open."
        : "The screenplay does not answer these. An answer becomes canon for this "
          + "board and rides every panel's prompt. Left blank, the question stays "
          + "open and the render is told not to invent one.",
      fields: qs.map((q, n) => ({
        name: `q${n}`, label: q, value: have[q] || "", textarea: true,
        placeholder: "leave blank to keep it open",
      })),
      confirmLabel: "Save answers",
    });
    if (vals === null) return;
    const answers = {};
    qs.forEach((q, n) => {
      const v = (vals[`q${n}`] || "").trim();
      if (v) answers[q] = v;
    });
    try {
      await api(`/api/specs/${specId}`, { method: "PUT",
        json: { ...collect(), question_answers: answers } });
      const n = Object.keys(answers).length;
      toast(n ? `${n} of ${qs.length} answered — they ride every panel's prompt.`
              : "Answers cleared — the questions stay open.");
      renderSpecs(specId);
    } catch (err) { toast(err.message, true); }
  };

}

/* ----------------------------------------------------------------- boards */

const IMAGE_SIZES = ["1K", "2K", "4K"];
// Aspect catalog comes from settings (film-format names + per-engine
// support); this is only the offline fallback if the payload is missing.
const ASPECT_FALLBACK = ["21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"]
  .map(id => ({ id, label: id, value: (([w, h]) => w / h)(id.split(":").map(Number)), engines: [] }));
// UNCANONIZED — 2026-08-16 — rendering style catalogue (user-directed).
// A rendering style is HOW a panel is drawn: medium, mark, finish. It is
// NOT mood, light or cinematography — those are set elsewhere, and the
// modal says so at the top, because "medium & finish" as a free-text box
// was collecting all four.
//
// `value` is the phrase written into #wiz-medium and therefore into the
// bible's Rendering Language section, so each one reads as a directive a
// render can follow, not as a label. `not` follows the SETS/NOT grammar
// the style-anchor columns already use.
/* Retired 2026-08-22 — these two libraries now live in
   docs/RENDERING_STYLES.md and docs/WORLD_TEXTURE_STYLES.md, parsed by
   app/style_docs.py, the same way cinematography has since 2026-08-16.
   Empty here on purpose: a fallback copy of a document is the second list
   that ruling forbids, and it would be the stale one.

   PLATES stays: a plate is drawn artwork keyed by style name, not
   authored prose, so it cannot live in a markdown document. */
const RENDER_STYLES = [];
const TEXTURE_STYLES = [];
const STYLE_PLATES = {"Production Painting": "markPaint", "Hand-Drawn Cartoon": "markCartoon", "Black & White Sketch": "markSketch", "3D Rendered Cartoon": "markRender3d", "Photo Real": "markPhoto", "Industrial Design": "markIndustrial", "Ink & Wash": "markInkWash", "Gouache & Watercolor": "markGouache", "Technical Blueprint": "markBlueprint", "Rendered Illustration": "markRendered", "Pristine": "texPristine", "Lived-In": "texLivedIn", "Weathered": "texWeathered", "Decayed": "texDecayed", "Industrial Grime": "texIndustrial"};

// The eight cinematography grammars live in docs/CINEMATOGRAPHY_STYLES.md
// and are READ from it (user ruling 2026-08-16), never copied — the
// document is the source of truth the user maintains, so editing it
// updates the picker and there is never a second list to keep in step.
// Populated by loadCinemaStyles(); empty until it resolves.
const CINEMA_STYLES = [];

// The switch (user 2026-08-16: "we need to evaluate the output — so we
// need to be able to roll this back"). OFF by default, so a render is
// byte-identical to before until it is thrown; throwing it back stops the
// grammar riding the next render, and every take already made under it
// keeps its own record of having done so. The consequence is stated here
// rather than discovered in the output.
async function saveCineSetting(patch) {
  try { return await api("/api/cinematography/setting",
                         { method: "PUT", json: patch }); }
  catch (err) { toast(err.message, true); }
}

const BR = String.fromCharCode(10);

/* The RENDERS switch that stood here is retired (user, 2026-08-22:
   "there should be no switch on the panels in the Production Design tab.
   That sets the default. It should be over-rideable on the panel render
   tab.").

   It was an off-by-default toggle deciding whether a chosen grammar's
   image-model prompt reached renders at all — built in 2026-08-16 so the
   feature could be evaluated and rolled back, which it was. What it left
   behind was a third lever: a production default, a global on/off, and a
   per-panel override, where the middle one silently decided whether the
   other two meant anything. Two levers now. Production Design sets the
   default; the panel's Grammar select overrides it or refuses it. */

/* Three anchors, three documents, one loader (2026-08-22). World texture
   and rendering style used to be arrays in this file — five and nine
   options carrying a one-line description and a prompt fragment of about
   sixty characters, against 1,200 for a cinematography grammar. They were
   exactly the "second list to keep in step" the 2026-08-16 ruling was
   written against: adding a texture meant editing the client. */
const STYLE_DOCS = {
  cinematography: "docs/CINEMATOGRAPHY_STYLES.md",
  texture: "docs/WORLD_TEXTURE_STYLES.md",
  rendering: "docs/RENDERING_STYLES.md",
};

async function loadStyleLibrary(library, into) {
  if (into.length) return into;
  let d;
  try {
    d = await api(`/api/styles/${library}`);
  } catch (err) {
    /* Never swallow this. The styles are READ from a document, so "none"
       is a real possible answer and a silently empty picker cannot be
       told apart from a broken fetch (user, 2026-08-21). */
    toast(`Could not load the ${library} styles: ${err.message} — they are `
          + `read from ${STYLE_DOCS[library]}.`, true);
    into.failed = true;
    return into;
  }
  for (const st of d.styles || []) {
    into.push({
      ...st,
      // the shared picker's vocabulary, mapped onto the document's
      desc: st.description,
      not: (st.avoid || []).slice(0, 3).join(" · "),
      // A plate is drawn artwork keyed by style NAME — it cannot live in a
      // markdown document, so it is looked up rather than parsed. A style
      // the document adds simply has no plate until one is drawn.
      plate: STYLE_PLATES[st.name] || undefined,
      rich: true,
    });
  }
  return into;
}

/* A2 — the framings, from docs/CAMERA_RECIPES.md. Loaded once, like the
   style libraries, and for the same reason: the document is the source of
   truth and a list here would be the second one to keep in step.

   Its own array rather than a fourth STYLE_DOCS entry, because it answers
   a different question. The style libraries say what a look is FOR; this
   says how the shot is taken — focal length, aperture, focus. */
const CAMERA_RECIPES = [];
async function loadCameraRecipes() {
  if (CAMERA_RECIPES.length) return CAMERA_RECIPES;
  try {
    const d = await api("/api/camera-recipes");
    CAMERA_RECIPES.push(...(d.recipes || []));
  } catch (err) {
    /* Same rule as the style libraries: never swallow it. An empty
       picker and a failed fetch look identical, and this one decides the
       lens a render is made at. */
    toast(`Could not load the camera recipes: ${err.message} — they are `
          + `read from docs/CAMERA_RECIPES.md.`, true);
    CAMERA_RECIPES.failed = true;
  }
  return CAMERA_RECIPES;
}
const recipeByKey = k => CAMERA_RECIPES.find(r => r.key === String(k || ""));

const loadCinemaStyles = () => loadStyleLibrary("cinematography", CINEMA_STYLES);
const loadTextureStyles = () => loadStyleLibrary("texture", TEXTURE_STYLES);
const loadRenderStyles = async () => {
  const out = await loadStyleLibrary("rendering", RENDER_STYLES);
  /* Style 1 is the HOUSE slot. adoptHouseStyle() replaces its words and
     its plate with this production's own captured style once a Bible and
     approved panels exist, so the card shows what this film is drawn in
     rather than a shipped default. The document says so in its Purpose
     section; carrying the marker by position rather than by name keeps
     the client from holding a second copy of a style's title. */
  if (out.length && out[0].key !== "house") {
    out[0].docKey = out[0].key;
    out[0].key = "house";
  }
  return out;
};



// UNCANONIZED — 2026-08-16 — style plates (user-directed: "you get the
// words with an associated example image of the style").
//
// These are DIAGRAMS, not photographs. We cannot ship stock imagery, and
// a generated sample would be one engine's opinion of the style rather
// than the style — so each plate draws the one thing its axis is about:
// for light, a lit form and where its shadow falls; for medium, the MARK
// on the surface. Hard stops only, tokens only — canon forbids gradients,
// and a lighting diagram that needed one would be describing a photo
// rather than a behaviour. `Add your own` is how a real picture gets in.
const PLATE = {
  // ---- light behaviour: one form, one ground, the source moved around it
  lightNatural: `<circle cx="34" cy="30" r="15" fill="#2b3037"/><path d="M34 15a15 15 0 0 1 0 30z" fill="#6b7278"/><ellipse cx="42" cy="47" rx="12" ry="3" fill="#23272c"/>`,
  lightHard: `<circle cx="34" cy="30" r="15" fill="#15181b"/><path d="M34 15a15 15 0 0 1 0 30z" fill="#eceef0"/><path d="M40 47h22l-6 4H36z" fill="#15181b"/>`,
  lightChiaro: `<circle cx="34" cy="30" r="15" fill="#0f1114"/><path d="M45 20a15 15 0 0 1 2 12l-6-2z" fill="#eceef0"/><ellipse cx="38" cy="47" rx="14" ry="3" fill="#0f1114"/>`,
  lightHighKey: `<circle cx="34" cy="30" r="15" fill="#e0e2e4"/><path d="M25 20a15 15 0 0 0-4 12l7-2z" fill="#9aa1a8"/><ellipse cx="35" cy="47" rx="9" ry="2" fill="#23272c"/>`,
  lightOvercast: `<circle cx="34" cy="30" r="15" fill="#9aa1a8"/><ellipse cx="34" cy="47" rx="6" ry="2" fill="#2b3037"/>`,
  lightPractical: `<circle cx="34" cy="30" r="15" fill="#23272c"/><path d="M34 15a15 15 0 0 1 11 5l-11 10z" fill="#9aa1a8"/><circle cx="52" cy="16" r="4" fill="#eceef0"/><circle cx="52" cy="16" r="8" fill="none" stroke="#6b7278"/>`,
  lightBacklit: `<circle cx="34" cy="30" r="15" fill="#0f1114" stroke="#eceef0" stroke-width="2"/><path d="M8 12h52v3H8z" fill="#6b7278"/><ellipse cx="34" cy="47" rx="15" ry="3" fill="#0f1114"/>`,
  // ---- medium: the mark left on the surface
  markPaint: `<path d="M10 18h20l-4 6H8zM32 18h26l-5 6H28zM8 28h24l-5 6H6zM34 28h22l-4 6H30zM12 38h22l-5 6H10zM36 38h20l-4 6H32z" fill="#6b7278"/>`,
  markCartoon: `<rect x="10" y="14" width="22" height="16" fill="#6b7278" stroke="#eceef0" stroke-width="2"/><circle cx="46" cy="36" r="11" fill="#2b3037" stroke="#eceef0" stroke-width="2"/>`,
  markSketch: `<g stroke="#9aa1a8"><path d="M10 44L28 14M16 44L34 14M22 44L40 14M28 44L46 14"/><path d="M34 44L52 14M40 44L58 14"/></g><g stroke="#6b7278"><path d="M10 30h48"/></g>`,
  markRender3d: `<circle cx="34" cy="29" r="16" fill="#2b3037"/><path d="M34 13a16 16 0 0 1 14 8l-14 8z" fill="#9aa1a8"/><path d="M48 21a16 16 0 0 1 1 12l-15-4z" fill="#6b7278"/><ellipse cx="34" cy="48" rx="14" ry="3" fill="#23272c"/>`,
  markPhoto: `<g fill="#6b7278"><rect x="8" y="12" width="52" height="34"/></g><g fill="#0f1114"><rect x="8" y="12" width="52" height="2"/><rect x="8" y="20" width="52" height="1"/><rect x="8" y="30" width="52" height="1"/><rect x="8" y="41" width="52" height="5"/></g><rect x="20" y="22" width="14" height="14" fill="#eceef0"/>`,
  markIndustrial: `<rect x="12" y="16" width="32" height="22" fill="none" stroke="#eceef0" stroke-width="1.5"/><path d="M44 16l10-6v22l-10 6z" fill="none" stroke="#eceef0" stroke-width="1.5"/><path d="M12 44h32" stroke="#6b7278"/><path d="M12 41v6M44 41v6" stroke="#6b7278"/>`,
  markInkWash: `<rect x="10" y="16" width="26" height="20" fill="#2b3037"/><g stroke="#eceef0" stroke-width="1.5" fill="none"><rect x="10" y="16" width="26" height="20"/><path d="M40 14v32M40 14h18M40 46h18"/></g>`,
  markGouache: `<path d="M10 15h18l3 9-4 8H9l-2-9z" fill="#6b7278"/><path d="M32 20h16l4 10-3 9H30l-1-10z" fill="#9aa1a8"/><path d="M14 36h14l2 8H12z" fill="#2b3037"/>`,
  // Continuous tone stepped through the plate palette's own greys, with
  // one sharp specular and a soft shape behind: modelling, finish and
  // falloff, which is all this style claims.
  markRendered: `<rect x="6" y="18" width="16" height="18" fill="#23272c"/>\
<circle cx="36" cy="30" r="15" fill="#2b3037"/><circle cx="36" cy="30" r="11" fill="#6b7278"/>\
<circle cx="38" cy="27" r="6" fill="#9aa1a8"/><circle cx="40" cy="25" r="1.8" fill="#eceef0"/>\
<ellipse cx="36" cy="48" rx="14" ry="3" fill="#23272c"/>`,
  markBlueprint: `<g stroke="#2b3037"><path d="M8 14h52M8 22h52M8 30h52M8 38h52M8 46h52M14 10v40M26 10v40M38 10v40M50 10v40"/></g><rect x="20" y="18" width="24" height="16" fill="none" stroke="#eceef0" stroke-width="1.5"/><path d="M20 42h24M20 39v6M44 39v6" stroke="#eceef0"/>`,
  // ---- world texture
  texPristine: `<rect x="10" y="14" width="48" height="32" fill="#6b7278"/>`,
  texLivedIn: `<rect x="10" y="14" width="48" height="32" fill="#6b7278"/><g fill="#2b3037"><rect x="16" y="20" width="10" height="3"/><rect x="34" y="30" width="14" height="2"/><rect x="22" y="38" width="8" height="2"/></g>`,
  texWeathered: `<rect x="10" y="14" width="48" height="32" fill="#2b3037"/><g fill="#6b7278"><rect x="10" y="14" width="18" height="12"/><rect x="34" y="22" width="16" height="10"/><rect x="14" y="34" width="12" height="8"/><rect x="44" y="36" width="10" height="6"/></g>`,
  texDecayed: `<rect x="10" y="14" width="48" height="32" fill="#15181b"/><g fill="#6b7278"><path d="M10 14h14l-3 10-8 2z"/><path d="M40 18h18v9l-12 3z"/><path d="M16 34h10l4 8H14z"/></g><g stroke="#2b3037"><path d="M24 14l6 32M42 14l-4 32"/></g>`,
  texIndustrial: `<rect x="10" y="14" width="48" height="32" fill="#2b3037"/><g fill="#6b7278"><rect x="10" y="14" width="48" height="4"/><rect x="10" y="42" width="48" height="4"/></g><g stroke="#15181b"><path d="M22 18v24M34 18v24M46 18v24"/></g>`,
};

// Real example images drop in over the diagram as they are made (user
// 2026-08-16: "you and i will generate images for this UI"). The manifest
// lists only the keys that HAVE a picture, so the page never asks for one
// that does not exist — and a key with no picture yet still shows its
// diagram rather than a hole.
let PLATE_SHOTS = null;
const loadPlateShots = () => PLATE_SHOTS ??= fetch("/style-plates/index.json")
  .then(r => r.ok ? r.json() : {}).then(m => (PLATE_SHOTS = m || {}), () => (PLATE_SHOTS = {}));

function stylePlate(key, shot, alt = "") {
  const body = PLATE[key];
  if (!body && !shot) return "";
  const file = (PLATE_SHOTS && !PLATE_SHOTS.then) ? PLATE_SHOTS[key] : null;
  const src = shot || (file ? `/style-plates/${file}` : "");
  // A real picture opens full size, the same as the photographed frames
  // beside it (user, 2026-08-22: "the one on the left does not expand if
  // I click on it"). `data-lb` is what the picker binds the lightbox to,
  // and this image never carried one — so the production's OWN captured
  // plate, the single most interesting picture in the modal, was the one
  // frame you could not look at. The drawn diagram gets none: an SVG at
  // 68x56 has no full size to open.
  return (body ? `<svg class="rs-plate" viewBox="0 0 68 56" aria-hidden="true"
    fill="none" stroke-width="1" vector-effect="non-scaling-stroke">${body}</svg>` : "")
    + (src ? `<img class="rs-shot" src="${esc(src)}" alt="${esc(alt)}"
         data-lb="${esc(src)}">` : "");
}

// The picker, shared by every anchor whose answer comes from a known
// vocabulary (rendering style 2026-08-16; cinematography the same day,
// user: "We need the same style picker for cinematography"). Selection is
// an ink keyline, never amber — a chosen look is STATE; amber stays with
// the one primary action (Use this). Free text survives: these were text
// boxes, and a catalogue that cannot say "something else" is a smaller
// field than the one it replaced.
// A production that has been rendering for weeks already HAS a rendering
// style, and it is not a phrase we wrote (user 2026-08-16: "we should
// capture my style and make it the Production Painting style"). Its
// authority is the saved bible's Rendering Language, which has ridden
// every prompt, and its truest example is a panel it actually produced.
// So the first card in the catalogue stops being generic and becomes
// THIS production's, with a real take as its plate.
async function adoptHouseStyle() {
  const card = RENDER_STYLES.find(x => x.key === "house");
  if (!card || card._adopted) return;
  let h;
  try { h = await api("/api/bible/house-style"); } catch { return; }
  if (!h?.has_bible) return;
  card._adopted = true;
  // The card must SHOW the style, not describe the fact that it was
  // captured (user-caught 2026-08-16: "the production painting card does
  // not contain the description of the rendering style"). The bible's own
  // words are the description; where they came from is a footnote.
  if (h.words) {
    card.value = h.words;
    card.desc = (h.lines || []).join(" · ") || h.words;
    // B6: first line, with a hairline under it. "Position alone does not
    // disclose" — so it names what kind of thing this card is.
    card.source = "FROM THIS PRODUCTION — ITS BIBLE AND ITS APPROVED PANELS";
  }
  if (h.plate) card.shot = h.plate;
}

// B4 (RULE_PASS 2026-08-16): three things that reward reading, behind one
// door. Seven text roles is a document rendered as a cell, and nobody
// reads an essay inside a grid. The key question leads — it keeps its
// emphasis by being FIRST, not by being italic (B5 refuses italic
// outright: the system has two voices and they are families, not slants).
function openGrammarReader(st) {
  const ov = document.createElement("div");
  ov.className = "modal-scrim";
  ov.innerHTML = `
    <div class="modal rs-prompt-modal" role="dialog" aria-modal="true">
      <div class="modal-title">${esc(st.name)}</div>
      <p class="rs-sub mono">${esc(st.subtitle || "")}</p>
      <p class="rs-q">${esc(st.question || "")}</p>
      <p class="rs-principle"><b>Operating principle</b> ${esc(st.principle || "")}</p>
      <p class="rs-read-k mono">IMAGE-MODEL PROMPT</p>
      <pre class="rs-prompt-text mono">${esc(st.prompt || "")}</pre>
      <div class="modal-actions">
        <button class="ghost" data-f="copy">Copy the prompt</button>
        <button class="ghost" data-f="close">Close</button>
      </div>
    </div>`;
  document.body.append(ov);
  const close = () => ov.remove();
  $("[data-f=close]", ov).onclick = close;
  ov.addEventListener("click", e => { if (e.target === ov) close(); });
  $("[data-f=copy]", ov).onclick = async () => {
    try { await navigator.clipboard.writeText(st.prompt || ""); toast("Prompt copied."); }
    catch { toast("Could not copy — select the text instead.", true); }
  };
}

// B1 (RULE_PASS 2026-08-16): ONE card, two lives, one function. The
// catalogue cell and the chosen card were two drawings of the same thing
// and were already drifting — the fix is not to reconcile them but to
// stop having two. Same reading order at both scales: PICTURE first and
// largest, at its own ratio, then the name, then the words.
//
// B4: four text roles, not seven. Canon's cards carry two or three; seven
// is a document rendered as a cell, which is why the description wrapped
// to a column an inch wide. The key question, the operating principle and
// the full prompt reward reading, and nobody reads inside a grid cell —
// they move behind `Read the grammar`.
//
// B6: a generated entry and an authored one must not look identical.
// Provenance is the FIRST line with a hairline under it; position alone
// does not disclose.
function styleCard(st, { chosen = false } = {}) {
  const shots = st.rich ? plateShots(st.key).slice(0, 3) : [];
  // B3: never pad to three. A reserved shape is forbidden unless it states
  // the blocker that keeps it empty, and a dashed cell states nothing.
  const drawn = st.plate || st.shot
    ? `<span class="rs-frame">${stylePlate(st.plate, st.shot, st.name)}</span>` : "";
  const picture = st.rich
    ? (shots.length
        ? `<span class="rs-frames" data-n="${shots.length}">${shots.map((src, i) =>
            `<span class="rs-cell"><img class="rs-thumb" src="${esc(src)}"
               alt="${esc(st.name)} reference frame ${i + 1}"
               data-lb="${esc(src)}"></span>`).join("")}</span>`
        /* A rich style with no photographed frames falls back to its drawn
           plate (user, 2026-08-22: "we lost the images on World Texture").
           Making texture and rendering document-backed set `rich`, which
           routed them down the frames path — and that path had no fallback,
           so five textures and nine rendering styles silently traded a
           diagram they HAD for a placeholder saying they had nothing.
           B3 still holds: this is not padding to three, it is the picture
           that already existed. The placeholder is for a style with
           neither. */
        : drawn || `<span class="rs-nof mono">REFERENCE FRAMES — NOT YET IN THE LIBRARY</span>`)
    : drawn;
  return `
    ${st.source ? `<span class="rs-src mono">${esc(st.source)}</span>
                   <span class="rs-seam"></span>` : ""}
    ${picture}
    <span class="rs-name">${esc(st.name)}</span>
    <span class="rs-desc">${esc(st.rich ? st.description : st.desc)}</span>
    ${st.rich && (st.films || []).length
      ? `<span class="rs-films">${esc(st.films.slice(0, 5).join(", "))}</span>` : ""}
    ${st.rich
      ? `<button type="button" class="text-act rs-prompt-link" data-prompt="${esc(st.key)}">Read the grammar</button>`
      : `<span class="rs-not mono">NOT ${esc(String(st.not).toUpperCase())}</span>`}`;
}

// The manifest may name one picture for a key or several — a style plate
// is one image, a cinematography grammar is three frames.
function plateShots(key) {
  const m = (PLATE_SHOTS && !PLATE_SHOTS.then) ? PLATE_SHOTS[key] : null;
  if (!m) return [];
  return (Array.isArray(m) ? m : [m]).map(f => `/style-plates/${f}`);
}

function openStylePicker({ title, definition, styles, current, onPick,
                          uploadRole, uploadLabel, extra = "", onOpen, onClose,
                          onPicked, footer,
                          ownPlaceholder = "describe it in your own words" }) {
  const ov = document.createElement("div");
  ov.className = "modal-scrim";
  const head = t => String(t).slice(0, 110);
  const hit = styles.find(x => x.value === current)
    || styles.find(x => x.key === "house" && x.value && current
         && (current.startsWith(head(x.value)) || x.value.startsWith(head(current))));
  ov.innerHTML = `
    <div class="modal rs-modal" role="dialog" aria-modal="true">
      <div class="modal-title">${esc(title)}</div>
      <p class="rs-def">${definition}</p>
      ${/* Only while something in THIS picker is actually showing a diagram.
             The note used to key off "has a plate", which stayed true after
             a library gained photographed frames — so cinematography and
             then world texture kept apologising for diagrams they no longer
             showed (2026-08-22). */
        styles.some(x => x.plate && !plateShots(x.key).length)
          ? `<p class="rs-placeholder mono">PLATES ARE DIAGRAMS UNTIL THE REFERENCE LIBRARY LANDS</p>` : ""}
      <div class="rs-cards${styles.some(x => x.rich) ? " rs-cards-rich" : ""}">${styles.map((st, i) => `
        <div class="rs-card${st === hit ? " on" : ""}${
            st.rich ? " rs-rich" : ""}" data-i="${i}" role="button" tabindex="0">
          ${styleCard(st)}
        </div>`).join("")}
      </div>
      <!-- B7: an escape hatch is not a member of the set it escapes, and
           it was drawn twice — a grid cell AND a field inside the modal.
           One control, below the grid, after a hairline, full width. -->
      <div class="rs-own-row">
        <span class="rs-own-lab mono">OR IN YOUR OWN WORDS</span>
        <input type="text" id="rs-own" class="rs-own-in"
               placeholder="${esc(ownPlaceholder)}"
               value="${esc(hit || !current ? "" : current)}">
        <span class="rs-own-thumbs" data-f="own-thumbs"></span>
        <button type="button" class="ghost" data-f="add-img"
          title="Attach an example image to this anchor">+ Add an image</button>
      </div>
      ${extra}
      <div data-f="footer"></div>
      <div class="modal-actions">
        <button class="ghost" data-f="cancel">Cancel</button>
        <button class="primary" data-f="ok">Use this</button>
      </div>
    </div>`;
  document.body.append(ov);
  let picked = hit ? hit.value : (current || "");
  const own = $("#rs-own", ov);
  const mark = () => $$(".rs-card[data-i]", ov).forEach(c =>
    c.classList.toggle("on", styles[+c.dataset.i].value === picked));
  // A frame opens full size; the prompt opens as a document. Neither is
  // "choose this style", so both stop the card's own click.
  $$("[data-lb]", ov).forEach(img => img.onclick = e => {
    e.stopPropagation();
    // The whole style's frames, opened at the one clicked — arrows then
    // step between them instead of dead-ending on a single picture.
    const set = $$("[data-lb]", img.closest(".rs-card"));
    openLightbox(set.map(x => ({ src: x.dataset.lb, caption: x.alt })),
                 set.indexOf(img));
  });
  $$(".rs-prompt-link", ov).forEach(b => b.onclick = e => {
    e.stopPropagation();
    const st = styles.find(x => x.key === b.dataset.prompt);
    if (st) openGrammarReader(st);
  });
  // A card is a DIV, not a button: it holds real buttons of its own (the
  // frames, the prompt link) and a button inside a button is invalid —
  // the parser hoists the inner one out and the card comes apart on
  // screen (caught 2026-08-16 the moment real frames landed). role and
  // tabindex put the keyboard back.
  const choose = c => {
    picked = styles[+c.dataset.i].value;
    own.value = "";
    mark();
    ov.querySelector(".rs-own-row").classList.remove("on");
  };
  $$(".rs-card[data-i]", ov).forEach(c => {
    c.onclick = () => choose(c);
    c.onkeydown = e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(c); }
    };
  });
  // Typing your own is choosing your own: the cards let go rather than
  // leaving two answers lit at once.
  own.addEventListener("input", () => {
    if (own.value.trim()) { picked = ""; mark(); }
    ov.querySelector(".rs-own-row").classList.toggle("on", !!own.value.trim());
  });
  own.onclick = e => e.stopPropagation();
  if (own.value.trim()) ov.querySelector(".rs-own-row").classList.add("on");
  // Controls that were MOVED into the panel go home on the way out,
  // bindings intact — re-creating them would mean re-binding them.
  const close = () => { onClose?.(ov); ov.remove(); };
  $("[data-f=cancel]", ov).onclick = close;
  ov.addEventListener("click", e => { if (e.target === ov) close(); });
  window.addEventListener("keydown", function esc2(e) {
    if (e.key === "Escape") { close(); window.removeEventListener("keydown", esc2); }
  });
  // The plus adds a real picture to THIS anchor, through the same upload
  // the card used to carry — one library, reached from where you are
  // rather than from a second control on the page (user 2026-08-16).
  const col = $(`.wiz-col[data-role="${uploadRole}"]`);
  $("[data-f=add-img]", ov).onclick = () => $("[data-f=addbtn]", col)?.click();
  // What is already attached lives here now, not on the card.
  const thumbs = $("[data-f=own-thumbs]", ov);
  const showAttached = () => {
    $$(".rs-thumb", thumbs).forEach(t => t.remove());
    for (const img of $$("[data-f=list] img", col).slice(0, 4)) {
      const c = document.createElement("img");
      c.className = "rs-thumb";
      c.src = img.src;
      c.alt = "";
      thumbs.append(c);
    }
  };
  showAttached();
  footer?.($("[data-f=footer]", ov));
  onOpen?.(ov, showAttached);
  $("[data-f=ok]", ov).onclick = () => {
    onPick((own.value.trim() || picked).trim());
    onPicked?.(styles.find(x => x.value === picked) || null);
    close();
  };
}

// C7 (RULE_PASS_2 C, 2026-08-18): the options truncated mid-definition
// (`SCENE — one screenplay scene, slugli⌄`). The 260px cap is canon R10,
// deliberately set, so the option text is what gives — the definitions are
// already in the control's own title. An option reads as its value.
const BOARD_TYPES = [
  { value: "SCENE", label: "SCENE",
    hint: "one screenplay scene, one time of day for every panel" },
  { value: "LOCATION", label: "LOCATION",
    hint: "a place across times — time of day is chosen per panel" },
  { value: "ASSET", label: "ASSET",
    hint: "a prop, vehicle or character — neutral presentation, no slugline" },
  { value: "LIGHTING_STUDY", label: "LIGHTING STUDY",
    hint: "derived from an approved panel — geometry locked, only light varies" },
  { value: "MASTER", label: "MASTER",
    hint: "presentation grammar — four panels, neutral, no slugline" },
];
/* ONE definition of the vocabulary, read by both selects. The intake's
   title named three of the five and the sheet editor's named all five,
   which is the drift this file has been bitten by before — and the
   intake, where a sheet is MADE, was the one missing them. */
const boardTypeTitle = lead => lead + " " + BOARD_TYPES
  .map(t => `${t.label}: ${t.hint}.`).join(" ");
const TIMES_OF_DAY = ["DAWN", "MORNING", "DAY", "AFTERNOON", "DUSK", "EVENING", "NIGHT"];

// Camera & composition vocabulary (user 2026-08-09) — [value, label]. Values
// match store.CAMERA_FIELDS; the model-facing phrasing lives server-side in
// generate.CAMERA_*_PHRASING. Reused by the sheet editor, the panels workbench,
// and the bible-default card.
const CAMERA_ANGLES = [["EYE_LEVEL", "Eye level"], ["LOW", "Low — looks up"],
  ["HIGH", "High — looks down"], ["BIRDS_EYE", "Bird's-eye — top-down"],
  ["WORMS_EYE", "Worm's-eye — straight up"]];
const CAMERA_LENSES = [["18MM", "18mm"], ["24MM", "24mm"], ["35MM", "35mm"],
  ["50MM", "50mm"], ["85MM", "85mm"], ["135MM", "135mm"]];
const CAMERA_TILTS = [["LEVEL", "Level"], ["DUTCH", "Dutch — tilted"]];
// The azimuth axis (2026-08-13): which face of the subject the camera sees.
// No baseline — unset means the model chooses (mirrors store.CAMERA_FIELDS).
const CAMERA_ORIENTATIONS = [["FRONT", "Front"],
  ["THREE_QUARTER_FRONT", "3/4 front"], ["SIDE", "Side — profile"],
  ["THREE_QUARTER_REAR", "3/4 rear"], ["REAR", "Rear"]];
const SHOT_SCALES = [["AERIAL", "Aerial"], ["EXTREME_WIDE", "Extreme wide"],
  ["WIDE", "Wide"], ["MEDIUM", "Medium"], ["CLOSE", "Close"],
  ["EXTREME_CLOSE", "Extreme close"], ["MACRO", "Macro"], ["MICRO", "Micro"]];
const CAMERA_AXES = [
  { key: "camera_angle", f: "angle", label: "Angle", opts: CAMERA_ANGLES },
  // `unset` keeps orientation clearable even on the defaults card, which
  // renders with no blank option — the other axes always carry a value
  // there, this one legitimately has none.
  { key: "camera_orientation", f: "orient", label: "View",
    opts: CAMERA_ORIENTATIONS, unset: "— free —" },
  { key: "camera_lens", f: "lens", label: "Lens", opts: CAMERA_LENSES },
  { key: "camera_tilt", f: "tilt", label: "Tilt", opts: CAMERA_TILTS },
  { key: "scale", f: "scale", label: "Shot", opts: SHOT_SCALES },
];
// Pre-2026-08-10 lens words map onto a focal length so old settings still show.
const _LEGACY_LENS = { WIDE: "24MM", NORMAL: "50MM", TELEPHOTO: "135MM" };
const lensValue = v => _LEGACY_LENS[String(v || "").toUpperCase()] || String(v || "").toUpperCase();
// Pre-enum autofill shot words map onto the canon scale so drafted panels
// show their real value instead of "— production default —" (a save persists the
// migrated form). Mirrors store.LEGACY_SCALE.
const _LEGACY_SCALE = { FULL_BODY: "WIDE", DETAIL: "EXTREME_CLOSE" };
const scaleValue = v => _LEGACY_SCALE[String(v || "").toUpperCase()] || String(v || "").toUpperCase();

// One camera <select>. `prefix` namespaces its data-f ("pcam"/"cam"/"dcam");
// `blank`, when given, is the empty "inherit" option — omitted for the
// production default, which always carries a concrete value. The lens axis adds
// a "Custom…" option that reveals a focal-length input.
function cameraSelect(prefix, axis, value, blank, disabled = false) {
  const dis = disabled ? "disabled" : "";
  const blankLabel = blank || axis.unset || "";
  const blankOpt = blankLabel ? `<option value="">${esc(blankLabel)}</option>` : "";
  if (axis.key === "camera_lens") {
    const v = lensValue(value);
    const custom = !!v && !axis.opts.some(([ov]) => ov === v);
    return `<label class="cam-field mini"><span>${esc(axis.label)}</span>
      <span class="cam-lens">
        <select data-f="${prefix}-lens" ${dis}>${blankOpt}
          ${axis.opts.map(([ov, ol]) => `<option value="${ov}" ${v === ov ? "selected" : ""}>${esc(ol)}</option>`).join("")}
          <option value="CUSTOM" ${custom ? "selected" : ""}>Custom…</option>
        </select>
        <input type="number" data-f="${prefix}-lens-mm" class="cam-lens-mm${custom ? "" : " hidden"}"
          min="8" max="800" step="1" placeholder="mm" value="${custom ? esc(v.replace(/MM$/, "")) : ""}" ${dis}>
      </span></label>`;
  }
  const uv = axis.key === "scale" ? scaleValue(value)
    : String(value || "").toUpperCase();
  return `<label class="cam-field mini"><span>${esc(axis.label)}</span>
    <select data-f="${prefix}-${axis.f}" ${dis}>${blankOpt}
      ${axis.opts.map(([ov, ol]) => `<option value="${ov}" ${uv === ov ? "selected" : ""}>${esc(ol)}</option>`).join("")}
    </select></label>`;
}
function cameraRow(prefix, obj, blank, disabled = false) {
  return `<div class="cam-row" data-f="${prefix}-row">${
    CAMERA_AXES.map(a => cameraSelect(prefix, a, obj?.[a.key], blank, disabled)).join("")
  }${blank ? grammarSelect(prefix, obj?.cinematography, blank, disabled)
            + framingSelect(prefix, obj, blank, disabled) : ""}</div>`;
}

/* The cinematography grammar as a per-panel axis (user, 2026-08-22: "check
   that we can actually set it when rendering a panel, including None").
   Three states, the same shape the camera axes already use — inherit the
   production's choice, name one, or refuse one for this panel alone.

   Only where there IS a blank option: the production defaults card sets
   the default itself, and "— production default —" there would point at
   itself. */
function grammarSelect(prefix, value, blank, disabled = false) {
  const v = String(value || "");
  const opts = (CINEMA_STYLES.length ? CINEMA_STYLES : [])
    .map(st => `<option value="${esc(st.key)}" ${v === st.key ? "selected" : ""}
      >${esc(st.name)}</option>`).join("");
  // Labelled "Grammar" until 2026-08-24, when the person who ASKED for
  // this axis could not find it and asked for it again: "I want to be able
  // to change the cinematography style when rendering the panel." The
  // control was there; the word was not one anyone reaches for. The
  // concept is still the production's cinematography grammar — the field
  // just answers to the name people use for it.
  return `<label class="cam-field mini"><span>Cinematography</span>
    <select data-f="${prefix}-grammar" ${disabled ? "disabled" : ""}>
      <option value="">${esc(blank)}</option>
      <option value="NONE" ${v.toUpperCase() === "NONE" ? "selected" : ""}
        >None — no grammar</option>
      ${opts}
    </select></label>`;
}
/* The framing as a per-panel axis (A2).

   The one control in this row written in optics rather than adjectives.
   Everything else here is a word the model may interpret; a framing is
   `85–135mm, f/1.4–2, very shallow`, which it cannot satisfy by doing
   nothing — the failure that made this necessary.

   Options are the framings the panel's grammar SANCTIONS, in the grammar's
   own order, not all twenty. A grammar constrains the family without
   determining the row, and offering an Epic environmental wide under
   Subjective/Poetic would offer a contradiction as a menu item. With no
   grammar chosen, nothing has been narrowed and all twenty are offered.

   The blank option names the row it would inherit, with its settings,
   rather than saying "default" — the whole point is that the decision is
   readable BEFORE the render, not inferable from the picture after. */
function framingSelect(prefix, panel, blank, disabled = false) {
  if (!CAMERA_RECIPES.length) return "";
  const v = String(panel?.camera_recipe || "");
  const st = CINEMA_STYLES.find(x => x.key === String(panel?.cinematography || ""));
  const ids = (String(panel?.cinematography || "").toUpperCase() === "NONE" ? [] : (st?.recipes || []));
  const rows = ids.length ? ids.map(recipeByKey).filter(Boolean) : CAMERA_RECIPES;
  /* The rest of the twenty, offered under their own label rather than
     withheld (user-caught 2026-08-26: "why only 8 options?").

     They were hidden on the reasoning that a menu containing a
     contradiction will eventually be used to pick one. That is true and
     it is not this app's rule: A4.3 kept the manual camera axes exactly
     so a director can overrule the recipe on one shot, and `conflict()`
     was built to STATE a disagreement rather than prevent it. Hiding the
     option made that note unreachable — the only way to see it was to
     choose a framing and then change the grammar underneath it.

     Gates are readable as state, never enforced by absence. */
  const others = ids.length
    ? CAMERA_RECIPES.filter(r => !ids.includes(r.key)) : [];
  const inherit = ids.length ? recipeByKey(ids[0]) : null;
  /* A framing the grammar does not sanction still has to APPEAR here when
     the panel holds one — otherwise the select shows "inherit", and the
     first save of any camera axis silently replaces a framing the
     director chose on purpose. Which is this week's failure exactly: a
     decision the app changes without saying so. It is labelled, and the
     note below says what it disagrees with. */

  const opt = (r, tail = "") => `<option value="${esc(r.key)}" ${
    v === r.key ? "selected" : ""}>${esc(r.name)} — ${esc(r.focal)}, ${
    esc(r.aperture)}${esc(tail)}</option>`;
  const opts = rows.map(r => opt(r)).join("")
    + (others.length
      ? `<optgroup label="Outside this grammar — a choice, not an error">${
          others.map(r => opt(r)).join("")}</optgroup>`
      : "");
  return `<label class="cam-field cam-field-wide mini"><span>Framing</span>
    <select data-f="${prefix}-framing" ${disabled ? "disabled" : ""}
      title="The lens, aperture and focus this panel renders at. Read live from docs/CAMERA_RECIPES.md.">
      <option value="">${esc(inherit
        ? `${inherit.name} — ${inherit.focal}, ${inherit.aperture} (from the grammar)`
        : blank)}</option>
      <option value="NONE" ${v.toUpperCase() === "NONE" ? "selected" : ""}
        >None — no framing</option>
      ${opts}
    </select>
    <span class="cam-note mini" data-f="${prefix}-framing-note">${framingNote(panel)}</span></label>`;
}

/* What the note under the framing says (A3.2 and A3.3).

   Two facts, both of which the app knew and neither of which it said:

   WHY this row — written by the pass that read the scene, so a director
   can argue with the choice instead of overruling it blind.

   That the row FIGHTS its grammar, where it does. Not silently resolved
   and not refused: choosing an epic environmental wide under a
   subjective grammar is a decision. What is not a decision is the app
   knowing the two disagree and saying nothing, which is exactly how a
   production-wide 24mm sat under a selective-focus grammar for two
   days. */
/* What the bible selection carried and withheld for this panel (R1.2).

   Character Presentation used to ride every prompt whole. On one real
   panel it was 31.5% of 18,636 characters — 5,868 of them describing a
   recon pilot and a colonel who are not in the frame, on a panel whose
   required content is a hull, a pan, shivering air, a ramp and six
   figures. Nearly six times the cinematography block that had all the
   attention.

   Withholding it is the fix. SAYING so is what keeps the fix honest. */
/* What an engine has been declared to accept, or 0 (C9).

   Only a custom engine has one. The built-ins have never refused a
   prompt — 132 takes from 289 to 21,179 characters all succeeded — and
   inventing a limit for them would be inventing the constraint that
   measurement disproved.

   Filled by whichever screen last read settings; empty until then, which
   states nothing rather than stating a wrong number. */
const ENGINE_PROMPT_LIMITS = {};
function promptCap(provider) {
  return ENGINE_PROMPT_LIMITS[String(provider || "")] || 0;
}
// The engine step's own select, found from any node inside the panel
// card. Read rather than captured, because the user can change it after
// the prompt report is drawn and the number has to follow.
function chosenEngine(node) {
  return $("[data-f=model]", node?.closest?.(".panel, .stage-card") || document)?.value || "";
}

function bibleSelectionHtml(sel) {
  if (!sel || (!sel.withheld?.length && !sel.unsure)) return "";
  if (sel.unsure) {
    /* R1.3 — nothing matched, so everything was carried. The prompt did
       not shrink; the reader still learns why, because "no saving here"
       is a result and an empty panel is not. */
    return `<div class="pc-with mini">
      <b>Characters — all carried.</b> This panel names none of them, and a panel
      that names no character may still be about one — a hand, a silhouette, a chair
      someone has just left. Losing the roster is worse than carrying it.</div>`;
  }
  return `<div class="pc-with mini">
    <b>Withheld from this panel</b> — ${sel.withheld.length} line${
      sel.withheld.length === 1 ? "" : "s"} of Character Presentation, because this
    panel does not name the people ${sel.withheld.length === 1 ? "it" : "they"}
    describe${sel.withheld.length === 1 ? "s" : ""}:
    ${[...new Set(sel.withheld.map(w => w.title))].map(esc).join(" · ")}.
    The ${sel.carried} that govern any frame — how people are presented, what
    not to invent — still ride.</div>`;
}

function framingNote(panel) {
  const pick = String(panel?.camera_recipe || "");
  const gk = String(panel?.cinematography || "");
  const st = CINEMA_STYLES.find(x => x.key === gk);
  const ids = gk.toUpperCase() === "NONE" ? [] : (st?.recipes || []);
  const key = pick && pick.toUpperCase() !== "NONE" ? pick : (pick ? "" : ids[0] || "");
  const out = [];
  if (key && ids.length && !ids.includes(key)) {
    const r = recipeByKey(key);
    out.push(`${r ? r.name : key} is not a framing ${st.name} sanctions — `
      + "rendering it is a choice, not an error, but the two will pull against each other.");
  }
  const why = String(panel?.camera_recipe_why || "").trim();
  if (why && !pick) out.push(why);
  return out.map(esc).join(" ");
}
// Read the five axes back off a rendered row. The lens resolves its Custom
// number field to a focal length like "28MM"; a blank select stays "".
function readCameraFields(prefix, root) {
  const val = f => $(`[data-f=${prefix}-${f}]`, root)?.value || "";
  let lens = val("lens");
  if (lens === "CUSTOM") {
    const mm = ($(`[data-f=${prefix}-lens-mm]`, root)?.value || "").trim();
    lens = mm ? `${mm}MM` : "";
  }
  const out = { camera_angle: val("angle"), camera_orientation: val("orient"),
                camera_lens: lens, camera_tilt: val("tilt"), scale: val("scale") };
  // Only sent when the row actually drew the control — the amend route
  // touches a field only if the caller names it, so a surface without the
  // grammar select must not silently clear a panel's choice.
  if ($(`[data-f=${prefix}-grammar]`, root)) out.cinematography = val("grammar");
  if ($(`[data-f=${prefix}-framing]`, root)) out.camera_recipe = val("framing");
  return out;
}
// Toggle the Custom focal-length input as the lens select changes, and run
// `onChange` after any axis changes (each surface persists differently).
function wireCameraRow(prefix, root, onChange) {
  const lensSel = $(`[data-f=${prefix}-lens]`, root);
  const mm = $(`[data-f=${prefix}-lens-mm]`, root);
  const toggle = () => { if (mm) mm.classList.toggle("hidden", !lensSel || lensSel.value !== "CUSTOM"); };
  /* A grammar decides WHICH framings are on the menu, so changing it has
     to redraw them — otherwise the select keeps offering the previous
     grammar's rows and the inherited default names a row the new grammar
     does not sanction. Redrawn in place; the panel is not re-fetched. */
  const gram = $(`[data-f=${prefix}-grammar]`, root);
  const fram = $(`[data-f=${prefix}-framing]`, root);
  if (gram && fram) gram.addEventListener("change", () => {
    const keep = fram.value;
    const holder = document.createElement("div");
    holder.innerHTML = framingSelect(prefix, { cinematography: gram.value,
                                               camera_recipe: keep }, "");
    const next = $(`[data-f=${prefix}-framing]`, holder);
    if (next) fram.innerHTML = next.innerHTML;
    note();
  });
  const note = () => {
    const el = $(`[data-f=${prefix}-framing-note]`, root);
    if (el && gram && fram) el.textContent = framingNote(
      { cinematography: gram.value, camera_recipe: fram.value });
  };
  if (fram) fram.addEventListener("change", note);
  root.querySelectorAll(`[data-f^="${prefix}-"]`).forEach(el =>
    el.addEventListener("change", () => { toggle(); if (onChange) onChange(); }));
}

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
// Does this engine hand the reference IMAGES to the image model, or only
// words about them? Server-declared (generate.sends_plates) so the two can
// never drift; a missing flag means yes, which is true of every engine
// that speaks the OpenAI Images API.
const sendsPlates = (settings, provider) => {
  const m = (settings.provider_meta || {})[provider];
  if (!m) return true;
  if ("plates" in m) return !!m.plates;
  if ("refs" in m) return !!m.refs;
  return true;
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
  // Whether an engine puts the reference PLATES in front of the image
  // model is the single most consequential thing about it in this app, and
  // the list used to read as three interchangeable names (user-caught
  // 2026-08-16: a likeness plate and a render of a different man). It is a
  // fact about the engine, so it rides in Courier on the option itself.
  return usable.map(([v, label]) =>
    `<option value="${esc(v)}" ${v === sel ? "selected" : ""}>${esc(label)}${
      sendsPlates(settings, v) ? "" : "  ·  NO REFERENCE IMAGES"}</option>`).join("")
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
  // Stage 04 stays per-revision (it is the working surface); a revision
  // labels itself as one: "BASE · R2 — subject".
  sel.innerHTML = `<option value="">— select a signed-off breakdown —</option>` +
    specs.map(s => `<option value="${esc(s.specification_id)}">${
      revOf(s) > 1 ? `${esc(baseOf(s.specification_id))} · R${revOf(s)}`
                   : esc(s.specification_id)} — ${esc(s.subject)}</option>`).join("");
  sel.onchange = () => { uiSet("boardSpec", sel.value); syncUrl(true); sel.value && renderBoardPanels(sel.value); };
  // U3 (HARNESS_AUDIT): a stage that knows what you were doing must not
  // ask. Land on the last breakdown worked (remembered per production),
  // else the first signed-off one — the select stays as a switcher above
  // the loaded work, never as the whole screen.
  const rememberedB = uiGet("boardSpec", "");
  if (rememberedB && specs.some(s2 => s2.specification_id === rememberedB)) {
    sel.value = rememberedB; renderBoardPanels(rememberedB);
  } else if (specs.length) {
    sel.value = specs[0].specification_id;
    uiSet("boardSpec", sel.value);
    renderBoardPanels(sel.value);
  }
  if (!specs.length) {
    $("#board-panels").innerHTML =
      `<div class="panel mini">No signed-off breakdowns yet — panels render from a locked breakdown.
       <button class="text-act" data-f="to-specs">Open Breakdowns</button></div>`;
    $("[data-f=to-specs]").onclick = () => showView("specs");
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

function renderCard(specId, c, refresh, lbItems = null, lbIndex = 0, getRefs = null, size = "thumb") {
  const cc = document.createElement("div");
  cc.className = `ref-card ${c.status === "REJECTED" ? "REJECTED" : ""}`;
  const label = c.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : c.status;
  const meta = c.kind === "assembled_board"
    ? `${c.width}×${c.height} 4K board${c.layout_variant && c.layout_variant !== "default" ? ` · ${esc(c.layout_variant)} layout` : ""} · panels: ${esc(Object.values(c.panels_used || {}).join(", "))}`
    : `${c.width}×${c.height} · ${esc(c.image_size || "")} ${esc(c.aspect_ratio || "")} · ${esc(c.model || "")} · refs: ${esc((c.references || []).map(r => r.id).join(", ") || "none")}`;
  cc.innerHTML = `
    <img src="/api/specs/${specId}/candidates/${c.candidate_id}/image?size=${size}" loading="lazy" alt="${esc(c.candidate_id)}">
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
        // User-caught 2026-08-23: "the board is still locked" right after
        // approving a panel. It was not a lock bug — approving is what
        // OPENS stage 05, and the band simply never re-read. The two
        // earlier transitions (breakdown lock, panel unlock) each call
        // this on purpose; the last one in the chain was missed, so
        // Boards opened silently on the next navigation instead of now.
        updateBand();
      } catch (err) { toast(err.message, true); }
    };
    actions.append(b);
  } else {
    // The same withdrawal the workbench offers — the gallery is where a
    // user lands when they are reviewing what is already approved, so it
    // is where they realise one should go back into draft.
    const wd = document.createElement("button");
    wd.className = "ghost"; wd.textContent = "Withdraw approval";
    wd.title = "Put this panel back into draft. The take keeps its image; "
             + "unlike Reject it records no reason and carries nothing into "
             + "future prompts.";
    wd.onclick = async () => {
      try {
        await post(`/api/specs/${specId}/candidates/${c.candidate_id}/unapprove`);
        toast(`${c.candidate_id} back to CANDIDATE — the panel is editable again.`);
        refresh();
        updateBand();  // withdrawal can CLOSE 05 again — same fact, reversed
      } catch (err) { toast(err.message, true); }
    };
    actions.append(wd);
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
        proposeCorrections(specId, c.candidate_id, refresh);
      } catch (err) { toast(err.message, true); }
    };
    actions.append(b);
  } else {
    const b = document.createElement("button");
    b.className = "danger"; b.textContent = "Delete forever";
    b.title = "Permanently remove this rejected image and its record from disk";
    b.onclick = async () => {
      if (!(await askConfirm(`Delete ${c.candidate_id} forever`,
        "The image file is removed from disk and cannot be recovered. Its rejection reason keeps riding this panel's future prompts as a director's correction, and stays in the rejection history.",
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

// A long render can outlive the request: a gateway cuts the connection at ~1 min
// but the engine finishes and the take lands on disk (user 2026-08-09). When that
// happens we don't fail — we keep waiting and poll for the new candidate on this
// panel. Returns the fresh record, or null if it never appears within the budget.
async function pollForNewTake(specId, panelId, beforeIds, { tries = 40, delayMs = 5000, signal } = {}) {
  for (let i = 0; i < tries; i++) {
    await new Promise(r => setTimeout(r, delayMs));
    // Cancel works mid-poll too (2026-08-12 review): once the fetch has
    // already failed, abort() has nothing to abort — the poll itself must
    // honor it, or Cancel is a silent no-op for the whole 200s budget.
    if (signal?.aborted) return null;
    try {
      const cands = await api(`/api/specs/${specId}/candidates`);
      const fresh = (cands || []).find(c =>
        c.panel_id === panelId && !beforeIds.has(c.candidate_id));
      if (fresh) return fresh;
    } catch { /* transient — keep waiting */ }
  }
  return null;
}

// Add a panel from the workbench (user 2026-08-09): the sheet stays locked, the
// panel lands as a work order, and the lock re-stamps server-side
// (store.add_panel) — the same controlled edit as the between-takes brief change.
async function addPanelDialog(specId) {
  const res = await modal({
    title: "Add a panel",
    body: "It joins this breakdown as a work order, ready to generate. The breakdown's lock re-stamps; existing takes keep the hash they were painted against.",
    fields: [
      { name: "title", label: "Panel title", placeholder: "e.g. The Pioneer's Workshop" },
      { name: "purpose", label: "Brief", textarea: true,
        placeholder: "What this panel must show — the brief every take is painted from.",
        hint: "The panel's purpose; it steers the render until objects are added on the breakdown." },
    ],
    confirmLabel: "Add panel",
  });
  if (!res) return;
  if (!res.purpose) { toast("A brief is required — it is the only thing steering the render.", true); return; }
  try {
    const p = await api(`/api/specs/${specId}/panels`, { method: "POST",
      json: { title: res.title, purpose: res.purpose } });
    toast(`${p.id} added — a work order at 0% allocation; balance it on the breakdown before assembly.`);
    await renderBoardPanels(specId);
  } catch (err) { toast(err.message, true); }
}

// Correction intake (2026-08-13): after a rejection saves, the reason is
// parsed into proposed structural deltas (camera axis, require/forbid,
// brief extension) shown under CARRIED REJECTIONS for the user to apply.
// Advisory and best-effort — a missing narrative key must never make
// rejecting itself feel broken, so failures stay silent here.
async function proposeCorrections(specId, candId, onDone) {
  try {
    const r = await api(`/api/specs/${specId}/candidates/${candId}/correction-intake`,
      { method: "POST", json: {} });
    if ((r.deltas || []).length) {
      toast(`${candId} — ${r.deltas.length} structural delta${r.deltas.length === 1 ? "" : "s"} proposed from the rejection. Review them under CARRIED REJECTIONS.`);
      if (onDone) onDone();
    }
  } catch (err) { /* advisory only */ }
}

async function renderBoardPanels(specId) {
  const host = $("#board-panels");
  // The per-panel grammar select names the grammars, so the library has to
  // be here before the card is drawn. Cached after the first call.
  // The framing select needs both: the recipes for its options, and the
  // grammars for which ones that panel's grammar sanctions.
  await Promise.all([loadCinemaStyles(), loadCameraRecipes()]);
  // A REDRAW is not a LOAD (user 2026-08-16: "when I click on the frames in
  // the strip the page jumps to the top"). Staging a take, saving a camera,
  // withdrawing an approval and saving a prompt all call this — and blanking
  // the host to "Loading…" collapses the page to nothing, so the browser
  // clamps the scroll to 0 and the card you were working in leaves the
  // screen. On a redraw the old DOM stays up until the new one is ready,
  // and the scroll goes back where it was.
  const isRedraw = !!host.querySelector(".wb-card");
  const keepY = window.scrollY;
  if (!isRedraw) host.innerHTML = `<div class="panel mini">Loading…</div>`;
  const [{ spec, lock_hash: lockHash }, refs, candidates, appSettings, slotMap, boards, camDefaults, carriedFb] = await Promise.all([
    api(`/api/specs/${specId}`),
    api("/api/references"),
    api(`/api/specs/${specId}/candidates`),
    api("/api/settings"),
    api(`/api/specs/${specId}/slot-map`).catch(() => null),
    api(`/api/specs/${specId}/boards`).catch(() => []),
    api("/api/camera-defaults").catch(() => ({})),
    api(`/api/specs/${specId}/carried-feedback`).catch(() => ({ items: [] })),
  ]);
  const prefProvider = appSettings.preferred_provider || "gemini";
  const prefKeyFailed =
    appSettings.engines?.[prefProvider]?.last_test?.ok === false;
  const genGateTitle = prefKeyFailed
    ? "The default engine's key failed its last test — retest it in Settings or pick another default in the Model Test."
    : "";
  // `isAutoStyle` used to live here with two of the four auto-attach roles
  // and no per-role cap (adversarial review F8). AUTO_ATTACH_HEADS has held
  // the correct four since 2026-08-03 — in this same file, used two screens
  // away — so the manifest was reading a second, wrong list. The manifest
  // now comes from the server; these two derivations only decide which
  // groups are OFFERED as tickable, and they use the correct list.
  const isAutoStyle = r => AUTO_ATTACH_HEADS.includes(roleHead(r.role));
  // Panels this revision declared unchanged (scope survives the lock):
  // locked on this workbench, takes flow to the board from elsewhere.
  const carriedRail = new Set(spec.revision_scope?.carried || []);
  const styleAnchors = refs.filter(r => r.status === "APPROVED" && isAutoStyle(r));
  // Swatches leave the generic subject groups (2026-08-13, user): they
  // have no role suffix, so all of them collapsed into ONE checkbox that
  // attached the whole palette — 19 references on every render. They get
  // their own per-swatch selector at the top of the rendering settings.
  const swatchRefs = refs.filter(r =>
    r.status === "APPROVED" && roleHead(r.role) === "COLOR_PALETTE");
  const approvedRefs = refs.filter(r => r.status === "APPROVED"
    && !isAutoStyle(r) && roleHead(r.role) !== "COLOR_PALETTE");
  host.innerHTML = "";

  // The workbench can add a panel to the locked sheet (it lands as a work
  // order; the lock re-stamps server-side). The button lives in the screen
  // header, so it survives the host rewrite — re-wire it each render.
  const addPanelBtn = $("#board-add-panel");
  if (addPanelBtn) { addPanelBtn.hidden = false; addPanelBtn.onclick = () => addPanelDialog(specId); }

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
    // The fourth copy of "does this phrase name that thing" (user-caught
    // 2026-08-16: this panel has "Sal's eyes" with no REF — "it should
    // find that ref because I have Sal Ref"). It asked whether either
    // string CONTAINED the other, so the group "SAL CRAFT" did not match
    // the object "Sal's eyes" and the plates never even offered
    // themselves. The same defect as the workbench's subjectFor and
    // generate.py's identity block, in the copy that drives the visible
    // green REF marker AND the first-take tick default — so a Sal panel
    // rendered with no Sal plate and nothing said why.
    // ...and the production can overrule it per object. The matcher cannot
    // read grammar — "airlock hatch behind Sal" names Sal because Sal is in
    // the phrase, though the object is an airlock and Sal is only where it
    // sits (user-caught 2026-08-16). Guessing harder is the wrong answer;
    // being correctable is the right one.
    const excluded = obj => (p.ref_exclusions || {})[String(obj)] || [];
    const matches = (obj, name) =>
      !excluded(obj).includes(name) && namesPhrase(obj, name);
    const objHasRef = obj => groupList.some(g => matches(obj, g.name));
    const reqObjs = p.required_objects || [];
    const withRef = reqObjs.filter(objHasRef).length;

    // P3: the user is about to spend a render — everything the render
    // obeys goes in the sequence. Forbidden states its provenance (panel
    // vs inherited from the board) in step 02; SCOPE carries the
    // languages, environment and slugline the prompt will actually use,
    // stated in step 05 beside the prompt it feeds.
    const ownForbid = p.forbidden_objects || [];
    const boardForbid = (spec.forbidden_elements || [])
      .filter(f => !ownForbid.some(o => String(o).toLowerCase() === String(f).toLowerCase()));
    const forbidChips = [...ownForbid, ...boardForbid].map(f =>
      `<span class="forbid-chip">${esc(String(f).toUpperCase())}</span>`).join("");
    const forbidHead =
      `${ownForbid.length ? `${ownForbid.length} ON THIS PANEL` : "NOTHING ON THIS PANEL"}`
      + ` · ${boardForbid.length} INHERITED FROM THE BOARD`;

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

    const roomSel = boardRoomSel[specId];
    roomSel.staged ??= {};
    let staged = panelCands.find(c => c.candidate_id === roomSel.staged[p.id]) || panelCands[0] || null;
    const role = p.composition_role === "hero" ? "HERO" : "STRIP";

    // STEP_SEQUENCE_SPEC §1.0/§2.15: the take is displayed at the PANEL's
    // own shape, never a fixed height that letterboxes it. A panel has no
    // declared aspect field — its established shape is whatever its last
    // take rendered at, which is also what the Aspect select must default
    // to (§2.4: the select hardcoded 16:9 and silently re-shaped a hero
    // panel between takes).
    const aspectList = appSettings.aspects || ASPECT_FALLBACK;
    const panelAspect = panelCands[0]?.aspect_ratio
      || (aspectList.some(a => a.id === "16:9") ? "16:9" : aspectList[0]?.id) || "16:9";
    const aspectLabel = (aspectList.find(a => a.id === panelAspect) || {}).label
      || panelAspect;
    const aspectCss = (() => {
      const [w, h] = String(panelAspect).split(":").map(Number);
      return w > 0 && h > 0 ? `${w}/${h}` : "16/9";
    })();

    // Step confirmations (§1.7). Advisory by design — §2.4 rules the gate
    // honest, so an unconfirmed step never blocks a render. That makes a
    // tick a reading posture over data already on screen, so it lives in
    // per-production UI state rather than canon. Editing a step's own
    // subject clears its tick, and any change upstream clears 05: a
    // confirmation that outlives what it confirmed is a lie.
    const CONF_STEPS = ["brief", "objects", "camera", "references", "prompt"];
    const confKey = `wbconf.${specId}.${p.id}`;
    const confAll = () => uiGet(confKey, {});
    const confIs = s => !!confAll()[s];
    const confSet = (s, on) => {
      const c = { ...confAll() };
      if (on) c[s] = 1; else delete c[s];
      if (s !== "prompt") delete c.prompt;
      uiSet(confKey, c);
    };
    // An approved take settles every step of its panel, so the count says
    // so rather than reporting ticks the user never had to make.
    const confCount = panelCands.some(c => c.status === "APPROVED")
      ? CONF_STEPS.length : CONF_STEPS.filter(confIs).length;

    const takeItems = panelCands.map(c => ({
      src: `/api/specs/${specId}/candidates/${c.candidate_id}/image`,
      caption: `${c.candidate_id} — ${p.id} (${c.status}) ${c.width}×${c.height}`,
      // B10: the fact travels with the picture.
      grammar: c.cinematography?.rides
        ? String(c.cinematography.name || "").toUpperCase() : "",
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
      <div class="stage-shot stage-hero" style="aspect-ratio:${aspectCss}" title="Click to open at full size">
        <img src="/api/specs/${specId}/candidates/${staged.candidate_id}/image?size=md" alt="${esc(staged.candidate_id)}" data-f="shot-img">
        <!-- T1 (TAKE_ACTIONS): state and identity ride the image so the
             row beneath carries verbs only and can fit. A chip swallows
             its own click; the picture opens the lightbox. §2.15 adds the
             pixel size to the image it describes — the frame carries the
             PANEL's shape, so a take is never letterboxed into a frame
             that lies about it. -->
        <span class="shot-tag shot-tag-state shot-status ${esc(staged.status)}">${staged.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : esc(staged.status)}</span>
        <span class="shot-tag shot-tag-id">${esc(staged.candidate_id)} · TAKE ${
          panelCands.length - panelCands.indexOf(staged)} OF ${panelCands.length}${
          stagedRef ? ` · REF ${esc(stagedRef)}` : ""}</span>
        <span class="shot-tag shot-tag-size">${staged.width} × ${staged.height} · ${
          esc(staged.aspect_ratio || "")} · NATIVE, NEVER UPSCALED</span>
        <span class="shot-tag shot-tag-run">${[
          staged.created_at ? `RUN ${esc(String(staged.created_at).slice(0, 16).replace("T", " "))}` : "",
          esc(staged.model || ""),
          staged.spec_hash ? `HASH ${esc(String(staged.spec_hash).slice(0, 8))}` : "",
        ].filter(Boolean).join("  ·  ")}</span>
        <!-- B10 (RULE_PASS 2026-08-16): facts about an image ride ON it.
             A take recorded whether the cinematography grammar rode it and
             no screen said so, which made the experiment unevaluable — the
             whole reason the switch exists. Absent entirely on a take that
             did not ride. -->
        <button type="button" class="shot-tag shot-tag-prompt" data-f="read-sent"
          title="Read the exact text this take was rendered from">${
          staged.render_prompt ? "SENT — HAND-EDITED" : "SENT — THE COMPILE"} ↗</button>
        ${staged.cinematography?.rides
          ? `<button type="button" class="shot-tag shot-tag-grammar" data-f="read-cine"
               data-key="${esc(staged.cinematography.key || "")}"
               title="Read this cinematography — the words the render was given">CINEMATOGRAPHY — ${
              esc(String(staged.cinematography.name || "").toUpperCase())} · ${
              staged.cinematography.from === "panel" ? "THIS PANEL" : "PRODUCTION DEFAULT"} ↗</button>`
          : ""}
        <!-- A2.3 — and the framing, beside the grammar. Two decisions,
             and the difference between a take under a grammar alone and
             one under both is large: the grammar says "selective focus",
             the framing says f/1.4–2. Until this the only place that
             difference showed was the picture. -->
        ${staged.camera_recipe?.in_prompt === false
          ? `<span class="shot-tag shot-tag-framing shot-tag-didnt">FRAMING — NOT IN THIS PROMPT · ${
              esc(String(staged.camera_recipe.would_be_name || "").toUpperCase())
            } WOULD RIDE A RECOMPILE</span>`
          : staged.camera_recipe?.rides
          ? `<span class="shot-tag shot-tag-framing">FRAMING — ${
              esc(String(staged.camera_recipe.name || "").toUpperCase())} · ${
              esc(staged.camera_recipe.focal || "")}, ${
              esc(staged.camera_recipe.aperture || "")}, ${
              esc(String(staged.camera_recipe.focus || "").toUpperCase())}${
              (staged.camera_recipe.mods || []).length
                ? ` · +${staged.camera_recipe.mods.length} MODIFIER${
                    staged.camera_recipe.mods.length === 1 ? "" : "S"}` : ""}</span>`
          : ""}
      </div>
      <!-- 17a (2026-08-08, superseding 14a's one-grammar row): one boxed
           amber verdict, six text acts in two LABELLED groups, Reject
           fenced right. The kickers say what the labels cannot — USE
           produces another take of THIS panel; DERIVE produces a record
           somewhere else, and reads dimmer because nothing in it advances
           this panel toward approval. -->
      <!-- §2.5: the USE / DERIVE kickers say what the labels cannot — USE
           produces another take of THIS panel, DERIVE produces a record
           somewhere else. Reject joins its own group (the spec and mock
           4a both place it under USE beside Approve; 17a had fenced it
           right, where it read as a fourth group of one). The run facts
           take the right edge — they describe the picture above. -->
      <div class="act-bar">
        <span class="act-zone act-use">
          <span class="act-kicker">USE</span>
          <span class="act-items act-approve" data-f="act-approve"></span>
          <span class="act-items" data-f="act-use"></span>
          <span class="act-items" data-f="act-danger"></span>
        </span>
        <span class="act-zone act-derive">
          <span class="act-kicker">DERIVE</span>
          <span class="act-items" data-f="act-derive"></span>
          <button type="button" class="text-act act-dim act-more" data-f="derive-more"
            title="Derive — Reference, Crop to reference, Light study">&ctdot;</button>
        </span>
        <span class="act-spacer" aria-hidden="true"></span>
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
      <div class="takes filmstrip">
        <div class="takes-head">
          <span class="f-label">Takes · ${panelCands.length}${pending.length ? ` <span style="color:var(--accent)">· ${pending.length} painting</span>` : ""}</span>
          <span class="hint">rejected takes stay as a record</span>
          ${staged && (staged.model_notes || staged.render_prompt) ? `<button class="text-act" data-f="notes">${staged.prompt_source === "edited" ? "Edited render prompt" : "Model notes / rewritten prompt"}</button>` : ""}
          ${sheetRejected ? `<button class="danger" data-f="purge" title="Removes the image files from disk — each rejection reason keeps riding its own panel's future prompts as a director's correction">Delete ${sheetRejected} rejected forever</button>` : ""}
        </div>
        <div class="takes-row filmroll">
          ${pending.map(pendingTileHtml).join("")}
          ${panelCands.map(c => {
            const pr = promotedRefOf(c);
            const isShown = staged && c.candidate_id === staged.candidate_id;
            // STATUS wins the word; selection is the ink outline (user-caught
            // 2026-08-16). "SHOWN" first meant an approved take you were
            // looking at lost its APPROVED caption altogether — the durable
            // fact reads, and the transient one is drawn.
            const word = c.status === "APPROVED" ? "APPROVED"
              : c.status === "REJECTED" ? "REJECTED"
              : isShown ? "SHOWN" : "";
            return `
            <button class="take${isShown ? " shown" : ""}${c.status === "REJECTED" ? " rejected" : ""}${c.status === "APPROVED" ? " approved" : ""}"
                    data-take="${esc(c.candidate_id)}"
                    title="${esc(c.candidate_id)} (${esc(c.status)})${pr ? ` — promoted to ${esc(pr)}` : ""}${c.status_reason ? ` — ${esc(c.status_reason)}` : ""}${isShown ? "" : " — click to show this take"}">
              <!-- The frame is a 35mm window (user 2026-08-15) and the take
                   is FITTED inside it, longest edge first — a strip of
                   identical frames reads as film; a strip that changes
                   shape per panel reads as a grid. -->
              <span class="take-frame">
                <img src="/api/specs/${specId}/candidates/${c.candidate_id}/image?size=thumb" loading="lazy" alt="">
              </span>
              <span class="take-cap">${esc(c.candidate_id)}${word ? ` · ${word}` : ""}${pr ? " · REF" : ""}</span>
            </button>`;
          }).join("")}
        </div>
      </div>`;

    const card = document.createElement("div");
    card.className = "panel seq wb-card";

    // The brief is editable BETWEEN takes (user 2026-08-08: a purpose that
    // says "the three people" keeps painting three people, and the only fix
    // lived behind a full unlock). The amend is journaled server-side and
    // the lock re-stamps; an APPROVED take freezes the brief it was
    // approved against — the gate reads as state here, before it is hit.
    const frozen = panelCands.some(c => c.status === "APPROVED");

    // The reference selection is REMEMBERED generation to generation (user
    // 2026-08-08): every take records which references it attached, so the
    // newest take of this panel is the memory — no new storage, survives
    // reloads and devices, and unticking everything is remembered too. The
    // keyword matcher is only the first-take default.
    const lastTake = panelCands[0];
    const lastRefIds = new Set((lastTake?.references || []).map(r => r.id));
    // A take-derived memory can only remember what has already been
    // RENDERED. It cannot hold an intention — and the moment between
    // ticking a reference and generating with it is exactly when a user
    // has one. First user test, 2026-08-23: he added "dark ship", ticked
    // it, rejected the take, generated — and the new take attached the
    // palette and nothing else. Rejecting redraws the card, the redraw
    // re-read the newest take, and the newest take was the one he had
    // just rejected, which never carried the ship.
    //
    // So a saved pick outranks the derivation. `null` means this panel has
    // never chosen and the old behaviour stands; `[]` means the user
    // deliberately unticked everything, which must not silently revert to
    // whatever the last render happened to use.
    const savedRefIds = Array.isArray(p.ref_ids) ? new Set(p.ref_ids) : null;
    buildWorkbench.isChecked = g => savedRefIds
      ? g.ids.some(id => savedRefIds.has(id))
      : lastTake
        ? g.ids.some(id => lastRefIds.has(id))
        : reqObjs.some(o => matches(o, g.name));
    // §2.3: references are not a free choice — the app has already ticked
    // them and can say why, so every row states its reason AND the off rows
    // state theirs. The two rules never both fire (matches-an-object is the
    // first-take default only), so a row never shows a reason it cannot have.
    const refWhy = savedRefIds ? "YOU PICKED THIS"
      : lastTake ? "RODE THE PREVIOUS TAKE" : "MATCHES A REQUIRED OBJECT";
    const refWhyOff = savedRefIds ? "YOU LEFT THIS OFF"
      : lastTake
        ? "DID NOT RIDE THE PREVIOUS TAKE"
        : "NOTHING ON THIS PANEL NAMES THEIR SUBJECT";

    const approvedN = panelCands.filter(c => c.status === "APPROVED").length;
    const takesWord = !panelCands.length ? "NO TAKES YET"
      : `${panelCands.length} TAKE${panelCands.length === 1 ? "" : "S"}, ${
          approvedN ? `${approvedN} APPROVED` : "NONE APPROVED"}`;

    // The shared renderer (seqStep) with this surface's confirmation store
    // bound in — stage 03 binds its own.
    const approvedTakes = panelCands.filter(c => c.status === "APPROVED")
      .map(c => c.candidate_id);
    const step = o => seqStep({
      ...o,
      done: !!(o.id && confIs(o.id)),
      frozen: approvedTakes.length > 0,
      // Named the fact but not the door. A user who cannot change the
      // camera needs to know WHERE the approval is withdrawn, not only
      // that one exists (2026-08-24: "it says I cant change camera... I
      // get the 'no' icon when i hover over change camera").
      frozenWhy: approvedTakes.length
        ? `FROZEN BY ${approvedTakes.join(", ")} — WHAT THIS PANEL ASKS FOR IS `
          + "SETTLED WHILE A TAKE IS APPROVED. USE WITHDRAW APPROVAL ON THAT "
          + "TAKE IN THE STRIP ABOVE TO CHANGE IT. GENERATING A NEW TAKE IS "
          + "NEVER BLOCKED."
        : "",
    });

    const camAxes = ["camera_angle", "camera_orientation", "camera_lens",
                     "camera_tilt", "scale"];
    // The grammar is an axis of this step too — it is set in this editor
    // and saved by this button. Leaving it out of `camOwn` meant a panel
    // that named its OWN cinematography still read "— PRODUCTION DEFAULT".
    const camOwn = camAxes.some(k => p[k]) || !!p.cinematography;
    const camRv = k => String(p[k] || camDefaults?.[k] || "—").replace(/_/g, " ");
    // Orientation states itself only when set — it has no baseline, and a
    // standing "—" would read as a missing value rather than a free axis.
    const camOrient = String(p.camera_orientation
      || camDefaults?.camera_orientation || "").replace(/_/g, " ");
    // The axes are stored uppercase (EYE_LEVEL); §1.2 makes this line prose,
    // and prose is sentence case — the Courier caps beside it are the
    // machine facts, this is what a person reads.
    // User-caught 2026-08-24: "It did not update the cinematography style
    // on the new take after I changed it." It did — it saved, and it rode.
    // But this line listed the five camera axes and NOT the grammar, and
    // this line is the whole of what the step shows once the editor
    // closes. So changing the cinematography left the panel looking
    // byte-identical, and the only place the change surfaced was a tag on
    // a take that had not been rendered yet.
    // Three renders were spent on panels that did not carry the setting the
    // user had made on a DIFFERENT panel (2026-08-25). The take's stamp
    // knew — "from": "panel" vs "production" — and no screen showed it, so
    // "my grammar is live here" and "this panel inherits" looked identical
    // both before and after paying. The axis is per-panel; the screen has
    // to say so on the panel.
    const camGrammar = (() => {
      const v = String(p.cinematography || "");
      if (!v) return "";
      if (v.toUpperCase() === "NONE") return "no cinematography grammar";
      const st = (CINEMA_STYLES || []).find(x => x.key === v);
      return st ? st.name.toLowerCase() : "";
    })();
    /* The one line the step shows once the editor closes, so it has to be
       what the next take will actually paint from.

       It was not. It listed the five axes resolved against the PRODUCTION
       DEFAULT, and A2 made the compiler stop using that default the
       moment a framing resolves — so a panel on Subjective / Poetic read
       "Low · 24mm · level · wide" while its render would use 50–100mm at
       f/1.4–2.8, and the word Framing appeared nowhere (user-caught
       2026-08-26). A step that states a camera the render will not use is
       the failure this whole week was about.

       So: the framing leads when there is one, only axes THIS PANEL set
       follow it, and the production default is named as a fallback only
       when nothing has displaced it. */
    const camFraming = (() => {
      const v = String(p.camera_recipe || "");
      if (v.toUpperCase() === "NONE") return null;
      const gk = String(p.cinematography || "");
      const st = CINEMA_STYLES.find(x => x.key === gk);
      const key = v || (gk.toUpperCase() === "NONE" ? "" : (st?.recipes || [])[0] || "");
      return key ? recipeByKey(key) : null;
    })();
    const camSummary = (() => {
      const own = k => String(p[k] || "").replace(/_/g, " ");
      const axes = camFraming
        ? [own("camera_angle"), own("camera_orientation"), own("camera_lens"),
           own("camera_tilt"), own("scale")].filter(Boolean)
        : [camRv("camera_angle"), camOrient, camRv("camera_lens"),
           camRv("camera_tilt"), camRv("scale")].filter(Boolean);
      const lead = camFraming
        ? `${camFraming.name} · ${camFraming.focal} · ${camFraming.aperture} · ${
            camFraming.focus.toLowerCase()} focus`
        : "";
      const s = [lead, axes.join(" · ").toLowerCase()].filter(Boolean).join(" · ");
      const head = camFraming ? s : s.charAt(0).toUpperCase() + s.slice(1);
      return camGrammar
        ? `${head} — ${camGrammar} (this panel)`
        : `${head} — cinematography inherited from the production`;
    })();

    // Which PLATES of a group ride (user ruling 2026-08-15). Precedence:
    // an explicit narrowing the user made in the viewer, then the memory
    // of what rode the last take, then the whole group. A group whose
    // plates were all unticked is off, not empty.
    const pickKey = `refpick.${specId}.${p.id}`;
    const picks = () => uiGet(pickKey, {});
    const pickFor = g => {
      const saved = picks()[g.name];
      if (Array.isArray(saved)) return g.ids.filter(id => saved.includes(id));
      if (lastTake) {
        const rode = g.ids.filter(id => lastRefIds.has(id));
        if (rode.length) return rode;
      }
      return g.ids;
    };
    const setPick = (g, ids) => {
      uiSet(pickKey, { ...picks(), [g.name]: ids });
    };

    const onGroups = groupList.filter(buildWorkbench.isChecked);
    const offGroups = groupList.filter(g => !buildWorkbench.isChecked(g));
    const groupRow = (g, on) => {
      const use = pickFor(g);
      const narrowed = use.length !== g.ids.length;
      return `
      <label class="ref-row${on ? " on" : ""}" data-was="${on ? "1" : ""}"
             data-group="${esc(g.name)}"
             title="${esc(use.join(", ") || "no plates selected")} — click to ${on ? "detach" : "attach"} this group">
        <input type="checkbox" data-ids="${esc(JSON.stringify(use))}" ${on && use.length ? "checked" : ""}>
        <span class="ref-name mono">${esc(g.name)}</span>
        <span class="ref-kind">${esc(g.head.replaceAll("_", " ").toLowerCase())} · ${
          narrowed ? `${use.length} OF ${g.ids.length}` : g.ids.length}</span>
        <span class="ref-ids mono">${idSpan(use)}</span>
        <span class="ref-why mono">${on ? refWhy : ""}</span>
        <button type="button" class="verb ref-plates" data-plates="${esc(g.name)}"
          title="See the photos and choose which of them the render works from">${
          g.ids.length > 1 ? "Choose plates" : "View plate"}</button>
      </label>`;
    };

    card.innerHTML = `
      <div class="wb-head">
        <span class="pid-badge">${esc(p.id)}</span>
        <h2 class="seq-subject">${esc(p.title || p.purpose)}</h2>
        <span class="wb-facts mono">${[alloc ? `${alloc}%` : "", role,
          String(aspectLabel).toUpperCase()].filter(Boolean).join("  ·  ")}</span>
        <span class="wb-progress mono">${confCount} OF 5 STEPS ${
          approvedTakes.length ? "SETTLED" : "CONFIRMED"}  ·  ${takesWord}</span>
      </div>
      ${stagedHtml}
      ${takesHtml}
      <div class="steps">
        ${step({ n: "01", id: "brief", label: "BRIEF",
          verbs: `
            <button type="button" class="verb" data-f="scan-scene"
              ${frozen ? "disabled" : ""} title="${frozen
                ? "An approved take was painted from this panel. Withdraw it first to change what the panel says."
                : "Say anything about this panel — a question, a correction, a feeling, a paste from elsewhere — and the screenplay scene behind it is read again against what you said. One text call, no render; nothing changes until you accept a proposal."}">Tell me about this panel</button>
            <button type="button" class="verb" data-f="brief-edit"
              ${frozen ? "disabled" : ""} title="${frozen
                ? "An approved take was painted from this brief. Reject it first to change what the panel asks for."
                : "Rewrite what this panel asks for — the next take is painted from the new brief"}">Edit brief</button>`,
          body: `
            <div class="brief-row" data-f="brief-row">
              <p class="step-prose" data-f="brief-text">${esc(p.purpose)}</p>
            </div>
            <div class="brief-editor hidden" data-f="brief-editor">
              <textarea data-f="brief-input" rows="2"></textarea>
              <div class="brief-acts">
                <button type="button" class="ghost" data-f="brief-save">Save brief</button>
                <button type="button" class="verb" data-f="brief-cancel">Cancel</button>
                <span class="mini mono">JOURNALED · NEXT TAKE PAINTS FROM THE NEW BRIEF · NOTHING ELSE INHERITS IT</span>
              </div>
            </div>` })}

        ${step({ n: "02", id: "objects", label: "REQUIRED",
          meta: `${reqObjs.length} OBJECT${reqObjs.length === 1 ? "" : "S"} · ${withRef} WITH A REFERENCE`,
          verbs: `<button type="button" class="verb" data-f="to-breakdown"
            title="Required objects are authored on the breakdown — opens 03 Breakdowns for this sheet">Edit objects</button>`,
          body: `
            <div class="obj-grid">${reqObjs.map(o => `
              <span class="obj-tile">${esc(o)}${objHasRef(o)
                ? `<button type="button" class="obj-ref" data-viewref="${esc(o)}"
                     title="View the matching reference plate(s) in the lightbox">REF</button>`
                : `<button type="button" class="obj-ref obj-ref-add" data-addref="${esc(o)}"
                     title="No reference matches this object — supply one right here; it enters the library approved and attaches like any other">+ REF</button>`}</span>`).join("")
              || '<span class="mini">none — this panel is steered by its purpose alone</span>'}</div>
            <div class="step-note mono">+ FORBIDDEN ${ownForbid.length + boardForbid.length} · ${forbidHead}</div>
            ${forbidChips ? `<div class="step-note mono step-forbid">${
              [...ownForbid, ...boardForbid].map(f => esc(String(f).toUpperCase())).join("  ·  ")}</div>` : ""}` })}

        ${step({ n: "03", id: "camera", label: "CAMERA",
          // The blank option used to read "from bible", which named the
          // wrong document entirely (user-caught 2026-08-16: "what does
          // 'from Bible' mean?"). The default is the production's camera
          // grammar, set on the Cinematography anchor in Production
          // Design — nothing to do with the Art Direction Bible.
          meta: camOwn ? "— THIS PANEL" : "— PRODUCTION DEFAULT",
          verbs: `<button type="button" class="verb" data-f="cam-open"
            ${frozen ? `disabled title="Frozen by an approved take — it was composed at this camera; the setting unfreezes if the take is rejected"` : ""}>Change camera</button>`,
          body: `
            <div class="cam-inline" data-f="cam-inline">
              <div class="cam-stated">
                <span class="step-prose cam-sum">${esc(camSummary)}</span>
              </div>
              ${(() => {
                const notes = [
                  camFraming ? "" : camOrient ? "" : "VIEW NOT FIXED — PRODUCTION DEFAULT",
                  camFraming ? "FRAMING SET — THE PRODUCTION DEFAULT DOES NOT RIDE THIS PANEL" : "",
                  scopeBits.length ? `SETTING ${esc(scopeBits.slice(-2).join(" "))} OVERRIDES THE HOUR AND HUE OF ANY ATTACHED STYLE IMAGE` : "",
                ].filter(Boolean);
                return notes.length ? `<div class="step-note mono">${notes.join("  ·  ")}</div>` : "";
              })()}
              <div class="cam-editor hidden" data-f="cam-editor">
                <span class="mono cam-open-k">CAMERA OPENED · NEXT TAKE PAINTS FROM THESE</span>
                ${cameraRow("cam", p, "— production default —", false)}
                <div class="cam-editor-acts">
                  <button type="button" class="primary" data-f="cam-save">Save camera</button>
                  <button type="button" class="verb" data-f="cam-cancel">Cancel</button>
                </div>
                <span class="mini mono">JOURNALED · RE-STAMPS THE LOCK · A CUSTOM LENS STATES ITS MM IN THE LINE, NEVER "CUSTOM"</span>
              </div>
            </div>` })}

        ${step({ n: "04", id: "references", label: "REFERENCES",
          meta: `<span data-f="ref-count"></span>`,
          verbs: `<button type="button" class="verb mono" data-f="show-ids"
            title="Name every plate this render will attach — the ticked groups AND the always-on style anchors">Show ids</button>`,
          body: `
            <div class="step-note mono">GROUPED BY SUBJECT · EACH CONTROLS ONLY ITS OWN ROLE</div>
            ${(() => {
              // P5: unchecked boxes read as a choice not yet made; in fact
              // the app decided and the answer was NOTHING MATCHED. Say so
              // before a 4K spend. With a previous take the selection is the
              // user's own memory and an empty one is their decision — no
              // warning second-guesses it.
              if (!groupList.length || panelCands.length
                  || groupList.some(g => reqObjs.some(o => matches(o, g.name))))
                return "";
              const shown = reqObjs.slice(0, 4).map(o => `"${esc(o)}"`).join(", ");
              const more = reqObjs.length > 4 ? ` (+${reqObjs.length - 4} more)` : "";
              return `<div class="nomatch">
                <b class="mono">NO MATCHES</b>
                <p>${reqObjs.length
                  ? `Nothing in the library matches what this panel requires: ${shown}${more}.`
                  : "This panel lists no required objects, so nothing could be matched."}
                It will render from text and style alone — tick a group below to
                attach one anyway.</p></div>`;
            })()}
            <div class="ref-groups">
              ${onGroups.map(g => groupRow(g, true)).join("")}
              ${offGroups.length ? `<div class="ref-off-head mono">OFF · ${offGroups.length}
                <span>${refWhyOff}</span></div>` : ""}
              <div class="ref-off">${offGroups.map(g => groupRow(g, false)).join("")}</div>
              ${groupList.length ? "" : '<span class="mini">no approved subject references yet — add them via the cast &amp; subjects cards on Production Design</span>'}
            </div>
            ${(() => {
              // §2.3: the always-on style anchors are not optional and must
              // not sit among the toggles — they are set on Production
              // Design and ride every render on this board.
              if (!styleAnchors.length)
                return '<div class="step-note mono">NO STYLE ANCHORS YET — UPLOAD A BOARD RENDERING STYLE OR CINEMATOGRAPHY STYLE IMAGE ON PRODUCTION DESIGN</div>';
              const heads = {};
              for (const r of styleAnchors) (heads[roleHead(r.role)] ??= []).push(r);
              const pretty = h => h.replace(/_STYLE$/, "").replaceAll("_", " ");
              return `<div class="step-note mono anchors-line">
                <span class="anchors-k">STYLE ANCHORS</span>
                ${Object.entries(heads).map(([h, rs]) =>
                  `${esc(pretty(h))} ${rs.length} PLATE${rs.length === 1 ? "" : "S"}`).join("  ·  ")}
                <span class="always-on" title="Auto-attached to every render on this board — they control style only, never content">ALWAYS ON</span>
                <span class="anchors-src">SET ON PRODUCTION DESIGN · ATTACHED TO EVERY RENDER ON THIS BOARD</span>
              </div>
              <div class="mini hidden" data-f="anchor-ids">${styleAnchors.map(r =>
                `<span class="badge LOCKED" title="Auto-attached — controls style only, never content">${esc(r.id)} ${esc(r.role)}</span>`).join(" ")}
              </div>`;
            })()}
            ${swatchRefs.length ? (() => {
              // A palette is applied WHOLE (user, 2026-08-14; canon
              // "a set that means something as a set renders as one
              // object", PALETTE_GROUPS 2026-08-06): the ramp IS the
              // swatch and the colours are its inside, so this offers one
              // row per design language, never a grid of loose colours.
              // Unselected = the style shelf's automatic pick (the 2
              // newest, server-side, ruled 2026-08-03); choosing any
              // palette takes over the COLOR_PALETTE role entirely.
              const rows = [];
              const byLang = new Map();
              for (const r of swatchRefs) {
                const sw = { ...swatchNotes(r.notes), ref_id: r.id };
                if (!sw.hex) continue;
                const key = sw.language || sw.name || r.id;
                if (!byLang.has(key)) {
                  const row = { label: key, unfiled: !sw.language, swatches: [] };
                  byLang.set(key, row);
                  rows.push(row);
                }
                byLang.get(key).swatches.push(sw);
              }
              if (!rows.length) return "";
              return `<div class="fgroup pal-group"
                title="Which palette rides this render as its colour reference. Unselected = the style shelf's automatic pick; choosing a palette replaces that with exactly the one you pick — a palette attaches whole, never colour by colour.">
                <span class="f-label">Palette</span>
                <button type="button" class="ghost" data-f="swatch-open"></button>
                <div class="hidden dropdown-panel pal-menu" data-f="swatch-menu">
                  ${rows.map(row => {
                    const ids = row.swatches.map(s => s.ref_id);
                    const hero = row.swatches.find(s => s.hero);
                    return `
                    <label class="pal-row" title="${esc(row.label)} — ${ids.length} colour${ids.length === 1 ? "" : "s"}${
                      hero ? ` · hero ${esc(hero.hex.toUpperCase())}` : ""}; attaches whole">
                      <input type="checkbox" data-ids="${esc(JSON.stringify(ids))}"
                             ${ids.some(id => lastRefIds.has(id)) ? "checked" : ""}>
                      <span class="sw-ramp pal-ramp">${rampOrder(row.swatches).map(band).join("")}</span>
                      <span class="sw-ramp-label pal-row-label">
                        <span class="lang">${esc(row.label)}</span>
                        <span class="n">${ids.length} COLOUR${ids.length === 1 ? "" : "S"}</span>
                        ${hero ? `<span class="hero">HERO ${esc(hero.hex.toUpperCase())}</span>`
                               : `<span class="hero open">OPEN</span>`}
                      </span>
                    </label>`;
                  }).join("")}
                  <label class="pal-row pal-row-none"
                    title="Send no colour reference at all. The palette's WORDS still reach the render through the Bible; only the swatch plate stops riding.">
                    <input type="checkbox" data-f="pal-none">
                    <span class="sw-ramp pal-ramp pal-ramp-none"></span>
                    <span class="sw-ramp-label pal-row-label">
                      <span class="lang">No colour reference</span>
                      <span class="n">NO PLATE ATTACHED</span>
                    </span>
                  </label>
                  <div class="mini mono pal-foot">NOTHING TICKED = AUTO · A PALETTE ATTACHES WHOLE</div>
                </div>
              </div>`;
            })() : ""}` })}

        ${step({ n: "05", id: "prompt", label: "PROMPT",
          // A saved prompt makes steps 01–04 inert for this panel's TEXT.
          // Discovering that by editing the camera and seeing no change is
          // exactly the failure the gate rules forbid, so the step says it
          // where the step is read (user 2026-08-16).
          meta: p.prompt_override
            ? `<span class="step-meta-alert">SAVED PROMPT — STEPS 01–04 DO NOT WRITE THIS PANEL</span>`
            : `COMPILED FROM 01–04${lockHash ? ` · HASH ${esc(String(lockHash).slice(0, 16))}` : ""}`,
          verbs: `
            <button type="button" class="verb" data-f="preview"
              title="Show the exact compiled prompt this panel would send — free, no generation">Read &amp; edit</button>
            <button type="button" class="verb" data-f="compcheck"
              title="Have the narrative model read this panel's scene in the screenplay and judge whether the compiled prompt's angle and composition serve its action — one text call, no image spend">Check composition</button>
            <button type="button" class="verb" data-f="prose"
              title="Have GPT-5.6 rewrite the compiled spec into editable render prose without generating an image">Draft prose</button>`,
          body: `
            <pre class="step-prompt mono" data-f="prompt-peek">READING THE COMPILED PROMPT…</pre>
            ${scopeBits.length ? `<div class="step-note mono">SCOPE ${
              scopeOverride ? "PANEL OVERRIDE" : "INHERITED FROM THE BOARD"} · ${
              esc(scopeBits.join("  ·  "))}</div>` : ""}
            <!-- C6 (RULE_PASS 2026-08-16): the manifest belongs with the
                 thing it BECOMES. Step 04 keeps its count by role; the
                 full list of plates that will ride sits beside the prompt
                 they ride in. -->
            <div class="attached mono" data-f="attached"></div>
            <div class="dispatch-facts mono" data-f="dispatch-facts"></div>` })}

        ${step({ n: "06", label: "GENERATE",
          verbs: `
            <button type="button" class="verb" data-f="gen-change"
              title="Change the model, size or aspect for this render">Change</button>
            <button class="${workOrder ? "primary" : "ghost gen-go"}" data-f="generate"
              ${prefKeyFailed ? "disabled" : ""} title="${prefKeyFailed ? genGateTitle : workOrder
                ? "Render this panel's first take — the one action that fills the card"
                : "Render the next take with the model, size, aspect and references confirmed above"}">${
              workOrder ? "Generate first take" : "Generate candidate"}</button>`,
          body: `
            ${p.prompt_override ? `<div class="step-note mono"><span
              class="step-meta-alert">THIS TAKE RENDERS FROM THE SAVED PROMPT</span>
              · STEP 05 HOLDS THE TEXT · CAMERA AND OBJECTS BELOW DO NOT WRITE IT</div>` : ""}
            <div class="gen-stated mono">
              <span><i>MODEL</i> <b data-f="say-model">—</b></span>
              <span><i>SIZE</i> <b data-f="say-size">—</b></span>
              <span><i>ASPECT</i> <b data-f="say-aspect">—</b></span>
            </div>
            <div class="gen-row hidden" data-f="gen-row">
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
                <select data-f="aspect">${aspectList.map(a =>
                  `<option value="${esc(a.id)}" ${a.id === panelAspect ? "selected" : ""}>${esc(a.label)}</option>`).join("")}</select>
              </div>
            </div>
            <div class="gen-warn mono hidden" data-f="aspect-warn"></div>
            <div class="gen-warn mono hidden" data-f="plates-warn"></div>
            <div class="gen-gate mono" data-f="gen-gate"></div>` })}
      </div>
      <div data-f="busy"></div>
      <div data-f="report"></div>`;

    // A palette row carries every id in its group: selecting it attaches
    // the whole ramp, which is the object the user actually chose.
    // "I cant see a way to remove the color swatch reference" (user,
    // 2026-08-25). There was none: the menu chose WHICH palette rides and
    // ticking nothing meant the shelf's automatic pick, so a production
    // whose every palette is low-saturation could not ask a colour grammar
    // what it would do unaided. The control said "which" and had no
    // "none". This is the missing third answer — and it is a real
    // production act, not only a test harness: a panel may legitimately
    // want the Bible's colour words without a swatch plate steering the
    // hues.
    const paletteOff = () => !!$("[data-f=pal-none]", card)?.checked;
    // The server tops up an automatic palette when the user picked none,
    // which is right by default and exactly wrong here — so "none" has to
    // be SENT, not merely left out.
    const checkedSwatches = () =>
      paletteOff() ? ["-COLOR_PALETTE"] :
      $$("[data-f=swatch-menu] input:checked", card)
        .filter(x => !x.dataset.f)
        .flatMap(x => JSON.parse(x.dataset.ids));
    const checkedRefs = () => [
      ...$$(".ref-groups input:checked", card).flatMap(x => JSON.parse(x.dataset.ids)),
      ...checkedSwatches(),
    ];
    const report = $("[data-f=report]", card);
    const busyHost = $("[data-f=busy]", card);

    const refCount = $("[data-f=ref-count]", card);
    const dispatchFacts = $("[data-f=dispatch-facts]", card);
    // The palette is its OWN role, and counting it as SUBJECT was why a
    // panel with ONE ticked group reported "13 SUBJECT" and sat over the
    // cap with nothing on screen to explain it (user 2026-08-14). Since a
    // palette attaches whole, its swatches are a real share of the 14 and
    // have to be named as such.
    const attachedHost = $("[data-f=attached]", card);
    // The manifest and the count come from the SERVER, resolved by the code
    // a render actually uses (adversarial review F5/F8). The client's own
    // arithmetic knew two of the four auto-attach roles, had no per-role
    // cap, and hardcoded the cap of 14 as a JS literal — so it named plates
    // that did not ride, omitted plates that did, and printed a count the
    // screen could not prove. On the screen where money is spent.
    //
    // Debounced because it fires on every tick, and it is one local call
    // that touches no disk: _resolve_generation_inputs is pure resolution.
    let refCountSeq = 0;
    const updateRefCount = () => {
      const ids = checkedRefs();
      const seq = ++refCountSeq;
      refCount.textContent = "RESOLVING WHAT WILL ATTACH…";
      refCount.style.color = "";
      api(`/api/specs/${specId}/panels/${p.id}/attachments?refs=${ids.join(",")}`)
        .then(m => {
          if (seq !== refCountSeq) return;   // a later tick already won
          const auto = m.attachments.filter(a => a.auto);
          const picked = m.attachments.filter(a => !a.auto);
          refCount.textContent =
            `${picked.length} PICKED + ${auto.length} ALWAYS-ON`
            + ` = ${m.count} OF ${m.max} ATTACHED`
            + (m.over ? " — OVER LIMIT, UNTICK A GROUP OR NARROW THE PALETTE" : "");
          refCount.style.color = m.over ? "var(--bad)" : "";

          // Every plate that will ride, named, grouped by role. Consecutive
          // ids collapse to their ends so the manifest stays a few facts.
          const byRole = {};
          for (const a of m.attachments)
            (byRole[a.role || a.head || "REFERENCE"] ??= []).push(a.id);
          const parts = Object.entries(byRole)
            .map(([role, rids]) => `${esc(String(role).toUpperCase())} ${idSpan(rids)}`);
          attachedHost.innerHTML =
            `<span class="attached-k">ATTACHED · ${m.count}</span>`
            + (parts.length ? parts.join("&ensp;·&ensp;") : "NOTHING ATTACHED")
            // D3.2 — a panel whose design language has no palette now gets
            // none rather than the newest of some other faction's. Silence
            // beats the wrong palette, but only if the silence is stated:
            // otherwise it is a quieter version of the same surprise.
            + (m.notes || []).map(n =>
                `<div class="attached-note">${esc(n)}</div>`).join("");
          attachedHost.classList.toggle("over", m.over);

          // P6: what is about to be sent, legible at the moment of sending.
          // Same resolution as the manifest above — it used to recompute
          // the tally from the client's own style/palette/subject split,
          // which is the split that was wrong (F8).
          const byHead = {};
          for (const a of m.attachments)
            byHead[a.head] = (byHead[a.head] || 0) + 1;
          const tally = Object.entries(byHead)
            .map(([h, n]) => `${n} ${esc(String(h).replaceAll("_", " "))}`)
            .join(" · ");
          dispatchFacts.innerHTML =
            `${tally || "NOTHING"} · ${m.count} IMAGE${m.count === 1 ? "" : "S"} ATTACHED<br>`
            + `${lockHash ? `SPEC ${esc(lockHash.slice(0, 8).toUpperCase())} · ` : ""}`
            + "NATIVE RENDER, NEVER UPSCALED";
        })
        .catch(err => {
          if (seq !== refCountSeq) return;
          // Say it cannot be resolved rather than guessing — a guessed
          // manifest is what this replaced.
          refCount.textContent = "COULD NOT RESOLVE THE ATTACHMENTS — " +
            String(err.message || "").toUpperCase();
          refCount.style.color = "var(--bad)";
          attachedHost.innerHTML =
            `<span class="attached-k">ATTACHED · ?</span>NOT RESOLVED`;
          dispatchFacts.innerHTML = "ATTACHMENTS NOT RESOLVED<br>"
            + `${lockHash ? `SPEC ${esc(lockHash.slice(0, 8).toUpperCase())} · ` : ""}`
            + "NATIVE RENDER, NEVER UPSCALED";
        });

    };
    // A tick has to LAND: the row brightens and states what it now is, so
    // attaching a group is visibly an act rather than a glyph flip
    // (user 2026-08-14). The reason follows the live state — a group the
    // app chose keeps its own reason when re-ticked.
    $(".ref-groups", card).addEventListener("change", ev => {
      const row = ev.target.closest(".ref-row");
      if (row) {
        const on = ev.target.checked;
        row.classList.toggle("on", on);
        const why = $(".ref-why", row);
        if (why) {
          why.textContent = on
            ? (row.dataset.was ? refWhy : "ATTACHED — RIDES THE NEXT TAKE")
            : (row.dataset.was ? "DETACHED — WILL NOT RIDE" : "");
          why.classList.toggle("ref-why-user", on ? !row.dataset.was : !!row.dataset.was);
        }
      }
      updateRefCount();
      // Write the pick down. Without this the tick lives in the DOM only,
      // and the next redraw — a reject, a panel switch, a reload — throws
      // it away silently.
      p.ref_ids = checkedRefs();
      api(`/api/specs/${specId}/panels/${p.id}/refs`, {
        method: "POST", json: { ref_ids: p.ref_ids },
      }).catch(err => toast(
        `Reference pick not saved — ${err.message}. It will ride THIS take `
        + "but may not survive a refresh.", true));
      // §1.7: a confirmation that outlives what it confirmed is a lie.
      if (confIs("references")) { confSet("references", false); renderBoardPanels(specId); }
    });
    updateRefCount();

    // Step confirmations (§1.7) — two states, both reversible. Repainting
    // the card is what re-reads the state, so the head count, the step's
    // own dimming and the gate line stay one fact.
    $$("[data-confirm]", card).forEach(b => b.onclick = () => {
      confSet(b.dataset.confirm, true);
      renderBoardPanels(specId);
    });
    $$("[data-unconfirm]", card).forEach(b => b.onclick = () => {
      confSet(b.dataset.unconfirm, false);
      renderBoardPanels(specId);
    });

    // Required objects are authored on the breakdown; the step points at
    // where the edit actually happens rather than growing a second editor.
    const toBreakdown = $("[data-f=to-breakdown]", card);
    if (toBreakdown) toBreakdown.onclick = () => {
      uiSet("openSpec", specId);
      showView("specs");
    };

    // Scanning belongs where you are LOOKING at what the panel produced
    // (user-caught 2026-08-17: it shipped only on the breakdown editor,
    // three screens down, and "Dont see it"). Accepting a find writes the
    // object AND its evidence row server-side — the workbench has amended
    // the brief and the camera between takes since 2026-08-08; objects
    // were the missing third.
    const scanHere = $("[data-f=scan-scene]", card);
    if (scanHere) scanHere.onclick = () => scanScreenplayDialog({
      specId, panelId: p.id, brief: p.purpose || "",
      has: () => reqObjs,
      accept: async (obj, quote) => {
        const r = await api(`/api/specs/${specId}/panels/${p.id}/objects`, {
          method: "POST", json: { add: [{ object: obj, quote: quote || "" }] },
        });
        if (!r.added.length) return false;
        renderBoardPanels(specId);
        return true;
      },
      // The brief goes through the SAME endpoint the workbench's own Edit
      // brief uses — journaled, lock re-stamped, refused on an approved
      // take. A proposal accepted is an amendment like any other.
      acceptBrief: async text => {
        await api(`/api/specs/${specId}/panels/${p.id}/purpose`, {
          method: "POST", json: { purpose: text } });
        renderBoardPanels(specId);
      },
    });

    // §2.15/§2.1 step 05 shows the real compiled prompt, but that is a
    // server round-trip PER PANEL — so it loads when the step first scrolls
    // into view rather than on every repaint of a 24-panel sheet.
    const peek = $("[data-f=prompt-peek]", card);
    if (peek) {
      const load = async () => {
        try {
          const r = await api(`/api/specs/${specId}/panels/${p.id}/prompt`);
          const text = String(r.prompt || r.text || "").trim();
          peek.textContent = text || "THE COMPILED PROMPT IS EMPTY.";
        } catch (err) {
          peek.textContent = `COULD NOT READ THE COMPILED PROMPT — ${String(err.message || "").toUpperCase()}`;
        }
      };
      if (typeof IntersectionObserver === "function") {
        const io = new IntersectionObserver(es => {
          if (es.some(e => e.isIntersecting)) { io.disconnect(); load(); }
        }, { rootMargin: "200px" });
        io.observe(peek);
      } else load();
    }

    // Add-reference-in-place (user 2026-08-14): the library widget opens
    // prefilled with the required object; approved on save (supplying it
    // deliberately IS the review) and the card re-renders so the new
    // group appears in the attach list immediately.
    // Two ways to give an object a reference (user 2026-08-16: "in this
    // dialogue I need to be able to select existing ref"). Uploading was
    // the only one, which meant re-photographing something the library
    // already held whenever the name did not match. Choosing an existing
    // plate ticks its group for this panel, which is the same mechanism
    // an auto-matched group uses — nothing special-cased downstream.
    $$("[data-addref]", card).forEach(b => b.onclick = async () => {
      const obj = b.dataset.addref;
      // Near-misses first. The library runs to dozens of plates and an
      // unordered wall of thumbnails is not a choice — anything sharing a
      // word with the object leads, then the rest in id order.
      const near = r => namesPhrase(obj, String(r.role).split("—")[1]?.trim() || r.role);
      // TRIAGE §1 (ruled 2026-08-18): style and palette anchors are
      // excluded — a look anchor is never the answer for a prop, and
      // offering one is a defect rather than a choice.
      const pickable = approvedRefs.filter(r =>
        !AUTO_ATTACH_HEADS.includes(roleHead(r.role))
        && roleHead(r.role) !== "BOARD_LAYOUT_STYLE");
      const ordered = [...pickable].sort((a, b2) => (near(b2) ? 1 : 0) - (near(a) ? 1 : 0));
      const how = await pickReferenceSource(obj, ordered);
      if (how === null) return;
      if (how === "new") {
        addReferenceDialog({ head: "PROP_REFERENCE", title: obj },
          { approve: true, onDone: () => renderBoardPanels(specId) });
        return;
      }
      // `how` is a chosen reference record: tick its group so it rides.
      const g = groupList.find(x => x.ids.includes(how.id));
      if (!g) { toast("That reference is not in a selectable group.", true); return; }
      // Choosing a group deliberately overrules an earlier "not this
      // object's reference" about the same group — otherwise the tile would
      // stay + REF while its plate rides, which is the two halves
      // disagreeing again.
      if (excluded(obj).includes(g.name)) {
        try {
          await api(`/api/specs/${specId}/panels/${p.id}/object-refs`, {
            method: "POST", json: { object: obj, include: [g.name] } });
        } catch { /* the tick below still stands; the marker catches up on reload */ }
      }
      const box = $$(".ref-groups input", card).find(
        x => JSON.parse(x.dataset.ids || "[]").includes(how.id));
      if (!box) { toast("That group is not on this panel's shelf.", true); return; }
      box.checked = true;
      updateRefCount();
      box.closest(".ref-row")?.scrollIntoView({ behavior: "smooth", block: "center" });
      toast(`${how.id} (${g.name}) will ride this panel's next take — `
            + "ticked in step 04, untick it there to change your mind.");
    });

    // View (user 2026-08-14, corrected same day): not a bare lightbox —
    // the full reference widget for the object, showing every matching
    // plate with its role and jurisdiction (the same match the ✓ REF
    // verdict and the generation itself are built from), the stated
    // thin-anchor warning, and Add another plate in place.
    $$("[data-viewref]", card).forEach(b => b.onclick = () => {
      const obj = b.dataset.viewref;
      const gs = groupList.filter(g => matches(obj, g.name));
      const recs = gs.flatMap(g => g.ids)
        .map(id => refs.find(x => x.id === id)).filter(Boolean);
      if (!recs.length) { toast("No matching reference found.", true); return; }
      // What covers this object is what will actually RIDE for it — the
      // plates chosen from its group, not the whole library group (user
      // 2026-08-15). Choosing here writes back to the same per-panel pick
      // the reference row reads, so the two can never disagree.
      const picked = gs.flatMap(pickFor);
      viewObjectReferences(obj, recs,
        { head: gs[0]?.head || "PROP_REFERENCE", title: gs[0]?.name || obj },
        () => renderBoardPanels(specId),
        { pick: picked,
          onPick: ids => {
            for (const g of gs) setPick(g, g.ids.filter(id => ids.includes(id)));
            renderBoardPanels(specId);
          },
          onDetach: async () => {
            try {
              await api(`/api/specs/${specId}/panels/${p.id}/object-refs`, {
                method: "POST",
                json: { object: obj, exclude: gs.map(g => g.name) },
              });
              toast(`"${obj}" is no longer matched to ${
                gs.map(g => g.name).join(", ")}. The plates stay in the library `
                + "— use + REF to point it somewhere else.");
              renderBoardPanels(specId);
            } catch (err) { toast(err.message, true); }
          } });
    });

    // "Choose plates" opens the photos, because choosing which image the
    // render works from is a thing you do by LOOKING at them. The pick
    // lands live — the row's ids, its count and the manifest all follow.
    $$("[data-plates]", card).forEach(b => b.onclick = ev => {
      ev.preventDefault();
      ev.stopPropagation();
      const g = groupList.find(x => x.name === b.dataset.plates);
      if (!g) return;
      const recs = g.ids.map(id => refs.find(x => x.id === id)).filter(Boolean);
      if (!recs.length) { toast("No plates found for this group.", true); return; }
      const row = b.closest(".ref-row");
      const box = $("input", row);
      viewObjectReferences(g.name, recs,
        { head: g.head, title: g.name },
        () => renderBoardPanels(specId),
        { pick: pickFor(g),
          onPick: ids => {
            setPick(g, ids);
            box.dataset.ids = JSON.stringify(ids);
            box.checked = box.checked && ids.length > 0;
            $(".ref-kind", row).textContent =
              `${g.head.replaceAll("_", " ").toLowerCase()} · ${
                ids.length === g.ids.length ? g.ids.length
                                            : `${ids.length} OF ${g.ids.length}`}`;
            $(".ref-ids", row).innerHTML = idSpan(ids);
            row.classList.toggle("on", box.checked);
            updateRefCount();
          } });
    });

    // Palette selector: stated summary, toggled menu, count kept live.
    const swatchOpen = $("[data-f=swatch-open]", card);
    if (swatchOpen) {
      const menu = $("[data-f=swatch-menu]", card);
      // The summary states the live outcome — the rule AND the result. It
      // shows the actual colours chosen, capped so a 19-swatch pick cannot
      // outgrow its own button; the denominator counts swatches that
      // PARSED, never the raw role count (a count must be provable).
      // The summary states the live outcome — the rule AND the result. It
      // names the palette chosen and shows its ramp, because the palette
      // is the object; a colour count is its inside, not its identity.
      const palRows = $$("input[data-ids]", menu);
      const totalSwatches = palRows
        .reduce((n, x) => n + JSON.parse(x.dataset.ids).length, 0);
      const summary = () => {
        const picked = palRows.filter(x => x.checked);
        if (!picked.length) {
          swatchOpen.innerHTML =
            `<span class="mono">AUTO · ${Math.min(2, totalSwatches)} NEWEST OF ${totalSwatches}</span>`;
          return;
        }
        const names = picked.map(x =>
          x.parentElement.querySelector(".lang")?.textContent || "").filter(Boolean);
        const ramp = picked[0].parentElement.querySelector(".pal-ramp");
        swatchOpen.innerHTML =
          `<span class="pal-sum-ramp">${ramp ? ramp.innerHTML : ""}</span>` +
          `<span class="mono">${esc(names.length === 1 ? names[0]
            : `${names.length} PALETTES`)}</span>`;
      };
      // R15 (HARNESS_AUDIT) — THE dropdown contract: --panel ground,
      // --line border, no shadow, no rounding, no animation, ≤60vh,
      // below-left of its summary, closes on Escape and outside click.
      const closeOn = ev => {
        if (ev.type === "keydown" && ev.key !== "Escape") return;
        if (ev.type === "mousedown" &&
            (menu.contains(ev.target) || swatchOpen.contains(ev.target))) return;
        menu.classList.add("hidden");
        document.removeEventListener("mousedown", closeOn, true);
        document.removeEventListener("keydown", closeOn, true);
      };
      swatchOpen.onclick = () => {
        const nowOpen = !menu.classList.toggle("hidden");
        const op = nowOpen ? "addEventListener" : "removeEventListener";
        document[op]("mousedown", closeOn, true);
        document[op]("keydown", closeOn, true);
      };
      menu.addEventListener("change", () => { summary(); updateRefCount(); });
      summary();
      updateRefCount();
    }

    // The brief editor — swap the purpose line for a textarea, save through
    // the journaled amend, repaint so the header and the next prompt agree.
    const briefEdit = $("[data-f=brief-edit]", card);
    if (briefEdit && !briefEdit.disabled) briefEdit.onclick = () => {
      $("[data-f=brief-row]", card).classList.add("hidden");
      const ed = $("[data-f=brief-editor]", card);
      ed.classList.remove("hidden");
      const input = $("[data-f=brief-input]", ed);
      input.value = p.purpose || "";
      input.focus();
      $("[data-f=brief-cancel]", ed).onclick = () => {
        ed.classList.add("hidden");
        $("[data-f=brief-row]", card).classList.remove("hidden");
      };
      $("[data-f=brief-save]", ed).onclick = async () => {
        try {
          const out = await api(`/api/specs/${specId}/panels/${p.id}/purpose`, {
            method: "POST", json: { purpose: input.value } });
          toast(`${p.id} brief amended — journaled; the next take paints from it.`);
          p.purpose = out.purpose;
          renderBoardPanels(specId);
        } catch (err) { toast(err.message, true); }
      };
    };

    // R7: stated → opened → saved. The selects stay local until Save
    // camera posts once (journaled + lock re-stamped server-side).
    const camInline = $("[data-f=cam-inline]", card);
    if (camInline) {
      // Scoped to the CARD, not to cam-inline. seqStep puts `verbs` in
      // the step's head and `body` beneath it, so the button is a sibling
      // of this div and never a descendant — the lookup found nothing,
      // no handler was bound, and Change camera did nothing at all
      // (user-hit 2026-08-22). The editor it opens IS inside cam-inline;
      // the two live in different halves of the step.
      const openBtn = $("[data-f=cam-open]", card);
      const editor = $("[data-f=cam-editor]", camInline);
      wireCameraRow("cam", camInline, null);  // Custom-lens reveal only
      if (openBtn && !openBtn.disabled) openBtn.onclick = () => {
        editor.classList.remove("hidden");
        $(".cam-stated", camInline).classList.add("hidden");
      };
      $("[data-f=cam-cancel]", camInline).onclick = () =>
        renderBoardPanels(specId);
      $("[data-f=cam-save]", camInline).onclick = async () => {
        try {
          await api(`/api/specs/${specId}/panels/${p.id}/camera`,
            { method: "POST", json: readCameraFields("cam", camInline) });
          toast(`${p.id} camera set — the next take uses it.`);
          renderBoardPanels(specId);
        } catch (err) { toast(err.message, true); renderBoardPanels(specId); }
      };
    }

    // P4 disclosure: the full anchor badge list, unchanged, on demand.
    // "Which references is this panel using?" must be answerable without a
    // mouse (user-asked 2026-08-14): the ids used to live in a hover title
    // on each row, and this verb revealed the style anchors' ids ONLY.
    // "what is the grammer for that cenematography? Let me read it"
    // (user, 2026-08-24). The take says which cinematography rode it; the
    // words themselves lived only in docs/CINEMATOGRAPHY_STYLES.md, which
    // is not somewhere a director is going to go mid-review. The document
    // stays the source — this reads it, it does not copy it.
    // C4 — what this take was actually rendered from.
    //
    // The record keeps two prompts and they are not the same thing:
    // `prompt` is the compile at render time, the governance record, and
    // `render_prompt` is the text the image model received when an
    // override rode. Nothing on any screen showed either, and Preview
    // prompt shows the panel's CURRENT compile, which may be nothing like
    // what this take saw.
    //
    // Two days of this investigation were spent reading `prompt` and
    // reasoning about renders it had never described (2026-08-25).
    const readSent = $("[data-f=read-sent]", card);
    if (readSent) readSent.onclick = () => {
      const sent = String(staged.render_prompt || "").trim();
      const compiled = String(staged.prompt || "").trim();
      if (!sent && !compiled)
        return toast("This take recorded no prompt.", true);
      const NL = String.fromCharCode(10);
      const body = sent
        ? ["THE IMAGE MODEL RECEIVED THIS, VERBATIM:", "", sent, "",
           "─".repeat(60), "",
           "The steps 01–04 compile at the time of this render is kept "
           + "as the governance record. It is NOT what was sent:", "",
           compiled || "(none recorded)"].join(NL)
        : compiled;
      promptOverlay(
        `${staged.candidate_id} — ${sent ? "hand-edited prompt" : "compiled prompt"}`,
        body,
        sent
          ? `${sent.length} CHARACTERS SENT · ${compiled.length} COMPILED · `
            + `OVERRIDE SCOPE: ${String(staged.prompt_override_scope || "take").toUpperCase()}`
          : `${compiled.length} CHARACTERS · COMPILED FROM STEPS 01–04`);
    };

    const readCine = $("[data-f=read-cine]", card);
    if (readCine) readCine.onclick = async () => {
      await loadCinemaStyles();
      const st = (CINEMA_STYLES || []).find(x => x.key === readCine.dataset.key);
      if (!st) return toast(
        "That cinematography is no longer in docs/CINEMATOGRAPHY_STYLES.md — "
        + "the take still records which one rode it.", true);
      const NL = "\n";
      const para = t => String(t || "").trim();
      const list = a => (Array.isArray(a) ? a : [a]).filter(Boolean)
        .map(x => "  · " + String(x).trim()).join(NL);
      const body = [
        para(st.description),
        st.principle ? "PRINCIPLE" + NL + para(st.principle) : "",
        st.mechanics ? "MECHANICS" + NL + list(st.mechanics) : "",
        st.avoid ? "AVOID" + NL + list(st.avoid) : "",
        st.films ? "SEEN IN" + NL + list(st.films) : "",
        // C3 — the author's own hedges, where the author is reading.
        // Deliberately not in the picker: a director choosing a look does
        // not need a lint, and a lint shown where it is noise gets
        // ignored where it is not.
        (st.hedges || []).length
          ? "HEDGED LINES — THESE SOFTEN THE STYLE'S OWN INSTRUCTIONS"
            + NL + "A hedge lets the model satisfy the line by doing LESS. "
            + "Not always wrong — a craft rule is a counterweight — "
            + "but a hedge on a style's defining mechanic is why it never "
            + "reaches an image."
            + NL + (st.hedges || []).map(h =>
                "  · " + h.words.join(", ") + " — " + h.line).join(NL)
          : "",
        "─".repeat(60),
        "SENT TO THE MODEL, VERBATIM:",
        para(st.prompt),
      ].filter(Boolean).join(NL + NL);
      await promptOverlay(
        st.name + (st.subtitle ? " — " + st.subtitle : ""),
        body,
        "READ FROM docs/CINEMATOGRAPHY_STYLES.md · THE DOCUMENT IS THE SOURCE");
    };

    const showIds = $("[data-f=show-ids]", card);
    if (showIds) showIds.onclick = () => {
      const open = card.classList.toggle("ids-open");
      $("[data-f=anchor-ids]", card)?.classList.toggle("hidden", !open);
      showIds.textContent = open ? "Hide ids" : "Show ids";
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
      // §2.4 (STEP_SEQUENCE_SPEC): the remembered generation settings are
      // INSTALL-wide, but a panel's shape is its own. Once this panel has
      // rendered a take, that ratio is its established shape and outranks
      // the global memory — the select used to reopen at a hardcoded 16:9
      // and silently re-shape a 21:9 hero panel on the next Generate.
      const remembered = k === "aspect" && panelCands.length ? null : gen[k];
      if (remembered && [...selEl.options].some(o => o.value === remembered && !o.disabled))
        selEl.value = remembered;
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

    // §2.4 — step 06 states its three values and its gate. The selects are
    // the same controls as before, folded behind Change; what the step
    // SHOWS is what the render will use.
    const genChange = $("[data-f=gen-change]", card);
    const genRow = $("[data-f=gen-row]", card);
    if (genChange && genRow) genChange.onclick = () => {
      const opening = genRow.classList.toggle("hidden") === false;
      genChange.textContent = opening ? "Done" : "Change";
    };
    const sayModel = $("[data-f=say-model]", card);
    const saySize = $("[data-f=say-size]", card);
    const sayAspect = $("[data-f=say-aspect]", card);
    const aspectWarn = $("[data-f=aspect-warn]", card);
    const platesWarn = $("[data-f=plates-warn]", card);
    const genGate = $("[data-f=gen-gate]", card);
    const syncStated = () => {
      sayModel.textContent = modelSel.options[modelSel.selectedIndex]?.text || "—";
      saySize.textContent = sizeSel.value || "—";
      sayAspect.textContent =
        aspectSel.options[aspectSel.selectedIndex]?.text || aspectSel.value || "—";
      // The mismatch is the single best argument for the whole sequence:
      // three facts that used to live in three places — the panel head, the
      // rail, and a select 3000px down — now contradict each other in one
      // step, where a wasted 4K render is still preventable.
      const mismatch = !!(lastTake && aspectSel.value
        && aspectSel.value !== panelAspect);
      aspectWarn.classList.toggle("hidden", !mismatch);
      if (mismatch) {
        aspectWarn.textContent =
          `ASPECT DOES NOT MATCH THE PANEL — ${p.id} IS ${String(aspectLabel).toUpperCase()}`
          + ` AND THE LAST TAKE RENDERED ${lastTake.width} × ${lastTake.height}`;
      }
      // The plates gate. Ticking six references and choosing an engine that
      // cannot receive them is the most expensive silent mismatch in the
      // app — it produced a render of a completely different man from a
      // likeness plate, with nothing anywhere saying why (user-caught
      // 2026-08-16). Stated where the spend happens, and only when there is
      // actually something to lose.
      const nPlates = checkedRefs().length + styleAnchors.length;
      const blind = nPlates > 0 && !sendsPlates(appSettings, modelSel.value);
      platesWarn.classList.toggle("hidden", !blind);
      if (blind) {
        platesWarn.textContent =
          `THIS ENGINE NEVER SEES YOUR ${nPlates} REFERENCE PLATE${nPlates === 1 ? "" : "S"}`
          + " — IT RENDERS FROM A WRITTEN DESCRIPTION OF THEM."
          + " A LIKENESS WILL BE APPROXIMATE. PICK GEMINI OR GPT IMAGE 2 TO SEND THE IMAGES.";
      }
      // §2.4 the gate is honest: unconfirmed steps do NOT block a render,
      // so the surface says so rather than grey out the button. A render is
      // the end of a sequence, not a reward for finishing one.
      const left = CONF_STEPS.length - confCount;
      genGate.textContent = left
        ? `${left} STEP${left === 1 ? "" : "S"} UNCONFIRMED — YOU CAN STILL RENDER`
        : "ALL FIVE STEPS CONFIRMED";
      genGate.classList.toggle("gate-clear", !left);
    };
    [modelSel, sizeSel, aspectSel].forEach(s =>
      s.addEventListener("change", syncStated));
    // syncAspects may snap the ratio to one the chosen engine can render,
    // so the stated line is written after it, never before.
    syncAspects(true);
    syncStated();

    $("[data-f=preview]", card).onclick = async () => {
      try {
        const r = await api(`/api/specs/${specId}/panels/${p.id}/prompt?refs=${checkedRefs().join(",")}`);
        // The prompt's own acts travel WITH the prompt (they used to sit on
        // the rail block that step 05 replaced): a 16k-character prompt is a
        // file, not a clipboard payload (user 2026-08-06).
        // The verb said "Read & edit" and the body was a `<pre>`
        // (user-caught 2026-08-16: "there is a Read and Edit button on the
        // prompt, but I cannot edit and save it"). The override has always
        // existed end-to-end — generate_panel takes `render_prompt` and
        // records `prompt_source: "edited"` — but only Draft prose ever
        // fed it, so the compiled prompt was the one thing you could not
        // correct. It is now a textarea over the same path.
        report.innerHTML = `<div class="report">
          <div class="report-head"><b>Compiled prompt — ${esc(p.id)}</b>
            <span style="display:inline-flex;gap:16px;align-items:baseline">
              <button class="verb" data-f="copy" title="Copy the full prompt to the clipboard">Copy</button>
              <button class="verb" data-f="dl" title="Download this prompt as a .md file — the exact text this take was rendered from, with its conditions in the header">Download</button>
              <button class="ghost" data-f="close-report">Close</button>
            </span></div>
          <div class="prompt-comp" data-f="composition"></div>
          <textarea data-f="prompt-edit" spellcheck="false"
            style="width:100%;min-height:300px;font-family:Consolas,monospace;font-size:12px"></textarea>
          <div class="row" style="margin-top:8px;align-items:baseline;gap:16px">
            <button class="ghost" data-f="save-prompt" ${r.frozen ? "disabled" : ""}
              title="${r.frozen
                ? "This panel has an approved take, which freezes what it was approved against. Withdraw that approval to change the prompt."
                : "Keep this text on the panel. Every take of this panel renders from it until you clear it, and steps 01–04 stop compiling this panel."}">Save prompt to this panel</button>
            <button class="ghost gen-go" data-f="generate-edited"
              ${prefKeyFailed ? "disabled" : ""} ${prefKeyFailed ? `title="${genGateTitle}"` : ""}
              title="Render one take from the text exactly as it stands above, without saving it">Generate from this prompt</button>
            <button class="verb" data-f="revert"
              title="Put the compiled text back in the box. Does not touch a saved prompt.">Revert to compiled</button>
            <button class="verb ${r.saved ? "" : "hidden"}" data-f="clear-saved"
              title="Delete the saved prompt so this panel compiles from steps 01–04 again">Clear saved prompt</button>
            <span class="mini mono" data-f="edit-state"></span>
          </div>
          <p class="mini" data-f="edit-help"></p></div>`;
        $("[data-f=close-report]", report).onclick = () => { report.innerHTML = ""; };
        const promptBox = $("[data-f=prompt-edit]", report);
        const editState = $("[data-f=edit-state]", report);
        const editHelp = $("[data-f=edit-help]", report);
        const saveBtn = $("[data-f=save-prompt]", report);
        const clearBtn = $("[data-f=clear-saved]", report);
        // `r.prompt` is what a render WOULD send — the saved text when there
        // is one. `r.compiled` is what steps 01–04 make of the panel. The
        // editor has to keep both: which one is in the box is the whole
        // state, and Revert would otherwise need a second round trip.
        let saved = r.saved ? r.prompt : "";
        promptBox.value = r.prompt;
        // The gate is readable as state before it is hit, not discovered
        // after. A saved prompt is the sharpest override in the app: while
        // one exists, editing the camera or the objects below changes
        // nothing about the render, and the only honest way to run that is
        // to say so on every surface that shows a step.
        const sayState = () => {
          const text = promptBox.value.trim();
          const isSaved = !!saved && text === saved.trim();
          // A stale server (or an older build behind a proxy) answers this
          // endpoint without `compiled`, and `.trim()` on undefined would
          // throw out of the whole handler — killing Save, Clear and Revert
          // together while the editor still looked fine.
          const base = (saved || r.compiled || r.prompt || "").trim();
          const dirty = text !== base;
          editState.textContent = r.frozen
            // The gate FIRST: a state line that says "save this" beside a
            // Save that cannot be pressed is worse than saying nothing
            // (user-caught 2026-08-16: "I cant save prompt to panel once I
            // open and edit" — the refusal lived only in a hover tooltip).
            ? "AN APPROVED TAKE FREEZES THIS PANEL · NO PROMPT CAN BE SAVED TO IT"
            : isSaved
              ? "SAVED PROMPT · EVERY TAKE OF THIS PANEL RENDERS FROM THIS"
              : saved
                ? "UNSAVED CHANGES OVER THE SAVED PROMPT · SAVE OR THEY RIDE ONE TAKE"
                : dirty
                  ? "EDITED · UNSAVED · THIS TAKE ONLY"
                  : "UNEDITED · STEPS 01–04 COMPILE THIS";
          // Amber is the live signal — the text a render is about to use.
          // A frozen panel is a SETTLED fact, and canon already paints
          // settled steps with --ok (.step-confirmed), so this borrows that
          // rather than spending the accent on a refusal.
          editState.classList.toggle("settled", !!r.frozen);
          editState.classList.toggle("edited",
            !r.frozen && (isSaved || dirty || !!saved));
          editHelp.innerHTML = r.frozen
            // State the unmet condition beside the disabled control, and
            // say where it is resolved — the approval is withdrawn on the
            // TAKE, not here. And say what still works: the one-take path
            // is open, so an experiment is not blocked, only a save is.
            ? `${approvedTakes.length
                 ? `<b>Settled by ${esc(approvedTakes.join(", "))}.</b>`
                 : "<b>Settled by an approved take.</b>"}
               An approval freezes exactly what it was approved against, and
               this panel's prompt is part of that. Withdraw the approval on
               that take in the strip above to change it.
               <b>You can still test:</b> <i>Generate from this prompt</i>
               renders one take from your edits without saving anything.`
            : saved
              ? `<b>Steps 01–04 no longer compile this panel.</b> Camera, required
                 objects and references below still attach their images, but the
                 written prompt is the text above — change it here, or
                 <i>Clear saved prompt</i> to go back to the compile.`
              : `Unsaved edits ride ONE take and are archived with it under
                 <i>Edited render prompt</i>. <b>Save prompt to this panel</b> to make
                 them stick — every later take of this panel then renders from them.`;
          clearBtn.classList.toggle("hidden", !saved || r.frozen);
          saveBtn.textContent = r.frozen ? "Save prompt — frozen by an approval"
                                : saved ? "Save changes to this panel"
                                        : "Save prompt to this panel";
          saveBtn.disabled = r.frozen || (!!saved && isSaved) || (!saved && !dirty);
        };
        promptBox.addEventListener("input", sayState);
        sayState();
        $("[data-f=revert]", report).onclick = () => {
          // The compile, not the save — reverting is how you SEE what steps
          // 01–04 would make of this panel while a saved prompt is on it.
          promptBox.value = r.compiled;
          sayState();
          toast(saved
            ? "Compiled text restored in the box. The saved prompt is untouched — Save to replace it, or Clear to remove it."
            : "Reverted to the compiled prompt.");
        };
        const putPrompt = async (text, msg) => {
          const res = await api(`/api/specs/${specId}/panels/${p.id}/prompt`, {
            method: "POST", json: { prompt: text },
          });
          saved = text;
          p.prompt_override = text;   // the card's own copy, for later redraws
          sayState();
          toast(msg);
          // The card's step 05 head and step 06 note are the standing
          // warning that 01–04 are inert, so they have to move with the
          // save — but redrawing the whole card CLOSES the editor you just
          // saved from, which is its own small betrayal. Patch the two
          // surfaces in place instead.
          const meta = $("[data-step=prompt] .step-meta", card);
          if (meta) {
            meta.innerHTML = text
              ? `<span class="step-meta-alert">SAVED PROMPT — STEPS 01–04 DO NOT WRITE THIS PANEL</span>`
              : `COMPILED FROM 01–04${lockHash ? ` · HASH ${esc(String(lockHash).slice(0, 16))}` : ""}`;
          }
          const genStep = $("[data-step='06'] .step-content", card)
                       || $("[data-step=generate] .step-content", card);
          const note = genStep && $(".step-note", genStep);
          if (text && genStep && !note) {
            genStep.insertAdjacentHTML("afterbegin",
              `<div class="step-note mono"><span class="step-meta-alert">THIS TAKE
               RENDERS FROM THE SAVED PROMPT</span> · STEP 05 HOLDS THE TEXT ·
               CAMERA AND OBJECTS BELOW DO NOT WRITE IT</div>`);
          } else if (!text && note) {
            note.remove();
          }
          return res;
        };
        saveBtn.onclick = async () => {
          saveBtn.disabled = true;
          try {
            await putPrompt(promptBox.value.trim(),
              "Saved. Every take of this panel renders from this text until you clear it.");
          } catch (err) { toast(err.message, true); saveBtn.disabled = false; }
        };
        clearBtn.onclick = async () => {
          clearBtn.disabled = true;
          try {
            await putPrompt("", "Cleared — this panel compiles from steps 01–04 again.");
            promptBox.value = r.compiled;
            sayState();
          } catch (err) { toast(err.message, true); }
          clearBtn.disabled = false;
        };
        $("[data-f=generate-edited]", report).onclick = (e2) => {
          const text = promptBox.value.trim();
          // What is already in force is not an override. Sending the saved
          // text back as a per-call one would file the take as a one-off
          // test when it is in fact reproducible from the panel; sending an
          // untouched compile would claim a hand edit that never happened.
          const inForce = (saved || r.compiled).trim();
          runGenerate(e2.target, "Generate from this prompt",
                      text === inForce ? "" : text);
        };
        // R1.5 — the prompt's own composition, biggest block first. A
        // style is not weak because it is short; it is weak because
        // everything disagreeing with it is long, and until this was
        // measured nobody could see which blocks those were.
        const comp = $("[data-f=composition]", report);
        if (comp && r.composition?.blocks?.length) {
          const cm = r.composition;
          const rows = [...cm.blocks].sort((a, b) => b.chars - a.chars).slice(0, 8);
          comp.innerHTML =
            /* C9 — and how that sits against what the engine has been
               declared to take, where anyone has declared it. A gate must
               be readable BEFORE it is hit; a refusal after Generate is
               the shape this app tries never to have. */
            `<div class="pc-head mono">MADE OF · ${cm.total.toLocaleString()} CHARACTERS${
              promptCap(chosenEngine(report)) ? ` · OF ${
                promptCap(chosenEngine(report)).toLocaleString()} THIS ENGINE ACCEPTS` : ""
            }</div>`
            + rows.map(b => `<div class="pc-row">
                 <span class="pc-bar" style="width:${Math.max(2, Math.round(b.share * 100))}%"></span>
                 <span class="pc-pct mono">${(b.share * 100).toFixed(1)}%</span>
                 <span class="pc-name mono">${esc(b.head)}</span>
                 <span class="pc-n mono">${b.chars.toLocaleString()}</span>
               </div>`).join("")
            + `<div class="mini">Every block here reaches the image model. A block that
               describes something this panel does not contain is not neutral — it
               competes with the ones that do.</div>`
            /* R1.2 — and what was left OUT, with the reason. The measure
               above says a block is 31% of the prompt; this says which
               paragraphs the selection decided not to send. A selector
               that drops a section silently takes canon out of a render
               and leaves nobody able to see it — which is exactly the
               failure being fixed, so it is stated on the same surface as
               the evidence for it. */
            + bibleSelectionHtml(r.bible_selection);
        }
        $("[data-f=copy]", report).onclick = () => copyText(promptBox.value, "Compiled prompt");
        // The header carries what the prompt text itself does not: the
        // engine, the size, and WHICH references were actually attached —
        // the first thing to check when a render appears to ignore one.
        $("[data-f=dl]", report).onclick = () => {
          const c = staged;
          const attached = c?.references || [];
          const lines = [
            `# ${c?.candidate_id || p.id} — compiled prompt`,
            "",
            `- **Panel** — ${p.id}`,
            `- **Sheet** — ${specId}`,
            `- **Engine** — ${c?.model || modelSel.value || "unrecorded"}`,
            `- **Size** — ${c?.image_size || sizeSel.value || "unrecorded"}${
              c?.aspect_ratio ? " · " + c.aspect_ratio : ""}`,
            `- **Rendered** — ${c?.created_at || "not yet rendered"}`,
            `- **Status** — ${c?.status || "no take yet"}`,
            "",
          ];
          if (attached.length) {
            lines.push(`## Attached references — ${attached.length}`, "");
            attached.forEach(x => lines.push(
              `- ${x.id} — ${x.role || "role unrecorded"}`));
          } else {
            lines.push("## Attached references — none", "",
                       "This take rendered from the written spec and the style",
                       "anchors alone. No subject reference was attached.");
          }
          // Download what is on screen, not what was compiled — the two
          // can differ now, and a download that silently drops your edits
          // is a file that lies about the take it names.
          const shown = promptBox.value;
          if (shown !== r.prompt) {
            lines.splice(lines.length - 1, 0,
              "- **Prompt** — EDITED BY HAND, not the steps 01–04 compile");
          }
          lines.push("", "---", "", "```text", shown, "```", "");
          const blob = new Blob([lines.join("\n")],
                                { type: "text/markdown;charset=utf-8" });
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = `${c?.candidate_id || p.id}.md`;
          document.body.append(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(a.href), 5000);
          toast(`${a.download} downloaded.`);
        };
      } catch (err) { toast(err.message, true); }
    };

    // Composition check (2026-08-13): the screenplay's own scene against
    // the compiled prompt, judged pre-spend. Advisory — WARN never gates;
    // the verdict renders into the same report host as Preview prompt and
    // persists nothing (a changed brief just means re-checking).
    const compBtn = $("[data-f=compcheck]", card);
    if (compBtn) compBtn.onclick = async () => {
      compBtn.disabled = true;
      const busy = startBusy(busyHost,
        `Checking ${p.id} composition against the screenplay…`,
        "one narrative call, no image spend — typically 5–20 seconds");
      try {
        const v = await api(`/api/specs/${specId}/panels/${p.id}/composition-check`, {
          method: "POST",
          json: { ref_ids: checkedRefs(),
                  provider: modelSel.value === "mock" ? "mock" : "" },
        });
        const warns = v.findings.filter(f => f.severity === "WARN").length;
        const anchorLine = v.anchor?.matched
          ? `SCREENPLAY SCENE: ${esc(String(v.anchor.location || "").toUpperCase())} — ${v.anchor.scenes} SCENE${v.anchor.scenes === 1 ? "" : "S"} READ`
          : "SCREENPLAY SCENE NOT LOCATED — JUDGED AGAINST THE SHEET'S SCENE PROSE";
        const rows = v.findings.map(f => `
          <li><span class="mono"${f.severity === "WARN" ? ' style="color:var(--hold)"' : ""}>${f.severity} — ${esc(f.axis)}</span>
            <div class="mono" style="color:var(--ink-dim)">${esc(f.note)}${f.suggestion ? `<br>→ ${esc(f.suggestion)}` : ""}</div></li>`).join("");
        const camInl = $("[data-f=cam-inline]", card);
        // Same scope mistake, same card: this one silently disabled the
        // composition check's Apply suggested camera, since canApply
        // needs the button it could not find.
        const camOpen = $("[data-f=cam-open]", card);
        const canApply = v.suggested_camera && camOpen && !camOpen.disabled;
        const sugLine = v.suggested_camera
          ? `SUGGESTED CAMERA · ${esc(Object.entries(v.suggested_camera)
              .map(([k, x]) => `${k.replace("camera_", "")} ${x.replace(/_/g, " ")}`)
              .join(" · ").toUpperCase())}`
          : "";
        report.innerHTML = `<div class="report${warns ? "" : " pass"}">
          <div class="report-head"><b>Composition check — ${esc(p.id)} · ${warns ? `${warns} WARNING${warns === 1 ? "" : "S"}` : "OK"}</b>
            <button class="ghost" data-f="close-report">Close</button></div>
          <div class="mini mono">${anchorLine} · SPEC ${esc(String(v.spec_hash || "").toUpperCase())} · ${esc(String(v.model || v.provider || ""))}</div>
          ${warns ? "" : `<div class="mini mono">NO AXIS CONFLICT · CHECKED AGAINST ${
            v.anchor?.matched ? esc(String(v.anchor.location || "").toUpperCase())
                              : "THE SHEET'S SCENE PROSE"}</div>`}
          <ul>${rows}</ul>
          ${v.purpose_amendment ? `<div class="mono" style="color:var(--ink-dim)">BRIEF AMENDMENT PROPOSED — ${esc(v.purpose_amendment)}</div>` : ""}
          ${sugLine ? `<div class="mini mono">${sugLine}${canApply
            ? ` <button class="ghost" data-f="comp-apply">Apply suggested camera</button>`
            : camOpen && camOpen.disabled ? " · CAMERA FROZEN BY AN APPROVED TAKE" : ""}</div>` : ""}
        </div>`;
        $("[data-f=close-report]", report).onclick = () => { report.innerHTML = ""; };
        const applyBtn = $("[data-f=comp-apply]", report);
        if (applyBtn) applyBtn.onclick = () => {
          // Act-where-condition-is-met: open the existing camera editor
          // prefilled with the suggestion merged over the current values —
          // the user reviews and hits the same journaled Save camera.
          camOpen.click();
          for (const a of CAMERA_AXES) {
            const want = v.suggested_camera[a.key];
            if (!want) continue;
            const sel = $(`[data-f=cam-${a.f}]`, camInl);
            if (!sel) continue;
            if (a.key === "camera_lens" && ![...sel.options].some(o => o.value === want)) {
              sel.value = "CUSTOM";
              const mm = $("[data-f=cam-lens-mm]", camInl);
              if (mm) { mm.classList.remove("hidden"); mm.value = want.replace(/MM$/, ""); }
            } else {
              sel.value = want;
            }
          }
          applyBtn.disabled = true;
        };
      } catch (err) { toast(err.message, true); }
      busy.done();
      compBtn.disabled = false;
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
      const before = new Set(panelCands.map(c => c.candidate_id));
      const pendId = addPendingTake(specId, p.id, `PAINTING — NEW TAKE · ${size}`);
      const finish = () => { busy.done(); btn.disabled = false; btn.textContent = idleLabel;
        removePendingTake(specId, p.id, pendId); };
      const landed = cand => {
        finish();
        toast(`${cand.candidate_id} generated (${cand.width}×${cand.height}) — CANDIDATE, unapproved.`);
        // A gateway-cut poll can outlive navigation: announce the arrival,
        // never hijack whatever view the user is on now back to this spec
        // (2026-08-12 review). The take is on disk; the strip shows it on
        // the next visit.
        if ($("#board-panels") && $("#board-spec")?.value === specId) {
          renderBoardPanels(specId);
        }
      };
      try {
        landed(await api(`/api/specs/${specId}/panels/${p.id}/generate`, {
          method: "POST",
          signal: ctrl.signal,
          json: {
            ref_ids: checkedRefs(),
            image_size: size,
            aspect_ratio: aspect,
            provider: modelSel.value,
            render_prompt: renderPrompt,
          },
        }));
      } catch (err) {
        if (err.name === "AbortError") {
          finish();
          toast("Canceled. Note: if the model had already started painting, the candidate may still arrive — check the gallery in a minute.");
          return;
        }
        // A cut connection — a gateway 502/504 on a long render, or a dropped
        // fetch — does NOT stop the render: it finishes in the threadpool and the
        // take lands on disk (user 2026-08-09). So keep the pending tile and the
        // spinner up and poll for the take instead of crying failure over a
        // render that is actually completing.
        if ((err instanceof TypeError) || (err.gateway && err.status >= 500)) {
          const fresh = await pollForNewTake(specId, p.id, before,
            { signal: ctrl.signal });
          if (ctrl.signal.aborted) {
            finish();
            toast("Canceled. Note: if the model had already started painting, the candidate may still arrive — check the gallery in a minute.");
            return;
          }
          if (fresh) { landed(fresh); return; }
          finish();
          report.innerHTML = `<div class="report"><b>Still rendering</b> — the connection
            dropped, but the engine keeps working; the take appears in the strip above when
            it finishes (this can take a couple of minutes). Refresh if it doesn't.
            <button class="ghost" style="float:right" onclick="this.parentElement.remove()">Dismiss</button></div>`;
          return;
        }
        finish();
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
            the sensitive element rather than inventory it (edit the breakdown's required
            objects), or try a different engine — policy lines differ.</p>
            ${detail ? `<p class="mini mono" style="margin-top:6px">PROVIDER — ${esc(detail)}</p>` : ""}
            <button class="ghost" style="float:right" onclick="this.parentElement.remove()">Dismiss</button></div>`;
        } else {
          report.innerHTML = `<div class="report fail"><b>Generation failed</b> — ${esc(err.message)}
            <button class="ghost" style="float:right" onclick="this.parentElement.remove()">Dismiss</button></div>`;
        }
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

    // The takes roll hides its scrollbar like the board roll, so it needs
    // the same way to move: drag with momentum. Without this a long strip
    // would be reachable only by wheel.
    const takesRoll = $(".takes-row", card);
    if (takesRoll) dragScroll(takesRoll); stripKeys(takesRoll);

    // Takes filmstrip: a click STAGES that take, and nothing else.
    //
    // It used to open the lightbox at the same time (user 2026-08-15) and
    // the user reversed that on 2026-08-16: "I told you to open the
    // fullsize image if you click the frame. That was bad." Staging is the
    // frequent act — you move along the strip comparing takes — and a
    // modal over every step of that is a door you have to close before you
    // can take the next one. Full size stays one click away on the big
    // viewport image below, which is where you already are once a take is
    // staged.
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
        `Every rejected candidate image for ${specId} is removed from disk. Each rejection reason keeps riding its own panel's future prompts as a director's correction, and stays in the rejection history. This cannot be undone.`,
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

      if (c.status !== "REJECTED") actDanger.append(mk("Reject", "text-act act-reject", async () => {
        const reason = await askText(`Reject ${c.candidate_id}`, "Reason",
          { hint: "recorded verbatim, carried into this panel's future prompts as rejection feedback",
            confirmLabel: "Reject", danger: true });
        if (reason === null) return;
        try {
          await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "REJECTED", reason });
          toast(`${c.candidate_id} rejected.`); refresh();
          proposeCorrections(specId, c.candidate_id, refresh);
        } catch (err) { toast(err.message, true); }
      }));
      actDerive.append(mk("Reference", "text-act act-dim", () => promoteDialog(specId, c),
        c.status !== "APPROVED"
        ? { disabled: true, title: "Approve this take first — only approved renders become canon anchors" }
        : { title: "Promote this approved render into the reference library" }));
      if (c.status !== "APPROVED") actApprove.append(mk("Approve panel", "primary act-approve-btn", async () => {
        try {
          await post(`/api/specs/${specId}/candidates/${c.candidate_id}/status`, { status: "APPROVED" });
          toast(`${c.candidate_id} approved.`); refresh();
          // User-caught 2026-08-23: "the board is still locked" right after
          // approving a panel. It was not a lock bug — approving is what
          // OPENS stage 05, and the band simply never re-read. The two
          // earlier transitions (breakdown lock, panel unlock) each call
          // this on purpose; the last one in the chain was missed, so
          // Boards opened silently on the next navigation instead of now.
          updateBand();
        } catch (err) { toast(err.message, true); }
      }));
      // Withdrawing is NOT rejecting (user 2026-08-16: "I need to be able
      // to put an approved panel back into draft without having to reject
      // it"). The backend and the endpoint have existed since this morning
      // and nothing ever called them — so the only way back out of an
      // approval was Reject, whose reason is carried verbatim into every
      // future prompt for this panel as a DIRECTOR'S CORRECTION. Using it
      // to unlock an edit poisons the work that follows with a correction
      // that was never true.
      if (c.status === "APPROVED") actApprove.append(mk("Withdraw approval",
        "text-act", async () => {
          try {
            const r = await post(
              `/api/specs/${specId}/candidates/${c.candidate_id}/unapprove`);
            toast(`${r.candidate_id} back to CANDIDATE — the take is untouched, `
                  + "nothing rides future prompts, and the panel is editable again.");
            refresh();
            updateBand();
          } catch (err) { toast(err.message, true); }
        },
        { title: "Put this panel back into draft. The take keeps its image and "
               + "stays in the strip; unlike Reject it records no reason and "
               + "carries nothing into future prompts." }));

      // Re-performance for resolution (never interpolation): the take
      // anchors itself; a locked reproduce-exactly instruction renders it
      // at full size. The answer to a good take trapped in a small file.
      if (c.kind !== "derived_palette") actUse.append(mk("Full-size take", "text-act", () => {
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
      if (c.kind !== "derived_palette") actUse.append(mk("Repair region", "text-act", () =>
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
      actDerive.append(mk("Crop to reference", "text-act act-dim", () =>
        cropToReference({ type: "candidate", spec_id: specId, id: c.candidate_id },
          `/api/specs/${specId}/candidates/${c.candidate_id}/image`),
        c.status !== "APPROVED"
          ? { disabled: true, title: "Approve this take first — crops enter the library as approved canon" }
          : { title: "Harvest a region of this image as a new reference with its own narrow role" }));
      actDerive.append(mk("Light study", "text-act act-dim", async () => {
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
      // 17a — a group folds before the row breaks: DERIVE collapses to ⋯
      // when the bar's content would exceed its box, measured by a
      // ResizeObserver on the bar itself — the rail and the side panel
      // both change the stage's width without changing the viewport's.
      {
        const bar = $(".act-bar", card);
        const deriveZone = $(".act-derive", bar);
        const deriveItems = $("[data-f=act-derive]", bar);
        for (const zn of [".act-use", ".act-derive"]) {
          const zone = $(zn, bar);
          // Count the buttons in the WHOLE zone, not the first .act-items
          // in it. USE holds three spans now (approve · use · danger), and
          // testing only the first hid the entire group the moment a take
          // was approved — Approve correctly steps aside on an approved
          // take, and Full-size take, Repair region and Reject went with
          // it (user-reported 2026-08-14: "no reject button on approved
          // panels"). A rejected take needs Reject gone; an approved one
          // needs it most.
          if (!$$(".act-items button", zone).length) zone.classList.add("hidden");
        }
        let menu = null;
        const closeMenu = () => {
          if (!menu) return;
          deriveItems.append(...menu.querySelectorAll("button"));
          menu.remove(); menu = null;
        };
        $("[data-f=derive-more]", bar).onclick = e => {
          e.stopPropagation();
          if (menu) return closeMenu();
          menu = document.createElement("div");
          menu.className = "card-menu act-derive-menu";
          menu.append(...deriveItems.querySelectorAll("button"));
          deriveZone.append(menu);
          setTimeout(() => document.addEventListener("click", closeMenu, { once: true }));
        };
        // Wrapped content is not overflow — once flex-wrap absorbs the
        // row, scrollWidth never exceeds clientWidth. So the fold's real
        // test is "did any zone leave the first line" — and with
        // align-items:center that means comparing vertical CENTERS, not
        // offsetTops: same-line items of different heights (the 60px
        // Approve zone, 37px text zones, the 0px spacer) have different
        // tops but identical centers, and the offsetTop version folded
        // DERIVE to ⋯ with a bar's worth of room (user 2026-08-08). rAF
        // keeps the mutation out of the observer's own frame.
        const fit = () => requestAnimationFrame(() => {
          closeMenu();
          bar.classList.remove("derive-collapsed");
          const centers = [...bar.children]
            .filter(z => z.offsetParent !== null)
            .map(z => z.offsetTop + z.offsetHeight / 2);
          const spread = Math.max(...centers) - Math.min(...centers);
          if (spread > 8 || bar.scrollWidth > bar.clientWidth + 1)
            bar.classList.add("derive-collapsed");
        });
        new ResizeObserver(fit).observe(bar);
        fit();
      }

      if (c.status === "REJECTED") actDanger.append(mk("Delete forever", "danger", async () => {
        if (!(await askConfirm(`Delete ${c.candidate_id} forever`,
          "The image file is removed from disk and cannot be recovered. Its rejection reason keeps riding this panel's future prompts as a director's correction, and stays in the rejection history.",
          "Delete forever", true))) return;
        try {
          await api(`/api/specs/${specId}/candidates/${c.candidate_id}`, { method: "DELETE" });
          delete roomSel.staged[p.id];
          toast(`${c.candidate_id} permanently deleted.`); refresh();
        } catch (err) { toast(err.message, true); }
      }, { title: "Permanently remove this rejected image and its record from disk" }));
    }
    // Carried panels are LOCKED on the workbench (user 2026-08-13): this
    // revision declared it unchanged, so no work happens here — its take
    // flows to the board from where it was approved. The server refuses
    // amends on carried panels too; this states the gate before it's hit.
    if (carriedRail.has(p.id)) {
      const note = document.createElement("div");
      note.className = "report";
      note.innerHTML = `<b class="mono">CARRIED — NOT IN THIS REVISION</b>
        <p style="margin:6px 0 0">This revision declared ${esc(p.id)} unchanged, so it is locked
        here — its approved take keeps flowing to the board. To work it in this
        revision, use <b>Also revise</b> on the Breakdowns tab.</p>`;
      card.prepend(note);
      for (const f of ["generate", "prose", "compcheck", "brief-edit", "cam-open"]) {
        const b = $(`[data-f=${f}]`, card);
        if (b) { b.disabled = true; b.title = "Carried — not in this revision; Also revise it on the Breakdowns tab first."; }
      }
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
  // A scoped revision lands on the panel it was created to revise
  // (user 2026-08-13); carried panels stay reachable but locked.
  const revisedFirst = (spec.revision_scope?.revised || [])
    .find(id => pids.includes(id));
  if (roomSel.panel !== "__derived" && !pids.includes(roomSel.panel))
    roomSel.panel = revisedFirst || pids[0] || "__derived";
  // A shared /panels/<spec>/<panel> link SELECTS that panel. It used to be
  // handled at the tail of this function by scrolling a `.panel-card` into
  // view — a class this host stopped rendering when the workbench became
  // one card at a time, so the link had been silently landing on whatever
  // panel was last open (found 2026-08-16 while fixing the scroll jump).
  // Selecting is also the truer act now: there is nothing to scroll TO.
  if (_routePanel && pids.includes(_routePanel)) roomSel.panel = _routePanel;

  const slotStatus = {};
  (slotMap?.slots || []).forEach(s => { slotStatus[s.panel_id] = s.status; });
  const approvedCount = pids.filter(pid =>
    candidates.some(c => c.panel_id === pid && c.status === "APPROVED")).length;

  const railMark = pid => {
    if (carriedRail.has(pid))
      return '<span class="rail-mark none" title="Carried — not in this revision; its approved take flows to the board. Also revise it on the Breakdowns tab to work it here.">CARRIED</span>';
    const st = slotStatus[pid];
    const n = candidates.filter(c => c.panel_id === pid).length;
    if (st === "TOO_SMALL") return '<span class="rail-mark bad">SIZE</span>';
    if (st === "OK") return '<span class="rail-mark okdot" title="approved candidate ready"></span>';
    if (n) return `<span class="rail-mark warn" title="${n} take(s), none approved">${n}</span>`;
    return '<span class="rail-mark none">—</span>';
  };
  const latestThumb = pid => {
    const last = candidates.filter(c => c.panel_id === pid).slice(-1)[0];
    return last ? `<img src="/api/specs/${specId}/candidates/${last.candidate_id}/image?size=thumb" loading="lazy" alt="">` : "";
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
      <div class="rail-note">Both are measured from this breakdown's approved panels at assembly.</div>
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
    // The carried list is the server's own carry sources — live rejected
    // takes AND archive rows from deleted takes (2026-08-13: rendering
    // only live records made a deleted take's still-carrying note
    // invisible, which read as destroyed). Visibility equals reality.
    const carried = (carriedFb.items || [])
      .filter(f => f.panel_id === c.panel_id);
    const liveByCand = Object.fromEntries(panelCands.map(t => [t.candidate_id, t]));
    // Correction-intake delta, named in the app's own vocabulary — used
    // by the rail checklist and the >4-delta review modal (R18) alike.
    const intakeLabel = d => d.kind === "camera"
      ? `CAMERA ${(CAMERA_AXES.find(a => a.key === d.field)?.label || d.field.replace("camera_", "")).toUpperCase()} → ${String(d.value).replace(/_/g, " ")}`
      : d.kind === "require" ? `REQUIRE "${d.value}"`
      : d.kind === "forbid" ? `FORBID "${d.value}"`
      : `BRIEF + "${d.value}"`;
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
        <div class="rail-label">ANCHORED TO · ${allRefs.length}</div>
        ${subjRefs.length === 0 ? `
          <div class="nomatch" style="margin:6px 0 2px">
            <b class="mono">NO SUBJECT REFERENCES</b>
            <p>This take was painted from the written spec${styleCount ? ` and the ${styleCount} style plate${styleCount === 1 ? "" : "s"} only` : " alone"}.</p>
          </div>` : ""}
        ${(() => {
          // Grouped by kind (§2.15): eleven plate ids read as four facts,
          // and consecutive ids collapse to a range — the rail states what
          // rode the render, it does not re-show the pictures.
          const byHead = {};
          for (const r of allRefs) (byHead[roleHead(r.role)] ??= []).push(r.id);
          return Object.entries(byHead).map(([h, ids]) => `
            <div class="anchor-kind">
              <span class="anchor-head mono">${esc(h)}</span>
              <span class="anchor-ids mono">${idSpan(ids)}</span>
            </div>`).join("");
        })()}
        <div class="mini mono" style="margin-top:8px;color:var(--ink-faint)">${allRefs.length} PLATE${allRefs.length === 1 ? "" : "S"} RODE THIS RENDER</div>
      </div>
      ${carried.length ? `
      <div class="side-sec">
        <div class="rail-label carried-label">CARRIED NOTES · ${carried.length}<span>RIDE THE NEXT TAKE</span></div>
        ${carried.map(f => `<div class="carried${f.retired ? " retired" : ""}">
          <div class="carried-head">
            <span class="carried-id">${esc(f.source)}</span>
            <span style="display:inline-flex;gap:12px;flex:none">
            <button class="text-act" data-fb-edit="${esc(f.source)}"
              title="Rewrite this note — journaled; deleting it forever also lives in this modal">Edit</button>
            <button class="text-act" data-retire="${esc(f.source)}"
              data-retired="${f.retired ? "1" : ""}"
              title="${f.retired
                ? "Carry this note into future prompts again — journaled"
                : "Stop carrying this note into future prompts — reversible, journaled; the note stays here, stated NOT CARRIED. Stop a note once it is satisfied, or when it contradicts a newer one."}">Stop carrying</button>
            </span>
          </div>
          <div class="carried-note">${esc(f.reason)}</div>
          ${f.archived || f.retired ? `<div class="carried-state">${[
              f.archived ? (f.retired ? "TAKE DELETED" : "TAKE DELETED, NOTE CARRIES") : "",
              f.retired ? "NOT CARRIED" : "",
            ].filter(Boolean).join(" · ")}</div>` : ""}
        </div>${(() => {
          const t = liveByCand[f.source];
          if (!t) return "";
          // Correction intake (2026-08-13): the rejection parsed into
          // proposed structural deltas — the model proposes, the user
          // applies; applied rows read as state, not verbs.
          const ci = t.correction_intake;
          if (!ci || ci.dismissed || !(ci.deltas || []).length) return "";
          const open = ci.deltas.some(d => !d.applied);
          // R18 (HARNESS_AUDIT): a rail is 300px and cannot host an
          // arbitrary form — past four deltas the rail states the count
          // and the checklist opens in a modal.
          if (ci.deltas.length > 4) {
            return `<div class="mini mono" style="margin:2px 0 8px 12px">
              <span style="color:var(--ink-dim)">PROPOSED STRUCTURE · ${ci.deltas.length} DELTAS${open ? "" : " · ALL APPLIED"}</span>
              ${open ? ` <button class="text-act" data-intake-modal="${esc(t.candidate_id)}"
                title="Review and apply the proposed deltas — the model proposes, you promote">Review</button>` : ""}
            </div>`;
          }
          return `<div class="mini mono" data-intake="${esc(t.candidate_id)}" style="margin:2px 0 8px 12px">
            <span style="color:var(--ink-dim)">PROPOSED STRUCTURE — FROM THIS REJECTION</span>
            ${ci.deltas.map((d, i) => `<label style="display:block;margin:2px 0${d.applied ? ";color:var(--ink-faint)" : ""}">
              <input type="checkbox" data-di="${i}" ${d.applied ? "disabled checked" : "checked"}>
              ${esc(intakeLabel(d))}${d.applied ? " · APPLIED" : ""}</label>`).join("")}
            ${open ? `<div style="display:flex;gap:16px;margin-top:5px">
              <button class="text-act" data-apply-intake="${esc(t.candidate_id)}"
                title="Apply the checked deltas to the panel — journaled, lock re-stamped; the verbatim note above still carries until you stop it">Apply selected</button>
              <button class="text-act" data-dismiss-intake="${esc(t.candidate_id)}"
                title="Drop this proposal — the note and its verbatim carry are untouched">Dismiss</button></div>` : ""}
          </div>`;
        })()}`).join("")}
      </div>` : ""}
      </div>`;
    $$("[data-retire]", el).forEach(b => b.onclick = async () => {
      try {
        await api(`/api/specs/${specId}/candidates/${b.dataset.retire}/feedback-retire`,
          { method: "POST", json: { retired: !b.dataset.retired } });
        toast(b.dataset.retired
          ? `${b.dataset.retire} carries again — future prompts ride it.`
          : `${b.dataset.retire} no longer carried — the note stays, stated in the rail.`);
        renderBoardPanels(specId);
      } catch (err) { toast(err.message, true); }
    });
    // Rejection-note verbs (2026-08-13, restructured by HARNESS_AUDIT
    // R17): the rail offers Edit and one reversible Stop carrying; the
    // only door to hard delete is inside the Edit modal, out of pointer
    // range, and still confirmed. All three acts are journaled.
    $$("[data-fb-edit]", el).forEach(b => b.onclick = async () => {
      const item = carried.find(f => f.source === b.dataset.fbEdit);
      const r = await modal({
        title: `Edit ${b.dataset.fbEdit}'s note`,
        fields: [{ name: "v", label: "Note", value: item?.reason || "",
                   hint: "journaled — the note keeps carrying into future prompts with the new words" }],
        confirmLabel: "Save note",
        extraLabel: "Delete forever", extraDanger: true,
      });
      if (r === null) return;
      if (r.__extra) {
        if (!(await askConfirm(`Delete ${b.dataset.fbEdit}'s note forever`,
            "The note leaves the rail and every future prompt for this panel. The take's history and the approval log keep the record. This cannot be undone.",
            "Delete note", true))) return;
        try {
          await api(`/api/specs/${specId}/candidates/${b.dataset.fbEdit}/feedback-delete`,
            { method: "POST", json: {} });
          toast(`${b.dataset.fbEdit} note deleted — journaled; no longer carried.`);
          renderBoardPanels(specId);
        } catch (err) { toast(err.message, true); }
        return;
      }
      try {
        await api(`/api/specs/${specId}/candidates/${b.dataset.fbEdit}/feedback-edit`,
          { method: "POST", json: { reason: r.v } });
        toast(`${b.dataset.fbEdit} note updated — it carries into future prompts as written.`);
        renderBoardPanels(specId);
      } catch (err) { toast(err.message, true); }
    });
    // R18: past four deltas the checklist opens here instead of the rail.
    $$("[data-intake-modal]", el).forEach(b => b.onclick = () => {
      const t = liveByCand[b.dataset.intakeModal];
      const ci = t?.correction_intake;
      if (!ci) return;
      modal({
        custom: `<div class="modal-title">Proposed structure — ${esc(t.candidate_id)}</div>
          <p class="modal-body">Parsed from this note. The model proposes, you promote.</p>
          <div class="mini mono" data-intake="${esc(t.candidate_id)}">
            ${ci.deltas.map((d, i) => `<label style="display:block;margin:3px 0${d.applied ? ";color:var(--ink-faint)" : ""}">
              <input type="checkbox" data-di="${i}" ${d.applied ? "disabled checked" : "checked"}>
              ${esc(intakeLabel(d))}${d.applied ? " · APPLIED" : ""}</label>`).join("")}
          </div>
          <div class="modal-actions">
            <button class="ghost" data-x="dismiss" style="margin-right:auto"
              title="Drop this proposal — the note and its verbatim carry are untouched">Dismiss proposal</button>
            <button class="ghost" data-x="cancel">Cancel</button>
            <button class="primary" data-x="apply"
              title="Apply the checked deltas to the panel — journaled, lock re-stamped">Apply selected</button>
          </div>`,
        mount: (ov, done) => {
          $("[data-x=cancel]", ov).onclick = () => done(null);
          $("[data-x=dismiss]", ov).onclick = async () => {
            try {
              await api(`/api/specs/${specId}/candidates/${t.candidate_id}/correction-intake/dismiss`,
                { method: "POST", json: {} });
              done(null);
              renderBoardPanels(specId);
            } catch (err) { toast(err.message, true); }
          };
          $("[data-x=apply]", ov).onclick = async () => {
            const indices = $$("input[data-di]:checked", ov)
              .filter(x => !x.disabled).map(x => +x.dataset.di);
            if (!indices.length) { toast("Nothing selected.", true); return; }
            try {
              const r = await api(`/api/specs/${specId}/candidates/${t.candidate_id}/correction-intake/apply`,
                { method: "POST", json: { indices } });
              toast(`${r.applied} delta${r.applied === 1 ? "" : "s"} applied — journaled; the next take paints from them.`);
              done(null);
              renderBoardPanels(specId);
            } catch (err) { toast(err.message, true); }
          };
        },
      });
    });
    // Correction-intake acts — wired outside the prompt block so a take
    // without a stored prompt still gets them.
    $$("[data-apply-intake]", el).forEach(b => b.onclick = async () => {
      const box = $(`[data-intake="${b.dataset.applyIntake}"]`, el);
      const indices = $$("input[data-di]:checked", box)
        .filter(x => !x.disabled).map(x => +x.dataset.di);
      if (!indices.length) { toast("Nothing selected.", true); return; }
      try {
        const r = await api(`/api/specs/${specId}/candidates/${b.dataset.applyIntake}/correction-intake/apply`,
          { method: "POST", json: { indices } });
        toast(`${r.applied} delta${r.applied === 1 ? "" : "s"} applied — journaled; the next take paints from them.`);
        renderBoardPanels(specId);
      } catch (err) { toast(err.message, true); }
    });
    $$("[data-dismiss-intake]", el).forEach(b => b.onclick = async () => {
      try {
        await api(`/api/specs/${specId}/candidates/${b.dataset.dismissIntake}/correction-intake/dismiss`,
          { method: "POST", json: {} });
        renderBoardPanels(specId);
      } catch (err) { toast(err.message, true); }
    });
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

  // Put the reader back. The new DOM is the same height as the old one in
  // every redraw case (a staged take swaps an image, it does not add a
  // card), so this lands on the same pixel rather than approximately.
  // An explicit route to a panel below wins — it asked to move.
  if (isRedraw && !_routePanel) window.scrollTo({ top: keepY, behavior: "instant" });

  // The panel itself was selected above, before the room rendered. All
  // that is left is to put the view at the top of it and let the address
  // settle back to the spec — the route is one shot.
  if (_routePanel) {
    _routePanel = "";
    host.scrollIntoView({ behavior: "smooth", block: "start" });
    syncUrl();
  }
}

/* --------------------------------------------------- assembly (stage 05) */

async function renderAssembly() {
  useTemplate("tpl-assembly");
  // One board per UNIT (2026-08-13): the picker lists bases, not
  // revisions — the newest locked revision labels the unit.
  const allSpecs = await api("/api/specs");
  const byBase = {};
  const units = [];
  for (const s of allSpecs.filter(x => x.locked)) {
    const b = baseOf(s.specification_id);
    if (!byBase[b]) { byBase[b] = { base: b, structure: s, family: 0 }; units.push(byBase[b]); }
    else if (revOf(s) > revOf(byBase[b].structure)) byBase[b].structure = s;
  }
  for (const s of allSpecs) {
    const b = baseOf(s.specification_id);
    if (byBase[b]) byBase[b].family += 1;
  }
  const specs = units;  // downstream: one entry per unit
  const sel = $("#asm-spec");
  sel.innerHTML = `<option value="">— select a signed-off breakdown —</option>` +
    units.map(u => `<option value="${esc(u.base)}">${esc(u.base)} — ${esc(u.structure.subject)}${
      u.family > 1 ? ` · ${u.family} REVISIONS` : ""}</option>`).join("");
  sel.onchange = () => { uiSet("asmSpec", sel.value); syncUrl(true); sel.value ? renderAssemblyFor(sel.value) : renderAssembly(); };

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
  const all = (await Promise.all(units.map(u =>
    api(`/api/specs/${u.base}/boards`)
      .then(bs => bs.map(b => ({ ...b, _spec: u.structure, _base: u.base, _family: u.family })))
      .catch(() => []))))
    .flat()
    .sort((a, b) => String(b.candidate_id).localeCompare(String(a.candidate_id)));

  if (!all.length) {
    // C2 (ratified 2026-08-01): the middle state gets one line, not the
    // checklist — the picker and bench already state the path by being
    // present. The line disappears the moment a board exists.
    const note = `<div class="mini mono asm-none">NO BOARDS YET &mdash; APPROVE EVERY PANEL IN A SHEET, THEN ASSEMBLE</div>`;
    const rememberedA = baseOf(uiGet("asmSpec", ""));
    if (rememberedA && units.some(u => u.base === rememberedA)) {
      sel.value = rememberedA;
      await renderAssemblyFor(rememberedA);
      host.insertAdjacentHTML("afterbegin", note);
      return;
    }
    if (units.length === 1) {
      sel.value = units[0].base;
      await renderAssemblyFor(sel.value);
      host.insertAdjacentHTML("afterbegin", note);
      return;
    }
    host.innerHTML = note;
    return;
  }

  const lbItems = all.map(b => ({
    src: `/api/specs/${b._base}/candidates/${b.candidate_id}/image`,
    caption: `${b.candidate_id} — ${b._spec.subject || b._spec.specification_id} (${b.status}) ${b.width}×${b.height}`,
  }));

  const showGrid = () => {
    uiSet("drilledBoard", "");
    syncUrl();  // leaving a drilled board: the address drops its id
    host.innerHTML = "";
    const p = document.createElement("div");
    p.className = "panel";
    p.dataset.f = "made-boards";   // A7: arrange mode hides it
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
        <img src="${lbItems[i].src}?size=thumb" loading="lazy" alt="${esc(b.candidate_id)}">
        <div class="body">
          <div><span class="badge ${esc(b.status)}">${esc(b.status === "CANDIDATE" ? "CANDIDATE — UNAPPROVED" : b.status)}</span> <b>${esc(b.candidate_id)}</b></div>
          <div class="meta">${esc(b._spec.subject || b._spec.specification_id)}</div>
          <div class="meta">${b.width}×${b.height}${b.layout_variant ? ` · ${esc(b.layout_variant)} layout` : ""} · ${esc((b.created_at || "").slice(0, 16).replace("T", " "))}${
            b._family > 1 ? ` · BUILT ON R${String(b.specification_id || "").match(/_R(\d+)$/)?.[1] || 1}` : ""}</div>
        </div>`;
      card.onclick = () => showBoard(b, i);
      grid.append(card);
    });
    host.append(p);
  };

  const showBoard = (b, i) => {
    // The drilled board is addressable AND remembered.
    uiSet("drilledBoard", b.candidate_id);
    history.pushState(null, "", "/boards/"
      + encodeURIComponent(b._base || baseOf(b._spec.specification_id)) + "/"
      + encodeURIComponent(b.candidate_id));
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
      const sid = b._base || baseOf(b._spec.specification_id);
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
              ${takeOf(pid) ? `<img src="/api/specs/${sid}/candidates/${esc(takeOf(pid))}/image?size=md" loading="lazy" alt="${esc(pid)}" data-bfp="${esc(pid)}" title="Click for the full-sized, uncropped take (${esc(takeOf(pid))})">` : ""}
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
      const card = renderCard(b._spec.specification_id, b, () => renderAssembly(), lbItems, i, null, "md");
      card.classList.add("board-solo");
      bh.append(card);
    }
    host.append(p);
  };

  // The drilled board is REMEMBERED (user 2026-08-13): leaving the tab
  // and coming back reopens the same board; showGrid clears it.
  const pendingOpen = uiGet("openBoard", "") || uiGet("drilledBoard", "");
  if (pendingOpen) {
    uiSet("openBoard", "");
    const idx = all.findIndex(x => x.candidate_id === pendingOpen);
    if (idx >= 0) { showBoard(all[idx], idx); return; }
    uiSet("drilledBoard", "");  // the remembered board no longer exists
  }
  // The board being WORKED ON is remembered too (user 2026-08-13):
  // returning to this tab reopens the selected breakdown's bench, not
  // the grid. Clearing the picker is the way back to the grid.
  const rememberedA = uiGet("asmSpec", "");
  if (rememberedA && specs.some(s2 => s2.specification_id === rememberedA)) {
    sel.value = rememberedA;
    await renderAssemblyFor(rememberedA);
    return;
  }
  showGrid();
}

async function renderAssemblyFor(specId) {
  const host = $("#assembly-host");
  host.innerHTML = `<div class="panel mini">Loading…</div>`;
  // The slot map resolves the unit first: the base id is also R1's spec
  // id, so the STRUCTURE spec (newest locked revision) must come from the
  // map, never from a bare specs read (one board per unit, 2026-08-13).
  let sm = null;
  try { sm = await api(`/api/specs/${specId}/slot-map`); }
  catch { /* the map is a preview; assembly still states its own errors */ }
  const structureId = sm?.structure_spec_id || specId;
  const [{ spec }, candidates, boards] = await Promise.all([
    api(`/api/specs/${structureId}`),
    api(`/api/specs/${specId}/candidates?scope=base`),
    api(`/api/specs/${specId}/boards`),
  ]);
  host.innerHTML = "";
  const structRev = Number(String(structureId).match(/_R(\d+)$/)?.[1] || 1);

  // The slot map makes the never-upscaled rule visible BEFORE a render is
  // spent: exact assembler geometry, one verdict per slot (Part A.4 canonical:
  // ID chip top-left, verdict chip bottom-right, APP-DRAWN title block).
  // Layout is presentation grammar, not canon — the variant chips rearrange
  // how approved work hangs on the canvas and are recorded on the board.
  const VERDICT = { OK: "OK", UNAPPROVED: "UNAPPROVED",
                    TOO_SMALL: "TOO SMALL", NO_CANDIDATE: "NO CANDIDATE",
                    STALE_APPROVAL: "REVISED SINCE" };
  // A STALE_APPROVAL slot states the choice in full in its own title and
  // Keep act; the not-ready alert speaks the one shared verdict
  // vocabulary (R14, HARNESS_AUDIT: a third member, not a third
  // mechanism). (One board per unit,
  // 2026-08-13): the panel changed in a later revision, so its old take
  // is OFFERED — re-render on the workbench, or Keep it explicitly.
  const staleLine = s =>
    `${s.panel_id} APPROVED AGAINST R${s.offered_from_revision} — ` +
    `${s.panel_id} CHANGED IN R${structRev}; RE-RENDER ON THE WORKBENCH OR KEEP`;
  const slotHtml = sm => {
    const notReady = sm.slots.filter(s => s.status !== "OK");
    const minY = Math.min(1, ...sm.slots.map(s => s.y));
    return `
      ${notReady.length ? `<div class="slot-alert">${notReady.length} SLOT${notReady.length > 1 ? "S" : ""} NOT READY —
        ${esc(notReady.map(s =>
          `${s.panel_id} ${VERDICT[s.status].toLowerCase()}`).join(" · "))}
        — nothing is ever blown up${notReady.some(s => s.status === "TOO_SMALL") ? "; regenerate the small panel larger" : ""}</div>` : ""}
      <div class="slotmap" style="aspect-ratio:${sm.canvas.width}/${sm.canvas.height}">
        <div class="slot apdrawn" style="left:1.7%;top:3%;width:96.6%;height:${Math.max(4, (minY - 0.05) * 100).toFixed(1)}%">
          <span class="slot-id">${esc((_bandState?.project || spec.project || "").toUpperCase())} — ${esc((spec.subject || specId).toUpperCase())}</span>
          <span class="slot-id">TITLE BLOCK · APP-DRAWN</span>
        </div>
        ${sm.slots.map(s => `
          <div class="slot ${s.status === "OK" ? "clean" : s.status === "TOO_SMALL" ? "hatch-bad" : "hatch"} ${esc(s.status)}" style="left:${(s.x * 100).toFixed(2)}%;top:${(s.y * 100).toFixed(2)}%;width:${(s.w * 100).toFixed(2)}%;height:${(s.h * 100).toFixed(2)}%"
               title="${esc(s.title)} — slot ${s.slot_width}×${s.slot_height}px${s.candidate_id ? ` · ${s.candidate_id}${s.candidate_width ? ` ${s.candidate_width}×${s.candidate_height}px` : ""}` : ""}${s.status === "STALE_APPROVAL" ? ` · ${esc(staleLine(s))}` : ""}">
            ${s.candidate_id || s.offered_candidate_id ? `<img class="slot-img" src="/api/specs/${encodeURIComponent(specId)}/candidates/${esc(s.candidate_id || s.offered_candidate_id)}/image?size=thumb" loading="lazy" alt="">` : ""}
            <span class="slot-id">${esc(s.panel_id)}${s.allocation_percent ? ` · ${s.allocation_percent}%` : ""}${s.status === "TOO_SMALL" ? ` · ${s.candidate_width} PX` : ""}${
              s.from_revision && s.from_revision !== structRev ? ` · FROM R${s.from_revision}` : ""}${s.kept ? " · KEPT" : ""}</span>
            ${s.status === "STALE_APPROVAL" ? `<button type="button" class="text-act" data-keep="${esc(s.panel_id)}" data-cand="${esc(s.offered_candidate_id)}"
              title="Keep the R${s.offered_from_revision} take for this slot — an explicit, journaled decision; the slot stops asking">Keep</button>` : ""}
            <span class="slot-verdict ${esc(s.status)}">${VERDICT[s.status]}</span>
          </div>`).join("")}
      </div>`;
  };

  // (sm was fetched at the top — the structure spec depends on it.)

  // Layout moved to the sheet grammar (SHEET_SYSTEM_PLAN ba-4a): stage 05
  // judges readiness, the arrange room arranges. The variant chips are
  // gone — Arrange this board opens the room inline on this scene's
  // BOARD sheet, and the map reads the default grammar.
  const variant = sm?.layout_variant === "arranged" ? "arranged" : "aspect";
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
      <button class="ghost" id="asm-arrange" title="Open the arrange room right here — this scene's BOARD sheet, slots already made from this slot map. Readiness travels with it and is not recomputed.">Arrange this board</button>
      <button class="primary" id="asm-go" ${sm?.ready && !dupBoard ? "" : "disabled"} title="${dupBoard ? `Already assembled as ${dupBoard.candidate_id} with these exact takes — approve a new take to assemble again, or rearrange it below` : sm?.ready ? "Compose the latest approved candidate of every panel onto the canvas with board typography — no upscaling" : "Enabled when every slot reads OK — approve a candidate per panel at sufficient size first"}">${dupBoard ? "Assembled" : "Assemble 4K board"}</button>
    </div>
    <div class="slot-caption" style="margin-top:14px">
      <span class="f-label">Slot map · true 4K canvas</span>
      <span class="hint">readiness only — Arrange this board opens the arrange room below</span>
    </div>
    <div data-f="slot-wrap">${sm ? slotHtml(sm) : ""}</div>
    <div id="asm-arrange-host" style="margin-top:14px"></div>
    <div class="row" data-f="canvas-row">
      <label class="mini" title="Pixel dimensions of the final assembled board. Panels are composed at native resolution — never upscaled — so every panel needs enough source resolution for its allocation.">Canvas <select id="asm-size">
        <option value="3840x2160" selected>3840 × 2160 (4K UHD)</option>
        <option value="4096x2304">4096 × 2304 (DCI-flavor wide)</option>
        <option value="4500x2400">4500 × 2400 (print-leaning)</option>
      </select></label>
    </div>
    <div id="asm-busy"></div>
    <div class="ref-grid" id="asm-gallery" style="margin-top:12px"></div>`;
  host.append(asm);

  // The Keep act — delegated, because the slot map re-renders on every
  // canvas change. An explicit, journaled seat of the old take.
  asm.addEventListener("click", async e => {
    const kb = e.target.closest("[data-keep]");
    if (!kb) return;
    try {
      await api(`/api/specs/${specId}/board-keeps/${kb.dataset.keep}`,
        { method: "PUT", json: { candidate_id: kb.dataset.cand } });
      toast(`${kb.dataset.keep} — old take kept; journaled. The slot stops asking.`);
      refreshMap();
    } catch (err) { toast(err.message, true); }
  });

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
        ? `Already assembled as ${dup.candidate_id} with these exact takes — approve a new take to assemble again, or rearrange it below`
        : sm.ready
          ? "Compose the latest approved candidate of every panel onto the canvas with board typography — no upscaling"
          : "Enabled when every slot reads OK — approve a candidate per panel at sufficient size first";
    } catch (err) { toast(err.message, true); }
  };
  $("#asm-size", asm).onchange = refreshMap;

  // Arrange is a MODE, not an addition (user 2026-08-13: the readiness
  // map beside the arranged tiles read as two copies of the board). The
  // room REPLACES the slot map; Done arranging — or the room's own
  // Close — brings the map back. Every change already saved.
  const roomHost = $("#asm-arrange-host", asm);
  const slotCap = $(".slot-caption", asm);
  const slotWrap = $("[data-f=slot-wrap]", asm);
  const setArrangeMode = open => {
    slotCap?.classList.toggle("hidden", open);
    slotWrap?.classList.toggle("hidden", open);
    // A7 (RULE_PASS_2 A): the hand-over was half-done. Scrolling past the
    // room you were still looking at this spec's earlier boards, each with
    // a live Approve and a live Delete forever — two copies of the board
    // PLUS the destructive verbs of a different task. A mode hands over
    // the whole surface: canvas select and the completed-boards grid go
    // with the map. One board on screen at a time.
    $("[data-f=canvas-row]", asm)?.classList.toggle("hidden", open);
    asm.parentElement?.querySelector("[data-f=made-boards]")
      ?.classList.toggle("hidden", open);
    // A6: three ways out of one surface, stacked. The parent's primary is
    // the one control that toggles (R7), so the room does not draw a
    // second — and you cannot assemble while arranging.
    $("#asm-go", asm)?.classList.toggle("hidden", open);
    const b = $("#asm-arrange", asm);
    if (b) {
      b.textContent = open ? "Done arranging" : "Arrange this board";
      b.title = open
        ? "Close the arrange room — every change is already saved"
        : "Switch this board into arrange mode — the readiness map hands over to the room";
    }
  };
  const closeRoom = () => {
    roomHost.innerHTML = "";
    uiSet("asm.room", "");
    syncUrl(true);
    setArrangeMode(false);
    // Done arranging returns to a map that TELLS THE TRUTH: refetch it
    // so it shows the arranged geometry, not the packer's default.
    refreshMap();
  };
  const openRoom = async () => {
    const rec = await api(`/api/specs/${specId}/arrange`, { method: "POST" });
    await renderArrangeRoom(rec.sheet_id, roomHost, closeRoom);
    setArrangeMode(true);
  };
  $("#asm-arrange", asm).onclick = async () => {
    if (roomHost.childElementCount) return closeRoom();
    uiSet("asm.room", specId);
    syncUrl(true);
    try { await openRoom(); } catch (err) { toast(err.message, true); closeRoom(); }
  };
  if (uiGet("asm.room", "") === specId) {
    openRoom().catch(() => uiSet("asm.room", ""));
  }

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
  watchForUpdates();
  let first = false;
  try {
    const pr = await api("/api/projects");
    first = pr.first_run;
    uiLoad(pr.active || "");
  } catch { uiLoad(""); /* boot anyway */ }
  if (!first) {
    // Deep-link support: a pasted path (/panels/SPEC-0001, /boards/…)
    // outranks the remembered view; "/" reopens exactly where the app
    // was left. Legacy #view hashes still land, then read as paths.
    const routed = applyRoute(location.pathname);
    const stored = uiGet("view", "status");
    const hashView = location.hash.slice(1).split("/")[0];
    showView(routed
      || (Object.hasOwn(views, hashView) ? hashView
        : Object.hasOwn(views, stored) ? stored : "status"),
      { push: false });
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

/* ---------------------------------------------------------- arrange room
   The board's arrange physics (user 2026-08-12, prototyped in the Reflow
   Lab): tiles are the real takes, ghosted; edges and corners resize with
   linked renegotiation; dropping a tile on another splits it (sides go
   beside, top/bottom stacks); claim arrows take an edge to the canvas;
   the trash benches a panel and + docks it back. The client owns only
   the rows -> columns -> stacked-cells STRUCTURE during a gesture —
   every commit PUTs it to /api/sheets/{id}/arrangement and the SERVER
   maps structure to slot geometry, the stored truth. Overlays are app
   chrome and never enter render_sheet. */

function sheetSizeLine(sh) {
  const [w, h] = sh.size;
  return sh.medium === "PRINT"
    ? `${w * 300} × ${h * 300} AT 300 DPI (${w} × ${h} IN)`
    : `${w} × ${h} PX`;
}

async function renderArrangeRoom(sheetId, host, onClose) {
  const root = host;
  let sh = await api(`/api/sheets/${sheetId}`);
  let ready = await api(`/api/sheets/${sheetId}/readiness`);
  const specId = sh.spec_id || "";
  // The unit's whole pool, ordered revision-major oldest-first — the
  // last-wins fold below then reads "newest revision's newest approved".
  const cands = specId
    ? await api(`/api/specs/${baseOf(specId)}/candidates?scope=base`).catch(() => []) : [];
  const BW = sh.size[0], BH = sh.size[1];
  // The panels live in the sheet's CONTENT field (inside margins and the
  // masthead band), not the full page — the server states the rect. All
  // room geometry (surface aspect, pixel readouts, ratio snap, crop
  // aspects) works in this field, so the room, the slot map, the gate
  // and the export all describe the same panels (bug 2026-08-13: the
  // room previewed 16:9-canvas shapes the export never had).
  const CR = sh.content_rect || { w: 1, h: 1, x: 0, y: 0 };
  const CW = BW * CR.w, CH = BH * CR.h;
  const GRID_X = 24, GRID_Y = 12, SNAP_PX = 10;
  let GUT = 6;  // CSS px, derived from the sheet-pixel gutter in layout()
  const MIN_W = 0.07, MIN_H = 0.09, MIN_CELL = 0.2;
  const RATIOS = [["2.39:1", 2.39], ["16:9", 16 / 9], ["4:3", 4 / 3], ["1:1", 1]];

  // Take facts per panel: the sheet's slots carry the ids; the candidate
  // list fills in pixel dimensions and covers benched panels.
  const takeOf = {};
  for (const b of sh.blocks || []) {
    for (const s of b.slots || []) {
      if (s.panel_id && s.candidate_id) {
        takeOf[s.panel_id] = { spec: s.spec_id, cand: s.candidate_id };
      }
    }
  }
  const latestApproved = {};
  for (const c of cands) {
    if (c.status === "APPROVED" && String(c.candidate_id || "").startsWith("CAND-")) {
      latestApproved[c.panel_id] = c;
    }
  }
  const factsFor = pid => {
    // Latest approved wins (2026-08-13): the pinned slot id is only the
    // fallback for panels whose take lost approval.
    const la = latestApproved[pid];
    const t = la ? { spec: la.spec_id || specId, cand: la.candidate_id,
                     rev: la.revision } : takeOf[pid];
    if (!t) return null;
    const rec = cands.find(c => c.candidate_id === t.cand);
    return { ...t, w: rec?.width || 0, h: rec?.height || 0 };
  };
  // Client mirror of sheet.display_window — gesture feedback only; the
  // server recomputes the same window when it renders and judges.
  const winFor = (crop, aspect, nw, nh) => {
    const c = crop || {};
    const fx = c.x || 0, fy = c.y || 0;
    const fw = c.w || 1, fh = c.h || 1;
    if (!nw || !nh || !aspect) return { x: fx, y: fy, w: fw, h: fh };
    let w = fw, h = (w * nw) / (aspect * nh);
    if (h < fh) { h = fh; w = (aspect * nh * h) / nw; }
    if (w > 1) { w = 1; h = (w * nw) / (aspect * nh); }
    if (h > 1) { h = 1; w = (aspect * nh * h) / nw; }
    w = Math.min(w, 1); h = Math.min(h, 1);
    const x = Math.min(Math.max(0, 1 - w), Math.max(0, fx + fw / 2 - w / 2));
    const y = Math.min(Math.max(0, 1 - h), Math.max(0, fy + fh / 2 - h / 2));
    return { x, y, w, h };
  };
  const cropFor = pid => {
    for (const b of sh.blocks || []) {
      for (const s of b.slots || []) {
        if (s.panel_id === pid) return s.crop || null;
      }
    }
    return null;
  };
  const panelOf = (blockId, slotId) => {
    const b = (sh.blocks || []).find(x => x.block_id === blockId);
    return b?.slots.find(s => s.slot_id === slotId)?.panel_id || slotId;
  };

  const clone = o => JSON.parse(JSON.stringify(o));
  let arr = sh.arrangement?.rows ? clone(sh.arrangement) : { rows: [], bench: [] };
  arr.bench = arr.bench || [];
  let gutter = Number.isFinite(arr.gutter) ? arr.gutter : 36;  // sheet px
  const allIds = () => {
    const out = [];
    for (const r of arr.rows) for (const c of r.cols) for (const k of c.cells) out.push(k.id);
    return out;
  };

  /* ------------------------------------------------ structure physics */
  const normalize = st => {
    for (const row of st.rows) row.cols = row.cols.filter(c => c.cells.length);
    st.rows = st.rows.filter(r => r.cols.length);
    const hs = st.rows.reduce((a, r) => a + r.h, 0) || 1;
    for (const row of st.rows) {
      row.h /= hs;
      const ws = row.cols.reduce((a, c) => a + c.w, 0) || 1;
      for (const col of row.cols) {
        col.w /= ws;
        const cs = col.cells.reduce((a, k) => a + k.h, 0) || 1;
        for (const cell of col.cells) cell.h /= cs;
      }
    }
    return st;
  };
  const rectsOf = st => {
    const out = {};
    let y = 0;
    st.rows.forEach((row, ri) => {
      let x = 0;
      row.cols.forEach((col, ci) => {
        let cy = y;
        col.cells.forEach((cell, ki) => {
          out[cell.id] = { x, y: cy, w: col.w, h: row.h * cell.h, ri, ci, ki };
          cy += row.h * cell.h;
        });
        x += col.w;
      });
      y += row.h;
    });
    return out;
  };
  const findCell = (id, st) => {
    for (let ri = 0; ri < st.rows.length; ri++) {
      const row = st.rows[ri];
      for (let ci = 0; ci < row.cols.length; ci++) {
        const ki = row.cols[ci].cells.findIndex(k => k.id === id);
        if (ki >= 0) return { ri, ci, ki };
      }
    }
    return null;
  };
  const removeCell = (st, id) => {
    const p = findCell(id, st);
    if (p) st.rows[p.ri].cols[p.ci].cells.splice(p.ki, 1);
    normalize(st);
  };
  const share = (list, idx, target, key, min) => {
    if (list.length === 1) return;
    const max = 1 - min * (list.length - 1);
    const v = Math.min(max, Math.max(min, target));
    const others = list.reduce((a, o, i) => i === idx ? a : a + o[key], 0);
    const k = (1 - v) / (others || 1);
    list.forEach((o, i) => { o[key] = i === idx ? v : o[key] * k; });
  };
  const insertionAt = (px, py, st) => {
    let y = 0;
    const bands = [0];
    for (const row of st.rows) { y += row.h; bands.push(y); }
    for (let bi = 0; bi < bands.length; bi++) {
      if (Math.abs(py - bands[bi]) < 0.035) return { kind: "row", at: bi };
    }
    const R = rectsOf(st);
    for (const id of Object.keys(R)) {
      const r = R[id];
      if (px < r.x || px > r.x + r.w || py < r.y || py > r.y + r.h) continue;
      const u = (px - r.x) / r.w, v = (py - r.y) / r.h;
      const d = [["left", u], ["right", 1 - u], ["top", v], ["bottom", 1 - v]]
        .sort((a, b) => a[1] - b[1])[0][0];
      return { kind: d === "left" || d === "right" ? "beside" : "stack",
               side: d, target: id };
    }
    return { kind: "row", at: st.rows.length };
  };
  const placedIn = (base, id, ins) => {
    const st = clone(base);
    removeCell(st, id);
    const p = ins.target ? findCell(ins.target, st) : null;
    if (ins.kind === "row" || !p) {
      const at = Math.min(ins.at ?? st.rows.length, st.rows.length);
      st.rows.splice(at, 0,
        { h: 1 / (st.rows.length + 1), cols: [{ w: 1, cells: [{ id, h: 1 }] }] });
      return normalize(st);
    }
    const row = st.rows[p.ri], col = row.cols[p.ci];
    if (ins.kind === "beside") {
      const at = p.ci + (ins.side === "right" ? 1 : 0);
      col.w /= 2;
      row.cols.splice(at, 0, { w: col.w, cells: [{ id, h: 1 }] });
    } else {
      const cell = col.cells[p.ki];
      const at = p.ki + (ins.side === "bottom" ? 1 : 0);
      cell.h /= 2;
      col.cells.splice(at, 0, { id, h: cell.h });
    }
    return normalize(st);
  };
  // One step, not the whole canvas (user 2026-08-13): the claim cuts
  // THROUGH the next panel — the edge extends to that neighbor's far
  // edge, and only that neighbor re-homes. Clicking again takes the
  // next one; the canvas edge is reached by walking, not leaping.
  const claimedTo = (base, id, dir) => {
    const st = clone(base);
    const p = findCell(id, st);
    if (!p) return null;
    const row = st.rows[p.ri], col = row.cols[p.ci], cell = col.cells[p.ki];
    let displaced = [];
    if (dir === "left" || dir === "right") {
      const ni = p.ci + (dir === "right" ? 1 : -1);
      if (ni < 0 || ni >= row.cols.length) return null;
      const [removed] = row.cols.splice(ni, 1);
      displaced = removed.cells.map(k => k.id);
      col.w += removed.w;
    } else {
      const nk = p.ki + (dir === "down" ? 1 : -1);
      if (nk >= 0 && nk < col.cells.length) {
        const [removed] = col.cells.splice(nk, 1);
        displaced = [removed.id];
        cell.h += removed.h;
      } else {
        const nr = p.ri + (dir === "down" ? 1 : -1);
        if (nr < 0 || nr >= st.rows.length) return null;
        const [removedRow] = st.rows.splice(nr, 1);
        displaced = removedRow.cols.flatMap(c => c.cells.map(k => k.id));
        row.h += removedRow.h;
      }
    }
    if (!displaced.length) return null;
    normalize(st);
    const orig = rectsOf(normalize(clone(base)));
    let cur = st;
    for (const d of displaced) {
      const oc = orig[d];
      const cx = oc.x + oc.w / 2, cy = oc.y + oc.h / 2;
      const R = rectsOf(cur);
      let best = null, bd = Infinity;
      for (const tid of Object.keys(R)) {
        if (tid === id && Object.keys(R).length > 1) continue;
        const r = R[tid];
        const dx = (r.x + r.w / 2) - cx, dy = (r.y + r.h / 2) - cy;
        if (dx * dx + dy * dy < bd) { bd = dx * dx + dy * dy; best = { tid, r }; }
      }
      if (!best) return null;
      const r = best.r;
      const dyc = cy - (r.y + r.h / 2);
      // Refugees STACK into their nearest neighbor, never dock beside
      // it — a beside-split would rebuild the very boundary the claim
      // just cut through and the click would read as doing nothing
      // (user-hit 2026-08-13, found in the Reflow Lab).
      cur = placedIn(cur, d, {
        kind: "stack", side: dyc < 0 ? "top" : "bottom", target: best.tid });
    }
    const out = normalize(cur);
    out._claimed = displaced;
    return out;
  };

  /* --------------------------------------------------------- markup */
  const exportBtns = ok => `
      <button class="ghost" data-f="export-pdf" ${ok ? "" : `disabled title="Export is blocked — the gate below states by what"`}>Export PDF</button>
      <button class="${ok ? "primary" : "ghost"}" data-f="export" ${ok ? "" : `disabled title="Export is blocked — the gate below states by what"`}>Export PNG</button>`;
  root.innerHTML = `
    <div class="lb-head">
      <span class="lb-title mono">${esc((sh.masthead?.title || "BOARD").toUpperCase())} — ARRANGED BOARD</span>
      <span class="lb-saved mono" title="There is no save button — every change writes rev ${sh.rev}">EVERY CHANGE SAVED</span>
      <button class="ghost" data-f="style" title="Choose a presentation style for this board — the room stays neutral; the style shows in previews and export">Style…</button>
      <span data-f="export-slot">${exportBtns(ready.ready)}</span>
    </div>
    <div class="stage-meta mono">BOARD · ${sh.medium === "PRINT" ? "3:2" : "16:9"} · ${esc(sheetSizeLine(sh))}
      <span class="stage-meta-note">drag middle to move · drop on a tile to split · edges resize · Alt = free</span></div>
    <div class="arr-ctls mono">
      <label>GUTTER <input type="range" data-f="gutter" min="0" max="120" step="6" value="${gutter}">
        <span data-f="gutter-val">${gutter} PX</span></label>
      <button class="vchip set" data-f="readouts" title="Per-frame pixel readouts">READOUTS</button>
      <button class="arr-corner-add hidden" data-f="corner-add" title="Dock a benched panel back onto the board as a bottom row">
        <svg viewBox="0 0 12 12" fill="none"><path d="M6 1.5 V10.5 M1.5 6 H10.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
        <span data-f="bench-n"></span></button>
    </div>
    <div class="arr-board" data-f="board">
      <div class="arr-ghost" data-f="ghost"><span class="arr-ghost-k mono" data-f="ghost-k"></span></div>
      <div class="arr-arrows" data-f="arrows"></div>
      <div class="arr-menu" data-f="menu"></div>
      <div class="arr-chip mono" data-f="chip"></div>
    </div>
    <div class="arr-hud mono" data-f="hud">hover a frame — its slot and take facts read here</div>
    <div data-f="gate"></div>`;

  const boardEl = $("[data-f=board]", root);
  const ghost = $("[data-f=ghost]", root);
  const ghostK = $("[data-f=ghost-k]", root);
  const chip = $("[data-f=chip]", root);
  const hud = $("[data-f=hud]", root);
  const gateEl = $("[data-f=gate]", root);
  const menuEl = $("[data-f=menu]", root);
  const cornerAdd = $("[data-f=corner-add]", root);
  boardEl.style.aspectRatio = `${CW} / ${CH}`;

  /* tiles — one per panel this sheet knows (placed or benched) */
  const tiles = {};
  const knownIds = [...new Set([...allIds(), ...arr.bench])];
  const ICON = {
    trash: `<svg viewBox="0 0 12 12" fill="none"><path d="M2.5 3.2 H9.5 M4.2 3.2 V2 H7.8 V3.2 M3.3 3.2 L3.9 10 H8.1 L8.7 3.2 M5.1 5 V8.2 M6.9 5 V8.2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    plus: `<svg viewBox="0 0 12 12" fill="none"><path d="M6 1.5 V10.5 M1.5 6 H10.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,
    crop: `<svg viewBox="0 0 12 12" fill="none"><path d="M3.2 1 V8.8 H11 M1 3.2 H8.8 V11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
  };
  for (const pid of knownIds) {
    const t = factsFor(pid);
    const el = document.createElement("div");
    el.className = "arr-tile";
    el.dataset.pid = pid;
    el.innerHTML = `${t ? `<img class="arr-img" draggable="false" alt="" src="/api/specs/${encodeURIComponent(t.spec)}/candidates/${encodeURIComponent(t.cand)}/image?size=md">` : ""}
      <span class="arr-tag mono">${esc(pid)}${
        t && t.rev && cands.some(c => (c.revision || 1) > t.rev)
          ? ` · FROM R${t.rev}` : ""}</span>
      <span class="arr-dim mono"></span>
      <span class="arr-verdict mono"></span>
      <button class="arr-act arr-trash" data-act="bench" title="Remove from the board — the take goes to the bench; + docks it back">${ICON.trash}</button>
      <button class="arr-act arr-plus" data-act="add" title="Dock a benched panel next to this one">${ICON.plus}</button>
      <button class="arr-act arr-crop" data-act="crop" title="Crop, zoom and rotate inside the frame">${ICON.crop}</button>`;
    boardEl.appendChild(el);
    tiles[pid] = el;
  }

  /* --------------------------------------------------------- painting */
  const layout = (st, skipId = null) => {
    const R = rectsOf(st);
    const bw = boardEl.clientWidth, bh = boardEl.clientHeight;
    GUT = gutter * (bw / BW);
    for (const pid of Object.keys(tiles)) {
      const r = R[pid], el = tiles[pid];
      if (!r) { el.style.display = "none"; continue; }
      el.style.display = "";
      if (pid === skipId) continue;
      const fw = Math.max(4, r.w * bw - GUT), fh = Math.max(4, r.h * bh - GUT);
      el.style.left = (r.x * bw + GUT / 2) + "px";
      el.style.top = (r.y * bh + GUT / 2) + "px";
      el.style.width = fw + "px";
      el.style.height = fh + "px";
      const t = factsFor(pid);
      const pw = Math.round(r.w * CW), ph = Math.round(r.h * CH);
      const crop = cropFor(pid);
      const win = t && t.w ? winFor(crop, pw / ph, t.w, t.h) : null;
      const img = el.querySelector(".arr-img");
      if (img && t && t.w && win && img.complete !== undefined) {
        const scale = Math.max(fw / (win.w * t.w), fh / (win.h * t.h));
        img.style.width = (t.w * scale) + "px";
        img.style.height = (t.h * scale) + "px";
        img.style.left = (fw / 2 - (win.x + win.w / 2) * t.w * scale) + "px";
        img.style.top = (fh / 2 - (win.y + win.h / 2) * t.h * scale) + "px";
        img.style.transform = `rotate(${(crop && crop.rotate) || 0}deg)`;
      }
      // Same verdict the HUD shows — one function, no second rule.
      const { availW, availH, short } = shortFor(pid, r);
      el.classList.toggle("short", !!short);
      el.querySelector(".arr-dim").textContent = `${pw} × ${ph}`;
      el.querySelector(".arr-verdict").textContent =
        short ? `SHORT — PLATE SHOWS ${availW} × ${availH}`
          : (t ? "" : "NO APPROVED TAKE");
    }
    return R;
  };
  const gateHtml = () => {
    const rows = (ready.blocked || []).slice(0, 4).map(b =>
      b.kind === "TYPE_FLOOR"
        ? `<span>${esc(b.block_id)} sets type under the floor — pick a larger size.</span>`
        : b.kind === "SLOT_APPROVAL"
        ? `<span>${esc(panelOf(b.block_id, b.slot_id))} — <span class="mono">${esc(b.candidate_id)}</span> is not approved — approve it on the workbench.</span>`
        : b.kind === "SLOT_OFFERED"
        ? `<span>${esc(b.panel_id || panelOf(b.block_id, b.slot_id))}'s take <span class="mono">${esc(b.candidate_id)}</span> was approved against R${b.from_revision} and the panel changed in R${b.floor} — re-render on the workbench or <button type="button" class="text-act" data-gate-keep="${esc(b.panel_id || "")}" data-cand="${esc(b.candidate_id)}">Keep</button> it.</span>`
        : `<span>${esc(panelOf(b.block_id, b.slot_id))} ${b.have?.[0] ? `has ${b.have[0]}×${b.have[1]}px of the ${b.need[0]}×${b.need[1]} it needs — regenerate larger or crop less` : "has no approved take — approve one on the workbench"}.</span>`)
      .join("");
    return ready.ready ? "" : `
      <div class="panel panel-lead lb-blocked">
        <div class="lb-blocked-k mono">${ready.blocked.length} THING${ready.blocked.length === 1 ? "" : "S"} BLOCK${ready.blocked.length === 1 ? "S" : ""} EXPORT</div>
        <div class="lb-blocked-rows">${rows}
          ${ready.blocked.length > 4 ? `<span class="mono">AND ${ready.blocked.length - 4} MORE</span>` : ""}</div>
      </div>`;
  };
  const paintChrome = () => {
    gateEl.innerHTML = gateHtml();
    // Keep, where the gate states the condition (act-where-condition-is-met).
    $$("[data-gate-keep]", gateEl).forEach(b => b.onclick = async () => {
      try {
        await api(`/api/specs/${baseOf(specId)}/board-keeps/${b.dataset.gateKeep}`,
          { method: "PUT", json: { candidate_id: b.dataset.cand } });
        toast(`${b.dataset.gateKeep} — old take kept; journaled.`);
        ready = await api(`/api/sheets/${sheetId}/readiness`);
        paintChrome();
      } catch (err) { toast(err.message, true); }
    });
    $("[data-f=export-slot]", root).innerHTML = exportBtns(ready.ready);
    const stBtn = $("[data-f=style]", root);
    if (stBtn) {
      stBtn.textContent = sh.look?.key
        ? `Style · ${sh.look.key.replace(/_/g, " ")}` : "Style…";
      stBtn.classList.toggle("on", !!sh.look?.key);
    }
    // A2 (RULE_PASS_2 A): a control for returning benched panels has no
    // business being visible on a board with an empty bench. It carries
    // the count, so the bench is readable without opening anything.
    cornerAdd.classList.toggle("hidden", !arr.bench.length);
    $("[data-f=bench-n]", cornerAdd).textContent =
      `${arr.bench.length} BENCHED`;
    cornerAdd.title =
      `Dock a benched panel back onto the board — on the bench: ${arr.bench.join(", ")}`;
    for (const el of root.querySelectorAll(".arr-plus")) {
      el.classList.toggle("empty", !arr.bench.length);
      el.title = arr.bench.length
        ? `Dock a benched panel next to this one — on the bench: ${arr.bench.join(", ")}`
        : "Nothing on the bench — trash a panel first";
    }
  };
  const paint = () => { layout(arr); paintChrome(); };

  // ONE geometry verdict, read by the tile and by the drag HUD
  // (adversarial review F22). They computed it twice with different rules:
  // the tile against the CROPPED window, the HUD against the full take. The
  // HUD was never pessimistic and the tile was never wrong, so the failure
  // was one-directional — drag a cropped panel, read OK, let go, watch it
  // flip to SHORT. DESIGN_SYSTEM R2 already forbids exactly this: "geometry
  // is computed once and declared… two implementations of one geometry is a
  // drift bug with a permanent maintenance cost."
  const shortFor = (pid, r) => {
    const t = factsFor(pid);
    const pw = Math.round(r.w * CW), ph = Math.round(r.h * CH);
    if (!t || !t.w) return { t, pw, ph, availW: 0, availH: 0, short: false };
    const win = winFor(cropFor(pid), pw / ph, t.w, t.h);
    const availW = win ? Math.round(t.w * win.w) : 0;
    const availH = win ? Math.round(t.h * win.h) : 0;
    return { t, pw, ph, availW, availH,
             short: pw > availW + 1 || ph > availH + 1 };
  };

  // A1 (RULE_PASS_2 A): the four film ratios are discoverable only from
  // use — a legend listing them would be a fifth instruction on a surface
  // that already carries four — so when a snap is in force the HUD names
  // it beside the aspect it produced.
  const RATIO_SNAPS = [[2.39, "2.39:1"], [16 / 9, "16:9"],
                       [4 / 3, "4:3"], [1, "1:1"]];
  const snapNameFor = ar => {
    const hit = RATIO_SNAPS.find(([v]) => Math.abs(ar - v) <= 0.02);
    return hit ? hit[1] : "";
  };

  const hudFor = (pid, live = false) => {
    const r = rectsOf(arr)[pid];
    if (!r) return;
    const { t, pw, ph, availW, availH, short } = shortFor(pid, r);
    const snapped = snapNameFor(pw / ph);
    // B6: with a look in force these numbers are the DRESSED field's, so
    // the room and the gate stop disagreeing — the HUD names which.
    const dressedFor = sh.look?.key
      ? ` · DRESSED FOR ${sh.look.key.replace(/_/g, " ")}` : "";
    hud.innerHTML = `<b>${esc(pid)}</b> · slot ${pw} × ${ph} px `
      + `(${(pw / ph).toFixed(2)}:1${snapped ? ` — SNAPPED ${snapped}` : ""})`
      + dressedFor
      + (t ? ` · take ${t.w} × ${t.h} · ` : " · no approved take · ")
      + (short
        ? `<span class="arr-bad">SHORT — PLATE SHOWS ${availW} × ${availH} — `
          + `regenerate larger or shrink the frame</span>`
        : `<span class="arr-ok">OK</span>`)
      + (live ? " · dragging" : "");
  };

  /* ---------------------------------------------------------- commit */
  let committing = false;
  const commit = async () => {
    if (committing) return;
    committing = true;
    try {
      sh = await api(`/api/sheets/${sheetId}/arrangement`, {
        method: "PUT", json: { rows: arr.rows, bench: arr.bench, gutter } });
      arr = clone(sh.arrangement);
      ready = await api(`/api/sheets/${sheetId}/readiness`);
    } catch (err) {
      toast(err.message, true);
      sh = await api(`/api/sheets/${sheetId}`);
      arr = sh.arrangement?.rows ? clone(sh.arrangement) : arr;
    } finally {
      committing = false;
      paint();
    }
  };

  /* ------------------------------------------------------ claim arrows */
  const arrowLayer = $("[data-f=arrows]", root);
  const ARROWS = {};
  const ARROW_ROT = { right: 0, down: 90, left: 180, up: 270 };
  let hoveredTile = null, hideTimer = null;
  for (const dir of ["left", "right", "up", "down"]) {
    const b = document.createElement("button");
    b.className = "arr-arrow";
    b.innerHTML = `<svg viewBox="0 0 12 12" fill="none" style="transform: rotate(${ARROW_ROT[dir]}deg)">
      <path d="M1.5 6 H10.5 M6.8 2.2 L10.5 6 L6.8 9.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    // A4 (RULE_PASS_2 A): claimedTo() takes ONE step by design (ruling
    // 2026-08-13, in the comment above it) — the old copy promised the
    // canvas edge and the code delivered the next panel.
    b.title = "Claim through the next panel — it re-homes into its nearest "
      + "neighbour. Click again to take the next one.";
    b.addEventListener("pointerdown", e => { e.stopPropagation(); e.preventDefault(); });
    b.addEventListener("mouseenter", () => {
      clearTimeout(hideTimer);
      if (!hoveredTile) return;
      const c = claimedTo(arr, hoveredTile, dir);
      if (!c) return;
      const r = rectsOf(c)[hoveredTile];
      if (!r) return;
      const bw = boardEl.clientWidth, bh = boardEl.clientHeight;
      ghost.style.display = "block";
      ghost.style.left = (r.x * bw + GUT / 2) + "px";
      ghost.style.top = (r.y * bh + GUT / 2) + "px";
      ghost.style.width = (r.w * bw - GUT) + "px";
      ghost.style.height = (r.h * bh - GUT) + "px";
      ghostK.textContent = `CLICK — ${hoveredTile} CLAIMS THROUGH ${
        (c._claimed || []).join(" · ")}`;
    });
    b.addEventListener("mouseleave", () => { ghost.style.display = "none"; scheduleHide(); });
    b.addEventListener("click", e => {
      e.stopPropagation();
      if (!hoveredTile) return;
      const c = claimedTo(arr, hoveredTile, dir);
      ghost.style.display = "none";
      hideArrows();
      if (c) { arr = c; paint(); commit(); }
    });
    arrowLayer.appendChild(b);
    ARROWS[dir] = b;
  }
  function hideArrows() {
    hoveredTile = null;
    for (const d in ARROWS) ARROWS[d].classList.remove("show");
  }
  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideArrows, 160);
  }
  function showArrows(pid) {
    hoveredTile = pid;
    const r = rectsOf(arr)[pid];
    if (!r) return hideArrows();
    const bw = boardEl.clientWidth, bh = boardEl.clientHeight, eps = 0.004, IN = 15;
    const pos = {
      left:  [r.x * bw + IN, (r.y + r.h / 2) * bh, r.x > eps],
      right: [(r.x + r.w) * bw - IN, (r.y + r.h / 2) * bh, r.x + r.w < 1 - eps],
      up:    [(r.x + r.w / 2) * bw, r.y * bh + IN, r.y > eps],
      down:  [(r.x + r.w / 2) * bw, (r.y + r.h) * bh - IN, r.y + r.h < 1 - eps],
    };
    for (const d in pos) {
      const [px, py, ok] = pos[d];
      ARROWS[d].classList.toggle("show", !!ok);
      ARROWS[d].style.left = px + "px";
      ARROWS[d].style.top = py + "px";
    }
  }

  /* --------------------------------------------------- bench & verbs */
  let menuTarget = null;
  const openMenu = (target, ev) => {
    menuTarget = target;
    menuEl.innerHTML = arr.bench.map(id =>
      `<button data-add="${esc(id)}">${esc(id)}</button>`).join("");
    menuEl.classList.add("open");
    const br = boardEl.getBoundingClientRect();
    if (target && ev) {
      menuEl.style.right = "auto"; menuEl.style.bottom = "auto";
      menuEl.style.left = Math.min(ev.clientX - br.left, br.width - 180) + "px";
      menuEl.style.top = Math.min(ev.clientY - br.top + 10, br.height - 40) + "px";
    } else {
      menuEl.style.left = "auto"; menuEl.style.top = "auto";
      menuEl.style.right = "10px"; menuEl.style.bottom = "64px";
    }
  };
  const dockNear = (id, targetId) => {
    arr.bench = arr.bench.filter(b => b !== id);
    const r = rectsOf(arr)[targetId];
    if (r) {
      const wide = (r.w * CW) / (r.h * CH) > 1.55;
      arr = placedIn(arr, id, { kind: wide ? "beside" : "stack",
                                side: wide ? "right" : "bottom", target: targetId });
    } else {
      arr = placedIn(arr, id, { kind: "row", at: arr.rows.length });
    }
    paint(); commit();
  };
  const benchPanel = pid => {
    if (allIds().length <= 1) {
      toast("A board keeps at least one panel — bench the rest, not the last.", true);
      return;
    }
    hideArrows();
    ghost.style.display = "none";
    removeCell(arr, pid);
    if (!arr.bench.includes(pid)) arr.bench.push(pid);
    paint(); commit();
  };
  menuEl.addEventListener("click", e => {
    const b = e.target.closest("[data-add]");
    if (!b) return;
    menuEl.classList.remove("open");
    const id = b.dataset.add;
    if (menuTarget) dockNear(id, menuTarget);
    else { arr.bench = arr.bench.filter(x => x !== id);
           arr = placedIn(arr, id, { kind: "row", at: arr.rows.length });
           paint(); commit(); }
    menuTarget = null;
  });
  cornerAdd.addEventListener("pointerdown", e => e.stopPropagation());
  cornerAdd.addEventListener("click", e => {
    e.stopPropagation();
    if (!arr.bench.length) return;
    if (arr.bench.length === 1) {
      const id = arr.bench[0];
      arr.bench = [];
      arr = placedIn(arr, id, { kind: "row", at: arr.rows.length });
      paint(); commit();
      return;
    }
    openMenu(null, e);
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".arr-menu") && !e.target.closest(".arr-corner-add")
        && !e.target.closest(".arr-plus")) {
      menuEl.classList.remove("open");
    }
  });

  /* crop — one stage, two tools (2026-08-13, from the Reflow Lab): the
     WHOLE plate with the crop box on the region the panel displays,
     outside dimmed, live ON-THE-PANEL preview beside it. HAND (icon)
     slides the window from anywhere; CROP (icon) edits the box — edges
     resize, inside moves, outside draws fresh, ratio chips apply. The
     crop is framing intent: the server re-derives the drawn window for
     the frame's aspect (sheet.display_window), so what this modal sets
     can grow back out when the frame changes. */
  const ARR_TOOL_ICON = {
    hand: `<svg viewBox="0 0 12 12" fill="none"><path d="M4 6 V2.8 a.7 .7 0 0 1 1.4 0 V5.4 M5.4 5.4 V2.2 a.7 .7 0 0 1 1.4 0 V5.4 M6.8 5.4 V2.9 a.7 .7 0 0 1 1.4 0 V6.2 M8.2 6.2 V4.2 a.7 .7 0 0 1 1.4 0 V7.8 c0 2 -1.2 3.2 -3 3.2 h-.7 c-1 0 -1.8 -.5 -2.4 -1.3 L2.1 7.6 a.75 .75 0 0 1 1.2 -.9 L4 7.6" stroke="currentColor" stroke-width="1.05" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    crop: `<svg viewBox="0 0 12 12" fill="none"><path d="M3.2 1 V8.8 H11 M1 3.2 H8.8 V11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`,
  };
  const cropPanel = async pid => {
    let bid = null, sid = null, slot = null;
    for (const b of sh.blocks || []) {
      for (const s of b.slots || []) {
        if (s.panel_id === pid) { bid = b.block_id; sid = s.slot_id; slot = s; }
      }
    }
    const t = factsFor(pid);
    if (!slot?.candidate_id || !t) {
      return toast("No take in this frame to crop.", true);
    }
    const src = `/api/specs/${esc(slot.spec_id)}/candidates/${esc(slot.candidate_id)}/image?size=md`;
    const rect = rectsOf(arr)[pid];
    const frameA = rect ? (rect.w * CW) / (rect.h * CH) : 16 / 9;
    const RATS = [["SLOT", 0], ["16:9", 16 / 9], ["2.39:1", 2.39],
                  ["4:3", 4 / 3], ["1:1", 1], ["FREE", -1]];
    let f = { x: 0, y: 0, w: 1, h: 1, rotate: 0, ...(slot.crop || {}) };
    let ratio = 0;
    let tool = "hand";
    const wantAspect = () => ratio === 0 ? frameA : ratio;
    if (t.w && Math.abs((f.w * t.w) / (f.h * t.h) - frameA) / frameA > 0.01) {
      f = { ...f, ...winFor(f, frameA, t.w, t.h) };
    }
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    ov.innerHTML = `
      <div class="modal arr-crop-modal" role="dialog" aria-modal="true">
        <div class="modal-title">${esc(pid)} — crop on the full plate</div>
        <div class="arr-crop-tools">
          <button class="arr-tool on" data-tool="hand" title="Hand — drag anywhere to reposition the image within the crop">${ARR_TOOL_ICON.hand}</button>
          <button class="arr-tool" data-tool="crop" title="Crop — resize the box by its edges, draw fresh outside it">${ARR_TOOL_ICON.crop}</button>
          <span class="arr-crop-ratios hidden">${RATS.map(([n]) =>
            `<button class="vchip${n === "SLOT" ? " on" : ""}" data-ratio="${n}">${n}</button>`).join("")}</span>
          <label class="mono lb-rot">ROTATE <input type="number" id="arr-rot" min="-45" max="45" step="0.5" value="${f.rotate || 0}">°</label>
        </div>
        <div class="arr-crop-side">
          <div class="arr-crop-plate">
            <div class="arr-crop-stage"><img src="${src}" draggable="false" alt="">
              <div class="arr-crop-box"><span class="bk mono"></span></div></div>
          </div>
          <div class="arr-crop-preview-wrap">
            <div class="arr-crop-preview-k mono">ON THE PANEL</div>
            <div class="arr-crop-preview"><img src="${src}" draggable="false" alt=""></div>
          </div>
        </div>
        <p class="hint" data-f="tool-hint">Hand — drag anywhere to slide what the frame shows.</p>
        <div class="modal-actions">
          <button class="ghost" data-f="cancel">Cancel</button>
          <button class="primary" data-f="save">Save crop</button>
        </div>
      </div>`;
    document.body.appendChild(ov);
    const stage = $(".arr-crop-stage", ov);
    const box = $(".arr-crop-box", ov);
    const bk = $(".bk", box);
    const prev = $(".arr-crop-preview", ov);
    const prevImg = $("img", prev);
    const ratioRow = $(".arr-crop-ratios", ov);
    prev.style.aspectRatio = `${frameA}`;

    const lockH = () => {
      const want = wantAspect();
      if (want > 0 && t.w) f.h = (f.w * t.w) / (want * t.h);
    };
    const clampF = () => {
      f.w = Math.min(1, Math.max(0.04, f.w));
      f.h = Math.min(1, Math.max(0.04, f.h));
      if (f.h > 1) {
        f.h = 1;
        const want = wantAspect();
        if (want > 0 && t.w) f.w = (want * t.h) / t.w;
      }
      f.x = Math.min(1 - f.w, Math.max(0, f.x));
      f.y = Math.min(1 - f.h, Math.max(0, f.y));
    };
    const paintCrop = () => {
      box.style.left = `${f.x * 100}%`;
      box.style.top = `${f.y * 100}%`;
      box.style.width = `${f.w * 100}%`;
      box.style.height = `${f.h * 100}%`;
      bk.textContent = t.w
        ? `${Math.round(f.w * t.w)} × ${Math.round(f.h * t.h)} PX` : "";
      const vw = prev.clientWidth, vh = prev.clientHeight;
      if (vw && t.w) {
        const scale = Math.max(vw / (f.w * t.w), vh / (f.h * t.h));
        prevImg.style.width = (t.w * scale) + "px";
        prevImg.style.height = (t.h * scale) + "px";
        prevImg.style.left = (vw / 2 - (f.x + f.w / 2) * t.w * scale) + "px";
        prevImg.style.top = (vh / 2 - (f.y + f.h / 2) * t.h * scale) + "px";
      }
    };
    requestAnimationFrame(paintCrop);
    prevImg.onload = paintCrop;

    const C = 12;
    let act = null;
    const boxMode = ev => {
      const b = box.getBoundingClientRect();
      const x = ev.clientX - b.left, y = ev.clientY - b.top;
      if (x < -C || x > b.width + C || y < -C || y > b.height + C) return null;
      const L = Math.abs(x) < C, R2 = Math.abs(b.width - x) < C;
      const T = Math.abs(y) < C, B = Math.abs(b.height - y) < C;
      if (L || R2 || T || B) return { l: L, r: R2, t: T, b: B };
      if (x >= 0 && x <= b.width && y >= 0 && y <= b.height) return "move";
      return null;
    };
    const setCursor = ev => {
      if (act) return;
      if (tool === "hand") { stage.style.cursor = "grab"; return; }
      const m = ev ? boxMode(ev) : null;
      stage.style.cursor = !m ? "crosshair" : m === "move" ? "move"
        : (m.l && m.t) || (m.r && m.b) ? "nwse-resize"
        : (m.l && m.b) || (m.r && m.t) ? "nesw-resize"
        : (m.l || m.r) ? "ew-resize" : "ns-resize";
    };
    stage.addEventListener("pointermove", ev => setCursor(ev));
    stage.addEventListener("pointerdown", ev => {
      const rc = stage.getBoundingClientRect();
      const px = (ev.clientX - rc.left) / rc.width;
      const py = (ev.clientY - rc.top) / rc.height;
      if (tool === "hand") {
        act = { kind: "move", px, py, f0: { ...f } };
        stage.style.cursor = "grabbing";
      } else {
        const m = boxMode(ev);
        act = m === "move" ? { kind: "move", px, py, f0: { ...f } }
          : m ? { kind: "edge", m, px, py, f0: { ...f } }
          : { kind: "draw", px, py };
      }
      stage.setPointerCapture(ev.pointerId);
      ev.preventDefault();
    });
    stage.addEventListener("pointermove", ev => {
      if (!act) return;
      const rc = stage.getBoundingClientRect();
      const px = Math.max(0, Math.min(1, (ev.clientX - rc.left) / rc.width));
      const py = Math.max(0, Math.min(1, (ev.clientY - rc.top) / rc.height));
      if (act.kind === "move") {
        f.x = act.f0.x + (px - act.px);
        f.y = act.f0.y + (py - act.py);
        clampF();
      } else if (act.kind === "draw") {
        f.x = Math.min(act.px, px);
        f.y = Math.min(act.py, py);
        f.w = Math.abs(px - act.px) || 0.01;
        f.h = Math.abs(py - act.py) || 0.01;
        lockH();
        clampF();
      } else {
        const m = act.m, f0 = act.f0;
        f = { ...f, x: f0.x, y: f0.y, w: f0.w, h: f0.h };
        if (m.l) { f.x = f0.x + (px - act.px); f.w = f0.w - (px - act.px); }
        if (m.r) f.w = f0.w + (px - act.px);
        if (m.t) { f.y = f0.y + (py - act.py); f.h = f0.h - (py - act.py); }
        if (m.b) f.h = f0.h + (py - act.py);
        if (f.w < 0.04) f.w = 0.04;
        if (f.h < 0.04) f.h = 0.04;
        if (wantAspect() > 0) {
          const anchorBottom = m.t && !m.b;
          const oldH = f.h;
          lockH();
          if (anchorBottom) f.y += oldH - f.h;
        }
        clampF();
      }
      paintCrop();
    });
    const endAct = () => { act = null; setCursor(); };
    stage.addEventListener("pointerup", endAct);
    stage.addEventListener("pointercancel", endAct);

    const setTool = tl => {
      tool = tl;
      $$("[data-tool]", ov).forEach(b =>
        b.classList.toggle("on", b.dataset.tool === tl));
      ratioRow.classList.toggle("hidden", tl !== "crop");
      $("[data-f=tool-hint]", ov).textContent = tl === "hand"
        ? "Hand — drag anywhere to slide what the frame shows."
        : "Crop — drag the box's edges to resize, inside to move, outside to draw fresh. SLOT keeps the frame's ratio.";
      setCursor();
    };
    ov.addEventListener("click", async e => {
      const tb = e.target.closest("[data-tool]");
      if (tb) return setTool(tb.dataset.tool);
      const rc = e.target.closest("[data-ratio]");
      if (rc) {
        ratio = RATS.find(x => x[0] === rc.dataset.ratio)[1];
        $$("[data-ratio]", ov).forEach(b => b.classList.toggle("on", b === rc));
        lockH();
        clampF();
        paintCrop();
        return;
      }
      if (e.target.dataset.f === "cancel" || e.target === ov) { ov.remove(); return; }
      if (e.target.dataset.f === "save") {
        try {
          await api(`/api/sheets/${sheetId}/blocks/${bid}/slots/${sid}`, {
            method: "PUT", json: { crop: { x: +f.x.toFixed(4), y: +f.y.toFixed(4),
              w: +f.w.toFixed(4), h: +f.h.toFixed(4),
              rotate: parseFloat($("#arr-rot", ov).value) || 0 } } });
          ov.remove();
          sh = await api(`/api/sheets/${sheetId}`);
          ready = await api(`/api/sheets/${sheetId}/readiness`);
          paint();
        } catch (err) { toast(err.message, true); }
      }
    });
  };

  /* ------------------------------------------------------ style picker */
  // Board looks (2026-08-13): the room always works in INK; a chosen
  // look dresses previews and export only. Cards are REAL renders of
  // this sheet at a small scale (md-tier sources server-side), so the
  // user chooses from the actual board, not an illustration.
  const stylePicker = async () => {
    let cat;
    try { cat = await api(`/api/sheets/looks`); }
    catch (err) { return toast(err.message, true); }
    let selKey = sh.look?.key || "";
    let opts = { ...(sh.look?.options || {}) };
    const cards = [{ key: "", label: "Ink — none", options: {} }, ...cat];
    const ov = document.createElement("div");
    ov.className = "modal-scrim";
    ov.innerHTML = `
      <div class="modal arr-style-modal" role="dialog" aria-modal="true">
        <div class="modal-title">Board style — each card is this board, rendered</div>
        <div class="arr-style-cards">${cards.map(c => `
          <button class="arr-style-card${c.key === selKey ? " on" : ""}" data-key="${esc(c.key)}">
            <span class="arr-style-img" style="aspect-ratio:${BW} / ${BH}"><span class="mini">rendering…</span></span>
            <span class="arr-style-name mono">${esc(c.key ? c.label.toUpperCase() : "INK — NONE")}</span>
          </button>`).join("")}</div>
        <div class="arr-style-opts mono" data-f="opts"></div>
        <p class="hint">The room stays INK while you arrange — the chosen style dresses previews, export and the assembled board.</p>
        <div class="modal-actions">
          <button class="ghost" data-f="cancel">Cancel</button>
          <button class="primary" data-f="apply">Apply style</button>
        </div>
      </div>`;
    document.body.appendChild(ov);
    const urls = [];
    const cleanup = () => { urls.forEach(u => URL.revokeObjectURL(u)); ov.remove(); };
    const cardImg = key =>
      $(`.arr-style-card[data-key="${CSS.escape(key)}"] .arr-style-img`, ov);
    const loadCard = async c => {
      const body = { scale: 0.12,
        look: c.key ? { key: c.key, options: c.key === selKey ? opts : {} } : null };
      const r = await fetch(`/api/sheets/${sheetId}/render`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body) });
      const holder = cardImg(c.key);
      if (!holder) return;
      if (!r.ok) { holder.innerHTML = `<span class="mini">preview failed</span>`; return; }
      const u = URL.createObjectURL(await r.blob());
      urls.push(u);
      holder.innerHTML = `<img src="${u}" alt="${esc(c.label)} preview">`;
    };
    // two renders in flight at a time — a card is a real sheet render
    const queue = [...cards];
    Array.from({ length: 2 }, async () => {
      while (queue.length && ov.isConnected) await loadCard(queue.shift());
    });
    const paintOpts = () => {
      const c = cat.find(x => x.key === selKey);
      const host = $("[data-f=opts]", ov);
      host.innerHTML = c ? Object.entries(c.options).map(([n, m]) => `
        <label><input type="checkbox" data-opt="${esc(n)}"${(opts[n] ?? m.default) ? " checked" : ""}> ${esc(m.label.toUpperCase())}</label>`).join("")
        : `<span class="mini">INK is the bare working sheet — no dress</span>`;
    };
    paintOpts();
    ov.onclick = async e => {
      if (e.target === ov) return cleanup();
      const card = e.target.closest(".arr-style-card");
      if (card) {
        selKey = card.dataset.key;
        opts = selKey === (sh.look?.key || "") ? { ...(sh.look?.options || {}) } : {};
        for (const el of ov.querySelectorAll(".arr-style-card")) {
          el.classList.toggle("on", el === card);
        }
        paintOpts();
        return;
      }
      const opt = e.target.closest("[data-opt]");
      if (opt) {
        opts[opt.dataset.opt] = opt.checked;
        const holder = cardImg(selKey);
        if (holder) holder.innerHTML = `<span class="mini">rendering…</span>`;
        await loadCard(cat.find(x => x.key === selKey) || cards[0]);
        return;
      }
      const f = e.target.dataset.f || "";
      if (f === "cancel") return cleanup();
      if (f === "apply") {
        try {
          sh = await api(`/api/sheets/${sheetId}/look`, {
            method: "PUT",
            json: { key: selKey || null, options: selKey ? opts : undefined } });
          ready = await api(`/api/sheets/${sheetId}/readiness`);
          cleanup();
          paint();
          toast(selKey
            ? `Style set: ${selKey.replace(/_/g, " ")} — previews and export now dress the board.`
            : "Style cleared — the board exports as bare INK.");
        } catch (err) { toast(err.message, true); }
      }
    };
  };

  /* --------------------------------------------------------- pointers */
  const EDGE = 9, CORNER = 14;
  let drag = null;
  const hitMode = (el, ev) => {
    const r = el.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    const L = x < EDGE, R2 = r.width - x < EDGE, T = y < EDGE, B = r.height - y < EDGE;
    const Lc = x < CORNER, Rc = r.width - x < CORNER,
          Tc = y < CORNER, Bc = r.height - y < CORNER;
    if ((Lc || Rc) && (Tc || Bc)) return { l: Lc, r: Rc, t: Tc, b: Bc, corner: true };
    if (L || R2 || T || B) return { l: L, r: R2, t: T, b: B, corner: false };
    return null;
  };
  const cursorFor = m => {
    if (!m) return "grab";
    if (m.corner) return (m.l && m.t) || (m.r && m.b) ? "nwse-resize" : "nesw-resize";
    return (m.l || m.r) ? "ew-resize" : "ns-resize";
  };
  const snapFrac = (v, steps, span) =>
    !steps ? v : (Math.abs(Math.round(v * steps) / steps - v) * span <= SNAP_PX
      ? Math.round(v * steps) / steps : v);

  boardEl.addEventListener("pointermove", ev => {
    if (drag) return;
    if (ev.target.closest(".arr-arrow") || ev.target.closest(".arr-act")
        || ev.target.closest(".arr-corner-add")) { clearTimeout(hideTimer); return; }
    const el = ev.target.closest(".arr-tile");
    if (!el) { boardEl.style.cursor = ""; scheduleHide(); return; }
    boardEl.style.cursor = cursorFor(hitMode(el, ev));
    hudFor(el.dataset.pid);
    clearTimeout(hideTimer);
    if (el.dataset.pid !== hoveredTile) showArrows(el.dataset.pid);
  });
  boardEl.addEventListener("pointerleave", () => scheduleHide());

  boardEl.addEventListener("pointerdown", ev => {
    const act = ev.target.closest(".arr-act");
    if (act) { ev.stopPropagation(); ev.preventDefault(); return; }
    const el = ev.target.closest(".arr-tile");
    if (!el) return;
    ev.preventDefault();
    ghost.style.display = "none";
    hideArrows();
    boardEl.classList.add("dragging");
    boardEl.setPointerCapture(ev.pointerId);
    const pid = el.dataset.pid;
    const p = findCell(pid, arr);
    if (!p) return;
    const col = arr.rows[p.ri].cols[p.ci];
    drag = {
      pid, el, mode: hitMode(el, ev), start: clone(arr), pos: p,
      x0: ev.clientX, y0: ev.clientY,
      startW: col.w, startRowH: arr.rows[p.ri].h,
      startCellH: col.cells[p.ki].h,
      grabbed: el.getBoundingClientRect(),
      moved: false, preview: null,
    };
    el.classList.add("active");
  });

  boardEl.addEventListener("pointermove", ev => {
    if (!drag) return;
    const bw = boardEl.clientWidth, bh = boardEl.clientHeight;
    const dx = (ev.clientX - drag.x0) / bw, dy = (ev.clientY - drag.y0) / bh;
    if (Math.abs(dx) * bw + Math.abs(dy) * bh > 3) drag.moved = true;
    const free = ev.altKey;

    if (drag.mode) {                                   /* resize */
      const st = clone(drag.start);
      const p = drag.pos;
      const col = st.rows[p.ri].cols[p.ci];
      const innerTop = drag.mode.t && p.ki > 0;
      const innerBottom = drag.mode.b && p.ki < col.cells.length - 1;
      let w = drag.startW;
      if (drag.mode.l || drag.mode.r) {
        w = drag.startW + (drag.mode.r ? dx : -dx);
        if (!free) w = snapFrac(w, GRID_X, bw);
      }
      let caught = "";
      if (drag.mode.corner && !free) {
        const t = factsFor(drag.pid);
        const cellAbsH = drag.startRowH * drag.startCellH;
        const cand = t && t.w ? [[`TAKE ${t.w}×${t.h}`, t.w / t.h], ...RATIOS] : RATIOS;
        const aspect = (w * CW) / (cellAbsH * CH);
        for (const [name, target] of cand) {
          if (Math.abs(aspect - target) / target < 0.05) {
            w = (target * cellAbsH * CH) / CW;
            caught = name;
            break;
          }
        }
      }
      if (drag.mode.l || drag.mode.r) share(st.rows[p.ri].cols, p.ci, w, "w", MIN_W);
      if (innerTop || innerBottom) {
        let ch = drag.startCellH + (innerBottom ? dy : -dy) / drag.startRowH;
        if (!free) {
          const abs = snapFrac(drag.startRowH * ch, GRID_Y, bh);
          ch = abs / drag.startRowH;
        }
        share(st.rows[p.ri].cols[p.ci].cells, p.ki, ch, "h", MIN_CELL);
      } else if (drag.mode.t || drag.mode.b) {
        let h = drag.startRowH + (drag.mode.b ? dy : -dy);
        if (!free) h = snapFrac(h, GRID_Y, bh);
        share(st.rows, p.ri, h, "h", MIN_H);
      }
      arr = normalize(st);
      layout(arr);
      if (caught) {
        chip.style.display = "block";
        chip.textContent = caught;
        const br = boardEl.getBoundingClientRect();
        chip.style.left = (ev.clientX - br.left + 14) + "px";
        chip.style.top = (ev.clientY - br.top + 14) + "px";
      } else chip.style.display = "none";
      hudFor(drag.pid, true);
      return;
    }

    /* move: lift + split-dock ghost preview — the state under your hand
       IS the state you get */
    if (!drag.moved) return;
    const el = drag.el;
    el.classList.add("lifted");
    const br = boardEl.getBoundingClientRect();
    el.style.left = (drag.grabbed.left - br.left + ev.clientX - drag.x0) + "px";
    el.style.top = (drag.grabbed.top - br.top + ev.clientY - drag.y0) + "px";
    const px = Math.min(1, Math.max(0, (ev.clientX - br.left) / bw));
    const py = Math.min(1, Math.max(0, (ev.clientY - br.top) / bh));
    const without = clone(drag.start);
    removeCell(without, drag.pid);
    const ins = insertionAt(px, py, without);
    const next = placedIn(drag.start, drag.pid, ins);
    drag.preview = next;
    const R = layout(next, drag.pid);
    const r = R[drag.pid];
    if (r) {
      ghost.style.display = "block";
      ghost.style.left = (r.x * bw + GUT / 2) + "px";
      ghost.style.top = (r.y * bh + GUT / 2) + "px";
      ghost.style.width = (r.w * bw - GUT) + "px";
      ghost.style.height = (r.h * bh - GUT) + "px";
      ghostK.textContent = ins.kind === "row" ? "NEW ROW"
        : `SPLIT — ${ins.kind === "beside" ? "BESIDE" : "STACKED"} ${ins.side === "left" || ins.side === "top" ? "BEFORE" : "AFTER"} ${ins.target}`;
    }
  });

  const endDrag = commitIt => {
    if (!drag) return;
    drag.el.classList.remove("active", "lifted");
    boardEl.classList.remove("dragging");
    ghost.style.display = "none";
    chip.style.display = "none";
    const changed = drag.moved || drag.mode;
    if (drag.preview && commitIt) arr = drag.preview;
    else if (!commitIt) arr = drag.start;
    drag = null;
    normalize(arr);
    paint();
    if (changed && commitIt) commit();
  };
  boardEl.addEventListener("pointerup", () => endDrag(true));
  boardEl.addEventListener("pointercancel", () => endDrag(false));
  const escHandler = ev => { if (ev.key === "Escape") endDrag(false); };
  window.addEventListener("keydown", escHandler);

  /* tile verbs + head actions */
  boardEl.addEventListener("click", ev => {
    const act = ev.target.closest(".arr-act");
    if (!act) return;
    ev.stopPropagation();
    const pid = act.closest(".arr-tile").dataset.pid;
    if (act.dataset.act === "bench") return benchPanel(pid);
    if (act.dataset.act === "crop") return cropPanel(pid);
    if (act.dataset.act === "add") {
      if (!arr.bench.length) return;
      if (arr.bench.length === 1) return dockNear(arr.bench[0], pid);
      return openMenu(pid, ev);
    }
  });
  root.onclick = async e => {
    const f = e.target.dataset.f || "";
    try {
      if (f === "back") {
        window.removeEventListener("keydown", escHandler);
        return onClose();
      }
      if (f === "style") return stylePicker();
      if (f === "export" || f === "export-pdf") {
        const r = await api(`/api/sheets/${sheetId}/export`, {
          method: "POST", json: { format: f === "export-pdf" ? "pdf" : "png" } });
        window.open(`/api/sheets/${sheetId}/export/${encodeURIComponent(r.file)}`, "_blank");
        return;
      }
    } catch (err) { toast(err.message, true); }
  };

  /* gutter slider (live visual, commits on release) + readouts toggle */
  const gutIn = $("[data-f=gutter]", root);
  const gutVal = $("[data-f=gutter-val]", root);
  gutIn.addEventListener("input", () => {
    gutter = +gutIn.value;
    gutVal.textContent = `${gutter} PX`;
    layout(arr);
  });
  gutIn.addEventListener("change", () => commit());
  const roBtn = $("[data-f=readouts]", root);
  const paintReadouts = () => {
    const on = uiGet("arr.readouts", true);
    roBtn.classList.toggle("on", on);
    boardEl.classList.toggle("hide-dims", !on);
  };
  roBtn.addEventListener("click", () => {
    uiSet("arr.readouts", !uiGet("arr.readouts", true));
    paintReadouts();
  });
  paintReadouts();

  new ResizeObserver(() => { if (!drag) paint(); }).observe(boardEl);
  normalize(arr);
  paint();

  // A board opened after new approvals refreshes itself: if any slot
  // pins a take that is no longer its panel's latest approved, one
  // silent commit re-resolves every slot (server rule: latest wins) and
  // the gate re-judges against the new pixels.
  const stale = (sh.blocks || []).some(b => (b.slots || []).some(s =>
    s.panel_id && latestApproved[s.panel_id]
    && s.candidate_id !== latestApproved[s.panel_id].candidate_id));
  if (stale) commit();
}

boot();
