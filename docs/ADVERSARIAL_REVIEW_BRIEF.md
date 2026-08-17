# Adversarial review — brief for the reviewing agent

Paste everything below the line into the reviewing agent's first message.
It should have this repository connected, read-only.

Keep this file. When the report comes back, the response and the next
round are appended to `docs/REVIEW_ROUND_<n>.md`, and this brief is the
thing both sides re-read when an argument drifts.

---

You are reviewing **Screenboard Studio**, and your job is to find where it
is wrong. Not to praise it, not to summarise it, and not to rewrite it.
Produce a report; the implementing agent will answer it; we iterate until
both sides are satisfied, and the settled version becomes the
implementation plan.

Be adversarial about the product, not performatively harsh about the code.
A finding that changes what gets built is worth more than ten that are
merely true.

## What the product claims to be

An art department for a film production. It reads a screenplay, builds an
Art Direction Bible with the director, breaks scenes down element by
element with cited evidence, renders concept panels against approved
references, and assembles native-4K presentation boards.

Its stated reason to exist is preventing one failure: **image models
reinterpreting approved work.** Locked sheets, evidence classes, reference
jurisdictions, the no-upscale rule and hash-pinned approvals all exist to
make drift structurally hard once a human has said "this is canon."

The pipeline is strictly sequential and gated:

```
01 Screenplay → 02 Prod. Design → 03 Breakdowns → 04 Panels → 05 Boards
```

Only a locked breakdown can generate panels; a board needs every panel
approved.

## Read these first, in this order

| Path | Why |
|---|---|
| `docs/INTENT.md` | the premise in the product's own words |
| `CLAUDE.md` | the rules the implementing agent works under |
| `docs/ARCHITECTURE.md` | how it is put together |
| `app/static/DESIGN_SYSTEM.md` | the binding UI system; its `## Uncanonized patterns` table is the queue of unreviewed features |
| `docs/USER_GUIDE.md`, `APP_GUIDE.md` | what the user is told it does |
| `docs/RETIRED_PLANS.md` | decisions already made and closed — do not reopen these without new evidence |

Then the code. It is not large: `app/*.py` is ~15,800 lines across 28
modules, `app/static/app.js` is ~13,100 lines, `app/static/styles.css`
~3,600. There are 71 test files, ~1,250 app tests plus ~204 storefront.
`agents/*.md` describes the intended role of each pipeline stage — useful
for judging intent against implementation.

`storefront/` is a separate product surface (the sales site) with its own
design system. **Out of scope unless you find it contradicting the app.**

## The five questions

Answer these. Everything else is optional.

### 1. Premise versus implementation

Is the app achieving its stated goal in the best available way? Walk the
board-creation process end to end as a user would and judge the *shape* of
it, not the polish. Where does the mechanism serve the anti-drift promise,
and where is it ceremony that only looks like rigour? If a stage earns its
place, say so briefly and move on. If a stage exists because it seemed
orderly rather than because it prevents drift, say that plainly.

Name at least one thing you would **remove**.

### 2. Cognitive load, and simplification that respects the premise

The interface is dense on purpose: it states conditions rather than hiding
them. That is a deliberate stance, not an accident, and "it looks
complicated" is not a finding on its own.

What we want is where density stops paying for itself: two surfaces
reporting one fact, a step whose confirmation changes nothing, a number
the user cannot act on, a warning that fires when nothing is at stake.
Propose simplifications that keep the promise. A simplification that
weakens the gate model is not a simplification, it is a different product
— if you think the gate model itself is wrong, argue that as its own
finding rather than smuggling it in.

Read `DESIGN_SYSTEM.md` before criticising typography or colour. Its two
laws (amber is a signal, not decoration; Courier carries machine data,
Archivo carries hierarchy) are binding, and a violation of them **is** a
finding.

### 3. Intent versus implementation gaps — and things that do not work

Highest-value section. Prioritise it.

Find anything represented to the user that does not do what it says. This
codebase has a demonstrated history of exactly that failure, so hunt the
pattern rather than waiting to trip over it:

- **A capability built end-to-end with no caller.** Three were found in
  one day: a prompt editor, its Save, and `unapprove_candidate` — each
  complete in `store.py`/`main.py`, each unreachable from the UI. Sweep
  every route in `app/main.py` for a caller in `app.js`. One test now does
  this for candidate routes only; the same hole may exist elsewhere.
- **A label that lies.** A button reading `Read & edit` that only read. A
  camera default labelled "from Bible" that came from a different file. A
  strip reading "read-only" on a sheet that was editable.
- **One question answered by several different rules.** Four separate
  copies of "does this phrase name that thing" existed simultaneously and
  disagreed, so a panel showed a green REF marker while the render
  received no reference. Look for duplicated predicates generally.
- **A gate that reports only after the fact.** The product rule is that a
  gate must be readable as state *before* it is hit, with the unmet
  condition beside the disabled control and a link to where it is
  resolved. Find the ones that only surface as an error.
- **A test that passes through a broken surface.** ~1,086 tests once
  passed while a panel rendered with a horizontal scrollbar, because every
  assertion checked for the *presence* of a string rather than the
  *result*. Judge the test suite on whether it could detect the failures
  that actually happened. A CSS parse error silently dropped two-thirds of
  the stylesheet and nothing failed.

For each gap, state what the user is told, what actually happens, and how
you verified it. **Verification matters more than volume.** Say plainly
whether you read code, ran it, or inferred it — an inferred finding is
still welcome, labelled as inferred.

### 4. Agent-facing structure: skills and reference files

The implementing agent works from `CLAUDE.md` plus a set of reference
documents, and loads skills from `.claude/skills/`. Some of that structure
is load-bearing and some is sediment.

Propose the **file and skill structure** that would most improve a future
agent's effectiveness on specific features. Concretely:

- Which documents does an agent actually need before touching a given
  area, and which are stale, duplicated, or never read? `docs/` holds 20+
  files including several dated handoffs and audits.
- What deserves to be a **skill** — a repeatable procedure with a checklist
  — rather than prose an agent may skim? `/design-verify` and `/iterate`
  exist; say what else should, and what should stop being one.
- Where would a short, checkable rule have prevented a real defect above?
  Rules that pay for themselves are the ones a reviewer can verify in one
  command.

Be specific enough to implement: propose paths, and what each file
contains, and what it deliberately leaves out.

### 5. Token economy

Every model call spends the user's money. Judge the pipeline for waste and
name the wins available.

The pattern to emulate: the screenplay is extracted to text **once**, and
the raw PDF is never sent to a model — the extracted text is the agents'
copy, the upload is the user's to read. That single decision removed a
recurring cost from every downstream call.

Look for: documents re-sent that could be cached or extracted once;
prompts that carry material the model cannot use; a model asked to do
deterministic work that code should do; full-file passes where an anchored
excerpt would serve; retries that re-send everything. `app/generate.py`
compiles an ~11,000-character prompt per panel — audit what earns its
place in it, and note that a prompt is not automatically better for being
longer.

Also flag the inverse: anywhere the app is *too* stingy and produces bad
output to save a few thousand tokens. Under-spending that forces a
re-render costs more than it saved, because images cost far more than text.

## What not to do

- Do not rewrite `DESIGN_SYSTEM.md` or `STORE_DESIGN_SYSTEM.md`. They are
  upstream of the code; when they disagree, the code is wrong.
- Do not propose a CSS framework, a build step, a bundler, npm, new fonts,
  new accent colours, gradients, rounded corners, or emoji. There is no
  build step by design and that is not up for review.
- Do not propose upscaling renders, or any relaxation of the no-upscale
  rule. It is the product's most-stated promise.
- Do not reopen anything in `docs/RETIRED_PLANS.md` without new evidence.
- Do not send the raw screenplay upload to a model in any proposal.
- Do not pad the report. A section with nothing to say should say "nothing
  to add" and stop.

## The report

Write `REVIEW_v1.md` in the repository root. Later rounds are `v2`, `v3`.
Never edit a published version — a superseded finding is answered in the
next version, so the argument stays legible.

Head it with a table of contents and this front matter:

```
version:    1
date:       <ISO date>
app_sha:    <git rev-parse --short HEAD>
read:       <which files you actually read, and which you only listed>
ran:        <what you executed, if anything>
```

Then one section per question above. Number every finding `F1`, `F2`, … and
give each:

- **Claim** — one sentence.
- **Evidence** — file and line, a command and its output, or "inferred".
- **Severity** — `BLOCKING` (the product does not deliver its promise) /
  `SERIOUS` (a user is misled or work is lost) / `WORTH FIXING` /
  `TASTE` (defensible either way, stated as taste).
- **Proposal** — what you would do instead, concretely.
- **Cost** — your honest guess at whether this is a small change, a
  refactor, or a redesign.

Close with **Top 10 in priority order**, and a short section called
**Where I could be wrong**, naming the findings you are least sure of and
what would settle them. That section is not humility theatre — it is where
the next round starts.

## The loop

The implementing agent will answer every finding with one of: `ACCEPTED`,
`ACCEPTED WITH CHANGES` (and what changes), `REJECTED` (and why), or
`NEEDS EVIDENCE` (and what would settle it). Answers land in
`docs/REVIEW_ROUND_<n>.md`.

You then produce the next version, dropping what was settled and pressing
what was not. We stop when both sides agree the remainder is taste. The
settled set becomes the implementation plan.

Two things will earn a fast `REJECTED`, so avoid them: a finding that
proposes a different product rather than a better version of this one, and
a finding that cannot be verified. Two things will earn a fast `ACCEPTED`:
a named thing that does not work, and a place where one fact is reported
by two surfaces that can disagree.

Assume the implementing agent knows this codebase better than you do and
has still missed things — because it demonstrably has. Your advantage is
that you have not spent a week becoming used to it.
