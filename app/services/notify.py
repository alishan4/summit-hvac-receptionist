"""Owner notifications: emergency alerts (SMS + email) and end-of-call summary email."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.company import CompanyConfig
from app.models import Call
from app.services.email import send_email
from app.services.events import record_event
from app.services.sms import send_sms

log = logging.getLogger(__name__)


def build_emergency_alert(
    cfg: CompanyConfig, call: Call, details: str | None = None, address: str | None = None
) -> tuple[str, str]:
    """(subject, body) of the owner's emergency alert - also used by the demo's notification preview."""
    hazard = (call.emergency_hazard or "unknown").replace("_", " ")
    lines = [
        f"EMERGENCY call - hazard: {hazard}",
        f"Caller: {call.caller_name or 'unknown'} {call.caller_number or ''}".strip(),
    ]
    if address:
        lines.append(f"Address: {address}")
    if details:
        lines.append(f"Details: {details}")
    lines.append("Caller was told to leave the home and call 911 / the gas utility. NOT booked.")
    return f"[EMERGENCY] {hazard} - {cfg.company.name} after-hours line", "\n".join(lines)


def notify_emergency(db: Session, cfg: CompanyConfig, call: Call, details: str | None, address: str | None) -> None:
    """Idempotent: owner is alerted once per call, unless every channel failed (then retry next time)."""
    if call.emergency_notified:
        return
    subject, body = build_emergency_alert(cfg, call, details, address)

    sms_ok = send_sms(cfg.owner.phone, f"{cfg.company.name} {body}")
    email_ok = send_email(cfg.owner.email, subject, body)
    if sms_ok or email_ok:
        call.emergency_notified = True
        db.commit()
        record_event(db, call.id, "emergency_alert_sent", {"sms": sms_ok, "email": email_ok})
    else:
        log.error("emergency notification failed on all channels", extra={"call_id": call.retell_call_id})


def build_call_summary(cfg: CompanyConfig, call: Call) -> tuple[str, str]:
    """(subject, body) of the owner's end-of-call email - also used by the demo's notification preview."""
    outcome = (call.outcome or "in progress").upper()
    lines = [
        f"Outcome: {outcome}",
        f"Urgency: {call.urgency or 'n/a'}",
        f"Caller: {call.caller_name or 'unknown'} ({call.caller_number or 'unknown number'})",
        f"Duration: {call.duration or 0}s",
        "",
        f"Summary: {call.summary or '(no summary)'}",
    ]
    for a in call.appointments:
        when = a.slot_start.astimezone(cfg.tz).strftime("%a %b %d, %I:%M %p")
        lines += [
            "",
            "APPOINTMENT",
            f"  {a.customer_name} - {a.phone}",
            f"  {a.address}, {a.zip}",
            f"  {a.issue_type.replace('_', ' ')} ({a.urgency}) - arrival window starts {when}",
            f"  SMS confirmation sent: {'yes' if a.sms_sent else 'no'}",
        ]
    if call.outcome == "callback":
        lines += ["", "CALLBACK REQUESTED", f"  Number: {call.callback_number or call.caller_number}",
                  f"  Message: {call.callback_message or ''}"]
    if call.emergency_hazard:
        lines += ["", f"SAFETY HAZARD REPORTED: {call.emergency_hazard}"]
    if call.transcript:
        lines += ["", "--- Transcript ---", call.transcript]
    subject = f"[{outcome}] After-hours call - {call.caller_name or call.caller_number or 'unknown'}"
    return subject, "\n".join(lines)


def send_call_summary(db: Session, cfg: CompanyConfig, call: Call) -> None:
    """Owner summary email, once per call (call_analyzed webhooks can be retried)."""
    if call.summary_emailed:
        return
    subject, body = build_call_summary(cfg, call)
    if send_email(cfg.owner.email, subject, body):
        call.summary_emailed = True
        db.commit()
        record_event(db, call.id, "summary_email_sent", {})
    record_event(db, call.id, "summary_ready", {})
