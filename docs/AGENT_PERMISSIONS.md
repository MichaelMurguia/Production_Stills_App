# Agent permissions — how this machine runs Claude Code without prompts

Hand this to any agent (or human) setting up a new VS Code / Claude Code
session that should behave like this one: **no permission modals, ever.**

Audited 2026-08-16 from a live session in `c:\dev\Beltminer\Production_Stills_App`.

---

## 1. What is actually configured

Two files, two layers. **The user-level file is the one that makes this
apply everywhere**; the project file only covers one repo.

### Layer 1 — user level (applies to every project on this machine)

`C:\Users\<you>\.claude\settings.json`

| Key | Value here | What it does |
|---|---|---|
| `permissions.defaultMode` | `"bypassPermissions"` | **The load-bearing line.** Tools run without asking. |
| `skipDangerousModePermissionPrompt` | `true` | Removes the startup "are you sure?" confirmation for that mode. |
| `skipAutoPermissionPrompt` | `true` | Removes the other startup permission prompt. |
| `permissions.additionalDirectories` | 15 paths | Roots outside the project the agent may touch. |
| `permissions.allow` | 196 entries | **Vestigial — see §3.** |
| `permissions.deny` | *absent* | No blocklist. |
| `permissions.ask` | *absent* | Nothing forced to prompt. |

### Layer 2 — project level (this repo only)

`.claude/settings.local.json` — **gitignored**, never committed, never in a
release zip.

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": [ … 91 entries … ]
  }
}
```

Redundant with layer 1 on this machine, but it keeps the repo
self-describing if it's cloned onto a box where the user file is absent.

---

## 2. The minimum you need to copy

Ignore the hundreds of accumulated `allow` rules. This is the whole thing:

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "additionalDirectories": [
      "c:\\path\\to\\another\\repo",
      "c:\\tmp"
    ]
  },
  "skipDangerousModePermissionPrompt": true,
  "skipAutoPermissionPrompt": true
}
```

Put it in `~/.claude/settings.json` for machine-wide, or
`<project>/.claude/settings.local.json` for one repo (and **gitignore that
file** — it is a local trust decision, not a project fact).

Note the doubled backslashes: it's JSON, so Windows paths need escaping.

`defaultMode` is the only key that must be right. If a future version
renames the two `skip*` keys you'll get two startup confirmations and
nothing else; the session still runs unprompted afterwards.

---

## 3. Why the `allow` lists are noise

287 `allow` entries across both files, and **not one of them matters while
`defaultMode` is `bypassPermissions`** — bypass already covers everything
they list. They're sediment from before the mode was set, one entry per
approval, including things like:

```
Bash(curl -sL --max-time 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) …" …)
```

— a fully-quoted one-off command that will never match again.

**Do not copy them.** They make the file unreadable and imply a
least-privilege posture that isn't in force. If you ever step *down* from
bypass to `acceptEdits` or `default`, write a fresh, deliberate allowlist
instead of inheriting this pile.

---

## 4. What this actually permitted in one working session

Everything below ran with **zero prompts** during the audited session:

- **Shell** — `Bash` and `PowerShell`, including `git push` to `origin main`,
  `Stop-Process -Force` on servers found by port, launching headless Edge,
  and driving a browser over a CDP WebSocket.
- **Files** — `Write`, `Edit`, `Read`, `Glob`, `Grep` anywhere in the project.
- **Outside the project** — the session scratchpad under
  `%LOCALAPPDATA%\Temp\claude\…`, and `/tmp`.
- **Network out** — `curl` to a live production tenant, health polling.
- **Production deploys** — a push triggers a Railway build; the agent pushed
  ~10 releases and verified each one at `/api/healthz`.

That last one is the honest headline: **this configuration lets an agent
ship to production without asking.**

---

## 5. What bypass does *not* cover

Copying these settings will not remove every interruption.

- **OAuth-gated MCP servers.** In this session `claude.ai Gmail`, `Google
  Calendar` and `Slack` were unusable, with: *"This session is
  non-interactive, so Claude cannot run the OAuth flow here."* Permission
  mode is irrelevant — a human must authorise those in claude.ai connector
  settings or an interactive `/mcp` session.
- **Directory scope.** `additionalDirectories` is a separate mechanism from
  prompting. List every root you want reachable; don't assume bypass mode
  reaches outside the project.
- **Hooks.** If a repo defines hooks, they still intercept tool calls and
  their output still comes back as feedback.
- **Writes to `.claude/` itself.** Creating or editing files under the
  project's `.claude/` directory — skills, hooks, settings — prompted for
  approval in the audited session **despite `bypassPermissions` being set
  at both levels**. That is the harness protecting agent configuration
  from agent self-modification, and it is the right call: a skill file
  changes how the agent behaves on every future turn, so "the agent may
  freely edit its own instructions" is a materially different grant from
  "the agent may freely edit the project". Expect a prompt when an agent
  adds a skill or a hook, and read it rather than clicking through — it
  is one of the few prompts left, and it is the one worth reading.
- **Interactive commands.** `git rebase -i`, `Read-Host`, `Get-Credential`
  and friends hang or fail regardless of permissions. Unrelated to this
  config; just don't run them.

---

## 6. The half that isn't configuration

**Settings stop the modals. They do not stop an agent asking in prose.**
An agent with bypass on will still write "shall I proceed?" unless told
not to. On this machine that's handled in the project's `CLAUDE.md`:

> This project runs with permission prompts bypassed
> (`.claude/settings.local.json` → `"defaultMode": "bypassPermissions"`,
> gitignored — never ship it in the repo or a release zip). The user has
> stated they never read confirmation modals; the prompts were pure
> friction. **Do not re-create that friction in text — act, don't ask.**
> What remains is judgment, not ceremony: for truly irreversible or
> outward-facing actions (deleting user data, force-pushes, publishing,
> spending real money), state what you're doing in one line as you do it,
> and stop only when the evidence genuinely contradicts the request.

Copy that paragraph into the new project's `CLAUDE.md` (or `AGENTS.md`)
alongside the JSON. Without it you get an agent that has permission to act
and asks anyway — the worst of both.

Note what it preserves: irreversible and outward-facing acts still get a
**stated line**, not a prompt. That's the intended shape — narrate, don't
block.

---

## 7. What you are accepting

Stated plainly, because the config is easy to copy and the consequences
are not obvious:

- An agent can **delete or overwrite any file** in the project or any
  listed directory, without asking.
- An agent can **push to your default branch** and trigger a deploy.
- An agent can **run any shell command** your user account can run,
  including ones that reach the network or terminate processes.
- A prompt-injected instruction — from a fetched web page, an untrusted
  file, a third-party MCP result — reaches the same unguarded tools.

This is a reasonable trade for a solo developer on their own repo, working
alongside the agent and reading its output. It is **not** appropriate for
a shared machine, a repo with production credentials on disk, an unattended
or scheduled run, or any session that reads untrusted content.

Mitigations that survive bypass mode, in rough order of value:

1. **Git is the undo.** Commit often; that's what makes destructive edits
   recoverable. Almost everything in the audited session was recoverable
   because each step was a commit.
2. **Keep secrets out of the working tree.** On this machine they live in
   Railway variables and local shells, never the repo.
3. **Use `permissions.deny`** for the few things you never want, even here
   — e.g. `Bash(git push --force*)`, `Bash(rm -rf /*)`. Deny beats bypass.
   Neither file currently sets one; adding a short deny list is the single
   cheapest hardening step available.
4. **Don't add `additionalDirectories` you don't need.** Each one widens
   the blast radius permanently.

---

## 8. Verifying a new session

1. `/status` (or `/config`) → permission mode reads **bypassPermissions**.
2. No startup confirmation appeared.
3. Ask the agent to run something trivial but real — `git status`, or write
   and delete a scratch file. It should just do it.
4. Ask it to touch a path in `additionalDirectories`. If that refuses, the
   directory list is wrong — not the mode.

If prompts still appear, check in this order: the project
`.claude/settings.local.json` (a `defaultMode` there overrides nothing but
can confuse), then `~/.claude/settings.json`, then whether the client was
launched with a CLI flag that pins a different mode.

---

## 9. Files, for reference

| Path | Committed? | Purpose |
|---|---|---|
| `~/.claude/settings.json` | no (outside repo) | machine-wide mode, extra dirs |
| `<project>/.claude/settings.local.json` | **no — gitignored** | per-repo mode |
| `<project>/.claude/settings.json` | yes, if present | shared project settings; **not used for bypass here** |
| `<project>/CLAUDE.md` | yes | the behavioural half (§6) |

Release zips on this project ship `app/`, `requirements.txt`, `run.bat`,
`README.md`, `INSTALL.md`, `VERSION` — `.claude/` and `docs/` never leave
the repo, so neither this file nor the settings reach a customer.
