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
import threading

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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


def is_random_slug(name: str) -> bool:
    """True while a studio still wears its auto-assigned adjective-noun
    slug — the account page says "Claim name" then, "Rename" after. A
    buyer who deliberately claims a wordlist pair reads as unclaimed;
    harmless, the button still renames."""
    parts = name.split("-")
    if len(parts) == 3 and parts[2].isdigit():
        parts = parts[:2]
    return len(parts) == 2 and parts[0] in _ADJ and parts[1] in _NOUN


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
        for _ in range(3):  # random slug can race the unique index
            ws = db.Workspace(purchase_id=purchase.id,
                              subdomain=random_subdomain(s),
                              detail="" if settings.railway_configured()
                              else NOT_CONFIGURED)
            s.add(ws)
            try:
                s.commit()
                break
            except IntegrityError:
                s.rollback()
                existing = s.scalar(select(db.Workspace).where(
                    db.Workspace.purchase_id == purchase.id))
                if existing:  # concurrent fulfill won the row itself
                    return existing
        s.refresh(ws)
    return ws


def _is_owner(purchase: db.Purchase) -> bool:
    return (purchase.email or "").strip().lower() in settings.OWNER_EMAILS


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
        variables = {
            "SCREENBOARD_HOME": MOUNT_PATH,
            "SCREENBOARD_ACCESS_TOKEN": ws.access_token,
            # Railway's edge proxies every request; uvicorn must trust its
            # X-Forwarded-Proto so cookies see the real (https) scheme.
            "FORWARDED_ALLOW_IPS": "*",
        }
        if _is_owner(purchase):
            # Debug tools exist only on the store owner's own studios —
            # linked to the account, never shipped to customers.
            variables["SCREENBOARD_DEBUG_TOOLS"] = "1"
        railway.upsert_variables(ws.railway_service_id, variables)
        railway.set_start_command(ws.railway_service_id, START_COMMAND)
        try:
            railway.configure_graceful_deploys(ws.railway_service_id)
        except Exception:
            pass  # a tenant without drain still works; next update retries
        if not ws.url:
            ws.url = f"https://{railway.create_domain(ws.railway_service_id)}"
        if not ws.railway_url:
            ws.railway_url = ws.url
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
    """Point the workspace at its branded address. The address is served
    by the storefront's wildcard router (*.TENANT_DOMAIN_BASE is attached
    to the storefront service ONCE — see docs/DEPLOYMENT.md), so claiming
    or renaming a studio needs no DNS work and no Railway domain calls.
    Per-tenant Railway custom domains are retired; any still attached
    from the earlier design are removed. Non-fatal by design: the
    railway.app URL keeps working regardless."""
    base = settings.TENANT_DOMAIN_BASE
    if not base or not ws.railway_service_id:
        return
    if not ws.subdomain:  # pre-naming workspaces get their slug here
        for _ in range(3):
            ws.subdomain = random_subdomain(s)
            try:
                s.commit()
                break
            except IntegrityError:
                s.rollback()
    try:
        for d in railway.list_custom_domains(ws.railway_service_id):
            railway.delete_custom_domain(d["id"])
        ws.detail = ""
    except Exception as e:
        ws.detail = f"legacy custom-domain cleanup pending: {str(e)[:400]}"
    new_url = f"https://{ws.subdomain}.{base}"
    if ws.url != new_url:
        ws.url = new_url
        ws.domain_live = 0  # the new address re-verifies before doors use it
    s.commit()


def _revoke(s, ws: db.Workspace, railway) -> None:
    """Subscription gone → service deleted. REVOKED is only ever stamped
    after the delete succeeds — a terminal status on a still-running
    service would host it unbilled forever. The workspace row (and its
    token) is kept as the record of what existed; the subdomain is
    released so the name can be claimed again (REVOKED rows must not
    squat names the router already serves as unclaimed)."""
    try:
        if ws.railway_service_id:
            railway.delete_service(ws.railway_service_id)
        ws.status = "REVOKED"
        ws.subdomain = ""
        ws.detail = "subscription canceled — service deleted"
    except Exception as e:
        ws.detail = f"revoke failed, will retry: {str(e)[:500]}"
    s.commit()


def update_tenants(railway=railway_client) -> dict:
    """Push the current product build to every ACTIVE tenant studio —
    the cloud edition sells 'updates land the day they ship', and tenant
    services otherwise stay frozen on the build they were provisioned
    with. Per-service failures are recorded, never raised; a studio that
    misses an update catches it on the next run."""
    import os
    sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "")
    out = {"updated": [], "failed": [], "commit": sha}
    if not settings.railway_configured():
        return out
    with db.session() as s:
        active = s.scalars(select(db.Workspace).where(
            db.Workspace.status == "ACTIVE")).all()
        for ws in active:
            if not ws.railway_service_id:
                continue
            try:
                try:  # existing tenants gain graceful drain before the build
                    railway.configure_graceful_deploys(ws.railway_service_id)
                except Exception:
                    pass
                railway.deploy_latest(ws.railway_service_id, sha)
                out["updated"].append(ws.subdomain or ws.railway_service_id)
            except Exception as e:
                ws.detail = f"update failed, will retry: {str(e)[:400]}"
                s.commit()
                out["failed"].append(ws.subdomain or ws.railway_service_id)
    return out


# reconcile() is spawned from startup, /success, the webhook, and studio
# naming — often concurrently. Every step is idempotent, but two runs
# interleaving through _provision can still double-create Railway
# resources; one run at a time is enough, so overlapping calls just skip.
_reconcile_lock = threading.Lock()


def reconcile(railway=railway_client) -> dict:
    """Converge workspaces toward the purchases table. Returns a small
    summary for logs/ops. Never raises."""
    out = {"provisioned": 0, "revoked": 0, "pending": 0, "failed": 0}
    if not _reconcile_lock.acquire(blocking=False):
        return {**out, "skipped": "reconcile already running"}
    try:
        return _reconcile(railway, out)
    finally:
        _reconcile_lock.release()


def _reconcile(railway, out: dict) -> dict:
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
                    if not ws.railway_url:
                        try:  # backfill the reliable door for older rows
                            doors = railway.service_domains(ws.railway_service_id)
                            if doors:
                                ws.railway_url = f"https://{doors[0]}"
                                s.commit()
                        except Exception:
                            pass
                    _ensure_custom_domain(s, ws, purchase, railway)
                    if _is_owner(purchase):
                        try:  # standing upgrade: owner studios gain the flag
                            railway.upsert_variables(ws.railway_service_id, {
                                "SCREENBOARD_DEBUG_TOOLS": "1"})
                        except Exception:
                            pass  # next reconcile retries
                    # Doors must open before they are offered: the branded
                    # address unlocks in the UI only once it provably
                    # serves. Probe is read-only — never a re-attach.
                    if (not ws.domain_live and ws.url
                            and ws.url != ws.railway_url
                            and _domain_serves(ws.url.replace("https://", ""))):
                        ws.domain_live = 1
                        s.commit()
            elif (purchase.status in ("CANCELED", "REFUNDED")
                  and ws.status in ("ACTIVE", "FAILED", "PENDING")):
                if ws.railway_service_id:
                    if settings.railway_configured():
                        _revoke(s, ws, railway)
                    else:
                        # A real service exists but Railway credentials are
                        # missing — REVOKED here would be terminal while the
                        # studio kept running unbilled. Stay put, say why.
                        ws.detail = ("cancel pending — " + NOT_CONFIGURED)
                        s.commit()
                else:
                    ws.status = "REVOKED"
                    ws.subdomain = ""
                    ws.detail = "subscription canceled before provisioning"
                    s.commit()
                if ws.status == "REVOKED":
                    out["revoked"] += 1
    return out
