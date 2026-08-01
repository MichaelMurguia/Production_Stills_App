from __future__ import annotations

from pathlib import Path

import stripe
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from . import db, provisioner, settings

stripe.api_key = settings.STRIPE_SECRET_KEY

app = FastAPI(title="Screenboard Studio — Storefront")
db.init_db()


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
