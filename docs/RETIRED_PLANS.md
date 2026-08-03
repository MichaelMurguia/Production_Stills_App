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
