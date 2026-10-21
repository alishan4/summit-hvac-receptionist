from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.logging_setup import mask_phone
from app.models import Call, Outcome

log = logging.getLogger(__name__)
URGENCY_RANK = {"routine": 0, "urgent": 1, "emergency": 2}


def get_or_create_call(db: Session, retell_call_id: str, caller_number: str | None = None) -> Call:
    call = db.scalar(select(Call).where(Call.retell_call_id == retell_call_id))
    if call is None:
        call = Call(retell_call_id=retell_call_id, caller_number=caller_number)
        db.add(call)
        try:
            db.commit()
        except IntegrityError:  # concurrent tool call + webhook created it first
            db.rollback()
            call = db.scalar(select(Call).where(Call.retell_call_id == retell_call_id))
            assert call is not None
    elif caller_number and not call.caller_number:
        call.caller_number = caller_number
        db.commit()
    return call


def raise_urgency(call: Call, urgency: str) -> None:
    if URGENCY_RANK.get(urgency, 0) > URGENCY_RANK.get(call.urgency or "routine", 0) or not call.urgency:
        call.urgency = urgency


def _ts(ms: int | None) -> datetime | None:
    return datetime.fromtimestamp(ms / 1000, UTC) if ms else None


def _transcript_text(call_payload: dict) -> str | None:
    if call_payload.get("transcript"):
        return call_payload["transcript"]
    turns = call_payload.get("transcript_object") or []
    if turns:
        return "\n".join(f"{t.get('role', '?')}: {t.get('content', '')}" for t in turns)
    return None


def _user_turns(call_payload: dict) -> int:
    return sum(1 for t in call_payload.get("transcript_object") or [] if t.get("role") == "user")


def apply_webhook(db: Session, event: str, payload: dict) -> Call:
    """Idempotently fold a Retell call event into the calls row."""
    call = get_or_create_call(db, payload["call_id"], payload.get("from_number"))
    if started := _ts(payload.get("start_timestamp")):
        call.started_at = started
    if event in ("call_ended", "call_analyzed"):
        if payload.get("duration_ms") is not None:
            call.duration = round(payload["duration_ms"] / 1000)
        elif payload.get("start_timestamp") and payload.get("end_timestamp"):
            call.duration = round((payload["end_timestamp"] - payload["start_timestamp"]) / 1000)
        if text := _transcript_text(payload):
            call.transcript = text
        if call.outcome is None:
            call.set_outcome(_infer_outcome(call, payload))
    if event == "call_analyzed":
        summary = (payload.get("call_analysis") or {}).get("call_summary")
        if summary:
            call.summary = summary
    db.commit()
    log.info(
        "call event",
        extra={"event": event, "call_id": call.retell_call_id, "caller": mask_phone(call.caller_number),
               "outcome": call.outcome, "duration": call.duration},
    )
    return call


def _infer_outcome(call: Call, payload: dict) -> Outcome:
    """No booking/emergency/callback happened. Caller left mid-intake or never engaged => abandoned."""
    if _user_turns(payload) == 0 or (call.duration or 0) < 10:
        return Outcome.ABANDONED
    if call.tool_calls > 0:  # started intake/booking but never finished
        return Outcome.ABANDONED
    return Outcome.INFO_ONLY
