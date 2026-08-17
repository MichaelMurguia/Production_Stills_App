# REVIEW_v2 — Screenboard Studio

```
version:    2
date:       2026-08-17
app_sha:    84db4d9
answering:  docs/REVIEW_ROUND_1.md (17 ACCEPTED · 3 ACCEPTED WITH CHANGES · 0 REJECTED)
read:       app/autofill.py (_coerce, _instructions), app/revisions.py (in full),
            app/main.py:655-690, app/static/app.js:11967-12400 (the arrange room),
            tests/test_subject_identity_match.py, app/static/styles.css
ran:        app.revisions.qualifying_approved_by_panel() on a consolidated unit
            app.generate.subjects_for_object() on the production's real cast shape
            a transliteration of app.js winFor + both SHORT tests over 15 slot cases
            a comment-stripped hex audit of app/static/styles.css
```

## Contents

- [Settled — dropped from this round](#settled--dropped-from-this-round)
- [Your three evidence corrections](#your-three-evidence-corrections) — two stand, one does not
- [Your three asks for round 2](#your-three-asks-for-round-2) — F21, F22, F23
- [Still pressed](#still-pressed) — F10, F24
- [Revised order of work](#revised-order-of-work)
- [Where I could be wrong](#where-i-could-be-wrong)

---

## Settled — dropped from this round

F2, F3, F5, F7, F8, F9, F11, F12, F13, F14, F15, F16, F17, F18, F19, F20 are
accepted with no change I want to argue, and I have nothing to add to them.
They are not repeated here; `REVIEW_v1.md` remains their statement.

Two notes and then they are closed:

- **F8** — your catch is better than my finding. `AUTO_ATTACH_HEADS`
  (`app.js:352`, correct four roles, used at 5189 and 5413) sitting in the
  same file as `isAutoStyle` (`app.js:9150`, wrong two, used by the
  manifest) is the sharper statement of it. Verified. Delete `isAutoStyle`.
- **F19** stays taste and stays yours to measure. Nothing further from me.

F1 and F6 both grow, below.

---

## Your three evidence corrections

### F1's migration hook — **you are right, and I was wrong**

`main.py:662 _collapse_legacy_revisions` → `revisions.migrate_all_projects()`
(`revisions.py:419`) is a real startup hook and my grep for `consolidat`
missed it because the caller is named for the effect. Correction accepted,
and your reading of the consequence is right: F1 is stronger, not weaker.
The deletion is unblocked.

One thing this changes that you did not name — see **F23**.

### F4's third duplicate — **you are right; here is the settled count**

We reported 46 and 48 hex literals; both were wrong, because neither of us
stripped comments before counting and `styles.css` quotes hex values in
prose. Comment-stripped:

```
tokens in :root ......... 21
hex occurrences outside .. 44
distinct values .......... 29

literals that duplicate an existing token:
  #21252a  = --panel2     (3 occurrences)
  #23272c  = --line-soft  (1 occurrence)
  #2b3037  = --line       (1 occurrence)
```

Your three duplicates confirmed, and `--panel2` is duplicated three times
(`styles.css:1405`, `1447`, `1448` — the hatch band pairs), not once. Note
for the `SANCTIONED` dict: the hatch ruling sanctions the *tone*, not the
*hardcoding*, so those three become `var(--panel2)` and the ruling still
holds. Use 44/29 as the baseline the new test asserts against.

### F10's possessive half — **your correction does not survive**

You wrote: *"`_word_in` treats the apostrophe as a word boundary, so `sal`
matches `Sal's` without any possessive normalisation"*, and reported
`"Sal's eyes" -> ['Sal Craft']`.

The statement about `_word_in` is true. The outcome is not, on the cast the
bug was reported against. Ran:

```python
CAST = [{'name': 'SAL CRAFT',          'traits': ['Mid-40s']},
        {'name': "SAL'S CRYO-CHAMBER", 'traits': ['frosted']}]

"Sal's eyes"          -> []                        # not ['Sal Craft']
'closing cryochamber' -> []                        # hyphen gap, as agreed
'closing cryo-chamber'-> ["SAL'S CRYO-CHAMBER"]    # matches only when hyphenated
```

`_word_in` never gets the chance. `_name_words("SAL'S CRYO-CHAMBER")` is
`['sal', 'cryo', 'chamber']`, so `counts['sal'] == 2`, and the
distinctiveness rule at `generate.py:793` refuses before the apostrophe
matters.

**Why your run disagreed:** `tests/test_subject_identity_match.py`'s `CAST`
contains `CRYOCHAMBER`, not `SAL'S CRYO-CHAMBER`. The fixture is missing the
one card that collides — which is also why the suite is green on a case the
user caught in the field. `app.js:665-667` names both cards explicitly and
records the user catching exactly this on 2026-08-16:

> *"'Sal's eyes' matched nothing because 'sal' is shared by SAL CRAFT and
> SAL'S CRYO-CHAMBER, which are a person and his prop, not two people
> (user-caught 2026-08-16)."*

So this is not policy working as designed. The client was fixed for this
case; the server was not; and `generate.py:760-763` calls the server copy
*"the more damaging one"* to miss, because a missing identity renders a
stranger's face. **F10 stands in full, all three halves** — stopword,
possessive and hyphen — and the fixture gains `SAL'S CRYO-CHAMBER` in the
same commit, or the regression comes straight back.

---

## Your three asks for round 2

### F21 — `autofill` is the third route, it is the primary one, and it is bigger than F6

**Claim.** Every evidence row in every breakdown is written from model
output with the model's chosen `evidence_class`, the model's chosen `status`
and the model's chosen `source` string, and the citation is never checked
against the screenplay. The one guard that exists protects the class that
cannot be checked and leaves unchecked the only class that can.

**Evidence.** Read `autofill._coerce` (`autofill.py:274-299`). The guards:

```python
if ec not in EVIDENCE_CLASSES:                      # enum check only
    ec, status = "WEAK_INFERENCE", "HOLD"
if ec in {"WEAK_INFERENCE", "PROPOSED_NOT_CANON"} and status == "PASS":
    status = "HOLD"      # "the user, not the model, promotes weak evidence"
```

then

```python
"evidence_class": ec,                               # model's, verbatim
"source": str(row.get("source", ""))[:500],         # model's, truncated, unverified
"status": status,                                   # model's, guarded only as above
```

The demotion rule is deliberate and good. But look at what it covers. A row
the model labels `WEAK_INFERENCE` cannot self-promote to `PASS` — correct.
A row the model labels **`SCRIPT_EXPLICIT`** goes straight to `PASS` with no
human decision and no check, and `SCRIPT_EXPLICIT` is the *only* class that
makes a falsifiable claim: it asserts a verbatim line exists in a document
the server is holding. `_instructions` asks for `"source": "exact quote or
scene citation from the screenplay"` (`autofill.py:203`) and nothing ever
opens the screenplay to look.

So the app **verifies the class it cannot check and skips the class it
can**, and the incentive runs the wrong way: classifying strongly is the
route to a row that needs no human.

Three consequences, all following from code I read:

1. **The lock gate is satisfied by unverified rows.** `validate_spec`
   requires PASS coverage for every required object; these rows supply it.
2. **The `CANON_EXTRACTION` weak-inference budget is bypassed, not spent.**
   The ≤2 cap counts weak inferences. A generous `SCRIPT_EXPLICIT` costs
   nothing against it.
3. **F7 makes the coverage non-deterministic.** `insights._QUOTE_RE`
   only inspects `source` text inside `"…"`. The model chooses whether to
   quote. So whether any given row of the primary ledger is ever re-checked
   is decided, per row, by the model's punctuation.

**Severity.** `BLOCKING`, and it supersedes F6 as the top of the list. F6 is
one amendment path added on 2026-08-17. F21 is every row of every breakdown
since the feature existed. INTENT conviction 1 — *"Canon is extracted, never
invented… Every claim must cite its screenplay evidence"* — is enforced
nowhere on the path that writes almost all of the claims.

**Proposal.** You already wrote the routine; it is in the wrong module.
`scan._coerce` (`scan.py:117-136`) verifies a claimed quote against the text
actually sent, drops what it cannot prove rather than demoting it, and
counts the drops on screen. Apply the same three lines in
`autofill._coerce`, against `store.screenplay_text_cached()` with
`insights._norm`/`_squash` normalisation:

- `SCRIPT_EXPLICIT` whose `source` quote is not found → demote to
  `STRONG_INFERENCE` / `HOLD` and keep the model's text as `rationale`.
  Demote rather than drop here: unlike `scan`, this row is the only record
  that an object was proposed at all, and dropping it would silently shrink
  the ledger the user is about to review.
- Count the demotions and surface them on the breakdown as
  `N OF M CITATIONS COULD NOT BE FOUND IN THE SCREENPLAY` — a fact the
  reviewer needs before they approve, and the number that tells you whether
  the narrative model is worth its price.
- With F7's `quote` field, this check and `citation_check` become the same
  predicate at two times. Extract it once (`insights.quote_is_in_screenplay`)
  and call it from `autofill._coerce`, `scan._coerce`,
  `store.amend_panel_objects` and `citation_check`. That is four call sites
  for one question — exactly the `one-rule` skill's case, and worth building
  the skill on.

**Cost.** Small change for the check; the surfacing is a small UI addition.

**Note on scope.** This does not make the model's *judgement* trustworthy
and I am not claiming it does — a real quote can still support a wrong
object, which is what the human ledger review is for. It makes the
*provenance* checkable, which is the promise the evidence classes actually
make.

### F22 — the arrange room's two advisory SHORT readouts disagree, and the one shown during the gesture is the optimistic one

**Claim.** The room computes "does this take fill this slot" twice on the
client, with different rules, and the readout the user reads *while
dragging* under-reports SHORT.

**Evidence.** Ran a transliteration of the room's own code over 15 slot
cases. The two tests:

```js
app.js:12309  // tile verdict, painted on release
const short = t && t.w && (pw > availW + 1 || ph > availH + 1);
              // availW/availH = winFor(crop, …) — the CROPPED window

app.js:12372  // drag HUD, painted continuously during the gesture
const short = t && t.w && (pw > t.w || ph > t.h);
              // t.w/t.h = the FULL take, crop ignored
```

Take 3840×2160, `winFor` transliterated exactly (`app.js:12018`):

```
crop       slot         tile verdict (12309)   drag HUD (12372)   agree
no crop    2600x2600    SHORT (2160x2160)      SHORT              yes
crop 50%   2000x2000    SHORT (1920x1920)      OK                 NO
crop 50%   2400x1600    SHORT (1920x1280)      OK                 NO
crop 50%   3000x1400    SHORT (2314x1080)      OK                 NO
crop 60%   2400x1600    SHORT (2304x1536)      OK                 NO
crop 60%   3000x1400    SHORT (2777x1296)      OK                 NO

disagreements: 5 of 15 — every one in the same direction
```

The HUD is never pessimistic and the tile is never wrong; the failure is
one-directional. A user drags a cropped panel, reads `OK` in the HUD, lets
go, and the tile flips to `SHORT`. There is a third computation behind both
— the server's `readiness` (`/api/sheets/{id}/readiness`), which is what
actually gates export — so this is three implementations of one question,
in the room the design queue has deferred twice.

**Severity.** `SERIOUS`. The no-upscale rule is the product's most-stated
promise, and this is the surface where the user chooses geometry against it.
`DESIGN_SYSTEM.md` canon R2 — *"Geometry is computed once and declared…
Two implementations of one geometry is a drift bug with a permanent
maintenance cost"* — already forbids exactly this, and the room is the place
that rule was written for.

**Proposal.** `hudFor` should call the same expression the tile does. Concretely:
extract one `shortFor(pid, r)` returning `{pw, ph, availW, availH, short}`
and have `layout()` and `hudFor()` both render from it — the HUD then also
gains the `PLATE SHOWS availW × availH` number, which is the actionable half
it currently lacks. This does not touch the client/server question in the
uncanonized table's open item 7; it removes a disagreement that exists
entirely inside the client and does not need a designer to rule on it.

**Cost.** Small change.

### F23 — F1's real precondition is not "the migration ran", it is "the migration ran with zero skips", and nothing can tell you that

**Claim.** `migrate_all_projects` swallows per-chain failures to a log
nothing reads, so a chain that did not collapse is invisible — and deleting
`revisions.py` over it would silently change which takes a board uses.

**Evidence.** Read `revisions.py:447-454`:

```python
try:
    r = consolidate(b)
    …
except Exception as e:            # noqa: BLE001 — boot must survive
    store.append_approval_log(
        f"BOARD {b}: CONSOLIDATION SKIPPED — {e} "
        "(the chain stays split; nothing was moved).")
```

`grep -rn "CONSOLIDATION SKIPPED" app/ app/static/` returns the write site
and nothing else. `insights.blocking()` does not know the string;
`main.py:676-678` prints only the *successes* (`for r in done:`), so a boot
with three collapses and one skip prints three lines and looks clean. The
docstring names the realistic cause — *"a take id colliding across
revisions"* — which is precisely the case where the surviving take pool
would change under a naive read.

**Also answering your ask directly: yes, the collapse is clean.** Ran
`qualifying_approved_by_panel` on a consolidated unit (`BOARD_A`, no `_Rn`
siblings, three approved takes across two panels):

```
revisions_of('BOARD_A')  : ['BOARD_A']
revision_of('BOARD_A')   : 1
panel_revision_floor P01 : 1
qualifying               : {'P01': 'CAND-004', 'P02': 'CAND-002'}
offered (below floor)    : {}

naive "newest approved CAND- take per panel": {'P01': 'CAND-004', 'P02': 'CAND-002'}
IDENTICAL: True
```

Post-migration the floor is always 1, `offered` is always empty, and the
keeps registry is inert. `qualifying_approved_by_panel` reduces to the naive
read with no residue. So `assemble.py`'s eleven call sites collapse cleanly
and your sequencing holds — **conditional on there being no skipped chain.**

**Severity.** `WORTH FIXING` on its own; it is a `BLOCKING` precondition on
F1's deletion.

**Proposal.** Before any deletion lands: have `migrate_all_projects` return
skips alongside `done`, print them at boot as loudly as the successes, and
add a `CARE` advisory row in `insights.blocking()` naming the chain and the
reason. Then F1 proceeds when that count is zero across the fleet. If a skip
is ever found, the honest fix is to make `consolidate` renumber colliding
take ids rather than to keep the revision machinery alive for one board.

**Cost.** Small change, and it gates a refactor.

---

## Still pressed

**F10** — see the corrections section. Stands in full, all three halves,
plus the fixture gap that let the suite pass.

### F24 — the arrange room's `SLOT_OFFERED` gate row and its `Keep` button are already unreachable

**Claim.** F1's UI deletion is larger than `Create revision`: a gate row and
a user-facing act in the arrange room can no longer fire on any migrated
production, and still render.

**Evidence.** Read code, following the F23 proof. `app.js:12324-12325`
renders a gate row for `b.kind === "SLOT_OFFERED"`, reading
`"…was approved against R{from_revision} and the panel changed in R{floor} —
re-render on the workbench or [Keep] it"`, whose button PUTs to
`/api/specs/{base}/board-keeps/{panel}` (`app.js:12340`). `SLOT_OFFERED`
derives from `qualifying_approved_by_panel`'s `offered` map, which I proved
above is `{}` for every consolidated unit. So on migrated data the row is
dead, the `Keep` verb is dead, and both `board-keeps` routes are dead —
though the routes have callers, which is why my F9 sweep did not catch them.
A route with a caller that can never fire is the same defect one layer down.

**Severity.** `WORTH FIXING`, and it belongs to F1's commit.

**Proposal.** Delete `SLOT_OFFERED`, the `Keep` act, both `board-keeps`
routes, `load_keeps`/`_keeps_path` and the `keeps.json` registry with the
rest of revisions. Worth adding to the `reachable` skill's checklist: the
sweep should ask not only *is there a caller* but *can the branch that calls
it still be reached*, because the second question is the one that catches
mechanisms retired by a ruling rather than by a deletion.

**Cost.** Small change; folds into F1.

---

## Revised order of work

Your order was right. Three edits:

1. **Canon integrity — F21 first, then F6, F7.** F21 is the same fix one
   module upstream and covers vastly more rows. Doing F6 first ships a
   guarantee on the amendment path while the primary path stays open, which
   is the harder story to explain later. One shared
   `insights.quote_is_in_screenplay` serves all four call sites.
2. **F23 before F1.** Skip visibility is a small change and it is the
   precondition for a refactor you cannot easily reverse. F24 rides F1.
3. **F22 into step 2** (*One resolved manifest*) rather than into hygiene —
   it is the same class as F5/F8, it is entirely client-side, and it does
   not need the design ruling the rest of the arrange room is waiting on.

Everything else stands as you sequenced it.

---

## Where I could be wrong

**F21's demote-don't-drop choice is a judgement I am making from outside the
product.** I am proposing that an unverifiable `SCRIPT_EXPLICIT` becomes
`STRONG_INFERENCE`/`HOLD` rather than vanishing, because the row is the only
record the object was proposed. But `STRONG_INFERENCE` is a real class with
a real meaning, and writing it onto a row whose actual status is "the model
said so and could not show it" may be its own small lie — `WEAK_INFERENCE`
would be truer and would spend the `CANON_EXTRACTION` budget the row
arguably should spend. I do not know which the user wants. That choice is
yours or theirs, not mine; the *checking* is not in doubt.

**F21 assumes `citation_check` is the only other verification.** I traced
`_QUOTE_RE` and the four `source` writers, but I did not read
`scripts/validation.py` — `grep` found no `validate_spec` there and I did
not chase where it actually lives. If `validate_spec` or `audit_spec`
already re-reads citations at lock time, F21 is narrower than I have filed
it: still a gap between draft and lock, but not an unchecked path to a
locked sheet. **This is the single thing I would most like you to check
before accepting F21 at BLOCKING.** One command settles it: does anything in
the lock path open `screenplay_text_cached()`?

**F22's numbers are a transliteration, not the running app.** I ported
`winFor` and both `short` expressions into Python and ran them; I did not
open the arrange room in a browser. If `hudFor` is called somewhere that
passes an already-cropped `t`, the divergence is smaller than five in
fifteen. The two expressions differing on their face is not in doubt — one
reads `availW`, the other reads `t.w` — but the frequency is derived.

**F23's skip path may never have fired.** I proved nothing surfaces a skip;
I did not prove any skip exists. If the fleet's `approval_log.md` files
contain no `CONSOLIDATION SKIPPED` line, F23 is a guard against a hazard
rather than a live defect, and it drops from BLOCKING-precondition to
cheap insurance. `grep -rl "CONSOLIDATION SKIPPED"` across the tenants
settles it in one command, and you can run that and I cannot.

**Unchanged from v1:** I have still never used the product. Every finding in
both rounds comes from reading code and running Python against it. The
arrange room's *interaction* — the drag, the claim arrows, the split-docking
— remains unreviewed by me; F22 is one arithmetic defect inside it, not a
review of it.
