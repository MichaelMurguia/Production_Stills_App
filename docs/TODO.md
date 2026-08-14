# TODO — improvements backlog

User-dictated improvements, recorded as given. An item leaves this list
in the same commit that implements it.

## 1. Reference panel — approved refs cannot be deleted (2026-08-13)

Approved references must not be deletable directly. The card's verbs
become:

- **Crop** — as today.
- **Reject** — rejecting the ref is what unlocks deletion (delete is
  available only on a rejected ref).
- **Edit** — new verb; opens editing of the ref, from which the user can
  delete it or add images to the ref.

So the approved-state row reads `Crop · Reject · Edit` — no bare
`Delete`.

## 3. Panels rail — render-in-progress spinner (2026-08-13)

When a render is in progress for a panel, that panel's thumbnail in the
PANELS rail must show a spinning indicator. Today there is no visible
sign in the rail that a render is underway.

## 4. One board across revisions + revision panel picker (2026-08-13)

Product-model change, user-specified. Today a revision forks the board;
approved takes strand on the old one. Instead:

- **One board per base spec id.** Revisions are versions of the same
  creative unit (the app already treats them so for carried rejections).
  The newest LOCKED revision defines the board's structure (panels,
  layout); a draft revision never changes the board.
- **Create revision opens a modal**: "What panels would you like to
  include in revision" — checkbox per panel. Checked = being revised
  (editable in the new draft; their old approved takes do NOT auto-seat
  on the board — each slot states "approved against R<n> — re-render or
  keep"). Unchecked = unchanged (come along read-only; their approved
  takes carry to the board automatically). An "also revise this panel"
  act on a read-only row upgrades the declaration mid-edit.
- Same panel approved in two revisions: newest wins by default; the
  existing swap-in take picker is the override.
- Boards-stage picker lists bases, not revisions. Readiness gates
  evaluate the newest locked revision's panel list but accept approvals
  from any revision. Derived panels (palette/materials) sample
  base-wide. One-time migration for existing per-revision boards.
- Provenance stated, never hidden: a slot filled from an older revision
  carries a `FROM R<n>` chip (each take already records its spec hash).
