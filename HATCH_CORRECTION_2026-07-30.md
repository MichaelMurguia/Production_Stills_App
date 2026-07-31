# HATCH_CORRECTION_2026-07-30.md — placeholder treatment superseded

**For the coding agent.** User ruling: the thin-line hatch specced in
DESIGN_REVIEW_2026-07-30c §1 is rejected. The canonical placeholder
treatment everywhere is the **Board Assembly band stripe** — opaque
two-tone 135° bands, no thin lines, no translucent ink.

## Canon (replaces the `.hatch`/`.hatch-deep` gradients)

```css
/* placeholder bands — canonical. Opaque two-tone, 135°, equal bands.
   MUST stay last in the component cascade (background: shorthand resets). */
.hatch      { background: repeating-linear-gradient(135deg, #21252a 0 7px, #1c1f23 7px 14px); }  /* standard blocks */
.hatch-fine { background: repeating-linear-gradient(135deg, #21252a 0 5px, #1c1f23 5px 10px); }  /* thumbs < 60px */
.hatch-bad  { background: repeating-linear-gradient(135deg, #211b1b 0 7px, #1b1717 7px 14px); }  /* TOO-SMALL / error surfaces */
```

- Keep the class names and application points from review c; only the
  gradients change. If review c was already applied, swap the gradient
  values; if not, apply review c with these values instead.
- Band tones are deliberate near-surface pairs (panel2/[#1c1f23]), not new
  greys — they already exist in the assembly slot map and reference-card
  placeholders.
- `.hatch-bad` replaces "white stripe over red tint": error placeholders use
  the red-shifted band pair with the `--bad-line` border, exactly as the
  assembly slot map does today.
- Scale rule: 7/14px bands for blocks ≥ 60px tall; 5/10px for smaller thumbs.
- Update DESIGN_SYSTEM.md's hatch entry + changelog line:
  `**2026-07-30** — Placeholder hatch superseded by user ruling: opaque
  two-tone 135° bands (assembly-style), 7/14px standard, 5/10px fine,
  red-shifted pair for error surfaces.`
- Delete this file after applying.
