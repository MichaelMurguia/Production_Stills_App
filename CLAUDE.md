# CLAUDE.md — Production Stills App

## UI work

**UI work must follow `app/static/DESIGN_SYSTEM.md`. Read it before writing any
markup or CSS.**

The interface was redesigned in July 2026. Code that predates the redesign still
exists in places, and matching the style of surrounding code will reproduce the
problems the redesign fixed. If existing code conflicts with `DESIGN_SYSTEM.md`,
the design system wins — bring the old code forward rather than copying it.

Two rules govern everything, both explained in full in that file:

1. **Amber (`--accent`) is a signal, not a decoration.** It marks the current
   pipeline stage, the one primary action in view, and focus. Nothing else.
2. **Courier carries machine data** — IDs, statuses, counts, timestamps, roles,
   hashes. Archivo carries hierarchy — headings, labels, prose.

Do not introduce a CSS framework, new fonts, new accent colors, gradients,
rounded corners, or emoji.

### Keeping the design system current — you own this

The user does not maintain these docs by hand. **You update them as part of the
work**, in the same commit as the feature. Do not ask permission and do not defer
it to a later pass.

**Most features need no new pattern.** A panel, a table, a badge, a gated button
— the design system already covers them. Reuse and ship.

**Every new feature is non-canon until Claude Design reviews it.** Whatever a
feature's UI is made of — a genuinely new pattern or pure reuse of canon
vocabulary — append a row for it to the `## Uncanonized patterns` table in
`app/static/DESIGN_SYSTEM.md` in the same commit: date, what it is, where it's
used, and what the designer should rule on (for pure-reuse features, note
"built from canon — review placement/copy only"). This applies to features from
design-handoff plans and user-directed changes alike; only the designer's
review moves a feature from that table into canon. ("Claude Design" = the
user's separate design-review Claude chat, which has this project folder
connected and delivers its rulings as `*_PLAN.md` files in the repo.)

**When a feature genuinely needs a pattern the design system doesn't cover,
additionally:**

1. Build the smallest thing that works, using existing tokens only.
2. Mark the CSS block `/* UNCANONIZED — <date> — <feature> */`.
3. Add a dated line to `## Changelog` at the bottom of that file.

The uncanonized table is a to-do list for a designer, not a permanent home. When
it reaches ~4 rows, tell the user in plain language that the UI has accumulated
patterns worth a design review: they open their design-review Claude chat with
this folder connected (re-syncing it so it sees the current files) and ask it to
review the Uncanonized table; it answers with a plan file to implement. Then
keep working — do not block on it.

**Also update `DESIGN_SYSTEM.md` when you:** add or reorder a pipeline stage
(the nav band and its numbering are documented there), add a token, change a
gate, or retire a pattern. Keep edits surgical — amend the relevant section, add
a changelog line, and leave the rest alone.

**Direction is one-way.** The design system is upstream of the code. When they
disagree, the code is wrong. Never rewrite the design system to describe what the
code drifted into — the only legitimate reasons to change it are a deliberate new
pattern (logged as above) or an instruction from the user.

## Architecture

- FastAPI app (uvicorn, auto-reload) serving a **vanilla-JS single-page app** —
  no build step, no bundler, no npm. Edit the source files directly.
- `app/static/index.html` — shell, nav, and all view `<template>` elements.
- `app/static/app.js` — all view rendering and behavior.
- `app/static/styles.css` — the whole design system.
- `data/` — references, screenplay, sheets, boards, `settings.json` (API keys).
- `project_state/` — `approval_log.md` is the append-only approval record.

`app.js` generates markup against the class names in `styles.css`. **Do not
rename existing CSS classes** — the stylesheet deliberately preserves every one
of them so styling and behavior stay decoupled.

## Storefront & deployment

The repo holds **two apps**. `app/` is the internal production tool and is
never deployed. `storefront/` is the public sales site (the app itself is the
product — download license + cloud subscription via Stripe), deployed on
Railway with Root Directory `storefront`. Two references govern this, split by concern:
`docs/WEBAPP_GUIDE.md` (how the system works, development requirements,
tests — read before changing `storefront/` code; `agents/15_webapp_engineer.md`
defines the role) and `docs/DEPLOYMENT.md` (hosting, Stripe, env vars,
runbook — read before touching infra; `agents/14_devops_engineer.md`).
Update the governing doc in the same commit as any such change. Storefront
tests: `cd storefront && python -m unittest discover -s tests`.

Hard boundary: no imports across `app/` ↔ `storefront/`; nothing from
`data/` or `project_state/` is ever served publicly or packaged into a
release zip; secrets live only in Railway variables and local shells, never
in the repo. Store UI must follow `STORE_DESIGN_SYSTEM.md` (its own binding system:
imagery-as-argument, motion rules, trait-list pricing, stated gates,
profession vocabulary, a two-amber page budget). It is a separate surface —
it does not add rows to the app DESIGN_SYSTEM.md's Uncanonized table.

## Product model

Strictly sequential: screenplay → art direction bible → breakdown sheet → lock →
panels → board. Later stages are gated on earlier ones (only a locked sheet can
generate panels; a board needs every panel approved).

Gates must be **readable as state before they are hit**, never surfaced only as
an error after the user acts. Show the disabled control, state the unmet
condition beside it, and link to where it gets resolved.

Renders are never upscaled. If a panel is smaller than its slot, flag it and
require regeneration.

## Testing — you own this

Two suites, both green before any push:

- **Product app:** `python -m unittest discover -s tests -v` at repo root —
  unit tests (bible section model, re-run merge, board layout, size rules,
  keyword derivation, project paths) plus functional API tests via
  TestClient (auth gate, projects lifecycle) against a throwaway home.
- **Storefront:** `cd storefront && python -m unittest discover -s tests -v`
  — fulfillment idempotency, Stripe-shaped objects, provisioning.

**Every new feature or bug fix updates or extends the unit and functional
tests for what it touched, in the same commit.** A bug that reached
production gets a regression test that reproduces it before the fix. Tests
never touch the real install — redirect `app.paths` to a temp home (see
`tests/test_app_api.py`) and inject fakes for external services (see
`storefront/tests/test_provisioner.py`).

## Changes

Functionality is not to change as part of design or styling work. Keep existing
endpoints, actions, and data shapes intact unless a change is explicitly
requested.
