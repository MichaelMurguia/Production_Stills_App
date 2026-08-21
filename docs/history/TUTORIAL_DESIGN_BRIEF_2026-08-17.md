> **ANSWERED AND IMPLEMENTED — 2026-08-18. Not binding; do not build from
> this file.** Claude Design ruled all eleven questions
> (`TUTORIAL_RULING_PLAN`, retired) and the rulings shipped, so the
> descriptions below are of the tour layer as it was BEFORE the ruling.
> Most notably: the amber ring described throughout was **refused** — the
> target is matted, not lit — the dim moved to `--ground`, the popover's
> foot decides its own amber, a third `page` surface exists, and the
> walkthrough starts on Settings and is four steps. Kept because it
> records what was asked and why.
>
> Current truth: `docs/TUTORIALS.md` (the system), `docs/FIRST_RUN.md`
> (the flow), `app/static/DESIGN_SYSTEM.md` (the look).

# TUTORIAL_DESIGN_BRIEF.md — for Claude Design: the tutorial layer

**From the implementer, 2026-08-17.** A tutorial system landed today:
authored onboarding that runs against the live app. The mechanism is built,
tested and green. **The look is not designed** — it is structure assembled
from existing tokens so that something correct exists to rule on, and it is
logged as one row in `app/static/DESIGN_SYSTEM.md` → `## Uncanonized
patterns`.

This brief is the full spec: what the system is, every surface and state,
the exact values I shipped, what is mechanism (not yours), and the eleven
questions that are.

> **Read `docs/TUTORIALS.md` first if you want the system's own reference.**
> This file is the design half; that one is the engineering half.

---

## 1. What it is, in one page

A tutorial is a **JSON document**, not code — a trigger and a list of steps.
Two kinds ship:

- **`flow`** — a guided sequence. The first-run walkthrough is one: five
  steps, ending by handing the user the real upload control and waiting for
  them to use it.
- **`announcement`** — a release note, usually one step, shown once per
  revision. "Here is what changed, and here is the control it changed."

Steps render on one of two **surfaces**:

- **`spotlight`** — the anchored form. Four masks dim everything except the
  target, leaving a genuine hole (the highlighted control stays clickable),
  a ring marks it, and a popover sits on a named side.
- **`modal`** — the same popover, centred, no cutout. For openings,
  closings, and anything about the product rather than about one control.

Authoring happens in **Settings → Tutorials**, which exists only on owner
installs. Customers get the runtime, never the CMS.

**The one fact that shapes the design:** the copy is *authored*, later,
by someone who is not you. A step's body can be one line or six
paragraphs; a heading can be three words or fifteen. Whatever you rule has
to hold for content that does not exist yet.

---

## 2. Seeing it

Four captures are in `design_mocks/`, all at the 1420 design width:

| File | Shows |
|---|---|
| `tutorial-modal-2026-08-17.png` | Flow, step 1 of 5, centred modal over the Status view |
| `tutorial-spotlight-2026-08-17.png` | Flow, step 4 of 5 — spotlight on the DO-THIS-NEXT card, held gate, waiting line |
| `tutorial-announcement-2026-08-17.png` | Announcement — WHAT'S NEW, spotlight on the Settings tab, act button |
| `tutorial-cms-2026-08-17.png` | The CMS list |

**To drive it yourself** (nothing is billed; no keys needed):

```bash
SCREENBOARD_DEBUG_TOOLS=1 SCREENBOARD_HOME=/tmp/tut python -m uvicorn app.main:app --port 8733
curl -X POST localhost:8733/api/projects -H "Content-Type: application/json" -d '{"name":"Demo"}'
```

Open `http://127.0.0.1:8733/`. The FTUE fires by itself (its trigger is "this
production has no screenplay"). Then:

- **Any step on demand** — `Tutorials.run("first-board")` in the console, or
  Settings → Tutorials → **Preview** on any row.
- **A specific step** — `POST /api/tutorials/state {id, status:"seen", step:N}`
  and reload; the flow resumes at step N.
- **Again from the top** — Settings → Tutorials → **Forget**.
- **A shape that does not exist yet** — write it in the editor and hit
  Preview. Preview records nothing, and runs unsaved edits.

---

## 3. The state matrix — every state, all of them yours

### 3.1 The tour popover

| # | State | How it differs today | Reach it |
|---|---|---|---|
| S1 | Flow, first step | No **Back**. Kicker `STEP 1 OF 5` | FTUE step 1 |
| S2 | Flow, middle step | Back + Next | step 2 |
| S3 | Flow, last step | Next reads **Done** | step 5 |
| S4 | Single-step flow | Kicker reads `WALKTHROUGH`; skip reads **Dismiss** | author one |
| S5 | Announcement | Kicker reads `WHAT'S NEW`; otherwise identical | the example row |
| S6 | Held gate | **Next disabled**, waiting line above the foot stating the condition | FTUE step 4 |
| S7 | With an act button | A ghost button between skip and Back (`Open AI & engines`) | FTUE step 3 |
| S8 | Centred (modal surface) | No cutout, no ring; one mask covers all | FTUE steps 1 and 5 |
| S9 | Anchor missing | Silently becomes S8. In Preview it also toasts | point a step at `screenplay.upload` with no draft |
| S10 | Blocked target | Target dimmed-through but not clickable | set `block` on a step |
| S11 | Scrim clicked | Popover nudges 3px twice; nothing else happens | click the dim |
| S12 | Side flipped | Requested side does not fit → first side that does | shrink the window |

Also true of every state, and worth your attention because a screenshot
cannot show it: the popover is `max-height: 80vh` with its own scroll, so a
long authored body scrolls **inside** the popover.

### 3.2 The CMS (Settings → Tutorials)

| # | State | Notes |
|---|---|---|
| C1 | List, populated | Nine columns; two rows ship |
| C2 | Row, shipped | Source reads `SHIPPED` |
| C3 | Row, studio-authored | Source reads `THIS STUDIO` |
| C4 | Row, disabled | An `OFF` chip (`.wv-tag`) beside the title |
| C5 | Row, invalid | Whole row tinted `--accent-soft`, first error beneath the title in `--bad` — **I think this is wrong; see Q7** |
| C6 | Seen-state column | `NOT SEEN` / `COMPLETED · REV 1 · 2026-08-17` / `DISMISSED …` / `SEEN …` |
| C7 | Where-saves-land line | Two mutually exclusive sentences — checkout vs cloud studio |
| C8 | **List, empty** | **Not designed.** Deleting both rows leaves a bare header and a `+ New` button. See Q11 |
| C9 | Editor, existing | Header fields, trigger builder, step cards, foot |
| C10 | Editor, new | Same, all blank, kicker reads `NEW TUTORIAL` |
| C11 | Condition builder, simple | Kind select + one argument control, inline |
| C12 | Condition builder, composite | `all`/`any`/`not` drop to a full-width Courier JSON field |
| C13 | Save refused | Every reason at once, in a `--bad` bordered list above the foot |
| C14 | Step card | Head (`STEP 01` + Up/Down/Duplicate/Remove), then a field grid |

---

## 4. What I shipped, element by element

Everything below is in `app/static/styles.css` under
`/* ====== TUTORIALS  UNCANONIZED — 2026-08-17 */`. Every value is an
existing token; there are no new colours, no radius, and one animation.

### 4.1 Layering

```
45/44  header / band          400  app dialog (.modal-scrim)
460    THE TOUR LAYER         480  cropper          500  lightbox
```

The tour is **above** the app dialog on purpose — a step can point at
something inside one — and **below** the cropper and lightbox, which are
full-surface tools a tour has no business drawing over. `tests/
test_design_tokens.py` asserts `400 < z < 480`.

### 4.2 The spotlight

| Part | Current |
|---|---|
| Masks (×4) | `rgba(18, 20, 23, .78)`, `pointer-events: auto` |
| Cutout padding | 6px around the target rect |
| Ring | `1px solid var(--accent)` + `box-shadow: 0 0 0 1px var(--accent-soft)` |
| Block layer | transparent, `pointer-events: auto`, only when the step says so |
| Popover offset | 12px from the cutout; clamped ≥12px from every viewport edge |

### 4.3 The popover

| Part | Current | Voice |
|---|---|---|
| Container | `--panel2` on `1px solid var(--line)`, `min(440px, 92vw)`, `max-height: 80vh`, padding `18px 20px`, gap 10 | — |
| Kicker | 10px, `.12em`, uppercase, `--ink-faint` | Courier |
| Close (×) | `--ink-faint` → `--ink` on hover, 18px | — |
| Heading | 15.5px / 600 / `--ink`, line-height 1.25 | Archivo |
| Body | 13.5px / 1.5 / `--ink-dim`, 9px between paragraphs | Archivo |
| Inline code | 12px, `--ink` | Courier |
| Waiting line | 10px, `.1em`, uppercase, `--ink-faint`, `border-top: 1px solid var(--line-soft)`, 8px above | Courier |
| Foot | skip (`.text-act`) · gap · act (`.ghost`) · Back (`.ghost`) · Next (`.primary`) | — |
| Nudge | `translateX(3px)`, .18s, ×2, silenced under `prefers-reduced-motion` | — |

### 4.4 The CMS

Built from canon and nothing else: `.panel`, `.lib-head` / `.lib-title` /
`.lib-intro`, `.table`, `.modal-field`, `.fact-head`, `.text-act`,
`.ghost`, `.primary`, `.mini`, `.mono`, `.wv-tag`. The only new
declarations are layout: a `repeat(auto-fit, minmax(240px, 1fr))` field
grid, a step card on `--panel` / `--line`, a flex condition row, and the
error list on a `--bad` border.

---

## 5. What is mechanism — please do not redesign these

Changing any of these changes behaviour, not appearance. If one of them is
the problem, say so and I will change the mechanism; do not work around it
in CSS.

1. **The cutout is a real hole.** Four masks rather than a clipped scrim,
   because the highlighted control must stay clickable — the FTUE's last
   step is the user actually uploading their screenplay through the
   spotlight. A design that dims the target uniformly breaks the product.
2. **Anchors, not selectors.** Content names `status.next`; the registry
   maps it. Do not propose markup changes without saying so — the registry
   has a selector for each, and a test resolves every one against the real
   markup.
3. **The held gate.** When a step waits on a real action, Next is disabled
   and the reason is stated. The rule that gates are readable as state
   applies to a walkthrough too. You may rule *how* it reads.
4. **One tutorial at a time**, never over an open dialog, lightbox or
   cropper; resumes where it was left.
5. **Focus and keyboard.** Focus is trapped in the popover and returned on
   exit; Esc ends the tour; the waiting line is an `aria-live` region.
   Whatever you rule must keep a visible focus state on every control.
6. **Markdown-lite only.** Bodies are escaped, then `**bold**` and
   `` `code` `` are restored. HTML is never rendered. If you want a new
   inline form (a list, a keycap), name it and I will add it to the
   renderer — do not assume authors can write markup.

---

## 6. What is yours — the eleven questions

Ranked. Q1–Q3 are the ones I would not ship without.

**Q1 — The amber ring.** Amber has three sanctioned jobs: the current
pipeline stage, the one primary action in view, and focus. Is a tour target
one of those? It reads as "the one thing being asked for", which is close to
the second. But look at `tutorial-spotlight-2026-08-17.png`: the ring lands
on the DO-THIS-NEXT card, which **already** carries an amber left keyline
and an amber `DO THIS NEXT` kicker — and the popover's Next button is amber
too. Three ambers, one screen. Rule the ring: keep it amber, demote it to
`--ink`, or replace it with something that is not colour (a heavier
hairline, an inversion, a corner mark).

**Q2 — Two primaries, one screen.** The popover's `Next` is amber because
it is the primary action *of the popover*. But a spotlight step exists to
point at the app's own primary action. On step 4 the user should press the
app's control, not Next — and Next is the disabled one. Should the tour's
Next ever be `.primary`? A ghost Next with the app's control left as the
only amber thing in view would read more truthfully; it would also make the
tour's own progression feel weightless, which may be exactly right.

**Q3 — The dim value.** `rgba(18,20,23,.78)` over this ground reads as
"slightly darker", not "not this" — in the captures the cutout is legible
mostly because of its ring, which is doing two jobs at once. Give me a
value (or a treatment — the app's hatch is how it says "nothing here"
elsewhere) that separates cut-out from dimmed without the ring's help.

**Q4 — The waiting line's tier.** It is `--ink-faint` Courier under a
hairline today. The app has two existing grammars it could borrow instead:
`.gen-warn` (a stated consequence before a spend) and `step-cond` (a
condition beside a step). Which is it? It is not a warning — nothing is
wrong — but it is the most important line in the popover at that moment,
and faint is the quietest tier we have.

**Q5 — Announcement vs walkthrough chrome.** Today only the kicker text
differs (`WHAT'S NEW` vs `STEP 2 OF 5`). I built an amber kicker for
announcements and removed it as decoration. Does a release note earn its
own chrome — a rule, a different ground, an eyebrow — or is one popover
with different words correct?

**Q6 — The step counter.** `STEP 2 OF 5` in Courier at `--ink-faint`. It is
machine data by the voice rule, so Courier is right, but should progress be
*shown* rather than counted (a five-cell strip, a rule that fills)? A count
is honest and cheap; a strip is a promise about length that authored
content can break when a step is skipped by `skip_if`.

**Q7 — The invalid CMS row.** I tinted it `--accent-soft`, which I believe
is wrong: amber is not an error colour and a broken tutorial is a `--bad`
fact, not a current-stage one. My default if you say nothing is to change
it to a `--bad` left keyline with the ground untouched. Confirm or replace.

**Q8 — Where the tour's own exit lives.** There are two exits today — the
`×` at the top right and `Skip walkthrough` at the bottom left — because a
first-time user should never feel trapped, and one of them is where a
person's hand already is. Two exits may be one too many.

**Q9 — Popover width and measure.** `min(440px, 92vw)`, giving roughly
55–60 characters at 13.5px. The app's standing prose measure is 74ch. A
tour popover next to a control cannot be 74ch wide, but 440 may be too
narrow for a five-paragraph opening step. Rule the width, and whether the
centred (modal) form should be wider than the anchored one — today they are
identical, and only the centred one has room to be.

**Q10 — Motion.** One nudge on a scrim click (3px, twice, reduced-motion
guarded) and nothing else: steps cut, they do not slide. Should the cutout
travel between steps? It would help a user follow where the tour went; it
also costs the "steps(1), never fade" discipline the rest of the app holds.

**Q11 — The CMS empty state.** Not designed (C8). Deleting both shipped
rows leaves a header, a where-saves-land line and a `+ New tutorial` button
with a bare table above it. The app's grammar for this is the
stated-empty (`no activity recorded yet`, `none recorded`) — I need the
wording and the placement.

---

## 7. Constraints that still bind

Nothing here is up for review; it is the standing system, restated so the
ruling lands inside it.

- Amber is a signal, not a decoration — this is the whole substance of Q1
  and Q2, and the answer must survive the rule, not amend it.
- Courier for machine data (kicker, counter, waiting line, ids, statuses,
  the where-saves-land line); Archivo for hierarchy and prose.
- No framework, no new fonts, no new accent colours, no gradients, no
  rounded corners (`--radius` is 0 everywhere), no emoji.
- Every animation under `prefers-reduced-motion: reduce`.
- Existing class names are frozen; `tut-*` and `tut-adm-*` are new and
  yours to rename if a better name exists.
- Assertions in `tests/test_design_tokens.py` encode what I built. When you
  rule, they change with the CSS in the same commit — a red there means
  either the CSS or the contract is wrong, and your ruling decides which.

---

## 8. Delivering the ruling

A `*_PLAN.md` at the repo root, as usual — or a `*_SNIPPET.html` for any
element you would rather show than describe, which I will transliterate
(hex → existing token) rather than reinterpret.

Two process facts that bite here:

1. **Check `docs/RETIRED_PLANS.md` before assuming a plan is new.** Folder
   sync has resurrected implemented plans twice.
2. **The plan file is deleted the moment it is implemented**, and its row
   goes in that ledger. Write it as a document that is meant to be consumed
   and thrown away, not as a reference I will keep.

The Uncanonized table is at **eight rows** — twice the review threshold —
so if you are reviewing the whole queue, this is one row among eight and
should be ruled with the others rather than alone.
