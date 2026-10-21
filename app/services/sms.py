from __future__ import annotations

import logging

import httpx

from app.logging_setup import mask_phone
from app.settings import get_settings

log = logging.getLogger(__name__)
SENT_LOG: list[tuple[str, str]] = []  # (to, body) - populated by the "log" backend, used by tests


def send_sms(to: str, body: str) -> bool:
    """Transactional SMS via Twilio REST. Returns True on success; never raises."""
    s = get_settings()
    if s.sms_backend == "log":
        SENT_LOG.append((to, body))
        log.info("sms (log backend)", extra={"to": mask_phone(to)})
        return True
    try:
        resp = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Messages.json",
            auth=(s.twilio_account_sid, s.twilio_auth_token),
            data={"To": to, "From": s.twilio_from_number, "Body": body},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("sms sent", extra={"to": mask_phone(to)})
        return True
    except Exception:
        log.exception("sms failed", extra={"to": mask_phone(to)})
        return False
