# Pooled re-architecture — summary and trigger

*Written 2026-08-08, after the beltminer-inc disk incident prompted an
architecture review. This is the parked plan; nothing here is scheduled.*

## Where we are

Every cloud customer gets a full private instance: one Railway service, one
volume at `/workspace` (`SCREENBOARD_HOME`), one shared access token. The
storefront is the control plane (Postgres, Stripe, provisioner). This is the
**silo** pattern, and it was not chosen — it fell out of the app: `app/` has no
database (JSON records, PNG takes on disk) and uses process-global path state
(`paths.set_project()` mutates module globals under a lock). One process
cannot safely serve two customers.

## What typical looks like

The industry default for a SaaS at this price point is **pooled**: one
autoscaled deployment; Postgres with `tenant_id` on every row (plus RLS);
binaries in object storage (S3/R2) under tenant prefixes with signed URLs;
real user accounts (org → workspace); long renders in a queue with workers;
one deploy and one migration per release; near-zero marginal cost per
customer.

## What silo buys us (real, not rationalized)

- **Blast radius** — the full disk took out exactly one studio.
- **Isolation as a sales asset** — unreleased screenplays are the customer's
  most sensitive IP; "your script sits on your own disk in your own
  container" is a differentiator at any tier.
- **No `tenant_id` retrofit** into a codebase with no concept of a tenant.
- **Restore is a volume copy**, not surgery on shared tables.

## What it costs

- **Margin floor** ~$2–5/mo per idle customer, linear.
- **Ops scale linearly** — the disk incident is the archetype; fleet storage
  and the capability probes exist because of it.
- **Releases are N serial deploys**, non-atomic (fine at 2, a problem at 200).
- **No tenant backups yet** (Railway `volumeInstanceBackupScheduleUpdate`
  exists and can close this without re-architecting).
- **Provisioning is a failure surface at signup.**
- **Railway services-per-project ceiling** is a hard wall — confirm the limit
  before it matters.

## The migration, if/when

It is a storage-layer rewrite, not a deployment change:

1. **Kill process-global path state** — every store/paths call takes an
   explicit tenant/project context. *This step is shared with the parked
   Organizations work (SCOPES_PLAN): both need the app to hold more than one
   tenant's state at once. Doing it for Organizations buys the pooling option
   cheaply.*
2. **Records to Postgres** (specs, references metadata, approvals, state) with
   `tenant_id` + RLS; keep the JSON shapes as JSONB first, normalize later.
3. **Pixels to object storage** under tenant prefixes; signed URLs; takes
   never upscaled is unaffected.
4. **Identity**: real accounts replace the shared studio token (magic-link
   machinery already exists on the storefront).
5. **Renders to a queue** (workers), which also fixes long-request timeouts.
6. **Migrate silo tenants** one at a time — volume → bucket + DB import;
   keep silo as a premium isolation tier if it sells.

Rough order: weeks of focused work, dominated by step 1–2. Steps are
independently shippable; step 1 alone de-risks everything else.

## Trigger to revisit (decision, not drift)

**~50 paying customers, or per-tenant infra cost exceeding ~15% of the
Personal tier price — whichever comes first.** Before then, silo's weaknesses
are cheaper to patch than to re-architect away. Close the backup gap before
the first real subscriber regardless: "your IP is isolated on your own
volume" and "your volume has no backups" cannot be said in the same breath.
