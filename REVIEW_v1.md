# REVIEW_v1 — Screenboard Studio

```
version:    1
date:       2026-08-17
app_sha:    84319a4
read:       docs/INTENT.md, CLAUDE.md, docs/ARCHITECTURE.md,
            app/static/DESIGN_SYSTEM.md (in full), docs/RETIRED_PLANS.md,
            app/main.py (routes + gate handlers), app/generate.py,
            app/store.py (spec/reference/amend paths), app/bible.py,
            app/autofill.py, app/narrative.py, app/scan.py,
            app/insights.py (citation + stage_summary + scene_anchor),
            app/paths.py, app/connectors.py (constants),
            app/static/app.js (matchers, workbench, ref bench, revisions),
            app/static/styles.css (token audit), tests/test_withdraw_approval_ui.py,
            tests/test_subject_identity_match.py, tests/test_object_ref_matching.py,
            tests/test_suite_hygiene.py, tests/test_stylesheet_parses.py,
            docs/TODO.md, docs/SOURCE_FILE_LIST.txt, SKILL.md (root)
            LISTED ONLY: docs/USER_GUIDE.md, APP_GUIDE.md, docs/DEPLOYMENT.md,
            docs/WEBAPP_GUIDE.md, docs/FULL_INSTRUCTIONS.md, agents/*.md,
            storefront/ (except the one preview-render caller I traced)
ran:        python -m unittest discover -s tests  → Ran 1249 tests, OK, 90.3s
            a route→caller sweep over app/main.py vs app.js + index.html
            app.store.auto_style_references() against a forged reference shelf
            app.generate.compile_panel_prompt() on a synthetic bible + spec
            app.store.amend_panel_objects() + app.scan._coerce() on a temp home
            app.insights._QUOTE_RE against a scan-written evidence row
            app.autofill._parse_json() on a truncated model reply
            a hex/token audit of app/static/styles.css
```

## Contents

- [1. Premise versus implementation](#1-premise-versus-implementation) — F1, F2
- [2. Cognitive load](#2-cognitive-load) — F3, F4, F5
- [3. Intent versus implementation gaps](#3-intent-versus-implementation-gaps) — F6–F13
- [4. Agent-facing structure](#4-agent-facing-structure) — F14, F15, F16
- [5. Token economy](#5-token-economy) — F17–F20
- [Top 10 in priority order](#top-10-in-priority-order)
- [Where I could be wrong](#where-i-could-be-wrong)

---

## 1. Premise versus implementation

Walking it end to end, most of the mechanism earns its place and I will not
spend words re-describing it. Briefly, what works:

- **The extract-once screenplay rule.** One decision, permanent saving, and
  `autofill._screenplay_bytes()` refuses rather than silently falling back.
  This is the model the rest of the app should be judged against.
- **`app/scan.py`.** Anchored excerpt instead of a full pass, server-side
  verbatim verification, drops counted on screen, nothing written until
  accepted. It is the best-built module in the app — which makes F6 and F7
  the more painful, because the guarantee it establishes is thrown away one
  function call later.
- **The no-upscale rule.** `sheet_render` raises `RenderShortfall`; only the
  assemble path letterboxes and flags. Enforced at the geometry authority
  rather than by convention. It holds.
- **The lock → hash-pinned approval snapshot.** `approval_snapshot` attaches
  the governing spec to the artifact. This is genuinely the right answer to
  "what was this approved as?", and it is why F1 follows.

What does not earn its place:

### F1 — Revisions are retired by ruling and still load-bearing in code and UI

**Claim.** The app runs two live answers to "what was this panel approved
as?" — the approval snapshot (which the codebase itself calls the better
one) and the revision chain it replaced — and the migration between them is
unreachable.

**Evidence.** Read code, plus the route sweep.
`app/generate.py:2578-2583`: *"(user rulings 2026-08-16). Revisions existed
to answer 'what was this approved AS?' — a snapshot answers it better."*
`app/main.py:1101-1103`: *"Collapse a revision chain into one breakdown
(user ruling 2026-08-16). Revisions are retired; this is the migration off
them."* Neither `POST /api/specs/{id}/consolidate` nor
`GET /api/specs/{id}/consolidation` has a caller in `app.js` (F9), and
`grep -rn "consolidat" app/*.py` finds no boot hook — so the migration has
never run on any production. Meanwhile the mechanism is fully live:
`Create revision` renders twice on the stage-03 editor
(`app.js:7147` in the lock strip, `app.js:7274` in the editor header),
`POST /api/specs/{id}/revise` is called at `app.js:8148`, and
`app/assemble.py` routes board assembly through `revisions.base_of`,
`revisions.load_keeps`, `revisions.qualifying_approved_by_panel` and
`revisions.panel_revision_floor` at eleven call sites. `app/revisions.py`
is 457 lines; "revision" appears 204 times across `app/*.py` and 46 times
in `app.js`; seven routes serve it.

**Severity.** `SERIOUS`. Not because either mechanism is broken, but because
a user's board can now be composed of takes selected by revision-floor rules
while the record of what each take was approved against comes from a
different structure. Two truths about one fact, and the project's own memory
rule (*migrations run, not offered*) is violated in the strongest possible
way: the migration is neither run nor offered.

**Proposal.** Remove revisions. Concretely: (a) run `revisions.consolidate`
as a boot migration under the A2 conditions already canon in
`DESIGN_SYSTEM.md` — journal the collapse, take a backup first, no screen;
(b) delete `Create revision`, `revision_scope`, `Also revise`, `board-keeps`
and the `FROM R(n)` chips; (c) reduce `assemble.py` to reading approved
takes for the spec directly, since after consolidation `base_of(id) == id`;
(d) delete `app/revisions.py` and its seven routes. The approval snapshot
already carries everything the revision chain was invented to carry.

**Cost.** Refactor. `assemble.py` is the real work; the UI half is deletion.

### F2 — The project-lessons mechanism is wired end to end and has never been written to

**Claim.** `rejection_lessons.json` and `project_state.json` are read by the
prompt compiler, the breakdown instructions, the dashboard and the stage
summary — and nothing in the app ever writes either of them.

**Evidence.** Read code.
- `generate.add_lesson()` / `generate.remove_lesson()` are called from
  exactly one place each: `app/main.py:2371` and `2377`, i.e. the orphaned
  `POST /api/lessons` and `POST /api/lessons/remove` (F9). No caller in
  `app.js`. So `rejection_lessons.json` is never created.
- `paths.PROJECT_STATE` is read at `autofill.py:465`, `generate.py:264`,
  `main.py:712` and `store.py:265`, and written by nothing in `app/` —
  only by `scripts/state_manager.py`, a CLI.
- Therefore `generate.project_negatives()` (`generate.py:260`) always
  returns `[]`, and the `PROJECT LESSONS LEARNED — standing corrections
  from previously rejected work` block at `generate.py:912-916` has never
  appeared in a prompt. `_instructions` always says
  `Known prohibited inventions for this project (never include): none recorded`.
- `insights.stage_summary` reports `"lessons": len(generate.load_lessons())`
  (`insights.py:225`) — a number that is structurally always 0.
- `app.js:2229` renders `#dash-prohibited` from `state.prohibited_inventions`,
  which is always `[]`, so that dashboard block permanently reads
  `none recorded`.

Rejection reasons are **not** lost — `archive_feedback` / `carried_feedback`
/ `rejection_feedback` are real and ride the prompt as DIRECTOR'S
CORRECTIONS. But that is a per-panel mechanism, and the project-wide one
beside it is empty scaffolding. See F12 for the copy that tells the user
otherwise.

**Severity.** `WORTH FIXING` as dead code; `SERIOUS` for its copy (F12).

**Proposal.** Remove it. Delete `add_lesson`/`remove_lesson`/`load_lessons`,
the three `/api/lessons` routes, the `PROJECT LESSONS LEARNED` prompt block,
the `lessons` count in `stage_summary`, and `#dash-prohibited`. Keep
`prohibited_inventions` **only** if `scripts/state_manager.py` is a real
operator tool — and if it is, say so where the block is read. The carried-
rejections mechanism already does this job honestly.

**Cost.** Small change.

---

## 2. Cognitive load

The density stance is correct and I am not arguing with it. Three places
where it stops paying.

### F3 — The uncanonized queue is at 14 rows against its own ~4-row trigger

**Claim.** `DESIGN_SYSTEM.md`'s own rule says to tell the user at ~4 rows;
the table holds 14, the oldest from 2026-08-12.

**Evidence.** Ran `grep -n 'Uncanonized' app/static/DESIGN_SYSTEM.md`;
read lines 1480-1519. Fourteen rows dated 2026-08-12 through 2026-08-17,
including two explicitly `DEFERRED` twice (arrange room, board looks).
`CLAUDE.md` and `DESIGN_SYSTEM.md:1488` both state the ~4 trigger.

**Severity.** `WORTH FIXING`. This is process, not pixels, but it is the
mechanism that keeps the UI coherent, and it has been off for five days
while the densest new surfaces in the app (the panels workbench steps 01–06)
were built. Nine of the fourteen rows land on one card.

**Proposal.** Ship the review before more workbench features. If the queue
genuinely cannot be cleared at this cadence, the trigger is the wrong number
and should be raised deliberately in the file rather than exceeded silently —
a rule the code routinely violates teaches the next agent that the file is
advisory.

**Cost.** Small change (the telling); the review itself is the user's.

### F4 — 46 hardcoded hex values outside `:root`, including two literal copies of existing tokens, with no standing contract

**Claim.** *"Use variables. Never hardcode a hex in new CSS"* has no test,
and the newest CSS in the file breaks it — twice by re-typing a token's own
value.

**Evidence.** Ran a hex audit over `app/static/styles.css`. 21 tokens in
`:root`, 46 hex literals outside it. Most are sanctioned by named rulings
(`#4a4d52` disabled, `#17191c` locked cell, `#3a4048` popover, the sheet-ink
palettes under R4.6b, the hatch band pairs). These are not:

```
styles.css:3578   border: 1px solid #2b3037;      /* this IS --line */
styles.css:3599   border: 1px solid #23272c;      /* this IS --line-soft */
styles.css:3577   #0d0e10;                        /* new grey */
styles.css:3594   border-right: 1px solid #14171b;/* new grey */
styles.css:3599   background: #050607;            /* darker than --field #0f1114 */
```

All five are in the `.filmroll` / `.take-frame` block dated 2026-08-15/16 —
the most recent CSS in the file. `tests/test_design_tokens.py` has 40+
assertions but none of them is "no undocumented hex"; `test_no_undocumented_
hex_in_hover` is scoped to one rule.

**Severity.** `WORTH FIXING`. `#050607` and `#0d0e10` are a fourth and fifth
surface below `--field`, which is exactly what *"do not invent a fourth
grey"* forbids; and two of the five are drift waiting to happen the next
time `--line` moves.

**Proposal.** Add one test to `tests/test_design_tokens.py`: collect every
hex outside `:root`, subtract an explicit `SANCTIONED` dict mapping each
allowed literal to the ruling that allows it, assert the remainder is empty.
That dict is also the documentation. Then fix the five above — the two token
copies become `var(--line)` / `var(--line-soft)`, and the three greys either
become tokens with a changelog line or collapse onto `--field`/`--bg`.

**Cost.** Small change.

### F5 — `N OF 14 ATTACHED` states a count the screen cannot prove, and the cap is written twice

**Claim.** The reference bench reports the render's attachment budget from
client-side rules that do not match the server's, and hardcodes the cap.

**Evidence.** Read code. `app.js:9788-9793` computes
`total = subject.length + palCount + styleAnchors.length` and prints
`= ${total} OF 14 ATTACHED`, with `over = total > 14`. The `14` is a JS
literal in two places; the server's is `generate.MAX_REFERENCE_IMAGES = 14`
(`generate.py:142`) and there is a third copy, `connectors.APP_MAX_REFS = 14`
(`connectors.py:38`). Separately, `_resolve_generation_inputs` inserts the
lighting-study geometry anchor (`generate.py:1123`) into `refs` **after** the
client has counted, so a lighting-study board at 14 is refused server-side by
a limit the screen said was not reached — a gate that reports after the fact.
The larger problem with this same count is F8.

**Severity.** `WORTH FIXING`. `DESIGN_SYSTEM.md` §9: *"State a count without
making it provable"* is a listed Do-not, and this is the count that decides
whether a paid render carries the right plates.

**Proposal.** Delete the client's arithmetic. Have the server return the
resolved manifest — `GET /api/specs/{id}/panels/{id}/attachments?refs=…`
returning the exact `refs` list `_resolve_generation_inputs` would build,
including geometry anchor, per-role caps and palette collapse — and render
that. One computation, one cap constant, and the manifest becomes provable
by construction. `MAX_REFERENCE_IMAGES` ships to the client in `/api/state`.

**Cost.** Small change (the endpoint is a 6-line extraction of code that
already exists).

---

## 3. Intent versus implementation gaps

### F6 — A fabricated citation is written into the evidence ledger as `SCRIPT_EXPLICIT` / `PASS`, with no verification against the screenplay

**Claim.** `store.amend_panel_objects` decides an object's evidence class
from the mere *presence* of a `quote` string in the request body, and never
checks that string against the screenplay.

**Evidence.** Ran it. `app/store.py:1060-1065`:

```python
ledger.append({
    "panel_id": panel_id, "object": obj,
    "evidence_class": "SCRIPT_EXPLICIT" if quote else "USER_DIRECTED",
    "source": quote or "User direction",
    "status": "PASS",
})
```

Against a throwaway home with a screenplay reading only
`INT. TERRA NOVA SECURE BAY - NIGHT / SAL crosses the empty bay.`:

```
POST .../panels/P01/objects  add=[{object: "a shrine of welded scrap",
                                   quote: "A shrine of welded scrap stands in the corner."}]
→ {"panel_id": "P01", "object": "a shrine of welded scrap",
   "evidence_class": "SCRIPT_EXPLICIT",
   "source": "A shrine of welded scrap stands in the corner.",
   "status": "PASS"}
screenplay actually contains that line? False
```

There is a second route to the same row that does not require a hand-crafted
request. `scan.scan_panel` verifies quotes against `source`, but `source` is
`anchor["text"]` **only when the anchor matched**; on a miss it falls back to
`str(spec.get("scene", ""))` (`scan.py:171-172`) — the breakdown's own
`scene` field, which `autofill` had a *model* write (`autofill.py:185`,
`_scene_field`). So on an anchor miss the app verifies the model's citation
against the model's own earlier prose and files the result as the
screenplay's word. Ran it:

```
scan._coerce({"finds":[{"from":"screenplay","object":"votive candles",
              "detail":"Candles ring the shrine.",
              "quote":"ringed by votive candles"}]},
             spec["scene"])
→ accepted, from: "screenplay", dropped: 0
```

`spec["scene"]` in that run was model-drafted prose. The screenplay says
nothing about candles.

**Severity.** `BLOCKING`. INTENT conviction 1 is *"Canon is extracted, never
invented… unsupported objects can never pass, in any mode."* This is the one
write path where canon reaches disk with a citation, and it takes the
citation on trust. Downstream, `validate_spec` requires PASS coverage to
approve and lock; a fabricated `SCRIPT_EXPLICIT` row silently satisfies that
gate, and because it is not a `WEAK_INFERENCE` it does not consume the
`CANON_EXTRACTION` budget of 2 either. The product's central promise is that
a human said "this is canon" — here the app says it on the model's behalf.

**Proposal.** Move verification to the write, where the guarantee has to
live. In `store.amend_panel_objects`, before filing `SCRIPT_EXPLICIT`,
re-check the quote against `store.screenplay_text_cached()` using the same
normalisation `insights.citation_check` uses (`_norm` / `_squash`); on a
miss, file `USER_DIRECTED` with the user's own text as `source` and return
the demotion so the UI can state it. In `scan.scan_panel`, when the anchor
does not match, mark every find `direction` regardless of what the model
claimed — the screenplay was not read, so nothing can be sourced to it — and
say so in `note`. Add a regression test that a quote absent from the
screenplay can never produce a `SCRIPT_EXPLICIT` row through any route.

**Cost.** Small change. The normalisation helpers already exist.

### F7 — The citation re-check is structurally blind to the rows F6 writes

**Claim.** `insights.citation_check` only inspects quoted spans, and
`amend_panel_objects` writes the quote unquoted — so the app's one standing
net for bad citations never looks at the newest source of them.

**Evidence.** Ran it. `insights.py:755`:
`_QUOTE_RE = re.compile(r'["“]([^"“”]{12,300})["”]')`, applied at line 781 to
`row["source"]`.

```
scan-written source: 'A shrine of welded scrap stands in the corner.'
_QUOTE_RE.findall(...) → []                # not checked, not counted
quoted source:       '"A shrine of welded scrap stands in the corner."'
_QUOTE_RE.findall(...) → ['A shrine of welded scrap stands in the corner.']
```

`checked` does not increment, so the row is absent from `quotes_checked`
as well as from `missing`. The user is shown a clean citation report over a
denominator that silently excludes the fabricated rows.

**Severity.** `SERIOUS` on its own, and it is what turns F6 from a bug into
an invisible one.

**Proposal.** Make the ledger's contract explicit rather than inferring it
from punctuation: add `quote` as its own field on evidence rows (empty for
non-quoting classes) and have `citation_check` read that field, keeping
`_QUOTE_RE` only as a legacy reader for rows written before the change. A
row whose `evidence_class` is `SCRIPT_EXPLICIT` with an empty `quote` is
itself a finding the report should raise.

**Cost.** Small change plus a boot migration to backfill `quote` from
existing `source` strings (which the A2 migration rule already permits).

### F8 — The render manifest names plates that do not ride and omits plates that do

**Claim.** The workbench's "every plate that will ride, named" manifest and
its `N OF 14 ATTACHED` count are computed from a client-side rule that
disagrees with `store.auto_style_references()` in both directions.

**Evidence.** Ran it against the real `store` on a forged shelf.

Server (`store.py:98-99, 411-423`): `AUTO_STYLE_ROLES = {WORLD_TEXTURE,
COLOR_PALETTE, CINEMATOGRAPHY_STYLE, BOARD_RENDERING_STYLE}`, newest
`STYLE_ATTACH_CAP = 2` per role.
Client (`app.js:9150-9155`): `isAutoStyle = r => ["BOARD_RENDERING_STYLE",
"CINEMATOGRAPHY_STYLE"].includes(roleHead(r.role))`, **no cap**.

With three approved `WORLD_TEXTURE`, three `CINEMATOGRAPHY_STYLE` and one
`BOARD_RENDERING_STYLE` on the shelf:

```
SERVER auto-attaches: REF-002, REF-001 (WORLD_TEXTURE)
                      REF-005, REF-004 (CINEMATOGRAPHY_STYLE)
                      REF-006          (BOARD_RENDERING_STYLE)   = 5
CLIENT counts as STYLE: REF-003, REF-004, REF-005, REF-006        = 4
client omits : REF-001, REF-002      (ride, unnamed)
client invents: REF-003              (named, does not ride)
```

Three plates misreported on a shelf of seven. `WORLD_TEXTURE` references
additionally fall into `approvedRefs` (`app.js:9162`) and are offered as
tickable subject groups, so the UI presents as optional something that
attaches unconditionally.

**Severity.** `SERIOUS`. `DESIGN_SYSTEM.md` C6 requires the manifest to be
*"listed in full beside the prompt it rides in"*, and the workbench states
`THE RENDER WORKS FROM EXACTLY WHAT IS BELOW`. This is one fact reported by
two surfaces that disagree, on the screen where money is spent — and the
misreported role is `WORLD_TEXTURE`, i.e. the anti-drift anchor.

**Proposal.** The same server-resolved manifest endpoint as F5. Do not fix
`isAutoStyle` by adding the two missing roles — that leaves the per-role cap
still unimplemented on the client and re-creates the drift on the next
ruling. Delete the client's copy.

**Cost.** Small change; shares its fix with F5.

### F9 — Ten routes have no caller

**Claim.** The unreachable-capability pattern is not confined to candidate
routes; a full sweep finds ten more.

**Evidence.** Ran a route→caller sweep: every `@app.<verb>("…")` in
`app/main.py` (143 routes) matched against `app.js` + `index.html` with
path parameters relaxed to template-literal interpolation, then each
non-match traced by hand. Four non-matches are legitimate (`GET /login`
and `POST /api/login` — server-rendered login page;
`/connectors/openrouter/callback` — OAuth redirect; `/api/preview-render` —
called server-to-server at `storefront/app/main.py:777`). The remaining ten:

| Route | What it is |
|---|---|
| `GET /api/projects/safety-zip` | pre-import safety copy download |
| `GET /api/screenplay/text` | the extracted text the models read |
| `GET /api/specs/{id}/revisions` | docstring: *"feeds the boards-stage base picker"* |
| `GET /api/specs/{id}/consolidation` | the migration's read-before-the-act plan |
| `POST /api/specs/{id}/consolidate` | the migration off revisions (F1) |
| `GET /api/bible/sections` | duplicate — `bible_catalog` already rides `GET /api/specs/{id}` (`main.py:993`) |
| `GET /api/lessons` | F2 |
| `POST /api/lessons` | F2 — the only writer of `rejection_lessons.json` |
| `POST /api/lessons/remove` | F2 |
| `GET /api/sheets/candidates` | `sheet.fill_candidates()`, described in `ARCHITECTURE.md:34` as *"the arrange room's tray"* |

Two deserve calling out. `safety-zip`'s own docstring reads *"It was
insurance with no way to collect it — written to the volume and
unreachable"* — the endpoint was added to fix exactly that and the UI half
was never built, so the safety copy is still uncollectable
(`grep "safety" app/static/app.js` finds only prose). And
`/api/screenplay/text` means the extracted text — the copy every model
actually reads, and the whole point of the two-copies rule — has no reader
in the product; `Open the screenplay ↗` opens the raw PDF
(`app.js:2284`, `5869`).

`tests/test_withdraw_approval_ui.py:99` tests this property for
`POST /api/specs/{spec_id}/candidates/{cand_id}/*` only.

**Severity.** `SERIOUS`. Individually most are `WORTH FIXING`; collectively
it is the demonstrated failure pattern, unswept, with a test that covers
1 of 143 routes' worth of the surface.

**Proposal.** Generalise the existing test to every route, with an explicit
`SERVER_TO_SERVER` allow-list naming the caller for each exemption
(`/api/preview-render` → `storefront/app/main.py`, `/api/login` →
`_LOGIN_HTML`, the OAuth callback). Then close each row: wire `safety-zip`
into the Productions card's care states, delete `/api/bible/sections`,
delete the lessons routes (F2), resolve the revisions routes with F1, and
either wire or delete `/api/sheets/candidates`. `/api/screenplay/text`
should get a caller: a "read what the models read" door beside
`Open the screenplay ↗` is a two-line change and makes the token rule
legible to the user.

**Cost.** Small change for the test; the rows are individually small.

### F10 — The subject-identity matcher has no stopword list, so a common word in a cast card's name injects that subject's canon into unrelated panels

**Claim.** `generate.subjects_for_object` treats any ≥3-letter word as
distinctive; `app.js` fixed this with `NAME_STOPWORDS` and the server copy
never got it.

**Evidence.** Ran `subjects_for_object` directly.

```python
subjects = [{"name": "The Beacon",  "traits": ["brass, cracked lens"]},
            {"name": "Sal's Cryo-Chamber", "traits": ["frosted glass"]},
            {"name": "Sal Craft",   "traits": ["dark-haired, forties"]}]

"the drill rig"                 -> ['The Beacon']
"a mug of coffee on the table"  -> ['The Beacon']
```

Both phrases put `- The Beacon (PROP): brass, cracked lens` into the
prompt's `SUBJECT IDENTITIES` block, under the instruction *"Render each as
EXACTLY what it is named to be — never a generic substitute of its type"*.
The client has `NAME_STOPWORDS` at `app.js:634-637` with the comment
*"A group really is called 'P02 SHACK IN THE MEADOW', and 'the' clears three
letters — without this, every object containing the word 'the' matched it"*,
and `tests/test_object_ref_matching.py:102` pins it. `app/generate.py:743`
has no equivalent, and `tests/test_subject_identity_match.py` has no
stopword case.

I checked whether the JS/Python divergence is deliberate: it is, and it is
documented at `app.js:659-667` and `generate.py:773-777` (the identity rule
refuses on shared words, the plate-offer rule does not). I am not raising
that. The stopword gap is a separate omission on the strict side of a
deliberate split.

The same one-sided fix applies to `normName` (`app.js:648-651`, possessive
and hyphen normalisation): `"closing cryochamber"` and `"Sals eyes"` both
return `[]` server-side. Those two cases are the ones the JS comment cites
as user-caught, and the identity block is the copy `generate.py:760-763`
calls *"the more damaging one"* to miss.

**Severity.** `SERIOUS`. A panel that never asked for a prop gets that prop's
canon description asserted into its render prompt. That is invented content
reaching the model under the app's own authority — the failure the evidence
system exists to make impossible.

**Proposal.** Move `NAME_STOPWORDS` and `normName` to one place and share
it. Since `_word_in`/`_name_words` are pure string functions, put them in
`app/validation.py` (already the stdlib-only rule engine both sides import),
export the stoplist through `/api/state`, and have `app.js` read it rather
than hold its own — one list, one normalisation, two callers with their
deliberately different *policies* on top. Add the stopword and possessive
cases to `tests/test_subject_identity_match.py`.

**Cost.** Small change.

### F11 — A truncated model reply surfaces as a JSON parser message and a 502

**Claim.** The most expensive failure in the app has the least usable error.

**Evidence.** Ran it. `autofill._parse_json` (`autofill.py:367-382`) catches
`JSONDecodeError` from the first `json.loads`, then calls
`json.loads(m.group(0))` **outside any try**:

```
_parse_json('{"subject": "…", "panels": [{"id": "P01", "title": "The over')
→ json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 91 (char 90)
```

`main.py:2402` catches it as the catch-all
`except Exception as e: raise HTTPException(502, f"auto-fill failed: {e}")`.
So a user who has just paid for a full-screenplay pass is told
`auto-fill failed: Expecting ',' delimiter: line 1 column 91 (char 90)`,
with nothing to act on and no indication that re-running will hit the same
ceiling. The likely cause is `narrative.MAX_OUTPUT_TOKENS = 8192` (F20), and
the Anthropic response's `stop_reason` is never inspected
(`narrative.py:107-111`).

**Severity.** `WORTH FIXING`.

**Proposal.** Wrap the second `json.loads` and raise
`AutofillError("The model's reply was cut off before the JSON closed …")`.
Read `stop_reason == "max_tokens"` in `anthropic_complete` and raise a
stated error naming the limit and the fix. Both messages should say what a
retry will cost, since a retry re-sends the whole screenplay.

**Cost.** Small change.

### F12 — Four confirmation dialogs tell the user rejection reasons go somewhere that does not exist

**Claim.** A label that lies, in the copy protecting a destructive act.

**Evidence.** Read code, following F2. The lessons list is never written,
yet:

```
app.js:9019   "Its rejection reason stays in the lessons list and rejection history."
app.js:10969  (same string, second delete path)
app.js:9368   title="…rejection reasons stay in the lessons list and rejection history"
app.js:10718  "Rejection reasons stay in the lessons list and rejection history."
app.js:7203   Forbidden elements <span class="hint">(one per line — seeded from
              the rejection history on the dashboard)</span>
app.js:7546   title="…Merged with the board-wide forbidden elements and project
              lessons in the prompt."
```

The first four are the reassurance that makes `Delete forever` safe to
press. Half of it is true (rejection history and carried feedback are real);
the "lessons list" half names a file the app never creates, and the last two
promise a prompt contribution and a seeding path that do not exist.

**Severity.** `SERIOUS`. The user is being reassured about a destructive act
by a mechanism that is not there.

**Proposal.** With F2's removal, rewrite the four strings to name what
actually survives: *"Its rejection reason keeps riding this panel's future
prompts as a director's correction."* That is both true and more useful,
because it says the reason still costs tokens. Delete the seeding claim at
`app.js:7203` or build the seeding.

**Cost.** Small change.

### F13 — One predicate written twice under a comment asserting it is one list

**Claim.** "Which evidence rows justify this panel's objects" has two
implementations, in the two places that must agree, and the comment above
one of them says they share a list.

**Evidence.** Read code.

`app/store.py:816-825` (the gate that refuses edits):
```python
objs = {str(o).lower() for o in (… required_objects …)}
return [r for r in (spec.get("evidence_ledger") or [])
        if str(r.get("panel_id", "")).upper() == str(pid).upper()
        or str(r.get("object", "")).lower() in objs]
```
`app/generate.py:2593-2596` (the snapshot the gate protects):
```python
objects = {str(o).lower() for o in (panel.get("required_objects") or [])}
rows = [r for r in (spec.get("evidence_ledger") or [])
        if str(r.get("panel_id", "")).upper() == str(panel_id).upper()
        or str(r.get("object", "")).lower() in objects]
```

Directly above the second, `generate.py:2588-2591`: *"One list, read by both
the snapshot and the gate that protects it: what an approval freezes and
what a locked breakdown refuses must be the same set, or the app promises
one thing and guards another."* What is actually shared is
`SNAPSHOT_BOARD_FIELDS = store.BOARD_LEVEL_FIELDS` — the board fields, not
the row predicate. The two row selectors agree today by coincidence of
having been typed twice.

**Severity.** `WORTH FIXING`. Nothing is broken now; the comment is what
makes it worth fixing, because the next reader will trust it and change one
side.

**Proposal.** Extract `store.evidence_rows_for_panel(spec, panel_id)` and
call it from both. Delete the comment's claim or make it true.

**Cost.** Small change.

---

## 4. Agent-facing structure

### F14 — A pre-app, project-hardcoded skill sits at the repo root

**Claim.** `SKILL.md` at the repository root is the July "Beltminers
Production Art Director v2" prompt-skill from before the app existed, and it
contradicts the product it now sits beside.

**Evidence.** Read it. Line 1: `# Beltminers Production Art Director v2`.
Line 5: *"The purpose of this skill is not to invent* The Beltminers.*"* Its
source-authority ladder and PROPOSED-NOT-CANON vocabulary are the ancestors
of the current evidence system, but it is written for one film.
`INTENT.md:128` states the opposite as a product rule: *"no template art
direction, no hardcoded project names anywhere in prompts or records"*, and
`bible.py:1` opens *"Art Direction Bible ingestion — project-agnostic."*
`docs/SOURCE_FILE_LIST.txt` confirms the provenance: it lists
`/mnt/data/beltminers_production_art_director_v2/SKILL.md`, i.e. paths from
a sandbox that no longer exists.

**Severity.** `WORTH FIXING`. `SKILL.md` at a repo root is a filename agents
read on sight, and it teaches a project-specific model of a project-agnostic
app.

**Proposal.** Move it to `docs/history/SKILL_v2_2026-07.md` with a one-line
header saying it is the pre-app origin document and is not current, or
delete it — `agents/01_research_agent.md` through `13_approval_recorder.md`
already carry the live role descriptions. Delete
`docs/SOURCE_FILE_LIST.txt` outright; it is a listing of a filesystem that
does not exist.

**Cost.** Small change.

### F15 — `docs/` is 24 files with no map, several of them dated snapshots and one live plan the project's own rule says should be deleted

**Claim.** An agent cannot tell from the directory which documents are
binding.

**Evidence.** Listed and spot-read. Binding and current: `INTENT.md`,
`ARCHITECTURE.md`, `DEPLOYMENT.md`, `WEBAPP_GUIDE.md`, `SECURITY.md`,
`IMAGE_SERVING.md`, `CAMERA_AND_COMPOSITION.md`, `CINEMATOGRAPHY_STYLES.md`,
`RETIRED_PLANS.md`, `USER_GUIDE.md`, `TEST_MATRIX.md`. Dated snapshots that
read as instructions: `AUDIT_2026-08-02.md`, `HANDOFF_2026-08-10.md`,
`PROMPT_TEST_2026-08-16.md`, `POOLED_REARCHITECTURE.md`,
`FULL_INSTRUCTIONS.md` (2026-07-20, 22 KB, predates the redesign).
`BUGFIX_PLAN_2026-08-12.md` is a `*_PLAN.md` still in the tree, which
`CLAUDE.md`'s own 2026-08-12 ruling says must be deleted the moment it is
implemented and recorded in `RETIRED_PLANS.md` — it is in neither state.
Two backlogs, `docs/TODO.md` and `docs/TODO_2026-08-16.md`, with no stated
relationship; `docs/TODO.md` says *"An item leaves this list in the same
commit that implements it"* and its item 1 (approved references not directly
deletable, 2026-08-13) does not obviously correspond to shipped code —
`app.js:8904` still renders `.ref-card` without the `Crop · Reject · Edit`
row the item specifies. Add `SOURCE_CODE_GUIDE.md` (1.1 KB) and
`MANIFEST.md` (285 bytes), which say almost nothing.

**Severity.** `WORTH FIXING`.

**Proposal.** Three concrete moves.

1. **`docs/README.md` — the map, and the only file an agent must read to
   know what to read.** One table: *area touched → the one document that
   governs it → what is out of date about it*. Rows: `app/` UI →
   `app/static/DESIGN_SYSTEM.md`; `app/` behaviour → `docs/ARCHITECTURE.md`;
   `storefront/` code → `docs/WEBAPP_GUIDE.md`; infra → `docs/DEPLOYMENT.md`;
   prompts/models → `docs/INTENT.md` §Cost posture + `app/generate.py`
   docstrings; anything with a `*_PLAN.md` name → `docs/RETIRED_PLANS.md`
   first. It deliberately does **not** summarise those documents — a summary
   is a second copy that drifts.
2. **`docs/history/`.** Move `AUDIT_2026-08-02.md`, `HANDOFF_2026-08-10.md`,
   `PROMPT_TEST_2026-08-16.md`, `POOLED_REARCHITECTURE.md`,
   `FULL_INSTRUCTIONS.md`, `SOURCE_CODE_GUIDE.md` there with a one-line
   `README` stating that nothing in the folder is binding. Retire
   `BUGFIX_PLAN_2026-08-12.md` into `RETIRED_PLANS.md` per the existing
   rule. Merge the two TODOs into one and reconcile item 1 with the code.
3. **Delete** `docs/SOURCE_FILE_LIST.txt` and `MANIFEST.md`.

**Cost.** Small change.

### F16 — Two skills exist; three more would each have prevented a defect in this report

**Claim.** The procedures that catch this codebase's characteristic failures
are prose, or nothing, rather than checklists.

**Evidence.** `.claude/skills/` holds `design-verify` and `iterate` only.
The failures above cluster into three repeatable procedures.

**Proposal.**

1. **`.claude/skills/reachable/`** — *"you built a capability; prove a user
   can reach it."* Runs the F9 sweep as a command, then one checklist: name
   the caller in `app.js` for each new route; name the surface it renders
   on; state which gate makes it visible. Exits by extending the
   generalised route test. This alone is F9, and would have caught the
   prompt editor, its Save, `unapprove_candidate`, `safety-zip` and
   `consolidate` at the commit that introduced each. It deliberately does
   **not** review the feature's design — `design-verify` owns that.
2. **`.claude/skills/one-rule/`** — *"this question is now answered in two
   places."* Triggered whenever a predicate is written in both Python and
   JS, or twice in Python. Checklist: is there an existing shared helper;
   if the two must differ, is the difference documented at both sites and
   pinned by a test at both sites; is the shared half actually shared, or
   merely claimed to be. F8, F10 and F13 are all one skill's worth of the
   same discipline, and F13 shows the failure mode — a comment asserting a
   sharing that does not exist.
3. **`.claude/skills/spend/`** — *"you added a model call or a prompt
   block."* Checklist: what is in the prompt that the model cannot act on;
   is the stable material a prefix; is provider-side caching actually
   engaged for **each** configured provider (F17); what is the output
   ceiling and what happens at it (F11, F20); does a retry re-send
   everything. Emits a measured before/after character count per block, the
   way §5 below is measured, into the commit message.

Two short checkable rules that would each have paid for themselves, both
verifiable in one command:

- **No hex outside `:root` without a named ruling** (F4) —
  `python -m unittest tests.test_design_tokens.NoUndocumentedHex`.
- **No route without a caller or a named server-to-server consumer** (F9) —
  the generalised form of the existing candidate-route test.

**Cost.** Small change each.

---

## 5. Token economy

Measured, not estimated. I compiled a panel prompt through the real
`generate.compile_panel_prompt` against a synthetic bible (four global
sections, two design languages, one environment, one scene lesson — smaller
than a real one) with eight attached references:

```
TOTAL 6,443 chars / 96 lines
 2,639  41%  APPROVED REFERENCE ROLES
   578   9%  CAMERA
   302   5%  BOARD-SPECIFIC TREATMENT
   300   5%  RENDERING LANGUAGE
   259   4%  NON-NEGOTIABLE SOURCE RULES
   242   4%  SETTING
   222   3%  THE MEDIUM IS NOT NEGOTIABLE
   213   3%  DETAIL BUDGET
   198   3%  <design language>
   … everything else ≤ 3% each
```

The brief's ~11,000 characters is this with a real bible. The distribution
is the useful finding: the largest block by a factor of four is not art
direction, it is the app explaining reference roles to the model.

### F17 — The Anthropic narrative path engages no prompt caching, and `INTENT.md` says it does

**Claim.** `INTENT.md` claims *"prompt-caching engaged by keeping the
screenplay as the stable prompt prefix"*. That is true for OpenAI and Gemini,
whose caching is automatic, and false for Anthropic, whose caching requires
an explicit `cache_control` breakpoint that the code never sets.

**Evidence.** Read code. `narrative.anthropic_complete`
(`narrative.py:81-111`) builds
`content = [{"type": "text", "text": "SCREENPLAY FOLLOWS\n…" + doc}, …,
{"type": "text", "text": instructions}]` and posts it with no
`cache_control` on any block and no `anthropic-beta` header. Prompt caching
on the Messages API is opt-in per block; without a breakpoint nothing is
cached and every pass bills the screenplay at full input rate.
`ARCHITECTURE.md:180` gives the reference draft as 131 KB of text — roughly
33k tokens — re-sent on every scene scan, every breakdown draft, every
re-draft and every bible draft. `anthropic` is one of the two documented
narrative homes (`ARCHITECTURE.md:39`) and the default model is
`claude-sonnet-5` (`narrative.py:23`).

**Severity.** `SERIOUS` — a stated cost guarantee that does not hold on one
of the shipped paths, and the saving is the largest single one available.

**Proposal.** Put `"cache_control": {"type": "ephemeral"}` on the screenplay
text block in `anthropic_complete`. The ordering is already correct — the
screenplay is first, instructions last — so one field turns the existing
structure into a cache hit. Then either confirm the same for OpenRouter's
pass-through (`openrouter_complete`, which has the same shape and the same
omission) or state in `INTENT.md` which providers cache and which do not.
The claim should name its providers either way.

**Cost.** Small change.

### F18 — The anchored scenes are sent twice in every breakdown draft

**Claim.** When `scene_anchor` matches, the same scene text goes to the
model once inside the attached screenplay and again verbatim inside the
instructions.

**Evidence.** Read code. `autofill.autofill_spec:463` sends the whole
extracted screenplay as `doc`; `:498-500` then appends `_anchor_block(anchor,
board_type)` to the instructions, whose own header reads *"All of its scenes
are quoted below verbatim from the attached screenplay."* `anchor["text"]` is
capped at `max_chars=7000` (`insights.py:475`), so the duplication is up to
~7 KB (~1,750 tokens) per breakdown draft on top of the ~33k-token document.

I am **not** proposing that the whole screenplay stop being sent — the
instructions explicitly use the rest as context (*"any other location in the
screenplay is context only and never the subject"*), and narrowing it is a
quality change I cannot evaluate from here. The duplication is separable
from that question.

**Severity.** `WORTH FIXING`.

**Proposal.** Keep the anchor block's framing sentences — they are what fixed
the 2026-08-06 mis-anchoring — and replace the quoted body with the scene
headings and their line ranges, pointing into the attached document
(`"Scenes 14, 27 and 31 — headings quoted below — are the subject"`). If a
measurement shows quality drops, the honest fallback is the inverse: send
the anchored scenes **only**, as `scan.py` already does, and drop the full
document for anchored breakdowns. Either way the same text stops being paid
for twice.

**Cost.** Small change.

### F19 — The reference-role block is 41% of the prompt and repeats itself across every panel in a production

**Claim.** The largest block in the prompt is mostly production-constant
boilerplate re-derived per panel.

**Evidence.** Measured (above). The four auto-attached style anchors
contribute their `style_defaults` declarations — `BOARD_RENDERING_STYLE`,
`WORLD_TEXTURE`, `COLOR_PALETTE`, `CINEMATOGRAPHY_STYLE` at
`generate.py:954-979`, ~1,400 characters — byte-identically to **every**
panel prompt in the production, since `auto_style_references()` attaches them
unconditionally. The role-grouping work at `generate.py:1013-1048` is good
and I would keep it; the per-panel-variable part is the subject roles.

I want to be careful here: this is not automatically waste. These are the
declarations that stop a style plate from binding composition, which is the
anti-drift promise made operational. A prompt is not better for being
shorter either.

**Severity.** `TASTE`, stated as taste, with one concrete ask below.

**Proposal.** Not "make it shorter" — measure it. `docs/PROMPT_TEST_2026-08-16.md`
suggests this kind of comparison has been run before; run it on this block.
Render the same panel with the full block and with the four style-anchor
declarations compressed to one sentence each, on the same seed and engine,
and keep whichever holds the anchors. If they tie, the shorter one wins on
cost. If the long form wins, this finding is closed and the measurement is
worth recording in `INTENT.md` beside the cost posture, because the block is
the single largest recurring spend in the render path and it should be there
on evidence rather than on assumption.

**Cost.** Small change to compress; the measurement is the work.

### F20 — The one place the app is too stingy: `MAX_OUTPUT_TOKENS = 8192` on the path that produces the largest JSON

**Claim.** The Anthropic narrative path caps output at 8192 tokens; the
breakdown draft it produces is a full spec plus an evidence ledger with one
cited row per object, which is the app's largest structured output. On
overflow the whole input is paid for and nothing is returned.

**Evidence.** Read code. `narrative.MAX_OUTPUT_TOKENS = 8192`
(`narrative.py:25`), applied at `narrative.py:105`. The Gemini path
(`autofill._draft_gemini`) and the OpenAI path (`_draft_openai`) set no
output ceiling at all, so the cap is unique to Anthropic. The failure mode
is F11: truncated JSON, an unstated 502, and a re-run that re-sends the full
screenplay — so under-spending 8k output tokens costs a full ~33k-token
input pass, and does so on the provider where that input is uncached (F17).
`stop_reason` is never read, so the app cannot even tell the user which
failure it was.

**Severity.** `WORTH FIXING`.

**Proposal.** Raise the ceiling to the model's maximum for the narrative
role and check `stop_reason == "max_tokens"` explicitly, raising a stated
`AutofillError`. This is the inverse case the brief asks about, and it is
clear-cut: images cost far more than text, but so does re-sending a
screenplay, and 8k output tokens is cheap against either.

**Cost.** Small change.

---

## Top 10 in priority order

| # | Finding | Severity | Why here |
|---|---|---|---|
| 1 | **F6** — fabricated citations file as `SCRIPT_EXPLICIT` / `PASS` | BLOCKING | Defeats the product's stated reason to exist, at the one write path where canon reaches disk |
| 2 | **F7** — the citation re-check cannot see those rows | SERIOUS | Turns F6 from a bug into an invisible one; fix them together |
| 3 | **F8** — the render manifest names plates that do not ride | SERIOUS | One fact, two surfaces, disagreeing on the screen where money is spent |
| 4 | **F10** — no server-side stopword list on subject identities | SERIOUS | A cast card named with a common word injects its canon into unrelated panels |
| 5 | **F9** — ten routes with no caller | SERIOUS | The demonstrated failure pattern, unswept; fixing the test closes the class |
| 6 | **F17** — Anthropic path caches nothing while INTENT says it does | SERIOUS | Largest single saving available, and a stated guarantee that does not hold |
| 7 | **F12** — four confirmations promise a lessons list that is never written | SERIOUS | The reassurance that makes `Delete forever` safe to press is half false |
| 8 | **F1** — revisions retired by ruling, still load-bearing, migration unreachable | SERIOUS | Two live answers to one question; the largest deletion available |
| 9 | **F2** — the project-lessons mechanism has never been written to | WORTH FIXING | Dead prompt block, dead dashboard list, always-zero count |
| 10 | **F16** — the three missing skills | WORTH FIXING | Each one would have prevented several rows above at the commit that caused them |

F3, F4, F5, F11, F13, F14, F15, F18, F20 stand as filed. F19 is taste and
should be settled by measurement, not argument.

---

## Where I could be wrong

**F19 (prompt length) is the one I am least confident in**, and I have filed
it as taste for that reason. I have measured the block's *size*, not its
*value*, and the app's history suggests the long form was arrived at by
hitting real failures — `generate.py:1007-1012` records the five-GT40-plates
defect that produced the grouping logic. What would settle it: two renders
of one panel, same seed and engine, long form versus compressed, judged by
the user. I would accept "the long form holds the anchors better" as a
complete answer.

**F1 (remove revisions) is the largest thing I am proposing and the one I
have verified least deeply.** I traced eleven `assemble.py` call sites and
read `revisions.py`'s exports, but I did not walk a real multi-revision
production. If `panel_revision_floor` and `board-keeps` encode a behaviour
that the approval snapshot genuinely cannot express — a board deliberately
mixing takes approved under different specs — then this is not a removal but
a rename, and I would withdraw it. What would settle it: one sentence from
whoever made the 2026-08-16 ruling on whether a board may mix takes from
different revisions on purpose.

**F18 (double-sent anchor)** — I am confident about the duplication and
unconfident about the remedy. Whether the model needs the surrounding
screenplay is an empirical question I cannot answer by reading. If the full
document is load-bearing, my proposal to replace the quoted body with
headings may cost quality to save 1,750 tokens, which is the wrong trade.
What would settle it: run three breakdowns both ways and compare the
evidence ledgers' citation accuracy.

**F5 / F8 share a proposed fix I have not costed against the workbench's
render path.** I am assuming `_resolve_generation_inputs` can be split so
its resolution half runs without side effects. If it cannot — if resolving
requires the disk work that `_render_ready` does — the endpoint is more
expensive than I have said, and the cheaper answer is to have the *generate*
response return the manifest it actually used and render that after the
fact. That is worse (it reports after the spend rather than before) but it
is honest, and I would take it over the current disagreement.

**F10's `normName` half** — I claim the server misses `"Sal's eyes"` and
`"closing cryochamber"`, and I verified both by running
`subjects_for_object`. What I did **not** verify is whether the distinctive-
word rule is *supposed* to refuse `"Sal's eyes"` (two cards share `sal`), in
which case only the hyphen case is a genuine miss and the possessive case is
the documented policy working as intended. `generate.py:773-777` can be read
either way. The stopword half of F10 is not in doubt.

**Things I did not look at**, so that their absence is not read as
approval: `storefront/` beyond the one `preview-render` caller; the arrange
room's interaction code (`renderArrangeRoom`, the largest single unreviewed
surface in the app and already twice-deferred in the uncanonized table);
`sheet_render.py`'s geometry; the backup/restore path; and any judgement of
the app running in a browser — every finding here is from reading code and
running Python against it, never from using the product.
