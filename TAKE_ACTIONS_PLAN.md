# TAKE_ACTIONS_PLAN.md — the take viewer's action row, and the door preview

**For the coding agent.** Two small passes from the same morning's review.
Mocks: `design_mocks/14a-take-actions.png` (panel take viewer) and
`store-14a-workspace-door.png` (storefront account page). Read
`app/static/DESIGN_SYSTEM.md` first. T1–T3, then S1–S2.

---

## T1 — Tags float on the image

The action row under the shown take overflows its column and scrolls
horizontally. **Horizontal scroll on navigation is never acceptable** —
actions that scroll out of view are actions the user cannot find.

Root cause is that the row carries both the state/identity tags and the six
verbs. Move the tags onto the image: state chip top-left, take identity
bottom-right, each on `rgba(11,12,14,.82)` with a `--line` border so they
read on any take. The picture stays the evidence; the row below is verbs only,
and then it fits.

Clicking the image (not a chip) opens the existing lightbox with the clean
full-screen take, so the overlay costs the user nothing.

## T2 — The six actions are six buttons

`app.js` builds all six as `mk(label, "ghost")` — Approve flips the
candidate's status, `→ Full-size take` and `Repair region` open render
modals, `→ Reference` opens the promote dialog, `Crop → reference` the crop
tool, `→ Light study` a derived render. They are **peer verbs**, but the
current CSS renders one as a button and five as bare text links, which reads
as one action plus five footnotes.

Give all six the ghost-button border. Approve keeps its `--ok` border and
text (it is the row's consequential act, and green is its state colour, not
an emphasis). The row wraps to a second line when the column narrows —
never scrolls.

**Canonical rule** (Components): *a row of peer verbs renders in one
grammar. If they are all `mk(…, "ghost")` in the source they are all ghost
buttons on screen; a bare text link in a button row states a hierarchy the
code does not have.*

## T3 — Canon

Add T1's overlay-tag pattern (tags on the image, verbs beneath) to Layout
patterns, with the no-horizontal-scroll rule stated. Add T2's peer-verb rule
to Components. Changelog once.

---

## S1 — The workspace door shows the work

`storefront` account page, the `ACTIVE` studio box. It is all infrastructure
— URL, rename form, terms — and shows nothing of the movie behind it.

Add a preview above the name row: **one random approved render from that
studio**, re-picked per page load, 180px tall, `object-fit: cover`, with a
Courier provenance chip bottom-right naming production and board
(`THE OXCART · BOARD-0001`). Approved only — the door shows finished work,
never a rejected take.

No renders yet → the canonical `.hatch` block at the same height with its
stated chip: `NO RENDERS YET — THE FIRST APPROVED PANEL LANDS HERE`. (Use the
class per `HATCH_RULE.md`; do not re-declare the gradient.)

The whole preview block and the amber button share one target: the workspace.

**Needs a small endpoint.** The storefront cannot read the tenant's `data/`,
so the studio exposes `GET /api/preview-render` returning one random approved
panel's thumb URL plus its production and board ids, cached briefly. If that
is not ready, ship the hatch state — it is correct, not a placeholder.

## S2 — Hierarchy: the name leads

In the same box, the URL is currently the largest type on the card and the
studio name appears only inside the rename field. That is backwards.

- **Studio name** — 22px Archivo 600, the card's headline. It is what the
  user chose, what they rename, and how they refer to the place.
- **`LIVE`** — beside the name, where a status belongs.
- **URL** — demoted to a Courier link beneath it in `--ink-faint`. An address
  is machine data; it was only loud because it held the biggest type.
- Everything below is unchanged: rename form, the `WILL BE —` live preview,
  and the release-first terms paragraph.

Delete this file when T1–T3 and S1–S2 ship.
