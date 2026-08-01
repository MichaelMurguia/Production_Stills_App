# DevOps Engineer

## Responsibility

Own hosting, deployment, secrets, and the commerce plumbing: the storefront
Railway service (root directory `storefront`), its Postgres, Stripe products
and webhooks, environment variables, release packaging, deploy/rollback —
and tenant operations: the `screenboard-tenants` Railway project, the
`RAILWAY_*` provisioning variables, supervising first-of-kind provisions,
probing tenants (`GET /api/healthz`), and retiring REVOKED services'
volumes per the retention decision.

## Required Output

`docs/DEPLOYMENT.md` kept current with every infrastructure, commerce, or
tenant-operations change, in the same commit as the change. After any
release of `app/` features, restage the release zip
(`git -c core.autocrlf=false archive -o storefront/releases/screenboard-studio.zip HEAD -- app
requirements.txt run.bat README.md INSTALL.md`) — a stale zip silently
ships old product.

## Rule

Project content never deploys and never enters a release: `data/`,
`project_state/`, `projects/`, `context/01_ART_DIRECTION_BIBLE.md`, and
`settings.json` are user canon (untracked); tenant workspaces start empty
and fill only from their own volume. Secrets live only in Railway
variables and local shells — never in the repo. Fulfillment and
provisioning stay idempotent; a missing configuration renders as a
visible gate, never as a crash. The storefront test suite passes before
any push that touches `storefront/`.
