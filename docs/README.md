# docs — what governs what

The map, and the only file you need to read to know what to read. It
deliberately does **not** summarise the documents it points at: a summary
is a second copy, and a second copy drifts.

| If you are touching… | The document that governs it | Known to be out of date |
|---|---|---|
| `app/` UI — markup, CSS, copy | `app/static/DESIGN_SYSTEM.md` | its `## Uncanonized patterns` table is a queue, not canon |
| `app/` behaviour | `docs/ARCHITECTURE.md` | — |
| prompts, models, token spend | `docs/INTENT.md` §Cost posture, then the docstrings in `app/generate.py` and `app/narrative.py` | — |
| what the product IS | `docs/INTENT.md` | — |
| `storefront/` code | `docs/WEBAPP_GUIDE.md` | — |
| hosting, Stripe, env vars | `docs/DEPLOYMENT.md` | — |
| security posture | `docs/SECURITY.md` | — |
| camera / composition vocabulary | `docs/CAMERA_AND_COMPOSITION.md` | — |
| cinematography grammars | `docs/CINEMATOGRAPHY_STYLES.md` | — |
| image serving and variants | `docs/IMAGE_SERVING.md` | — |
| what to tell a user | `docs/USER_GUIDE.md`, `APP_GUIDE.md` | — |
| test coverage | `docs/TEST_MATRIX.md` | — |
| how an agent should work here | `CLAUDE.md`, then `.claude/skills/` | — |

## Before implementing any `*_PLAN.md`

Read `docs/RETIRED_PLANS.md` first. Folder sync can resurrect a plan that
was already implemented and deleted; if it is listed there, delete it again
rather than building it twice.

## Reviews

`REVIEW_v*.md` at the repo root are an external adversarial review;
`docs/REVIEW_ROUND_*.md` are the implementer's answers. Together they are
the current work plan. A finding marked `ACCEPTED` is a commitment.

## `docs/history/`

Nothing in it is binding. See its own README.
