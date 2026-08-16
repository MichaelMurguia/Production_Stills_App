# RULE_PASS_2026-08-16 — Part C: the sequence surfaces, the film, the ledger

Ten queued rows across stages 03, 04 and 05, plus one app-wide bar. Most are
ratification of work built from a designer spec; three are corrections and
one stays deferred for the second time.

Apply **Part A** first — A5 (the 24px spine), A7 (verb vs tool) and A8
(`SETTLED`) all land here.

---

## C1 — Stage 04 as a six-step sequence · RATIFIED

The reference implementation of the Part 1 vocabulary. All four reported
deviations from mock hier-4a are **ratified as built** — in every case the
build followed canon and the mock did not:

1. **Generate stays a ghost once a take exists**, so `Approve panel` keeps
   the surface's single amber. The mock drew two ambers against §1.3. The
   build is right; the mock was wrong and is superseded.
2. **OFF reference rows read `DID NOT RIDE THE PREVIOUS TAKE`** on a panel
   with takes. §2.3 wins over a mock label that shows a first-take reason in
   a state that cannot have it.
3. **`Read & edit` carries Copy/Download inside the prompt's reading view.**
   Correct — the spec's rail deletion would have taken a shipped feature with
   it. A layout ruling never deletes a capability silently.
4. **Brief and camera verbs lost their ghost boxes to §1.4.** Ratified. This
   reverses the user's 2026-08-13 direction, so it is flagged rather than
   buried: at 11.5px a boxed verb in a row is the footnote problem A7
   describes. If the user wants the boxes back, they come back as **tools in
   a bar**, not as boxes on inline verbs.

Confirmations staying advisory (never gating, §2.4) and living in
per-production UI state is right. Any edit upstream of 05 unconfirming it is
right.

---

## C2 — Stage 03 in the same vocabulary · RATIFIED

Seven steps, one shared `seqStep()` for both surfaces. The transfer is what
proves the vocabulary is a vocabulary, and it worked at close to zero cost.

**The empty frame is canonized as the sanctioned exception** to *never
reserve the shape of the missing thing*, on one condition, now written into
the rule: it earns the exception by **stating the blocker that keeps it
empty**. A reserved shape that says nothing is still forbidden — see **B3**,
where the same principle refuses three dashed cells.

Keeping the slugline fields inside `01 IDENTITY` was right; a guessed
six-step reading would have deleted them.

The approve gate — `n QUESTIONS OPEN AND n STEPS UNCONFIRMED — YOU CAN STILL
APPROVE` — is the model §2.4 wants everywhere.

---

## C3 — The evidence ledger · CORRECTED

**The trigger is the LOCK, not the confirmation.**

The hybrid itself is ratified: selects while drafting, a stated provenance
record once frozen. But a confirmation is *advisory* — §2.4 and C1 both say
it never gates — and a control that loses its affordance when you confirm a
step is a confirmation that gated something. Two rules cannot both be true.

Ship: the ledger reads as a document **when the sheet locks**. Confirming
step 06 changes the step, not the ledger. Editing after the lock goes
through the existing withdraw path.

---

## C4 — The film rolls · RATIFIED

Both the 08-15 rows, ruled together — they are one strip.

- **The 35mm window, the fitted (not cropped) image, the perforated bands.**
  Ratified. The perforations are a hard-stop repeating pattern, which is the
  hatch's own mechanism, not a gradient — no conflict with canon.
- **Letterboxing when every take shares the panel's ratio** — keep the fit.
  The bars are constant today and cost nothing; the first mixed-ratio strip
  makes them load-bearing, and a rule that only works while the data is
  uniform is not a rule.
- **The hidden scrollbar is allowed**, narrowly: drag and wheel both work and
  the strip's contents are visible at rest. **Add arrow-key stepping when the
  strip has focus** — that closes the honesty gap the row identifies, and it
  is the last standard control the strip lacks.
- **The retired edge marking stays retired.** The rule that put OUR data there
  rather than a stock name still stands and applies if it ever returns; two
  lines of height on a strip whose job is pictures is not a trade worth making.
- Thumb-tier loading, full image on click, and a drag swallowing exactly one
  click are all correct.

---

## C5 — A frame may be a way in · RATIFIED, with the difference named

Two frames side by side doing materially different things on click is
acceptable **because the difference is the only thing that distinguishes
them and it is visible**: a filled frame has a picture and zooms it; an empty
frame has no picture and its click becomes the act that resolves the
consequence it states.

A report may be a control **when it has nothing to show**. Where it has
something to show, showing it is the act.

Refusing the click on an unsigned sheet, and stating the gate in the frame
(`approve & lock this breakdown first`), is §2.4 done properly. Per the
2026-08-16 cursor ruling, that frame takes `help`, not `not-allowed`.

---

## C6 — Palettes and plates · RATIFIED, with the manifest moved

- **The composite palette plate** (`app/palette_plate.py`) is ratified. It is
  a rendered artifact a model reads, so it follows the sheet-render/chrome
  split, not app canon — its captions, ordering and hero band are render
  design and are correct as described. A palette costing one of the fourteen
  reference slots however many colours it holds is the right economy.
- **`Choose plates`** and the set-aside (dimmed, greyscale) presentation are
  ratified — unpicked is not deleted, and `3 OF 5` states it.
- **The manifest moves to step 05, beside the prompt it feeds.** The row asks
  where it belongs; it belongs with the thing it becomes. Step 04 keeps its
  count by role (`SUBJECT + PALETTE + STYLE`); step 05 states the full list of
  plates that will ride.

---

## C7 — The stale-tab bar · RATIFIED

Never queued, never ruled, and correct as built. A stale tab means the user
is reading a UI that no longer exists — the bar is right to be persistent
and right to be non-dismissable, because dismissing it would leave someone
working confidently inside a dead build. 60s polling plus `visibilitychange`
is the right cadence; the original navigation-only check was the bug.

No change. Fold it into canon as the app-wide staleness pattern.

---

## C8 — Arrange room physics · DEFERRED AGAIN, and this is now the blocker

Second deferral, same reason, and it is worth naming plainly: **the room has
never been seen.** It was not in the recorded harness bundle, and chip sizes,
ghost-scrim strength, snap values and the claim arrows cannot be ruled from
prose — they are tuned by feel, which is precisely why the user tuned them in
a lab.

Already ruled and holding: **square chips** (canon forbids rounding) and the
**amended R2 reading** (client owns arrangement STRUCTURE, server owns
GEOMETRY).

Still open: chip sizes (40/20/48), ghost-scrim strength, snap values
(24×12 grid + film-ratio), edge-midpoint claim arrows.

**Action:** the row stays in the table and is the first item of the next
recording walk. If the room is not in the next bundle, it should be treated
as un-reviewable and the user told the design queue cannot clear it.
