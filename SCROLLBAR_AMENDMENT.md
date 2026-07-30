# DESIGN_SYSTEM.md amendment — scrollbars

**For the coding agent:**
1. Append the CSS below to the end of `app/static/styles.css` (before the
   `@media (prefers-reduced-motion)` block).
2. Insert the doc section below into `app/static/DESIGN_SYSTEM.md`, after the
   `## Components` section.
3. Add a changelog line: `**2026-07-29** — Scrollbar treatment added
   (thin, square, track invisible, thumb --line → --ink-faint on hover).`
4. Delete `scrollbars.css.snippet` and this file after applying.

---

## CSS (append to styles.css)

```css
/* =============================================================== scrollbars
   Scrollbars are chrome, not content: flat, square, track invisible against
   its surface, thumb one line-tone that brightens only under the pointer.
   Amber never appears here — a scrollbar is not a signal. */
* {
  scrollbar-width: thin;                       /* Firefox */
  scrollbar-color: var(--line) transparent;
}
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--line);
  border: 2px solid transparent;               /* inset the thumb to 6px */
  background-clip: padding-box;
  border-radius: 0;                            /* square, like everything */
}
::-webkit-scrollbar-thumb:hover { background-color: var(--ink-faint); background-clip: padding-box; }
::-webkit-scrollbar-corner { background: transparent; }
/* Dark overlays (lightbox, cropper) get a dimmer thumb so it doesn't glow */
.lightbox ::-webkit-scrollbar-thumb, .cropper ::-webkit-scrollbar-thumb { background-color: var(--line-soft); background-clip: padding-box; }
```

## Doc section (insert into DESIGN_SYSTEM.md after `## Components`)

```markdown
## Scrollbars

Scrollbars are chrome, not content. The global rules in `styles.css` cover
every scroll container — never restyle one locally.

- Thin (10px), square, thumb inset 2px so it reads as a 6px bar.
- Track invisible; the thumb is `--line`, `--ink-faint` on hover. No amber,
  no status colors — a scrollbar is never a signal.
- Overlays (`.lightbox`, `.cropper`) use `--line-soft` so the thumb doesn't
  glow against near-black.
- New scroll containers (rails, filmstrips, code blocks) inherit this
  automatically. If a thumb is invisible against a custom surface, fix the
  surface color, not the scrollbar.
- `overflow: auto`, not `scroll` — no dead tracks on content that fits.
```
