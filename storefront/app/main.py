from __future__ import annotations

from pathlib import Path

import hmac

import stripe
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from . import auth, db, mailer, provisioner, settings

stripe.api_key = settings.STRIPE_SECRET_KEY

app = FastAPI(title="Screenboard Studio — Storefront")
db.init_db()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline hardening on every public response — and the session read,
    so every template can render the header account widget."""
    request.state.account_email = auth.read_session(
        request.cookies.get(auth.SESSION_COOKIE, ""))
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    return resp


def _set_session(resp, request: Request, email: str) -> None:
    resp.set_cookie(auth.SESSION_COOKIE, auth.make_session(email),
                    max_age=auth.SESSION_DAYS * 86400, httponly=True,
                    samesite="lax", secure=request.url.scheme == "https")


def _login_account(email: str, name: str = "", google_sub: str = "") -> None:
    """First sign-in creates the account; later ones refresh it. Signup and
    sign-in deliberately converge — identity is the verified email."""
    import datetime as dt
    with db.session() as s:
        acct = s.scalar(select(db.Account).where(db.Account.email == email))
        if acct is None:
            acct = db.Account(email=email, name=name, google_sub=google_sub)
            s.add(acct)
        else:
            if name and not acct.name:
                acct.name = name
            if google_sub and not acct.google_sub:
                acct.google_sub = google_sub
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
templates = Jinja2Templates(directory=_here / "templates")

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
    import os
    return {"ok": True, "rev": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local")[:12]}


@app.get("/")
def index(request: Request):
    ready = _ready()
    return templates.TemplateResponse(request, "index.html", {
        "ready": ready,
        "all_ready": all(ready.values()),
    })


@app.get("/checkout/{plan}")
def checkout(plan: str):
    if plan not in PLANS:
        raise HTTPException(404)
    price = PLANS[plan]["price"]()
    if not (settings.STRIPE_SECRET_KEY and price):
        raise HTTPException(503, "Stripe is not configured yet")
    checkout_session = stripe.checkout.Session.create(
        mode=PLANS[plan]["mode"],
        line_items=[{"price": price, "quantity": 1}],
        success_url=f"{settings.BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.BASE_URL}/",
        metadata={"plan": plan},
    )
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
        )
        s.add(purchase)
        if kind == "download":
            purchase.license = db.License()
        s.commit()
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
             purchase.workspace.access_token)
    s.expunge_all()


@app.get("/success")
def success(request: Request, background: BackgroundTasks, session_id: str = ""):
    if not session_id:
        return RedirectResponse("/")
    checkout_session = stripe.checkout.Session.retrieve(session_id)
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


@app.get("/download/{token}")
def download(token: str):
    with db.session() as s:
        lic = s.scalar(select(db.License).where(db.License.token == token))
        if not lic or lic.purchase.status != "PAID":
            raise HTTPException(404)
        if not settings.DOWNLOAD_FILE.exists():
            raise HTTPException(503, "Release artifact is not staged on the server yet")
        lic.downloads_used += 1
        s.commit()
    return FileResponse(settings.DOWNLOAD_FILE, filename=settings.DOWNLOAD_FILE.name,
                        media_type="application/zip")


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


@app.post("/auth/email")
def auth_email(request: Request, email: str = Form(""), mode: str = Form("signin")):
    """Send a magic link. Uniform response for any address; creating vs
    signing in converges at the link — the inbox is the proof."""
    mode = "signup" if mode == "signup" else "signin"
    if not mailer.configured():
        return _auth_page(request, mode)
    email = email.strip().lower()
    if email and "@" in email:
        with db.session() as s:
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
    return RedirectResponse(auth.google_auth_url(auth.make_state()), status_code=303)


@app.get("/auth/google/callback")
def auth_google_callback(request: Request, code: str = "", state: str = ""):
    if not auth.google_configured():
        raise HTTPException(404)
    if not code or not auth.check_state(state):
        return _auth_page(request, "signin",
                          error="Google sign-in didn't complete — try again.")
    try:
        ident = auth.google_identity(code)
    except auth.AuthError as e:
        return _auth_page(request, "signin", error=str(e))
    _login_account(ident["email"], ident["name"], ident["sub"])
    resp = RedirectResponse("/account", status_code=303)
    _set_session(resp, request, ident["email"])
    return resp


@app.post("/auth/logout")
def auth_logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE)
    return resp


@app.get("/account")
def account_page(request: Request):
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
                _ = (p.workspace.status, p.workspace.url,
                     p.workspace.access_token)
        s.expunge_all()
    return templates.TemplateResponse(request, "account.html", {
        "purchase": None, "missed": False, "purchases": purchases,
        "email": email})


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


@app.get("/admin/export")
def admin_export(token: str = ""):
    """Entitlement-data backup: purchases, licenses, workspaces as JSON.
    Exists only when ADMIN_EXPORT_TOKEN is configured; fetch it on a
    schedule and keep the file — losing this data means losing the record
    of who owns what."""
    if not settings.ADMIN_EXPORT_TOKEN:
        raise HTTPException(404)
    if not hmac.compare_digest(token, settings.ADMIN_EXPORT_TOKEN):
        raise HTTPException(404)
    def row(o, cols):
        return {c: (v.isoformat() if hasattr(v := getattr(o, c), "isoformat") else v)
                for c in cols}
    with db.session() as s:
        return {
            "purchases": [row(p, ("id", "kind", "tier", "email",
                                  "stripe_session_id", "stripe_customer_id",
                                  "stripe_subscription_id", "status", "created_at"))
                          for p in s.scalars(select(db.Purchase)).all()],
            "licenses": [row(l, ("id", "purchase_id", "token",
                                 "downloads_used", "created_at"))
                         for l in s.scalars(select(db.License)).all()],
            "workspaces": [row(w, ("id", "purchase_id", "status", "access_token",
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

    if event["type"] == "checkout.session.completed":
        purchase = _fulfill(stripe.checkout.Session.retrieve(event["data"]["object"]["id"]))
        if purchase.kind == "cloud":
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
