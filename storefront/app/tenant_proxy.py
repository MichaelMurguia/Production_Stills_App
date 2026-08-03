"""Wildcard tenant router — one DNS record for every studio, forever.

`*.TENANT_DOMAIN_BASE` points at the storefront service (a single wildcard
custom domain, attached once in the Railway dashboard — see
docs/DEPLOYMENT.md). This ASGI wrapper inspects the Host of every request:
the storefront's own hosts pass straight through; a claimed studio
subdomain is reverse-proxied to that tenant's *.up.railway.app service.

This retires per-tenant DNS records and per-tenant Railway custom domains
entirely. Claiming or renaming a studio is live the moment the row
commits — no DNS to propagate, no certificate to issue, no domain caps,
no churn.

Safety: the proxy only ever forwards to a host under .up.railway.app taken
from the workspace row's railway_url — never to a user-influenced host,
and never to a branded address (which would loop back here).
"""
from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import jinja2
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from . import db, provisioner, settings

# Hop-by-hop headers never cross a proxy (RFC 9110 §7.6.1); host is
# recomputed for the upstream URL.
_HOP = {b"connection", b"keep-alive", b"proxy-authenticate",
        b"proxy-authorization", b"te", b"trailers", b"transfer-encoding",
        b"upgrade", b"host"}

# The router's own pages (STORE_ROUTER_PLAN 2026-08-01) render outside
# FastAPI, so they get their own tiny Jinja env over the same templates.
# They serve on TENANT hostnames — templates must link every asset and
# href absolutely to the store host, never relatively.
_jinja = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).resolve().parent / "templates"),
    autoescape=True)

# Last time each studio's upstream answered, by subdomain — in-process
# only, so the LAST ANSWERED row simply drops after a storefront restart
# rather than ever guessing (T2's rule: no data, no row).
_last_answered: dict[str, float] = {}


def _ago(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s} SECOND{'S' if s != 1 else ''} AGO"
    m = s // 60
    if m < 60:
        return f"{m} MINUTE{'S' if m != 1 else ''} AGO"
    return f"{m // 60} HOUR{'S' if m // 60 != 1 else ''} AGO"


def _studio_name(sub: str) -> str:
    return " ".join(w.capitalize() for w in sub.split("-") if w) or sub


async def _page(send, status: int, body: bytes,
                extra_headers: list | None = None) -> None:
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"text/html; charset=utf-8"),
                            (b"content-length", str(len(body)).encode())]
                + (extra_headers or [])})
    await send({"type": "http.response.body", "body": body})


def _render(template: str, **ctx) -> bytes:
    return _jinja.get_template(template).render(
        base_url=settings.BASE_URL.rstrip("/"), **ctx).encode()


class TenantProxy:
    """ASGI wrapper: tenant hosts are proxied, everything else delegates
    to the wrapped storefront app. `transport` is injectable for tests."""

    def __init__(self, app, transport: httpx.AsyncBaseTransport | None = None):
        self.app = app
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    # -- routing -----------------------------------------------------------

    def _target(self, host: str):
        """None → not a tenant host, pass through. '' → a studio host with
        nothing to serve (stated 404). Otherwise the upstream base URL."""
        base = settings.TENANT_DOMAIN_BASE
        host = (host or "").split(":", 1)[0].lower()
        if not base or not host.endswith("." + base):
            return None
        sub = host[: -(len(base) + 1)]
        if (not sub or "." in sub
                or sub in provisioner.RESERVED_SUBDOMAINS):
            return None
        with db.session() as s:
            row = s.scalar(select(db.Workspace).join(db.Purchase).where(
                db.Workspace.subdomain == sub,
                db.Workspace.status == "ACTIVE",
                db.Purchase.status == "PAID"))
            target = (row.railway_url or "") if row else ""
        # urlsplit's hostname, not string surgery — userinfo/query tricks
        # like https://evil.com?x=.up.railway.app must never pass.
        try:
            hostname = urlsplit(target).hostname or ""
        except ValueError:
            hostname = ""
        if target.startswith("https://") and hostname.endswith(".up.railway.app"):
            return target.rstrip("/")
        return ""

    def _pending(self, sub: str):
        """A PAID studio that owns this name but is not ACTIVE yet — the
        coming-soon case (2026-08-04). Returns its status, or None: a
        paying owner must never be told their own address does not
        exist."""
        with db.session() as s:
            row = s.scalar(select(db.Workspace).join(db.Purchase).where(
                db.Workspace.subdomain == sub,
                db.Workspace.status.in_(("PENDING", "FAILED")),
                db.Purchase.status == "PAID"))
            return row.status if row else None

    def _renamed_to(self, sub: str):
        """The current subdomain of an ACTIVE studio that last released
        `sub`, or None. Only consulted when `sub` itself matched nothing —
        a claimed name always wins over a forward."""
        with db.session() as s:
            row = s.scalar(select(db.Workspace).join(db.Purchase).where(
                db.Workspace.prev_subdomain == sub,
                db.Workspace.subdomain != "",
                db.Workspace.status == "ACTIVE",
                db.Purchase.status == "PAID"))
            return row.subdomain if row else None

    # -- proxying ----------------------------------------------------------

    def _client_for(self) -> httpx.AsyncClient:
        if self._client is None:
            # Renders inside a studio legitimately run for minutes — the
            # read timeout must outlive the slowest render call.
            self._client = httpx.AsyncClient(
                transport=self._transport, follow_redirects=False,
                timeout=httpx.Timeout(connect=15, read=600, write=600,
                                      pool=15))
        return self._client

    @staticmethod
    def _host_of(scope) -> str:
        for k, v in scope.get("headers") or ():
            if k.lower() == b"host":
                return v.decode("latin-1")
        return ""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            # The proxy speaks plain HTTP only; a websocket reaching a
            # tenant host must not fall through to the storefront app
            # (cross-host confusion). Refuse the handshake outright.
            host = self._host_of(scope)
            if await run_in_threadpool(self._target, host) is not None:
                await send({"type": "websocket.close", "code": 1008})
                return
            await self.app(scope, receive, send)
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        host = self._host_of(scope)
        # _target does sync DB work — keep it off the event loop.
        target = await run_in_threadpool(self._target, host)
        if target is None:
            await self.app(scope, receive, send)
            return
        sub = host.split(":", 1)[0].lower().split(".", 1)[0]
        if not target:
            # A renamed studio's released name forwards to its new address
            # while unclaimed — stale doors and old bookmarks keep working
            # (2026-08-04). The moment someone claims the name, they own it.
            moved = await run_in_threadpool(self._renamed_to, sub)
            if moved:
                path = (scope.get("raw_path") or scope["path"].encode("latin-1")).decode("latin-1")
                q = scope.get("query_string") or b""
                loc = f"https://{moved}.{settings.TENANT_DOMAIN_BASE}{path}" + (
                    "?" + q.decode("latin-1") if q else "")
                await send({"type": "http.response.start", "status": 302,
                            "headers": [(b"location", loc.encode("latin-1")),
                                        (b"x-robots-tag", b"noindex")]})
                await send({"type": "http.response.body", "body": b""})
                return
            # Claimed and paid, workspace still building: a receipt, not a
            # 404 (user request 2026-08-04). FAILED reads the same way to
            # the owner — reconcile retries on its own — and never leaks
            # infrastructure detail onto a customer's address.
            pending = await run_in_threadpool(self._pending, sub)
            if pending:
                await _page(send, 503, _render(
                    "router_coming_soon.html",
                    host=host.split(":", 1)[0],
                    studio_name=_studio_name(sub),
                    state="SETTING UP" if pending == "PENDING"
                          else "SETTING UP — RETRYING"),
                    extra_headers=[(b"retry-after", b"15"),
                                   (b"x-robots-tag", b"noindex")])
                return
            # The one failure page that sells (T1): a stranger, a typo, or
            # someone guessing — full store chrome, the address as the H1.
            await _page(send, 404, _render(
                "router_unclaimed.html", host=host.split(":", 1)[0], sub=sub),
                extra_headers=[(b"x-robots-tag", b"noindex")])
            return
        await self._forward(scope, receive, send, target, host, sub)

    async def _forward(self, scope, receive, send, target: str, host: str,
                       sub: str = ""):
        path = scope.get("raw_path") or scope["path"].encode("latin-1")
        url = target + path.decode("latin-1")
        if scope.get("query_string"):
            url += "?" + scope["query_string"].decode("latin-1")
        # Drop hop-by-hop headers AND any inbound x-forwarded-* — a client
        # could otherwise smuggle a spoofed chain straight to the tenant.
        # The proxy is the authority on forwarding facts.
        headers = [(k, v) for k, v in scope["headers"]
                   if k.lower() not in _HOP
                   and not k.lower().startswith(b"x-forwarded-")]
        client = scope.get("client")
        headers += [(b"x-forwarded-host", host.encode("latin-1")),
                    (b"x-forwarded-proto", b"https"),
                    # Proof-of-router: Railway's edge cannot set this, so
                    # the tenant app can tell OUR proxy from a direct hit
                    # and never redirect proxied traffic (loop guard).
                    (b"x-screenboard-router", b"1")]
        if client:
            headers.append((b"x-forwarded-for",
                            str(client[0]).encode("latin-1")))
        has_body = any(k.lower() in (b"content-length", b"transfer-encoding")
                       for k, _ in scope["headers"])

        async def body():
            while True:
                msg = await receive()
                if msg["type"] != "http.request":
                    return
                if msg.get("body"):
                    yield msg["body"]
                if not msg.get("more_body"):
                    return

        client = self._client_for()
        try:
            req = client.build_request(
                scope["method"], url, headers=headers,
                content=body() if has_body else None)
            resp = await client.send(req, stream=True)
        except httpx.HTTPError:
            # A paying customer locked out mid-session (T2): reassure
            # about the work first, state what is known, recheck honestly.
            # 503 + Retry-After — this is temporary and says so.
            seen = _last_answered.get(sub)
            await _page(send, 503, _render(
                "router_unreachable.html",
                host=host.split(":", 1)[0],
                studio_name=_studio_name(sub),
                last_answered=_ago(time.time() - seen) if seen else ""),
                extra_headers=[(b"retry-after", b"15"),
                               (b"x-robots-tag", b"noindex")])
            return
        # A tenant mid-redeploy answers through Railway's edge with the
        # platform's own bare error page — a 502/503, or a 404 stamped
        # x-railway-fallback while the internal domain re-attaches. A
        # customer must never see raw infrastructure on their branded
        # address (flashed on a12-oxcart during the .60 fleet update), so
        # browser navigations get the styled unreachable page instead.
        # The app's own 404s carry no fallback stamp and pass through;
        # non-HTML clients keep the true upstream status.
        accept = next((v for k, v in scope["headers"]
                       if k.lower() == b"accept"), b"").decode("latin-1", "replace")
        edge_error = (resp.status_code in (502, 503)
                      or (resp.status_code == 404
                          and resp.headers.get("x-railway-fallback") == "true"))
        if (edge_error and scope["method"] in ("GET", "HEAD")
                and "text/html" in accept):
            await resp.aclose()
            seen = _last_answered.get(sub)
            await _page(send, 503, _render(
                "router_unreachable.html",
                host=host.split(":", 1)[0],
                studio_name=_studio_name(sub),
                last_answered=_ago(time.time() - seen) if seen else ""),
                extra_headers=[(b"retry-after", b"15"),
                               (b"x-robots-tag", b"noindex")])
            return
        _last_answered[sub] = time.time()
        try:
            # Private studios are never crawlable — every proxied tenant
            # response says so (SEO pass, 2026-08-03).
            await send({"type": "http.response.start",
                        "status": resp.status_code,
                        "headers": [(k, v) for k, v in resp.headers.raw
                                    if k.lower() not in _HOP]
                        + [(b"x-robots-tag", b"noindex")]})
            if resp.is_stream_consumed:
                # Content arrived preloaded (mock transports, cached
                # responses) — a second stream would raise.
                await send({"type": "http.response.body",
                            "body": resp.content})
            else:
                # aiter_raw keeps upstream bytes exactly as sent, so the
                # content-encoding/length headers above stay truthful.
                async for chunk in resp.aiter_raw():
                    if chunk:
                        await send({"type": "http.response.body",
                                    "body": chunk, "more_body": True})
                await send({"type": "http.response.body", "body": b""})
        finally:
            await resp.aclose()
