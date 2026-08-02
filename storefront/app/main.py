from __future__ import annotations

from pathlib import Path

import hmac

import stripe
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from . import auth, db, mailer, provisioner, settings

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
        purchase = db.Purchase(
            kind=kind,
            tier=tier,
            email=_sget(checkout_session.customer_details, "email") or "",
            stripe_session_id=checkout_session.id,
            stripe_customer_id=checkout_session.customer or "",
            stripe_subscription_id=checkout_session.subscription or "",
            stripe_payment_intent=_sget(checkout_session, "payment_intent") or "",
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
        _ = (purchase.workspace.status, purchase.workspace.url,
             purchase.workspace.access_token,
             purchase.workspace.railway_url, purchase.workspace.domain_live)
    s.expunge_all()


@app.get("/success")
def success(request: Request, background: BackgroundTasks, session_id: str = ""):
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
                                      {"state": "PAID", "purchase": purchase})


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
def signin_page(request: Request):
    if request.state.account_email:
        return RedirectResponse("/account")
    return _auth_page(request, "signin")


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
def auth_email(request: Request, email: str = Form(""), mode: str = Form("signin")):
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
        try:
            mailer.send(email, "Sign in to Screenboard Studio",
                        "Click to sign in (valid 30 minutes, single use):\n\n"
                        f"{link}\n\nNot you? Ignore this mail — nothing "
                        "happens without the link.\n\n— Screenboard Studio")
        except mailer.MailError as e:
            print(f"[auth] magic link send failed for {email}: {e}")
    return _auth_page(request, mode, sent=True)


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
    return resp


@app.post("/auth/logout")
def auth_logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE)
    return resp


@app.post("/studio/name")
def name_studio(request: Request, background: BackgroundTasks,
                workspace_id: int = Form(0), name: str = Form("")):
    """Claim or rename a studio's subdomain. Owner-only (signed-in email
    must match the purchase). The wildcard router serves the new name the
    moment reconcile commits it; the old name then reads as unclaimed."""
    from urllib.parse import quote
    email = request.state.account_email
    if not email:
        return RedirectResponse("/signin", status_code=303)
    name = name.strip().lower()
    err = ""
    if not provisioner.valid_subdomain(name):
        err = ("names are 2-63 characters: lowercase letters, digits, and "
               "hyphens (not first or last)" if name not in
               provisioner.RESERVED_SUBDOMAINS else "that name is reserved")
    with db.session() as s:
        ws = s.get(db.Workspace, workspace_id)
        if not ws or ws.purchase.email != email:
            raise HTTPException(404)
        if not err and ws.subdomain != name:
            clash = s.scalar(select(db.Workspace).where(
                db.Workspace.subdomain == name, db.Workspace.id != ws.id))
            if clash:
                err = "that name is taken"
            else:
                ws.subdomain = name
                try:
                    s.commit()
                except IntegrityError:
                    # Two buyers claimed the same name in the same instant;
                    # the partial unique index picks exactly one winner.
                    s.rollback()
                    err = "that name is taken"
    if err:
        return RedirectResponse(f"/account?name_error={quote(err)}",
                                status_code=303)
    background.add_task(provisioner.reconcile)
    return RedirectResponse("/account?named=1", status_code=303)


@app.get("/account")
def account_page(request: Request, name_error: str = "", named: int = 0,
                 claim: str = ""):
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
def recover(request: Request, email: str = Form("")):
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
            try:
                mailer.send(email, "Your Screenboard Studio licenses",
                            _recovery_body(purchases))
            except mailer.MailError as e:
                print(f"[recover] send failed for {email}: {e}")  # ops-only
    return templates.TemplateResponse(request, "recover.html", {
        "mail_ready": True, "sent": True})


def _admin_gate(request: Request, token: str) -> None:
    """One gate for every /admin endpoint. The token still works as a
    query param (curl-friendly, existing runbooks), but an Authorization
    bearer header is preferred — query strings land in access logs."""
    supplied = token or request.headers.get(
        "authorization", "").removeprefix("Bearer ").strip()
    if not settings.ADMIN_EXPORT_TOKEN:
        raise HTTPException(404)
    if not hmac.compare_digest(supplied, settings.ADMIN_EXPORT_TOKEN):
        raise HTTPException(404)


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
