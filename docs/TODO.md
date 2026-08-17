# TODO — improvements backlog

User-dictated improvements, recorded as given. An item leaves this list
in the same commit that implements it.

---

## Open from the adversarial review (2026-08-17)

`REVIEW_v1.md` + `REVIEW_v2.md` with the answers in
`docs/REVIEW_ROUND_1.md` / `_2.md`; what shipped is in `_3.md`. Twenty
findings are closed. These are not.

### R1. Delete the revisions machinery (F1, F24) — the big one

Revisions were retired by ruling on 2026-08-16 and the migration runs at
boot, but the mechanism is still fully live: 457 lines of
`app/revisions.py`, five routes, eleven `app/assemble.py` call sites, and
a `SLOT_OFFERED` gate row plus a `Keep` verb in the arrange room that can
no longer fire on any consolidated production. Two live answers to "what
was this panel approved as?", the other being the approval snapshot the
codebase itself calls the better one.

**The precondition is proven and pinned** — `tests/test_revisions_are_inert.py`
shows that on consolidated data every panel floor is 1, `offered` is
empty, the keeps registry is inert, and `qualifying_approved_by_panel`
reduces exactly to "newest approved take per panel". No skipped chain
exists on this machine, and F23 shipped so a future one is visible.

What is left is the refactor. Order: `assemble.py` first behind those
tests, then the routes, then the UI half (`Create revision`, `Also
revise`, `revision_scope`, `FROM R(n)` chips, `SLOT_OFFERED`, `Keep`,
`board-keeps`), then delete `app/revisions.py`.

**Deliberately not started at the end of a long session.** It is on the
path that produces the user's final boards, and a subtle error there
changes which takes appear on one without failing any test.

### R2. Two measurements only the user can settle (F18, F19)

Neither is a code change until a render decides it.

- **F19** — the reference-role block is 41% of the panel prompt and mostly
  production-constant. Filed as taste by the reviewer, correctly. Settle
  it with two renders of one panel, same seed and engine, full block
  versus the four style-anchor declarations compressed to a sentence each.
  If they tie, the shorter wins on cost; if the long form holds the
  anchors better, close the finding and record the measurement in
  `INTENT.md` beside the cost posture.
- **F18** — the anchored scenes are sent twice, once in the attached
  screenplay and again verbatim in the instructions (up to ~7 KB per
  breakdown draft). The duplication is real; the remedy is not obvious,
  because `insights.scene_anchor` does not expose scene headings, so
  replacing the quoted body with pointers would be a quality change made
  blind. Run three breakdowns both ways and compare the ledgers' citation
  accuracy.

### R3. Five routes still exempted as RETIRED

They sit in `tests/test_every_route_is_reachable.py`'s `RETIRED` map,
which is a to-do list rather than a category — deleting the route deletes
the row.

- `/api/specs/{id}/revisions`, `/consolidation`, `/consolidate` — go with R1.
- `/api/bible/sections` — duplicate; `bible_catalog` already rides
  `GET /api/specs/{id}`. Delete.
- `/api/sheets/candidates` — `sheet.fill_candidates()`, described in
  `ARCHITECTURE.md` as "the arrange room's tray". Wire it or delete it.

### R4. `unverified_citations` has no surface

`store.amend_panel_objects` returns it — the objects whose quote was not
found in the screenplay and so filed `USER_DIRECTED` instead of
`SCRIPT_EXPLICIT` — and nothing renders it. The user is told the object
was added, not that its citation did not hold. Logged in the non-canon
table for the designer.

### R5. Two surfaces neither side has reviewed

Named so their absence is not read as approval.

- **The arrange room's interaction** — drag, claim arrows, split-docking.
  The largest unreviewed surface in the app, twice-deferred in the design
  queue. F22 fixed one arithmetic defect inside it; nobody has reviewed it.
- **`storefront/` and the billing path** — out of scope for the review by
  instruction. A defect there costs real money rather than tokens.

### R6. The design queue is at 16 rows against its own ~4 trigger

`app/static/DESIGN_SYSTEM.md` → `## Uncanonized patterns`. Nine of the
rows land on the panels workbench card alone. The rule is that the user
opens their design-review chat with the folder re-synced and asks it to
review the table; the resulting plan files implement against
`DESIGN_SYSTEM.md`.

### R7. Nothing is deployed

28 commits are held locally, including the canon-integrity fix. Local mode
holds until the user says push.

---

## 1. Reference panel — approved refs cannot be deleted (2026-08-13)

Approved references must not be deletable directly. The card's verbs
become:

- **Crop** — as today.
- **Reject** — rejecting the ref is what unlocks deletion (delete is
  available only on a rejected ref).
- **Edit** — new verb; opens editing of the ref, from which the user can
  delete it or add images to the ref.

So the approved-state row reads `Crop · Reject · Edit` — no bare
`Delete`.

## 3. Panels rail — render-in-progress spinner (2026-08-13)

When a render is in progress for a panel, that panel's thumbnail in the
PANELS rail must show a spinning indicator. Today there is no visible
sign in the rail that a render is underway.

---

## Merged from TODO_2026-08-16.md (2026-08-17)

# Open work — 2026-08-16

Everything asked for and not yet shipped. Kept on disk because context
gets compacted and this does not. Tick a line only when it is committed
and tested; delete the file when it is empty.

Local mode is on (`.claude/iteration.json`) — items land as local commits
and go out together on "ship it".

## User feedback, in the order asked

- [x] Settings `Test & save` — no feedback during a long call
- [x] Productions moved into Settings as its first tab, FTUE unchanged
- [x] Locked stage cell showed the "no" cursor
- [x] Locations divided into acts, chronological, five per act + Expand
- [x] Lessons learned removed from Production Design
- [x] Act names when the screenplay prints no ACT headings
- [x] `Name the acts` without a destructive re-scan
- [x] Two screenplay copies — raw upload never reaches a model
- [x] **Casting modal** — clicking `Cast` opens a modal carrying the
      screenplay identity and the photo attach; on save the card lands
      where it does now.
- [x] **Blank Sheet, three fields** — server half is DONE (a pasted
      section can be the source; a panels hint pins the panels). Still to
      build: the form itself.
      1. *What should I get?* — fetched from the screenplay automatically
      2. *Paste a screenplay section* — the breakdown derives from it;
         carries an Open Screenplay link
      3. *What panels should it include?* — typed, or `Auto-generate`

## RULE_PASS_2026-08-16 — the design review

- [x] **Part A** — 8 rules folded, 7 rows cleared, 2 refusals shipped
- [x] **Part C** — stages 03/04/05, film rolls, ledger, stale-tab bar
      (10 rows; mostly ratification, small diffs — do this next)
- [x] **Part B** — the anchor cards (9 rows; the real work: one component
      with two lives, shared render, `Add your own` currently ships in two
      places and must collapse to one). Mocks: `rp-4a`, `rp-4b`
- [x] **Part D** — Productions as a tab; the self-reporting act (2 rows)
- [x] **Part E** — store queue, against `STORE_DESIGN_SYSTEM.md` (2 rows)
- [x] **B10 blocker** — a take records whether the cinematography grammar
      rode it and no screen says so. Ship the Courier fact line
      `GRAMMAR — <NAME>` on the hero and in the lightbox, absent on takes
      that did not ride. That row does not clear until it does.

Standing, from the bundle README:

- Arrange room stays deferred — never recorded, first item of the next
  harness walk. Do not ask about it.
- C1 reverses the 2026-08-13 direction on brief/camera ghost boxes
  deliberately. If they are wanted back they return as tools in a bar.
- A8 and C3 change shipped behaviour (`SETTLED`; the ledger freezing on
  the LOCK rather than on step 06) — A8 is done, C3 is in Part C.

## Housekeeping

- [x] `STEP_SEQUENCE_SPEC_2026-08-14.md` deleted + ledgered (superseded)
- [x] Delete each `RULE_PASS_*` file as its part lands, ledger it in
      `docs/RETIRED_PLANS.md`
- [x] Clear `design_handoff/` of everything already applied — user asked
      2026-08-16, AFTER the bundle is implemented, not before
- [ ] Re-run `/design-verify` on the UI-touching parts before shipping
