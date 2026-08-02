# DESIGN_REVIEW_2026-07-30b.md — role picker ruling

**For the coding agent.** One pattern in the uncanonized table (role picker).
Apply, fold into DESIGN_SYSTEM.md, clear the table, delete this file.

## Ruling: CANONIZED as "vocabulary picker", with three refinements

The pattern is right — the role vocabulary is finite and load-bearing, and
suggestion-first entry is the correct cure for "GT40" vs "GT 40" drift. The
user's pending refinements (passive faint preview, per-family facet chips,
free-text notes) are all approved as described. Refinements:

1. **Suggestion chips (single-pick): `.vchip` is fine, but NO `.on` state.**
   Clicking a suggestion fills the field — the field is then the state; the
   chip never stays lit. If code currently marks the clicked chip `.vchip.on`,
   remove it.
2. **Facet toggle chips (multi-select): never amber.** `.vchip.on`'s amber
   fill means "the one active choice" (variant, filter). A multi-select
   toggle needs a different vocabulary — reuse `.chip.open`'s treatment:
   toggled = `--ink` text, `--ink-faint` border, `--panel2` fill; untoggled =
   `.vchip` resting state. Name it `.vchip.set` in CSS with a comment saying
   why it isn't `.on`. One dialog may show many `.set` chips and zero amber.
3. **Preview line**: the shipped `WILL BE STORED AS` ::before treatment is
   approved — keep it Courier `--ink-faint` with the value in `--ink-dim`,
   no field chrome, and render it only when it differs from what the user
   typed (a preview that repeats the input is noise).

## Canonical rule for the doc (Components section)

*Vocabulary picker: for finite, load-bearing vocabularies (roles, and any
future controlled names). Suggestion chips above the field harvest existing
app values — clicking fills the field and the chip never stays selected;
free text remains possible but reuse is the easy path. Multi-select facet
chips use `.vchip.set` (ink/panel2), never amber — amber selection fill is
reserved for single-choice chips (variant, filter). A passive Courier
`WILL BE STORED AS` preview shows the normalized value only when it differs
from the input. Notes and other provenance prose stay free text.*

## Doc moves

1. Move the table row into `## Components` as above; clear the table.
2. Changelog: `**2026-07-30** — Vocabulary picker canonized: suggestion
   chips stateless, facet toggles .vchip.set (never amber), conditional
   stored-as preview.`
3. Remove the `/* UNCANONIZED */` marker at styles.css ~975.
4. Delete this file.

## Also noted, no action needed

The aspect catalog (film-format names, per-engine disabling, snap on model
change) shipped canonically and is well handled — logged, correct tokens, no
new pattern. Good work.
