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
A pricing card's middle block is a Courier list: four `■` traits in `--ok`,
then **exactly one** `□` tradeoff in `--ink-faint`. Both editions carry a
tradeoff. A card with only upsides reads as marketing; a card that names
its cost reads as a spec sheet, which is what this audience trusts.

### 5. Gates are stated, never errored
Unconfigured checkout, missing mail, missing Google: render as a visible
stated condition (SETUP notice in `--hold`, disabled control, Courier
`UNAVAILABLE — …` line). Never a toast, never a red error, never a
hidden control.

### 6. Provenance lines
A faint Courier line naming what is shown (`SHOWN — THE BELTMINERS · 3
BOARDS · 41 APPROVED PANELS`) accompanies gallery sections. It converts
decoration into evidence. Keep the numbers true.

### 7. Vocabulary
Use the profession's words, correctly: production design, art department,
art direction, art direction bible / lookbook, script breakdown, set,
set dressing, picture vehicle, prop, atmosphere, continuity, concept
board, panel, plate. Never "AI art", "prompt", "generation" in sales copy
— the buyer is a production, not a prompter. "Render" is fine.

### 8. Amber budget per page
Two amber elements maximum in the static layout (typically the hero CTA and
the recommended plan's Buy), plus one moving amber state (the active stage
rule). Count it before shipping.

---

## Changelog

- **2026-08-01** — Storefront system established with the homepage rebuild:
  the Wall hero, Standalone/Cloud trait-list pricing, filmstrip, and the
  five-stage pipeline dissolve.
- **2026-08-01** — Non-canon: reliable-door workspace buttons. On /account
  and /success, the "Open your workspace" button links the branded address
  only once it provably serves (`domain_live`); until then it links the
  always-working railway address with a small mono note ("… IS PROVISIONING
  — THIS BUTTON USES THE RELIABLE ADDRESS MEANWHILE"). Reuses existing
  `hero-sub mono` styling; no new tokens. Awaiting design review.
