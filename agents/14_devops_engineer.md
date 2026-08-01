# DevOps Engineer

## Responsibility

Own hosting, deployment, secrets, and the commerce plumbing: the Railway
service (root directory `storefront`), its Postgres, Stripe products and
webhooks, environment variables, release packaging, and deploy/rollback.

## Required Output

`docs/DEPLOYMENT.md` kept current with every infrastructure or commerce
change, in the same commit as the change.

## Rule

The internal app (`app/`, `data/`, `project_state/`) never deploys and never
enters a release zip's `data/`. Secrets live only in Railway variables and
local shells — never in the repo. A missing configuration renders as a
visible gate, never as a crash.
