# ADMIN_CONSOLE_FIX.md — three defects on /admin

**For the coding agent.** Corrects the operator console. Mocks: turn 12a
(header) and 12b (mint form + codes table) — `design_mocks/12a-admin-header.png`,
`12b-admin-console.png`. **This supersedes S1 in
`NON_CANON_REVIEW_2026-08-06.md`**, which ratified the page's density from the
queue's description rather than the built page. The page is not ratified.
Read `STORE_DESIGN_SYSTEM.md` first. One commit per task, X1–X4.

## X1 — The header link stops shouting

`.head-admin` is the only item in the header wearing a different typeface:
`font-family: var(--mono)`, `text-transform: uppercase`, `.08em` tracking,
and (until the last ruling) `--accent`. Three signals all saying "this one is
special" — and the only special thing about it is who can see it, which is
already handled by not rendering it for anyone else.

Its neighbours are `.head-links-nav a` — `color: var(--ink-dim); font-size:
13px;` in `--sans`, hovering to `--ink`. Match them exactly:

```css
.head-admin { color: var(--ink-dim); font-size: 13px; text-decoration: none; }
.head-admin:hover { color: var(--ink); }
```

No mono, no uppercase, no tracking, no amber, and **not one ink tier down**
either — a dimmer link is still a mismatch, just a quieter one. Sentence case
(`Admin`, already correct in the template). Add a 1px `--line` hairline
separator before it so position does the distinguishing. Keep it owner-only
and keep the title attribute.

The link sits in `.head-side` between `.head-links-nav` and the account
block, so the hairline goes on `.head-admin` as a `border-left` with
`padding-left`, not as a new element.

**Canon** (`### 9. Internal surfaces`, extending the S1 entry): *a link into
an internal surface is styled exactly like the public links beside it. Access
is not a visual style.*

## X2 — Cut the prose. All of it.

The console is the wordiest page in the store, on the one surface with nobody
to persuade. Delete these three `<p class="hero-sub">` paragraphs entirely:

1. **Debug tools** — "While text edit is on, Alt-click any text…" (3 lines).
   The checkbox label already says `Store text edit mode (Alt-click to
   rewrite)`. Keep one Courier line for the fact the label omits:
   `REWRITES APPLY FOR EVERY VISITOR AND SURVIVE DEPLOYS · CLEARING RESTORES THE AUTHORED COPY`.
2. **Mint a trial code** — "A code grants an arbitrary run…" (3 lines). The
   distinction it draws (code trials are ours, card trials are Stripe's) is
   real but belongs where it bites: on the **ON TRIAL** table, as a Courier
   footer — `CARD TRIALS ARE STRIPE'S · ONLY STRIPE ENDS ONE`. That is
   precisely why some rows have no `End now` button, and stating it there
   answers the question at the moment it is asked.
3. **Operations** — "The same functions the runbook calls by curl…" (3 lines).
   Replace with a Courier line under the buttons:
   `RECONCILE IS IDEMPOTENT · FLEET UPDATE REBUILDS EVERY LIVE STUDIO FROM REPO HEAD`.
   The destructive confirm already carries the long warning.

Also: `<h1>Admin</h1>` + the `OPERATOR CONSOLE` kicker is two titles for one
page. Drop the `<h1>`; the kicker becomes the page's Courier heading at the
scale the other section labels use.

Net: three paragraphs and one heading out, three Courier lines in, one of
them relocated to where it answers something.

## X3 — Enums are pickers, not text fields

`<input type="text" name="tier" value="personal">` is a free-text field for a
two-value enum. A typo mints a code for a tier that does not exist. This is
the same defect class as a dropdown whose only option was an error message:
**a control whose valid answers are known must never be free text.**

- `EDITION` → `<select>` with `Personal` / `Business`, default Personal.
- `CODE STALE IN (DAYS, 0 = NEVER)` → `CODE EXPIRES` `<select>`:
  `Never` / `30 days` / `90 days`. A parenthetical instruction inside a label
  is prose in disguise; the picker states the same fact as a control.
- `DAYS` and `REDEMPTIONS` stay numeric (genuinely open ranges), but shorten
  the labels — `DAYS OF ACCESS` → `DAYS`, `TIMES REDEEMABLE` → `REDEMPTIONS`.
  The column they sit in is already `MINT A TRIAL CODE`; nothing else could
  be counted.
- Lay the form out as a **fixed-track grid** (`120px 160px 130px 150px
  minmax(0,1fr) auto`), labels above fields, `align-items: end` so every
  field and the Mint button share one baseline. The current `<br>`-separated
  labels in a flex-wrap row give five different field heights.

**Canon** (`### 9`): *a field with a known answer set is a picker. Free text
is for names, notes and addresses only.*

## X4 — Table polish

The two tables are right in kind — keep them Courier, keep one-word states in
status colours, never amber. Two corrections:

- Give both tables **fixed column tracks** rather than auto-width `<table>`
  cells, so `CODE`/`STATE` do not reflow as notes change length.
- Row action buttons (`Withdraw`, `End now`) render in **Archivo, not
  Courier** — they are verbs, not machine values. `.admin-act` should set
  `font-family: var(--sans)` (confirmed defined in `store.css` as
  `'Archivo', sans-serif`).

## Close-out

Update the S1 entry in `STORE_DESIGN_SYSTEM.md`'s changelog to record that
the console's density was corrected on review of the built page, not
ratified. Add the two `### 9` rules above. Delete this file when shipped.
