# Test Matrix

**Generated** — `python -m scripts.test_matrix`. Do not hand-edit: a test
asserts this file is exactly what the generator produces, so an edit here
fails the suite instead of silently drifting. The prose that a generator
cannot derive lives in the script's own PREAMBLE and NOTES.

Two suites, both green before any push (CLAUDE.md):

| suite | command |
|---|---|
| Product app | `python -m unittest discover -s tests` |
| Storefront | `cd storefront && python -m unittest discover -s tests` |

Counts are test methods parsed from source, inherited ones included. They
land within a few of a live run — close enough to see the shape of the
suite, and stable enough that this file can assert against itself.

The standing convention: **every feature or bug fix updates or extends the
tests for what it touched, in the same commit**, and a bug that reached the
user gets a regression test carrying that user's real data — the reporting
production's own hexes, the reporting screenplay's own filenames — before
the fix. Tests never touch a real install: `app.paths` is redirected to a
temp home and external services are faked.


**1942 tests** across 106 files.


## Product app — 1726 tests in 89 files

| File | Tests | What it holds |
|---|---:|---|
| `test_add_panel.py` | 8 | Add a panel from the panels workbench (user 2026-08-09). |
| `test_anchor_consolidation.py` | 159 | One question per anchor (user 2026-08-16: "we now have duplicative entries and we should consolidate"). |
| `test_anchors_stay_in_step.py` | 32 | Regression, user-hit 2026-08-22 and reproduced from the install. |
| `test_app_api.py` | 28 | Functional pass over the app's API surface via TestClient: the cloud auth gate, the projects lifecycle, and healthz — all against a throwaway home so  |
| `test_approval_snapshot.py` | 26 | One breakdown, per-panel gates — the foundation (user rulings 2026-08-16). |
| `test_assemble_layout.py` | 8 | Board layout invariants: the aspect variant honors take ratios with a uniform minimal residual, variants resolve per the ruling, and geometry stays in |
| `test_audit_fixes.py` | 14 | Regression tests for the 2026-08-02 product-app audit batch: path traversal guards, canvas bounds, corrupt-state resilience, model-JSON shape, quarant |
| `test_autofill_board_type.py` | 27 | The board's shape is the user's decision (user-hit 2026-08-07). |
| `test_backup_import.py` | 22 | Importing a backup INTO an existing production (2026-08-06). |
| `test_backup_security.py` | 7 | Backup roundtrip + security invariants: no keys in backups, zip-slip refused, restore never overwrites, traversal ids 404, headers present, and the re |
| `test_bible.py` | 5 | Bible section model: every non-system ## section is a design language, environments ride the level-3 container, and render_context injects in the docu |
| `test_bible_editor.py` | 25 | The Art Direction Bible panel: one button, at the top, four verbs. |
| `test_brief_amend.py` | 9 | The panel brief is editable BETWEEN takes (user 2026-08-08). |
| `test_camera.py` | 32 | Camera & composition language (user 2026-08-09). |
| `test_canon_2026_08_07.py` | 22 | NON_CANON_REVIEW_2026-08-07 — the seven rulings, held. |
| `test_cinematography_grammar.py` | 30 | The cinematography grammar that rides a render — and the ability to take it back (user 2026-08-16: "the doc provides a prompt — shouldn't we apply the |
| `test_citation_is_verified.py` | 18 | No route may file SCRIPT_EXPLICIT for a line the screenplay does not contain. |
| `test_composition.py` | 15 | Scene composition check (2026-08-13). |
| `test_concurrent_generation.py` | 1 | Two panels rendered simultaneously must be two separate prompts. |
| `test_connectors.py` | 19 | Connector registry, state derivation, filters, enable rules (N1) — all against a temp install home; no network anywhere in this file. |
| `test_consolidate_revisions.py` | 29 | Collapsing a revision chain into one breakdown (user ruling 2026-08-16, "Yes Collapse", asked for concretely 2026-08-16: "I still have 2 CANYON_GRM br |
| `test_correction_intake.py` | 14 | Correction intake (2026-08-13): a rejection becomes structure. |
| `test_credential_blocker.py` | 64 | A missing credential is a blocker (user ruling 2026-08-18). |
| `test_debug_tools.py` | 7 | Debug tools (user request 2026-08-03): the mock engine — the whole pipeline scan → bible → breakdown → panels → board on static content, zero model ca |
| `test_deep_links.py` | 9 | Every stage and selection is a shareable URL (user 2026-08-12): /panels/SPEC-0001, /boards/SPEC-0001/BOARD-0002, /boards/SPEC-0001/arrange. |
| `test_design_tokens.py` | 97 | Mechanical token assertions (design-verify step 4, standing suite). |
| `test_docs_are_current.py` | 4 | Documentation that can go stale is derived, not restated. |
| `test_engine_sends_plates.py` | 12 | Which engines put the reference IMAGES in front of the image model. |
| `test_every_route_is_reachable.py` | 6 | Every route a user needs must be reachable from the UI. |
| `test_file_pickers.py` | 4 | Programmatic file pickers must be attached to the document. |
| `test_generate_units.py` | 5 | Engine-facing unit rules: size legality (×16, ≤3840, no upscaling), the ChatGPT-pipeline preset clamp, and deterministic keyword derivation. |
| `test_harness_tooling.py` | 17 | HARNESS tooling (2026-08-13): the fixture recorder and the replay harness builder. |
| `test_image_variants.py` | 22 | Display-tier image serving (app.imaging + candidate/reference resolvers). |
| `test_ledger_ui.py` | 15 | Evidence ledger + workbench scope UX (user 2026-08-13) — JS pins. |
| `test_loc_cap.py` | 20 | A long list shows its head and states its tail (SCAN_CONSOLIDATION §3). |
| `test_location_acts.py` | 21 | The location list reads in acts, chronologically (user 2026-08-16: "LOCATION list should be divided into 3 acts if they can be derived from the screen |
| `test_lock_is_not_freeze.py` | 13 | A LOCK is not a FREEZE. |
| `test_looks.py` | 19 | Board looks (2026-08-13): a look is a persisted sheet-level property that survives arrangement commits; dress is PURE DERIVATION resolved from canon a |
| `test_medium_guard.py` | 4 | Regression (user-hit 2026-08-06): a bake-off sample rendered photo-real past an attached BOARD_RENDERING_STYLE anchor. |
| `test_name_acts.py` | 16 | Naming the acts is its own small call (user 2026-08-16: "No Act Titles", reported on an analysis that predates the field). |
| `test_narrative.py` | 12 | F6 backend (narrative via OpenRouter/Claude): the narrative role runs on the stored Anthropic key or the OpenRouter connection — dispatch, gating, set |
| `test_no_control_bytes.py` | 2 | No control bytes in source. |
| `test_no_scroll_jump.py` | 7 | Redrawing the panels host must not throw the reader to the top (user 2026-08-16: "when I click on the frames in the strip the page jumps to the top. |
| `test_object_ref_detach.py` | 10 | A required object can be ruled NOT covered by a reference group (user 2026-08-16: "I have reference for 'airlock hatch behind Sal' and its green but t |
| `test_object_ref_matching.py` | 11 | One rule for "does this phrase name that thing", shared by every surface that asks (user-caught 2026-08-16: a panel with the required object "Sal's ey |
| `test_one_resolved_manifest.py` | 18 | One fact, one computation — the manifest, the count, and the arrange room's SHORT verdict. |
| `test_p1_lifecycle.py` | 13 | P1 coverage from docs/TEST_MATRIX.md: the sheet lock/hash contract, the candidate lifecycle, and the assemble endpoint — the behaviors that guard cano |
| `test_palette_distinctness.py` | 25 | Four design languages must not share one palette. |
| `test_palette_order.py` | 23 | Band order in a palette ramp (PALETTE_GROUPS_PLAN §1, §5). |
| `test_paths_projects.py` | 5 | Multi-project home: switching repoints every mutable path, the legacy root layout is always project '', and the active pointer persists. |
| `test_pipeline.py` | 5 | The scripts layer end to end: validate, compile, audit. |
| `test_prompt_download.py` | 5 | The compiled-prompt download (user 2026-08-06). |
| `test_prompt_edit.py` | 11 | Step 05's verb says "Read & edit" and both halves have to be true (user-caught 2026-08-16: "there is a 'Read and Edit' button on the prompt, but I can |
| `test_read_progress.py` | 37 | The read, as it happens. |
| `test_reference_locations.py` | 11 | The screenplay's places reach the Reference library (user 2026-08-08). |
| `test_reference_roles.py` | 6 | Reference role jurisdiction — what each role tells the model it controls. |
| `test_rejection_notes.py` | 13 | Rejection notes survive their takes (user ruling 2026-08-13). |
| `test_render_resilience.py` | 6 | A cut connection must not read as a failed render (user 2026-08-09). |
| `test_required_object_refs.py` | 12 | A required object names a subject the way the SCRIPT does (user-caught 2026-08-16: "the script specifically mentions Sal — why would the required obje |
| `test_rescan_and_questions.py` | 34 | Rescanning swatches, answered design questions, and the hour that wasn't. |
| `test_revision_scope_ui.py` | 14 | One board across revisions — client wiring pins (2026-08-13). |
| `test_revisions_are_inert.py` | 8 | After consolidation the revision machinery answers nothing. |
| `test_revisions_board.py` | 32 | One board per creative unit (user model, 2026-08-13). |
| `test_role_head_legacy.py` | 12 | A titled reference still belongs to its family (user 2026-08-07). |
| `test_saved_panel_prompt.py` | 23 | A hand-edited prompt can be SAVED onto the panel (user 2026-08-16: "I need to be able to Save the prompt once I edit it — explicit button"). |
| `test_saved_prompt_follows_art_direction.py` | 12 | Regression, user-hit 2026-08-22 and reproduced end to end. |
| `test_scan_screenplay.py` | 32 | Tell the app anything about a panel; it re-reads the screenplay. |
| `test_scene_anchor.py` | 14 | Scene anchor regression (user-hit 2026-08-06): a breakdown run for "INT_BRIEFING_ROOM_DAY_V01" drafted the crash site. |
| `test_screenplay_formats.py` | 4 | The four formats the app claims, actually read. |
| `test_screenplay_two_copies.py` | 6 | Two copies of the screenplay, and only one of them costs money (user rule, 2026-08-16). |
| `test_sheet.py` | 70 | The sheet grammar (SHEET_SYSTEM_PLAN §12 + tech spec §7, amended by the Lookbook rollback 2026-08-12): the size ladder with the R1 elastic/fixed rulin |
| `test_step_numbers.py` | 9 | Copy that names a wizard step names the right one. |
| `test_step_sequence.py` | 60 | The step sequence — STEP_SEQUENCE_SPEC_2026-08-14, mock hier-4a. |
| `test_step_sequence_03.py` | 26 | Stage 03 in the step vocabulary — STEP_SEQUENCE_SPEC Part 3, mock hier-5a. |
| `test_storage_guard.py` | 14 | Disk space is a gate, not a 502 (user 2026-08-07). |
| `test_style_anchors.py` | 12 | The four-anchor ruling (2026-08-03): three movie parameters + one board parameter auto-attach, capped per role; board layout is assembly grammar. |
| `test_style_libraries.py` | 37 | Three anchors, three documents, one parser. |
| `test_style_plate_tooling.py` | 11 | The two scripts that stand between a folder of renders and the picker. |
| `test_stylesheet_parses.py` | 4 | The stylesheet must actually parse. |
| `test_subject_identity_match.py` | 16 | The SUBJECT IDENTITIES block missed the same way the workbench did. |
| `test_suite_hygiene.py` | 3 | The suite checks itself for dead tests. |
| `test_swatch_edit.py` | 31 | Swatch labels, hero colours and recolour (user 2026-08-06). |
| `test_swatches.py` | 13 | Color swatches (NON-CANON widget, user-directed 2026-08-05): the swatch reference endpoint renders pure solid pixels with the facts in the notes; prop |
| `test_take_bar.py` | 15 | The take action bar — one verdict, two lists, no wrap (mock 17a, 2026-08-08; supersedes the 14a comparison contract in this file's own history). |
| `test_token_economy.py` | 12 | What a model call costs, and what happens when it runs out. |
| `test_tutorials.py` | 42 | The tutorial system: content, vocabulary, and the two places it can rot. |
| `test_vocabulary.py` | 5 | One act, one name. |
| `test_withdraw_approval_ui.py` | 13 | An approved panel can go back to draft WITHOUT being rejected (user 2026-08-16: "I need to be able to put an approved panel back into draft without ha |
| `test_wizard_merge.py` | 5 | Re-run merge semantics (Gap 5 rulings): confirmed work survives by name, fresh finds arrive PROPOSED, answered questions are never touched. |


## Storefront — 216 tests in 17 files

| File | Tests | What it holds |
|---|---:|---|
| `test_account_keeps_its_promise.py` | 12 | Regression, user-hit 2026-08-22 on the live site. |
| `test_accounts.py` | 14 | Account lifecycle: magic links are single-use and uniform, sessions come from signed cookies, the account page lists the email's purchases, Google rou |
| `test_admin_storage.py` | 23 | Fleet storage on the admin page (user 2026-08-07). |
| `test_audit_fixes.py` | 13 | Regression tests for the 2026-08-02 storefront audit batch: unpaid sessions never fulfill, refunds close the door, canceled services are never abandon |
| `test_door_preview.py` | 8 | The workspace door's render preview (TAKE_ACTIONS S1). |
| `test_fleet_autoupdate.py` | 5 | The fleet updates itself when a push deploys the storefront (user ruling 2026-08-12: "update automatically when you push changes"). |
| `test_fulfillment.py` | 3 | Fulfillment invariants: idempotency on stripe_session_id, detached-safe returns, and Stripe-shaped (attribute-only, no dict .get()) field access. |
| `test_mail_paths.py` | 17 | Mail, end to end — the send path and the receive path. |
| `test_pipeline.py` | 3 | The /pipeline page: static, always 200, and its provenance claims stay tied to the real Beltminers record (STORE_DESIGN_SYSTEM §6 — true numbers). |
| `test_provisioner.py` | 6 | Provisioning invariants: cloud fulfillment queues a workspace; reconcile converges PENDING → ACTIVE exactly once with a configured Railway; missing co |
| `test_recovery_and_export.py` | 9 | Tier A invariants: license recovery is anti-enumeration and env-gated, legal pages exist, the entitlement export hides without its token and never lea |
| `test_seo.py` | 6 | SEO pass (user request 2026-08-03): public pages carry full head metadata and structured data; private/transactional pages and every tenant host say n |
| `test_site_text.py` | 11 | Owner page-text rewrites (debug tool 2026-08-03): public reads — the overrides ARE the page copy — but writes exist only for signed-in OWNER_EMAILS ac |
| `test_store_images.py` | 4 | Responsive marketing imagery — the storefront must not serve raw stills. |
| `test_store_tokens.py` | 22 | Store token contracts (design-verify step 4 for `storefront/`). |
| `test_tenant_proxy.py` | 12 | The wildcard tenant router: studio hosts proxy to their tenant's railway service, storefront hosts pass through, unknown studios get a stated 404, and |
| `test_trials.py` | 48 | Trials, both kinds. |


## What is deliberately not covered

- **Model output quality.** No test asserts that a bible reads well or a
  render looks right; that is the user's judgement and the reason the
  product exists. What IS tested is everything measurable around it —
  that a prompt contains what it claims, that a set of colours is
  actually distinct, that a citation exists in the screenplay.
- **Live provider calls.** Every engine is faked. A test that spends
  money is a test nobody runs.
- **Pixel-perfect layout.** Captured and reviewed by eye through the
  `/design-verify` loop; only token contracts, contrast ratios and
  structural facts are asserted mechanically.

## Known flake

One storefront provisioner test can reach the real network through the
`_domain_serves` probe when a row's `url` and `railway_url` diverge — seen
once. Stub it if it recurs.
