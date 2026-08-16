# Style plates

The example image on each style card in the anchor panels (stage 02).

Until a real picture exists for a style, its card shows the SVG **diagram**
drawn in `app.js` (`PLATE`) — a lit form and its shadow for a light
behaviour, the mark on the surface for a medium. A diagram is honest about
being a diagram; a stock photo would be someone else's film and a generated
sample would be one engine's opinion of the style rather than the style.

To add a real one:

1. Put the file here, e.g. `lightChiaro.webp` (any web format; ~340×280
   renders 1:1 in the card, and the frame is `68/56` so match that ratio).
2. Add it to `index.json`, keyed by the `plate:` value in the catalogue:

   ```json
   { "lightChiaro": "lightChiaro.webp" }
   ```

The page fetches this manifest once and only requests keys it lists, so a
style with no picture yet is never a broken image — it keeps its diagram.

Keys come from `RENDER_STYLES` and `TEXTURE_STYLES` in
`app/static/app.js`, and — for the cinematography grammars — from
`docs/CINEMATOGRAPHY_STYLES.md`, slugged as `cine-<name>` (e.g.
`cine-classical-adventure`).

## Three frames, not one

A cinematography card shows **three** reference frames, so its manifest
entry is a LIST and the first three are used:

```json
{ "cine-classical-adventure": ["ca-1.webp", "ca-2.webp", "ca-3.webp"] }
```

An empty slot renders as a dashed cell rather than a broken image, so a
style with one frame is fine and a style with none still reads.
