# STORE_HOMEPAGE_PLAN.md — build the new storefront homepage

**For the coding agent.** Replaces `storefront/app/templates/index.html` and the
landing portion of `storefront/app/static/store.css`. Mock:
`design_mocks/store-homepage.png` (full page, 1180px design width).
Read `STORE_DESIGN_SYSTEM.md` (new, in this drop) before starting.

Routes, form actions, field names and template variables are unchanged. The
`ready[...]` / `all_ready` gate logic is unchanged — only its presentation.

## Page order (one continuous scroll)

1. Header
2. **The Wall** — hero over a drifting gallery
3. Figure band (4 cells)
4. **Standalone App or Cloud-Based** — the two-edition pricing block
5. **Filmstrip** — infinite marquee of panels
6. **The pipeline dissolve** — 5 stages, auto-advancing + clickable
7. Footer

## S1 — Assets

Copy `storefront_img/` from this drop to `storefront/app/static/img/`.
15 panel stills (`p01`–`p15`), one finished board (`board-0001.png`), three
cinematography plates (`ref-0009/10/11.jpg`). All are real output from *The
Beltminers* — the storefront's whole argument is that this is what it makes,
so do not substitute stock or placeholders. Serve them from
`/static/img/…`. Add `loading="lazy"` to everything below the hero.

## S2 — The Wall (hero)

Three equal columns of stills in a grid that is inset `-70px` top and bottom
inside a `600px` overflow-hidden band, each column running its own
`ease-in-out infinite alternate` drift (21s / 14s / 26s; the middle column
starts offset and runs the opposite direction). Over it, one angled
`linear-gradient(97deg, …)` scrim from near-opaque at the left to ~34% at
72%. Copy sits on the opaque side and never moves.

- Kicker: `PRODUCTION DESIGN · CONTINUITY · ART DIRECTION`
- H1: **Your Movie Visualized** (60px, -.035em, max 12ch)
- Courier sub-line: `CAST · LOCATIONS · OBJECTS · SCENES · DESIGN LANGUAGES`
- Paragraph, primary CTA + ghost CTA, then the faint provenance line
  (`SHOWN — THE BELTMINERS · 3 BOARDS · 41 APPROVED PANELS`) — keep the
  counts truthful; wire them to real numbers if that is cheap, otherwise
  hard-code and note it.

## S3 — Pricing: `Standalone App or Cloud-Based`

Two cards, equal width. Standalone carries the amber top rule and the amber
Buy button — it is the recommended path and the section's only amber.

Each card is four stacked parts: kind + terms line → title + paragraph →
**a Courier trait list** → per-SKU rows (name, one-line qualifier, price,
button). The trait list is the point of this section: four `■` traits in
`--ok`, then **one honest tradeoff** as a grey `□` line. Do not soften or
drop the tradeoff line — it is what makes the comparison credible.

Gate states: when a plan's `ready[...]` is false, its button renders
disabled (`#1c1f23` / `#23272c` / `#4a4d52`) and the card gains
`UNAVAILABLE — CHECKOUT NOT CONFIGURED` as a Courier line under its rows.
When `all_ready` is false, the SETUP notice renders above the two cards,
using the existing notice markup restyled per the design system.

## S4 — Filmstrip

Full-bleed band on `--bg`, one Courier label, then a `200%`-wide flex row of
12 stills (6 unique, repeated once) running `sb-strip 52s linear infinite`
to `translateX(-50%)`. Purely decorative — `aria-hidden="true"`.

## S5 — The pipeline dissolve

Left column: the five stages (`01 SCREENPLAY` … `05 BOARD`), each a
2px-left-border block. Active stage: amber border, amber Courier kicker,
`--ink-dim` body; inactive: `--line-soft` border and dimmer text. All
transitions `.45s`.

Right: a `396px` stage holding five absolutely-positioned artifact panes,
cross-fading on `opacity .7s ease`. Under it, five progress ticks mirroring
the stage state, plus a Courier caption.

**Behavior:** auto-advance every 5200ms; clicking any stage *or any tick*
selects it and re-arms the timer from zero. Implement in vanilla JS in a
`<script>` at the end of the template (the storefront has no framework) —
one `setActive(i)` that writes the styles, one interval, `clearInterval` +
restart on click. Honor `prefers-reduced-motion`: no auto-advance, no
cross-fade transition; clicking still switches panes.

**The five artifacts, in order — each is a real work product, not an
illustration:**

1. **Screenplay** — a correctly formatted screenplay page in Courier
   (scene heading and action at the left margin, character name and
   dialogue indented). Keep the format exact; screenwriters will notice.
2. **Production Design** — the Cinematography lookbook card: role title,
   `CONTROLS` line in `--ok` and `NEVER` line in `--bad`, three plates
   (REF-0009/10/11) each with its ID and an `IN USE` badge, and a footer
   naming what else the bible sets.
3. **Breakdown** — two panes: the scene excerpt on the left with extracted
   phrases highlighted in amber, and the breakdown sheet on the right —
   `ID · ELEMENT · CATEGORY · EVIDENCE` using real categories (SET, SET
   DRESSING, PICTURE VEHICLE, PROP, ATMOSPHERE), five PASS rows and one
   HOLD, with the FORBIDDEN line beneath.
4. **Panel** — a full-bleed approved panel with its Courier facts bar
   (ID, dimensions, anchor count, APPROVED badge).
5. **Board** — the finished board, `object-fit: contain` on `--bg` so the
   composition reads whole, with `TYPOGRAPHY DRAWN BY THE APP, NEVER THE
   MODEL` in its facts bar.

## S6 — Sweep the rest of the storefront

The other pages (`signin`, `account`, `success`, `recover`, `terms`,
`privacy`) are not redesigned in this pass, but they inherit `store.css`.
After landing S1–S5, check each still renders correctly and fix anything the
CSS changes broke. Do not restructure them — their redesign is a later pass.

## Ground rules

Tokens only (the store palette is in `STORE_DESIGN_SYSTEM.md`); square
corners; Archivo for hierarchy, Courier for machine data. Amber follows the
four-role rule in `STORE_DESIGN_SYSTEM.md` §8 — on this page that means
**two fills** (hero CTA, standalone Buy), one Courier kicker per section,
inline highlights only in the breakdown pane, and one active dissolve step.
Match the mock; do not apply the product app's stricter amber rule here.
No frameworks, no new fonts, no emoji, no gradients except the hero scrim.
Every animation sits behind `prefers-reduced-motion`. Keep `/` serving 200
for CI.
