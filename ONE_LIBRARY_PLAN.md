# ONE_LIBRARY_PLAN.md — "one library, visibly"

**For the coding agent.** Implements the Reference restructure agreed with the
user 2026-07-30. Mocks: `design_mocks/5a-reference-library.png`,
`5b-cast-the-film.png`, `5c-object-intake-chips.png`. Rulings here override
mocks; mocks are layout intent. One task per commit, order D1→D6.

## The model (write this into DESIGN_SYSTEM.md's Layout patterns when done)

There is ONE reference library. "Research" is renamed **REFERENCE** and is
organized by *when an image rides along*, not how it arrived:

- **STYLE** — rides along on every render, automatically.
- **SUBJECTS** — rides along when its subject appears on a panel. Subject
  cards ARE this shelf — the casting binder is the shelf's presentation, not
  a separate collection.
- **SCENES** — rides along when a board covers its scene (promoted takes,
  light studies, environment crops).

Production Design step 3 ("Cast the film") is a *door* into SUBJECTS: the
extraction proposes uncast subjects; casting creates the card in the library.
The wizard owns the moment and the gate; the library owns the data.

## What does NOT change

Prompt compiler, extraction, matching (`refInfoFor`), governance actions,
endpoints that write, REF-ids, approval log. This is re-homing + presentation.
Locations stay with the screenplay stage (coverage table) — they are NOT
castable subjects; they become references via scene anchors and promotion.

## D1 — Rename Research → Reference

Header tool label, view title, all copy ("add to reference", "promote to
reference"). Keep `data-view="references"` and all class names — this is a
label pass, not an identifier pass. Update Workflow/FAQ text.

## D2 — Three-shelf layout (mock 5a)

Replace the filter-chip grouping with three shelf sections, each headed:
Courier shelf name · faint ride-along line (`RIDES ALONG — …`) · right-aligned
Courier counts. Bucket by roleHead exactly as the existing chip mapping
(STYLE roles / SCENE_REFERENCE + LOCATION_GEOMETRY / everything else =
SUBJECTS). Keep the search field (finder-list vocabulary) and status counts
top-right; the intake row moves behind the `+ Add reference` button as the
existing dialog. Style/scene cards keep the current ref-card anatomy
(jurisdiction block, facts). Quarantined cards: dim image only, reason,
Reinstate — unchanged.

## D3 — Subject cards become the SUBJECTS shelf

Move the card component from the wizard into the shelf (one component, two
hosts). Card anatomy per mock: name (Courier bold) · kind badge (bordered
grey) · CAST/UNCAST badge (`--ok` / `--hold` border, never filled) · identity
text (sans, 12px, `--ink-dim`) · photo mosaic with `+` drop slot · Courier
facts line (`n PHOTOS · ROLE — NAME · USED IN n RENDERS`). Uncast
recommendations render as dashed-border cards with a `Cast this subject`
ghost button. Identity text becomes editable here (same write path as the
wizard). Migration: existing cards re-parent; verify `refInfoFor` still
matches (same strings — assert, don't assume).

## D4 — Wizard step 3 becomes "Cast the film" (mock 5b)

Step body = the SUBJECTS shelf embedded with a casting lens:
1. **Uncast block first** (`FOUND IN THE SCREENPLAY — UNCAST`): recommendation
   chips grouped by kind — CHARACTERS / VEHICLES / PROPS rows, Courier faint
   row labels at fixed width. Extraction already emits the kind; grouping is
   presentation only. Clicking a chip casts it (creates the library card).
2. Manual cast row below (name + kind select + `+ Cast` ghost) — the existing
   add-subject controls, relabeled.
3. Cast cards below, same component as D3, each with a `VIEW IN REFERENCE`
   text link (navigates to the shelf).
Step badge: `n CAST · m UNCAST` (`--hold` border while uncast > 0, `--ok`
when all cast). Step h2 keeps its position in the wizard; nothing else in
the wizard moves.

## D5 — + Object suggestion chips (mock 5c)

The spec editor's object intake row gains two chip groups above the input:
1. `IN THE LIBRARY — PICKING ONE GUARANTEES THE MATCH`: solid-border chips
   harvested from reference group titles + subject card names (existing
   groups first). Clicking adds the object with the exact title → green ✓.
   Scene/geometry entries carry a faint `· SCENE` / `· GEOMETRY` suffix.
2. `IN THE SCENE PARAGRAPH — WILL NEED EVIDENCE`: dashed-border chips from
   the sheet's own scene-paragraph nouns (client-side: title-case tokens not
   already objects; keep it dumb — no NLP, no new endpoint). Clicking adds
   the object un-matched, as free-typing would.
Free-text input + kind select + `+ Object` stay, full-width row per the
intake-row rule. This is the vocabulary-picker grammar — suggestion chips
stateless, never amber.

## D6 — Doc pass

DESIGN_SYSTEM.md: add the one-library model to Layout patterns; subject card
+ shelf header anatomy to Components; changelog line. Update
`docs/USER_GUIDE.md` and the Workflow subview: the chain copy becomes
"Screenplay → Cast & anchors (REFERENCE) → Specification → …". Any new CSS
follows the uncanonized protocol only if it's genuinely new — shelf headers
and cast badges reuse existing vocabularies and should not need it.

## Ground rules

Tokens only; amber budget unchanged (nothing in 5a/5b/5c is amber except the
option badges in the mock frame, which are not app UI). Hatch classes for
empty image slots per the canonical spec. No mutating-endpoint changes; the
only new write path is "cast" = existing subject-card creation, callable from
both doors. If migration surfaces a mismatch `refInfoFor` can't absorb, stop
and report.
