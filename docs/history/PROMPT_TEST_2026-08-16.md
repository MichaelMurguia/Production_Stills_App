# Hand test — does the verbatim screenplay fix the confrontation panel?

Two takes, run separately. Take A tests whether the screenplay's own stage
directions are enough on their own. Take B adds an explicit staging block.
Run them in that order — running both at once cannot tell you which half
did the work, and the answer decides what gets built.

Keep the model, size and aspect identical to the take you are comparing
against, or the comparison is not one.

Both takes will be filed with `prompt_source: edited` and read back on the
card under **Edited render prompt**. Steps 01–04 are untouched, so the next
normal take compiles from the panel again.

---

## Where it goes

Panels → the confrontation panel → step **05 PROMPT** → `Read & edit`.

Scroll the textarea to the block that reads:

```
THE SCENE
At night, Sal ... <a summarised paragraph>
```

Put the new text **directly under that paragraph**, above the line that
reads `PANEL PURPOSE`. Do not delete the summary — leaving it in place is
what makes this an additive test.

If the panel has no `THE SCENE` block at all, put it immediately after the
`SETTING` block instead.

---

## TAKE A — paste this

```text
THE SCENE — AS WRITTEN
The following is the screenplay scene this panel comes from, verbatim. It
is the authority on what is physically present, where it sits, and what
state it is in. Read its stage directions as staging instructions.

Render ONE still image of a single moment from it. Dialogue is context,
not content — do not render text, speech, or lettering. Camera moves
described below (DOLLY, PUSH IN) describe the scene's coverage, not this
frame: the CAMERA block later in this prompt governs this panel's framing
and overrides them.

INT. TERRA NOVA SECURE BAY - NIGHT

CLOSE ON SAL's eyes. Cold, calculating, defiant. His breath fogs the air.
We only see his face at first - sweat beads, a faint frost line at his
hair.

As he speaks, the camera DOLLIES BACK, revealing restraints across his
chest, arms, and legs. A curved glass door frames him. Frost tendrils
creep along the edges. Behind him - an airlock hatch.

SAL
Humanity will eat itself alive without me. You think they'll choose
freedom over order?

His voice echoes in the cold. We DOLLY FURTHER BACK - revealing the whole
cryochamber. Tubes snake into ports on his suit. Subtle vapor leaks from
the seals.

TOM steps into frame from shadow, calm but edged with steel.

TOM
You froze yourself for a century just to wake up and crown yourself king.

SAL
Order is survival. Chaos is death.

TOM
Yeah. Maybe.

SAL
When you're rationing hope like oxygen, you'll need me to...

Tom hits a control. With a violent HISS, the cryochamber SLAMS SHUT
mid-sentence - Sal's final word cut off. Freezing gas floods in, coating
him in rime in seconds. His eyes lock on Tom as frost claims them.

The chamber seals with a deep metallic THUD.

THE MOMENT THIS PANEL DEPICTS
Tom has stepped from shadow and Sal is still speaking. He has NOT yet hit
the control. Everything the scene describes after "Tom hits a control" —
the chamber slamming shut, the freezing gas, the rime, the seal — has not
happened yet and must not appear.
```

Generate. Then look for the four things:

1. an airlock hatch behind the cryochamber, and whether its door reads round
2. the chamber standing **open**
3. sweat on Sal's face with frost at his hairline — both at once
4. Tom reading as having stepped out of shadow, rather than standing in
   the foreground with his back to camera

Write down which of the four landed. That number is the whole result.

---

## TAKE B — only if A left things out

Go back into `Read & edit` (it recompiles clean each time, so Take A's
text is gone). Paste Take A's block again, and then add this immediately
after it:

```text
STAGING — WHAT IS IN FRAME, WHERE, AND IN WHAT STATE
This overrides any conflicting arrangement implied elsewhere. Every item
below is a fact about this frame, not a suggestion.

- The cryochamber door is OPEN. Sal is visible and unglazed — nothing
  between him and the room.
- The door is a single CURVED glass panel, swung or slid clear of the
  opening, and it is visible in frame in its open position.
- Directly BEHIND the cryochamber, set into the far bulkhead, is an
  AIRLOCK HATCH: a circular iris door, closed, its overlapping leaves
  reading clearly as a mechanism that opens by rotating apart.
- Sal is upright inside the chamber, held by restraints across his chest,
  arms and legs. Tubes run from ports on his suit into the chamber wall.
- Sal's face carries BOTH conditions at once: sweat beaded on his skin,
  and a distinct line of frost in his hair and across his brow. He is hot
  and freezing in the same shot. He is mid-speech, eyes on Tom.
- Vapor leaks from the chamber seals and pools low across the deck.
  Frost tendrils creep along the edges of the door frame.
- TOM stands clear of the chamber, having just stepped OUT OF DARKNESS
  into the light: the shadow he came from is visible behind and beside
  him as an unlit part of the bay. He is lit only along one edge. He
  faces Sal. His face is at least partly readable.
```

Generate again and score the same four.

---

## What the result decides

| Outcome | What it means | What gets built |
|---|---|---|
| A gets all four | the summary was the only problem | carry the scene verbatim; no new field |
| A gets some, B gets the rest | verbatim helps, but state and relation need their own slot | verbatim **and** a per-panel staging field |
| B misses things too | the failure is not the prompt — it is the model, the references, or the camera | investigate before building either |

That third row is a real possibility and worth naming in advance: if B
cannot put a round airlock behind the chamber when told to in plain
words, no amount of prompt engineering upstream will do it either, and
the fix is a reference plate, not a field.

## One more thing to check while you are in there

The panels I inspected locally had `camera: {}` — nothing set on any axis.
The script opens CLOSE ON Sal's eyes and dollies back, and an unset camera
means the model chose the wide you got. Look at step 03 on this panel
before you run Take A. If it is empty, that is a second, independent cause
of the same complaint, and it is worth fixing separately rather than
letting the prompt text try to compensate for it.
