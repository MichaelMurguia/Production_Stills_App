# Webapp Engineer

## Responsibility

Continue development of both surfaces: the product app (`app/`, per
`CLAUDE.md` and `app/static/DESIGN_SYSTEM.md`) and the public storefront
(`storefront/`, per `docs/WEBAPP_GUIDE.md` and `docs/DEPLOYMENT.md`).

## Required Output

Working code with the storefront test suite passing
(`storefront/tests`), and the governing doc updated in the same commit as
any change it describes.

## Rule

The `app/` ↔ `storefront/` boundary is absolute. Fulfillment stays
idempotent on `stripe_session_id` with webhook and success page as
redundant paths. Gates render as state before they are hit — a missing
configuration or unmet precondition is shown and explained, never thrown.
The product app must keep working standalone and offline.
