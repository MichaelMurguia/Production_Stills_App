# What a cloud studio actually costs — findings, 2026-09-19

**Status: findings, no decision taken. Nothing here has been built.**

The user asked whether one Railway service per customer is worth keeping:
*"It's not very scalable, but I like the custom domain name. What are my
options?"* This records what the measurements said, because they reversed
the intuition twice and the wrong number was already written down in
`docs/DEPLOYMENT.md`.

---

## The conclusion, first

**One service per customer is not the scaling problem.** Compute is about
**$0.60/month per studio and it does not grow with use.** That buys an
OS-enforced boundary around unreleased screenplays, which is the right
trade at that price.

**The cost is image bytes on a Railway volume, and it only ever goes up.**
A Cloud Personal subscriber at $9.99/mo crosses into negative margin
somewhere around **55–60 GB** of accumulated work — not from a spike, from
ordinary continued use. Nothing in the product removes a byte, and Railway
volumes cannot be shrunk.

So the re-architecture that was on the table — pooling customers into
shared processes — **addresses the cheap half.** Pooled or isolated, the
gigabytes cost the same.

---

## And the custom domain was never at risk

Worth stating because it framed the original question. Since the wildcard
router (`storefront/app/tenant_proxy.py`), `<studio>.screenboardstudio.com`
is served by the **storefront**, which reverse-proxies to whatever is
behind it. One DNS record, one certificate, forever; a rename is a row
commit. The branded address survives every option below, including the
ones that delete per-customer servers entirely. It is a routing-layer
feature and it is not coupled to the hosting model.

---

## What was measured, and how

### 1. What an idle tenant weighs

Booted exactly as a tenant boots — `SCREENBOARD_HOME` pointed at an empty
temp directory, `SCREENBOARD_NO_KEYS=1`, `uvicorn app.main:app` — then
sampled RSS and CPU with `psutil`, including children, after serving the
SPA and settling.

```
cold boot to first healthz     2.5 s
RSS idle (settled)              60 MB
CPU idle                      0.01 %  of one vCPU
peak, 12-panel 4K composite    116 MB  (0.2 s)
after release                   58 MB  <- returns; no memory ratchet
```

Generation is **network wait**, not local compute — the model call costs a
socket. The board composite is the only real CPU and it is fifths of a
second. **RAM is flat whether the studio is worked in or not**, which is
why the idle figure is also the working figure to within pennies.

### 2. What a real production weighs

Measured against `projects/the-beltminers/` — the ANCESTOR proof-test,
mid-flight, three boards:

```
266 MB total
├── boards       159 MB   (3 boards, 100 files)
├── references   107 MB   (656 files — 97 originals + 11 thumbs)
└── everything else < 7 MB   ← bible, sheets, subjects, analysis,
                                screenplay, specs, activity log
```

**97% of a production is images. The entire state of the app is under half
a megabyte.** That ratio is the whole finding.

Inside the boards:

| | files | MB | share |
|---|---|---|---|
| CANDIDATE (a take) | 96 | 148.5 | **93%** |
| BOARD (the composite) | 4 | 10.7 | 7% |

**93% of board storage is takes that were not used.** One board,
`KYRA_CHARACTER_V001`, is 110 MB by itself.

### 3. Railway's published rates (fetched 2026-09-16)

| | |
|---|---|
| Memory | $10 per GB / month |
| CPU | $20 per vCPU / month |
| Volume | $0.15 per GB / month — **billed on USED bytes, not provisioned** |
| Egress | $0.05 per GB |
| Pro plan | $20/month per workspace, **including $20 of usage credits** |

All billed per second of actual usage. Volumes can be expanded on paid
plans and **cannot be reduced**.

---

## The margin curve

Volume is the only line that moves. RAM holds at ~$0.60; CPU stays in
pennies.

| customer | GB | Railway/mo | net of $9.99 | gross |
|---|---|---|---|---|
| just signed up | 1 | $0.75 | $8.65 | 87% |
| one production going | 5 | $1.35 | $8.05 | 81% |
| one feature finished | 15 | $2.85 | $6.55 | 66% |
| two features | 35 | $5.85 | $3.55 | 36% |
| working pro, 3 years in | 60 | $9.60 | −$0.20 | **negative** |

(Net is after Stripe's 2.9% + $0.30 = $0.59 on $9.99.)

**Measured:** the $0.60 compute, the 266 MB production, the 93% candidate
share, the rates.
**Extrapolated — the weak joint:** everything past 5 GB. Scaling three
boards to a finished feature assumes 50–100 scenes at the observed
~50 MB/board. **This is arithmetic, not a measurement**, and it is the
first thing to settle on follow-up.

The shape holds regardless of where exactly the curve sits: it slopes one
way, it is driven by retained data, and **the best customers become the
least profitable ones monotonically.**

---

## What this reverses

- **`$2–5/mo per tenant`**, written in `docs/DEPLOYMENT.md` on 2026-07-31
  and repeated in analysis since, was an estimate, never a measurement. It
  is 3–8× too high for compute and open-ended too low for storage — wrong
  in both directions at once, which is why it produced the wrong strategy.
  Corrected in that file, pointing here.
- **Scale-to-zero / sleeping the tenants** was recommended and is now
  withdrawn. It saves at most ~$0.60/studio/month and puts wake-up logic
  in the request path of every customer. At 100 studios that is $60/month
  for a permanent latency tax. Not worth it.
- **Moving to a cheaper compute substrate** (Fly Machines et al) —
  withdrawn for the same reason. It optimises a line item that is already
  near zero.
- **Pooling customers into shared processes** — not recommended, and now
  for a second and better reason than the first. The original objection
  stands (`app/paths.py` is process-global; ~21,000 lines across 30
  modules read `paths.DATA` at call time, so two customers cannot share a
  process without a large refactor whose failure mode is one customer
  seeing another's screenplay). The new objection is simpler: **it would
  not save money.**

---

## The two levers, in order

### 1. Get the blobs off the volume

Object storage — Cloudflare R2 is ~$0.015/GB-month, **10× cheaper, with
zero egress fees.** The 60 GB customer goes from $9.60/month to $0.90.

It also closes three other things at once:

- **`Tenant volume backups — Not built`** (listed in `DEPLOYMENT.md` under
  deliberate scope cuts). Losing a customer's screenplay and boards is a
  worse outcome than any amount of overpaying. Object storage is backed up
  and versioned by default.
- **The double egress.** `tenant_proxy.py` forwards to the tenant's
  **public** `*.up.railway.app` host (the tenants project is deliberately
  separate from the storefront's, so Railway's private network is not
  available across them). Every byte a customer downloads therefore
  appears to cross billable egress twice: tenant → edge → storefront →
  edge → customer. **Unverified** — check the egress line on the Usage
  page before treating it as real. R2's zero-egress makes it moot.
- **Tenant portability.** With the volume reduced to the half-megabyte of
  JSON that is the actual studio, a tenant becomes near-stateless, and
  every operation that is currently awkward — rebuild, migrate, change
  host, restore — becomes easy.

### 2. Decide what a take is worth once its board locks

93% of board bytes are rejected candidates at 2–7 MB each. If a take
downsamples to a preview after its board locks, board storage drops ~90%.

This is a **product decision, not infrastructure**, and it runs against
the app's posture of stating things rather than silently removing them —
so it has to be visible, probably opt-out, and it needs the user's ruling
before anything is built.

Together, the 60 GB customer costs roughly **$0.15/month** instead of
$9.60.

---

## Open questions for the follow-up

1. **How many boards does a finished feature have in this workflow?** The
   single input that turns the extrapolated half of the curve into a real
   break-even.
2. **The per-service Usage breakdown.** Billing History is a total only;
   Railway → workspace → **Usage**, filtered to the tenants project, gives
   RAM/CPU/volume/egress per service. Needed to confirm the curve against
   reality and to check the double-egress claim.
3. **Retention.** Does a rejected take survive its board's lock, and for
   how long? User's call.
4. **`SCOPES_PLAN.md`'s open question** — *does a second studio mean a
   second Railway service or a second folder inside one install?* Under
   these numbers it is no longer a cost question, only an operational one.
   Folder-per-studio still reduces service count for multi-studio orgs
   without any multi-tenancy risk, and it extends the mechanism
   `paths.set_project()` already implements.

## What the numbers do NOT cover

**The operational ceiling, which money was never the measure of.** Every
push is N builds (the storefront's boot fans out `auto_update_tenants()`),
N log streams to search when a customer says it is slow, and N volumes
with no backup. That arrives on subscriber count regardless of what
compute costs, and on these figures it is now the *only* argument left
against one-service-per-customer.

## Reproducing this

- Idle weight: boot `uvicorn app.main:app` with `SCREENBOARD_HOME` on an
  empty temp dir and `SCREENBOARD_NO_KEYS=1`; sample `psutil` RSS across
  the process tree after serving `/`, `/api/state`, `/static/app.js`.
- Production footprint: `du -sh projects/*/data/*`, then group
  `projects/<slug>/data/boards` by `CAND-` vs `BOARD-` filename prefix.
- Rates: railway.com/pricing and docs.railway.com/reference/volumes.

**No Railway credentials exist on the development machine** — no CLI, no
token, no config — so none of the above touched the live account. Every
figure is either local measurement or published rate.
