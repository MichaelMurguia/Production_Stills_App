# First run — the arrival flow

*Written 2026-08-17, walked end to end against a booted empty install
rather than described from the code. This is the one document that follows
a **new user** from nothing to their first upload; `docs/INTENT.md` §"The
pipeline" picks up where this ends, and `docs/USER_GUIDE.md` is the
screen-by-screen reference for everything after.*

Two things arrive at once for a new user and they are easy to confuse:

- **The app's own first-run screens** — the "name the show" screen and the
  Settings setup form. These are structural: they are the only thing
  reachable, and you cannot proceed without them.
- **The walkthrough** (`app/content/tutorials/first-board.json`) — authored
  content laid over the working app. It explains; it never gates.

They must not overlap, and the ordering below is the whole reason the
walkthrough's trigger is what it is.

---

## Door 1 — getting in

**Standalone (download buyers, and this machine).** `run.bat` binds
127.0.0.1. No account, no login, no config file. The OS user account is the
boundary. The app opens straight into Step 1 below.

**Cloud studio (one tenant = one Railway service).** Everything sits behind
the workspace access token. The gate reads *"Screenboard access — paste the
access token from your order confirmation."* Two ways through it:

- **From the store**, the tenant link carries `/login#<token>`: the token
  never reaches a server or a log, the fragment is stripped immediately,
  and the customer sees a quiet *"Signing you in…"* rather than a form they
  did not ask for.
- **By hand**, pasting the token from the order confirmation.

A deep link that hits the gate carries its destination through `?next=`, so
signing in lands on the addressed page rather than dumping the user at `/`.

Governed by `docs/DEPLOYMENT.md` (provisioning) and `docs/SECURITY.md`
(the gate's guarantees).

## Step 1 — name the show

`GET /api/projects` returns `first_run: true` while no production exists.
The app then does something it does nowhere else: **it hides the pipeline
band** and renders one screen.

> FIRST RUN — NO PRODUCTIONS YET
> **Name the show you're working on.**
> *A production holds one screenplay and everything the art department
> builds from it. You can add more later and switch between them from the
> header.*
> [ name your production… ] · **Create production**
> ALREADY HAVE A BACKUP ZIP? · Restore a production

Two doors, and nothing else is reachable:

| Door | What happens |
|---|---|
| **Create production** | `POST /api/projects`, then the page reloads into the new production |
| **Restore a production** | `POST /api/projects/restore` → activate → reload. A restore **always creates a new production** and never overwrites one; API keys are not in backups |

**No walkthrough runs here, deliberately.** It used to — caught on
2026-08-17 by walking this flow — and the welcome modal covered the name
field and the Create button, while its next step would have pointed at a
band that is hidden on this screen. The trigger now waits for a production
to exist (`{"not": {"first_run": true}}`), and
`tests/test_tutorials.py::test_the_ftue_waits_for_a_production_to_exist`
keeps it that way. The rule generalises: **an empty install is already
onboarding, so the walkthrough waits its turn.**

## Step 2 — the studio opens, and the walkthrough starts

After the reload the band appears, every stage past 01 carries a `LOCKED`
chip, and the user lands on **Status**, which names one next action:
*Upload the screenplay*.

Now the walkthrough fires — its trigger is "a production exists **and** it
has no screenplay". Five steps:

| # | Surface | Says | Moves on when |
|---|---|---|---|
| 1 | Spotlight — Settings → `Connect OpenRouter` | What the studio does, and that none of it can start until a model is connected | **A model is connected** (`capability.any_credential`) — skipped entirely if one already is |
| 2 | Spotlight — the band | Five stages, strictly sequential; a locked stage tells you what is missing | Next |
| 3 | Spotlight — the DO-THIS-NEXT card | Upload the draft. The card stays **clickable through the cutout** | The user actually uploads (`POST /api/screenplay`) |
| 4 | Centred modal | What stages 02–05 do, and that Status always names the next action | Done |

**It starts on Settings by user ruling (2026-08-18), and the upload is
locked until a model is connected** — `POST /api/screenplay` returns 423,
and both upload forms disable themselves and say why. The read begins the
moment the draft lands and the read needs an engine, so taking the file
first would be accepting work the studio cannot start.

This reversed a ruling made hours earlier, which had *removed* the
credential step on the grounds that a tour should not teach what a blocker
already states. That was right while the upload worked without an engine.
It no longer does.

Esc ends it at any point; so do `×` and *Skip walkthrough*. Closing the tab
mid-way is not an exit — the step is recorded, and the next boot resumes
there. It runs **once per install**, not once per production.

## Step 3 — credentials

Settings → **AI & engines** has two lives, and which one a user sees is
decided by whether any credential exists:

- **No credential** — the page is a *setup form*: one recommended path
  (connect OpenRouter with one click, nothing to paste), a plain statement
  of what the models are for, and the chain it will walk you through. A
  dropdown is never an error message.
- **A credential exists** — the same page is a control panel.

The header's **engine dots** state the same fact from anywhere in the app:
filled green (key saved here), blue (environment variable), hollow (none).

## Step 4 — upload, and the pipeline takes over

The upload is the last thing the walkthrough asks for, and it is the root
dependency for everything: the app extracts the text once at import, maps
every slugline location, and unlocks stage 02. From here
`docs/INTENT.md` §"The pipeline — how a user moves through it" is the
guide.

---

## Branches

| Situation | What the user gets |
|---|---|
| Restored from a backup instead of creating | A production with content, so the walkthrough's trigger is already false — it does not run. Correct: they are not new to the product |
| Creates a **second** production later | The band and gates behave the same, but the walkthrough does **not** return — seen-state is per install |
| Returning mid-walkthrough | Resumes at the recorded step |
| Skipped or dismissed it | Never shown again. Settings → Tutorials → **Forget** re-arms it; a raised `rev` re-issues it to everyone |
| Arrived on a shared deep link | The gate carries `?next=`, so they land on the addressed page. If that production has no screenplay the walkthrough still fires there |
| A release ships an announcement | A one-step note pointing at what changed, once per revision |

## What a new user is never asked to do

Worth stating, because each was a decision: create an account (standalone
has none), edit a config file, choose a model before seeing anything, or
read documentation to get to their first screen.

## Known seams

Honest gaps in this flow, none of them regressions:

1. ~~A missing credential is not a blocker.~~ **Closed 2026-08-18** by
   user ruling. `blocking()` now emits a `KEY` row: *"No AI engine
   connected — the script read, the bible, breakdowns and every render
   need one"*, with **Connect** jumping to Settings → AI & engines. The
   two AI roles fail separately, so an install that can research but not
   render says exactly that, and a key that FAILED its own test reads
   differently from one that was never added — telling someone to connect
   an engine when they have a failing one sends them to the wrong fix.
   The row sorts after the screenplay (the upload is the root dependency
   and needs no engine) and before the board-layout gap (which only
   matters at assembly), so on a keyless install *"Upload the
   screenplay"* still leads, and the moment the draft is in, the
   credential becomes the next action.
2. ~~The walkthrough is the only thing that walks a user to Settings.~~
   **Closed 2026-08-18** — and closing it removed the walkthrough's own
   credential step, which existed only to do this job.
3. **The look of the walkthrough is not designed yet** — it is structure in
   existing tokens, awaiting a ruling (`TUTORIAL_DESIGN_BRIEF.md`).

## Editing any of this

The walkthrough is content: Settings → **Tutorials** (owner installs only).
Change the copy, reorder the steps, point one somewhere else, then commit —
every studio gets it on its next update. `docs/TUTORIALS.md` is the
reference. The app's own first-run screens are markup, and changing them
follows the normal UI rules in `app/static/DESIGN_SYSTEM.md`.
