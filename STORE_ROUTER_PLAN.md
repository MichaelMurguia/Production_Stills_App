# STORE_ROUTER_PLAN.md — the three open store items

**For the coding agent.** Closes the three entries logged "Awaiting design
review" in `STORE_DESIGN_SYSTEM.md`'s changelog. Mocks:
`design_mocks/11a-no-studio.png`, `11b-studio-no-answer.png`,
`11c-workspace-door.png`. Read `STORE_DESIGN_SYSTEM.md` first. One task per
commit, T1→T4.

---

## The governing idea

The router's two failure pages were built identically. **They serve opposite
audiences and must not look alike.**

- **Unclaimed address** — a stranger, a typo, or someone guessing a name.
  This is the only failure page that should *sell*. Full store chrome.
- **Studio not answering** — a paying customer locked out mid-session. This
  is a trust moment, and selling to someone in it is a mistake. No nav, no
  pricing, nothing to buy.

## T1 — Unclaimed address (mock 11a)

Promote out of `tenant_proxy.py` inline HTML into a real template rendered
with the store's `base.html` chrome (header with The pipeline / Pricing /
Sign in, and the standard footer).

- Kicker `NO STUDIO AT THIS ADDRESS` (keep the changelog's string).
- **The address itself is the H1**, in Courier, `word-break: break-all`.
  It is the most useful thing on the page — the reader is checking their
  own typing.
- One paragraph explaining what a Screenboard studio is.
- Amber fill `Claim this name` (prefill the attempted subdomain into the
  claim flow if that is cheap; if not, link `/` and note it) plus ghost
  `See what Screenboard does` → `/pipeline`.
- Below a rule: `LOOKING FOR A STUDIO YOU WERE INVITED TO?` with the line
  about checking spelling. **Keep this** — an unclaimed name and a mistyped
  one are indistinguishable from the visitor's side, and the page must name
  both possibilities or half its readers leave confused.
- Status code 404.

## T2 — Studio not answering (mock 11b)

Also a real template, but a deliberately stripped one: **wordmark only in
the header**, no nav links, no footer links, no pricing anywhere.

- Kicker `YOUR STUDIO DID NOT ANSWER` in `--hold` (keep the string; the
  changelog's second sentence becomes the H1).
- H1 names the studio: "The Beltminers is redeploying."
- **Lead with reassurance about the work**, not with the error. The first
  paragraph says storage stays put while the studio restarts and nothing
  approved is at risk — that is the actual question in the reader's head.
- A Courier status block, `--hold` left border: `ADDRESS`, `LAST ANSWERED`,
  `TYPICAL RETURN`, and `YOUR WORK — SAFE, STORED SEPARATELY` in `--ok`.
  **NEEDS DATA:** `LAST ANSWERED` needs a last-good-proxy timestamp. If the
  proxy doesn't track one, drop that row rather than guessing — the other
  three carry the page.
- Amber `Try again` plus a stated Courier line
  `RECHECKING AUTOMATICALLY EVERY 15 SECONDS`, and implement the recheck
  (a `setTimeout` reload, same shape as `success.html`'s poller). A page
  that says it rechecks must recheck.
- Support block: mail address, and tell them to include the studio address
  because that is what identifies the tenant.
- Status code 503, and `Retry-After: 15`.

## T3 — The workspace door (mock 11c)

The mechanic is already correct — this only promotes the footnote into a
stated condition, per §5 (*gates are stated, never errored*). A 10px mono
whisper under a CTA is not stating.

**Scope, exactly: the cloud-`ACTIVE` state, in three places** —
`success.html`'s `purchase.workspace.status == "ACTIVE"` branch, and both
cloud-`ACTIVE` blocks in `account.html` (the signed-in purchase list and the
token-purchase view). All three already emit the identical
`hero-sub mono` line, so factor it into one partial and change it once.

In each, when `door != workspace.url`, render **above** the button:

```
[ PROVISIONING ]  THE-BELTMINERS.SCREENBOARDSTUDIO.COM IS PROVISIONING —
                  THIS BUTTON USES THE RELIABLE ADDRESS MEANWHILE.
```

— bordered `--hold` chip, Courier text, on `--field` with a 2px `--hold`
left border. Copy is unchanged from what ships today. When the branded name
serves, no block; the `YOUR STUDIO` box gains a bordered `--ok` `LIVE`
chip beside its label.

**Do not touch any other state.** Payment pending, download license,
*Building your studio.* (no door exists yet — only the polling line),
subscription ended and the signed-out token paste keep their current
treatment. Headings in the mock are the templates' own; do not replace page
copy with mock copy anywhere in this task.

## T4 — Provenance: name the work, don't count it

`STORE_DESIGN_SYSTEM.md` §6 says keep the numbers true, and you correctly
replaced the mock's placeholders with the production record. The ruling now
goes one step further, because *true* and *persuasive* diverged: "41
approved panels" was doing sales work and the honest figure is 7.

**Amend §6** to: *a provenance line names the work being shown. It may
carry a count only when the count is impressive on its own terms; a small
true number invites the wrong comparison and undersells a young product.
Never inflate — reword.*

Apply:
- Homepage hero: `SHOWN — THE BELTMINERS · EXT. CHARLIE'S CABIN · KYRA
  COSTUME AND ACTION STUDY`
- `/pipeline` hero figures: `124-PAGE DRAFT, READ IN FULL` ·
  `6 DESIGN LANGUAGES` · `4 ENVIRONMENTS` · `EVERY IMAGE BELOW IS FROM IT`
  (the last in `--ink-dim`). Drop the panel and board tallies.
- Leave the homepage figure band alone — `3840×2160`, `100%`, `0`, `5` are
  rules and guarantees, not tallies of output.

## Ground rules

Tokens only; square corners; Archivo for hierarchy, Courier for machine
data. Amber per §8 — one fill on 11a, one on 11b, one per state card on
11c. Both router pages must render with zero JS for their content (the
recheck timer is progressive enhancement). Add `/pipeline` and both router
responses to the CI route check. Update the `STORE_DESIGN_SYSTEM.md`
changelog and clear the three "Awaiting design review" entries; delete this
file when done.
