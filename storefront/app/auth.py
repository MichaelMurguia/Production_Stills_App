"""Accounts without passwords: signed-cookie sessions, email magic links,
and Google OIDC — all stdlib, all env-gated.

Nothing here ever stores or checks a password. Identity is a verified
email: either Google vouches for it (OIDC) or the inbox does (magic link).
Sessions are HMAC-signed cookies; SESSION_SECRET unset falls back to a
per-boot secret (sessions survive until the next deploy — set the variable
in production).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
import urllib.request

from . import settings

SESSION_COOKIE = "sb_account"
SESSION_DAYS = 30

_EPHEMERAL = secrets.token_bytes(32)


class AuthError(RuntimeError):
    pass


def _secret() -> bytes:
    return settings.SESSION_SECRET.encode() if settings.SESSION_SECRET else _EPHEMERAL


def _sign(msg: str) -> str:
    return hmac.new(_secret(), msg.encode(), hashlib.sha256).hexdigest()


def make_session(email: str) -> str:
    exp = int(time.time()) + SESSION_DAYS * 86400
    payload = f"{email}|{exp}"
    return f"{payload}|{_sign(payload)}"


def read_session(cookie: str) -> str | None:
    """Cookie → email, or None. Constant-time signature check; expiry
    enforced server-side regardless of the cookie's max-age."""
    if not cookie or cookie.count("|") != 2:
        return None
    email, exp, sig = cookie.rsplit("|", 2)
    if not hmac.compare_digest(sig, _sign(f"{email}|{exp}")):
        return None
    try:
        if int(exp) < time.time():
            return None
    except ValueError:
        return None
    return email


# ------------------------------------------------------------- Google OIDC

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"


def google_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def make_state() -> str:
    nonce = secrets.token_urlsafe(16)
    return f"{nonce}.{_sign(nonce)}"


def check_state(state: str) -> bool:
    nonce, _, sig = (state or "").partition(".")
    return bool(nonce) and hmac.compare_digest(sig, _sign(nonce))


def google_auth_url(state: str) -> str:
    q = urllib.parse.urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.BASE_URL}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    return f"{GOOGLE_AUTH}?{q}"


def google_identity(code: str) -> dict:
    """Exchange the code, then read identity from Google's userinfo
    endpoint over TLS — no local JWT validation needed since the claims
    come straight from Google, not from the browser."""
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"{settings.BASE_URL}/auth/google/callback",
        "grant_type": "authorization_code",
    }).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(
                GOOGLE_TOKEN, data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"}),
                timeout=30) as r:
            tok = json.loads(r.read().decode())
        with urllib.request.urlopen(urllib.request.Request(
                GOOGLE_USERINFO,
                headers={"Authorization": f"Bearer {tok['access_token']}"}),
                timeout=30) as r:
            info = json.loads(r.read().decode())
    except Exception as e:
        raise AuthError(f"Google sign-in failed: {e}") from e
    if not info.get("email") or not info.get("email_verified"):
        raise AuthError("Google did not return a verified email")
    return {"email": str(info["email"]).lower(),
            "name": str(info.get("name") or ""),
            "sub": str(info.get("sub") or "")}
