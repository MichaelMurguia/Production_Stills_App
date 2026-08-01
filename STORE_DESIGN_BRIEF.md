# STORE_DESIGN_BRIEF.md — for Claude Design: the storefront, full redesign

**From the webapp agent, 2026-08-01.** The public sales site is live and
functionally complete; it has grown by accretion over two days and deserves
a real design pass. This brief is how you see it, where it lives, and what
must survive the redesign.

## Seeing it

- **Live site (public):** https://www.screenboardstudio.com — pages `/`,
  `/signin`, `/signup`, `/recover`, `/terms`, `/privacy`, `/account`
  (signed-out state). It is deployed from `main`; whatever you see there is
  current.
- **Signed-in and purchase states can't be reached anonymously** — design
  them from the template sources + the state matrix below rather than live.
- **Run it locally (all gates visible, no credentials needed):**
  `cd storefront && pip install -r requirements.txt && uvicorn app.main:app
  --port 8100 --reload` — SQLite, unconfigured Stripe/SMTP/Google render
  their stated gates, which are themselves states to design.

## Where it lives

- `storefront/app/templates/` — Jinja pages: `base.html` (header/footer
  shell), `index.html` (landing + pricing), `signin.html` (also covers
  signup), `account.html` (three modes), `success.html` (four states),
  `recover.html` (three states), `terms.html`, `privacy.html`.
- `storefront/app/static/store.css` — the store's ENTIRE stylesheet,
  seeded from the app's tokens and appended to all day; expect accretion.

**The storefront is a separate surface from the product app.** It follows
the same design language (`app/static/DESIGN_SYSTEM.md`: amber = one
signal, Courier = machine data, square corners, no frameworks/fonts/emoji)
but has its OWN stylesheet and its own freedom: unlike `app/`, storefront
class names are NOT frozen — restructure markup and CSS as you see fit.
What must not change: routes, form actions/field names, and template
variables (the FastAPI side reads them).

## The state matrix — every screen has states, all must be designed

| Page | States |
|---|---|
| `/` | plans configured; plans unconfigured (disabled buttons + SETUP notice); signed-in header (avatar + email + sign out) vs signed-out (Sign in button) |
| `/signin`, `/signup` | Google configured (button) vs not; mail configured (magic-link form) vs neither (stated gate + token fallback link); link-sent confirmation; error line (expired link, failed Google) |
| `/success` | payment pending; download license (token + download); cloud building (self-polling "SETTING UP…" that becomes the door); cloud active (Open button, token behind ADVANCED disclosure) |
| `/account` | signed out (token-paste fallback + miss state); signed in with purchases (per-purchase boxes: download / cloud-active with naming form, named/ error lines / cloud-pending / ended); signed in empty |
| `/recover` | mail unconfigured (stated gate); form; sent (uniform, anti-enumeration) |
| header/footer | everywhere: brand→home link, avatar widget (Google photo or DiceBear shapes in store palette), footer Lost license · Terms · Privacy |

## Product facts that shape the design

- Four SKUs: Download $119 / $249.99 one-time; Cloud $9.99 / $29.99 monthly.
- Accounts are passwordless (Google OIDC + email magic links); the token
  paths remain as fallbacks and must stay reachable.
- Cloud buyers get a private hosted studio at
  `<claimed-name>.screenboardstudio.com` (random two-word slug until they
  claim); the "Open your workspace" button signs them in via a URL
  fragment — credentials are deliberately hidden behind an ADVANCED
  disclosure everywhere.
- Gates philosophy applies to the store too: missing configuration renders
  as visible stated conditions, never errors — those gate states are
  first-class design targets.
- Every deploy is CI-verified against `/`, `/terms`, `/privacy`,
  `/recover`, `/account`, `/signin` — keep those routes serving 200.

## What the redesign owns

Everything visual: layout, typography scale, the pricing presentation, the
funnel's narrative, empty states, the header account widget, how the four
success states feel (especially "Building your studio" — it is the
product's first impression after payment). The uncanonized-table docket in
`app/static/DESIGN_SYSTEM.md` is the separate PRODUCT-side review; this
brief is the STORE-side one. If rulings here should bind future store work,
write them into a `STORE_DESIGN_SYSTEM.md` (or a store section appended to
the main design system) and the coding side will follow it.
