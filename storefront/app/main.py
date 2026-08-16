from __future__ import annotations

import asyncio
import datetime as dt
import threading
import time
from pathlib import Path
from urllib.parse import quote

import hmac

import stripe
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import (FileResponse, JSONResponse, RedirectResponse,
                               Response)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from . import auth, db, mailer, provisioner, settings, trials

stripe.api_key = settings.STRIPE_SECRET_KEY

app = FastAPI(title="Screenboard Studio — Storefront")
db.init_db()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline hardening on every public response — and the session read,
    so every template can render the header account widget."""
    email = auth.read_session(request.cookies.get(auth.SESSION_COOKIE, ""))
    request.state.account_email = email
    request.state.is_owner = bool(email) and email.lower() in settings.OWNER_EMAILS
    request.state.account_avatar = ""
    request.state.account_name = email  # header shows first name when known
    if email and not request.url.path.startswith(("/static", "/healthz")):
        def _acct() -> tuple[str, str]:
            with db.session() as s:
                acct = s.scalar(select(db.Account).where(
                    db.Account.email == email))
                return (acct.name if acct else "", acct.picture if acct else "")
        # Sync DB work off the event loop — this middleware wraps every
        # request, including long-poll proxying.
        name, picture = await run_in_threadpool(_acct)
        request.state.account_avatar = auth.avatar_url(email, picture)
        if name.strip():
            request.state.account_name = name.split()[0]
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    return resp


PREVIEW_COOKIE = "sb_preview"
_PREVIEW_EXEMPT = ("/static", "/healthz", "/stripe/webhook", "/api/site-text",
                   "/robots.txt", "/sitemap.xml", "/preview/unlock", "/admin")


def _preview_open(request: Request) -> bool:
    """True when the visitor may pass the coming-soon gate."""
    if not settings.PREVIEW_PASSWORD:
        return True
    cookie = request.cookies.get(PREVIEW_COOKIE, "")
    return hmac.compare_digest(cookie, auth._sign("preview:" + settings.PREVIEW_PASSWORD))


@app.middleware("http")
async def coming_soon_gate(request: Request, call_next):
    path = request.url.path
    if _preview_open(request) or path.startswith(_PREVIEW_EXEMPT):
        return await call_next(request)
    if request.method in ("GET", "HEAD"):
        return templates.TemplateResponse(
            request, "coming_soon.html", {"error": False}, status_code=200)
    return JSONResponse({"detail": "coming soon"}, status_code=403)


@app.post("/preview/unlock")
def preview_unlock(request: Request, password: str = Form("")):
    if not settings.PREVIEW_PASSWORD:
        return RedirectResponse("/", status_code=303)
    if not hmac.compare_digest(password.strip(), settings.PREVIEW_PASSWORD):
        import time
        time.sleep(0.5)  # guessing stays slow
        return templates.TemplateResponse(
            request, "coming_soon.html", {"error": True}, status_code=200)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(PREVIEW_COOKIE,
                    auth._sign("preview:" + settings.PREVIEW_PASSWORD),
                    max_age=30 * 86400, httponly=True, samesite="lax",
                    secure=_cookies_secure(request))
    return resp


def _cookies_secure(request: Request) -> bool:
    """Railway terminates TLS upstream, so request.url.scheme can read
    'http' on a fully-HTTPS deployment — the public BASE_URL is the truth
    about whether Secure cookies are safe to require."""
    return (request.url.scheme == "https"
            or settings.BASE_URL.startswith("https"))


def _set_session(resp, request: Request, email: str) -> None:
    resp.set_cookie(auth.SESSION_COOKIE, auth.make_session(email),
                    max_age=auth.SESSION_DAYS * 86400, httponly=True,
                    samesite="lax", secure=_cookies_secure(request))


# A code held across the sign-in round trip. Redeeming needs an identity,
# but asking someone to find their code again after signing in is the kind
# of small cruelty that loses a trial. The cookie is signed (a forged one
# could only redeem a code the forger already knows) and short-lived.
TRIAL_COOKIE = "sb_trial"
TRIAL_COOKIE_TTL = 1800


def _stash_trial_code(resp, request: Request, code: str) -> None:
    code = (code or "").strip()[:32]
    resp.set_cookie(TRIAL_COOKIE, f"{code}|{auth._sign('trial:' + code)}",
                    max_age=TRIAL_COOKIE_TTL, httponly=True, samesite="lax",
                    secure=_cookies_secure(request))


def _consume_trial_code(request: Request, resp, email: str) -> str:
    """Redeem a stashed code the moment an identity exists. Returns the
    redirect path the caller should use instead of its own. Failures are
    carried to /trial as stated errors — never swallowed, never fatal to
    the sign-in itself."""
    raw = request.cookies.get(TRIAL_COOKIE, "")
    code, _, sig = raw.partition("|")
    if not code or not hmac.compare_digest(sig, auth._sign("trial:" + code)):
        return ""
    resp.delete_cookie(TRIAL_COOKIE)
    with db.session() as s:
        try:
            purchase = trials.redeem(s, code, email)
            provisioner.ensure_workspace_row(s, purchase)
        except trials.TrialError as e:
            return f"/trial?error={quote(str(e))}&code={quote(code)}"
    threading.Thread(target=provisioner.reconcile, daemon=True).start()
    return "/account?trial=1"


def _redirect_keeping(resp, location: str):
    """Change where a prepared response points without losing the cookies
    already set on it (the session — losing it would sign the user
    straight back out)."""
    out = RedirectResponse(location, status_code=303)
    for key, value in resp.raw_headers:
        if key.lower() == b"set-cookie":
            out.raw_headers.append((key, value))
    return out


def _login_account(email: str, name: str = "", google_sub: str = "",
                   picture: str = "") -> None:
    """First sign-in creates the account; later ones refresh it. Signup and
    sign-in deliberately converge — identity is the verified email."""
    import datetime as dt
    with db.session() as s:
        acct = s.scalar(select(db.Account).where(db.Account.email == email))
        if acct is None:
            acct = db.Account(email=email, name=name, google_sub=google_sub,
                              picture=picture)
            s.add(acct)
        else:
            if name and not acct.name:
                acct.name = name
            if google_sub and not acct.google_sub:
                acct.google_sub = google_sub
            if picture:
                acct.picture = picture
        acct.last_login_at = dt.datetime.now(dt.timezone.utc)
        s.commit()


@app.on_event("startup")
def _reconcile_on_start():
    """Converge workspaces toward the purchases table on boot — catches
    anything missed while the service was down. reconcile() never raises."""
    import threading
    threading.Thread(target=provisioner.reconcile, daemon=True).start()


@app.on_event("startup")
def _fleet_update_on_start():
    """Updates follow the push (user ruling 2026-08-12): this deploy IS
    the release event, so a boot on a commit the fleet has not seen
    triggers the tenant fleet update automatically. The manual door
    (/admin/tenants/update and scripts/update_tenants.sh) remains as the
    fallback; auto_update_tenants() skips outside Railway."""
    import threading

    def run():
        out = provisioner.auto_update_tenants()
        print(f"[fleet] auto-update: {out}", flush=True)

    threading.Thread(target=run, daemon=True).start()

_here = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=_here / "static"), name="static")
# Brand icons at /icons/ per brand spec — the webmanifest's src paths and
# both sites' head snippets agree on this root.
app.mount("/icons", StaticFiles(directory=_here / "static" / "icons"), name="icons")
templates = Jinja2Templates(directory=_here / "templates")
# Canonical URLs and og:url must always name the PUBLIC host, never
# whatever Host header arrived — BASE_URL is the truth (SEO pass).
templates.env.globals["base_url"] = settings.BASE_URL.rstrip("/")

# Plan slug -> Stripe mode + price env var. Slugs appear in checkout URLs and
# in session metadata; kind/tier are derived by splitting on the hyphen.
PLANS = {
    "download-personal": {"mode": "payment", "price": lambda: settings.STRIPE_PRICE_DOWNLOAD_PERSONAL},
    "download-business": {"mode": "payment", "price": lambda: settings.STRIPE_PRICE_DOWNLOAD_BUSINESS},
    "cloud-personal": {"mode": "subscription", "price": lambda: settings.STRIPE_PRICE_CLOUD_PERSONAL},
    "cloud-business": {"mode": "subscription", "price": lambda: settings.STRIPE_PRICE_CLOUD_BUSINESS},
}


def _ready() -> dict[str, bool]:
    return {slug: bool(settings.STRIPE_SECRET_KEY and plan["price"]())
            for slug, plan in PLANS.items()}


@app.get("/healthz")
def healthz():
    """Liveness, serving revision, and which optional gates are open —
    booleans only, never values; lets ops verify configuration landed
    without touching a dashboard."""
    import os
    return {"ok": True,
            "rev": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local")[:12],
            "stripe": bool(settings.STRIPE_SECRET_KEY),
            "mail": mailer.configured(),
            "google_auth": auth.google_configured(),
            "session_secret": bool(settings.SESSION_SECRET),
            "provisioning": settings.railway_configured(),
            "export": bool(settings.ADMIN_EXPORT_TOKEN)}


@app.get("/")
def index(request: Request):
    ready = _ready()
    return templates.TemplateResponse(request, "index.html", {
        "ready": ready,
        "all_ready": all(ready.values()),
        "trials_open": settings.trials_open(),
        "trial_days": settings.TRIAL_DAYS,
    })


@app.get("/pipeline")
def pipeline(request: Request):
    """The method page — static marketing, no data dependencies."""
    return templates.TemplateResponse(request, "pipeline.html", {})


# ------------------------------------------------------------------- SEO
# Crawl surface (SEO pass, user request 2026-08-03): the four public pages
# index and sitemap; everything transactional or private is disallowed
# here AND carries a noindex meta (belt and braces — robots.txt is a
# request, the meta is the instruction).

_PUBLIC_PATHS = ("/", "/pipeline", "/terms", "/privacy")


@app.get("/robots.txt")
def robots_txt():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        "User-agent: *\n"
        "Disallow: /account\n"
        "Disallow: /success\n"
        "Disallow: /signin\n"
        "Disallow: /signup\n"
        "Disallow: /recover\n"
        "Disallow: /auth/\n"
        "Disallow: /checkout/\n"
        "Disallow: /download/\n"
        "Disallow: /admin/\n"
        "Disallow: /studio/\n"
        f"Sitemap: {settings.BASE_URL.rstrip('/')}/sitemap.xml\n")


@app.get("/sitemap.xml")
def sitemap_xml():
    base = settings.BASE_URL.rstrip("/")
    urls = "\n".join(
        f"  <url><loc>{base}{p}</loc></url>" for p in _PUBLIC_PATHS)
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n", media_type="application/xml")


# --------------------------------------------- owner page-text rewrites
# Debug tool (user request 2026-08-03): the store owner rewrites page copy
# in place. Reads are public (the overrides ARE the page copy every
# visitor sees); writes exist only for signed-in OWNER_EMAILS accounts.

def _require_owner(request: Request) -> None:
    if not getattr(request.state, "is_owner", False):
        raise HTTPException(404)


@app.get("/api/site-text")
def api_get_site_text() -> dict:
    with db.session() as s:
        rows = s.scalars(select(db.SiteText)).all()
        return {"overrides": {r.original: r.replacement for r in rows}}


@app.put("/api/site-text")
async def api_put_site_text(request: Request, body: dict) -> dict:
    _require_owner(request)
    overrides = body.get("overrides")
    if not isinstance(overrides, dict):
        raise HTTPException(422, "overrides must be an object of text → text")
    clean = {str(k)[:500]: str(v)[:500] for k, v in overrides.items()
             if str(k).strip()}
    with db.session() as s:
        s.execute(sa_delete(db.SiteText))
        for orig, repl in clean.items():
            s.add(db.SiteText(original=orig, replacement=repl))
        s.commit()
    return {"overrides": clean}


@app.delete("/api/site-text")
def api_clear_site_text(request: Request) -> dict:
    _require_owner(request)
    with db.session() as s:
        s.execute(sa_delete(db.SiteText))
        s.commit()
    return {"overrides": {}}


@app.get("/checkout/{plan}")
def checkout(plan: str):
    if plan not in PLANS:
        raise HTTPException(404)
    price = PLANS[plan]["price"]()
    if not (settings.STRIPE_SECRET_KEY and price):
        raise HTTPException(503, "Stripe is not configured yet")
    try:
        checkout_session = stripe.checkout.Session.create(
            mode=PLANS[plan]["mode"],
            line_items=[{"price": price, "quantity": 1}],
            success_url=f"{settings.BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BASE_URL}/",
            metadata={"plan": plan},
        )
    except stripe.StripeError as e:
        # A misconfigured price/key must read as a stated condition, not a
        # mystery 500. Stripe's message names the offending object (price
        # ids are not secrets); the buyer sees that checkout is down.
        raise HTTPException(503, f"Checkout is unavailable: {getattr(e, 'user_message', None) or str(e)}")
    return RedirectResponse(checkout_session.url, status_code=303)


def _sget(obj, key, default=None):
    """Read a field off a StripeObject or a plain dict. Stripe's objects
    support attribute access but not dict .get(); tests use dicts."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fulfill(checkout_session) -> db.Purchase:
    """Record a paid Checkout session, creating the license for downloads.
    Idempotent on stripe_session_id — safe to call from both the webhook and
    the /success page."""
    with db.session() as s:
        existing = s.scalar(select(db.Purchase).where(
            db.Purchase.stripe_session_id == checkout_session.id))
        if existing:
            if existing.kind == "cloud":
                provisioner.ensure_workspace_row(s, existing)
            _detach_loaded(s, existing)
            return existing

        plan = _sget(checkout_session.metadata, "plan") or (
            "cloud" if checkout_session.mode == "subscription" else "download")
        kind, _, tier = plan.partition("-")
        # Card trial: the window is carried on the session's metadata so
        # fulfillment needs no extra Stripe call. Stripe's own trial_end
        # is authoritative and corrects this date on the first
        # customer.subscription.updated event.
        trial_days = int(_sget(checkout_session.metadata, "trial_days") or 0)
        purchase = db.Purchase(
            kind=kind,
            tier=tier,
            email=_sget(checkout_session.customer_details, "email") or "",
            stripe_session_id=checkout_session.id,
            stripe_customer_id=checkout_session.customer or "",
            stripe_subscription_id=checkout_session.subscription or "",
            stripe_payment_intent=_sget(checkout_session, "payment_intent") or "",
            trial_kind="card" if trial_days else "",
            trial_ends_at=(dt.datetime.utcnow() + dt.timedelta(days=trial_days)
                           if trial_days else None),
        )
        s.add(purchase)
        if kind == "download":
            purchase.license = db.License()
        try:
            s.commit()
        except IntegrityError:
            # Webhook and /success fulfilled the same session at once; the
            # unique stripe_session_id makes exactly one insert win. Read
            # the winner and serve it — the buyer must never see a 500.
            s.rollback()
            existing = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_session_id == checkout_session.id))
            if existing.kind == "cloud":
                provisioner.ensure_workspace_row(s, existing)
            _detach_loaded(s, existing)
            return existing
        s.refresh(purchase)
        if kind == "cloud":
            provisioner.ensure_workspace_row(s, purchase)
        _detach_loaded(s, purchase)
        return purchase


def _detach_loaded(s, purchase: db.Purchase) -> None:
    """Force-load the relationships templates read, then detach — the
    detached-safe rule from the DetachedInstanceError production bug."""
    if purchase.license:
        _ = purchase.license.token
    if purchase.workspace:
        ws = purchase.workspace
        _ = (ws.id, ws.status, ws.url, ws.access_token,
             ws.railway_url, ws.domain_live, ws.subdomain)
        # Claimed vs auto-assigned drives the door's naming-first state.
        ws.name_claimed = bool(ws.subdomain
                               and not provisioner.is_random_slug(ws.subdomain))
    s.expunge_all()


@app.get("/success")
def success(request: Request, background: BackgroundTasks, session_id: str = "",
            name_error: str = ""):
    if not session_id:
        return RedirectResponse("/")
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        # Garbage or foreign session ids are a visitor problem, not a 500.
        return RedirectResponse("/")
    if checkout_session.payment_status not in ("paid", "no_payment_required"):
        return templates.TemplateResponse(request, "success.html",
                                          {"state": "PENDING", "purchase": None})
    purchase = _fulfill(checkout_session)
    if purchase.kind == "cloud":
        # Provision after the response goes out; the buyer revisits this
        # page (idempotent) and finds the workspace once it's ACTIVE.
        background.add_task(provisioner.reconcile)
    return templates.TemplateResponse(request, "success.html",
                                      {"state": "PAID", "purchase": purchase,
                                       "session_id": session_id,
                                       "name_error": name_error[:120]})


@app.get("/success/status")
def success_status(session_id: str = ""):
    """Tiny poll target for the success page: is the workspace ready yet?
    session_id is the same capability the success page itself uses; the
    response carries state only, never credentials."""
    if not session_id:
        raise HTTPException(404)
    with db.session() as s:
        purchase = s.scalar(select(db.Purchase).where(
            db.Purchase.stripe_session_id == session_id))
        if not purchase:
            return {"workspace": "NONE"}
        ws = purchase.workspace
        return {"workspace": ws.status if ws else "PENDING"}


def available_versions() -> list[tuple[str, Path]]:
    """Every staged versioned release, newest first. Versions are parsed
    from filenames (screenboard-studio-<v>.zip) — the directory IS the
    registry; versioned zips are immutable by CI rule."""
    import re as _re
    out = []
    for f in settings.DOWNLOAD_FILE.parent.glob("screenboard-studio-*.zip"):
        m = _re.fullmatch(r"screenboard-studio-([0-9][0-9A-Za-z.\-]*)\.zip", f.name)
        if m:
            out.append((m.group(1), f))
    def key(item):
        # Typed tuples, not bare values — a version like 2026.08.01-rc
        # would make int < str comparisons raise and 500 the account page.
        return [(0, int(x), "") if x.isdigit() else (1, 0, x)
                for x in _re.split(r"[.\-]", item[0])]
    return sorted(out, key=key, reverse=True)


@app.get("/download/{token}")
def download(token: str, version: str = ""):
    """The current release by default; any past version via ?version=.
    Versions resolve only through the staged-file registry — never from
    the raw parameter — so the token gate stays the only door."""
    with db.session() as s:
        lic = s.scalar(select(db.License).where(db.License.token == token))
        if not lic or lic.purchase.status != "PAID":
            raise HTTPException(404)
        lic.downloads_used += 1
        s.commit()
    versions = available_versions()
    if version:
        match = next((f for v, f in versions if v == version), None)
        if match is None:
            raise HTTPException(404, "no such version")
        path = match
    elif versions:
        path = versions[0][1]
    else:
        path = settings.DOWNLOAD_FILE
    if not path.exists():
        raise HTTPException(503, "Release artifact is not staged on the server yet")
    return FileResponse(path, filename=path.name, media_type="application/zip")


@app.get("/terms")
def terms(request: Request):
    return templates.TemplateResponse(request, "terms.html", {})


@app.get("/privacy")
def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})


def _auth_page(request: Request, mode: str, **ctx):
    return templates.TemplateResponse(request, "signin.html", {
        "mode": mode, "google_ready": auth.google_configured(),
        "mail_ready": mailer.configured(), "sent": False,
        "error": "", **ctx})


@app.get("/signin")
def signin_page(request: Request, trial: int = 0):
    if request.state.account_email:
        return RedirectResponse("/account")
    return _auth_page(request, "signin", trial_pending=bool(trial))


@app.get("/signup")
def signup_page(request: Request):
    if request.state.account_email:
        return RedirectResponse("/account")
    return _auth_page(request, "signup")


# Last magic-link send per address — one mail a minute is plenty for a
# human and starves a mail-bomb loop. In-process on purpose: a restart
# forgiving the throttle is harmless.
_magic_last: dict[str, float] = {}


@app.post("/auth/email")
def auth_email(request: Request, background: BackgroundTasks,
               email: str = Form(""), mode: str = Form("signin")):
    """Send a magic link. Uniform response for any address; creating vs
    signing in converges at the link — the inbox is the proof."""
    import datetime as dt
    import time
    mode = "signup" if mode == "signup" else "signin"
    if not mailer.configured():
        return _auth_page(request, mode)
    email = email.strip().lower()
    if email and "@" in email:
        now = time.time()
        if now - _magic_last.get(email, 0) < 60:
            return _auth_page(request, mode, sent=True)  # uniform response
        _magic_last[email] = now
        with db.session() as s:
            # Opportunistic hygiene: dead tokens never accumulate forever.
            s.execute(sa_delete(db.LoginToken).where(
                db.LoginToken.expires_at
                < dt.datetime.utcnow() - dt.timedelta(days=1)))
            t = db.LoginToken(email=email)
            s.add(t)
            s.commit()
            link = f"{settings.BASE_URL}/auth/verify?token={t.token}"
        # The SMTP round trip — connect, STARTTLS, AUTH, send — ran inline
        # and the browser waited for all of it (user-hit 2026-08-06: 20
        # seconds to reach "check your inbox"; the 30s timeout was the
        # worst case). It goes out AFTER the response now. Nothing is
        # lost: the response never depended on the send succeeding,
        # because it must be identical for every address.
        background.add_task(_send_magic_link, email, link)
    return _auth_page(request, mode, sent=True)


def _send_magic_link(email: str, link: str) -> None:
    """Runs after the response. A failure is recorded for the owner and
    never reaches the visitor — telling them the send failed would leak
    which addresses exist."""
    try:
        mailer.send(email, "Sign in to Screenboard Studio",
                    "Click to sign in (valid 30 minutes, single use):\n\n"
                    f"{link}\n\nNot you? Ignore this mail — nothing "
                    "happens without the link.\n\n— Screenboard Studio")
        mailer.record("magic link", email, "")
    except mailer.MailError as e:
        mailer.record("magic link", email, str(e))
        print(f"[auth] magic link send failed for {email}: {e}")


@app.get("/auth/verify")
def auth_verify(request: Request, token: str = ""):
    import datetime as dt
    with db.session() as s:
        t = s.scalar(select(db.LoginToken).where(db.LoginToken.token == token))
        if not t or t.used or t.expires_at < dt.datetime.utcnow():
            return _auth_page(request, "signin",
                              error="That link is expired or already used — request a fresh one.")
        t.used = 1
        email = t.email
        s.commit()
    _login_account(email)
    resp = RedirectResponse("/account", status_code=303)
    _set_session(resp, request, email)
    pending = _consume_trial_code(request, resp, email)
    if pending:
        return _redirect_keeping(resp, pending)
    return resp


@app.get("/auth/google")
def auth_google(request: Request):
    if not auth.google_configured():
        raise HTTPException(404)
    state = auth.make_state()
    resp = RedirectResponse(auth.google_auth_url(state), status_code=303)
    # The callback must come from the browser that started the flow —
    # the state cookie is the binding (login-CSRF guard).
    resp.set_cookie(auth.STATE_COOKIE, state, max_age=auth.STATE_TTL,
                    httponly=True, samesite="lax",
                    secure=_cookies_secure(request))
    return resp


@app.get("/auth/google/callback")
def auth_google_callback(request: Request, code: str = "", state: str = ""):
    if not auth.google_configured():
        raise HTTPException(404)
    state_cookie = request.cookies.get(auth.STATE_COOKIE, "")
    if not code or not auth.check_state(state, state_cookie):
        return _auth_page(request, "signin",
                          error="Google sign-in didn't complete — try again.")
    try:
        ident = auth.google_identity(code)
    except auth.AuthError as e:
        return _auth_page(request, "signin", error=str(e))
    _login_account(ident["email"], ident["name"], ident["sub"],
                   ident.get("picture", ""))
    resp = RedirectResponse("/account", status_code=303)
    resp.delete_cookie(auth.STATE_COOKIE)
    _set_session(resp, request, ident["email"])
    pending = _consume_trial_code(request, resp, ident["email"])
    if pending:
        return _redirect_keeping(resp, pending)
    return resp


@app.post("/auth/logout")
def auth_logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE)
    return resp


@app.post("/studio/name")
def name_studio(request: Request, background: BackgroundTasks,
                workspace_id: int = Form(0), name: str = Form(""),
                session_id: str = Form("")):
    """Claim or rename a studio's subdomain. Owner-only: the signed-in
    email must match the purchase — or, on the success page, the Stripe
    session id is the same capability that page already trusts to show
    the workspace itself (a fresh buyer has not signed in yet). The
    wildcard router serves the new name the moment reconcile commits it;
    the old name then reads as unclaimed."""
    from urllib.parse import quote
    email = request.state.account_email
    if not email and not session_id:
        return RedirectResponse("/signin", status_code=303)
    back = (f"/success?session_id={quote(session_id)}" if session_id
            else "/account")
    name = name.strip().lower()
    err = ""
    if not provisioner.valid_subdomain(name):
        err = ("names are 2-63 characters: lowercase letters, digits, and "
               "hyphens (not first or last)" if name not in
               provisioner.RESERVED_SUBDOMAINS else "that name is reserved")
    with db.session() as s:
        ws = s.get(db.Workspace, workspace_id)
        owner_ok = ws and (
            (email and ws.purchase.email == email)
            or (session_id and ws.purchase.stripe_session_id == session_id))
        if not owner_ok:
            raise HTTPException(404)
        if not err and ws.subdomain != name:
            clash = s.scalar(select(db.Workspace).where(
                db.Workspace.subdomain == name, db.Workspace.id != ws.id))
            if clash:
                err = "that name is taken"
            else:
                old_name = ws.subdomain
                ws.subdomain = name
                # The door must tell the truth on the very next render —
                # never wait for the background reconcile (a user renamed,
                # refreshed, and was handed their OLD address, 2026-08-04).
                if settings.TENANT_DOMAIN_BASE:
                    ws.url = f"https://{name}.{settings.TENANT_DOMAIN_BASE}"
                    ws.domain_live = 0  # re-probed by reconcile before doors prefer it
                if old_name and old_name != name:
                    ws.prev_subdomain = old_name  # forwards until reclaimed
                try:
                    s.commit()
                except IntegrityError:
                    # Two buyers claimed the same name in the same instant;
                    # the partial unique index picks exactly one winner.
                    s.rollback()
                    err = "that name is taken"
    if err:
        sep = "&" if "?" in back else "?"
        return RedirectResponse(f"{back}{sep}name_error={quote(err)}",
                                status_code=303)
    background.add_task(provisioner.reconcile)
    sep = "&" if "?" in back else "?"
    return RedirectResponse(f"{back}{sep}named=1", status_code=303)


# --------------------------------------------- the door's render preview
# The store cannot read a tenant's disk, so it asks the studio — with the
# studio's own access token, server-side. The token never reaches a
# browser and the tenant is never called from one. Cached briefly so a
# page reload does not hammer a customer's service.

_preview_cache: dict[int, tuple[float, dict]] = {}
_PREVIEW_TTL = 300


def _studio_for(request: Request, ws_id: int):
    """The workspace this signed-in account owns, or None. Ownership is
    the gate on every preview route — a studio's work is nobody else's."""
    email = request.state.account_email
    if not email:
        return None
    with db.session() as s:
        ws = s.get(db.Workspace, ws_id)
        if not ws or ws.purchase.email != email or ws.status != "ACTIVE":
            return None
        door = ws.railway_url or ws.url
        return {"id": ws.id, "door": door, "token": ws.access_token}


def _ask_studio(studio: dict) -> dict:
    """One brief server-to-server call, cached. Any failure is 'no
    preview' — a door that cannot reach its studio still renders."""
    import time

    hit = _preview_cache.get(studio["id"])
    if hit and time.time() - hit[0] < _PREVIEW_TTL:
        return hit[1]
    out = {"found": False}
    try:
        import httpx
        r = httpx.get(f"{studio['door']}/api/preview-render",
                      cookies={"sb_session": studio["token"]},
                      timeout=4.0, follow_redirects=False)
        if r.status_code == 200:
            out = r.json()
    except Exception:
        pass  # the hatch is the correct fallback, stated by the caller
    _preview_cache[studio["id"]] = (time.time(), out)
    return out


@app.get("/studio/{ws_id}/preview")
def studio_preview(request: Request, ws_id: int):
    """What the door should show. Never blocks the account page — the
    page renders its hatch first and this fills it in."""
    studio = _studio_for(request, ws_id)
    if not studio:
        raise HTTPException(404)
    info = _ask_studio(studio)
    if not info.get("found"):
        return {"found": False}
    return {"found": True, "src": f"/studio/{ws_id}/preview.img",
            "production": info.get("production", ""),
            "board": info.get("board", "")}


@app.get("/studio/{ws_id}/preview.img")
def studio_preview_image(request: Request, ws_id: int):
    """Streams the panel through the store so the studio's credential
    stays server-side. Owner-gated exactly like the JSON above."""
    studio = _studio_for(request, ws_id)
    if not studio:
        raise HTTPException(404)
    info = _ask_studio(studio)
    if not info.get("found"):
        raise HTTPException(404)
    try:
        import httpx
        r = httpx.get(f"{studio['door']}{info['image']}",
                      cookies={"sb_session": studio["token"]}, timeout=8.0)
        if r.status_code != 200:
            raise HTTPException(404)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404)
    return Response(content=r.content,
                    media_type=r.headers.get("content-type", "image/png"),
                    headers={"Cache-Control": "private, max-age=300"})


@app.get("/account")
def account_page(request: Request, name_error: str = "", named: int = 0,
                 claim: str = "", trial: int = 0):
    # ?claim=<name> arrives from the router's unclaimed-address page (T1):
    # it prefills the naming form so "Claim this name" lands ready to go.
    claim = claim.strip().lower()[:63]
    email = request.state.account_email
    if not email:
        return templates.TemplateResponse(request, "account.html", {
            "purchase": None, "missed": False, "purchases": None, "email": None})
    with db.session() as s:
        purchases = s.scalars(select(db.Purchase).where(
            db.Purchase.email == email).order_by(db.Purchase.id.desc())).all()
        for p in purchases:
            # Detached-safe: touch every column the template reads while the
            # session is still open (the DetachedInstanceError rule).
            _ = (p.trial_kind, p.trial_ends_at, p.status)
            if p.license:
                _ = p.license.token
            if p.workspace:
                _ = (p.workspace.id, p.workspace.status, p.workspace.url,
                     p.workspace.access_token, p.workspace.subdomain,
                     p.workspace.railway_url, p.workspace.domain_live)
                # Claimed vs still-auto-assigned drives Claim name/Rename.
                p.workspace.name_claimed = bool(
                    p.workspace.subdomain
                    and not provisioner.is_random_slug(p.workspace.subdomain))
        s.expunge_all()
    return templates.TemplateResponse(request, "account.html", {
        "purchase": None, "missed": False, "purchases": purchases,
        "email": email, "tenant_base": settings.TENANT_DOMAIN_BASE,
        "name_error": name_error[:120], "named": named, "claim": claim,
        "trial_started": bool(trial),
        "versions": [v for v, _ in available_versions()],
        "reserved_names": sorted(provisioner.RESERVED_SUBDOMAINS)})


@app.post("/account")
def account(request: Request, token: str = Form("")):
    """Token-as-credential sign-in: a license token or workspace access
    token shows its purchase. Tokens are unguessable 24-byte values; misses
    pay a small delay and get one uniform message."""
    token = token.strip()
    purchase = None
    if token:
        with db.session() as s:
            lic = s.scalar(select(db.License).where(db.License.token == token))
            ws = None if lic else s.scalar(select(db.Workspace).where(
                db.Workspace.access_token == token))
            found = (lic.purchase if lic else ws.purchase if ws else None)
            if found and found.status == "PAID":
                purchase = found
                if purchase.license:
                    _ = purchase.license.token
                if purchase.workspace:
                    _ = (purchase.workspace.status, purchase.workspace.url,
                         purchase.workspace.access_token)
                s.expunge_all()
    if purchase is None:
        import time
        time.sleep(0.5)
    return templates.TemplateResponse(request, "account.html", {
        "purchase": purchase, "missed": purchase is None})


@app.get("/recover")
def recover_page(request: Request):
    return templates.TemplateResponse(request, "recover.html", {
        "mail_ready": mailer.configured(), "sent": False})


def _recovery_body(purchases: list[db.Purchase]) -> str:
    lines = ["Here is everything registered to this address:", ""]
    for p in purchases:
        if p.kind == "download" and p.license:
            lines += [f"- Download license ({p.tier or 'personal'}):",
                      f"  token: {p.license.token}",
                      f"  download: {settings.BASE_URL}/download/{p.license.token}", ""]
        elif p.kind == "cloud":
            ws = p.workspace
            if ws and ws.status == "ACTIVE":
                lines += [f"- Cloud workspace ({p.tier or 'personal'}):",
                          f"  url: {ws.url}",
                          f"  access token: {ws.access_token}", ""]
            else:
                lines += [f"- Cloud subscription ({p.tier or 'personal'}): "
                          "workspace pending — revisit your Stripe receipt's "
                          "order link", ""]
    lines += ["— Screenboard Studio"]
    return "\n".join(lines)


@app.post("/recover")
def recover(request: Request, background: BackgroundTasks,
            email: str = Form("")):
    """Anti-enumeration by construction: the response is identical whether
    the address has purchases or not — details only ever travel to the
    address itself."""
    if not mailer.configured():
        return templates.TemplateResponse(request, "recover.html", {
            "mail_ready": False, "sent": False})
    email = email.strip().lower()
    if email:
        with db.session() as s:
            purchases = s.scalars(select(db.Purchase).where(
                db.Purchase.email == email,
                db.Purchase.status == "PAID")).all()
            for p in purchases:
                if p.license:
                    _ = p.license.token
                if p.workspace:
                    _ = (p.workspace.status, p.workspace.url,
                         p.workspace.access_token)
            s.expunge_all()
        if purchases:
            # After the response, for the same reason as the magic link.
            background.add_task(_send_recovery, email,
                                _recovery_body(purchases))
    return templates.TemplateResponse(request, "recover.html", {
        "mail_ready": True, "sent": True})


def _send_recovery(email: str, body: str) -> None:
    try:
        mailer.send(email, "Your Screenboard Studio licenses", body)
        mailer.record("recovery", email, "")
    except mailer.MailError as e:
        mailer.record("recovery", email, str(e))
        print(f"[recover] send failed for {email}: {e}")  # ops-only


def _admin_gate(request: Request, token: str) -> None:
    """One gate for every /admin endpoint, satisfied two ways.

    A signed-in OWNER_EMAILS account passes — that is what makes the
    browser console usable without pasting a secret into the address bar.
    Otherwise the shared token is required, as a query param (curl-
    friendly, existing runbooks) or, preferred, an Authorization bearer
    header; query strings land in access logs.

    Both are closed sets: OWNER_EMAILS is operator-configured and the
    session is HMAC-signed. Failure is always 404 — an admin surface must
    not confirm its own existence.
    """
    if getattr(request.state, "is_owner", False):
        return
    supplied = token or request.headers.get(
        "authorization", "").removeprefix("Bearer ").strip()
    if not settings.ADMIN_EXPORT_TOKEN:
        raise HTTPException(404)
    if not hmac.compare_digest(supplied, settings.ADMIN_EXPORT_TOKEN):
        raise HTTPException(404)


@app.get("/admin")
def admin_home(request: Request, token: str = "", ok: str = ""):
    """The owner's one page: debug tools, trial codes, and the operations
    that were previously curl-only. Signed in as an owner, no token is
    needed anywhere on it — every form posts back with the session."""
    _admin_gate(request, token)
    supplied = "" if getattr(request.state, "is_owner", False) else (
        token or request.headers.get(
            "authorization", "").removeprefix("Bearer ").strip())
    with db.session() as s:
        codes = [{"code": c.code, "days": c.days, "tier": c.tier,
                  "uses": c.uses, "max_uses": c.max_uses, "note": c.note,
                  "state": c.state(),
                  "expires_at": c.expires_at.strftime("%Y-%m-%d") if c.expires_at else "",
                  "created_at": c.created_at.strftime("%Y-%m-%d")}
                 for c in s.scalars(select(db.TrialCode).order_by(
                     db.TrialCode.id.desc())).all()]
        people = [{"email": p.email, "kind": p.trial_kind, "tier": p.tier,
                   "status": p.status, "code": p.trial_code,
                   "days_left": p.trial_days_left,
                   "ends": p.trial_ends_at.strftime("%Y-%m-%d") if p.trial_ends_at else "",
                   "studio": (p.workspace.subdomain if p.workspace else ""),
                   "studio_state": (p.workspace.status if p.workspace else "NONE")}
                  for p in s.scalars(select(db.Purchase).where(
                      db.Purchase.kind == "cloud",
                      db.Purchase.trial_kind != "").order_by(
                          db.Purchase.id.desc())).all()]
        counts = {
            "purchases": s.scalar(select(func.count()).select_from(db.Purchase)) or 0,
            "studios": s.scalar(select(func.count()).select_from(
                db.Workspace).where(db.Workspace.status == "ACTIVE")) or 0,
            "rewrites": s.scalar(select(func.count()).select_from(db.SiteText)) or 0,
        }
    return templates.TemplateResponse(request, "admin.html", {
        "codes": codes, "people": people, "token": supplied, "counts": counts,
        "mail_ready": mailer.configured(), "mail_log": mailer.recent(),
        "max_days": settings.TRIAL_CODE_MAX_DAYS,
        "trial_days": settings.TRIAL_DAYS,
        "trials_open": settings.trials_open(),
        "preview_gate": bool(settings.PREVIEW_PASSWORD),
        "ok": ok[:120]})


@app.post("/admin/ops")
def admin_ops(request: Request, background: BackgroundTasks,
              token: str = Form(""), action: str = Form("")):
    """The operations that used to be curl-only, as buttons. Each one is
    the same function the token endpoints call — nothing new can happen
    here that could not happen before."""
    _admin_gate(request, token)
    if action == "reconcile":
        out = provisioner.reconcile()
        msg = (f"reconcile — {out['provisioned']} provisioned, "
               f"{out['revoked']} revoked, {out.get('expired', 0)} trials expired")
    elif action == "test-mail":
        # The one place the real SMTP error is visible. Same code path as
        # a magic link, sent to the owner who pressed the button.
        to = request.state.account_email or (settings.OWNER_EMAILS
                                             and sorted(settings.OWNER_EMAILS)[0])
        if not to:
            msg = "mail test needs a signed-in owner address"
        elif not mailer.configured():
            msg = "mail test — SMTP is not configured (SMTP_HOST / SMTP_FROM unset)"
        else:
            try:
                mailer.send(to, "Screenboard Studio — mail test",
                            "This is the mail self-test from /admin.\n\n"
                            "If you are reading it, sign-in links and "
                            "license recovery can reach this inbox.\n\n"
                            "— Screenboard Studio")
                mailer.record("self-test", to, "")
                msg = f"mail test sent to {to} — check that inbox"
            except mailer.MailError as e:
                mailer.record("self-test", to, str(e))
                msg = f"mail test FAILED — {e}"
    elif action == "update-tenants":
        out = provisioner.update_tenants()
        msg = (f"fleet update — {len(out['updated'])} studios rebuilding"
               + (f", {len(out['failed'])} failed" if out["failed"] else ""))
    else:
        msg = "unknown action"
    return RedirectResponse(f"/admin?ok={quote(msg)}"
                            + (f"&token={quote(token)}" if token else ""),
                            status_code=303)


# The product refuses a render below this; the fleet view must not
# disagree with it about when a studio has stopped working.
STORAGE_REFUSING = 350 * 1024 * 1024
STORAGE_TIGHT = 1024 * 1024 * 1024
_storage_cache: dict[str, tuple[float, list]] = {}
_STORAGE_TTL = 30.0


async def _ask_storage(client, ws) -> dict:
    """One studio's volume, server-to-server. A studio that will not answer
    is UNREACHABLE — never 0 bytes free. A dead studio must not read as a
    critically full one, which is the mistake that would send someone to
    fix the wrong thing during an incident.

    E1 (RULE_PASS 2026-08-16) splits that further: a studio that ANSWERS
    but returns no figure is up, and calling it UNREACHABLE sends an
    operator looking for a dead host. It reads CANNOT MEASURE."""
    door = ws["door"]
    row = {"studio": ws["subdomain"] or str(ws["id"]), "state": "UNREACHABLE",
           "free": None, "total": None, "used_pct": None, "top": ""}
    if not door:
        return row
    try:
        r = await client.get(f"{door}/api/storage",
                             cookies={"sb_session": ws["token"]}, timeout=6.0)
        if r.status_code != 200:
            return row
        d = r.json()
    except Exception:
        return row
    total, free = int(d.get("total") or 0), int(d.get("free") or 0)
    if not total:
        # It answered. It is up. It simply could not measure its volume —
        # a different fact from silence, and a different thing to go and do.
        row["state"] = "CANNOT MEASURE"
        return row
    top = (d.get("breakdown") or [{}])[0]
    row.update({
        "free": free, "total": total,
        "used_pct": round((total - free) / total * 100),
        "top": f"{top.get('kind', '')} {_gb(top.get('bytes', 0))}".strip(),
        "state": ("REFUSING" if free < STORAGE_REFUSING
                  else "TIGHT" if free < STORAGE_TIGHT else "OK"),
    })
    return row


def _gb(n: int) -> str:
    n = int(n or 0)
    for unit, size in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} B"


@app.get("/admin/storage")
async def admin_storage(request: Request, token: str = ""):
    """Every live studio's volume on one page. /api/storage on a tenant
    answers only that studio's own session, so a full disk could only be
    found by opening each studio in turn (2026-08-07). Same gate and same
    server-to-server call the preview door already uses."""
    _admin_gate(request, token)
    hit = _storage_cache.get("all")
    if hit and time.time() - hit[0] < _STORAGE_TTL:
        return {"studios": hit[1], "cached": True}

    with db.session() as s:
        live = [{"id": w.id, "subdomain": w.subdomain,
                 "door": w.railway_url or w.url, "token": w.access_token}
                for w in s.scalars(select(db.Workspace).where(
                    db.Workspace.status == "ACTIVE")).all()]
    rows: list = []
    if live:
        import httpx
        async with httpx.AsyncClient(follow_redirects=False) as client:
            rows = list(await asyncio.gather(
                *[_ask_storage(client, w) for w in live]))
    # Worst first: the reason to open this is to find the studio in trouble.
    order = {"REFUSING": 0, "TIGHT": 1, "UNREACHABLE": 2,
             "CANNOT MEASURE": 3, "OK": 4}
    rows.sort(key=lambda r: (order.get(r["state"], 9),
                             r["free"] if r["free"] is not None else 1 << 62))
    _storage_cache["all"] = (time.time(), rows)
    return {"studios": rows, "cached": False, "headline": _fleet_headline(rows)}


def _fleet_headline(rows: list) -> str:
    """The fleet's worst state, in a sentence, so the page answers the
    operator's question before the table is read (E1, 2026-08-16). The
    table stays whole beneath it — collapsing a healthy fleet to one line
    optimises for the day nothing is wrong, which is the day nobody opens
    this page."""
    if not rows:
        return "No live studios."
    n = len(rows)
    def count(state):
        return sum(1 for r in rows if r["state"] == state)
    refusing, tight = count("REFUSING"), count("TIGHT")
    dark, blind = count("UNREACHABLE"), count("CANNOT MEASURE")
    if refusing:
        worst = min((r for r in rows if r["state"] == "REFUSING"),
                    key=lambda r: r["free"] if r["free"] is not None else 0)
        return (f"{refusing} of {n} studios are REFUSING writes — worst is "
                f"{worst['studio']} at {_gb(worst['free'])} free.")
    if tight:
        worst = min((r for r in rows if r["state"] == "TIGHT"),
                    key=lambda r: r["free"] if r["free"] is not None else 0)
        return (f"{tight} of {n} studios are TIGHT — worst is "
                f"{worst['studio']} at {_gb(worst['free'])} free.")
    if dark or blind:
        bits = []
        if dark:
            bits.append(f"{dark} not answering")
        if blind:
            bits.append(f"{blind} answering but unable to measure")
        return (f"Every studio that reported is OK, but {' and '.join(bits)}"
                f" — nothing is known about {dark + blind} of {n}.")
    return f"All {n} studios OK."


@app.get("/admin/railway-capabilities")
def admin_railway_capabilities(request: Request, token: str = ""):
    """What Railway's API offers for volumes. Read-only introspection with
    a fixed query — asked because one studio's volume is far smaller than
    another's and the fix depends on whether it can be grown from here."""
    _admin_gate(request, token)
    from . import railway
    if not settings.railway_configured():
        return {"configured": False}
    try:
        return {"configured": True, **railway.volume_capabilities()}
    except Exception as e:
        return {"configured": True, "error": str(e)[:400]}


@app.get("/admin/wildcard")
def admin_wildcard(request: Request, token: str = "", attach: str = ""):
    """One-time ops tool for the wildcard tenant router: list the Railway
    project's services, and with ?attach=<service_id> attach
    *.TENANT_DOMAIN_BASE to that service (the storefront), returning the
    DNS records Railway wants. Replaces hunting through Railway's UI.
    Gated exactly like /admin/export; harmlessly idempotent — Railway
    rejects a duplicate attach with a stated error."""
    _admin_gate(request, token)
    if not (settings.railway_configured() and settings.TENANT_DOMAIN_BASE):
        raise HTTPException(503, "railway or TENANT_DOMAIN_BASE not configured")
    from . import railway
    out: dict = {"base": settings.TENANT_DOMAIN_BASE}
    try:
        out["services"] = railway.list_services()
        if attach:
            out["attached"] = f"*.{settings.TENANT_DOMAIN_BASE}"
            out["dns_records"] = railway.create_custom_domain_records(
                attach, f"*.{settings.TENANT_DOMAIN_BASE}")
    except railway.RailwayError as e:
        out["error"] = str(e)
    return out


@app.get("/admin/reconcile")
def admin_reconcile(request: Request, token: str = ""):
    """Run provisioner.reconcile() on demand — same gate as /admin/export.
    Ops use: after a DNS change, flip domain_live the moment the branded
    address serves instead of waiting for the next deploy or webhook."""
    _admin_gate(request, token)
    return provisioner.reconcile()


@app.get("/admin/tenants/update")
def admin_update_tenants(request: Request, token: str = "", status: int = 0):
    """Fleet update: rebuild every ACTIVE tenant studio from the current
    repo head. Same gate as /admin/export. Run after each product release
    (see DEPLOYMENT.md runbook) — the cloud edition promises updates land
    the day they ship. ?status=1 lists recent deployments per studio
    instead of triggering anything."""
    _admin_gate(request, token)
    if status:
        from sqlalchemy import select as _sel
        from . import railway
        out = {}
        with db.session() as s:
            for ws in s.scalars(_sel(db.Workspace).where(
                    db.Workspace.status == "ACTIVE")).all():
                try:
                    out[ws.subdomain or ws.railway_service_id] = (
                        railway.list_deployments(ws.railway_service_id))
                except railway.RailwayError as e:
                    out[ws.subdomain or ws.railway_service_id] = str(e)
        return out
    return provisioner.update_tenants()


@app.get("/admin/export")
def admin_export(request: Request, token: str = ""):
    """Entitlement-data backup: purchases, licenses, workspaces as JSON.
    Exists only when ADMIN_EXPORT_TOKEN is configured; fetch it on a
    schedule and keep the file — losing this data means losing the record
    of who owns what."""
    _admin_gate(request, token)
    def row(o, cols):
        return {c: (v.isoformat() if hasattr(v := getattr(o, c), "isoformat") else v)
                for c in cols}
    with db.session() as s:
        return {
            "purchases": [row(p, ("id", "kind", "tier", "email",
                                  "stripe_session_id", "stripe_customer_id",
                                  "stripe_subscription_id",
                                  "stripe_payment_intent", "status", "created_at"))
                          for p in s.scalars(select(db.Purchase)).all()],
            "licenses": [row(l, ("id", "purchase_id", "token",
                                 "downloads_used", "created_at"))
                         for l in s.scalars(select(db.License)).all()],
            "workspaces": [row(w, ("id", "purchase_id", "status", "subdomain", "railway_url", "domain_live", "access_token",
                                   "railway_service_id", "railway_volume_id",
                                   "url", "detail", "created_at"))
                           for w in s.scalars(select(db.Workspace)).all()],
        }


# ------------------------------------------------------------------ trials
# Two doors into the same product: a card-backed trial that converts
# itself, and an operator-granted code that expires on our clock. Both
# produce an ordinary cloud entitlement — see app/trials.py.


def _trial_context(request: Request, **extra) -> dict:
    """Everything the trial page needs to state its own conditions."""
    email = request.state.account_email
    held = None
    if email:
        with db.session() as s:
            held = trials.active_trial_for(s, email)
            if held:
                _ = (held.trial_ends_at, held.trial_kind, held.tier)
                held.days_left = held.trial_days_left
                if held.workspace:
                    _ = (held.workspace.status, held.workspace.url,
                         held.workspace.subdomain)
                s.expunge_all()
            elif trials.has_entitlement(s, email):
                extra.setdefault("has_studio", True)
    ctx = {"trial_days": settings.TRIAL_DAYS,
           "trials_open": settings.trials_open(),
           # Each edition is offered only when its own price exists —
           # same readiness rule the pricing cards use.
           "trial_ready": {
               "personal": bool(settings.TRIAL_DAYS and settings.STRIPE_SECRET_KEY
                                and settings.STRIPE_PRICE_CLOUD_PERSONAL),
               "business": bool(settings.TRIAL_DAYS and settings.STRIPE_SECRET_KEY
                                and settings.STRIPE_PRICE_CLOUD_BUSINESS)},
           "email": email, "held": held,
           "code_prefix": trials.CODE_PREFIX}
    ctx.update(extra)
    return ctx


@app.get("/trial")
def trial_page(request: Request, error: str = "", code: str = ""):
    return templates.TemplateResponse(request, "trial.html", _trial_context(
        request, error=error[:200], code=code[:32]))


@app.get("/trial/start/{plan}")
def trial_start(request: Request, plan: str):
    """Card trial: an ordinary subscription that begins in trial. The
    payment method is captured now and Stripe converts on day N with no
    action from us — so the buyer's only decision at the end is whether
    to cancel, which is the honest shape for a trial that says it will
    charge. The plan's real price id is used; nothing separate exists."""
    if plan not in PLANS or PLANS[plan]["mode"] != "subscription":
        raise HTTPException(404)
    if not settings.trials_open():
        # Gates are stated, never errored (STORE_DESIGN_SYSTEM §5).
        return RedirectResponse("/trial?error=" + quote(
            "Free trials are not open right now."), status_code=303)
    price = PLANS[plan]["price"]()
    if not price:
        return RedirectResponse("/trial?error=" + quote(
            "That edition is not available for trial yet."), status_code=303)
    email = request.state.account_email
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            # The card is taken now; nothing is charged until the trial
            # ends. Without this Stripe may skip collection entirely and
            # the conversion silently fails on day N.
            payment_method_collection="always",
            subscription_data={"trial_period_days": settings.TRIAL_DAYS},
            success_url=f"{settings.BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BASE_URL}/trial",
            metadata={"plan": plan, "trial_days": str(settings.TRIAL_DAYS)},
            **({"customer_email": email} if email else {}),
        )
    except stripe.StripeError as e:
        raise HTTPException(503, f"Checkout is unavailable: "
                                 f"{getattr(e, 'user_message', None) or str(e)}")
    return RedirectResponse(checkout_session.url, status_code=303)


@app.post("/trial/redeem")
def trial_redeem(request: Request, background: BackgroundTasks,
                 code: str = Form("")):
    """Code trial: no payment method, no Stripe object — the operator
    granted this time deliberately. Redemption needs a signed-in account
    because the trial belongs to an identity, not to a browser."""
    email = request.state.account_email
    if not email:
        # Keep the code across the sign-in round trip; it redeems itself
        # the instant an identity exists (see _consume_trial_code).
        resp = RedirectResponse("/signin?trial=1", status_code=303)
        _stash_trial_code(resp, request, code)
        return resp
    with db.session() as s:
        try:
            purchase = trials.redeem(s, code, email)
        except trials.TrialError as e:
            return RedirectResponse(
                f"/trial?error={quote(str(e))}&code={quote(code.strip()[:32])}",
                status_code=303)
        provisioner.ensure_workspace_row(s, purchase)
    background.add_task(provisioner.reconcile)
    return RedirectResponse("/account?trial=1", status_code=303)


def _admin_back(token: str, msg: str) -> str:
    """Admin forms return to the hub. A token-authenticated caller keeps
    carrying its token; an owner session needs nothing."""
    return f"/admin?ok={quote(msg)}" + (f"&token={quote(token)}" if token else "")


def _handle_subscription_updated(obj) -> None:
    """Keep our copy of a card trial's window honest.

    Stripe's subscription is the authority on both facts we display: when
    the trial ends, and whether it still is one. This event carries the
    end date while trialing, and reports the conversion by moving to
    `active` with no trial_end — which is what makes the account page
    stop counting down. Never touches entitlement: a conversion does not
    change status, and only `customer.subscription.deleted` cancels.
    """
    sub_id = _sget(obj, "id") or ""
    if not sub_id:
        return
    trial_end = _sget(obj, "trial_end")
    sub_status = _sget(obj, "status") or ""
    with db.session() as s:
        purchase = s.scalar(select(db.Purchase).where(
            db.Purchase.stripe_subscription_id == sub_id))
        if not purchase:
            return
        if sub_status == "trialing" and trial_end:
            purchase.trial_kind = "card"
            purchase.trial_ends_at = dt.datetime.utcfromtimestamp(int(trial_end))
        elif sub_status in ("active", "past_due", "unpaid"):
            purchase.trial_kind = ""
            purchase.trial_ends_at = None
        s.commit()


@app.get("/admin/trials")
def admin_trials(request: Request, token: str = ""):
    """The trial console moved into the one admin page; the old address
    keeps working because it is in the runbook."""
    _admin_gate(request, token)
    return RedirectResponse("/admin" + (f"?token={quote(token)}" if token else ""),
                            status_code=303)


@app.post("/admin/trials/new")
def admin_trials_new(request: Request, token: str = Form(""),
                     days: int = Form(14), tier: str = Form("personal"),
                     max_uses: int = Form(1), valid_days: str = Form("0"),
                     valid_days_custom: int = Form(0),
                     note: str = Form("")):
    """`valid_days` is the code's own shelf life, counted from minting —
    a different clock from `days`, which is the trial's length counted
    from redemption. "custom" defers to the number beside the picker."""
    _admin_gate(request, token)
    if str(valid_days).strip().lower() == "custom":
        shelf = max(0, int(valid_days_custom or 0))
    else:
        try:
            shelf = max(0, int(valid_days or 0))
        except ValueError:
            shelf = 0  # an unparseable pick means no expiry, never a 500
    shelf = min(shelf, settings.TRIAL_CODE_MAX_DAYS)
    with db.session() as s:
        trials.create_code(s, days=days, tier=tier, max_uses=max_uses,
                           note=note, valid_days=shelf)
    return RedirectResponse(_admin_back(token, "code minted"),
                            status_code=303)


@app.post("/admin/trials/disable")
def admin_trials_disable(request: Request, token: str = Form(""),
                         code: str = Form("")):
    """Withdraw a code. Trials already redeemed from it are untouched —
    ending someone's granted time is a separate, deliberate act."""
    _admin_gate(request, token)
    with db.session() as s:
        row = s.scalar(select(db.TrialCode).where(
            db.TrialCode.code == trials.normalize(code)))
        if row:
            row.disabled = 1
            s.commit()
    return RedirectResponse(_admin_back(token, "code withdrawn"),
                            status_code=303)


@app.post("/admin/trials/end")
def admin_trials_end(request: Request, background: BackgroundTasks,
                     token: str = Form(""), email: str = Form("")):
    """End a code trial now — the studio is revoked on the next reconcile
    (which this schedules). Card trials are never ended here: Stripe owns
    a subscription with a payment method on it."""
    _admin_gate(request, token)
    with db.session() as s:
        for p in s.scalars(select(db.Purchase).where(
                db.Purchase.email == email.strip().lower(),
                db.Purchase.trial_kind == "code",
                db.Purchase.status == "PAID")).all():
            p.status = "EXPIRED"
        s.commit()
    background.add_task(provisioner.reconcile)
    return RedirectResponse(_admin_back(token, "trial ended"),
                            status_code=303)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "invalid signature")

    if event["type"] in ("checkout.session.completed",
                         "checkout.session.async_payment_succeeded"):
        checkout_session = stripe.checkout.Session.retrieve(
            event["data"]["object"]["id"])
        # completed fires even for delayed-payment methods still pending —
        # fulfilling would hand out licenses for money that never arrives.
        # Unpaid sessions wait for async_payment_succeeded.
        if checkout_session.payment_status in ("paid", "no_payment_required"):
            purchase = _fulfill(checkout_session)
            if purchase.kind == "cloud":
                background.add_task(provisioner.reconcile)
    elif event["type"] in ("charge.refunded", "charge.dispute.created"):
        pi = _sget(event["data"]["object"], "payment_intent") or ""
        if pi:
            with db.session() as s:
                purchase = s.scalar(select(db.Purchase).where(
                    db.Purchase.stripe_payment_intent == pi))
                if purchase and purchase.status == "PAID":
                    purchase.status = "REFUNDED"
                    s.commit()
            # Download gate reads status; cloud studios get revoked.
            background.add_task(provisioner.reconcile)
    elif event["type"] == "customer.subscription.updated":
        _handle_subscription_updated(event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]
        with db.session() as s:
            purchase = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_subscription_id == sub_id))
            if purchase:
                purchase.status = "CANCELED"
                s.commit()
        background.add_task(provisioner.reconcile)
    return {"received": True}


# The public ASGI entrypoint. `store` is the FastAPI storefront; `app` —
# what uvicorn serves — wraps it in the wildcard tenant router, so
# *.TENANT_DOMAIN_BASE studio hosts proxy to their tenant service and
# every storefront host passes straight through (see tenant_proxy.py).
from .tenant_proxy import TenantProxy  # noqa: E402

store = app
app = TenantProxy(store)
