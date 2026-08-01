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

from sqlalchemy import select

from . import db, railway as railway_client, settings

MOUNT_PATH = "/workspace"
START_COMMAND = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
NOT_CONFIGURED = ("Railway provisioning is not configured — set "
                  "RAILWAY_API_TOKEN and RAILWAY_PROJECT_ID")


def ensure_workspace_row(s, purchase: db.Purchase) -> db.Workspace:
    """One workspace row per cloud purchase, created PENDING. Idempotent."""
    ws = s.scalar(select(db.Workspace).where(
        db.Workspace.purchase_id == purchase.id))
    if ws is None:
        ws = db.Workspace(purchase_id=purchase.id,
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
    except Exception as e:
        ws.status = "FAILED"
        ws.detail = str(e)[:600]
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
            elif purchase.status == "CANCELED" and ws.status in ("ACTIVE", "FAILED", "PENDING"):
                if ws.railway_service_id and settings.railway_configured():
                    _revoke(s, ws, railway)
                else:
                    ws.status = "REVOKED"
                    ws.detail = "subscription canceled before provisioning"
                    s.commit()
                out["revoked"] += 1
    return out
