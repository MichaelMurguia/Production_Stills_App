"""Cloud workspace provisioning — purchases in, workspaces out.

The `purchases` table is the entitlement truth: every PAID cloud purchase
deserves an ACTIVE workspace; every CANCELED one gets its workspace
revoked. `reconcile()` converges reality toward that statement and is safe
to run any time, from anywhere (startup, after fulfillment, after webhook
events) — every step is idempotent and every failure lands on the
workspace row as a stated detail, never a crash.

The Railway client is injected so tests drive the whole machine with a
fake; missing Railway config is a first-class state (workspaces queue as
PENDING with the condition stated).
"""
from __future__ import annotations

import re
import secrets

from sqlalchemy import select

from . import db, railway as railway_client, settings

MOUNT_PATH = "/workspace"

# --- studio naming --------------------------------------------------------
# A studio's subdomain is buyer-claimed (the Slack model); until claimed it
# carries a random two-word slug — never the bare purchase number, which
# would publish the customer count in certificate-transparency logs.

RESERVED_SUBDOMAINS = {
    "www", "api", "app", "apps", "mail", "smtp", "imap", "admin", "store",
    "shop", "status", "docs", "help", "support", "blog", "cdn", "static",
    "assets", "studio", "studios", "screenboard", "billing", "account",
    "accounts", "auth", "login", "signup", "download", "downloads", "dev",
    "staging", "test", "demo", "ftp", "ns1", "ns2",
}

_ADJ = ("amber", "brass", "cedar", "cobalt", "copper", "crimson", "ember",
        "flint", "gilded", "granite", "indigo", "iron", "ivory", "jade",
        "lunar", "mesa", "noble", "ochre", "onyx", "opal", "quartz", "raven",
        "saffron", "sable", "silver", "slate", "solar", "sterling", "stone",
        "summit", "timber", "topaz", "umber", "velvet", "walnut", "winter")
_NOUN = ("anvil", "atlas", "banner", "beacon", "canyon", "circuit", "comet",
         "compass", "crane", "delta", "engine", "falcon", "forge", "frame",
         "gantry", "hangar", "kestrel", "lantern", "ledger", "loom",
         "meadow", "orbit", "otter", "panther", "pillar", "prairie",
         "quarry", "ridge", "rocket", "saddle", "signal", "spur", "vault",
         "willow", "wren")

_SUBDOMAIN_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])\Z")


def valid_subdomain(name: str) -> bool:
    return bool(_SUBDOMAIN_RE.fullmatch(name)) and name not in RESERVED_SUBDOMAINS


def random_subdomain(s) -> str:
    """An unclaimed studio's slug: adjective-noun, digits appended only on
    collision. Checked against the table so it is unique at assignment."""
    for _ in range(64):
        slug = f"{secrets.choice(_ADJ)}-{secrets.choice(_NOUN)}"
        if _ != 0:
            slug += f"-{secrets.randbelow(90) + 10}"
        taken = s.scalar(select(db.Workspace).where(
            db.Workspace.subdomain == slug))
        if not taken and slug not in RESERVED_SUBDOMAINS:
            return slug
    return f"studio-{secrets.token_hex(4)}"
START_COMMAND = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
NOT_CONFIGURED = ("Railway provisioning is not configured — set "
                  "RAILWAY_PROJECT_TOKEN (from the tenants project's "
                  "Settings → Tokens)")


def ensure_workspace_row(s, purchase: db.Purchase) -> db.Workspace:
    """One workspace row per cloud purchase, created PENDING. Idempotent."""
    ws = s.scalar(select(db.Workspace).where(
        db.Workspace.purchase_id == purchase.id))
    if ws is None:
        ws = db.Workspace(purchase_id=purchase.id,
                          subdomain=random_subdomain(s),
                          detail="" if settings.railway_configured()
                          else NOT_CONFIGURED)
        s.add(ws)
        s.commit()
        s.refresh(ws)
    return ws


def _provision(s, ws: db.Workspace, purchase: db.Purchase, railway) -> None:
    """Build the tenant service. Any exception marks the row FAILED with
    the error; reconcile retries on its next run."""
    try:
        name = f"tenant-{purchase.id}-{purchase.tier or 'personal'}"
        if not ws.railway_service_id:
            ws.railway_service_id = railway.create_service(name)
            s.commit()
        if not ws.railway_volume_id:
            ws.railway_volume_id = railway.create_volume(
                ws.railway_service_id, MOUNT_PATH)
            s.commit()
        railway.upsert_variables(ws.railway_service_id, {
            "SCREENBOARD_HOME": MOUNT_PATH,
            "SCREENBOARD_ACCESS_TOKEN": ws.access_token,
        })
        railway.set_start_command(ws.railway_service_id, START_COMMAND)
        if not ws.url:
            ws.url = f"https://{railway.create_domain(ws.railway_service_id)}"
        railway.redeploy(ws.railway_service_id)
        ws.status = "ACTIVE"
        ws.detail = ""
        s.commit()
        _ensure_custom_domain(s, ws, purchase, railway)
        return
    except Exception as e:
        ws.status = "FAILED"
        ws.detail = str(e)[:600]
    s.commit()


def _domain_serves(domain: str) -> bool:
    """Does the branded address actually answer over TLS? A domain can be
    'attached' at Railway yet unverified (e.g. attached while DNS pointed
    elsewhere) — the edge then 404s and no certificate exists. Probing the
    tenant's open healthz is the truth."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"https://{domain}/api/healthz",
                                    timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _ensure_custom_domain(s, ws: db.Workspace, purchase: db.Purchase,
                          railway) -> None:
    """Upgrade the workspace to studio-<n>.<TENANT_DOMAIN_BASE> when the
    base is configured. Non-fatal by design: an ACTIVE workspace never
    regresses over a domain problem — the railway.app URL keeps working
    and the issue lands in detail."""
    base = settings.TENANT_DOMAIN_BASE
    if not base or not ws.railway_service_id:
        return
    if not ws.subdomain:  # pre-naming workspaces get their slug here
        ws.subdomain = random_subdomain(s)
        s.commit()
    domain = f"{ws.subdomain}.{base}"
    if ws.url == f"https://{domain}":
        return
    try:
        # SWAP, never accumulate: Railway caps custom domains per service,
        # so superseded ones are deleted before the new attach. The
        # *.up.railway.app address always remains as the fallback.
        existing = railway.list_custom_domains(ws.railway_service_id)
        if any(d.get("domain") == domain for d in existing):
            if _domain_serves(domain):
                ws.url = f"https://{domain}"
                ws.detail = ""
                s.commit()
                return
            # Attached but not serving — a stuck verification (attached
            # under wrong DNS). Fall through: delete and re-attach fresh,
            # which restarts verification against current DNS.
        for d in existing:
            railway.delete_custom_domain(d["id"])
        dns_target = railway.create_custom_domain(ws.railway_service_id, domain)
        ws.url = f"https://{domain}"
        ws.detail = (f"custom domain attached; wildcard *.{base} must point "
                     f"at {dns_target}" if dns_target else "")
    except Exception as e:
        detail = str(e)
        if "already" in detail.lower():  # attached on a prior run — done
            ws.url = f"https://{domain}"
            ws.detail = ""
        else:
            ws.detail = f"custom domain pending: {detail[:400]}"
    s.commit()


def _revoke(s, ws: db.Workspace, railway) -> None:
    """Subscription gone → service deleted. The workspace row (and its
    token) is kept as the record of what existed."""
    try:
        if ws.railway_service_id:
            railway.delete_service(ws.railway_service_id)
        ws.status = "REVOKED"
        ws.detail = "subscription canceled — service deleted"
    except Exception as e:
        ws.detail = f"revoke failed, will retry: {str(e)[:500]}"
    s.commit()


def reconcile(railway=railway_client) -> dict:
    """Converge workspaces toward the purchases table. Returns a small
    summary for logs/ops. Never raises."""
    out = {"provisioned": 0, "revoked": 0, "pending": 0, "failed": 0}
    with db.session() as s:
        cloud = s.scalars(select(db.Purchase).where(
            db.Purchase.kind == "cloud")).all()
        for purchase in cloud:
            ws = ensure_workspace_row(s, purchase)
            if purchase.status == "PAID" and ws.status in ("PENDING", "FAILED"):
                if not settings.railway_configured():
                    ws.detail = NOT_CONFIGURED
                    s.commit()
                    out["pending"] += 1
                    continue
                _provision(s, ws, purchase, railway)
                out["provisioned" if ws.status == "ACTIVE" else "failed"] += 1
            elif purchase.status == "PAID" and ws.status == "ACTIVE":
                # Standing upgrades for live workspaces (e.g. a custom
                # domain base configured after they were built).
                if settings.railway_configured():
                    _ensure_custom_domain(s, ws, purchase, railway)
            elif purchase.status == "CANCELED" and ws.status in ("ACTIVE", "FAILED", "PENDING"):
                if ws.railway_service_id and settings.railway_configured():
                    _revoke(s, ws, railway)
                else:
                    ws.status = "REVOKED"
                    ws.detail = "subscription canceled before provisioning"
                    s.commit()
                out["revoked"] += 1
    return out
