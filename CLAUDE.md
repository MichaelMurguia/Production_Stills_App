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

## Architecture

- Flask app serving a **vanilla-JS single-page app** — no build step, no bundler,
  no npm. Edit the source files directly.
- `app/static/index.html` — shell, nav, and all view `<template>` elements.
- `app/static/app.js` — all view rendering and behavior.
- `app/static/styles.css` — the whole design system.
- `data/` — references, screenplay, sheets, boards, `settings.json` (API keys).
- `project_state/` — `approval_log.md` is the append-only approval record.

`app.js` generates markup against the class names in `styles.css`. **Do not
rename existing CSS classes** — the stylesheet deliberately preserves every one
of them so styling and behavior stay decoupled.

## Product model

Strictly sequential: screenplay → art direction bible → breakdown sheet → lock →
panels → board. Later stages are gated on earlier ones (only a locked sheet can
generate panels; a board needs every panel approved).

Gates must be **readable as state before they are hit**, never surfaced only as
an error after the user acts. Show the disabled control, state the unmet
condition beside it, and link to where it gets resolved.

Renders are never upscaled. If a panel is smaller than its slot, flag it and
require regeneration.

## Changes

Functionality is not to change as part of design or styling work. Keep existing
endpoints, actions, and data shapes intact unless a change is explicitly
requested.
