/* The tutorial runtime — authored onboarding, run against the live app.
 *
 * Content comes from the server as JSON (app/tutorials.py). Nothing in
 * here knows what any particular tutorial says: steps name an ANCHOR and
 * the anchor registry (content/tutorial_schema.json) turns it into a
 * selector, so a redesign moves one line there instead of breaking every
 * walkthrough.
 *
 * Three things it must never do:
 *   - hang. A step whose anchor never appears falls back to a centred
 *     modal and moves on; it does not sit on a scrim forever.
 *   - interrupt. One tutorial at a time, never over an open dialog, and
 *     never while the user is mid-gesture in a modal.
 *   - lie about progress. Every step records to the server, so a refresh
 *     resumes where the user actually was.
 *
 * It leans on app.js globals: api, toast, esc, showView, applyRoute.
 */
(() => {
  "use strict";

  const WAIT_FOR_ANCHOR_MS = 4000;   // then fall back to a modal
  const STATE_TTL_MS = 1500;         // /api/state cache for predicates

  let BUNDLE = null;                 // { tutorials, state, version }
  let ANCHORS = {};                  // name → selector
  let running = null;                // the live run, or null
  let booted = false;

  // ---------------------------------------------------------------- events
  // app.js emits sb:api after every successful call and sb:view on every
  // navigation. Those two are the whole event surface: they are how a step
  // knows the user actually did the thing it asked for.

  const listeners = new Set();
  const fire = ev => { for (const fn of [...listeners]) fn(ev); };
  document.addEventListener("sb:api", e => {
    if (e.detail && e.detail.method !== "GET") stateCache = firstRunCache = null;
    fire({ type: "api", detail: e.detail || {} });
    // NOT while a trigger is being evaluated (2026-08-25). Evaluating a
    // trigger makes API calls; every API call fires sb:api; sb:api
    // re-arms the evaluation. That is a closed loop, and it ran: the only
    // shipped trigger is `not first_run AND not stage_summary.screenplay`,
    // so once the first-run tour was done and a screenplay existed, every
    // idle tab asked GET /api/projects every 400ms and GET /api/state
    // every 1.5s, for as long as it stayed open. Two tabs made ~5
    // requests a second against a studio nobody was touching.
    //
    // The cache below made it cheaper and hid it. The fix is that
    // consideration must not be able to re-arm itself — otherwise the next
    // predicate that fetches anything reintroduces the same loop.
    if (!probing) considerLater();
  });
  document.addEventListener("sb:view", e => {
    fire({ type: "view", detail: e.detail || {} });
    considerLater();
  });
  document.addEventListener("click", e => {
    fire({ type: "click", target: e.target });
  }, true);

  // ------------------------------------------------------------ predicates
  // One grammar, shared by triggers, step skips and advance conditions.
  // The kinds here are exactly the kinds declared in tutorial_schema.json
  // — tests/test_tutorials.py asserts the two lists match, because a
  // condition the server accepts and the browser ignores is a tutorial
  // that silently never fires.

  let stateCache = null;
  let stateCacheAt = 0;
  let firstRunCache = null;
  let firstRunCacheAt = 0;

  /* Reads made to answer a predicate, marked as such.

     They still emit sb:api — that event is the app's one honest record of
     a call happening — but they must not re-arm trigger evaluation, or
     asking whether to start a tutorial becomes the reason to ask again. */
  let probing = 0;
  async function probe(fn) {
    probing++;
    try { return await fn(); } finally { probing--; }
  }

  async function productState() {
    const now = Date.now();
    if (stateCache && now - stateCacheAt < STATE_TTL_MS) return stateCache;
    try { stateCache = await probe(() => api("/api/state")); }
    catch { stateCache = {}; }
    stateCacheAt = now;
    return stateCache;
  }

  /* Whether this install has ever had a production.

     Cached on the same clock as the state above, for the same reason and
     one more: this is close to a constant. It flips false the moment a
     production exists and only returns if every one is deleted, so asking
     twice a second was asking a settled question over and over. */
  async function firstRun() {
    const now = Date.now();
    if (firstRunCache !== null && now - firstRunCacheAt < STATE_TTL_MS) {
      return firstRunCache;
    }
    try { firstRunCache = !!(await probe(() => api("/api/projects"))).first_run; }
    catch { firstRunCache = false; }
    firstRunCacheAt = now;
    return firstRunCache;
  }

  const dig = (obj, path) =>
    String(path || "").split(".").reduce((o, k) => (o == null ? o : o[k]), obj);

  const cmpVersion = (a, b) => {
    const pa = String(a).split("."), pb = String(b).split(".");
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const x = parseInt(pa[i] || "0", 10), y = parseInt(pb[i] || "0", 10);
      if (x !== y) return x < y ? -1 : 1;
    }
    return 0;
  };

  const seenRow = id => (BUNDLE && BUNDLE.state && BUNDLE.state[id]) || null;
  const isDone = id => {
    const r = seenRow(id);
    return !!r && (r.status === "completed" || r.status === "dismissed");
  };

  /* `ev` is the event being tested against (advance conditions), or null
     for a level check (triggers, skips). A condition that needs an edge
     is false without one, and vice versa — that asymmetry is the reason
     the schema declares which contexts each kind may be used in. */
  async function test(pred, self, ev) {
    if (!pred || typeof pred !== "object") return true;
    const [kind, arg] = Object.entries(pred)[0] || [];
    switch (kind) {
      case "always":
        return true;
      case "first_run":
        // The same fact the app boots on — /api/projects declares it.
        return await firstRun();
      case "version_changed": {
        const r = seenRow(self && self.id);
        return !r || r.version !== (BUNDLE && BUNDLE.version);
      }
      case "version_at_least":
        return cmpVersion(BUNDLE ? BUNDLE.version : "0", arg) >= 0;
      case "state":
        return !!dig(await productState(), arg);
      case "state_equals":
        return dig(await productState(), arg && arg.path) === (arg && arg.value);
      case "view":
        return ev ? (ev.type === "view" && ev.detail.view === arg)
                  : document.body.dataset.view === arg;
      case "api":
        if (!ev || ev.type !== "api") return false;
        if (arg.method && String(arg.method).toUpperCase()
            !== String(ev.detail.method || "").toUpperCase()) return false;
        try { return new RegExp(arg.path).test(ev.detail.path || ""); }
        catch { return false; }
      case "click": {
        if (!ev || ev.type !== "click") return false;
        const sel = ANCHORS[arg];
        return !!(sel && ev.target && ev.target.closest
                  && ev.target.closest(sel));
      }
      case "seen":
        return isDone(arg);
      case "not_seen":
        return !isDone(arg);
      case "all":
        for (const p of arg) if (!(await test(p, self, ev))) return false;
        return true;
      case "any":
        for (const p of arg) if (await test(p, self, ev)) return true;
        return false;
      case "not":
        return !(await test(arg, self, ev));
      default:
        return false;   // unknown kind: inert, never accidentally true
    }
  }

  // -------------------------------------------------------------- anchoring

  /* Resolved by SELECTOR every time, never held as an element reference.
     The workbench replaces whole views mid-tour (`useTemplate` calls
     replaceChildren, and several views re-render again as their fetches
     land), so a node captured when the step opened is detached seconds
     later — which strands the cutout on a zero-sized ghost. A rect with
     no area is treated as "not on screen": better a centred modal than a
     spotlight on nothing. */
  const anchorEl = name => {
    const sel = ANCHORS[name];
    if (!sel) return null;
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 ? el : null;
  };

  /* A step cannot assume its target is there the instant it navigates.
     Poll on animation frames until the element exists AND has been the
     same size for two frames — catching it mid-layout is how a popover
     ends up clamped into a corner. */
  function waitForAnchor(name, ms = WAIT_FOR_ANCHOR_MS) {
    return new Promise(resolve => {
      const deadline = Date.now() + ms;
      let last = "";
      const tick = () => {
        const el = anchorEl(name);
        if (el) {
          const r = el.getBoundingClientRect();
          const now = `${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)}`;
          if (now === last) return resolve(el);
          last = now;
        } else {
          last = "";
        }
        if (Date.now() > deadline) return resolve(el);
        requestAnimationFrame(tick);
      };
      tick();
    });
  }

  // ------------------------------------------------------------- copy shape
  // Bodies are markdown-lite, never raw HTML: authored content is escaped
  // first and only **bold**, `code` and paragraph breaks are put back. The
  // author holds the workspace token, but the design system owns the type.

  function body(md) {
    const safe = esc(String(md || ""));
    const inline = safe
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, '<code class="mono">$1</code>');
    return inline.split(/\n{2,}/)
      .map(p => `<p class="tut-p">${p.replace(/\n/g, "<br>")}</p>`).join("");
  }

  // ----------------------------------------------------------------- layers

  let layer = null;      // the whole tutorial DOM while a run is live
  let lastFocus = null;

  function buildLayer() {
    layer = document.createElement("div");
    layer.className = "tut-layer";
    layer.innerHTML = `
      <div class="tut-mask" data-m="top"></div>
      <div class="tut-mask" data-m="right"></div>
      <div class="tut-mask" data-m="bottom"></div>
      <div class="tut-mask" data-m="left"></div>
      <div class="tut-block hidden"></div>
      <div class="tut-mount hidden"></div>
      <div class="tut-pop" role="dialog" aria-modal="true"
           aria-labelledby="tut-pop-title">
        <div class="tut-head">
          <span class="tut-kicker mono"></span>
          <button class="tut-x" type="button" title="End the walkthrough — the studio remembers where you stopped">×</button>
        </div>
        <div class="tut-title" id="tut-pop-title"></div>
        <div class="tut-body"></div>
        <div class="tut-wait mono hidden" aria-live="polite"></div>
        <div class="tut-foot">
          <button class="text-act tut-skip" type="button">Skip walkthrough</button>
          <span class="tut-foot-gap"></span>
          <button class="ghost tut-act hidden" type="button"></button>
          <button class="ghost tut-back" type="button">Back</button>
          <button class="primary tut-next" type="button">Next</button>
        </div>
      </div>`;
    document.body.append(layer);
    layer.querySelector(".tut-x").onclick = () => end("dismissed");
    layer.querySelector(".tut-skip").onclick = () => end("dismissed");
    layer.querySelector(".tut-back").onclick = () => go(running.i - 1);
    layer.querySelector(".tut-next").onclick = () => go(running.i + 1);
    for (const m of layer.querySelectorAll(".tut-mask")) {
      // A click on the dimmed part is a miss, not an exit: leaving must be
      // deliberate, because a half-run walkthrough teaches nothing.
      m.onclick = () => layer.querySelector(".tut-pop").classList.add("tut-nudge");
      m.addEventListener("animationend",
        () => layer.querySelector(".tut-pop").classList.remove("tut-nudge"));
    }
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", place, true);
    window.addEventListener("scroll", place, true);
    // The workbench redraws under the tour constantly; keep the cutout on
    // its target instead of stranding it over whatever moved in. Watched
    // on body, not #main — the band and header re-render too, and they
    // are anchors.
    running.mo = new MutationObserver(() => place());
    running.mo.observe(document.body, { childList: true, subtree: true });
  }

  function onKey(e) {
    if (!running) return;
    if (e.key === "Escape") { e.stopPropagation(); return end("dismissed"); }
    if (e.key === "Tab") trapFocus(e);
    if (e.key === "Enter" && e.target === document.body) {
      const next = layer.querySelector(".tut-next");
      if (!next.disabled) next.click();
    }
  }

  function trapFocus(e) {
    const pop = layer.querySelector(".tut-pop");
    const f = [...pop.querySelectorAll("button:not([disabled]), a[href]")]
      .filter(el => !el.classList.contains("hidden") && el.offsetParent !== null);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  }

  /* Geometry. Four masks rather than a clipped scrim: the cutout stays a
     real hole, so the highlighted control is genuinely clickable unless
     the step blocks it. */
  function place() {
    if (!running || !layer) return;
    const pop = layer.querySelector(".tut-pop");
    const mount = layer.querySelector(".tut-mount");
    const block = layer.querySelector(".tut-block");
    const pop0 = layer.querySelector(".tut-pop");

    /* Loose: no scrim, no cutout, nothing blocked — the page stays fully
       usable and the popover docks out of the way. */
    const goLoose = () => {
      layer.classList.add("tut-loose");
      pop0.classList.add("tut-docked");
      for (const m of layer.querySelectorAll(".tut-mask")) m.style.display = "none";
      mount.classList.add("hidden");
      block.classList.add("hidden");
      pop0.classList.remove("tut-centred");
      pop0.style.left = pop0.style.top = "";
    };

    // `page` (user 2026-08-18): for a step where more than one control is
    // the right one to press, so pointing at any single one would be wrong.
    if (running.step.surface === "page") return goLoose();

    layer.classList.remove("tut-loose");
    pop0.classList.remove("tut-docked");
    for (const m of layer.querySelectorAll(".tut-mask")) m.style.display = "";
    let el = running.step.anchor && !running.centredForResume
      ? anchorEl(running.step.anchor) : null;
    const masks = {};
    for (const m of layer.querySelectorAll(".tut-mask")) masks[m.dataset.m] = m;

    /* An anchor flaps: a view re-renders, its target is detached for a
       frame or two, and a placement that believed the first miss would
       latch the centred fallback for the rest of the step. So a miss on a
       step that HAS an anchor holds the last good geometry and re-checks;
       only a target that stays gone collapses to a centred modal. */
    if (!el && running.step.anchor && !running.centredForResume) {
      running.miss = (running.miss || 0) + 1;
      if (running.lastGood && running.miss < 8) {
        clearTimeout(running.recheck);
        running.recheck = setTimeout(place, 90);
        return;
      }
    } else if (el) {
      running.miss = 0;
      running.lastGood = true;
    }

    if (!el) {
      /* THE TOUR NEVER BLOCKS THE ACTION IT IS WAITING FOR (user,
         2026-08-20: "you started after selecting the AI model, I can't
         continue").

         A step with an `advance` predicate is by definition held until
         the user DOES something on the page. When such a step falls back
         to its centred form — because the anchor is gone, or because
         §5.11 centres a held step that was resumed into — the centred
         form used to draw one mask across the whole viewport. That mask
         has pointer-events, so it swallowed the click.

         The result was a step reading "Upload a PDF, Final Draft,
         Fountain or plain text" while covering the upload button with an
         unclickable scrim. Next still worked, so it was not a hard trap;
         it was worse than a trap, because the tour was refusing the exact
         act it was teaching. A held step therefore goes loose instead. */
      if (running.step.advance) return goLoose();

      // Centred: one mask covers everything, the rest collapse.
      mount.classList.add("hidden");
      block.classList.add("hidden");
      Object.assign(masks.top.style, { inset: "0", height: "auto" });
      for (const k of ["right", "bottom", "left"]) masks[k].style.display = "none";
      pop.classList.add("tut-centred");
      pop.style.left = pop.style.top = "";
      return;
    }
    pop.classList.remove("tut-centred");
    for (const k of ["right", "bottom", "left"]) masks[k].style.display = "";
    const p = 8;   // Q1: the mount's band
    const r = el.getBoundingClientRect();
    const box = { l: r.left - p, t: r.top - p, w: r.width + p * 2, h: r.height + p * 2 };
    const W = window.innerWidth, H = window.innerHeight;
    Object.assign(masks.top.style,
      { inset: "auto", left: "0px", top: "0px", width: W + "px", height: Math.max(0, box.t) + "px" });
    Object.assign(masks.bottom.style,
      { inset: "auto", left: "0px", top: (box.t + box.h) + "px", width: W + "px", height: Math.max(0, H - box.t - box.h) + "px" });
    Object.assign(masks.left.style,
      { inset: "auto", left: "0px", top: box.t + "px", width: Math.max(0, box.l) + "px", height: box.h + "px" });
    Object.assign(masks.right.style,
      { inset: "auto", left: (box.l + box.w) + "px", top: box.t + "px", width: Math.max(0, W - box.l - box.w) + "px", height: box.h + "px" });
    mount.classList.remove("hidden");
    mount.classList.toggle("is-blocked", !!running.step.block);
    Object.assign(mount.style,
      { left: box.l + "px", top: box.t + "px", width: box.w + "px", height: box.h + "px" });
    block.classList.toggle("hidden", !running.step.block);
    Object.assign(block.style,
      { left: box.l + "px", top: box.t + "px", width: box.w + "px", height: box.h + "px" });

    // Popover beside the target, flipped when it would leave the viewport
    // and clamped so it can never render off-screen.
    const pr = pop.getBoundingClientRect();
    const gap = 12;
    let side = running.step.side || "bottom";
    const fits = {
      top: box.t - gap - pr.height > 0,
      bottom: box.t + box.h + gap + pr.height < H,
      left: box.l - gap - pr.width > 0,
      right: box.l + box.w + gap + pr.width < W,
    };
    if (!fits[side]) side = ["bottom", "top", "right", "left"].find(s => fits[s]) || "bottom";
    let left, top;
    if (side === "top" || side === "bottom") {
      top = side === "top" ? box.t - gap - pr.height : box.t + box.h + gap;
      const align = running.step.align || "center";
      left = align === "start" ? box.l
        : align === "end" ? box.l + box.w - pr.width
        : box.l + box.w / 2 - pr.width / 2;
    } else {
      left = side === "left" ? box.l - gap - pr.width : box.l + box.w + gap;
      const align = running.step.align || "center";
      top = align === "start" ? box.t
        : align === "end" ? box.t + box.h - pr.height
        : box.t + box.h / 2 - pr.height / 2;
    }
    pop.style.left = Math.max(12, Math.min(left, W - pr.width - 12)) + "px";
    pop.style.top = Math.max(12, Math.min(top, H - pr.height - 12)) + "px";
    pop.dataset.side = side;
  }

  // -------------------------------------------------------------- the runner

  function navigate(path) {
    if (!path) return;
    const view = applyRoute(path);
    if (!view) return;
    history.pushState(null, "", path);
    showView(view, { push: false });
  }

  async function go(i) {
    if (!running) return;
    const steps = running.doc.steps;
    if (i < 0) return;
    if (i >= steps.length) return end("completed");

    // A step whose work is already done is not shown — an onboarding
    // walkthrough that explains a thing you already did is noise.
    let step = steps[i];
    while (step && step.skip_if && await test(step.skip_if, running.doc, null)) {
      i += 1;
      step = steps[i];
      if (!step) return end("completed");
    }
    // Drop the previous step's advance watcher before the next one takes
    // over, or a long walkthrough ends up with one listener per step.
    if (running.waiting) listeners.delete(running.waiting);
    running.i = i;
    running.step = step;
    running.resumedInto = i === running.resumeAt;
    running.waiting = null;
    running.miss = 0;
    running.lastGood = false;

    if (step.goto) navigate(step.goto);
    let el = null;
    if (step.anchor) {
      el = await waitForAnchor(step.anchor);
      if (!el && step.optional) return go(i + 1);
      if (!el && running.preview) {
        toast(`Step ${i + 1}: anchor "${step.anchor}" is not on screen here — `
              + "shown centred instead.", true);
      }
    }
    // §5.11: a held step resumed into converts to its centred form —
    // same copy, no spotlight, no held Next. One flag, not a new surface.
    if (running.resumedInto && step.advance) {
      el = null;
      running.centredForResume = true;
    } else {
      running.centredForResume = false;
    }
    running.anchorEl = el;
    // Instant, not smooth: a smooth scroll is still moving when the
    // popover is measured, and the placement lands on a rect that no
    // longer exists by the time anyone sees it.
    if (el) el.scrollIntoView({ block: "center", behavior: "auto" });
    render();
    if (!running.preview) {
      record("seen", i).catch(() => {});
    }
  }

  function render() {
    const { doc, step, i } = running;
    const total = doc.steps.length;
    const pop = layer.querySelector(".tut-pop");
    layer.querySelector(".tut-kicker").textContent =
      doc.kind === "announcement" ? "WHAT'S NEW"
        : total > 1 ? `STEP ${i + 1} OF ${total}` : "WALKTHROUGH";
    layer.querySelector(".tut-title").textContent = step.title || doc.title;
    layer.querySelector(".tut-body").innerHTML = body(step.body);
    pop.dataset.kind = doc.kind;

    const act = layer.querySelector(".tut-act");
    act.classList.toggle("hidden", !step.act);
    if (step.act) {
      act.textContent = step.act.label;
      // §4.1: the amber was on the button that DISMISSES. `Show me`
      // performs the act; `Done` closes. Corrected here.
      act.classList.toggle("primary", actPrimary);
      act.classList.toggle("ghost", !actPrimary);
      act.onclick = () => {
        if (step.act.goto) navigate(step.act.goto);
        setTimeout(place, 60);
      };
    }
    layer.querySelector(".tut-back").classList.toggle("hidden", i === 0);
    const next = layer.querySelector(".tut-next");
    next.textContent = i === total - 1 ? "Done" : "Next";
    /* §0/Q2 (ruled 2026-08-18) — A TOUR IS NEVER THE WORK; IT POINTS AT IT.
       On a step whose subject is one of the app's own controls, nothing in
       the tour is amber: the only amber left in the view is the control
       the step is asking for. On a step with no target the tour is all
       there is, and its Next takes the amber it has earned. A ghost Next
       does make the tour's progression feel weightless — which is correct,
       because the tour is not the achievement. */
    const anchored = !!running.anchorEl && step.surface !== "page";
    const actPrimary = doc.kind === "announcement" && !!step.act;
    next.classList.toggle("primary", !anchored && !actPrimary);
    next.classList.toggle("ghost", anchored || actPrimary);
    // "Skip walkthrough" is a lie on a one-step release note — there is no
    // walkthrough to skip, only this to dismiss.
    layer.querySelector(".tut-skip").textContent =
      total > 1 ? "Skip walkthrough" : "Dismiss";

    // A gate is readable as state: when a step waits on the user doing
    // something, Next is visibly held and the condition is stated beside
    // it — never a dead button with no reason.
    const wait = layer.querySelector(".tut-wait");
    // §5.11 (ruled 2026-08-18): a held step LEFT in progress is resumed
    // into on the next boot, so the app opened with a disabled Next and a
    // condition the user already declined once — the app appeared to be
    // waiting rather than offering. It has been shown already; on return
    // it is a reminder, not a gate.
    if (step.advance && !running.resumedInto) {
      // A held step has NO Next (user 2026-08-20). A disabled Next beside
      // the app's own live button read as two competing actions — and the
      // step's condition is the only way forward, so offering a second
      // control at all was the confusion. Skip and Back remain: leaving
      // must always be possible.
      next.classList.add("hidden");
      next.disabled = true;
      wait.classList.remove("hidden");
      wait.textContent = step.wait
        || "WAITING FOR YOU TO DO THIS — THIS STEP MOVES ON BY ITSELF";
      running.waiting = ev => {
        test(step.advance, doc, ev).then(ok => {
          if (ok && running && running.step === step) go(i + 1);
        });
      };
      listeners.add(running.waiting);
    } else {
      next.classList.remove("hidden");
      next.disabled = false;
      next.title = "";
      wait.classList.add("hidden");
      if (step.advance && running.resumedInto) {
        next.classList.remove("ghost");
        next.classList.add("primary");
      }
    }
    place();
    requestAnimationFrame(() => {
      place();
      (next.disabled ? layer.querySelector(".tut-x") : next).focus();
    });
    // A settle window: several views render again as their own fetches
    // land, seconds after navigation. Without this the cutout is correct
    // for one frame and wrong for the rest of the step.
    clearInterval(running.settle);
    let ticks = 0;
    running.settle = setInterval(() => {
      place();
      if (++ticks > 20) clearInterval(running.settle);
    }, 150);
  }

  const record = (status, step) => api("/api/tutorials/state", {
    method: "POST",
    json: { id: running.doc.id, status, step, rev: running.doc.rev || 1 },
  }).then(r => { if (BUNDLE) BUNDLE.state = r.state; });

  async function start(doc, { preview = false, from = 0 } = {}) {
    if (running) end("dismissed");
    lastFocus = document.activeElement;
    running = { doc, i: -1, preview, step: null, anchorEl: null,
                resumeAt: from > 0 ? from : -1 };
    buildLayer();
    document.body.classList.add("tut-open");
    await go(from);
  }

  function end(status) {
    if (!running) return;
    const { doc, i, preview } = running;
    if (running.waiting) listeners.delete(running.waiting);
    if (running.mo) running.mo.disconnect();
    clearInterval(running.settle);
    clearTimeout(running.recheck);
    window.removeEventListener("keydown", onKey, true);
    window.removeEventListener("resize", place, true);
    window.removeEventListener("scroll", place, true);
    layer.remove();
    layer = null;
    document.body.classList.remove("tut-open");
    const done = running;
    running = null;
    if (!preview) {
      api("/api/tutorials/state", {
        method: "POST",
        json: { id: doc.id, status, step: i, rev: doc.rev || 1 },
      }).then(r => { if (BUNDLE) BUNDLE.state = r.state; }).catch(() => {});
    }
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
    return done;
  }

  // ------------------------------------------------------------ eligibility

  function eligible(doc) {
    const row = seenRow(doc.id);
    if (!row) return 0;                                   // never seen
    if ((row.rev || 1) < (doc.rev || 1)) return 0;        // re-issued
    if (row.status === "seen") return row.step || 0;      // resume
    return -1;                                            // done with it
  }

  let considerTimer = 0;
  const considerLater = () => {
    clearTimeout(considerTimer);
    considerTimer = setTimeout(consider, 400);
  };

  /* Highest priority first, one at a time, never over an open dialog. */
  async function consider() {
    if (running || !BUNDLE) return;
    if (document.querySelector(".modal-scrim, .lightbox:not(.hidden), .cropper")) return;
    for (const doc of BUNDLE.tutorials) {
      const from = eligible(doc);
      if (from < 0 || !doc.trigger) continue;
      if (await test(doc.trigger, doc, null)) return start(doc, { from });
    }
  }

  async function load() {
    BUNDLE = await api("/api/tutorials");
    // The anchor map rides the PUBLIC bundle: a customer's studio must
    // resolve anchors too, and these are selectors for the app's own
    // chrome, not anything privileged.
    ANCHORS = {};
    for (const a of (BUNDLE.anchors || [])) ANCHORS[a.name] = a.selector;
  }

  // The public surface: the Tutorials tab and the "replay" acts drive
  // these, and so does the admin editor's Preview.
  window.Tutorials = {
    reload: async () => { await load(); return BUNDLE; },
    bundle: () => BUNDLE,
    anchors: () => ANCHORS,
    run: (id, opts) => {
      const doc = (BUNDLE.tutorials || []).find(t => t.id === id);
      if (!doc) return toast("No such tutorial.", true);
      return start(doc, opts);
    },
    preview: doc => start(doc, { preview: true }),
    stop: () => end("dismissed"),
    consider,
  };

  async function boot() {
    if (booted) return;
    booted = true;
    try { await load(); } catch { return; }
    consider();
  }

  if (document.readyState === "complete") boot();
  else window.addEventListener("load", boot);
})();
