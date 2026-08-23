# Board Rendering Styles

## Purpose

These ten rendering styles are reusable **medium** grammars for
production stills. Each describes **how a panel is drawn** — the material,
the mark, the finish — and nothing about what is drawn.

Each style uses a common format:

1. Key Question
2. Description
3. Operating Principle
4. Visual Mechanics
5. Image-Model Prompt

**Scope fence.** Rendering style is a BOARD parameter, not a movie
parameter. It owns medium, mark and finish. It does not set mood, it does
not set light behaviour (the Cinematography anchor owns that), it does not
set colour (the Color Palette anchor owns that), and it does not set
surface condition in the world (the World Texture anchor owns that).
Choosing a rendering style never changes what the world is — only how the
picture of it is made.

**Style 1 is the house slot.** Once this production has a saved Bible and
approved panels, the app replaces style 1's words and example plate with
the production's OWN captured style, so the first card shows what this
film is actually drawn in rather than a shipped default. Order matters
here: whichever style is numbered 1 is the one that gets replaced.

This file is the source of truth: the app parses it, so editing a style
here changes the picker and every future prompt. Adding a `# n. Name —
Subtitle` section adds a style; deleting one removes it.

---

# 1. Production Painting — Readable Form Over Surface

## Key Question

What does this look like painted by a production artist, read from across
the room?

## Description

Painterly production concept art made to be read on a wall, not studied at
arm's length. Form is carried by large value groups, silhouette and edge
quality; brushwork exists to support those, never to become a surface
effect in its own right. Materials are told apart by value, edge and
colour before any texture is described. This is the default medium of film
production art: fast, confident, and built for the distance a board is
actually viewed from.

## Operating Principle

Brushwork supports large readable forms — do not simulate brush texture
across every surface; favour shape readability over surface texture.

## Visual Mechanics

- Painterly production concept art
- Large value grouping over local detail
- Strong silhouette design
- Cinematic value grouping
- Practical material logic
- Materials read at production-board viewing distance: value, edge quality
  and colour before texture — no microscopic surface variation
- Real-world construction logic
- Restrained visual effects
- Clear production-design intent
- Board layouts that resemble an internal studio development wall

## Image-Model Prompt

```text
Painterly production concept art, built to read at production-board
viewing distance. Form is carried by large value groups, strong silhouette
design and deliberate edge quality — lost, soft and found — rather than by
local detail. Brushwork supports those large readable forms; it is not
simulated as texture across every surface, and shape readability wins over
surface description everywhere the two compete. Materials are told apart
by value, edge quality and colour before any texture is described, with no
microscopic surface variation. Construction and material behaviour follow
real-world logic. Visual effects are restrained. The image states a clear
production-design intent.

Avoid: photography, cel animation
```

---

# 2. Hand-Drawn Cartoon — Ink Line, Flat Fill

## Key Question

What does this look like drawn by hand and filled flat?

## Description

Drawn line with flat colour behind it. The mark stays human — line weight
breathes, shapes stay simple and readable — and colour arrives as flat
areas rather than rendered volume. Traditional animation production
drawing, where clarity of silhouette matters more than description of
surface.

## Operating Principle

The line carries the drawing; colour only fills it. Keep shapes simple
enough to read at a glance.

## Visual Mechanics

- Confident ink linework with varying weight
- Flat cel colour areas with hard boundaries
- Simplified, strongly readable silhouettes
- Shadow as a single flat shape, not a gradient
- No rendered volume, no soft shading
- Line weight heavier on outer contours than interior detail
- Detail reduced to what the silhouette needs
- Slight line irregularity — a human hand, not a vector

## Image-Model Prompt

```text
A hand-drawn animation-style drawing: confident ink linework of varying
weight over flat cel colour. Outer contours carry heavier line than
interior detail. Colour sits as flat areas with hard boundaries; shadow is
a single flat shape rather than a gradient. Silhouettes are simplified and
strongly readable, with detail reduced to what the silhouette needs. The
line is slightly irregular — clearly a human hand rather than a vector
tool. No rendered volume, no soft shading, no gradients.

Avoid: rendered volume, soft shading, texture, photographic detail,
airbrush, vector precision
```

---

# 3. Black & White Sketch — Graphite, No Colour

## Key Question

What does this look like as a tonal drawing in pencil, with no colour at
all?

## Description

Graphite on paper. Tone is built by hatching and pressure rather than
wash, the paper grain remains present, and there is no colour anywhere in
the frame. A drawing made to work out value structure and form before
anything else is decided.

## Operating Principle

Value does all the work. If the drawing fails in grey, colour would not
have saved it.

## Visual Mechanics

- Hatched and cross-hatched shading, direction following form
- Full tonal range from paper white to graphite black
- Paper grain visible through lighter passages
- Construction and gesture lines occasionally left in
- Edges varied by pressure, not by blending
- Erased highlights lifted back to paper
- Strictly monochrome — no colour cast whatsoever
- Graphite sheen in the darkest passages

## Image-Model Prompt

```text
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
```

---

# 4. 3D Rendered Cartoon — Stylised Dimension

## Key Question

What does this look like modelled and lit in three dimensions, but
deliberately stylised?

## Description

Built and lit as geometry, then pulled away from realism on purpose.
Surfaces are smooth and simply shaded, silhouettes are clean, forms are
slightly exaggerated for readability. The dimensionality is real; the
detail is not.

## Operating Principle

Keep the volume honest and the detail stylised. Simplify surfaces, never
silhouettes.

## Visual Mechanics

- Smooth shaded surfaces with soft, simple falloff
- Clean unbroken silhouettes and slightly rounded edges
- Forms simplified and mildly exaggerated in proportion
- Soft global illumination and gentle contact shadows
- Minimal surface texture; material read by shading, not by detail
- Subtle rim light separating forms from ground
- No brush marks and no outline
- Depth of field mild if present at all

## Image-Model Prompt

```text
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
```

---

# 5. Photo Real — No Mark Of The Hand

## Key Question

What does this look like as a photograph taken on set?

## Description

Reads as a photograph. Detail is lens-accurate, materials behave
physically, and no trace of illustration survives anywhere in the frame.
The image should be assessable as a still from the finished film rather
than as a drawing of one.

## Operating Principle

If any mark reveals a hand made this, it is the wrong style. Everything
must be explicable as optics.

## Visual Mechanics

- Lens-accurate detail falloff and natural depth of field
- Physically correct material response — specular, roughness, subsurface
- Real-world lighting behaviour including bounce and occlusion
- Natural sensor noise structure in shadow
- Micro-detail present at every scale the lens would resolve
- Highlight rolloff and shadow retention of a real sensor
- No outlines, no brushwork, no stylisation of any kind
- Perspective consistent with a plausible real focal length

## Image-Model Prompt

```text
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
```

---

# 6. Industrial Design — The Presentation Drawing

## Key Question

What does this look like as the presentation drawing of a designed object?

## Description

The drawing an industrial designer makes to sell a form: the object
described precisely with clean keylines and controlled shading, sitting on
a neutral ground with no environment around it. The object is the subject
and the world is deliberately absent.

## Operating Principle

Describe the object, not the scene. Nothing in the frame may compete with
the form.

## Visual Mechanics

- Clean confident keylines describing form and section
- Controlled tonal shading, restrained and even
- Neutral ground with no environment or horizon
- Simple ground shadow anchoring the object only
- Material indicated by a small number of well-placed highlights
- Section, detail call-out or alternate view occasionally alongside
- Colour restrained, often a single accent against neutral
- No atmosphere, weather or scene lighting

## Image-Model Prompt

```text
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
```

---

# 7. Ink & Wash — Line Carries, Wash Tones

## Key Question

What does this look like as a graphic-novel page — pen line with wash
behind it?

## Description

Pen line carrying the drawing and diluted wash carrying the tone. The line
is the structure and the wash is atmosphere; the two are visibly separate
processes, and the paper stays present between them.

## Operating Principle

The line describes; the wash only weights. Never let wash do the drawing.

## Visual Mechanics

- Confident pen linework describing all structure
- Diluted ink wash in a limited number of tonal steps
- Wash pooling at edges with visible boundaries
- Paper white reserved for highlights, never painted back in
- Hatching used where wash cannot go
- Line unbroken by the wash sitting over it
- Restrained, often monochrome or duotone
- Visible brush-edge where a wash stroke ended

## Image-Model Prompt

```text
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
```

---

# 8. Gouache & Watercolor — Pigment On Paper

## Key Question

What does this look like painted in water media on real paper?

## Description

Pigment in water on a textured ground. Edges pool and granulate, the paper
grain shows through the thinner passages, and opaque gouache sits over
transparent washes. The medium is unmistakably physical and slightly
unpredictable.

## Operating Principle

Let the medium behave. Pooling, granulation and grain are the style, not
defects to clean up.

## Visual Mechanics

- Pigment pooling and hard edges where washes dried
- Paper grain visible through transparent passages
- Granulation and separation within washes
- Opaque gouache passages over transparent underwash
- Reserved paper white for the brightest notes
- Soft wet-in-wet transitions beside hard dry edges
- Slight blooming and backruns left in
- Colour mixing occurring on the paper, not only on the palette

## Image-Model Prompt

```text
A painting in gouache and watercolour on textured paper. Transparent
washes pool and dry to hard edges, granulating and separating within
themselves, with paper grain visible through the thinner passages. Opaque
gouache passages sit over transparent underwash. The brightest notes are
reserved paper white rather than applied paint. Soft wet-in-wet
transitions sit beside hard dry edges, and slight blooms and backruns are
left in rather than corrected. Colour visibly mixes on the paper itself.

Avoid: digital smoothness, airbrush, photographic detail, vector edges,
uniform flat fills
```

---

# 9. Technical Blueprint — Information, Not Picture

## Key Question

What does this look like as a dimensioned orthographic drawing?

## Description

An orthographic technical drawing: no perspective, no lighting, no
rendering. Form is described by keyline, section and dimension. This is
information rather than a picture, and it should be readable as a
document.

## Operating Principle

Communicate measurement and construction. Anything pictorial is out of
scope.

## Visual Mechanics

- Orthographic projection — no perspective convergence
- Uniform keyline weight with heavier outer profile
- Dimension lines, ticks, extension lines and leaders
- Hidden detail as dashed line
- Hatched section cuts at consistent angle
- Centrelines through axes of symmetry
- No lighting, no shading, no cast shadow
- Flat single-colour ground with monochrome linework

## Image-Model Prompt

```text
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
```

---

# 10. Rendered Illustration — No Visible Hand

## Key Question

What does this look like as finished illustration — painted, then worked
until no mark is left?

## Description

A fully rendered digital illustration, worked to a finish. Form is modelled
in continuous tone, gradients are blended smooth, and speculars are sharp
and deliberately placed. Detail is dense where the eye rests and falls away
steeply into suggestion behind the subject. It is unmistakably illustrated
rather than photographed, but nothing in it announces a hand.

## Operating Principle

Model in continuous tone and resolve every mark away. Spend detail only
where the eye rests, and let the falloff behind it be painted rather than
photographed.

## Visual Mechanics

- Continuous tonal modelling — no stroke, hatch, grain or paper tooth
  anywhere in the frame
- Gradients blended smooth across broad forms
- Sharp, deliberately placed specular highlights that describe what each
  material is
- Detail dense where the eye rests, resolved down to panel lines, seams and
  fasteners
- Steep detail falloff into soft suggestion behind the subject
- Hard subject edges against softer background edges — the falloff is
  painted, not photographed
- Colour laid in blended passages rather than discrete marks
- The surface of the artwork itself clean and unbroken
- Reads as finished illustration, never as a study or a sketch

## Image-Model Prompt

```text
A fully rendered digital illustration, worked to a finish. Form is modelled
in continuous tone — gradients are blended smooth and no stroke, hatch,
grain or paper tooth is visible anywhere in the frame. Specular highlights
are sharp and deliberately placed, describing what each material is. Detail
is dense where the eye rests, resolved down to panel lines, seams and
fasteners, and falls away steeply into soft suggestion behind the subject.
Subject edges are hard against softer background edges, and that falloff is
painted rather than photographed. Colour is laid in blended passages rather
than discrete marks. The surface of the artwork itself is clean and
unbroken. The result reads as finished illustration — not a study, not a
sketch, and not a photograph.

Avoid: photography, visible brushwork, cel outlines, flat vector fills,
paper or canvas texture, sketch underdrawing, impasto
```
