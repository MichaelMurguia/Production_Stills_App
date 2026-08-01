from __future__ import annotations

from pathlib import Path

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from . import db, settings

stripe.api_key = settings.STRIPE_SECRET_KEY

app = FastAPI(title="Screenboard Studio — Storefront")
db.init_db()

_here = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=_here / "static"), name="static")
templates = Jinja2Templates(directory=_here / "templates")

PLANS = {
    "download": {"mode": "payment", "price": lambda: settings.STRIPE_PRICE_DOWNLOAD},
    "cloud": {"mode": "subscription", "price": lambda: settings.STRIPE_PRICE_CLOUD},
}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "stripe_ready": bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRICE_DOWNLOAD
                             and settings.STRIPE_PRICE_CLOUD),
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


def _fulfill(checkout_session) -> db.Purchase:
    """Record a paid Checkout session, creating the license for downloads.
    Idempotent on stripe_session_id — safe to call from both the webhook and
    the /success page."""
    with db.session() as s:
        existing = s.scalar(select(db.Purchase).where(
            db.Purchase.stripe_session_id == checkout_session.id))
        if existing:
            s.expunge(existing)
            _ = existing.license and existing.license.token  # load before detach
            return existing

        plan = (checkout_session.metadata or {}).get("plan") or (
            "cloud" if checkout_session.mode == "subscription" else "download")
        purchase = db.Purchase(
            kind=plan,
            email=(checkout_session.customer_details or {}).get("email") or "",
            stripe_session_id=checkout_session.id,
            stripe_customer_id=checkout_session.customer or "",
            stripe_subscription_id=checkout_session.subscription or "",
        )
        s.add(purchase)
        if plan == "download":
            purchase.license = db.License()
        s.commit()
        s.refresh(purchase)
        if purchase.license:
            _ = purchase.license.token
        s.expunge_all()
        return purchase


@app.get("/success")
def success(request: Request, session_id: str = ""):
    if not session_id:
        return RedirectResponse("/")
    checkout_session = stripe.checkout.Session.retrieve(session_id)
    if checkout_session.payment_status not in ("paid", "no_payment_required"):
        return templates.TemplateResponse(request, "success.html",
                                          {"state": "PENDING", "purchase": None})
    purchase = _fulfill(checkout_session)
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
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "invalid signature")

    if event["type"] == "checkout.session.completed":
        _fulfill(stripe.checkout.Session.retrieve(event["data"]["object"]["id"]))
    elif event["type"] == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]
        with db.session() as s:
            purchase = s.scalar(select(db.Purchase).where(
                db.Purchase.stripe_subscription_id == sub_id))
            if purchase:
                purchase.status = "CANCELED"
                s.commit()
    return {"received": True}
