# Handoff to Claude Design — input for implementation plan v3

**From the coding agent, 2026-07-29.** Read this alongside
`DESIGN_DISCREPANCY_REPORT.md` (the gap analysis) and
`app/static/DESIGN_SYSTEM.md` (the contract, now with four uncanonized
patterns and an updated changelog). This file is the forward-looking half:
what is now true of the app, what awaits your design decisions, and the
coding agent's recommendation on each so v3 can decide rather than research.

`design_handoff/current-dashboard-2026-07-29.png` is a live screenshot of the
shipped dashboard against the real Beltminers project — the mocks' data
assumptions are now real.

---

## 1. What is built since the mocks were drawn

All ten "needs data that doesn't exist" items from the discrepancy report
are implemented (report §7 has the table). The short version:

**Endpoints that now exist (all read-only unless noted):**

| Endpoint | Feeds |
|---|---|
| `/api/state` → `blocking[]`, `stage_summary`, `next` | dashboard lead, blocker rows, future nav sublines |
| `GET /api/activity?limit=n` | recent feed, human-phrased, newest first |
| `GET /api/screenplay/locations` | slugline coverage table (deterministic parse) |
| `GET /api/screenplay/citation-report` | citation re-check results (runs on every screenplay upload; report-only) |
| `GET /api/specs/{id}/slot-map?variant=` | slot geometry + per-slot verdicts, previews layout variants |
| `POST /api/specs/{id}/assemble` (+`variant`) | assembly with a recorded presentation layout |
| `/api/references` → `used_in` per ref | usage counts on cards |
| `/api/style-bible` → `rev` | bible revision badge (increments on save) |
| `/api/settings` → `engines{configured, source, last_test}` | honest engine status |

**UI shipped in the current four-stage nav** (all restructurable — nothing
here presumes final placement): dashboard DO-THIS-NEXT + BLOCKING + RECENT;
location coverage table inside the screenplay panel; slot map + layout picker
in the assembly section; used-in counts on reference cards; REV badge on the
bible editor; last-test PASS/FAIL in settings. Emoji are gone from buttons;
the mocks' own arrow labels (`→ Reference`, `→ Light study`) remain.

**Product rulings made by Michael that v3 must honor:**

1. **Layout is presentation grammar, not canon** (2026-07-29). Assembly
   offers `default | grid | hero:<panel>` variants; the variant is recorded
   on the board record; the locked sheet is never touched; the assembled
   board still requires approval. Mock 4b's "Change layout" should be
   designed as this variant picker, not as spec editing.
2. **Never upscale** — unchanged, and now visible in advance via the slot map.
3. **Citation re-check is report-only.** Broken citations surface as CITE
   blockers; specs are never auto-mutated. Copy must not promise automatic
   correction.

## 2. The four uncanonized patterns — please canonize in v3

Logged in `DESIGN_SYSTEM.md`'s table; CSS marked `/* UNCANONIZED */` at the
bottom of `styles.css`. Built with tokens only. They need proper design
judgment — spacing, weight, and whether they merge with existing patterns:

1. **DO-THIS-NEXT lead + blocking rows** (`.next-label/.next-row/.block-row/.block-kind`) — dashboard.
2. **Recent activity feed** (`.recent-row/.recent-ts`) — dashboard sidebar.
3. **Location coverage table** (`.loc-row/.loc-meter`) — screenplay panel; the segmented detail meter is new vocabulary.
4. **Assembly slot map** (`.slotmap/.slot/.slot-verdict/.slot-alert`) — proportional absolute-positioned slots; verdict chips use status tokens.

## 3. Open design decisions, with the coding agent's recommendations

These are yours to decide; recommendations are offered so v3 can be written
in one pass.

1. **Canonical navigation (report §2).** *Recommend:* the numbered stage
   band from mocks 1a/2a/3a, persistent on every screen, with Research and
   Settings right of the gap — drop 4c/4d's "Status · Pipeline · Research"
   text tabs and 3b/4b's band-less headers. The band's status sublines can
   be fed today from `stage_summary`; the `HERE` chip is the active view.
2. **Five-stage IA (report §1).** *Recommend:* adopt it in v3 as the
   centerpiece. The blockers that made it aspirational are gone: 01
   Screenplay gets the coverage table + citation report (already built, just
   re-parent out of the dashboard); 04 Panels is the judging room (plan v2
   Task 4 stands); 05 Boards is assembly + slot map (built). The dashboard's
   DO-THIS-NEXT/BLOCKING/RECENT becomes the landing surface under the band.
3. **Three providers, not two (report §4.1).** *Recommend:* Settings shows
   three engine cards — Gemini, GPT Image 2, and ChatGPT pipeline as a third
   card visibly annotated "uses the OpenAI key". Header engine dots stay at
   two (they reflect credentials, and there are two keys). The Default
   engine toggle needs all three.
4. **Placement of the four candidate actions mock 3b omits (report §4.9).**
   *Recommend:* keep Approve / Reject / → Reference as the primary group
   beside the staged render, and set Repair / Crop / → Light study / Delete
   forever as a ghost secondary row directly beneath it. No overflow menus —
   this is an operational tool; hiding destructive or daily-use actions
   behind a hover costs more than the cleanliness buys.
5. **Reference chips ALL/STYLE/SUBJECT/SCENE (report §4.5).** *Recommend:*
   bucket by `role_head`: STYLE = BOARD_LAYOUT_STYLE, BOARD_RENDERING_STYLE,
   CINEMATOGRAPHY_STYLE; SCENE = SCENE_REFERENCE, LOCATION_GEOMETRY;
   SUBJECT = everything else (likeness/geometry/prop roles carry subject
   suffixes). State the mapping in the plan so the coder doesn't invent one.
6. **Reject copy (report §4.3).** *Recommend:* keep the Reinstate action and
   write the card copy as "reject quarantines the file; reinstate returns it
   to provisional review" — never "for good".
7. **Spec-editor gate rule (report §5.1).** The plan v2 text is wrong; v3
   should state: the CANNOT-LOCK strip counts **required objects lacking a
   PASS evidence row** (missing row, HOLD, or REMOVE all block — this is the
   rule `validate_spec.py` enforces at approval). Backend `evidence_gaps()`
   already computes exactly this if a client-side mirror is unwanted.
8. **ID formats and status vocabulary (report §4.7–4.8).** v3 should direct
   the coder to render real formats — `CAND-0026`, `REF-0007`, `OBJ-003` —
   and note that LOCKED badges mean spec status APPROVED.
9. **Bible REV (report §3).** Now real (increments on save; currently REV 0
   until the next save). Just style the badge where 2a shows it.
10. **Evidence ledger presentation (report §4.6).** *Recommend:* keep it
    editable as plan v2 Task 3 decided; adopt mock 3a's columns as the
    *reading* order but keep inputs. Map: SOURCE column = `evidence_class`,
    CITED EVIDENCE column = the free-text `source` field.

## 4. Constraints that still stand from plan v2

- No renaming existing CSS classes; `app.js` generates against them.
- Amber budget: one primary action per screen; Courier for machine data.
- The judging-room restructure (plan v2 Task 4, mocks 3b) and the remaining
  plan tasks 1–3/5/6 are **still wanted and still unstarted** — v3 supersedes
  v2's task list; please carry them forward against the decisions above.
- The "no endpoint changes" ground rule can now be stated as: *the endpoints
  in §1 exist; anything beyond them stops and reports* — the same discipline,
  updated baseline.

## 5. Repo pointers

- `DESIGN_DISCREPANCY_REPORT.md` — full gap analysis, §7 buildability table.
- `IMPLEMENTATION_PLAN.md` — v2, to be superseded.
- `app/static/DESIGN_SYSTEM.md` — contract + uncanonized table + changelog.
- `design_mocks/*.png` — your eight screens.
- `design_handoff/current-dashboard-2026-07-29.png` — the shipped dashboard,
  live data.
- `app/insights.py`, `app/assemble.py::slot_map` — where the new data comes
  from, if the plan needs to reference shapes.
