# RENDERING STYLE CALIBRATION — 27 LOCKED GENERATION PROMPTS

Nine rendering styles x three locked standard scenes.

**A — Object:** the hauler alone, three-quarter front, neutral ground  
**B — Figure:** the driver, waist-up, at the open cab door  
**C — Environment:** the hauler crossing a dry lake bed at dusk

The subject, camera, light and palette blocks are identical across all nine styles. Only the rendering medium changes.

Generated from `docs/RENDERING_STYLES.md` by `scripts/render_style_prompts.py` — edit the document and re-run, never edit this file. It is the same nine styles the picker shows and the Art Direction Bible is written from, so a prompt here cannot describe a style the app does not have.

Save each render as `<Scene>_<Style>.png` — `Object_Production_Painting.png`, `Figure_Ink_Wash.png`, `Environment_Technical_Blueprint.png` — and the app's plate importer will map them without a rule per filename.

---

# 01. Production Painting — The Brush Left Visible

## 01-A — Object — Production Painting

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

PRODUCTION PAINTING — THE BRUSH LEFT VISIBLE

Painted concept art in which the brush is deliberately not hidden. Forms are described in massed tone rather than outline, edges vary from lost to found, and the surface reads as pigment worked on a ground. This is the default medium of film production art: fast, confident, and honest about being a painting.

Operating principle: Describe form with masses and edges, not with line. Let the mark stay visible.

Visual mechanics:
- Visible directional brushwork following form
- Massed tonal blocks rather than outlined shapes
- Edge hierarchy — lost, soft and hard edges used deliberately
- Matte finish; no photographic specular sheen
- Economy in the periphery, detail concentrated at the focal point
- Ground colour showing through in passages
- Palette-knife or dry-brush texture in broken passages
- No outlines around objects

A production painting with visible brushwork. Form is described in massed
tonal blocks and varied edges rather than outline — edges range from fully
lost to crisply found, used deliberately to steer the eye. Directional
brush marks follow the form and are not blended away. The finish is matte,
with no photographic specular sheen. Detail concentrates at the focal
point and drops to economical suggestion in the periphery. Ground colour
shows through in places and broken dry-brush passages carry texture.
Nothing is outlined.

Avoid: photographic detail, cel outlines, flat vector fills, lens
artefacts, airbrushed smoothness

Avoid:
photographic detail
cel outlines
flat vector fills
lens
```

## 01-B — Figure — Production Painting

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

PRODUCTION PAINTING — THE BRUSH LEFT VISIBLE

Painted concept art in which the brush is deliberately not hidden. Forms are described in massed tone rather than outline, edges vary from lost to found, and the surface reads as pigment worked on a ground. This is the default medium of film production art: fast, confident, and honest about being a painting.

Operating principle: Describe form with masses and edges, not with line. Let the mark stay visible.

Visual mechanics:
- Visible directional brushwork following form
- Massed tonal blocks rather than outlined shapes
- Edge hierarchy — lost, soft and hard edges used deliberately
- Matte finish; no photographic specular sheen
- Economy in the periphery, detail concentrated at the focal point
- Ground colour showing through in passages
- Palette-knife or dry-brush texture in broken passages
- No outlines around objects

A production painting with visible brushwork. Form is described in massed
tonal blocks and varied edges rather than outline — edges range from fully
lost to crisply found, used deliberately to steer the eye. Directional
brush marks follow the form and are not blended away. The finish is matte,
with no photographic specular sheen. Detail concentrates at the focal
point and drops to economical suggestion in the periphery. Ground colour
shows through in places and broken dry-brush passages carry texture.
Nothing is outlined.

Avoid: photographic detail, cel outlines, flat vector fills, lens
artefacts, airbrushed smoothness

Avoid:
photographic detail
cel outlines
flat vector fills
lens
```

## 01-C — Environment — Production Painting

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

PRODUCTION PAINTING — THE BRUSH LEFT VISIBLE

Painted concept art in which the brush is deliberately not hidden. Forms are described in massed tone rather than outline, edges vary from lost to found, and the surface reads as pigment worked on a ground. This is the default medium of film production art: fast, confident, and honest about being a painting.

Operating principle: Describe form with masses and edges, not with line. Let the mark stay visible.

Visual mechanics:
- Visible directional brushwork following form
- Massed tonal blocks rather than outlined shapes
- Edge hierarchy — lost, soft and hard edges used deliberately
- Matte finish; no photographic specular sheen
- Economy in the periphery, detail concentrated at the focal point
- Ground colour showing through in passages
- Palette-knife or dry-brush texture in broken passages
- No outlines around objects

A production painting with visible brushwork. Form is described in massed
tonal blocks and varied edges rather than outline — edges range from fully
lost to crisply found, used deliberately to steer the eye. Directional
brush marks follow the form and are not blended away. The finish is matte,
with no photographic specular sheen. Detail concentrates at the focal
point and drops to economical suggestion in the periphery. Ground colour
shows through in places and broken dry-brush passages carry texture.
Nothing is outlined.

Avoid: photographic detail, cel outlines, flat vector fills, lens
artefacts, airbrushed smoothness

Avoid:
photographic detail
cel outlines
flat vector fills
lens
```

---

# 02. Hand-Drawn Cartoon — Ink Line, Flat Fill

## 02-A — Object — Hand-Drawn Cartoon

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

HAND-DRAWN CARTOON — INK LINE, FLAT FILL

Drawn line with flat colour behind it. The mark stays human — line weight breathes, shapes stay simple and readable — and colour arrives as flat areas rather than rendered volume. Traditional animation production drawing, where clarity of silhouette matters more than description of surface.

Operating principle: The line carries the drawing; colour only fills it. Keep shapes simple enough to read at a glance.

Visual mechanics:
- Confident ink linework with varying weight
- Flat cel colour areas with hard boundaries
- Simplified, strongly readable silhouettes
- Shadow as a single flat shape, not a gradient
- No rendered volume, no soft shading
- Line weight heavier on outer contours than interior detail
- Detail reduced to what the silhouette needs
- Slight line irregularity — a human hand, not a vector

A hand-drawn animation-style drawing: confident ink linework of varying
weight over flat cel colour. Outer contours carry heavier line than
interior detail. Colour sits as flat areas with hard boundaries; shadow is
a single flat shape rather than a gradient. Silhouettes are simplified and
strongly readable, with detail reduced to what the silhouette needs. The
line is slightly irregular — clearly a human hand rather than a vector
tool. No rendered volume, no soft shading, no gradients.

Avoid: rendered volume, soft shading, texture, photographic detail,
airbrush, vector precision

Avoid:
rendered volume
soft shading
texture
photographic detail
```

## 02-B — Figure — Hand-Drawn Cartoon

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

HAND-DRAWN CARTOON — INK LINE, FLAT FILL

Drawn line with flat colour behind it. The mark stays human — line weight breathes, shapes stay simple and readable — and colour arrives as flat areas rather than rendered volume. Traditional animation production drawing, where clarity of silhouette matters more than description of surface.

Operating principle: The line carries the drawing; colour only fills it. Keep shapes simple enough to read at a glance.

Visual mechanics:
- Confident ink linework with varying weight
- Flat cel colour areas with hard boundaries
- Simplified, strongly readable silhouettes
- Shadow as a single flat shape, not a gradient
- No rendered volume, no soft shading
- Line weight heavier on outer contours than interior detail
- Detail reduced to what the silhouette needs
- Slight line irregularity — a human hand, not a vector

A hand-drawn animation-style drawing: confident ink linework of varying
weight over flat cel colour. Outer contours carry heavier line than
interior detail. Colour sits as flat areas with hard boundaries; shadow is
a single flat shape rather than a gradient. Silhouettes are simplified and
strongly readable, with detail reduced to what the silhouette needs. The
line is slightly irregular — clearly a human hand rather than a vector
tool. No rendered volume, no soft shading, no gradients.

Avoid: rendered volume, soft shading, texture, photographic detail,
airbrush, vector precision

Avoid:
rendered volume
soft shading
texture
photographic detail
```

## 02-C — Environment — Hand-Drawn Cartoon

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

HAND-DRAWN CARTOON — INK LINE, FLAT FILL

Drawn line with flat colour behind it. The mark stays human — line weight breathes, shapes stay simple and readable — and colour arrives as flat areas rather than rendered volume. Traditional animation production drawing, where clarity of silhouette matters more than description of surface.

Operating principle: The line carries the drawing; colour only fills it. Keep shapes simple enough to read at a glance.

Visual mechanics:
- Confident ink linework with varying weight
- Flat cel colour areas with hard boundaries
- Simplified, strongly readable silhouettes
- Shadow as a single flat shape, not a gradient
- No rendered volume, no soft shading
- Line weight heavier on outer contours than interior detail
- Detail reduced to what the silhouette needs
- Slight line irregularity — a human hand, not a vector

A hand-drawn animation-style drawing: confident ink linework of varying
weight over flat cel colour. Outer contours carry heavier line than
interior detail. Colour sits as flat areas with hard boundaries; shadow is
a single flat shape rather than a gradient. Silhouettes are simplified and
strongly readable, with detail reduced to what the silhouette needs. The
line is slightly irregular — clearly a human hand rather than a vector
tool. No rendered volume, no soft shading, no gradients.

Avoid: rendered volume, soft shading, texture, photographic detail,
airbrush, vector precision

Avoid:
rendered volume
soft shading
texture
photographic detail
```

---

# 03. Black & White Sketch — Graphite, No Colour

## 03-A — Object — Black & White Sketch

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

BLACK & WHITE SKETCH — GRAPHITE, NO COLOUR

Graphite on paper. Tone is built by hatching and pressure rather than wash, the paper grain remains present, and there is no colour anywhere in the frame. A drawing made to work out value structure and form before anything else is decided.

Operating principle: Value does all the work. If the drawing fails in grey, colour would not have saved it.

Visual mechanics:
- Hatched and cross-hatched shading, direction following form
- Full tonal range from paper white to graphite black
- Paper grain visible through lighter passages
- Construction and gesture lines occasionally left in
- Edges varied by pressure, not by blending
- Erased highlights lifted back to paper
- Strictly monochrome — no colour cast whatsoever
- Graphite sheen in the darkest passages

A graphite drawing on paper, strictly monochrome. Tone is built with
hatching and cross-hatching whose direction follows the form, running the
full range from paper white to dense graphite black with visible sheen in
the darkest passages. Paper grain shows through lighter areas. Highlights
are lifted back to bare paper with an eraser. Edge quality varies by
pencil pressure rather than blending, and construction or gesture lines
are occasionally left visible. There is no colour anywhere in the image,
not even a warm or cool cast.

Avoid: colour, ink wash, painted surfaces, digital smoothness,
photographic detail

Avoid:
colour
ink wash
painted surfaces
digital smoothness
```

## 03-B — Figure — Black & White Sketch

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

BLACK & WHITE SKETCH — GRAPHITE, NO COLOUR

Graphite on paper. Tone is built by hatching and pressure rather than wash, the paper grain remains present, and there is no colour anywhere in the frame. A drawing made to work out value structure and form before anything else is decided.

Operating principle: Value does all the work. If the drawing fails in grey, colour would not have saved it.

Visual mechanics:
- Hatched and cross-hatched shading, direction following form
- Full tonal range from paper white to graphite black
- Paper grain visible through lighter passages
- Construction and gesture lines occasionally left in
- Edges varied by pressure, not by blending
- Erased highlights lifted back to paper
- Strictly monochrome — no colour cast whatsoever
- Graphite sheen in the darkest passages

A graphite drawing on paper, strictly monochrome. Tone is built with
hatching and cross-hatching whose direction follows the form, running the
full range from paper white to dense graphite black with visible sheen in
the darkest passages. Paper grain shows through lighter areas. Highlights
are lifted back to bare paper with an eraser. Edge quality varies by
pencil pressure rather than blending, and construction or gesture lines
are occasionally left visible. There is no colour anywhere in the image,
not even a warm or cool cast.

Avoid: colour, ink wash, painted surfaces, digital smoothness,
photographic detail

Avoid:
colour
ink wash
painted surfaces
digital smoothness
```

## 03-C — Environment — Black & White Sketch

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

BLACK & WHITE SKETCH — GRAPHITE, NO COLOUR

Graphite on paper. Tone is built by hatching and pressure rather than wash, the paper grain remains present, and there is no colour anywhere in the frame. A drawing made to work out value structure and form before anything else is decided.

Operating principle: Value does all the work. If the drawing fails in grey, colour would not have saved it.

Visual mechanics:
- Hatched and cross-hatched shading, direction following form
- Full tonal range from paper white to graphite black
- Paper grain visible through lighter passages
- Construction and gesture lines occasionally left in
- Edges varied by pressure, not by blending
- Erased highlights lifted back to paper
- Strictly monochrome — no colour cast whatsoever
- Graphite sheen in the darkest passages

A graphite drawing on paper, strictly monochrome. Tone is built with
hatching and cross-hatching whose direction follows the form, running the
full range from paper white to dense graphite black with visible sheen in
the darkest passages. Paper grain shows through lighter areas. Highlights
are lifted back to bare paper with an eraser. Edge quality varies by
pencil pressure rather than blending, and construction or gesture lines
are occasionally left visible. There is no colour anywhere in the image,
not even a warm or cool cast.

Avoid: colour, ink wash, painted surfaces, digital smoothness,
photographic detail

Avoid:
colour
ink wash
painted surfaces
digital smoothness
```

---

# 04. 3D Rendered Cartoon — Stylised Dimension

## 04-A — Object — 3D Rendered Cartoon

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

3D RENDERED CARTOON — STYLISED DIMENSION

Built and lit as geometry, then pulled away from realism on purpose. Surfaces are smooth and simply shaded, silhouettes are clean, forms are slightly exaggerated for readability. The dimensionality is real; the detail is not.

Operating principle: Keep the volume honest and the detail stylised. Simplify surfaces, never silhouettes.

Visual mechanics:
- Smooth shaded surfaces with soft, simple falloff
- Clean unbroken silhouettes and slightly rounded edges
- Forms simplified and mildly exaggerated in proportion
- Soft global illumination and gentle contact shadows
- Minimal surface texture; material read by shading, not by detail
- Subtle rim light separating forms from ground
- No brush marks and no outline
- Depth of field mild if present at all

A stylised three-dimensional render. Geometry is real and lit in the
round, but detail is deliberately simplified: surfaces are smooth with
soft, simple shading falloff, edges are slightly rounded, and silhouettes
stay clean and unbroken. Proportions are mildly exaggerated for
readability. Lighting is soft global illumination with gentle contact
shadows and a subtle rim separating forms from the ground. Materials are
read through shading rather than through surface texture detail. No brush
marks, no outlines, and at most a mild depth-of-field effect.

Avoid: photoreal detail, visible brushwork, cel outlines, heavy texture
maps, lens dirt, chromatic aberration

Avoid:
photoreal detail
visible brushwork
cel outlines
heavy texture
```

## 04-B — Figure — 3D Rendered Cartoon

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

3D RENDERED CARTOON — STYLISED DIMENSION

Built and lit as geometry, then pulled away from realism on purpose. Surfaces are smooth and simply shaded, silhouettes are clean, forms are slightly exaggerated for readability. The dimensionality is real; the detail is not.

Operating principle: Keep the volume honest and the detail stylised. Simplify surfaces, never silhouettes.

Visual mechanics:
- Smooth shaded surfaces with soft, simple falloff
- Clean unbroken silhouettes and slightly rounded edges
- Forms simplified and mildly exaggerated in proportion
- Soft global illumination and gentle contact shadows
- Minimal surface texture; material read by shading, not by detail
- Subtle rim light separating forms from ground
- No brush marks and no outline
- Depth of field mild if present at all

A stylised three-dimensional render. Geometry is real and lit in the
round, but detail is deliberately simplified: surfaces are smooth with
soft, simple shading falloff, edges are slightly rounded, and silhouettes
stay clean and unbroken. Proportions are mildly exaggerated for
readability. Lighting is soft global illumination with gentle contact
shadows and a subtle rim separating forms from the ground. Materials are
read through shading rather than through surface texture detail. No brush
marks, no outlines, and at most a mild depth-of-field effect.

Avoid: photoreal detail, visible brushwork, cel outlines, heavy texture
maps, lens dirt, chromatic aberration

Avoid:
photoreal detail
visible brushwork
cel outlines
heavy texture
```

## 04-C — Environment — 3D Rendered Cartoon

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

3D RENDERED CARTOON — STYLISED DIMENSION

Built and lit as geometry, then pulled away from realism on purpose. Surfaces are smooth and simply shaded, silhouettes are clean, forms are slightly exaggerated for readability. The dimensionality is real; the detail is not.

Operating principle: Keep the volume honest and the detail stylised. Simplify surfaces, never silhouettes.

Visual mechanics:
- Smooth shaded surfaces with soft, simple falloff
- Clean unbroken silhouettes and slightly rounded edges
- Forms simplified and mildly exaggerated in proportion
- Soft global illumination and gentle contact shadows
- Minimal surface texture; material read by shading, not by detail
- Subtle rim light separating forms from ground
- No brush marks and no outline
- Depth of field mild if present at all

A stylised three-dimensional render. Geometry is real and lit in the
round, but detail is deliberately simplified: surfaces are smooth with
soft, simple shading falloff, edges are slightly rounded, and silhouettes
stay clean and unbroken. Proportions are mildly exaggerated for
readability. Lighting is soft global illumination with gentle contact
shadows and a subtle rim separating forms from the ground. Materials are
read through shading rather than through surface texture detail. No brush
marks, no outlines, and at most a mild depth-of-field effect.

Avoid: photoreal detail, visible brushwork, cel outlines, heavy texture
maps, lens dirt, chromatic aberration

Avoid:
photoreal detail
visible brushwork
cel outlines
heavy texture
```

---

# 05. Photo Real — No Mark Of The Hand

## 05-A — Object — Photo Real

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

PHOTO REAL — NO MARK OF THE HAND

Reads as a photograph. Detail is lens-accurate, materials behave physically, and no trace of illustration survives anywhere in the frame. The image should be assessable as a still from the finished film rather than as a drawing of one.

Operating principle: If any mark reveals a hand made this, it is the wrong style. Everything must be explicable as optics.

Visual mechanics:
- Lens-accurate detail falloff and natural depth of field
- Physically correct material response — specular, roughness, subsurface
- Real-world lighting behaviour including bounce and occlusion
- Natural sensor noise structure in shadow
- Micro-detail present at every scale the lens would resolve
- Highlight rolloff and shadow retention of a real sensor
- No outlines, no brushwork, no stylisation of any kind
- Perspective consistent with a plausible real focal length

A photograph. Detail is lens-accurate at every scale the optics would
resolve, with natural depth of field and realistic falloff. Materials
respond physically — correct specular behaviour, roughness variation and
subsurface where appropriate. Lighting behaves as real light does,
including bounce, occlusion and colour transfer between surfaces.
Highlight rolloff and shadow retention match a real sensor, with natural
noise structure in the darkest areas. Perspective is consistent with a
plausible real focal length. Nothing in the frame reveals a hand: no
outline, no brush mark, no stylisation.

Avoid: illustration, brushwork, outlines, stylisation, painterly edges,
cartoon proportion

Avoid:
illustration
brushwork
outlines
stylisation
painterly edges
```

## 05-B — Figure — Photo Real

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

PHOTO REAL — NO MARK OF THE HAND

Reads as a photograph. Detail is lens-accurate, materials behave physically, and no trace of illustration survives anywhere in the frame. The image should be assessable as a still from the finished film rather than as a drawing of one.

Operating principle: If any mark reveals a hand made this, it is the wrong style. Everything must be explicable as optics.

Visual mechanics:
- Lens-accurate detail falloff and natural depth of field
- Physically correct material response — specular, roughness, subsurface
- Real-world lighting behaviour including bounce and occlusion
- Natural sensor noise structure in shadow
- Micro-detail present at every scale the lens would resolve
- Highlight rolloff and shadow retention of a real sensor
- No outlines, no brushwork, no stylisation of any kind
- Perspective consistent with a plausible real focal length

A photograph. Detail is lens-accurate at every scale the optics would
resolve, with natural depth of field and realistic falloff. Materials
respond physically — correct specular behaviour, roughness variation and
subsurface where appropriate. Lighting behaves as real light does,
including bounce, occlusion and colour transfer between surfaces.
Highlight rolloff and shadow retention match a real sensor, with natural
noise structure in the darkest areas. Perspective is consistent with a
plausible real focal length. Nothing in the frame reveals a hand: no
outline, no brush mark, no stylisation.

Avoid: illustration, brushwork, outlines, stylisation, painterly edges,
cartoon proportion

Avoid:
illustration
brushwork
outlines
stylisation
painterly edges
```

## 05-C — Environment — Photo Real

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

PHOTO REAL — NO MARK OF THE HAND

Reads as a photograph. Detail is lens-accurate, materials behave physically, and no trace of illustration survives anywhere in the frame. The image should be assessable as a still from the finished film rather than as a drawing of one.

Operating principle: If any mark reveals a hand made this, it is the wrong style. Everything must be explicable as optics.

Visual mechanics:
- Lens-accurate detail falloff and natural depth of field
- Physically correct material response — specular, roughness, subsurface
- Real-world lighting behaviour including bounce and occlusion
- Natural sensor noise structure in shadow
- Micro-detail present at every scale the lens would resolve
- Highlight rolloff and shadow retention of a real sensor
- No outlines, no brushwork, no stylisation of any kind
- Perspective consistent with a plausible real focal length

A photograph. Detail is lens-accurate at every scale the optics would
resolve, with natural depth of field and realistic falloff. Materials
respond physically — correct specular behaviour, roughness variation and
subsurface where appropriate. Lighting behaves as real light does,
including bounce, occlusion and colour transfer between surfaces.
Highlight rolloff and shadow retention match a real sensor, with natural
noise structure in the darkest areas. Perspective is consistent with a
plausible real focal length. Nothing in the frame reveals a hand: no
outline, no brush mark, no stylisation.

Avoid: illustration, brushwork, outlines, stylisation, painterly edges,
cartoon proportion

Avoid:
illustration
brushwork
outlines
stylisation
painterly edges
```

---

# 06. Industrial Design — The Presentation Drawing

## 06-A — Object — Industrial Design

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

INDUSTRIAL DESIGN — THE PRESENTATION DRAWING

The drawing an industrial designer makes to sell a form: the object described precisely with clean keylines and controlled shading, sitting on a neutral ground with no environment around it. The object is the subject and the world is deliberately absent.

Operating principle: Describe the object, not the scene. Nothing in the frame may compete with the form.

Visual mechanics:
- Clean confident keylines describing form and section
- Controlled tonal shading, restrained and even
- Neutral ground with no environment or horizon
- Simple ground shadow anchoring the object only
- Material indicated by a small number of well-placed highlights
- Section, detail call-out or alternate view occasionally alongside
- Colour restrained, often a single accent against neutral
- No atmosphere, weather or scene lighting

An industrial design presentation drawing. The object is described with
clean confident keylines and controlled, restrained tonal shading. It
sits on a neutral ground with no environment, horizon or atmosphere — only
a simple contact shadow anchoring it. Material is indicated by a small
number of well-placed highlights rather than by texture detail. Colour is
restrained, typically neutral with at most a single accent. Occasionally a
section, detail call-out or alternate view sits alongside the main view.
Nothing in the frame competes with the form of the object.

Avoid: environment, scene lighting, atmosphere, weather, background
detail, painterly texture

Avoid:
environment
scene lighting
atmosphere
weather
background
```

## 06-B — Figure — Industrial Design

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

INDUSTRIAL DESIGN — THE PRESENTATION DRAWING

The drawing an industrial designer makes to sell a form: the object described precisely with clean keylines and controlled shading, sitting on a neutral ground with no environment around it. The object is the subject and the world is deliberately absent.

Operating principle: Describe the object, not the scene. Nothing in the frame may compete with the form.

Visual mechanics:
- Clean confident keylines describing form and section
- Controlled tonal shading, restrained and even
- Neutral ground with no environment or horizon
- Simple ground shadow anchoring the object only
- Material indicated by a small number of well-placed highlights
- Section, detail call-out or alternate view occasionally alongside
- Colour restrained, often a single accent against neutral
- No atmosphere, weather or scene lighting

An industrial design presentation drawing. The object is described with
clean confident keylines and controlled, restrained tonal shading. It
sits on a neutral ground with no environment, horizon or atmosphere — only
a simple contact shadow anchoring it. Material is indicated by a small
number of well-placed highlights rather than by texture detail. Colour is
restrained, typically neutral with at most a single accent. Occasionally a
section, detail call-out or alternate view sits alongside the main view.
Nothing in the frame competes with the form of the object.

Avoid: environment, scene lighting, atmosphere, weather, background
detail, painterly texture

Avoid:
environment
scene lighting
atmosphere
weather
background
```

## 06-C — Environment — Industrial Design

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

INDUSTRIAL DESIGN — THE PRESENTATION DRAWING

The drawing an industrial designer makes to sell a form: the object described precisely with clean keylines and controlled shading, sitting on a neutral ground with no environment around it. The object is the subject and the world is deliberately absent.

Operating principle: Describe the object, not the scene. Nothing in the frame may compete with the form.

Visual mechanics:
- Clean confident keylines describing form and section
- Controlled tonal shading, restrained and even
- Neutral ground with no environment or horizon
- Simple ground shadow anchoring the object only
- Material indicated by a small number of well-placed highlights
- Section, detail call-out or alternate view occasionally alongside
- Colour restrained, often a single accent against neutral
- No atmosphere, weather or scene lighting

An industrial design presentation drawing. The object is described with
clean confident keylines and controlled, restrained tonal shading. It
sits on a neutral ground with no environment, horizon or atmosphere — only
a simple contact shadow anchoring it. Material is indicated by a small
number of well-placed highlights rather than by texture detail. Colour is
restrained, typically neutral with at most a single accent. Occasionally a
section, detail call-out or alternate view sits alongside the main view.
Nothing in the frame competes with the form of the object.

Avoid: environment, scene lighting, atmosphere, weather, background
detail, painterly texture

Avoid:
environment
scene lighting
atmosphere
weather
background
```

---

# 07. Ink & Wash — Line Carries, Wash Tones

## 07-A — Object — Ink & Wash

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

INK & WASH — LINE CARRIES, WASH TONES

Pen line carrying the drawing and diluted wash carrying the tone. The line is the structure and the wash is atmosphere; the two are visibly separate processes, and the paper stays present between them.

Operating principle: The line describes; the wash only weights. Never let wash do the drawing.

Visual mechanics:
- Confident pen linework describing all structure
- Diluted ink wash in a limited number of tonal steps
- Wash pooling at edges with visible boundaries
- Paper white reserved for highlights, never painted back in
- Hatching used where wash cannot go
- Line unbroken by the wash sitting over it
- Restrained, often monochrome or duotone
- Visible brush-edge where a wash stroke ended

A graphic-novel style ink drawing with wash. Confident pen linework
carries all of the structure; diluted ink wash sits behind it in a limited
number of tonal steps, weighting the image without describing it. Wash
pools at its edges leaving visible boundaries and brush-edge marks where
strokes ended. Paper white is reserved for highlights rather than painted
back in. Hatching handles areas the wash cannot reach. The line remains
unbroken and legible beneath the wash. The result is restrained, usually
monochrome or duotone.

Avoid: full colour rendering, painted volume, photographic detail,
airbrush, digital gradients

Avoid:
full colour rendering
painted volume
photographic detail
```

## 07-B — Figure — Ink & Wash

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

INK & WASH — LINE CARRIES, WASH TONES

Pen line carrying the drawing and diluted wash carrying the tone. The line is the structure and the wash is atmosphere; the two are visibly separate processes, and the paper stays present between them.

Operating principle: The line describes; the wash only weights. Never let wash do the drawing.

Visual mechanics:
- Confident pen linework describing all structure
- Diluted ink wash in a limited number of tonal steps
- Wash pooling at edges with visible boundaries
- Paper white reserved for highlights, never painted back in
- Hatching used where wash cannot go
- Line unbroken by the wash sitting over it
- Restrained, often monochrome or duotone
- Visible brush-edge where a wash stroke ended

A graphic-novel style ink drawing with wash. Confident pen linework
carries all of the structure; diluted ink wash sits behind it in a limited
number of tonal steps, weighting the image without describing it. Wash
pools at its edges leaving visible boundaries and brush-edge marks where
strokes ended. Paper white is reserved for highlights rather than painted
back in. Hatching handles areas the wash cannot reach. The line remains
unbroken and legible beneath the wash. The result is restrained, usually
monochrome or duotone.

Avoid: full colour rendering, painted volume, photographic detail,
airbrush, digital gradients

Avoid:
full colour rendering
painted volume
photographic detail
```

## 07-C — Environment — Ink & Wash

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

INK & WASH — LINE CARRIES, WASH TONES

Pen line carrying the drawing and diluted wash carrying the tone. The line is the structure and the wash is atmosphere; the two are visibly separate processes, and the paper stays present between them.

Operating principle: The line describes; the wash only weights. Never let wash do the drawing.

Visual mechanics:
- Confident pen linework describing all structure
- Diluted ink wash in a limited number of tonal steps
- Wash pooling at edges with visible boundaries
- Paper white reserved for highlights, never painted back in
- Hatching used where wash cannot go
- Line unbroken by the wash sitting over it
- Restrained, often monochrome or duotone
- Visible brush-edge where a wash stroke ended

A graphic-novel style ink drawing with wash. Confident pen linework
carries all of the structure; diluted ink wash sits behind it in a limited
number of tonal steps, weighting the image without describing it. Wash
pools at its edges leaving visible boundaries and brush-edge marks where
strokes ended. Paper white is reserved for highlights rather than painted
back in. Hatching handles areas the wash cannot reach. The line remains
unbroken and legible beneath the wash. The result is restrained, usually
monochrome or duotone.

Avoid: full colour rendering, painted volume, photographic detail,
airbrush, digital gradients

Avoid:
full colour rendering
painted volume
photographic detail
```

---

# 08. Gouache & Watercolor — Pigment On Paper

## 08-A — Object — Gouache & Watercolor

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

GOUACHE & WATERCOLOR — PIGMENT ON PAPER

Pigment in water on a textured ground. Edges pool and granulate, the paper grain shows through the thinner passages, and opaque gouache sits over transparent washes. The medium is unmistakably physical and slightly unpredictable.

Operating principle: Let the medium behave. Pooling, granulation and grain are the style, not defects to clean up.

Visual mechanics:
- Pigment pooling and hard edges where washes dried
- Paper grain visible through transparent passages
- Granulation and separation within washes
- Opaque gouache passages over transparent underwash
- Reserved paper white for the brightest notes
- Soft wet-in-wet transitions beside hard dry edges
- Slight blooming and backruns left in
- Colour mixing occurring on the paper, not only on the palette

A painting in gouache and watercolour on textured paper. Transparent
washes pool and dry to hard edges, granulating and separating within
themselves, with paper grain visible through the thinner passages. Opaque
gouache passages sit over transparent underwash. The brightest notes are
reserved paper white rather than applied paint. Soft wet-in-wet
transitions sit beside hard dry edges, and slight blooms and backruns are
left in rather than corrected. Colour visibly mixes on the paper itself.

Avoid: digital smoothness, airbrush, photographic detail, vector edges,
uniform flat fills

Avoid:
digital smoothness
airbrush
photographic detail
vector edges
```

## 08-B — Figure — Gouache & Watercolor

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

GOUACHE & WATERCOLOR — PIGMENT ON PAPER

Pigment in water on a textured ground. Edges pool and granulate, the paper grain shows through the thinner passages, and opaque gouache sits over transparent washes. The medium is unmistakably physical and slightly unpredictable.

Operating principle: Let the medium behave. Pooling, granulation and grain are the style, not defects to clean up.

Visual mechanics:
- Pigment pooling and hard edges where washes dried
- Paper grain visible through transparent passages
- Granulation and separation within washes
- Opaque gouache passages over transparent underwash
- Reserved paper white for the brightest notes
- Soft wet-in-wet transitions beside hard dry edges
- Slight blooming and backruns left in
- Colour mixing occurring on the paper, not only on the palette

A painting in gouache and watercolour on textured paper. Transparent
washes pool and dry to hard edges, granulating and separating within
themselves, with paper grain visible through the thinner passages. Opaque
gouache passages sit over transparent underwash. The brightest notes are
reserved paper white rather than applied paint. Soft wet-in-wet
transitions sit beside hard dry edges, and slight blooms and backruns are
left in rather than corrected. Colour visibly mixes on the paper itself.

Avoid: digital smoothness, airbrush, photographic detail, vector edges,
uniform flat fills

Avoid:
digital smoothness
airbrush
photographic detail
vector edges
```

## 08-C — Environment — Gouache & Watercolor

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

GOUACHE & WATERCOLOR — PIGMENT ON PAPER

Pigment in water on a textured ground. Edges pool and granulate, the paper grain shows through the thinner passages, and opaque gouache sits over transparent washes. The medium is unmistakably physical and slightly unpredictable.

Operating principle: Let the medium behave. Pooling, granulation and grain are the style, not defects to clean up.

Visual mechanics:
- Pigment pooling and hard edges where washes dried
- Paper grain visible through transparent passages
- Granulation and separation within washes
- Opaque gouache passages over transparent underwash
- Reserved paper white for the brightest notes
- Soft wet-in-wet transitions beside hard dry edges
- Slight blooming and backruns left in
- Colour mixing occurring on the paper, not only on the palette

A painting in gouache and watercolour on textured paper. Transparent
washes pool and dry to hard edges, granulating and separating within
themselves, with paper grain visible through the thinner passages. Opaque
gouache passages sit over transparent underwash. The brightest notes are
reserved paper white rather than applied paint. Soft wet-in-wet
transitions sit beside hard dry edges, and slight blooms and backruns are
left in rather than corrected. Colour visibly mixes on the paper itself.

Avoid: digital smoothness, airbrush, photographic detail, vector edges,
uniform flat fills

Avoid:
digital smoothness
airbrush
photographic detail
vector edges
```

---

# 09. Technical Blueprint — Information, Not Picture

## 09-A — Object — Technical Blueprint

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE A — OBJECT

A single six-wheeled desert hauler, three-quarter front view, standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an open flatbed rear, six oversized run-flat wheels, external roll cage, stowed tools and fuel cans lashed along the flank, one spare wheel mounted behind the cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is the subject: proportion, structure, mechanical logic and silhouette.

RENDERING STYLE

TECHNICAL BLUEPRINT — INFORMATION, NOT PICTURE

An orthographic technical drawing: no perspective, no lighting, no rendering. Form is described by keyline, section and dimension. This is information rather than a picture, and it should be readable as a document.

Operating principle: Communicate measurement and construction. Anything pictorial is out of scope.

Visual mechanics:
- Orthographic projection — no perspective convergence
- Uniform keyline weight with heavier outer profile
- Dimension lines, ticks, extension lines and leaders
- Hidden detail as dashed line
- Hatched section cuts at consistent angle
- Centrelines through axes of symmetry
- No lighting, no shading, no cast shadow
- Flat single-colour ground with monochrome linework

An orthographic technical drawing. There is no perspective convergence,
no lighting, no shading and no cast shadow. Form is described entirely by
line: uniform keyline weight with a heavier outer profile, dashed lines
for hidden detail, centrelines through axes of symmetry, and section cuts
hatched at a consistent angle. Dimension lines with ticks, extension lines
and leaders annotate the drawing. The ground is flat and single-coloured
with monochrome linework throughout. The image reads as a document rather
than as a picture.

Avoid: perspective, lighting, shading, cast shadow, rendering,
atmosphere, painterly marks

Avoid:
perspective
lighting
shading
cast shadow
rendering
```

## 09-B — Figure — Technical Blueprint

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE B — FIGURE

The hauler's driver, waist-up, standing beside the open cab door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a dark undershirt, gloves pushed into a pocket. Looking off-frame at something that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close enough to read as the same vehicle. The face and hands are the subject.

RENDERING STYLE

TECHNICAL BLUEPRINT — INFORMATION, NOT PICTURE

An orthographic technical drawing: no perspective, no lighting, no rendering. Form is described by keyline, section and dimension. This is information rather than a picture, and it should be readable as a document.

Operating principle: Communicate measurement and construction. Anything pictorial is out of scope.

Visual mechanics:
- Orthographic projection — no perspective convergence
- Uniform keyline weight with heavier outer profile
- Dimension lines, ticks, extension lines and leaders
- Hidden detail as dashed line
- Hatched section cuts at consistent angle
- Centrelines through axes of symmetry
- No lighting, no shading, no cast shadow
- Flat single-colour ground with monochrome linework

An orthographic technical drawing. There is no perspective convergence,
no lighting, no shading and no cast shadow. Form is described entirely by
line: uniform keyline weight with a heavier outer profile, dashed lines
for hidden detail, centrelines through axes of symmetry, and section cuts
hatched at a consistent angle. Dimension lines with ticks, extension lines
and leaders annotate the drawing. The ground is flat and single-coloured
with monochrome linework throughout. The image reads as a document rather
than as a picture.

Avoid: perspective, lighting, shading, cast shadow, rendering,
atmosphere, painterly marks

Avoid:
perspective
lighting
shading
cast shadow
rendering
```

## 09-C — Environment — Technical Blueprint

```text
OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)

LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all

PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style.

CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style.

SCENE C — ENVIRONMENT

The same hauler crossing a dry lake bed at dusk, small in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how much atmosphere sits between it and the camera.

RENDERING STYLE

TECHNICAL BLUEPRINT — INFORMATION, NOT PICTURE

An orthographic technical drawing: no perspective, no lighting, no rendering. Form is described by keyline, section and dimension. This is information rather than a picture, and it should be readable as a document.

Operating principle: Communicate measurement and construction. Anything pictorial is out of scope.

Visual mechanics:
- Orthographic projection — no perspective convergence
- Uniform keyline weight with heavier outer profile
- Dimension lines, ticks, extension lines and leaders
- Hidden detail as dashed line
- Hatched section cuts at consistent angle
- Centrelines through axes of symmetry
- No lighting, no shading, no cast shadow
- Flat single-colour ground with monochrome linework

An orthographic technical drawing. There is no perspective convergence,
no lighting, no shading and no cast shadow. Form is described entirely by
line: uniform keyline weight with a heavier outer profile, dashed lines
for hidden detail, centrelines through axes of symmetry, and section cuts
hatched at a consistent angle. Dimension lines with ticks, extension lines
and leaders annotate the drawing. The ground is flat and single-coloured
with monochrome linework throughout. The image reads as a document rather
than as a picture.

Avoid: perspective, lighting, shading, cast shadow, rendering,
atmosphere, painterly marks

Avoid:
perspective
lighting
shading
cast shadow
rendering
```

---
