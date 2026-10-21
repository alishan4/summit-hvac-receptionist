"""Timeline events for the demo UI. Written by tool handlers and webhooks, read by /demo."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CallEvent

# Kinds that can only happen once per call (webhook retries must not duplicate them).
ONCE = {"call_started", "call_ended", "summary_ready", "summary_email_sent", "emergency_alert_sent"}


def record_event(db: Session, call_pk: int, kind: str, detail: dict | None = None) -> CallEvent | None:
    if kind in ONCE:
        existing = db.scalar(select(CallEvent).where(CallEvent.call_id == call_pk, CallEvent.kind == kind))
        if existing:
            return None
    ev = CallEvent(call_id=call_pk, kind=kind, detail=detail or {})
    db.add(ev)
    db.commit()
    return ev
