---
name: deploy-watch
description: Verify what is actually running — the store's rev, every studio's rev, and whether a rollout finished or died. Use after any push, when asked "is this live?", "did it deploy?", "what version is on the fleet?", or before claiming anything shipped.
---

# deploy-watch — a push is not a deploy

The rule this exists for: **never say a change is live because you pushed
it.** Read the rev off the running service and quote it. Git succeeding
tells you GitHub accepted a commit; it says nothing about what any studio
is serving, and the gap is minutes long.

This skill only *observes*. `/iterate ship` owns the release chain and
`/fleet-push` owns the rollout mechanics.

---

## The two endpoints, and what each proves

| Surface | Endpoint | Gate |
|---|---|---|
| Store | `https://www.screenboardstudio.com/healthz` | open |
| Studio | `https://<sub>.screenboardstudio.com/api/healthz` | open — every other route is behind the workspace login |

```bash
curl -s https://www.screenboardstudio.com/healthz
# {"ok":true,"rev":"78edd84d2330","stripe":true,"mail":true,...}

curl -s https://beltminer-inc.screenboardstudio.com/api/healthz
# {"ok":true,"rev":"78edd84d2330","app_sha":"78edd84","version":"2026.08.05.86"}
```

`rev` is the 12-char commit. `app_sha` is what to compare against
`git rev-parse --short HEAD`. **These two move at different times** — the
store rebuilds first, then its boot triggers the fleet, so a window where
the store is new and studios are old is normal, not a fault. Say which you
measured.

The healthz booleans are the other half: `stripe`, `mail`, `google_auth`,
`session_secret`, `provisioning`, `export`. A `false` there is a missing
Railway variable, and it will not announce itself anywhere else.

---

## Know the target before you watch

The most common way to waste a watch is to poll for "changed" without
knowing what it should change *to*.

```bash
git rev-parse --short HEAD          # what you expect to see
git log --oneline origin/main..HEAD # anything unpushed makes the answer "not yet"
```

If commits are unpushed, stop — the answer to "is it live?" is no, and no
amount of polling changes that.

---

## Watching, without burning the turn

Use **Bash with `run_in_background`** and an `until` loop that exits when
the condition is true. One notification, no polling by hand, and the user
can talk to you while it runs.

```bash
until [ "$(curl -s --max-time 10 https://www.screenboardstudio.com/healthz \
          | grep -o '"rev":"[a-f0-9]*"')" != '"rev":"<OLD_REV>"' ]; do sleep 15; done
echo "STORE REV NOW: $(curl -s https://www.screenboardstudio.com/healthz)"
```

Same shape for a studio, comparing `"app_sha":"<old>"`.

- **Never `sleep` in the foreground** — it blocks the turn for nothing.
- **Never poll in a loop of tool calls.** One backgrounded watcher.
- Compare against the OLD value and exit on *change*, not on a hoped-for
  new value — that way a rollback or an unexpected rev still wakes you.

---

## The fleet, not one studio

`scripts/watch_tenants.py` already does the whole fleet properly:
discovers ACTIVE studios, polls Railway build status **and** each
`/api/healthz`, and exits when all serve the target.

```bash
python scripts/watch_tenants.py            # target = current git HEAD
python scripts/watch_tenants.py <commit>   # explicit target
python scripts/watch_tenants.py --once     # one pass, print, exit
```

**Exit codes carry the outcome:** `0` all live · `2` a build FAILED or
CRASHED · `1` timeout. Check it — a script that ends is not a rollout that
worked.

It reads the admin token from `$ADMIN_EXPORT_TOKEN` or
`~/.screenboard_admin_token` and never prints it. Do not pass a token on a
command line.

Read-only fleet state without waiting:

```bash
scripts/update_tenants.sh --status   # per-studio deployments, triggers nothing
```

---

## Silence is not success

If you are watching for an outcome, the watch must be able to tell you
about a *bad* one. A loop that only exits on the rev you want will sit
quietly through a crashloop and look identical to "still building."

- Prefer `watch_tenants.py`, which already exits non-zero on a dead build.
- If you hand-roll, bound it — a timeout that reports "still not live after
  N minutes" is a result. Nothing is not.
- When a build fails, say so and stop. Do not re-push hoping.

---

## Reporting

Quote the rev. Name which surface. State the ones you did **not** check.

> Store is live at `78edd84`; `beltminer-inc` reconciled to `78edd84`.
> I did not check the other studios.

Never "should be live", "the deploy went out", or "that's deployed now"
without a rev behind it. If you have not measured it, the honest sentence
is *"pushed; I haven't verified the fleet yet"*.

**A 200 is not a version check.** The page that answers may be a
coming-soon gate, a cached build, or the previous image still draining —
all of which return 200 happily.

---

## Traps that have actually bitten

- **`www.screenboardstudio.com/` serves a coming-soon gate**, not the
  store, for anyone without the `sb_preview` cookie. You cannot verify
  rendered store markup from here; verify the *rev* and say that is what
  you verified.
- Studio routes other than `/api/healthz` return **401 workspace login
  required**. That is the auth wall working, not a broken deploy.
- The store and the fleet reconcile on **different clocks**. Check both
  before saying "deployed".
