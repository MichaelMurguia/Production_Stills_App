# STORE_DESIGN_SYSTEM.md — the storefront

**For the agent working on `storefront/`.** The product app's system
(`app/static/DESIGN_SYSTEM.md`) governs the studio. This file governs the
public site. Same language, different surface: class names here are NOT
frozen, so restructure markup freely — but the rules below are binding.

Add to the storefront's notes: *store UI must follow
`STORE_DESIGN_SYSTEM.md`.*

---

## Inherited without change

- **Amber is a signal.** On a sales page it marks the one action you want
  taken in a section — never decoration, never a heading color.
- **Courier carries machine data**: IDs, dimensions, counts, categories,
  status, trait lists, provenance. Archivo carries hierarchy and prose.
- Square corners. No frameworks, no additional fonts, no emoji, no
  gradients except a hero scrim.
- Tokens: `--bg #0b0c0e` (store base, one step darker than the app),
  `--panel #15181b`, `--panel2 #21252a`, `--line #2b3037`,
  `--line-soft #23272c`, `--ink #eceef0`, `--ink-dim #9aa1a8`,
  `--ink-faint #6b7278`, `--accent #e0a33f`, `--ok #6fae7a`,
  `--hold #7d8fd0`, `--bad #cd6155`.

## Store-only rules

### 1. Imagery is the argument
This product makes pictures; the page is mostly pictures. Every image on
the storefront is **real output from a real production** — never stock,
never a placeholder, never an illustration of a feature. If a section needs
an image that doesn't exist yet, cut the section.

### 2. Motion
Three permitted kinds, all decorative, all behind `prefers-reduced-motion`:
- **Drift** — slow vertical parallax on a gallery, `ease-in-out infinite
  alternate`, 14–26s, adjacent columns at clearly different rates and
  directions. Never fast enough to read as scrolling.
- **Marquee** — one-direction `linear infinite` strip, ≥45s, content
  duplicated so the loop is seamless. `aria-hidden`.
- **Cross-fade** — `opacity .7s ease` between stacked panes; the container
  never resizes.
Type never animates. Nothing bounces, slides in on scroll, or parallaxes
under the reader's copy.

### 3. Copy over an image
Copy sits on a scrim, never on picture. Use one angled linear-gradient from
~95% opaque on the copy side to ~35% on the image side; the copy column is
fully still while the image moves behind it.

### 4. Trait lists sell an edition
A pricing card's middle block is a Courier list: the `■` traits in `--ok`
(four or five), then **exactly one** `□` tradeoff in `--ink-faint`. Both
editions carry a tradeoff. A card with only upsides reads as marketing; a
card that names its cost reads as a spec sheet, which is what this audience
trusts.

**Parity rule (ruled 2026-08-03, STORE_PRICING_PLAN K2):** when two
editions are presented side by side, any trait true of both appears in
**both** lists, in the same position. A trait present in one column and
absent from the other is read as a difference between the editions,
whatever the footnotes say.

### 5. Gates are stated, never errored
Unconfigured checkout, missing mail, missing Google: render as a visible
stated condition (SETUP notice in `--hold`, disabled control, Courier
`UNAVAILABLE — …` line). Never a toast, never a red error, never a
hidden control.

**A dated future state names the date and the consequence as two facts**
(S2, ruled 2026-08-06). "Ends" alone is not a consequence. Worked
example: a trial's account line reads `TRIAL — N DAYS LEFT` with a
Courier line beneath stating both — `CONVERTS 18 SEP 2026 · YOUR CARD IS
CHARGED THEN AND THE STUDIO KEEPS RUNNING` for a card trial versus
`ENDS 18 SEP 2026 · NO CARD ON FILE · THE STUDIO STOPS SERVING ON THAT
DATE` for a granted one. The two futures are different and a single
"ends" sentence would flatten them.

### 6. Provenance lines
A faint Courier line naming what is shown accompanies gallery sections
(`SHOWN — THE BELTMINERS · EXT. CHARLIE'S CABIN · KYRA COSTUME AND ACTION
STUDY`). It converts decoration into evidence. **A provenance line names
the work being shown. It may carry a count only when the count is
impressive on its own terms; a small true number invites the wrong
comparison and undersells a young product. Never inflate — reword.**
(Ruled 2026-08-01: "41 approved panels" was doing sales work and the
honest figure was 7 — so the line names the work instead. Rules and
guarantees — 3840×2160, 100%, 0 — are not tallies and keep their
numbers.)

### 7. Vocabulary
Use the profession's words, correctly: production design, art department,
art direction, art direction bible / lookbook, script breakdown, set,
set dressing, picture vehicle, prop, atmosphere, continuity, concept
board, panel, plate. Never "AI art", "prompt", "generation" in sales copy
— the buyer is a production, not a prompter. "Render" is fine.

### 8. Amber has four sanctioned roles on the store — and only four

**This rule deliberately differs from the product app's.** In the app, amber
is scarce because the user is working and needs one obvious next action; the
app's "section titles do NOT get amber" is correct *there* and does not apply
here. The store is a document that has to be skimmed, and its amber is the
reader's index. Do not carry the app's amber rule across, and do not strip
amber from the store mocks to satisfy it.

| Role | What it is | Cap |
|---|---|---|
| **Fill** | Solid `--accent` background, `--accent-ink` text. The action you want taken. | **1–2 per page.** Hero CTA; the recommended plan's Buy. Never two side by side. |
| **Kicker** | Courier, ~10–11px, `.2em+` tracking, uppercase. Names the section or step you are in. | **One per section**, on the section's own kicker or step label — not on its `<h2>`, which stays `--ink`. |
| **Highlight** | `rgba(224,163,63,.16)` background on inline text. | **Only to show the software reading something** — extracted phrases in a breakdown, a scanning state. Never for emphasis in prose. |
| **State** | Border/text on the one active item in a rail, stepper or tab set. | **One active item per control.** |

Everything else — body copy, headings, facts, borders, badges, secondary
buttons — is ink or a status color. Before shipping, count the **fills**;
the other three roles are structural and self-limiting.

Also note: a green/blue/red footnote label (`THE GATE`, `WHAT HOLD MEANS`)
is a **status** kicker, not an amber one. Use the status color when the
label names a state the software enforces, amber when it names where the
reader is.

### 9. Internal surfaces

Ruled 2026-08-06 (S1 + ADMIN_CONSOLE_FIX), from the operator console.

**An owner-only page wears the store's shell and none of its
persuasion.** Header, footer and type scale stay — it is the same site,
one nav, one account session, and inventing a second chrome for one page
is a maintenance tax with no reader benefit. The sales furniture does
not come with it: no hero rhythm, no trait lists, no provenance lines,
no marquee. The body is a Courier console — facts line, state tables,
buttons. **One fill maximum**, on the page's single consequential act.

**A link into an internal surface is styled exactly like the public
links beside it.** Access is not a visual style. The console's `Admin`
link is 13px `--ink-dim` sans, sentence case, identical to its
neighbours, separated by a hairline rather than by typeface — and *not*
one ink tier down, which is a quieter version of the same mismatch. Who
may see a link is handled by not rendering it for anyone else. An amber
"role marker" would be the first amber whose meaning is *who you are*
rather than *what to do* — which is how a four-role budget becomes six.

**A field with a known answer set is a picker.** Free text is for names,
notes and addresses only. A text input for a two-value enum lets a typo
create a record for something that does not exist. A parenthetical
instruction inside a label (`CODE STALE IN (DAYS, 0 = NEVER)`) is prose
in disguise: the picker states the same fact as a control.

**The console states and acts.** It is the one surface with nobody to
persuade, so explanatory paragraphs are deleted outright; what survives
is the operational fact each was burying, as a Courier line placed where
it answers a question at the moment it is asked (`CARD TRIALS ARE
STRIPE'S · ONLY STRIPE ENDS ONE` belongs under the trials table, where a
reader is wondering why some rows have no End now). One title per page —
the Courier kicker is the heading; no `<h1>` beside it. Machine tables
get fixed column tracks so values stop reflowing; row action buttons are
verbs and render in Archivo, not the table's Courier.

### 10. Provider marks

Ruled 2026-08-06 (SIGNIN_BRANDING G3).

**A sign-in option wears its provider's official button** where the
provider publishes branding guidelines (Google does:
developers.google.com/identity/branding-guidelines). The button is the
provider's mark, not ours to restyle — no token colours, no Courier, no
amber, and its hexes are deliberately outside the token system. Providers
without published guidelines get our own secondary-button grammar with
their brand icon. **Our amber stays on our own actions**: with Google
wearing its own mark, `Email me a sign-in link` is the page's fill in
both configurations, and the two no longer compete in one visual voice.

**The branding values are not ours to tune.** An approved button that has
been "adjusted to fit" is no longer an approved button. Ship the delivered
snippet's values literally: `#131314` fill, `#8E918F` 1px stroke, `#E3E3E3`
Roboto Medium 14px, the 18×18 full-colour G — never mono, never on a
coloured chip — 40px minimum height, 12px gap and padding.

**The radius exception, stated.** This product is square-cornered
(`--radius: 0`). Google's mark specifies **4px**, and the third-party brand
wins inside its own button: a modified sign-in button reads as a phishing
affordance to exactly the users trained to trust the real one. **Nothing
else on the page borrows this radius**, and a contract asserts it stays the
only rounded rule in the stylesheet.

**The mark is a shipped asset, never rebuilt.** `google-g.svg` is served
locally from `storefront_img/` — never hotlinked, never recoloured, never
hand-inlined as paths. **Only Google's own strings**: `Sign in with Google`
and `Sign up with Google` by context; the alternatives the guidelines
exclude are excluded here too, and the contract fails the build on them.

Sibling to the app's icon rule (LobeHub tiles): *tiles identify a
provider inside our chrome; sign-in buttons are the provider's chrome and
follow the provider's guidelines.*

---

## Non-canon — awaiting review

**The store's review queue.** Same job as the app's `## Uncanonized
patterns` table and deliberately in the same structural position — a
designer asked to "review the non-canon items" reads THIS table, not the
changelog. (The changelog records what changed; it is history, not a
queue. Store items lived only there until 2026-08-06, and a design
review could not find them.)

Every new store feature lands here in the same commit that ships it —
genuinely new patterns and pure reuse alike. At ~4 rows, tell the user
the store has accumulated work worth a design review: they open their
design-review Claude chat with this folder connected (re-synced so it
sees current files) and ask it to review this table. The resulting plan
implements against THIS file, never the app's. Ruled rows are deleted
here and recorded as a dated `RULED (...)` changelog entry below.

| Date | What it is | Where | What the designer should rule on |
|---|---|---|---|

| 2026-08-07 | **Fleet storage table** on the admin page — every live studio's free space, largest consumer, and a state (`OK` / `TIGHT` / `REFUSING` / `UNREACHABLE`), fetched after page load and sorted worst-first. Built from canon: `.license-box`, `.admin-table.mono`, `.admin-note`. Only `REFUSING` carries colour, and it is `--bad`, not one of the four amber roles. | Admin, between trials and operations | Is a table right, or should a healthy fleet collapse to one line and only expand when a studio is in trouble? And is `UNREACHABLE` the right word for a studio that answers but cannot measure itself? |
| 2026-08-09 | **Responsive marketing imagery** — the hero wall, marquee, and pipeline-demo stills now serve WebP `srcset` derivatives at display-matched widths (build: `scripts/build_images.py`) instead of the raw multi-MB PNGs; the social card (`og:image`/JSON-LD) is a purpose-cropped 1200×630 JPEG and the coming-soon backdrop a 1600px WebP. No visual change — same images, same layout, smaller bytes. Built from mechanics, not a new visual pattern. | Landing (`index.html`), `base.html` head, `coming_soon.html` | Pure infra — review only: are the chosen display widths/sizes hints right for the wall (≈380px) and marquee (≈150px tall), and is a JPEG social card acceptable vs. a bespoke share image? |

---

## Changelog

- **2026-08-07** — Admin gains a **fleet storage table**: every live studio's
  free space, largest consumer and state, read server-to-server the same way
  the preview door reads a studio. A studio that will not answer reads
  UNREACHABLE, never 0 bytes — a dead studio must not look like a full one.
  The refusal threshold is the product's own, so the two cannot disagree
  about when a studio has stopped rendering.

- **2026-08-06** — S1 completed (user-caught): the door was showing
  `NO RENDERS YET` on a studio that **had** an approved panel. A surface
  may claim "nothing here" only when it has looked. The studio now exposes
  `GET /api/preview-render` (behind its own access token — never public:
  that would publish a customer's artwork to anyone who guessed a
  subdomain), the store asks it server-side with the token it already
  holds and proxies the bytes, and the door fills its hatch in
  asynchronously so the account page never waits on a customer's service.
  Until the answer lands the chip states what is true — that it is
  looking — rather than asserting an emptiness it has not verified. An
  unreachable studio leaves the door working with a stated condition.

- **2026-08-06** — CORRECTION (GOOGLE_SIGNIN_SNIPPET.html, delivered): the
  first pass at §10 was built from the plan's prose and got three things
  wrong. The snippet is the authority for its element and now ships
  transliterated: **4px radius** (the stated exception — the one place this
  square-cornered product yields), the **shipped `google-g.svg` asset**
  instead of hand-written paths, and Google's **approved string** — the
  earlier build used the one the snippet names forbidden, which the mock
  still shows. Snippet outranks mock. Also removed the Google Fonts
  `<link>` for Roboto that the first pass added: the snippet forbids it.
  **Still outstanding:** Roboto is not bundled — no font binary exists in
  the repo and none can be authored here — so the button renders in
  Archivo via the snippet's own fallback stack until the two .woff2 files
  are added to the storefront. Everything else about the button is exact.

- **2026-08-06** — RULED (TAKE_ACTIONS S1–S2, mock store-14a): the workspace
  door leads with the **studio name** at 22px Archivo 600 — it is what the
  user chose, what they rename, and how they refer to the place — with
  `LIVE` beside it and the URL demoted to a faint Courier line beneath.
  An address is machine data; it was only loud because it held the biggest
  type. The account page's third statement of the same address is deleted.
  **S1 ships its hatch state, deliberately:** the render preview needs a
  `GET /api/preview-render` on the studio that does not exist yet, and the
  plan is explicit that the hatch is correct rather than a placeholder. It
  uses the canonical `.hatch` class per HATCH_RULE with its stated chip.
  Note for whoever builds the endpoint: it must NOT be unauthenticated —
  it would publish a customer's approved artwork — so it needs the
  workspace access token and the store must proxy the image, which is why
  it is a follow-up rather than a line of markup.

- **2026-08-06** — RULED (SIGNIN_BRANDING G1–G3): `### 10. Provider marks`
  established. The Google button is Google's official dark-neutral variant
  with the full-colour G at 18px, its values deliberately outside the token
  system; our amber returns to `Email me a sign-in link` in both
  configurations, with a two-hairline Courier `OR` between them.
  **Deviation reported:** the plan said to ship Roboto 500 locally and never
  hotlink. The store has never shipped a font locally — `base.html` has
  always loaded Archivo from the Google Fonts CDN — so Roboto 500 rides that
  same existing link rather than becoming the one local font. Shipping one
  and hotlinking the other is the inconsistency the rule guards against. If
  the designer wants both local, that is an asset task, not a markup one.

- **2026-08-06** — RULED (user, reversing S2's Business position): **both
  editions trial.** The trial page offers `Start Personal Trial` and
  `Start Business Trial`; §8 still holds — Personal takes the page's one
  fill as the common path and Business sits beside it as a ghost, never
  two fills side by side. Each edition renders only when its own price id
  exists, the same readiness rule the pricing cards use. The cloud card's
  "Business is not self-serve trialable" line is deleted: it was true for
  four hours and is now false. Trial length default 5 days.

- **2026-08-06** — RULED (ADMIN_CONSOLE_FIX X1–X4, mocks 12a/12b): the
  console's density was **corrected on review of the built page, not
  ratified** — S1 had ratified it from the queue's description. The header
  link drops mono/uppercase/tracking/amber for an exact match with its
  neighbours plus a hairline; every explanatory paragraph is deleted (three
  out, three Courier lines in, one relocated to the table it explains); the
  duplicate `<h1>` goes and the kicker becomes the heading; EDITION and CODE
  EXPIRES become pickers on a fixed-track grid; both tables get fixed column
  tracks and their row acts render in Archivo. Folded into `### 9`.
- **2026-08-06** — RULED (S1): `### 9. Internal surfaces` established — an
  owner-only page wears the store's shell and none of its persuasion, one
  fill maximum, state tables in status colors. The `ADMIN` link is not a
  fifth amber role: §8's four roles all answer "where should the reader look
  next", and an owner already knows they are an owner.
- **2026-08-06** — RULED (S2): the trial page's two doors become one door
  and an escape hatch — the code box collapses to a single expanding line,
  because a peer box plants "do I need a code?" in every visitor who does
  not have one. The date pair is canon (§5). Entry points ratified as built.
  Business is deliberately not self-serve trialable and the cloud card now
  states that position rather than leaving it to be discovered.
- **2026-08-06** — RULED (S3): studio naming copy and placement ratified;
  the terms line now leads with the consequence that costs something (the
  released name), because a skimmed faint line is read first-clause-only.

- **2026-08-06** — RULED (user): the header carries the `ADMIN` link and
  nothing else. The Debug toggle added to the header on 2026-08-03 is
  removed — a debug control belongs inside the admin section, not in the
  chrome every page wears. The armed chip stays and now names its real
  exit (`EXIT ON /ADMIN`): a mode that changes what a click does must
  state itself and its exit wherever the owner is standing. Dead
  `.head-debug` CSS deleted, grep-proofed; a store contract asserts the
  header stays clean.

- **2026-08-06** — CORRECTION (not a new pattern): `--hold` was used by the
  engine band's condition row (`.eb-hold`, ruled by STORE_PRICING_PLAN K1),
  the setup notice, the router status blocks and one template, and was
  **never defined** in `store.css` — those rules fell back to inherited ink,
  so a ruling that shipped on 2026-08-03 was not actually rendering. Defined
  as `#7d8fd0`, inherited unchanged from the app system. `--warn` deleted in
  the same pass for the reason the app deleted it (R3): it aliased the
  accent, and a second amber token is how a fill budget quietly breaks. Its
  one user (the header Debug chip) is now `--hold`, which is what an armed
  debug mode is. `storefront/tests/test_store_tokens.py` now fails the build
  if any `var(--x)` has no `--x`.
- **2026-08-06** — Non-canon: the operator console (`/admin`, user-directed).
  A **new surface class for this store**: an internal, owner-only page
  wearing full store chrome — facts line, debug tools, trial minting, two
  Courier state tables (one-word states in status colors, never amber), and
  the operations that were previously curl-only as buttons. Its one amber
  fill is Mint. Reached by an **`ADMIN` header link in Courier amber, left
  of the avatar**, rendered only for an `OWNER_EMAILS` session — the first
  time the store's chrome has carried a role-conditional item. The debug
  tools moved here off `/account`, which returns to being purely the
  customer's view of their own purchases. Designer to rule on: whether an
  internal console should wear the sales chrome at all (it may want reduced
  chrome or its own header treatment), the amber `ADMIN` link against §8's
  four roles (it is arguably a fifth: a role marker, not a fill/kicker/
  highlight/state), and the facts-line density.

- **2026-08-06** — Non-canon: the trial surfaces (TRIALS_BUILT, user-directed).
  Four store-side pieces need a ruling. (1) `/trial` is a **two-door page** —
  a card-trial box carrying a §4 trait list (four ■, one □ naming the charge)
  with the page's single fill, above a code-redemption box; when a trial is
  already running the page stops selling and reports the state instead
  (days left, the date, and what happens on it). (2) A **stated date pair**
  on the account page: the license label carries `TRIAL — N DAYS LEFT` and a
  Courier line under it states the date AND the consequence separately
  (`CONVERTS 18 SEP · YOUR CARD IS CHARGED THEN` vs `ENDS 18 SEP · NO CARD
  ON FILE · THE STUDIO STOPS SERVING`), because those are two different
  facts. (3) `/admin/trials` is a **new surface type** — an internal
  table-driven operator console on store chrome (mint form, codes table with
  a one-word state column, people table with per-row acts). Nothing like it
  existed; it may deserve its own reduced chrome. (4) Two entry points: a
  `Try free` header link for signed-out visitors, and a Courier line on the
  cloud edition card (deliberately not a third fill). Built from canon
  vocabulary throughout — no new tokens, no new amber fills on any page.
  Designer to rule on: the two-door page's order and whether the code box
  belongs on the same page at all, the console's chrome, and the date-pair
  copy.

- **2026-08-01** — Storefront system established with the homepage rebuild:
  the Wall hero, Standalone/Cloud trait-list pricing, filmstrip, and the
  five-stage pipeline dissolve.
- **2026-08-01** — §8 rewritten. The original "two amber elements maximum"
  described neither mock (the homepage runs 13 amber elements, /pipeline 19)
  and would have forced Claude Code to either gut the approved design or
  ignore the design system on its first commit. Replaced with the four-role
  taxonomy — fill / kicker / highlight / state — which is the system the
  approved pages actually use. Only fills are capped.
- **2026-08-01** — `/pipeline` added: the long walk (five stages, sticky
  rail, per-stage gate footnotes) followed by the case file.
- **2026-08-01** — `/pipeline` implemented per STORE_PIPELINE_PLAN. One
  correction under §6 (true numbers): the mock's placeholder figures were
  replaced with the production record's — 124 pages read, 6 design
  languages (of 9 proposed), 7 panels approved, 1 board assembled; the
  stage-4 artifact is CAND-0042 (3136×1344, region repair of CAND-0040,
  promoted REF-0042) with its real carried rejection quoted; the case-file
  header reads 2 nights · 6 takes · 1 approved exterior. Layout, copy
  structure and all five concept footnotes follow the mock.
- **2026-08-01** — Non-canon: studio naming terms + Claim/Rename button.
  The account form's button reads "Claim name" while the studio wears its
  auto-assigned slug and "Rename" after (user-directed); a faint terms
  line under the form states what a rename does and does not do ("only
  the URL and studio name change… previous name is released… one studio
  per license"). Built from canon — review copy/placement only.
- **2026-08-01** — RULED (STORE_ROUTER_PLAN T1/T2): the router's two
  failure pages serve opposite audiences and must not look alike. The
  unclaimed address is the one failure page that sells — full store
  chrome, the address as the Courier H1, prefixed claim path, the
  invited-visitor line (`router_unclaimed.html`, 404). The not-answering
  page is a trust moment — wordmark only, nothing to buy, reassurance
  about the work first, honest status block, real 15s recheck
  (`router_unreachable.html`, 503 + Retry-After). Both zero-JS for
  content; assets absolute to the store host.
- **2026-08-01** — RULED (STORE_ROUTER_PLAN T3): the reliable-door
  mechanic was confirmed; its footnote became a stated block — a --hold
  PROVISIONING chip above the button on --field with the 2px --hold left
  border, unchanged copy — and the YOUR STUDIO label wears a bordered
  --ok LIVE chip once the branded name serves. One
  `_workspace_door.html` partial serves all three cloud-ACTIVE sites.
- **2026-08-03** — RULED (user): the workspace door leads with the studio,
  never the infrastructure. An unclaimed studio's door on the success page
  IS the naming form — NAME YOUR STUDIO input with a live
  `<name>.screenboardstudio.com` preview as they type; the raw
  `*.up.railway.app` address is never displayed anywhere (the Open button
  may use it silently while the branded name provisions — the T3 reliable-
  door mechanic unchanged). The provisioning chip names the claimed
  address, or states that the address is created at naming. Claiming works
  from the success page via the same session capability the page already
  trusts; the ADVANCED access-token reveal is deleted. Claim name is the
  door's one fill; Open drops to secondary while the form shows.
- **2026-08-03** — RULED (STORE_PRICING_PLAN K1–K3): the engine band —
  the BYO-render-key fact sits in a shared bordered band ABOVE the price
  cards (BOTH EDITIONS amber kicker, two --ok advantage rows, one --hold
  condition row), never in a footnote below them. §4 gains the parity
  rule (a trait true of both editions appears in both lists) and its
  trait count loosens to four-or-five; the ANY ENGINE — YOUR OWN API KEY
  line now sits in both lists. The editions footnote drops its engine
  clause and states prices are USD.
