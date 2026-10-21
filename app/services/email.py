from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.settings import get_settings

log = logging.getLogger(__name__)
SENT_LOG: list[tuple[str, str, str]] = []  # (to, subject, body) for the "log" backend / tests


def send_email(to: str, subject: str, body: str) -> bool:
    """Owner notification email. Returns True on success; never raises."""
    s = get_settings()
    try:
        if s.email_backend == "log":
            SENT_LOG.append((to, subject, body))
            log.info("email (log backend)", extra={"subject": subject})
            return True
        if s.email_backend == "resend":
            r = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {s.resend_api_key}"},
                json={"from": s.email_from, "to": [to], "subject": subject, "text": body},
                timeout=10,
            )
            r.raise_for_status()
        else:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = s.email_from, to, subject
            msg.set_content(body)
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
                if s.smtp_starttls:
                    smtp.starttls()
                if s.smtp_username:
                    smtp.login(s.smtp_username, s.smtp_password)
                smtp.send_message(msg)
        log.info("email sent", extra={"subject": subject})
        return True
    except Exception:
        log.exception("email failed", extra={"subject": subject})
        return False
