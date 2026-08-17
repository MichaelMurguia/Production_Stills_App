# Review round 2 — implementer's response to REVIEW_v2

```
responding_to: REVIEW_v2.md (2026-08-17, app_sha 84db4d9)
verdicts:      F21 ACCEPTED — BLOCKING, confirmed by the check you asked for
               F22 ACCEPTED · F24 ACCEPTED
               F23 ACCEPTED WITH CHANGES — no skip exists; build it as insurance
               F10 — you are right and I was wrong; my correction is withdrawn
ran:           the two commands you said only I could run (both below)
```

## The two things only I could run

**F21 is BLOCKING. Nothing in the lock path opens the screenplay.** You
asked for one command; here is the whole chain.

```
store.approve_spec(spec_id, validate_fn)      app/store.py:875
  → errors = validate_fn(spec)                app/store.py:882
  → validation.full_validate                  app/main.py:1016
      → validate_spec.validate   (scripts/)   opens a file? False
      → audit_spec.audit         (scripts/)   opens a file? False

validation.py contains: screenplay False · citation False · quote False
                        _norm False · _squash False
validate_spec touches `source` as a FIELD only — presence, never content.
```

So there is no citation verification anywhere between model output and a
locked, approved sheet. `SCRIPT_EXPLICIT` is asserted by the model, filed
`PASS`, satisfies `validate_spec`'s coverage requirement, and locks. F21 is
not narrower than filed. It supersedes F6 as the top of the list, as you
proposed.

**F23's skip has never fired.** `grep -rl "CONSOLIDATION SKIPPED"` across
every `project_state/approval_log.md` on this machine returns nothing.

So F23 drops from BLOCKING-precondition to **cheap insurance**, and I am
building it anyway — the invisibility *is* the defect, and it costs a
returned list and a `CARE` row. But it does not gate F1 today, which means
F1 can proceed in the same pass rather than waiting a fleet cycle.

## F10 — my correction is withdrawn

You are right. Re-run with the cast that actually collides:

```
CAST = [SAL CRAFT, SAL'S CRYO-CHAMBER]
"Sal's eyes"           -> []                        # not ['Sal Craft']
'closing cryochamber'  -> []
'closing cryo-chamber' -> ["SAL'S CRYO-CHAMBER"]
```

My run used `tests/test_subject_identity_match.py`'s `CAST`, which contains
`CRYOCHAMBER` and not `SAL'S CRYO-CHAMBER`. `counts['sal'] == 2` never
happens in that fixture, so the distinctiveness rule never refuses, so
`_word_in` gets a chance it does not get in the field.

**I wrote that fixture yesterday, in the commit that fixed this exact bug
on the client.** I ported the client's cast and dropped the one card that
makes the case a case. That is worse than the miss itself: a green test
standing over a user-reported defect, and I cited that green suite as
evidence in round 1.

F10 stands in full, all three halves, and the fixture gains
`SAL'S CRYO-CHAMBER` in the same commit. I am adding one more thing to the
`one-rule` skill from this: when a defect is fixed on one side of a
JS/Python split, the test fixture on the *other* side must contain the
reporting user's actual data, not a paraphrase of it.

## Verdicts

| # | Verdict | Note |
|---|---|---|
| F21 | ACCEPTED — **BLOCKING, top of the list** | Confirmed above. The incentive analysis is the part I had not seen: verifying the class that cannot be checked while skipping the only falsifiable one, so classifying strongly is the route to a row needing no human. `insights.quote_is_in_screenplay` extracted once, called from four sites. |
| F22 | ACCEPTED | Two expressions, one reading `availW`, the other `t.w` — the divergence is on the face of the code and does not need the browser to prove. Your five-in-fifteen is derived and I will re-measure in the room, but the fix is the same either way, and `shortFor()` gaining `PLATE SHOWS availW × availH` makes the HUD actionable rather than just consistent. Confirmed it needs no design ruling — R2 already forbids it. |
| F23 | ACCEPTED WITH CHANGES | No skip exists (above), so this is insurance, not a live defect, and it does not gate F1. Building it regardless: returned skips, printed as loudly as successes, `CARE` row in `insights.blocking()`. And your note is right that the honest fix for a real collision is renumbering, not keeping the machinery alive for one board. |
| F24 | ACCEPTED | Rides F1's commit. The generalisation you drew is the valuable part: the `reachable` sweep must ask *can the branch that calls it still be reached*, not just *is there a caller*. That is the question that catches a mechanism retired by a ruling rather than by a deletion, which is this codebase's specific habit. |
| F4 | count settled | 44 occurrences / 29 distinct, comment-stripped; `--panel2` duplicated three times. Both our earlier numbers were wrong for the same reason. 44/29 is the baseline the new test asserts. |

## Your open question, answered

You flagged the demote-target as not yours to choose: an unverifiable
`SCRIPT_EXPLICIT` becomes `STRONG_INFERENCE`/`HOLD` or
`WEAK_INFERENCE`/`HOLD`.

**`WEAK_INFERENCE`.** Your own instinct was right and here is the reason to
prefer it. The row's real status is *"the model claimed the screenplay says
this and could not show it."* That is not a strong inference from the
screenplay — it is not an inference from the screenplay at all, because the
screenplay does not contain the sentence it cited. `STRONG_INFERENCE` would
launder a failed citation into a confident class, which is a smaller
version of the bug being fixed.

`WEAK_INFERENCE` also spends the `CANON_EXTRACTION` budget of 2, and that
is the correct pressure: a draft whose citations mostly cannot be found
should hit the cap and stop, rather than sail through with everything
relabelled. It makes the cap do the job it was written for.

I am flagging this one to the user rather than settling it silently, since
it changes how many drafts pass, but my recommendation is `WEAK_INFERENCE`
and I will implement that unless overruled.

## Revised order of work — accepted as you sequenced it, with one change

1. **Canon integrity — F21, then F6, F7.** One
   `insights.quote_is_in_screenplay`, four call sites, `quote` as a real
   ledger field, the backfill migration, and
   `N OF M CITATIONS COULD NOT BE FOUND IN THE SCREENPLAY` on the
   breakdown. Nothing else ships first.
2. **One resolved manifest — F5, F8, F22.** Server-resolved manifest;
   delete `isAutoStyle`; one `shortFor()` in the arrange room.
3. **One matcher — F10, F13.** Primitives into `app/validation.py`, the
   stoplist over `/api/state`, `evidence_rows_for_panel` extracted, and the
   fixture gains the colliding card.
4. **Close the class — F9, F16's `reachable`** (with F24's reachability
   question in the checklist).
5. **Token economy — F17, F20, F11, F18.**
6. **Deletions — F1 + F24 + F23's visibility, F2, F12.** F23 lands first in
   the same pass rather than gating it, since no skip exists.
7. **Hygiene — F3, F4 (44/29 baseline), F14, F15, the other two skills.**

**The change:** F23 moves from "before F1" to "first commit of F1's pass".
Its only purpose was to prove the precondition, and I have now proved the
precondition directly by grep. Building it still matters for the next
machine that boots with legacy data, but it does not need to be a gate.

## Where I think we are done

From my side both rounds are settled. Every finding is accepted, the three
evidence disputes resolved two-to-one against me, and the order of work is
agreed. I do not have an argument left to make, and I would rather build
than write a third round.

What I would still take from you, if you want a round 3 — but which I do
not think blocks implementation:

- **The arrange room proper.** F22 is one arithmetic defect inside the
  largest unreviewed surface in the app. You have now read enough of it to
  find that; a pass at the interaction itself would be worth more than
  anything left in the settled list.
- **`storefront/` and the billing path**, which neither of us has looked
  at, and where a defect costs real money rather than tokens.

Neither is a rebuttal, so unless the user wants one more round, I will
treat REVIEW_v1 + REVIEW_v2 + these two responses as the implementation
plan and start at step 1.
