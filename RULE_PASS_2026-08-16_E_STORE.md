# RULE_PASS_2026-08-16 — Part E: the store queue

Two rows in `STORE_DESIGN_SYSTEM.md` → `## Non-canon — awaiting review`.
Under the ~4 threshold, ruled here because the pass is clearing everything.
Implements against **STORE_DESIGN_SYSTEM.md**, never the app's.

---

## E1 — Fleet storage table · KEEP THE TABLE, FIX THE WORD

**A table is right.** A fleet is a set, and the operator's question is
comparative — who is worst, and how much worse than the rest. Collapsing a
healthy fleet to one line optimises for the day nothing is wrong, which is
the day nobody opens the page. Worst-first sorting already does the work
that collapsing would.

**Add one line above it** stating the fleet's worst state in a sentence, so
the page answers the question before the table is read. The table stays
whole beneath it.

**`UNREACHABLE` is the wrong word** for a studio that answers but cannot
measure itself — that studio is up, and calling it unreachable sends an
operator to look for a dead host. Split it:

- `UNREACHABLE` — no answer at all.
- `CANNOT MEASURE` — answers, but returns no figure.

Both stay uncoloured; only `REFUSING` carries `--bad`, which is correct and
matches the app's scarcity instinct without borrowing its rule.

---

## E2 — Responsive marketing imagery · RATIFIED

Pure infrastructure, no visual change, correctly logged anyway.

The display widths are right for the surfaces as built (≈380px wall cells,
≈150px marquee height). The JPEG social card is acceptable — a purpose-cropped
1200×630 is a *decision*, not a fallback, and share surfaces re-encode
anything they are given.

One standing note, not a blocker: the moment the wall's cell size changes,
the `sizes` hints are wrong and nothing will fail loudly. Keep the widths in
`scripts/build_images.py` next to the layout constant they mirror, or state
the dependency in a comment on both sides.
