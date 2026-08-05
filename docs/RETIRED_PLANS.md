# Retired design plans — the ledger

The design chat's folder sync can resurrect plan files that were already
implemented and deleted (it has, twice — once as untracked files, once as
a commit). **Before implementing ANY `*_PLAN.md` / `*_SNIPPET.html` /
process file, check it against this ledger.** If it's listed, it's done:
delete it again, note the resurrection in the commit, and touch nothing
else. If a resurrected file DIFFERS from what shipped, treat only the
delta as new instructions.

| Plan / file | Implemented | Superseded by |
|---|---|---|
| PRODUCTIONS_PLAN.md (M1–M7 + C1/C2) | ≤ 2026.08.01 releases | — |
| CLEANUP_PLANS.md | ≤ 2026.08.01 | — |
| STORE_ROUTER_PLAN.md (T1–T4) | ≤ 2026.08.01 | rename forwarding (.55 era) |
| LOCKED_STAGE_PLAN.md (L1–L4) | ≤ 2026.08.01 | — |
| STORE_PIPELINE_PLAN.md | ≤ 2026.08.01 | — |
| CONNECTORS_PLAN / CONNECTORS_UI_PLAN (C1–C9) | 2026.08.03.40 | F-plan header renames |
| SETTINGS_FIRST_RUN_PLAN.md (F1–F7) | 2026.08.03.42; F6 backend 2026.08.04.43 | marquee snippet (.52), notice snippet (.53), Authenticate connector grammar (.48). **Resurrected + committed 2026-08-03, retired again** |
| PANEL_CARD_PLAN.md (P1–P9) | 2026.08.03.38 | — |
| MOCK_PARITY_PROCESS.md (D1–D8 + loop) | 2026.08.04.46; loop canonized | executable form: `.claude/skills/design-verify/` |
| PROVIDER_MARQUEE_SNIPPET.html | 2026.08.04.52 | — |
| AI_MODELS_NOTICE_SNIPPET.html | 2026.08.04.53 | — |
| design_handoff/CANONIZATION_PASS.md (R1–R19) | 2026.08.04.57 | — (emptied the Uncanonized table) |
| BAND_CONDENSE_PLAN.md (B1–B3) + BAND_CONDENSE_SNIPPET.html | 2026.08.04.58 | — |
| SETTINGS_CONTROL_PANEL_PLAN.md (P1–P4) | 2026.08.04.60 | mock 18b adopted; 18a re-export (marquee developer names) applied; brand-icon rule app-wide (P3) |
| PRODUCTION_DESIGN_V3_PLAN.md (D1–D6, D8, D9) | 2026.08.04.64 | D7 preset looks pending the plate library (plan file trimmed to D7; PRESET_LOOKS_SHOT_LIST.md kept); five uncanonized rows ruled and emptied |
| ADMIN_CONSOLE_FIX.md (X1–X4) | 2026.08.04.73 | mocks 12a/12b adopted; supersedes S1's density ratification |
| NON_CANON_REVIEW_2026-08-06.md (A1, S1–S3) | 2026.08.04.73 | emptied BOTH queues — app Uncanonized table and store Non-canon table |
| SWATCH_GENERATE_RULING.md (A1) | 2026.08.04.73 | act-where-condition-is-met canonized as the pair to anchored explanation |
| HATCH_RULE.md (H1–H3) | 2026.08.04.79 | audit found zero drift in app/; store gained a mirrored copy + drift contract |
| SIGNIN_BRANDING_PLAN.md (G1–G3) | 2026.08.04.79, corrected .80 | first pass built from prose; GOOGLE_SIGNIN_SNIPPET.html + google-g.svg later delivered and shipped verbatim (radius, asset, approved string). Roboto still unbundled |
| TAKE_ACTIONS_PLAN.md (T1–T3, S1–S2) | 2026.08.04.79 | S1 shipped as the hatch state; render preview needs a tenant endpoint (see changelog) |
| README_2026-08-06.md (bundle index) | 2026.08.04.79 | 3 of its 6 entries were resurrected ghosts already shipped in .73 |
| BREAKDOWN_INTAKE_PLAN.md (B1–B5) | 2026.08.04.83 | mock 13a-breakdown-intake; Spec ID help copy follows B3 not the mock's auto-fill line (see commit) |
