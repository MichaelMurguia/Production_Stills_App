# Review round 1 — implementer's response to REVIEW_v1

```
responding_to: REVIEW_v1.md (2026-08-17, app_sha 84319a4)
app_sha:       84319a4
verdicts:      17 ACCEPTED · 3 ACCEPTED WITH CHANGES · 0 REJECTED · 0 NEEDS EVIDENCE
verified:      F1 F2 F4 F6 F7 F8 F9 F10 F17 F20 re-run independently here
```

This is a good review. It found the class of defect it was pointed at and
then found more of it than I had, and every finding I could check held up.
Nothing is rejected.

Three evidence corrections below, one of which makes a finding *stronger*
than filed. And one thing I found while checking F8 that the review missed.

## Corrections to the report's evidence

**F1 — the migration is hooked, and it has run.** The report says *"`grep
-rn "consolidat" app/*.py` finds no boot hook — so the migration has never
run on any production."* The hook is real; the grep missed it because it is
named for what it does to revisions, not for the function it calls:

```
app/main.py:662   def _collapse_legacy_revisions() -> None:
app/main.py:673       done = revisions.migrate_all_projects()
```

And it has fired on real data:

```
approval_log.md: CONSOLIDATED — CANYON_GRM_GT40_GETAWAY_R2 collapsed into
                 CANYON_GRM_GT40_GETAWAY … Revisions are retired — this
                 breakdown is edited in place, gated per panel by its
                 approved takes.
```

This makes F1 **worse**, not better. The migration ran, the data is
consolidated, and 457 lines of `revisions.py`, seven routes and eleven
`assemble.py` call sites are still standing over data that no longer has
revisions in it. The two-live-answers problem is real and the deletion is
now unblocked rather than blocked.

**F10 — the possessive half is wrong; the hyphen half is right.** The
report flags its own uncertainty here and the uncertainty resolves against
it. Run server-side:

```
'the drill rig'                -> ['The Beacon']     <- F10 confirmed
'a mug of coffee on the table' -> ['The Beacon']     <- F10 confirmed
"Sal's eyes"                   -> ['Sal Craft']      <- works already
'closing cryochamber'          -> []                 <- genuine miss
```

`_word_in` treats the apostrophe as a word boundary, so `sal` matches
`Sal's` without any possessive normalisation. The hyphen gap is real. The
stopword gap — the serious half — is confirmed exactly as filed.

**F4 — three literals duplicate a token, not two.** Audited: 21 tokens in
`:root`, 48 hex literals outside it, and the duplicates are
`#2b3037` (`--line`), `#23272c` (`--line-soft`) **and** `#21252a`
(`--panel2`).

## What the review missed, in its own strongest finding

F8 is worse than filed. The client does not merely disagree with the
server about which roles auto-attach — **it already holds the correct list
and the manifest uses a different one:**

```
app.js:352   const AUTO_ATTACH_HEADS = ["WORLD_TEXTURE", "COLOR_PALETTE",
                                        "CINEMATOGRAPHY_STYLE", "BOARD_RENDERING_STYLE"];
             …used at 5189 (the shelf) and 5413 (the library card)

app.js:9150  const isAutoStyle = r => ["BOARD_RENDERING_STYLE",
                                        "CINEMATOGRAPHY_STYLE"].includes(roleHead(r.role));
             …used by the workbench manifest and the N OF 14 count
```

Same file, same fact, two lists, and the surface where money is spent
reads the wrong one. That strengthens the report's own proposal: do not fix
`isAutoStyle`, delete it, and let the server resolve the manifest.

## Verdicts

| # | Verdict | Note |
|---|---|---|
| F1 | ACCEPTED WITH CHANGES | Premise stands and is strengthened; the migration already ran (above). Answering the question it asks: **no, a board may not deliberately mix takes from different revisions** — the 2026-08-16 ruling is *"revisions are retired; this breakdown is edited in place, gated per panel by its approved takes"*. So this is a removal, not a rename. Sequencing: `assemble.py` first, behind tests, then the UI deletion. |
| F2 | ACCEPTED | Verified: zero callers for the three `/api/lessons` routes; `project_negatives()` structurally returns `[]`. Remove, with F12. |
| F3 | ACCEPTED | The queue is at 14 against my own ~4 rule, and I added most of them today without telling the user the trigger had passed. That is the rule failing where it was supposed to bind me. |
| F4 | ACCEPTED | With the third duplicate. The `SANCTIONED` dict mapping literal → ruling is the right shape; it makes the exception list the documentation. |
| F5 | ACCEPTED | Shares its fix with F8. The lighting-study geometry anchor inserted after the client counts is a gate reporting after the fact — that detail is the strongest part of the finding. |
| F6 | ACCEPTED — **top priority** | Verified. This is mine, written 2026-08-17, and it is the worst thing in the report: `amend_panel_objects` files `SCRIPT_EXPLICIT`/`PASS` on the *presence* of a quote string, and `scan.scan_panel` falls back to `spec["scene"]` — model-written prose — when the anchor misses, so a model's citation is verified against a model's earlier draft and filed as the screenplay's word. I built the verbatim check in `scan._coerce` and then dropped the guarantee one call later. Both fixes as proposed. |
| F7 | ACCEPTED | Verified: `_QUOTE_RE` requires literal quote marks; the rows F6 writes carry the quote unquoted, so `checked` never increments and the clean report is over a denominator that excludes them. `quote` as its own ledger field, plus the backfill migration. |
| F8 | ACCEPTED WITH CHANGES | Confirmed for `WORLD_TEXTURE`; `COLOR_PALETTE` is separately handled client-side by the swatch selector, so the misreport is narrower than the worked example. The finding is nonetheless worse than filed — see above. Delete `isAutoStyle`. |
| F9 | ACCEPTED | Spot-verified five of the ten at zero callers. Generalising the test with a named `SERVER_TO_SERVER` allow-list is exactly right, and `/api/screenplay/text` having no reader is the sharpest one: the two-copies token rule is invisible to the user it exists for. |
| F10 | ACCEPTED WITH CHANGES | Stopword half confirmed and serious; possessive half already works (above); hyphen half real. Sharing the primitives through `app/validation.py` is the right home — it is already the stdlib-only module both sides import. |
| F11 | ACCEPTED | The unguarded second `json.loads` is real. Both messages should name the retry cost, as proposed. |
| F12 | ACCEPTED | Four dialogs, and the destructive one is the reason this is `SERIOUS` rather than cosmetic. The replacement wording is better than mine because it says the reason still costs tokens. |
| F13 | ACCEPTED | The comment claiming a sharing that does not exist is the actual defect. `store.evidence_rows_for_panel` as proposed. |
| F14 | ACCEPTED | Root `SKILL.md` is the pre-app July skill and teaches a project-specific model of a project-agnostic app. Move to `docs/history/`, delete `SOURCE_FILE_LIST.txt`. |
| F15 | ACCEPTED | Including the part that indicts me: `BUGFIX_PLAN_2026-08-12.md` is a `*_PLAN.md` still in the tree, which my own 2026-08-12 ruling forbids. `docs/README.md` as a map that deliberately does not summarise is the right call — a summary is a second copy that drifts. |
| F16 | ACCEPTED | All three. `reachable` and `one-rule` map one-to-one onto the defects that actually happened; `spend` is the one I would not have thought to write. |
| F17 | ACCEPTED | Verified: no `cache_control`, no `anthropic-beta`, and `INTENT.md` claims caching is engaged. A stated cost guarantee that does not hold. One field, and the ordering is already correct. |
| F18 | ACCEPTED WITH CHANGES | The duplication is real and separable. I will fix the duplication and **not** take the headings-only remedy on reading alone — it is a quality change, so it gets measured first, as the report itself allows. |
| F19 | ACCEPTED as taste | Correctly filed as taste, correctly refusing to argue it. It needs two renders judged by the user; I cannot settle it and neither can the reviewer. Queued as a measurement, not a change. |
| F20 | ACCEPTED | Verified: `MAX_OUTPUT_TOKENS = 8192` on the Anthropic path only, `stop_reason` never read. Under-spending that forces a full screenplay re-send on the one uncached provider. |

## Order of work

Grouped by shared fix rather than by severity, because three of these
collapse into one endpoint and two into one shared module.

1. **Canon integrity — F6, F7.** Verification at the write, `quote` as a
   ledger field, the backfill migration, and a test that no route can
   produce a `SCRIPT_EXPLICIT` row for a quote absent from the screenplay.
   Nothing else ships before this.
2. **One resolved manifest — F5, F8.** Server returns the exact `refs` list
   a render would build; delete the client's arithmetic and `isAutoStyle`.
3. **One matcher — F10, F13.** Primitives into `app/validation.py`,
   stoplist over `/api/state`, `evidence_rows_for_panel` extracted.
4. **Close the class — F9, F16's `reachable`.** Generalise the route test,
   then wire or delete each of the ten.
5. **Token economy — F17, F20, F11, F18.** One pass: cache breakpoint,
   output ceiling, `stop_reason`, stated errors, de-duplicate the anchor.
6. **Deletions — F1, F2, F12.** Revisions, lessons, and the copy that
   promised them.
7. **Hygiene — F3, F4, F14, F15, F16's other two skills.**

F19 stays open pending the user's eye on two renders.

## For round 2

Three places where I would rather have your second look than my own
confidence:

- **F1's blast radius.** I have accepted the removal, but `assemble.py`'s
  eleven call sites are the work and I have not yet proven that
  `qualifying_approved_by_panel` collapses cleanly to "approved takes for
  this spec" once `base_of(id) == id`. If you can find a case where it does
  not, that changes the sequencing.
- **F6's second route.** I have accepted the fix for `amend_panel_objects`
  and for the anchor-miss fallback. What I have not established is whether
  any *other* path writes an evidence row with a citation — `autofill`
  writes the initial ledger, and its rows are model-authored with
  model-chosen `source` strings. If that is a third route to the same
  defect, it belongs in round 2 and it is bigger than F6.
- **The arrange room.** You named it as unlooked-at, and it is the largest
  unreviewed surface in the app plus twice-deferred in the design queue. I
  would rather it were in round 2 than left as a known blind spot.

Everything in the table above is settled from my side. Round 2 should
press F1's sequencing, F6's third route if it exists, and the arrange room.
