"""Retell webhook / custom-function signature verification.

Header: ``X-Retell-Signature: v=<unix ms>,d=<hex>`` where
d = HMAC-SHA256(key=RETELL_API_KEY, msg=raw_body + timestamp). Reject if >5 min old.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time

from fastapi import HTTPException, Request

from app.settings import get_settings

log = logging.getLogger(__name__)
_SIG_RE = re.compile(r"^v=(\d+),d=([0-9a-fA-F]+)$")
TOLERANCE_MS = 5 * 60 * 1000


def verify_signature(raw_body: bytes, header: str | None, api_key: str, now_ms: int | None = None) -> bool:
    if not header or not api_key:
        return False
    m = _SIG_RE.match(header.strip())
    if not m:
        return False
    ts, digest = m.group(1), m.group(2)
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    if abs(now_ms - int(ts)) > TOLERANCE_MS:
        return False
    expected = hmac.new(api_key.encode(), raw_body + ts.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest.lower())


def sign(raw_body: bytes, api_key: str, ts_ms: int | None = None) -> str:
    """Build a valid header (used by tests and local tooling)."""
    ts = str(int(time.time() * 1000) if ts_ms is None else ts_ms)
    d = hmac.new(api_key.encode(), raw_body + ts.encode(), hashlib.sha256).hexdigest()
    return f"v={ts},d={d}"


async def require_retell_signature(request: Request) -> bytes:
    """FastAPI dependency: returns the verified raw body or raises 401."""
    s = get_settings()
    body = await request.body()
    if s.retell_verify_signature and not verify_signature(
        body, request.headers.get("x-retell-signature"), s.retell_api_key
    ):
        log.warning("rejected request: bad retell signature", extra={"path": request.url.path})
        raise HTTPException(status_code=401, detail="invalid signature")
    return body
