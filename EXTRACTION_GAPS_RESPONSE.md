# EXTRACTION_GAPS_RESPONSE.md — investigation findings (items 5 & 6)

**From the coding agent, 2026-07-31.** Response to `EXTRACTION_GAPS.md`.
Both gaps are real and buildable as proposed. Two material corrections to the
proposed shapes, one risk the doc doesn't name, and cost answers below.
Nothing is built yet, per the doc's instruction.

## Evidence check

Gap 5's symptom is confirmed in the live project data, and it already cost
manual work: the saved analysis (`data/wizard_analysis.json`) has 5 design
worlds with no Resistance, while the user's hand-maintained Bible already
carries a `## Resistance` section and `CHARLIES_CABIN_V001` explicitly scopes
to it. The extraction missed a faction the project demonstrably needed.

Gap 6's symptom is structural, as the doc says: nothing in the analysis
schema, the Bible section model, or the spec scope fields answers "what world
is this in?" — `setting.atmosphere` is per-sheet weather/mood, not biome.

## Correction 1 — the real work in Gap 5 is re-run state, not the extra call

The self-check call itself is cheap and easy (details below). But the
constraint "must not re-litigate confirmed languages on re-run" has nothing
to stand on today:

- Design worlds carry **no confirmed/proposed state** — every chip is
  implicitly accepted.
- `POST /api/wizard/analyze` **replaces the whole analysis wholesale**; the
  UI's unlock dialog even warns "re-running replaces the design languages…".
  Subjects survive re-runs only because casting moved them into the library
  (D3/D4). Languages have no such durable home until the Bible is drafted.

So Gap 5 requires: a `status: CONFIRMED | PROPOSED` field on worlds, a merge
on re-run (confirmed worlds survive by name; fresh finds arrive PROPOSED),
and updated unlock-dialog copy. Migration: worlds standing in a saved
analysis are treated as CONFIRMED — they survived review under the current
destructive-replace rule. Editing-and-saving a proposed world, or an explicit
confirm on the chip, flips it. This state work is ~80% of Gap 5.

Self-check specifics:

- Rides the existing `autofill._draft_gemini/_draft_openai` plumbing — same
  doc + instructions path the analyze call uses. No new client code.
- The "covered" list fed to the prompt must be **analysis worlds ∪ current
  Bible language sections** — the Bible can hold confirmed languages the
  analysis never emitted (true in the live project right now).
- Confirmed names are listed as covered, so the check cannot re-propose them.
- A self-check failure must not fail the analysis: log, skip, keep the main
  result. The extra call runs inside the same Analyze busy state.

**Cost/latency:** one additional full-screenplay text call per analyze run.
The Beltminers extract is roughly 30–40k input tokens with trivial output —
single-digit cents on the Gemini research model, order $0.10–0.30 on a
GPT-5.6-class model, ~10–30s added. Analyze runs happen a handful of times
per project. Negligible; no design change needed on cost grounds.

## Correction 2 — environments cannot be top-level Bible sections

`bible.py` defines **every non-system `##` section as a design language**
(`design_language_names()` — that is the whole section model). Top-level
environment sections would be swallowed into the language list, appear as
language checkboxes, and match the materials attacher.

Environments should instead ride the **level-3 mechanism** the parser already
uses twice (Core Material Language, scene lessons): a `## Environments`
container added to `SYSTEM_SECTIONS`, one `### <Environment name>` entry each,
parsed with `parse_sections(level=3)`. `render_context()` gains an
`environments` parameter injecting `<NAME> — environment` blocks;
`_style_context()` passes `spec.get("environments")`. New scope kind, existing
mechanism — answers implication 2.

Injection order note for design: the environment block should land **before**
the sheet's SETTING/atmosphere lines so the sheet-specific atmosphere wins
ties. Environments (biome palette/light) and `setting.atmosphere` (per-sheet
weather) overlap; worth one line of UI copy so users don't double-steer.

## The unnamed risk — location names won't match without help

Extraction emits free-text `key_locations` ("John and Charlie's meadow shack
and workshop"); the coverage table derives deterministic slugline places
("SHACK") from `insights.locations()`. If environments group the free-text
names, neither the coverage table nor R2's finder list can inherit the
grouping without a fuzzy matcher that will guess wrong.

**Recommendation — constrain at the source:** feed the analysis call the
deterministic slugline location list and require each environment's
`locations` to be drawn from it verbatim (assignment, not generation). Then
both tables group with zero matching heuristics, and a location row
re-assigns by editing that list through the existing analysis save path.

## Answers to Gap 6's numbered implications

1. **Payload migration:** none needed. `environments` is additive; every
   consumer defaults to `[]`. Older payloads render an empty-state line
   ("no environments in this read — re-run to extract them") next to the
   existing Unlock & re-run affordance.
2. **Compiler:** new scope kind on the existing level-3 mechanism — see
   Correction 2. No new injection machinery.
3. **Spec schema:** optional `environments: []` mirroring `design_languages`.
   The store imposes no field whitelist, so old sheets are untouched; scope
   freezes at lock exactly as languages do today. One parallel line where
   lighting studies inherit the parent's `design_languages` so they inherit
   environments too.
4. **Re-run:** same merge rule as Gap 5 (CONFIRMED survives verbatim,
   including its `locations` list; fresh finds arrive PROPOSED). Manual
   location→environment moves are edits to that list via the existing
   `PUT /api/wizard/analysis` — no new endpoint.
5. **Cost:** confirmed — environments ride the existing analysis call as a
   schema addition (`ANALYZE_SCHEMA_NOTE` is a JSON-shape string). No second
   call.

## Order and size

Agree: Gap 5 first. Gap 5 ≈ one working session (state + merge + one call +
chip state). Gap 6 ≈ two (schema, Bible container, compiler param, spec
selector, wizard grouping state). Neither blocks R1–R4; R2 stays flat until
Gap 6 lands, as planned.
