/* The tutorial CMS — Settings → Tutorials, owner installs only.
 *
 * Fetched lazily by app.js the first time the tab is opened, so a
 * customer's studio never downloads it (and its routes 404 there anyway).
 *
 * Everything this editor offers is read from the server's schema:
 * predicate kinds, which contexts each may be used in, the anchor list,
 * the view list, the path list. Nothing about the vocabulary is written
 * twice — add a predicate to content/tutorial_schema.json and it appears
 * in these dropdowns.
 *
 * Validation is the server's. The editor posts and renders whatever comes
 * back, so the rules that decide whether a tutorial is usable live in one
 * place rather than being approximated here and enforced there.
 */
(() => {
  "use strict";

  let HOST = null;
  let DATA = null;      // { tutorials, schema, can_ship, target, version }
  let S = null;         // the schema
  let editing = null;   // a working copy while the editor is open

  const el = (html) => {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  };

  // ------------------------------------------------------------- summaries

  function summarize(pred) {
    if (!pred || typeof pred !== "object") return "—";
    const [k, arg] = Object.entries(pred)[0] || [];
    if (!k) return "—";
    if (k === "all" || k === "any") {
      return `${k}( ${(arg || []).map(summarize).join(" , ")} )`;
    }
    if (k === "not") return `not ${summarize(arg)}`;
    if (arg === true) return k;
    if (typeof arg === "object") {
      return `${k} ${Object.entries(arg).map(([a, b]) => `${a}=${b}`).join(" ")}`;
    }
    return `${k} ${arg}`;
  }

  const stateLine = (row) => {
    if (!row) return "NOT SEEN";
    const at = String(row.updated || "").slice(0, 10);
    return `${String(row.status || "").toUpperCase()} · REV ${row.rev || 1}`
      + (at ? `<br>${at}` : "");
  };

  // ------------------------------------------------------------- the list

  /* Transliterated from `Tutorial System.dc.html` turn 2a. A grid, not a
     table: the board's eight tracks, hairline rows, and every value at the
     tier the board states. Acts are all --ink — canon's destructive
     grammar is `button.danger` once, where its object reads in full, not
     --bad repeated down a column. */
  const COLS = "112px minmax(220px, 1.6fr) 96px 110px 56px 92px 148px 168px";

  function list() {
    const rows = DATA.tutorials;
    // C7: two lives. On a checkout the path is the useful half — it is
    // the file you are about to commit. On a cloud studio the ceiling is,
    // and the filename helps nobody.
    const where = DATA.can_ship
      ? `SAVING WRITES <b>app/content/tutorials</b> — COMMIT AND PUSH AND
         EVERY STUDIO GETS IT ON ITS NEXT UPDATE`
      : "SAVING WRITES THIS STUDIO ONLY — NOTHING HERE CAN REACH THE FLEET";
    HOST.innerHTML = "";
    const panel = el(`
      <div class="panel">
        <div class="fact-head">TUTORIALS &mdash; AUTHORED ONBOARDING</div>
        <h1 class="lib-title">What the studio teaches</h1>
        <p class="lib-intro">A tutorial is content, not code: a trigger, and
        steps that point at real controls. Use them for a first-run
        walkthrough, or to announce a feature to every studio the release
        reaches.</p>
        <p class="tut-adm-where mono">${where}</p>
        <div class="tut-adm-grid-list" style="--tut-cols:${COLS}">
          <div class="tut-adm-head">
            <span>ID</span><span>TITLE</span><span>KIND</span><span>TRIGGER</span>
            <span>REV</span><span>SOURCE</span><span>THIS INSTALL</span><span></span>
          </div>
        </div>
        <div class="row" style="margin-top:14px;gap:10px;align-items:center">
          <button class="primary" data-a="new">+ New tutorial</button>
          <button class="ghost" data-a="reset-all">Forget every tutorial on this install</button>
          <span class="mini">Forgetting is how you test a first-run walkthrough twice.</span>
        </div>
      </div>`);
    const grid = panel.querySelector(".tut-adm-grid-list");
    if (!rows.length) {
      // Q11: the heads stay — the CMS's shape is information.
      grid.append(el(`<div class="tut-adm-empty">no tutorials on this install
        <span class="mono">SHIPPED TUTORIALS RETURN ON THE NEXT UPDATE — DELETING
        ONE HERE ONLY REMOVES IT FROM THIS COPY</span></div>`));
    }
    for (const t of rows) {
      const errs = t.errors || [];
      const row = el(`
        <div class="tut-adm-row${errs.length ? " tut-adm-bad" : ""}">
          <span class="tut-adm-id mono">${esc(t.id)}</span>
          <span class="tut-adm-title">${esc(t.title || "")}
            ${t.enabled === false ? '<span class="wv-tag mono">OFF</span>' : ""}
            ${errs.length ? `<span class="tut-adm-err mono">${esc(errs[0])}${
              errs.length > 1 ? ` (+${errs.length - 1})` : ""}</span>` : ""}</span>
          <span class="mono tut-adm-dim">${esc(String(t.kind || "").toUpperCase())} · ${
            (t.steps || []).length} STEPS</span>
          <span class="mono tut-adm-faint tut-adm-trig"
                title="${esc(plainly(t.trigger) || summarize(t.trigger))}">${
            esc(summarize(t.trigger))}</span>
          <span class="mono tut-adm-dim">${t.rev || 1}</span>
          <span class="mono tut-adm-dim">${t.source === "packaged" ? "SHIPPED" : "THIS STUDIO"}</span>
          <span class="mono tut-adm-dim">${stateLine(t.state)}</span>
          <span class="tut-adm-acts mono">
            <button class="text-act" data-a="edit">Edit</button>
            <button class="text-act" data-a="preview">Preview</button>
            <button class="text-act" data-a="dup">Duplicate</button>
            <button class="text-act" data-a="forget">Forget</button>
            <button class="text-act" data-a="del">Delete</button>
          </span>
        </div>`);
      row.querySelectorAll("[data-a]").forEach(b => {
        b.onclick = () => rowAct(b.dataset.a, t);
      });
      grid.append(row);
    }
    panel.querySelector('[data-a="new"]').onclick = () => open(blank());
    panel.querySelector('[data-a="reset-all"]').onclick = async () => {
      if (!await askConfirm("Forget every tutorial?",
        "This install will behave as though it has never seen any of them — "
        + "first-run walkthroughs run again from the beginning. Content is "
        + "untouched.", "Forget all")) return;
      await api("/api/tutorials/state/reset", { method: "POST", json: {} });
      toast("Seen-state cleared for this install.");
      refresh();
    };
    HOST.append(panel);
  }

  async function rowAct(act, t) {
    if (act === "edit") return open(JSON.parse(JSON.stringify(t)));
    if (act === "preview") {
      if ((t.errors || []).length) {
        return toast("This tutorial does not validate — fix it before previewing.", true);
      }
      return window.Tutorials.preview(t);
    }
    if (act === "dup") {
      const copy = JSON.parse(JSON.stringify(t));
      copy.id = `${t.id}-copy`;
      copy.title = `${t.title} (copy)`;
      copy.enabled = false;
      delete copy.source; delete copy.state; delete copy.errors;
      delete copy.overrides_packaged; delete copy.updated;
      return open(copy);
    }
    if (act === "forget") {
      await api("/api/tutorials/state/reset", { method: "POST", json: { id: t.id } });
      toast(`"${t.title}" will run again on this install.`);
      return refresh();
    }
    if (act === "del") {
      const shipped = t.source === "packaged";
      if (!await askConfirm(`Delete ${t.id}?`,
        shipped && DATA.can_ship
          ? "This removes the shipped file from the repo. Studios keep their "
            + "copy until the deletion is committed and pushed."
          : "This studio stops showing it. Nothing else is affected.",
        "Delete", true)) return;
      await api(`/api/tutorials/admin/${encodeURIComponent(t.id)}`, { method: "DELETE" });
      toast("Deleted.");
      return refresh();
    }
  }

  // C10 (ruled 2026-08-18): not all-blank. It opens with the one surface
  // that cannot fail to resolve, so an author learns the step card by
  // editing one rather than pressing + Step to find out what it is.
  const blank = () => ({
    id: "", rev: 1, kind: "flow", title: "", note: "", enabled: false,
    priority: 50, replayable: true, trigger: null,
    steps: [{ surface: "modal", title: "", body: "" }],
  });

  // ----------------------------------------------------- predicate builder
  // Every control here is generated from the schema's declaration of the
  // predicate — including which kinds a context will even accept, so an
  // advance condition that could never fire is not offered in the first
  // place rather than refused on save.

  function kindsFor(ctx) {
    return Object.entries(S.predicates)
      .filter(([, d]) => d.use.includes(ctx))
      .map(([k, d]) => ({ k, label: d.label, hint: d.hint, arg: d.arg }));
  }

  /* C12 (TUTORIAL_RULING §5.10, ruled 2026-08-18): the JSON textarea is
     REFUSED. The CMS exists so an author never writes JSON, and a builder
     that surrenders to a textarea the moment all/any/not appears
     surrenders exactly where the help was needed — the shipped FTUE
     trigger IS composite, so the common case was the one that dropped
     out. The composite nests, capped at two levels: a third level means
     the trigger wants to be two tutorials. */
  const MAX_NEST = 2;

  function predWidget(ctx, value, depth = 0) {
    const kinds = kindsFor(ctx)
      .filter(k => depth < MAX_NEST || !["all", "any", "not"].includes(k.k));
    const cur = value && typeof value === "object"
      ? Object.entries(value)[0] : [null, null];
    const wrap = el(`
      <div class="tut-adm-pred" data-ctx="${ctx}" data-depth="${depth}">
        <select class="tut-adm-pk">
          <option value="">— no condition —</option>
          ${kinds.map(k => `<option value="${esc(k.k)}">${esc(k.label)}</option>`).join("")}
        </select>
        <div class="tut-adm-parg"></div>
        <div class="tut-adm-nest"></div>
        <div class="mini tut-adm-hint"></div>
      </div>`);
    const sel = wrap.querySelector(".tut-adm-pk");
    sel.value = cur[0] || "";
    const nest = wrap.querySelector(".tut-adm-nest");
    const paint = () => {
      const k = sel.value;
      const decl = k ? S.predicates[k] : null;
      const same = sel.value === (cur[0] || "");
      wrap.querySelector(".tut-adm-hint").textContent = decl ? decl.hint : "";
      nest.innerHTML = "";
      const composite = decl && (decl.arg === "list" || decl.arg === "predicate");
      wrap.querySelector(".tut-adm-parg").innerHTML =
        composite ? "" : argHtml(decl && decl.arg, same ? cur[1] : undefined);
      if (!composite) return;
      if (decl.arg === "predicate") {
        nest.append(predWidget(ctx, same ? cur[1] : null, depth + 1));
        return;
      }
      const kids = (same && Array.isArray(cur[1]) ? cur[1] : [null, null]);
      // The board numbers the nested rows — a composite you can point at
      // is a composite you can talk about.
      const renumber = () => [...nest.querySelectorAll(":scope > .tut-adm-pred")]
        .forEach((row, n) => {
          let tag = row.querySelector(":scope > .tut-adm-n");
          if (!tag) {
            tag = document.createElement("span");
            tag.className = "tut-adm-n mono";
            row.prepend(tag);
          }
          tag.textContent = String(n + 1).padStart(2, "0");
        });
      const addRow = v => {
        nest.insertBefore(predWidget(ctx, v, depth + 1), nest.lastElementChild);
        renumber();
      };
      nest.append(el(`<button type="button" class="text-act tut-adm-addcond">+ condition</button>`));
      kids.forEach(addRow);
      nest.lastElementChild.onclick = () => addRow(null);
      renumber();
    };
    sel.onchange = paint;
    paint();
    return wrap;
  }

  function argHtml(arg, v) {
    const opts = (pairs, sel) => pairs.map(([val, label]) =>
      `<option value="${esc(val)}"${val === sel ? " selected" : ""}>${esc(label)}</option>`).join("");
    switch (arg) {
      case undefined:
      case null:
        return "";
      case "none":
        return '<span class="mini mono">NO ARGUMENT</span>';
      case "string":
      case "path":
        return `<input type="text" data-arg="scalar" value="${esc(v == null ? "" : v)}"
                 placeholder="${arg === "path" ? "stage_summary.screenplay" : "2026.08.05.83"}">`;
      case "view":
        return `<select data-arg="scalar">${opts(
          S.views.map(x => [x, S.view_labels[x] || x]), v)}</select>`;
      case "anchor":
        return `<select data-arg="scalar">${opts(
          S.anchors.map(a => [a.name, `${a.name} — ${a.label}`]), v)}</select>`;
      case "tutorial":
        return `<select data-arg="scalar">${opts(
          DATA.tutorials.map(t => [t.id, `${t.id} — ${t.title}`]), v)}</select>`;
      case "api": {
        const o = v || {};
        return `<select data-arg="method">${opts(
          [["POST", "POST"], ["PUT", "PUT"], ["DELETE", "DELETE"], ["GET", "GET"]],
          o.method || "POST")}</select>
          <input type="text" data-arg="apipath" placeholder="^/api/screenplay"
                 value="${esc(o.path || "")}">`;
      }
      case "path_value": {
        const o = v || {};
        return `<input type="text" data-arg="pvpath" placeholder="stage_summary.breakdowns.locked"
                  value="${esc(o.path || "")}">
          <input type="text" data-arg="pvvalue" placeholder="value as JSON — true, 3, &quot;x&quot;"
                  value="${esc(o.value === undefined ? "" : JSON.stringify(o.value))}">`;
      }
      default:  // list / predicate — drawn as nested rows, never as JSON
        return "";
    }
  }

  function readPred(wrap) {
    const k = wrap.querySelector(".tut-adm-pk").value;
    if (!k) return null;
    const decl = S.predicates[k];
    const q = s => wrap.querySelector(`[data-arg="${s}"]`);
    switch (decl.arg) {
      case "none": return { [k]: true };
      case "api": return { [k]: { method: q("method").value, path: q("apipath").value.trim() } };
      case "path_value": {
        let val = q("pvvalue").value.trim();
        try { val = JSON.parse(val); } catch { /* a bare string is fine */ }
        return { [k]: { path: q("pvpath").value.trim(), value: val } };
      }
      case "predicate": {
        const kid = wrap.querySelector(".tut-adm-nest > .tut-adm-pred");
        const v = kid && readPred(kid);
        return v ? { [k]: v } : null;
      }
      case "list": {
        const kids = [...wrap.querySelectorAll(":scope > .tut-adm-nest > .tut-adm-pred")]
          .map(readPred).filter(Boolean);
        return kids.length ? { [k]: kids } : null;
      }
      default: {
        const v = q("scalar").value.trim();
        return v ? { [k]: v } : null;
      }
    }
  }

  // ------------------------------------------------------------ the editor

  /* A plain-English restatement of the trigger, which the board carries
     under the builder: a condition you can read back is a condition you
     can check. Falls back to the terse summary for anything it cannot
     phrase — never to silence. */
  function plainly(pred) {
    const say = p => {
      if (!p || typeof p !== "object") return "";
      const [k, arg] = Object.entries(p)[0] || [];
      if (k === "all") return (arg || []).map(say).filter(Boolean).join(" AND ");
      if (k === "any") return (arg || []).map(say).filter(Boolean).join(" OR ");
      if (k === "not") {
        const inner = Object.entries(arg || {})[0] || [];
        if (inner[0] === "first_run") return "A PRODUCTION EXISTS";
        if (inner[0] === "state") return `${String(inner[1]).toUpperCase()} IS NOT SET`;
        return `NOT ${say(arg)}`;
      }
      if (k === "first_run") return "NO PRODUCTION EXISTS YET";
      if (k === "state") return `${String(arg).toUpperCase()} IS SET`;
      if (k === "version_changed") return "THE STUDIO UPDATED SINCE IT WAS LAST SEEN";
      if (k === "version_at_least") return `THE STUDIO IS AT OR PAST ${arg}`;
      if (k === "seen") return `${String(arg).toUpperCase()} IS FINISHED`;
      if (k === "not_seen") return `${String(arg).toUpperCase()} IS NOT FINISHED`;
      if (k === "view") return `THE USER IS ON ${String(arg).toUpperCase()}`;
      return "";
    };
    const t = say(pred);
    return t ? `RUNS WHEN ${t}` : (pred ? `RUNS WHEN ${summarize(pred)}` : "");
  }

  function open(doc) {
    editing = doc;
    HOST.innerHTML = "";
    const isNew = !DATA.tutorials.some(t => t.id === doc.id);
    const panel = el(`
      <div class="panel tut-adm-editor">
        <button class="text-act tut-adm-back" data-a="back">&larr; All tutorials</button>
        <div class="tut-adm-edhead mono">
          <span class="tut-adm-faint">EDITING — ${esc(doc.id || "new tutorial")}</span>
          <span class="tut-adm-dim">REV ${Number(doc.rev || 1)} · ${
            isNew ? "NOT YET SAVED" : (doc.source === "packaged" ? "SHIPPED" : "THIS STUDIO")
          } · ${(doc.steps || []).length} STEPS</span>
        </div>

        <div class="tut-adm-fields">
          <label><span class="fl mono">ID</span>
            <input type="text" class="mono" data-f="id" value="${esc(doc.id)}">
            <span class="fn mono">THE FILENAME, AND THE KEY SEEN-STATE IS STORED UNDER</span></label>
          <label><span class="fl mono">KIND</span>
            <select data-f="kind">${Object.entries(S.kinds).map(([k]) =>
              `<option value="${esc(k)}"${k === doc.kind ? " selected" : ""}>${esc(k.toUpperCase())}</option>`).join("")}</select></label>
          <label><span class="fl mono">REV</span>
            <input type="text" class="mono" data-f="rev" value="${Number(doc.rev || 1)}">
            <span class="fn mono">RAISING IT RE-SHOWS TO EVERYONE</span></label>
          <label><span class="fl mono">PRIORITY</span>
            <input type="text" class="mono" data-f="priority" value="${Number(doc.priority || 0)}">
            <span class="fn mono">HIGHER RUNS FIRST</span></label>
          <label class="wide"><span class="fl mono">TITLE</span>
            <input type="text" data-f="title" value="${esc(doc.title || "")}">
            <span class="fn mono">THE LIST, AND A STEP'S HEADING WHEN IT HAS NONE</span></label>
          <label class="wide"><span class="fl mono">NOTE TO YOURSELF</span>
            <textarea data-f="note" rows="2">${esc(doc.note || "")}</textarea>
            <span class="fn mono">NEVER SHOWN TO A USER</span></label>
        </div>

        <div class="row tut-adm-flags">
          <label class="row"><input type="checkbox" data-f="enabled"${doc.enabled !== false ? " checked" : ""}>
            <span class="mono">LIVE — THE STUDIO MAY RUN THIS</span></label>
          <label class="row"><input type="checkbox" data-f="replayable"${doc.replayable !== false ? " checked" : ""}>
            <span class="mono">REPLAYABLE — A USER MAY RUN IT AGAIN</span></label>
        </div>

        <div class="tut-adm-sect" data-p="trigger">
          <span class="fl mono">WHEN IT RUNS BY ITSELF</span>
        </div>
        <p class="tut-adm-plain mono" data-f="plain">${esc(plainly(doc.trigger))}</p>

        <div class="tut-adm-sect">
          <span class="fl mono">STEPS · ${(doc.steps || []).length}</span>
        </div>
        <div class="tut-adm-steps"></div>
        <button class="ghost" data-a="addstep">+ Step</button>

        <div class="tut-adm-errors hidden"></div>
        <div class="modal-actions tut-adm-foot">
          <button class="text-act" data-a="cancel">Cancel</button>
          <button class="ghost" data-a="preview">Preview it now</button>
          <button class="primary" data-a="save">Save</button>
        </div>
      </div>`);
    panel.querySelector('[data-p="trigger"]').append(predWidget("trigger", doc.trigger));
    HOST.append(panel);
    paintSteps();
    // the restatement follows the builder
    panel.addEventListener("change", () => {
      try {
        const el2 = panel.querySelector("[data-f=plain]");
        if (el2) el2.textContent = plainly(readPred(
          panel.querySelector('[data-p="trigger"] .tut-adm-pred')));
      } catch { /* mid-edit; the summary catches up on the next change */ }
    });
    panel.querySelector('[data-a="back"]').onclick = () => refresh();
    panel.querySelector('[data-a="cancel"]').onclick = () => refresh();
    panel.querySelector('[data-a="addstep"]').onclick = () => {
      editing = collect(true);
      editing.steps.push({ surface: "modal", title: "", body: "" });
      open(editing);
    };
    panel.querySelector('[data-a="preview"]').onclick = () => {
      let doc2;
      try { doc2 = collect(); } catch (err) { return toast(err.message, true); }
      if (!doc2.steps.length) return toast("Nothing to preview — add a step.", true);
      window.Tutorials.preview(doc2);
    };
    panel.querySelector('[data-a="save"]').onclick = save;
  }

  function paintSteps() {
    const host = HOST.querySelector(".tut-adm-steps");
    host.innerHTML = "";
    editing.steps.forEach((st, i) => host.append(stepCard(st, i)));
  }

  function stepCard(st, i) {
    const opt = (pairs, sel) => pairs.map(([v, l]) =>
      `<option value="${esc(v)}"${v === sel ? " selected" : ""}>${esc(l)}</option>`).join("");
    const surface = st.surface || "modal";
    const held = st.advance ? " · HELD" : "";
    const card = el(`
      <div class="tut-adm-step" data-i="${i}">
        <div class="tut-adm-step-head mono">
          <span class="tut-adm-ink">STEP ${String(i + 1).padStart(2, "0")}</span>
          <span class="tut-adm-faint">${esc(surface.toUpperCase())}${held}</span>
          <span class="tut-adm-gap"></span>
          <span class="tut-adm-step-acts">
            <button data-s="up" ${i === 0 ? "disabled" : ""} title="Move up">&uarr;</button>
            <button data-s="down" ${i === editing.steps.length - 1 ? "disabled" : ""} title="Move down">&darr;</button>
            <button data-s="dup">Duplicate</button>
            <button data-s="del">Remove</button>
          </span>
        </div>
        <div class="tut-adm-fields tut-adm-step-grid">
          <label><span class="fl mono">SURFACE</span>
            <select data-sf="surface">${opt(Object.entries(S.surfaces)
              .map(([k, d]) => [k, `${k.toUpperCase()} — ${d.split(".")[0]}`]), surface)}</select></label>
          <label><span class="fl mono">ANCHOR</span>
            <select data-sf="anchor">${opt(
              [["", "— NONE (CENTRED) —"]].concat(S.anchors.map(a => [a.name, a.name])),
              st.anchor || "")}</select>
            <span class="fn mono">A NAME, NEVER A SELECTOR</span></label>
          <label><span class="fl mono">SIDE · ALIGN</span>
            <span class="tut-adm-pair">
              <select data-sf="side">${opt([["", "AUTO"]].concat(S.sides.map(x => [x, x.toUpperCase()])), st.side || "")}</select>
              <select data-sf="align">${opt([["", "AUTO"]].concat(S.aligns.map(x => [x, x.toUpperCase()])), st.align || "")}</select>
            </span>
            <span class="fn mono">FLIPPED IF IT WILL NOT FIT</span></label>
          <label><span class="fl mono">GO TO FIRST</span>
            <select data-sf="goto">${opt([["", "— STAY WHERE THE USER IS —"]].concat(
              Object.entries(S.paths).map(([pth]) => [pth, pth])), st.goto || "")}</select></label>
        </div>
        <div class="tut-adm-stack">
          <label><span class="fl mono">TITLE</span>
            <input type="text" data-sf="title" value="${esc(st.title || "")}"></label>
          <label><span class="fl mono">BODY</span>
            <textarea data-sf="body" rows="4">${esc(st.body || "")}</textarea>
            <span class="fn mono">PLAIN TEXT · <b>**BOLD**</b> AND <b>\`CODE\`</b> ONLY ·
              A BLANK LINE STARTS A PARAGRAPH · NO MARKUP</span></label>
          <div class="fgroup tut-adm-sub" data-p="advance">
            <span class="fl mono">HELD UNTIL</span>
            <span class="fn mono">WHILE HELD THERE IS NO NEXT — THE STEP'S OWN CONDITION IS THE WAY ON</span>
          </div>
          <label><span class="fl mono">AND THE LINE READS</span>
            <input type="text" class="mono" data-sf="wait" value="${esc(st.wait || "")}"
                   placeholder="UPLOAD THE SCREENPLAY AND THIS STEP MOVES ON"></label>
          <div class="tut-adm-fields" style="margin:0">
            <label><span class="fl mono">ACT BUTTON</span>
              <input type="text" data-sf="actlabel" value="${esc((st.act && st.act.label) || "")}"
                     placeholder="Show me">
              <span class="fn mono">OPTIONAL — A SECOND VERB ON THE STEP</span></label>
            <label><span class="fl mono">AND IT GOES TO</span>
              <select data-sf="actgoto">${opt([["", "— NO NAVIGATION —"]].concat(
                Object.entries(S.paths).map(([pth]) => [pth, pth])),
                (st.act && st.act.goto) || "")}</select></label>
          </div>
          <div class="fgroup tut-adm-sub" data-p="skip_if">
            <span class="fl mono">SKIP THIS STEP IF</span>
            <span class="fn mono">A STEP THAT EXPLAINS SOMETHING ALREADY DONE IS NOISE</span>
          </div>
          <div class="row tut-adm-flags">
            <label class="row"><input type="checkbox" data-sf="clickable"${st.block ? "" : " checked"}>
              <span class="mono">KEEP THE CONTROL CLICKABLE</span></label>
            <label class="row"><input type="checkbox" data-sf="optional"${st.optional ? " checked" : ""}>
              <span class="mono">SKIP IF ITS ANCHOR IS OFF SCREEN</span></label>
          </div>
        </div>
      </div>`);
    card.querySelector('[data-p="skip_if"]').append(predWidget("skip_if", st.skip_if));
    card.querySelector('[data-p="advance"]').append(predWidget("advance", st.advance));
    card.querySelectorAll("[data-s]").forEach(b => {
      b.onclick = () => {
        const doc = collect(true);
        const steps = doc.steps;
        const s2 = b.dataset.s;
        if (s2 === "up" && i > 0) [steps[i - 1], steps[i]] = [steps[i], steps[i - 1]];
        if (s2 === "down" && i < steps.length - 1) [steps[i], steps[i + 1]] = [steps[i + 1], steps[i]];
        if (s2 === "dup") steps.splice(i + 1, 0, JSON.parse(JSON.stringify(steps[i])));
        if (s2 === "del") steps.splice(i, 1);
        editing = doc;
        open(editing);
      };
    });
    return card;
  }

  /* Read the form back into a document. `lenient` is for the reorder acts,
     which must not lose a half-written step to a JSON typo. */
  function collect(lenient = false) {
    const root = HOST.querySelector(".tut-adm-editor");
    // Name the field that is missing. A bare null reaching .value or
    // .querySelector surfaced as "Cannot read properties of null" in the
    // save-refusal panel — a message about the editor's own wiring, shown
    // to an author as though their tutorial were at fault (2026-08-20).
    const need = (host, sel, what) => {
      const el2 = host && host.querySelector(sel);
      if (!el2) throw new Error(`the editor is missing its ${what} field — `
        + "this is a bug in the editor, not in your tutorial");
      return el2;
    };
    const f = n => need(root, `[data-f="${n}"]`, n);
    const doc = {
      id: f("id").value.trim().toLowerCase(),
      title: f("title").value.trim(),
      note: f("note").value.trim(),
      kind: f("kind").value,
      priority: parseInt(f("priority").value, 10) || 0,
      rev: parseInt(f("rev").value, 10) || 1,
      enabled: f("enabled").checked,
      replayable: f("replayable").checked,
      trigger: null,
      steps: [],
    };
    const readSafe = (w) => {
      try { return readPred(w); }
      catch (err) { if (lenient) return null; throw err; }
    };
    doc.trigger = readSafe(root.querySelector('[data-p="trigger"] .tut-adm-pred'));
    for (const card of root.querySelectorAll(".tut-adm-step")) {
      const g = n => need(card, `[data-sf="${n}"]`, n);
      // Start from what was loaded, not from nothing: a field this editor
      // does not render (a step id, anything added later) must survive an
      // edit. A CMS that quietly drops what it cannot show is worse than
      // one that refuses to open the document.
      const was = editing.steps[Number(card.dataset.i)] || {};
      const st = { ...was };
      for (const k of ["anchor", "side", "align", "goto", "wait", "block",
                       "optional", "act", "skip_if", "advance"]) delete st[k];
      st.surface = g("surface").value;
      st.title = g("title").value.trim();
      st.body = g("body").value;
      const put = (k, v) => { if (v) st[k] = v; };
      put("anchor", g("anchor").value);
      put("side", g("side").value);
      put("align", g("align").value);
      put("goto", g("goto").value);
      put("wait", g("wait").value.trim());
      // The board labels this by its EFFECT — checked means the control
      // stays live — so it is the inverse of the stored `block`. Read and
      // write both invert; the flag itself never flips meaning.
      if (!g("clickable").checked) st.block = true;
      if (g("optional").checked) st.optional = true;
      const label = g("actlabel").value.trim();
      if (label) {
        st.act = { label };
        if (g("actgoto").value) st.act.goto = g("actgoto").value;
      }
      const skip = readSafe(card.querySelector('[data-p="skip_if"] .tut-adm-pred'));
      if (skip) st.skip_if = skip;
      const adv = readSafe(card.querySelector('[data-p="advance"] .tut-adm-pred'));
      if (adv) st.advance = adv;
      doc.steps.push(st);
    }
    return doc;
  }

  async function save() {
    let doc;
    try { doc = collect(); } catch (err) { return showErrors([err.message]); }
    if (!doc.id) return showErrors(["Give it an id — it is the filename."]);
    try {
      await api(`/api/tutorials/admin/${encodeURIComponent(doc.id)}`,
                { method: "PUT", json: doc });
    } catch (err) {
      return showErrors(String(err.message).split("; "));
    }
    toast(DATA.can_ship
      ? "Saved to the shipped copy — commit and push to send it to every studio."
      : "Saved to this studio.");
    await window.Tutorials.reload();
    refresh();
  }

  function showErrors(lines) {
    const box = HOST.querySelector(".tut-adm-errors");
    if (!box) return toast(lines[0], true);
    box.classList.remove("hidden");
    // C13 (board turn 2a): every reason at once is right — keep it. Each
    // names the step it is about and clicking it scrolls there: a list of
    // faults with no addresses is a second search.
    const row = l => {
      const m = /^step (\d+)(?:\s*[-—:]\s*|\s+)?/i.exec(l);
      const addr = m ? `STEP ${String(+m[1]).padStart(2, "0")}`
        : /^id\b/i.test(l) ? "ID" : "";
      const rest = m ? l.slice(m[0].length) : l;
      const inner = `<span class="tut-adm-faint">${esc(addr || "—")}</span>`
        + ` <span class="tut-adm-ink">${esc(rest)}</span>`;
      return m
        ? `<button type="button" class="tut-adm-ereason mono" data-step="${+m[1] - 1}">${inner}</button>`
        : `<span class="tut-adm-ereason mono">${inner}</span>`;
    };
    box.innerHTML = `<span class="tut-adm-ehead mono">${lines.length} REASON${
      lines.length === 1 ? "" : "S"} THIS CANNOT SAVE</span>` + lines.map(row).join("");
    box.querySelectorAll("[data-step]").forEach(b => b.onclick = () =>
      HOST.querySelectorAll(".tut-adm-step")[+b.dataset.step]
        ?.scrollIntoView({ block: "center", behavior: "smooth" }));
    box.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  async function refresh() {
    DATA = await api("/api/tutorials/admin");
    S = DATA.schema;
    editing = null;
    list();
  }

  window.TutorialAdmin = {
    render: async (host) => {
      HOST = host;
      host.innerHTML = '<p class="mini">reading tutorials…</p>';
      try { await refresh(); }
      catch (err) { host.innerHTML = `<p class="mini">${esc(err.message)}</p>`; }
    },
  };
})();
