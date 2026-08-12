# Bug-fix plan — 2026-08-12 review of releases .14–.21

Source: three-agent review of `docs/HANDOFF_2026-08-10.md` and the concurrent
sheet-grammar commits. All bugs below were reproduced or verified against code
during the review. Two releases: a same-day fix batch (Release 1) and the
async-generation follow-up (Release 2). Every fix ships with a regression test
in the same commit (CLAUDE.md).

## Release 1 — the fix batch (low-risk, one fleet rollout)

### B1. Approval-gate bypass through the Arrange door — `app/sheet.py`
**Bug:** `arrange_board` copies unapproved takes into slots (`slot_map` keeps a
`candidate_id` regardless of status), `set_slot` checks only existence, and
`export_sheet` gates on pixels/type only — so a BOARD-archetype export can
contain never-approved renders, bypassing the stage-05 contract that the
untouched `assemble.py` gate still enforces.
**Fix (defense in depth, three layers):**
1. `arrange_board` carries only APPROVED takes into slots; a panel without an
   approved take arranges as an **empty slot** (the composer's fill tray
   already offers approved takes only, so the front door stays consistent).
2. `set_slot` on a BOARD-archetype sheet validates the take's approval, not
   just existence. Lookbooks keep their current tray rule (already clean).
3. `export_sheet` for BOARD archetypes refuses if any filled slot's take is
   unapproved — same error grammar as the assemble gate.
**Tests:** arrange with a CANDIDATE-status take → empty slot; `set_slot` with
an unapproved id → `SheetError`; export with an injected unapproved slot →
refused. Gate readability: the empty slot IS the state; no new UI needed.

### B2. Arrange 422s on real productions — `app/sheet.py:816` (R3 mapping)
**Bug:** the variant→block mapping sends all non-hero panels into one block,
but CLUSTER caps at 5 and GRID at 12 (`_validate` hard ceiling), and the
min-slot rule rejects a 3-panel spec with an unfilled slot. A 6-panel
"allocation" board (the pre-2026-07-31 default) or a 13+-panel spec throws a
jargon 422 from an ungated button; older productions are the likely victims.
**Fix:** make the mapping cap-aware — overflow chunks into additional blocks
of the same type (multiple blocks per sheet are already legal grammar; no
canon change). For the min-slot floor, arrange-built sheets pick the smallest
block type that fits the panel count; the every-slot-filled exemption extends
to arrange-time (slots may be legitimately empty per B1). Do **not** relax
`_validate` itself — hand-authored sheets keep the hard caps.
**Tests:** 6-panel allocation spec arranges (2 blocks); 13-panel spec
arranges; 3-panel spec with one take-less panel arranges with an empty slot.

### B3. Autofill camera vocabulary never migrated — `app/autofill.py:184`
**Bug:** autofill instructs the model to emit `FULL_BODY | DETAIL` (the
pre-camera-enum scale set) and persists it verbatim (`create_spec_from_dict`
never sanitizes), so the shot axis silently vanishes from prompts
(`SCALE_PHRASING` miss) and the sheet editor misreports "— from bible —".
**Fix:**
1. Update the autofill prompt to the canonical enum.
2. Sanitize at persist: `create_spec_from_dict` runs the same
   `_clean_camera_fields` path as every other write, with a legacy map for
   the two orphans (`FULL_BODY`→`FULL` if that exists in the enum, else
   `MEDIUM`; `DETAIL`→`MACRO` or `CLOSE` — pick the semantically nearest
   canon values when implementing, and record the mapping beside
   `_LEGACY_LENS`).
3. Harden resolution (review finding 2): `generate._camera_block.resolve`
   treats an unrecognized persisted value as unset — fall back to the
   production default instead of silently omitting the axis; same for
   `_lens_phrasing` returning `""`.
4. One-time sweep on sheet load (same lazy-migration style as
   `_LEGACY_LENS`) so existing drafted sheets heal without a script.
**Tests:** autofill dict with `DETAIL` persists the canon value; resolve with
garbage falls back to the default phrasing; legacy value in a stored sheet
renders the mapped enum in `pcam` and survives a save.

### B4. Variant-cache race / poisoned cache — `app/imaging.py:37-66`
**Bug:** `im.save` writes the final cache path directly; the pre-semaphore
fast path trusts existence+mtime, so a concurrent reader can serve a
truncated WebP during the boot-warm window, and a write that dies mid-flight
(ENOSPC, kill) leaves a fresh-looking poisoned file served forever.
**Fix:** write-to-temp + `os.replace` (atomic on the same volume); on any
save exception, unlink the temp file. With atomic replace, a visible cache
file is always complete, the fast path becomes safe, and a concurrent
double-build degrades to harmless last-writer-wins — no per-file lock needed
(keep the semaphore as the load bound it actually is). Also: guard the
`SCREENBOARD_VARIANT_CONCURRENCY` int parse (bad value → default, not an
import-time crash).
**Tests:** monkeypatched `save` that raises mid-write leaves no cache file
and the next call rebuilds; bad env var doesn't crash import.

### B5. Arranged mastheads born stale — `app/sheet.py:811`
**Bug:** `arrange_board` sets `masthead.binding` but never `bound_hash`;
`get_sheet` compares `bound_hash`, so every arranged board shows
"SOURCE MOVED" from birth.
**Fix:** stamp `bound_hash` in `arrange_board` (one line).
**Test:** freshly arranged board's masthead is not stale; goes stale after a
genuine source change.

### B6a. 502-workaround micro-fixes — `app/static/app.js`
(Interim only; the durable fix is Release 2.)
1. **Cancel works during a gateway-cut poll:** Cancel sets a flag/AbortSignal
   the `pollForNewTake` loop checks each tick; on cancel, stop polling and
   show the existing "take may still arrive" notice.
2. **No view hijack:** before `landed` re-renders, verify the panels view for
   *that spec* is still current; otherwise toast "Take arrived on <spec>"
   and skip the re-render.
**Tests:** extend `tests/test_render_resilience.py` beyond source-string pins
where feasible (poll-loop cancel flag pinned at minimum).

### B7. Test hygiene — `tests/test_rescan_and_questions.py`
The 9 order-dependent tests were already fixed in `0582f77`
(`_IsolatedStyleContext`); the handoff's risk item 3 is stale. Residual gap:
those two classes still read the real install (`rejection_feedback`,
`project_name`). **Fix:** add the file's existing temp-home redirect
(as `RescanKnowsWhatItHas` already does) to `_IsolatedStyleContext`.

**Release 1 rollout:** standard flow — bump VERSION → `stage_release.py` →
commit zips → push → verify storefront `/healthz` → `update_tenants.sh` →
`watch_tenants.py`. No UI pattern changes → no Uncanonized rows; B6a's toast
reuses existing toast grammar.

## Release 2 — async generation (the durable 502 fix)

The agreed-but-unbuilt follow-up from the handoff: fire-and-poll generation —
the render endpoint returns immediately with a job id, the client polls job
status, and the outcome (success, refusal, failure) is logged to the Status
panel, closing the original "a 502 leaves no status-panel entry" complaint.
This retires the client-side gateway heuristic (and B6a's patches) entirely.
Scope notes:
- Server: job registry in the existing file-backed style (no DB), render runs
  in a worker thread, graceful-drain deploys already cover in-flight jobs.
- Client: `runGenerate` becomes submit→poll; Cancel cancels the poll and
  marks the job abandoned (server finishes and logs regardless — spend is
  never silently discarded).
- Any visible Status-panel/progress UI change runs `/design-verify` and logs
  an Uncanonized row.

## Parked with owners (not this batch)

- **Tenant memory / composer preview cost** (handoff risk 4 + review finding):
  `sheet_render` composer previews decode placed takes at full 4K, ignoring
  the imaging tier system — same memory class as the d92229a incident. Fold a
  tiered-decode (md for scale < ~0.5) into Release 2 or a perf follow-up, and
  consider bumping tenant memory in the provisioner.
- **Display nits** (fix opportunistically): lightbox fit-view label prints the
  md derivative's resolution; `.ref-grid` columns can exceed the thumb tier's
  256-px promise on wide 2× screens; `store.py:1010` stamps workbench-added
  panels `scale: MEDIUM` instead of inheriting; locked sheet editor removes
  `+ Add panel` instead of pointing to the workbench.
