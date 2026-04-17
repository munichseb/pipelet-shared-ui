"""Pipelet cross-portal SSO — sign/verify click-through tokens.

Used by the app-switcher tiles. Source portal (where the user is logged in)
signs a short-lived token carrying {email, exp, aud}. Target portal verifies
the signature with the shared secret, looks up the user by email in its
OWN schema, mints its OWN session, and sets its OWN cookie.

No shared session store. No shared cookie. Each portal stays its own
authentication boundary — the token just replaces a magic-link email for
the one-click handoff.

Token format (JWT-lite, minimal deps):
    base64url(json_body) + '.' + base64url(hmac_sha256)

Body fields:
    email : str         the user's email on the source portal
    exp   : int         unix timestamp, token expires after this
    aud   : str         target portal id (e.g. "driver") — binds the token
                        to a specific destination, preventing cross-tile replay
    iss   : str         source portal id (e.g. "sim") — for audit / logging

TTL is intentionally very short (default 30s) since the link is clicked
immediately after issuance.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

DEFAULT_TTL_SECONDS = 30


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    # Restore padding
    padded = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def sign(email: str, aud: str, secret: str, iss: str = "", ttl: int = DEFAULT_TTL_SECONDS) -> str:
    """Create a signed SSO token for ``email`` destined for portal ``aud``."""
    if not secret:
        raise ValueError("sso.sign: empty secret")
    body = {
        "email": (email or "").strip().lower(),
        "aud": aud,
        "iss": iss,
        "exp": int(time.time()) + int(ttl),
    }
    body_json = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body_b64 = _b64u_encode(body_json)
    mac = hmac.new(secret.encode("utf-8"), body_b64.encode("ascii"), hashlib.sha256).digest()
    return body_b64 + "." + _b64u_encode(mac)


def verify(token: str, aud: str, secret: str) -> Optional[dict]:
    """Verify ``token`` is valid for audience ``aud``. Returns body dict or None.

    Returns None (never raises) for any failure mode: malformed, bad signature,
    expired, wrong audience. Callers treat None as "not authenticated".
    """
    if not token or not secret or not aud:
        return None
    try:
        body_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        return None
    try:
        expected = hmac.new(secret.encode("utf-8"), body_b64.encode("ascii"), hashlib.sha256).digest()
        given = _b64u_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected, given):
        return None
    try:
        body = json.loads(_b64u_decode(body_b64).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    if body.get("aud") != aud:
        return None
    if int(body.get("exp", 0)) < int(time.time()):
        return None
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return None
    body["email"] = email
    return body
