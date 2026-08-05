# HATCH_RULE.md — the empty-image pattern is a class, never a re-declaration

**For the coding agent.** One small canon amendment, prompted by a mock that
hand-rolled the pattern and got it wrong. No UI work unless the audit in H2
finds drift.

## H1 — Add to `DESIGN_SYSTEM.md` → Components

> **The hatch is the only empty-image surface.** Wherever an image is
> expected and absent — panel slots, take thumbs, board frames, reference
> rows, the storefront's workspace-door preview — the surface is one of the
> three canonical classes, never an inline gradient:
>
> | class | pattern | use |
> |---|---|---|
> | `.hatch` | `repeating-linear-gradient(135deg, #21252a 0 7px, #1c1f23 7px 14px)` | blocks ≥ 60px |
> | `.hatch-fine` | same at 5px/10px | thumbs < 60px |
> | `.hatch-bad` | `#211b1b`/`#1b1717` at 7px | TOO-SMALL and error surfaces |
>
> Always **135°**, always two near-equal thick bands — not hairlines, not
> 45°. Re-declaring the gradient inline is a conformance failure even when
> the values match, because the next hand-copy is where they stop matching.
> A hatch block states its condition in a bordered Courier chip on `--panel`
> in `--ink-dim` (`NO RENDERS YET — THE FIRST APPROVED PANEL LANDS HERE`);
> it never renders bare and never shows a broken-image glyph.

Changelog it.

## H2 — Audit

`grep -n "repeating-linear-gradient" app/static/ storefront/` — every hit
outside the three class definitions in `styles.css` is drift. Replace with
the class. Report anything that needed a fourth variant rather than
inventing one.

## H3 — For the storefront

`storefront/` has its own stylesheet, so it needs its own copy of the three
definitions with **identical values**, marked as mirrored from
`app/static/styles.css` and listed in the token test so the two cannot drift
apart silently.

Delete this file when H1–H3 are done.
