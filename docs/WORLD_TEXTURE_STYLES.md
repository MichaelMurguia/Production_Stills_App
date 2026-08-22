# World Texture Styles

## Purpose

These five world textures are reusable material grammars for production
stills. Each describes **how far the world has travelled from new** —
wear, patina, entropy, and the story that surface tells about use.

Each style uses a common format:

1. Key Question
2. Description
3. Operating Principle
4. Visual Mechanics
5. Image-Model Prompt

**Scope fence.** World texture owns surface condition and nothing else. It
does not set the palette (the Color Palette anchor owns hue, value key and
saturation), it does not set the light (the Cinematography anchor owns
light behaviour), and it does not set the medium a panel is drawn in (the
Rendering Style anchor owns that). A texture that starts prescribing
colour or lighting has left its jurisdiction.

This file is the source of truth: the app parses it, so editing a style
here changes the picker and every future prompt. Adding a `# n. Name —
Subtitle` section adds a style; deleting one removes it.

---

# 1. Pristine — Nothing Has Aged

## Key Question

What does this world look like the moment before anything has touched it?

## Description

Surfaces are as they left manufacture. Finishes are unbroken, tolerances
are visible in how precisely parts meet, and there is no accumulated
history anywhere on the frame. Pristine is a texture philosophy, not the
absence of one: an unmarked surface is a deliberate statement about
control, wealth, newness or sterility, and it should read as chosen rather
than as unfinished rendering.

## Operating Principle

Absence of wear is information. If nothing has aged, the frame should say
who is preventing it from ageing.

## Visual Mechanics

- Unbroken factory finishes; no scratches, chips or scuffs
- Panel gaps even and consistent along their whole run
- Edges crisp, corners unrounded by handling
- Specular highlights clean and continuous across a surface
- No dust settle in horizontal recesses or seams
- Fasteners unmarked, no tool witness around them
- Coatings uniform — no thin spots, no touch-up mismatch
- Contact points (handles, treads, sills) identical to surfaces nobody touches

## Image-Model Prompt

```text
Surfaces are factory-new throughout. Finishes are unbroken and uniform,
with no scratches, chips, scuffing or discoloration anywhere. Edges are
crisp and corners are not rounded by handling. Panel gaps are even along
their full length. Specular highlights run clean and continuous across
each surface. No dust has settled in seams or horizontal recesses.
Fasteners show no tool marks. Areas that would normally be touched — 
handles, treads, sills, controls — are indistinguishable in condition from
areas nobody touches. The cleanliness reads as maintained and deliberate,
not as an unfinished render.

Avoid: wear, patina, rust, dust, grime, scuffing, weathering, repair marks
```

---

# 2. Lived-In — Wear Where Hands Go

## Key Question

Where would this world actually be touched, and what would that leave?

## Description

Used and maintained. Everything is in service, nothing is failing, and the
wear is legible as a map of human traffic: worn where hands, feet and
tools actually go, intact everywhere else. This is the texture of a
working, cared-for world — the difference between a place that is old and
a place that is used.

## Operating Principle

Wear is a record of behaviour. Put it exactly where the body would put it,
and nowhere else.

## Visual Mechanics

- Wear concentrated at contact points — grips, edges, treads, latches
- Polish rather than damage on frequently handled surfaces
- Finish thinned to substrate at high-traffic corners
- Fabric nap flattened where weight rests
- Fingerprint and hand-oil accumulation near controls
- Floor wear following actual walking lines, not spread evenly
- Everything functional; nothing broken or awaiting repair
- Surfaces away from traffic still close to new

## Image-Model Prompt

```text
The world is in daily use and well maintained. Wear is concentrated
precisely where a body would touch: grips are polished smooth, edges and
tread plates are burnished, latches and controls carry hand-oil sheen and
thinned finish. Floor and stair wear follows the real walking line rather
than spreading evenly. Fabric shows flattened nap where weight rests.
Surfaces away from traffic remain close to new, which makes the worn
places read as a map of use. Everything is functional — nothing is
broken, corroded or awaiting repair.

Avoid: decay, ruin, structural failure, rust-through, abandonment, uniform
all-over grime
```

---

# 3. Weathered — Exposure, Then Repair

## Key Question

What has the outside done to this, and who patched it afterwards?

## Description

Exposure has done its work and someone has answered it. Sun has pulled
colour out of upward faces, water has run and left its track, metal has
oxidised where coating failed — and then a human intervened: a patch, a
mismatched panel, a re-coat that does not quite match. The presence of
repair is what separates weathered from decayed. This world is fought for.

## Operating Principle

Weather acts from a direction. Show where it came from, and show the
answer somebody made to it.

## Visual Mechanics

- Sun-bleach strongest on upward-facing and south-facing planes
- Water tracking and staining running downward from seams and fixings
- Oxidation blooming where coating has failed, not uniformly
- Repairs visible and deliberately imperfect — mismatched patches, over-paint
- Sheltered undersides markedly less affected than exposed faces
- Sealant and tape applied over failures, itself now ageing
- Fastener heads rust-stained while surrounding surface holds
- Chalking and matting of once-glossy finishes

## Image-Model Prompt

```text
Surfaces show long outdoor exposure that someone has been fighting.
Sun-bleach is strongest on upward and sun-facing planes; sheltered
undersides are noticeably less affected, so the weathering reads
directional rather than uniform. Water tracks downward from seams and
fixings leaving stain trails. Oxidation blooms where coating has failed
rather than spreading evenly. Fastener heads carry rust bleed onto sound
surface around them. Repairs are visible and imperfect: mismatched
patches, over-painted areas that do not match, sealant and tape applied
over failures and now ageing themselves. Once-glossy finishes have
chalked and gone matt.

Avoid: abandonment, structural collapse, reclaiming vegetation, pristine
finishes, uniform dirt layer
```

---

# 4. Decayed — Past Maintenance

## Key Question

What is left standing after nobody came back?

## Description

Maintenance stopped a long time ago. What remains is what has not
collapsed yet, and the world is being taken back — rust has moved from
surface to structure, growth is entering through failures, and loads have
found new paths through what is still standing. Nobody is fighting this.
The absence of repair is the point.

## Operating Principle

Nothing is being repaired. Every surface should read as the outcome of
that, not as damage somebody has yet to fix.

## Visual Mechanics

- Structural failure, not just surface damage — sag, buckle, collapse
- Rust through section, perforation, section loss at load points
- Growth entering through breaches; roots and moss in seams
- Glazing broken or gone, apertures open to weather
- Debris fallen and left where it landed, settled by time
- Coatings gone entirely rather than thinned
- Standing water, silt lines, biological staining
- No fresh material anywhere in frame — no patch, no tape, no paint

## Image-Model Prompt

```text
Maintenance ceased long ago and nothing here is being repaired. Damage is
structural rather than cosmetic: members sag and buckle, rust has eaten
through section at load points, and loads have visibly redistributed
through what still stands. Growth enters through breaches — roots, moss
and stems in seams and openings. Glazing is broken or absent and
apertures stand open to weather. Fallen debris lies where it landed and
has settled with time; silt lines and biological staining mark standing
water. Coatings are gone entirely rather than merely thinned. No fresh
material appears anywhere: no patch, no tape, no new paint, no sign of
anyone returning.

Avoid: repair, patching, occupancy, maintained equipment, fresh paint,
tidiness
```

---

# 5. Industrial Grime — What The Work Leaves

## Key Question

What does the work itself deposit on the surfaces that do it?

## Description

Heavy use rather than age. These are hard-wearing surfaces in active
service, carrying exactly what the process running on them deposits: oil
film, carbon, swarf, scale, dust of whatever is being handled. The
equipment is sound and working — the grime is a by-product of function,
not a symptom of neglect, and it accumulates according to what each
surface actually does.

## Operating Principle

Grime is deposited by a process. Put it where that process throws it, and
keep the machine sound underneath.

## Visual Mechanics

- Oil film and drip paths tracking from bearings, joints and fill points
- Carbon and soot deposit heaviest near exhaust and heat sources
- Swarf, scale and process dust collected in horizontal catches
- Hand-black transferred to controls, rails and door furniture
- Wiped-clean zones where an operator must actually see — gauges, sight glasses
- Floor staining pooled under machines, tracked outward by traffic
- Surfaces sound and functional beneath the deposit
- Hard-wearing substrates — steel, concrete, rubber — not delicate finishes

## Image-Model Prompt

```text
Hard-wearing industrial surfaces carrying the by-products of active work.
Oil film and drip paths track downward from bearings, joints and fill
points. Carbon and soot are heaviest near heat sources and exhausts.
Swarf, scale and process dust collect in horizontal catches and ledges.
Controls, rails and door furniture carry transferred hand-black, while
gauges and sight glasses are wiped clean in exactly the arc an operator
reaches. Floor staining pools beneath machines and is tracked outward
along traffic lines. Beneath the deposit every surface is sound and
functional: this is a working plant, not a derelict one, and substrates
are steel, concrete and rubber rather than delicate finishes.

Avoid: organic decay, rust-through, abandonment, structural failure,
delicate finishes, uniform even dirt
```
