---
name: iterate
description: Switch between LOCAL iteration (fast, nothing deploys) and ONLINE (every change ships), batch pending work, and run the release chain once when told. Use for /iterate local, /iterate ship, /iterate status, /iterate online.
---

# iterate — two speeds, and one place that remembers which

Before 2026-08-16 every change — including a two-word label fix — cost a
VERSION bump, a commit, a zip, a push and a three-minute fleet deploy
before anyone could look at it. The user asked for a local loop, then for
this: *"understand the diff mode between local and online iteration —
also collect changes and push when stated if we are in local mode."*

**The mode is state on disk, not something you remember.** Context gets
compacted; `.claude/iteration.json` does not. Read it at the start of any
turn that changes code.

---

## The state file

`.claude/iteration.json` — **gitignored**, per-machine, never shipped.

```json
{
  "mode": "local",
  "since": "2026-08-16T14:02:11Z",
  "pending": [
    "Cinematography switch copy rewritten — it did not explain itself",
    "Logline promoted to 16.5px"
  ]
}
```

Absent file ⇒ **online**. That is the safe default: a fresh clone, a cron
run, or another agent behaves exactly as before this skill existed.

---

## `/iterate local`

1. Write `{"mode": "local", "since": <now>, "pending": []}`.
2. If nothing is listening on 8080, tell the user to run `.\dev.bat`
   (PowerShell needs the `.\`). **Do not start it yourself** — it is a
   foreground server they will want to Ctrl-C, and a backgrounded one they
   cannot see is how a stale build gets verified.
3. Say what changed about your behaviour, in one line.

### What LOCAL mode changes

| | LOCAL | ONLINE |
|---|---|---|
| VERSION bump | **no** | yes, every change |
| `stage_release.py` | **no** | yes |
| `git commit` | **yes** — git is the undo | yes |
| `git push` | **no** | yes |
| fleet poll + "live on the fleet" | **no** | yes |
| verify by | the user's local loop | headless capture / CDP |
| tests | **yes, always** | yes, always |
| design-system rows | **yes, always** | yes, always |

Two of those never bend. **Tests stay green every commit** and **every
UI-touching change still logs its row** — batching is about deploys, not
about lowering the bar. A local commit that breaks the suite is worse
than a slow deploy, because it is discovered later.

### Working in LOCAL mode

- Make the change. Run the suite. Commit. **Append one line to
  `pending`.** Do not push.
- Tell the user what to look at and that it is local — *"hard-refresh and
  look at X"* — never *"live on the fleet"*, which would be a lie.
- If they ask "is this live?", the honest answer is **no**, with the
  pending count.

---

## `/iterate ship`

The release chain, once, for everything accumulated.

1. **Both suites green** — `python -m unittest discover -s tests` and
   `cd storefront && python -m unittest discover -s tests`. A red suite
   stops the ship; say so and do not push.
2. **Bump VERSION** once (`2026.08.05.<n+1>`).
3. **Commit the bump** with a message that lists the pending items — this
   is the release note, and it is the only commit the fleet's history
   shows as a version.
4. **`python scripts/stage_release.py`** — AFTER the commit. The zip
   archives HEAD; running it first ships stale content. This has been got
   wrong twice.
5. **Commit the zips**, then `git push origin main`.
6. **Watch the rollout** — `/deploy-watch`. Poll `/api/healthz` until the
   rev matches and report it. A push is not a deploy. The mechanics of
   steps 4–6, and what to do when a studio misses the update, live in
   `/fleet-push`; do not re-derive them here.
7. Clear `pending`, keep `mode` as it was.

Local commits made without a VERSION bump are fine: CI checks the pushed
HEAD, and HEAD carries the bump and a zip that matches it.

---

## `/iterate online`

Delete the state file (or set `mode: "online"`). From then on every change
ships on its own, exactly as before. Use it when the work is
infrastructure, a migration, or anything the user must see running on the
real tenant rather than a copy.

## `/iterate status`

Read the file and say: the mode, how long it has been set, the pending
list, whether 8080 is listening, and — if online — the deployed version
from `/api/healthz`. Do not change anything.

---

## Nothing ships on your own judgement

**In local mode you never push. Not for any reason.** (Ruled 2026-08-16,
replacing a list of exceptions.)

That list used to say a live-tenant fix, a migration, a `storefront/`
change or a security fix "must ship even in local mode." It got
stretched the same day it was written: a defect the user hit online was
shipped — defensible — and then a *feature* rode out in the same commit
under the same justification, which was not. The user's answer was
*"we work local until I say push."*

The failure mode is not laziness, it is that "this one is urgent" always
sounds true from the inside. So the rule no longer asks you to judge it.

Some changes genuinely cannot be proven on a local copy:

- a fix to something the user reported **on the live tenant**
- a boot migration (it only runs on a real boot, on real data)
- anything touching `storefront/`, deploys, or billing
- a data-loss or security fix

Those get **built, tested, committed, and named as unproven** — put them
at the TOP of `pending` prefixed `UNPROVEN LOCALLY —` with one line on
what a deploy would settle. Say it plainly in the reply too. Then stop.
If you think it needs pushing now, say why and wait for an answer;
asking costs one message, and a push the user did not want costs their
tenant.

**When the user says "push it" / "ship it" / "deploy"** in any words, that
is `/iterate ship` — do not wait for the exact command.

**Never let `pending` become the changelog.** It is a queue of what has
not shipped, cleared on every ship. The durable record is the commits and
`DESIGN_SYSTEM.md`.
