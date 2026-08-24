# Plan — first user test, 2026-08-23

**Status: FOR REVIEW. Nothing here is implemented.** Approve, modify or
strike items by ID. Sources: `feedback/Adam_Feedback_2026_08_23 13_21 PDT.md`
and the `ANCESTOR` production backup.

**One correction to the notes before anything else.** Gemini's diarization
failed — every transcript line is attributed to "Michael Murguia", and the
auto-summary then guessed at who said what and got it backwards in places
("Adam guided Michael through the process of setting up panel breakdowns";
"Michael reported a significant issue where progress disappears upon
reloading"). The tester reported the reload bug and was the one being
guided. The **raw notes** at the end of the file and the transcript body are
reliable; the Details section's attributions are not. Worth fixing before
this circulates. (The file is named Adam; you wrote Ada — one of the two is
wrong and it should be settled before it reaches him.)

---

## Part 1 — The three render failures, diagnosed

All three are **app defects, not model hallucinations.** Each was traced to
a mechanism in his data and verified against the code. That distinction
matters commercially: the product's claim is canon-locking, and a
hallucination would undermine it. These don't — they're our bugs.

### D1 — The WW2 plane: the app told the model to draw it

**PROVEN.** The compiled prompt for `SHIP_DESCENDS_V1 / P01` contains:

```
REQUIRED CONTENT
- matte hull the size of a fishing boat
- pan with crust and salt
- shivering air beneath the hull
- unlit open ramp
- six descending figures

SUBJECT IDENTITIES — required content above includes these canon subjects.
Render each as EXACTLY what it is named to be — never a generic substitute:
- LEDGER SIX (VEHICLE): RECON AIRCRAFT. SURVIVOR. EYE. Compact aircraft with
  tail flash 118. Riveted airframe older than its pilot. Sun-cracked paint
  and scratched canopy. Returns with nineteen holes and riveted patches...
```

A riveted, sun-cracked, patched recon aircraft — a verbal portrait of a WW2
plane — was **commanded** into a panel about a matte hull on a salt pan. The
model complied. It was never inventing.

**Why it matched.** `subjects_for_object()` matches a required object against
any *distinctive* word of a subject's name. Verified against his data:

```
'six descending figures'  ->  matched words: ['six']   ->  LEDGER SIX
(the other four required objects matched nothing)
```

The word **"six"**. `NAME_STOPWORDS` holds `the/and/for/with/...` but no
numerals and no general vocabulary, and the distinctiveness rule only
suppresses a word shared by two cards *of the same kind* — "six" appears in
one card, so it counted as identifying.

**Two aggravating factors, both worth fixing on their own:**

- The heading asserts *"required content above includes these canon
  subjects."* That was **false**. Nothing in the required list is LEDGER SIX.
  The prompt states a falsehood to the model with full authority.
- `forbidden_elements` guards ground intrusions ("unsupported buildings,
  roads, vegetation, or ground vehicles") but says nothing about aircraft or
  period. There was no backstop.

> **Note on the fix's risk.** This matcher is deliberately loose because it
> was fixed in the other direction on 2026-08-16: asking for the card's
> *whole* name meant `Sal inside the cryochamber` matched nothing, a panel
> rendered with no identity text, and a stranger's face came back. Tightening
> it without re-testing that case will reintroduce a worse bug. Any change
> here keeps the Sal case as a regression anchor.

**Proposed:**

| ID | Change | Size |
|---|---|---|
| **D1.1** | Numerals and common-vocabulary words never identify a subject on their own. A card whose only matching word is `six`/`one`/`dark`/`team` requires a second signal. | S |
| **D1.2** | The SUBJECT IDENTITIES heading stops asserting the subject is required. Say what is true: *"canon subjects that MAY appear."* One line, removes a lie from every prompt. | XS |
| **D1.3** | A matched subject whose `kind` is absent from the panel's required objects is **shown to the user before the spend**, in the breakdown, as *"LEDGER SIX (VEHICLE) will be described to the model because panel P01 says 'six'."* Reviewable, strikeable. | M |
| **D1.4** | Era/anachronism guard: the production states its period once; every prompt carries it as a forbidden clause. His screenplay is 230 years ahead and no panel ever said so in its own content. | M |

I recommend **D1.1 + D1.2 now**, D1.3 next, D1.4 as a product decision — it
touches the bible and every prompt.

### D2 — The ship reference that wouldn't stick: two separate faults

**PROVEN.** Reference attachments on every take of P01:

| Take | Status | References attached |
|---|---|---|
| CAND-0001 | APPROVED | PALETTE only |
| CAND-0002 | REJECTED (repair) | none |
| CAND-0003 | candidate (repair) | none |
| CAND-0004 | APPROVED | PALETTE only |
| CAND-0005 | candidate — **after he added and ticked "dark ship"** | **PALETTE only** |

**Fault A — the tick is not persisted anywhere.** The spec's panels carry
`camera_angle`, `required_objects`, `forbidden_objects`, `evidence`… and **no
reference field at all.** Selection is a per-request parameter passed at
generate time, so it lives only in the open page. In the session he ticked
the ship, then *rejected* the take, then generated — and the selection was
gone. `REF-0046` is APPROVED and would have ridden had it been sent, so the
client did not send it.

**Fault B — the ship is filed as a person.** `REF-0046` role is
`CHARACTER_LIKENESS — DARK SHIP`, because the walkthrough said to pick
"character likeness". Under reference jurisdiction, that role's scope is a
character's identity — the wrong jurisdiction for a vehicle. Even had it
ridden, it would have been introduced to the model under the wrong authority.

**Proposed:**

| ID | Change | Size |
|---|---|---|
| **D2.1** | Persist per-panel reference selections on the spec. A tick survives reject, redraw, navigation and reload. This is the actual bug. | M |
| **D2.2** | Role list offers a vehicle/object scope for crop references, and the picker stops defaulting a non-person to CHARACTER_LIKENESS. | S |
| **D2.3** | The generate control states what will ride *before* the spend — the app already computes this server-side (`resolved_attachments`); it isn't shown at the moment of spending. He would have seen "1 reference: PALETTE" and known. | M |
| **D2.4** | Retroactive: a role-repair action so a mis-filed reference can be re-scoped without re-cropping. | S |

**D2.1 and D2.3 are the pair that matter.** D2.1 stops the loss; D2.3 means
the next loss is visible before money is spent rather than after.

### D3 — Modern, weathered people: we attached the wrong faction's palette

**PROVEN, and this one is my favourite because the bible was right.**

His bible states the rule exactly:

> *Weathered Present / Pristine Future — a weathered wartime world
> interrupted by people from the future who come down pristine.*
> *The Descent Team is the controlled exception… unweathered bodies must
> register as pristine.*
> *…separated from the other worlds by pristine neutrality and the absence
> of warm institutional colour.*

That language **was** in the prompt. The panel's `design_languages` is
`["THE DESCENT TEAM"]`. And then the only image attached to the render was:

```
COLOR_PALETTE — FENN HARROW COMPACT
```

**Fenn Harrow is the weathered wartime faction** — patched timber, oxidized
metal, rationed amber. The prompt hands that image authority over *"the
film's COLOR LANGUAGE — the permitted hues, the global value key, and how far
saturation may travel."*

**Why.** `store.auto_style_references()` buckets by role *head* — every one of
his 30 approved palettes is `COLOR_PALETTE` — then attaches the **newest two**.
It never reads the panel's design language. He had 44 palettes across three
factions; the panel got whichever was most recent.

So the one image the model saw was the visual opposite of the panel's subject,
while LEDGER SIX simultaneously described sun-cracked paint and rivets. The
pristine instruction was outnumbered.

**Proposed:**

| ID | Change | Size |
|---|---|---|
| **D3.1** | Auto-attached style anchors respect the panel's design language. A palette scoped to a design language rides only panels using it; unscoped palettes stay global. | M |
| **D3.2** | When no palette matches the panel's language, attach none and say so, rather than attaching an arbitrary one. Silence beats the wrong faction. | S |
| **D3.3** | Panel-level required content can carry a condition attribute, so "six descending figures" becomes "six descending figures — pristine, unweathered". The bible said it 8,000 characters away; the panel never did. | M |

**D3.1 is the fix.** D3.2 is the principle it should fail by.

---

## Part 2 — The bug he hit that loses work

### B1 — Answers vanish on reload *(highest severity, unrelated to renders)*

His words: *"if I reload the page I can tell you that stuff's going away. I
don't know where."*

[`app.js:5321`](app/static/app.js#L5321):

```js
const saveAnalysis = a => {
  wizAnalysis = a;
  wizACacheSet(a);
  api("/api/wizard/analysis", { method: "PUT", json: a }).catch(() => {});
  ...
};
```

Local state and cache update immediately, so the UI shows the answer saved.
The persistence is **fire-and-forget with the error swallowed**. If the PUT
fails or hasn't landed before a reload, the app has already claimed success.

This compounds D1–D3: the open questions his breakdown raised included *"What
is the hull's exact geometry, colour, and surface construction beyond being
matte and fishing-boat-sized?"* — the app correctly identified the single
biggest visual unknown, asked, and then dropped the answer. The nebulous ship
he complained about was a question the app knew to ask.

| ID | Change | Size |
|---|---|---|
| **B1.1** | Await the save; surface failure; never render an unsaved answer as saved. | S |
| **B1.2** | Audit every `.catch(() => {})` on a write path — same defect class as the credential audit: success reported without confirmation. | M |

**B1.1 should ship first of everything in this document.** It loses user work
and it's small.

### B2 — Gates that refuse instead of stating themselves

Two in one session, both violating our own rule that a gate is readable as
state *before* it is hit:

- **Repair Region** silently refused until an instruction was typed. On the
  call: *"why isn't it allowing you to repair region. I don't know why that's
  a bug."* If the author can't tell, no customer can.
- **The board stayed locked** after approval, with no statement of the unmet
  condition.

| ID | Change | Size |
|---|---|---|
| **B2.1** | Repair Region states its precondition beside the disabled control. | S |
| **B2.2** | Board lock states which panels it is waiting on, and links to them. | S |

### B3 — Reported, not yet reproduced

Listed so they aren't lost; each needs confirmation before it's scheduled.

| ID | Report |
|---|---|
| **B3.1** | 404 opening the workspace; worked on a later attempt. Intermittent — routing or a cold tenant. |
| **B3.2** | Windows threw repeated trojan/security warnings after launch. **Investigate first** — if the download trips SmartScreen this outranks every UX item, because it stops installs. |
| **B3.3** | "Screenplay here" did not show the screenplay. |
| **B3.4** | A ChatGPT dropdown in the script scene plan that cannot be opened. |

---

## Part 3 — The structural feedback

These are not bugs, and two of them are bigger than any bug here.

### S1 — "The surface is an instrument"

> *"AI wants to make all surfaces a narrative surface. Don't let it. The
> surface is an instrument."*
> *"Get rid of all this kind of stuff: 124-PAGE DRAFT, READ IN FULL / 6 DESIGN
> LANGUAGES / 8 ENVIRONMENTS / EVERY IMAGE BELOW IS FROM IT"*
> *"AI wants to tell you a story with the app, which just confuses things."*

A creative director in the target audience handing over a design principle,
with the offending copy named. The app narrating its own accomplishments
instead of behaving like a tool.

**Recommendation: this goes to Claude Design as a ruling, not a copy edit.**
It's a standard that should govern future copy, and it plausibly belongs in
`DESIGN_SYSTEM.md` beside the amber and typography rules. The design queue is
already past its review trigger; this is a good reason to run that review.

### S2 — "The engine should fill out EVERYTHING, then ask for overrides"

> *"Production Design part was HARD. I really didn't know what to do, and
> stopping to read carefully didn't really help me."*
> *"I wish it was like, 'Screenplay? Got it. And from that screenplay I know
> everything I need to know. Have a nice day, BAM!' But… if ya want to guide
> me go ahead."*
> *"Parsing felt magical — because I recognized my locations, characters,
> every slug line it read."*

Note the shape: the parse delighted him, the **form** defeated him. The app's
sequential gating is right, but it currently presents each stage as work to
be done rather than work already done and open to override.

Smaller items in the same family, each cheap and each removing a decision he
couldn't make:

| ID | Change |
|---|---|
| **S2.1** | Cast members offer **Generate** from the screenplay, not only photo upload. He expected this and it's the first thing he hit. |
| **S2.2** | Sample location is a dropdown of the screenplay's own sluglines — *"you have all the headlines"*. |
| **S2.3** | Spec ID is picked from the scan, not typed. *"I don't have the vocabulary to understand what this should actually be."* |
| **S2.4** | Breakdown creation stops requiring copy-paste of a scene. Your own words on the call: *"this is all bad, right? You shouldn't have this experience."* |
| **S2.5** | Relabel the model test to **"Test your model"** — already agreed in the notes. |
| **S2.6** | A draft-resolution first take. He asked whether it renders rough or final; production res on take one is slow and expensive for a look-see. |

**S2.1 through S2.3 are small and land directly on his stated confusion.**
S2.4 is a larger redesign and should be scoped separately.

### S3 — API keys are a barrier to the audience *(business decision)*

> *"I don't want to put my key in, and most people won't have an API key."*
> *"The technical friction I feel is API keys. I'm trying to figure out how to
> fund this thing. I want to — but figuring out how to is hard because of my
> own technical gaps."*

Independent convergence worth naming: the security audit reached the same
place from the other side. Encryption at rest cannot make a hosted key private
from us, and the only real answers were *don't hold the key* or *don't take
one*. He arrives at "don't make me bring one" as an **adoption** problem.

Two signals pointing at the same design is the strongest evidence in this
document. **No engineering proposed** — it's your call, and it changes the
business model. Options as I understand them: proxy through your account and
bill usage; a bundled starter allowance; or keep BYO-key and accept the
audience it selects for.

### S4 — Store and first-run

| ID | Report |
|---|---|
| **S4.1** | No "Try for Free" button found anywhere. |
| **S4.2** | The trial button led to a login where he nearly signed up with his work account; **"have a code" was light grey** and almost missed. A hierarchy problem in exactly the place a wrong click costs a customer. |
| **S4.3** | The gallery showed text and pricing where he expected thumbnails. *"All the other stuff, pricing, cloud based, can go elsewhere."* |

S4.2 is the one with money attached.

---

## Part 4 — What I'd deliberately not do

- **Don't tighten the subject matcher aggressively.** The loose behaviour is a
  fix for a worse bug. D1.1 narrows one class (numerals, common words); going
  further re-opens the wrong-face failure.
- **Don't add an era filter to the model's output.** D1.4 states the period as
  canon; it should not become a post-hoc content check.
- **Don't rebuild Production Design before the design review.** S2 and S1 point
  at the same surface, and rebuilding it twice would be waste.
- **Don't treat the repair tool's perspective mismatch as a bug.** It behaved
  as designed on a large region; the fix is expectation-setting, which is
  already covered by B2.1's family.

---

## Part 5 — Suggested order

Sequenced by damage, not by size. **Every item still needs your approval.**

1. **B3.2** — the security-warning report. If installs are being blocked,
   nothing else matters. Investigate before scheduling anything.
2. **B1.1** — stop losing his answers.
3. **D1.1 + D1.2** — stop commanding aircraft into panels.
4. **D3.1 + D3.2** — stop attaching the wrong faction's palette.
5. **D2.1 + D2.3** — make a ticked reference survive, and show what will ride.
6. **B2.1 + B2.2** — the two silent gates.
7. **S2.1–S2.3, S2.5** — the cheap "fill it in for me" wins.
8. **S1** to Claude Design as a ruling; **S3** to you as a business decision.

Items 2–6 are all defects with mechanisms already identified, and each has a
natural regression test — his production makes an excellent fixture, and D1's
test writes itself: *the word "six" must never summon an aircraft.*

---

## Appendix — evidence index

| Claim | Where it was verified |
|---|---|
| LEDGER SIX injected into P01 | `data/boards/SHIP_DESCENDS_V1/CAND-0001.json` → `prompt`, SUBJECT IDENTITIES block |
| "six" is the matching word | `app.validation.name_words('LEDGER SIX')` run against P01's five required objects |
| No reference persisted on panels | `data/specs/SHIP_DESCENDS_V1.json` → panel keys contain no reference field |
| Ship filed as a character | `data/references/references.json` → `REF-0046`, role `CHARACTER_LIKENESS — DARK SHIP` |
| Ship never attached after ticking | `CAND-0005.json` → `references` = PALETTE only |
| Wrong palette rode | `CAND-0001/0004/0005` → `COLOR_PALETTE — FENN HARROW COMPACT`; panel `design_languages` = `THE DESCENT TEAM` |
| Palette chosen by recency, not language | `store.auto_style_references()` — buckets by role head, newest `STYLE_ATTACH_CAP` (2) |
| The bible was correct | `context/01_ART_DIRECTION_BIBLE.md` → Overall Visual Identity, Descent Team material language |
| Save is fire-and-forget | `app/static/app.js:5321` |

**Checked and found NOT to be a problem:** the apparent mojibake in
`unresolved_questions` is a proper U+2019 right quote rendering badly in my
console — the stored text is clean. No encoding bug.
