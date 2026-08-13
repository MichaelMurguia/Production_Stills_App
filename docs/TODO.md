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

## 2. Panel rendering — selectable palette swatches (2026-08-13)

Panel rendering today always references the full color palette — all 19
swatches go into every render. Instead, individual swatch references
must be selectable per panel, not all-or-nothing. The selector lives in
a dropdown at the top of the rendering settings.

## 3. Panels rail — render-in-progress spinner (2026-08-13)

When a render is in progress for a panel, that panel's thumbnail in the
PANELS rail must show a spinning indicator. Today there is no visible
sign in the rail that a render is underway.
