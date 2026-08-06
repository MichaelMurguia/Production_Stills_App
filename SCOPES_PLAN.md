> **PARKED — user ruling 2026-08-06. Read this before building.**
>
> Not now, and the top level gets a name. The user's model, verbatim:
> *"An org has many studios. A user admins the org. Maybe the admin adds
> another admin. Maybe not. No roles."*
>
> **This is a smaller change than this plan, not a bigger one.** An earlier
> note here guessed at members, seats, invitations and role tiers; that was
> wrong and the user corrected it — *"I'm trying to scope less, not more."*
> There is no membership system, no seats, no permission matrix. Admin is
> binary: a user either administers the org or does not, and a second admin
> is a maybe, not a requirement.
>
> The resulting hierarchy is this plan's, with the top level named:
>
> | scope | what it is | owns |
> |---|---|---|
> | **Organization** | the account-level container, administered by one user (possibly more later) | many studios |
> | **Studio** | one license | credentials, enabled catalog, default models per role, workflow instructions; contains productions |
> | **Production** | unchanged | its screenplay, bible, sheets, panels, boards |
>
> So A2–A5 stand largely as drawn — the address line's first segment is the
> org rather than "you", and A5's *user scope* becomes *org scope* (identity,
> billing, which studios the org holds). What must NOT be built: roles,
> invitations, seat counts, or any per-user permission on a studio.
>
> **The one question still open:** does a second studio mean a second Railway
> service (today's model — one service per cloud purchase, one workspace per
> purchase on the account page) or a second folder inside one install (what
> A1 describes)? Those are different builds and the plan does not say which.
>
> A1 also moves `settings.json` (live API keys) and restructures `data/` on
> running tenants — that migration wants its own verification pass and a
> backup taken first, not a ride-along with a UI release.
>
> A6's reasoning survives unchanged and is the part worth keeping whatever
> the naming settles on: a production never leaves the scope it was approved
> under, and standalone shows the hierarchy inert rather than hidden.

# SCOPES_PLAN.md — user ▸ studio ▸ production

**For the coding agent.** Mocks: `design_mocks/11a-address-line.png`,
`11c-lobby.png`, `11d-scope-ownership.png` (all 1360px, drawn on the shipped
header and band). Read `app/static/DESIGN_SYSTEM.md` first.
Tasks A1–A7, **in order — A2 onward all depend on A1.**

## What already exists (verified in source, do not rebuild)

The **production** switcher is built and correct: `#brand-project` gains
`.brand-switch`, click fetches `/api/projects/summary` and renders
`.proj-menu` with a preview line per row, `+ New production`,
`Manage productions…`, and the Courier foot
`SWITCHING RELOADS THE STUDIO…`. Inline rename on `#brand-rename` works.
That is PRODUCTIONS_PLAN M4/M5 and it stays as-is.

## What does not exist

**The studio scope — at all.** No model, no endpoints, no `data/` level;
`grep` for `studio_slug` finds nothing but a comment. So the address line
cannot be built as a UI change: today's switcher is one segment because
there is only one level to switch.

## A1 — The studio model — BACKEND FIRST

A studio is **one license**. It owns credentials, the enabled model catalog,
default models per role, and workflow instructions; it contains productions.

- `data/` gains a studio level above productions; `settings.json` moves into
  it. Existing single-studio installs migrate into a default studio — do not
  ask the user to name it during migration; name it from their account and
  let them rename later.
- Endpoints: `GET /api/studios/summary` (per studio: slug, name, license
  state, credential state, production count, enabled model count),
  `POST /api/studios/activate`, `POST /api/studios/rename`,
  `POST /api/studios/create`.
- `/api/projects/summary` gains the active studio's slug so the production
  menu can state which studio it is listing.

**The standalone build is one studio by definition.** It runs the same model
with exactly one row — see A6.

## A2 — The address line (mock 11a)

Extend `.brand-sub`, do not add chrome. It becomes three segments, separated
by `/` — the name is already a mono machine value at .1em tracking, and a
slash is what reads as an address in that face (not `▸`).

```
[KP tile] / NORTHLIGHT / THE BELTMINERS ▾   ✎
```

- **User segment** — a 19px Courier initials tile on `--panel2`/`--line`.
  Identity is a destination, not a place you work, so it is a tile and not a
  name. Opens the account menu (A5).
- **Studio segment** — `--ink-dim`, opens the studio menu (A3).
- **Production segment** — `--ink` 700, keeps today's `.brand-switch` menu and
  the `▾`. **The rename pencil stays bound to this segment only** and stays
  hidden until `.brand:hover`, exactly as canon has it.
- Every segment `flex: none; white-space: nowrap`. The line never wraps; it
  is one machine value.

## A3 — The studio menu

Same `.proj-menu` grammar, headed `STUDIO — N LICENSED`. Each row: name plus
a Courier preview of the two facts that decide whether work can happen there
— production count and credential state
(`3 PRODUCTIONS · OPENROUTER · 14 MODELS` / `1 PRODUCTION · NOT CONNECTED`).
Active row carries the amber left border and `--panel2`. Foot row:
`Add a studio`. Reuse the reload-and-foot-warning pattern verbatim.

## A4 — The lobby (mock 11c)

The shipped Productions view keeps its cards, reach bands and next verbs;
they **group under studio headers**. Header per studio: name, a Courier fact
line (`LICENSED · OPENROUTER · 14 MODELS ENABLED`), and a right-aligned
`Studio settings` link. A studio with no credential states it in the header,
so its dead production explains itself without a modal.

Two dashed cards close the grid: `New production` (starts at 01 with this
studio's engines and instructions) and `Another studio`, whose amber
`Add a license` is the **only** amber on the view. Buying sits next to what
it produces rather than in a menu.

Productions is a tool view, so **the band arrives condensed** per the
two-mode band (`body.tool-mode`) — already shipped.

## A5 — Split Settings by scope (mock 11d)

Nothing new is invented: every studio-scope item is already a Settings tab.

- **Studio scope** — `AI & engines`, `Workflow & instructions`, `FAQ`,
  `Debug tools`. The tab set is unchanged; it is now studio-scoped, and the
  storage line must say so once `settings.json` has moved.
- **User scope** — a small account menu off the initials tile: sign-in and
  identity, billing and receipts, which studios you hold. **This is the only
  added surface in the whole pass.**
- **Production scope** — the five stages plus Reference, unchanged.

## A6 — Two consequences to get right

1. **A production never leaves the studio it was created in.** No move, no
   transfer, no reassign — do not build one, and do not expose a studio
   dropdown on a production. The studio's credentials, enabled catalog and
   instructions are the conditions under which that production's entire
   reference library was approved and every panel was judged; moving it would
   invalidate the approval record. If a user wants the same movie in another
   studio, that is a **new production** (a copy of the screenplay, starting at
   01) — state it that way in any copy that comes up.
2. **Standalone shows the hierarchy, inert.** One studio, so the studio
   segment renders as text with no `▾` and no menu — it is not hidden. Same
   product, one license deep; hiding it would make the cloud build look like
   a different application.

## A7 — Canon

Add to `DESIGN_SYSTEM.md`: the three scopes and what each owns (Layout
patterns) — this is the ruling the rest of the product will be measured
against; the address-line pattern and its slash separator (Components); the
initials tile as the user segment (Icons). Changelog once. Delete this file
when A1–A6 ship.
