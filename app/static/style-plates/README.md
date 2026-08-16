# Style plates

The example image on each style card in the anchor panels (stage 02).

Until a real picture exists for a style, its card shows the SVG **diagram**
drawn in `app.js` (`PLATE`) — a lit form and its shadow for a light
behaviour, the mark on the surface for a medium. A diagram is honest about
being a diagram; a stock photo would be someone else's film and a generated
sample would be one engine's opinion of the style rather than the style.

To add a real one:

1. Put the file here as **WebP, 1280px on the long edge, quality ~78**
   (`ruled 2026-08-16`). That lands around 100-180 KB, serves both the
   ~110px card cell and the lightbox from one file, and ships inside the
   release zip — three 2.5 MB PNGs cost 8 MB for pictures nothing displays
   above 1280px. Masters do not belong in the repo.

   ```python
   im = Image.open(src).convert("RGB")
   if im.width > 1280:
       im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
   im.save(dst, "WEBP", quality=78, method=6)
   ```
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
