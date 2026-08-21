# Tutorials — authored onboarding

*Written 2026-08-17. System reference. The look is non-canon and awaiting a
design ruling (`app/static/DESIGN_SYSTEM.md` → Uncanonized patterns).*

A tutorial is **content, not code**: a JSON document with a trigger and a
list of steps. Nothing in `tutorial.js` knows what any tutorial says.

*For the flow this system lands in — what a new user meets before,
during and after the walkthrough — see `docs/FIRST_RUN.md`.*

## Where content lives, and how it reaches customers

| | Path | Who writes it | Who sees it |
|---|---|---|---|
| **Packaged** | `app/content/tutorials/*.json` | you, on a checkout | every studio, on its next update |
| **A studio's own** | `SCREENBOARD_HOME/tutorials/*.json` | that studio's owner install | that studio only |

They merge by id, install wins. A `{"id": "x", "deleted": true}` stub in a
studio's directory hides a packaged tutorial without editing the package.

**Saving is publishing, and `git push` is shipping.** On a git checkout the
editor writes the packaged file directly — commit it and the fleet gets it
on its next auto-update. On a cloud studio (no `.git`) the editor writes
that studio's copy and the page says so, because a fleet-wide publish from
there could never happen.

Seen-state is per install, in `HOME/tutorial_state.json`:
`{id: {status, step, rev, version, first_seen, updated}}`. Status is `seen`
(in progress — a refresh resumes there), `completed`, or `dismissed`.

## Authoring

Settings → **Tutorials**, on owner installs only (`SCREENBOARD_DEBUG_TOOLS`,
the same gate as Debug tools). Customers get the runtime, never the CMS.

Every dropdown in that editor is built from
`app/content/tutorial_schema.json`. Adding a predicate or an anchor is an
edit to that file — plus, for a predicate, a `case` in `tutorial.js`. A test
asserts the two agree, because a condition the server accepts and the
browser ignores is a tutorial that silently never fires.

### The document

```json
{
  "id": "first-board",          // lowercase; the filename and the state key
  "rev": 1,                     // raise it to re-show to everyone who saw rev 1
  "kind": "flow",               // flow | announcement (chrome only)
  "title": "…",                 // the CMS list, and a step's heading if it has none
  "note": "…",                  // to yourself; never shown
  "enabled": true,
  "priority": 100,              // higher runs first when two are eligible
  "replayable": true,
  "trigger": { … },             // when it runs by itself; omit for manual-only
  "steps": [ … ]
}
```

### A step

```json
{
  "id": "upload",
  "surface": "spotlight",       // spotlight | modal | page — see below
  "anchor": "status.next",      // a NAME from the registry, never a selector
  "side": "right",              // top|right|bottom|left — flipped if it won't fit
  "align": "start",             // start|center|end
  "goto": "/status",            // the app navigates here before the step shows
  "title": "…",
  "body": "…",                  // plain text; **bold**, `code`, blank line = paragraph
  "act": { "label": "Show me", "goto": "/settings" },
  "skip_if": { … },             // already done? the step is not shown at all
  "advance": { … },             // held until this happens; omit for a Next button
  "wait": "WAITING — UPLOAD THE SCREENPLAY",
  "block": true,                // block the highlighted control while up
  "optional": true              // skip if the anchor is not on screen
}
```

Bodies are escaped, then `**bold**` and `` `code` `` are put back. **HTML is
never rendered** — the author holds the workspace token, but the design
system owns the type.

### The three surfaces

| Surface | Scrim | Anchor | For |
|---|---|---|---|
| `spotlight` | dims all but the target | **required** | one control is the right one to press |
| `modal` | dims everything, centred | none | prose about the product |
| `page` | **none** | **refused** | more than one control is right, so pointing at any single one would be wrong. Docked in a corner, the page fully usable, nothing blocked |

`page` exists because of the credential step: OpenRouter, OpenAI, Gemini,
Anthropic and a custom endpoint are all correct answers, and a cutout
around one of them would have been the app recommending it.

### The condition grammar

One grammar for triggers, step skips and advance conditions. Each kind
declares the contexts it may be used in, and the validator enforces it:
`{"first_run": true}` as an *advance* condition would wait forever, so it
cannot be authored.

| Kind | Argument | Trigger | Skip | Advance |
|---|---|---|---|---|
| `always` | — | ✓ | ✓ | ✓ |
| `first_run` | — | ✓ | ✓ | |
| `version_changed` | — | ✓ | | |
| `version_at_least` | `"2026.08.05.83"` | ✓ | ✓ | |
| `state` | dotted path into `/api/state`, e.g. `stage_summary.screenplay` or `capability.any_credential` | ✓ | ✓ | ✓ |
| `state_equals` | `{path, value}` | ✓ | ✓ | ✓ |
| `view` | a view name | ✓ | ✓ | ✓ |
| `api` | `{method, path}` (path is a regex) | | | ✓ |
| `click` | an anchor name | | | ✓ |
| `seen` / `not_seen` | a tutorial id | ✓ | ✓ | |
| `all` / `any` | a list (nested in the editor, capped at two levels) | ✓ | ✓ | ✓ |
| `not` | one condition | ✓ | ✓ | ✓ |

`api` and `click` are **edges** — they match an event, which is why they
cannot be triggers. `state` and friends are **levels**, re-read from
`/api/state` (cached ~1.5s, invalidated by any mutation).

### Anchors

Steps name an anchor; `tutorial_schema.json` maps names to selectors. When
the markup moves, one line there changes and every tutorial still lands.
`tests/test_tutorials.py` resolves every selector against the real markup,
so a renamed id fails the build instead of stranding a spotlight in front
of a customer.

Two things a static test cannot catch, and how the system handles them:

- **An anchor that exists but is hidden.** `#screenplay-form` is the
  *replace* form and does not exist until a draft does. The runtime treats
  a zero-area rect as absent and falls back to a centred modal; in the
  CMS's Preview it also says so in a toast. Check your steps with Preview.
- **An anchor that flaps.** Views re-render as their fetches land. The
  placement re-resolves the anchor by selector on every pass, holds the
  last good geometry through a brief miss, and only collapses to a centred
  modal when the target is genuinely gone.

## Runtime behaviour

- **One at a time**, highest priority first, and never over an open dialog,
  lightbox or cropper.
- **A tour is never the work** (ruled 2026-08-18): on an anchored step every
  button in the popover is a ghost, because the only amber in view belongs
  to the control the step is pointing at. A centred step's `Next` takes the
  amber; an announcement's act button takes it from `Done`.
- **A held step that is resumed into converts to its centred form** — same
  copy, no spotlight, an enabled `Done`. It has been shown already; on
  return it is a reminder, not a gate.
- **Eligible** = never seen, or seen at a lower `rev`, or left in progress
  (which resumes at the recorded step).
- Triggers are re-checked on boot, on every navigation, and after every
  successful mutation.
- Esc ends it; focus is trapped in the popover and returned on exit; the
  waiting line is an `aria-live` region so a step change is announced.
- A click on the dim nudges the popover — leaving is deliberate, because a
  half-run walkthrough teaches nothing.

## Testing a walkthrough twice

Settings → Tutorials → **Forget** (one) or **Forget every tutorial on this
install**. Preview runs a document without recording anything, including
unsaved edits in the editor.
