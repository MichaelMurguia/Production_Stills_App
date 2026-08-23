"""Wrap the credentials in settings.json so the file alone is not enough.

Added 2026-08-23 after the audit that asked whether pasting an API key into
this app is safe for the person doing it. It mostly was — the key never
echoes from a route, never rides a backup, never reaches the customer
download — but it sat on disk in plaintext, and `SCREENBOARD_HOME` on a
standalone install IS the extracted folder. Nothing tells a customer where
to unzip, so that folder is routinely Downloads, Desktop, or Documents —
all OneDrive-synced by default on Windows 11. A plaintext key there syncs
to Microsoft's cloud and onto every other device on the account.

That is the threat this closes: **the file being copied somewhere.** It is
NOT a defence against someone who already has the machine and the user
account — the OS user remains the boundary, exactly as SECURITY.md says.

Two wraps, chosen by where we are running:

  dpapi  Windows standalone. CryptProtectData with no entropy, so the
         ciphertext is bound to the Windows user account and is inert on
         any other machine or profile. Stdlib ctypes, no dependency.

  key    Cloud studio. AES-GCM under a per-tenant key held in the Railway
         variable SCREENBOARD_SECRET_KEY — deliberately NOT on the volume,
         so a volume snapshot, a disk leak, or a restore onto another
         service yields nothing usable.

Anything else (macOS, Linux desktop) stores plaintext and SAYS SO through
`status()`. A wrap we cannot actually perform must never be reported as
one; a false green here is worse than a stated gap.

What this explicitly does not do: protect a hosted studio's key from us.
We hold the Railway variable. Encryption whose key we also hold is not a
defence against the key's holder, and the honest handling of that is
disclosure, not a stronger-sounding algorithm.
"""
from __future__ import annotations

import base64
import os
import sys

# A wrapped value is tagged so unwrap can tell it from a plaintext key that
# predates this, and so a value wrapped by one scheme is never fed to the
# other. Untagged input is returned as-is — that is the migration path.
PREFIX = "enc:"
_ENV_KEY = "SCREENBOARD_SECRET_KEY"


def _dpapi_available() -> bool:
    return sys.platform == "win32"


def _env_key() -> bytes:
    """The tenant's AES key, base64 or raw, from the environment only."""
    raw = (os.environ.get(_ENV_KEY) or "").strip()
    if not raw:
        return b""
    try:
        k = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except Exception:
        k = raw.encode("utf-8")
    return k if len(k) in (16, 24, 32) else b""


def scheme() -> str:
    """Which wrap applies here. The env key wins: a cloud studio runs on
    Linux anyway, but if both were ever available the explicit, operator-
    provisioned key is the one that was chosen on purpose."""
    if _env_key():
        return "key"
    if _dpapi_available():
        return "dpapi"
    return "none"


# ------------------------------------------------------------------ dpapi

def _blob(data: bytes):
    import ctypes
    import ctypes.wintypes as w

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", w.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    # The buffer must outlive the struct — returned so the caller holds it.
    return BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _dpapi(data: bytes, unprotect: bool) -> bytes:
    import ctypes

    class BLOB(ctypes.Structure):
        pass

    src, _keep = _blob(data)
    out = type(src)()
    fn = (ctypes.windll.crypt32.CryptUnprotectData if unprotect
          else ctypes.windll.crypt32.CryptProtectData)
    args = ([ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)]
            if not unprotect else
            [ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)])
    if not fn(*args):
        raise OSError(ctypes.GetLastError())
    return ctypes.string_at(out.pbData, out.cbData)


# -------------------------------------------------------------------- aes

def _aes(data: bytes, key: bytes, decrypt: bool) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if decrypt:
        return AESGCM(key).decrypt(data[:12], data[12:], None)
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, data, None)


# ------------------------------------------------------------------- api

def protect(value: str) -> str:
    """Wrap one secret. Returns the value unchanged when no wrap is
    available — a caller must be able to store a key on any platform."""
    v = str(value or "")
    if not v or v.startswith(PREFIX):
        return v
    s = scheme()
    try:
        if s == "key":
            blob = _aes(v.encode("utf-8"), _env_key(), decrypt=False)
        elif s == "dpapi":
            blob = _dpapi(v.encode("utf-8"), unprotect=False)
        else:
            return v
    except Exception:
        # Never lose a credential to a wrap failure. The user pasted it;
        # storing it readable beats refusing to store it at all.
        return v
    return f"{PREFIX}{s}:" + base64.b64encode(blob).decode("ascii")


def unprotect(value: str) -> str:
    """Unwrap, or pass through. An untagged value is a pre-2026-08-23 key
    and is returned as-is so nothing breaks on upgrade."""
    v = str(value or "")
    if not v.startswith(PREFIX):
        return v
    try:
        _, s, payload = v.split(":", 2)
        blob = base64.b64decode(payload)
        if s == "key":
            return _aes(blob, _env_key(), decrypt=True).decode("utf-8")
        if s == "dpapi":
            return _dpapi(blob, unprotect=True).decode("utf-8")
    except Exception:
        # Wrong machine, wrong profile, rotated or missing tenant key. The
        # credential is unreadable HERE; report it absent so the UI shows
        # the "no key configured" gate and the user re-enters it, rather
        # than sending ciphertext to a provider as if it were a key.
        return ""
    return ""


def is_wrapped(value: str) -> bool:
    return str(value or "").startswith(PREFIX)


def status() -> dict:
    """What the UI is allowed to claim. `at_rest` is the plain sentence to
    show a user — never a green tick that outruns the facts."""
    s = scheme()
    return {
        "scheme": s,
        "wrapped": s != "none",
        "at_rest": {
            "dpapi": "Encrypted by Windows and tied to your user account — "
                     "the file is unreadable on another machine or profile.",
            "key": "Encrypted with this studio's key, which is held outside "
                   "the storage volume.",
            "none": "Stored as plain text. Anyone who can read this "
                    "install's folder can read the key.",
        }[s],
    }
