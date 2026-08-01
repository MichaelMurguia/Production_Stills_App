# CLEANUP_PLANS.md — retire the applied design docs

**For the coding agent.** Housekeeping, no code changes. Every file below was
a one-shot instruction that has been applied; each said to delete itself when
done and none did. They now make it impossible to tell at a glance what is
actually pending. Do this in one commit.

## Delete — applied and confirmed in the code

```
IMPLEMENTATION_PLAN.md              v3 — C1–C15, shipped
DESIGN_REVIEW_2026-07-30.md         intake row / registry rows / reading view
DESIGN_REVIEW_2026-07-30b.md        vocabulary picker
DESIGN_REVIEW_2026-07-30c.md        hatch, pending tiles, finder list, lock strip
HATCH_CORRECTION_2026-07-30.md      superseded the hatch spec above
SCROLLBAR_AMENDMENT.md              scrollbar treatment
ONE_LIBRARY_PLAN.md                 D1–D6, REFERENCE restructure
READ_REVEAL_PLAN.md                 R1–R4, the read reveal
PRODUCTION_DESIGN_PLAN.md           P1–P9, stage 02
EXTRACTION_GAPS.md                  the ask
EXTRACTION_GAPS_RESPONSE.md         the reply
EXTRACTION_GAPS_APPROVED.md         the rulings — all three now in the code
DESIGN_DISCREPANCY_REPORT.md        superseded by plan v3
DESIGN_HANDOFF.md                   superseded by plan v3
MANAGE_PROJECTS_HANDOFF.md          (in design_handoff/) answered by PRODUCTIONS_PLAN.md
```

Before deleting each one, confirm its rulings are reflected in
`app/static/DESIGN_SYSTEM.md`. If any ruling lives **only** in the plan file,
move it into the design system first — the design system is the permanent
record, plans are disposable.

## Also delete — stale handoff zips

Everything in `design_handoff/*.zip`. They are snapshots of packages already
extracted and committed. Keep `design_handoff/FEATURE_INVENTORY.md` and any
screenshot referenced by a live plan.

## Keep — still pending

```
PRODUCTIONS_PLAN.md          M1–M7, not started
ICON_RULING.md               not started
CLEANUP_PLANS.md             this file — delete it last
STORE_HOMEPAGE_PLAN.md       S1–S6, check status before deleting
STORE_PIPELINE_PLAN.md       P1–P3, check status before deleting
STORE_DESIGN_BRIEF.md        the original brief; keep for reference
```

## Keep permanently

```
app/static/DESIGN_SYSTEM.md   the product contract
STORE_DESIGN_SYSTEM.md        the storefront contract
CLAUDE.md · APP_GUIDE.md · MANIFEST.md · README.md · INSTALL.md · SKILL.md
docs/** · design_mocks/**
```

## The standing rule

A plan file is a work order, not documentation. When its tasks are committed,
its rulings belong in `DESIGN_SYSTEM.md` and the file goes. The repo root
should only ever hold plans that are **not yet done** — that is how the next
person (or the next session) knows what is outstanding without reading
fifteen files.

Delete this file once the above is done.
