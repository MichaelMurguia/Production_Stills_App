---
name: fleet-push
description: Roll the current build out to every cloud studio — the order the release chain must run in, why the push is usually the whole rollout, and the manual fallback when a studio misses it. Use for "push to the tenants", "update the fleet", "get this out to the studios", or a studio stuck on an old build.
---

# fleet-push — the push IS the rollout

**Read `.claude/iteration.json` first.** In local mode nothing ships until
the user says so, and that has no exceptions — not a security fix, not a
live-tenant fix. `/iterate` owns that decision; this skill owns the
mechanics once it is made.

---

## The thing most people get wrong

Since the 2026-08-12 ruling, **you almost never trigger a fleet update by
hand.** Pushing to `main` does the whole thing:

```
git push origin main
   └─ Railway rebuilds the storefront
        └─ storefront boots
             └─ _fleet_update_on_start → auto_update_tenants()
                  └─ every ACTIVE studio rebuilds from the new commit
```

That chain is in code, not folklore — `storefront/app/main.py`
`_fleet_update_on_start`: *"Updates follow the push: this deploy IS the
release event."* A second `_reconcile_on_start` converges workspaces
against the purchases table.

So the default rollout is: **push, then watch.** Running
`update_tenants.sh` reflexively afterwards is noise, and it triggers a
second rebuild of studios that are already building the right commit.

---

## The chain, in the one order that works

1. **Both suites green.** Red stops the ship — say so, do not push.
   ```bash
   python -m unittest discover -s tests
   cd storefront && python -m unittest discover -s tests
   ```
2. **Bump `VERSION`** once (`2026.08.05.<n+1>`).
3. **Commit the bump.** This commit is the release note — list what is in it.
4. **`python scripts/stage_release.py`** — *after* the commit, never before.
   It runs `git archive HEAD`, so staging first ships the previous build.
   **This has been got wrong twice.**
5. **Commit the zips.**
6. **`git push origin main`.**
7. **Watch** — `/deploy-watch`. A push is not a deploy.
8. Clear `pending` in `.claude/iteration.json`; leave `mode` alone.

Skipping 2–5 is fine for an app-only change that is not a release: the
fleet still updates, because step 6 is what triggers it. What you must not
skip is 7.

---

## When a studio misses it

Symptoms: `/api/healthz` on one studio still shows the old `app_sha` long
after the store moved, or `watch_tenants.py` exits `2`.

```bash
scripts/update_tenants.sh --status   # read-only; what each studio last did
scripts/update_tenants.sh            # trigger a rebuild of every ACTIVE studio
```

`update_tenants()` records per-service failures rather than raising — one
studio failing does not stop the others, and a missed studio catches up on
the next run. So a partial failure is *quiet by design*: check the
returned `failed` list, do not assume an empty-looking success.

Then watch again. If the same studio fails twice, stop and report it with
the error rather than looping — the fault is in that service, and another
trigger will not fix it.

---

## The admin token

`update_tenants.sh` and `watch_tenants.py` both read it from, in order:

1. `$ADMIN_EXPORT_TOKEN`
2. `~/.screenboard_admin_token` (outside the repo, `chmod 600`)

**Never put the token on a command line** — it lands in shell history and
in this transcript. Never print it, never echo it into a file inside the
repo, never pass it as `?token=` (query strings land in access logs; the
scripts use `Authorization: Bearer` for exactly this reason). If it is
missing, say so and stop; do not ask the user to paste it into the chat.

---

## What ships, and what must never

The customer artifact is built by `stage_release.py`:

```
git archive HEAD -- app requirements.txt run.bat README.md INSTALL.md VERSION
```

From **HEAD**, not the worktree — so an untracked file cannot ride it by
construction. That is the guarantee; do not replace it with a directory
walk. `scripts/export_package.py` is a developer convenience only, and it
packages `git ls-files` output for the same reason (audited 2026-08-23,
when it still walked the worktree and would have zipped live API keys).

Nothing from `data/`, `projects/`, `project_state/`, or `settings.json`
ever enters a release or a deploy image. Secrets live in Railway variables
and local shells.

---

## Report like it matters

State the rev, per surface, and name what you did not check.

> Store `78edd84`; `beltminer-inc` reconciled to `78edd84`. Other studios
> not checked.

If a studio is stuck, say which and what its healthz shows. "The fleet is
updated" without revs is the sentence this skill exists to prevent.
