# EXTRACTION_GAPS.md — items 5 & 6: extraction changes (needs Claude Code design)

**For the coding agent.** UI targets are now mocked: design_mocks/6a (PROPOSED
language chip + confirm/drop, environment cards, environment-grouped location
finder with per-row reassign), 6b (prominence counts on chips, per-row bulk
cast), 6c (environment selector in sheet scope + prompt-will-carry line). Two real extraction gaps found in live use
(screenplay: Beltminer_Summer_25). These change what the AI extracts — your
domain. Investigate, propose the implementation, come back with material
implications before building. Presentation for both is already planned on the
design side; do not build UI beyond what's noted.

## Gap 5 — Missed factions (the Resistance)

**Symptom:** the read produced 5 design languages (POST-FALL FRONTIER, GRM
ORDER, BELTMINER AND TERRA NOVA, GENETICS, SKINNERS) but the Resistance — a
named faction with its own outposts, warp ships, and visual identity in the
screenplay — appears only inside location strings. A whole visual culture has
no Bible section.

**Proposed fix — self-check pass:** after the main analysis, one additional
cheap call: "List every named faction, order, culture, corporation, or
recurring group in this screenplay. For each, state which of these design
languages covers it: [list]. Flag any that none covers." Uncovered groups
return as **proposed languages** (marked PROPOSED, like other weak
inferences) for the user to confirm, rename, or drop in the existing language
chips UI — the confirm/rename/drop flow already exists, so no new UI beyond
a PROPOSED state on the chip.

**Design constraints:** the model must never silently add a language — the
user confirms. The self-check must not re-litigate confirmed languages on
re-run. Report cost/latency impact of the extra call.

## Gap 6 — Environments/biomes are a missing axis

**Symptom:** Forest, Desert, Asteroid Surface never extracted. They are not
factions — a Resistance camp in forest vs. desert shares culture but not
palette/light/atmosphere. Design languages answer "whose stuff is this?";
nothing answers "what world is this in?"

**Proposed model:** ENVIRONMENTS as a first-class extraction output alongside
design languages:

- Extraction emits environments (name, palette/light/atmosphere notes, which
  key_locations belong to each). Locations then group under environments —
  the step-2 finder list and the screenplay coverage table both inherit that
  grouping (design side will handle presentation).
- The Bible gains an Environments section (one entry each), parallel to
  design-language sections.
- Breakdown sheets scope by `language × environment`: an environment selector
  joins the existing design-language scope checkboxes; the prompt compiler
  injects the selected environment section exactly as it injects language
  sections today.
- Same governance as languages: confirm/rename/drop, PROPOSED until
  confirmed, `+ ADD ENVIRONMENT` manual door, and a location row can be
  re-assigned to an environment by hand.

**Material implications to assess and report back:**
1. Analysis payload schema change — migration for existing saved analyses
   (older payloads have no environments; render gracefully, offer re-run).
2. Bible structure change — does the compiler's section-injection need a new
   scope kind, or do environments ride the existing mechanism?
3. Spec schema — one new optional field (environment scope) on sheets; locked
   sheets unaffected (scope is frozen at lock as today).
4. Re-run semantics — re-running the read must preserve confirmed languages
   AND environments, and location→environment manual assignments.
5. Cost: environments extraction should ride the existing analysis call
   (one schema addition), not a second call — confirm feasibility.

**Order:** Gap 5 first (one prompt + one chip state), then Gap 6 (schema).
Neither blocks the R1–R4 presentation round, which is already planned —
but R2's flat location list is deliberately ungrouped until Gap 6 lands.
