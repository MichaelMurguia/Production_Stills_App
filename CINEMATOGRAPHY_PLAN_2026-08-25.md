# Plan — making art direction and cinematography reach the image

**2026-08-25. Trimmed to what is not built.** Everything else in this
plan — E1–E5, R1, R1.5, R2, A1–A4, C3, C4, C6, C7, C9 — was implemented
on 2026-08-25 and is recorded in `docs/RETIRED_PLANS.md`. The full
document, including what was tried and struck, is in git history.

One item remains, and it is not code.

---

## C8 — Engine per look *(untested)*

Every render in this investigation was `gpt-image-2`; the calibration
images were made in ChatGPT directly. One controlled pair against Gemini,
before assuming anything. If engines differ markedly on style adherence
that is a product fact worth surfacing.

**What is now in place to run it properly:** the style probe renders
twice per engine and shows both (C6), so a difference between engines can
be read against each engine's own run-to-run spread rather than against a
single take. That was the missing control — the reason this could not be
answered before is that nothing in the app ever rendered the same thing
twice.

**To answer it:** Production Design → engine style samples → Generate on
Gemini and on OpenAI with the same subject, then compare the two pairs.
Four renders. If the between-engine difference is smaller than the
within-engine difference, there is nothing here. If it is larger, the
engine belongs beside the grammar as a stated choice.
