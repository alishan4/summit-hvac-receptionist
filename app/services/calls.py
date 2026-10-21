from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.logging_setup import mask_phone
from app.models import Call, Outcome
from app.services.events import record_event

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


def save_transcript_snapshot(db: Session, call: Call, transcript: str | None) -> None:
    """Retell sends the conversation so far with each function call: a near-live transcript that
    works without any browser-side key. The final transcript from call_ended overwrites it."""
    if transcript and len(transcript) > len(call.transcript or "") and call.duration is None:
        call.transcript = transcript
        db.commit()


def raise_urgency(call: Call, urgency: str) -> None:
    if URGENCY_RANK.get(urgency, 0) > URGENCY_RANK.get(call.urgency or "routine", 0) or not call.urgency:
        call.urgency = urgency


def _ts(ms: int | None) -> datetime | None:
    return datetime.fromtimestamp(ms / 1000, UTC) if ms else None


def _turns(payload: dict) -> list[dict]:
    """Voice calls carry transcript_object; chats carry message_with_tool_calls (plus tool entries)."""
    items = payload.get("transcript_object") or payload.get("message_with_tool_calls") or []
    return [t for t in items if t.get("role") in ("agent", "user")]


def _transcript_text(call_payload: dict) -> str | None:
    if call_payload.get("transcript"):
        return call_payload["transcript"]
    turns = _turns(call_payload)
    if turns:
        return "\n".join(f"{t.get('role', '?')}: {t.get('content', '')}" for t in turns)
    return None


def _user_turns(call_payload: dict) -> int:
    return sum(1 for t in _turns(call_payload) if t.get("role") == "user")


def channel_of(event: str, payload: dict) -> str:
    if event.startswith("chat_"):
        return "chat"
    return "web" if payload.get("call_type") == "web_call" else "phone"


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
        analysis = payload.get("call_analysis") or payload.get("chat_analysis") or {}
        summary = analysis.get("call_summary") or analysis.get("chat_summary")
        if summary:
            call.summary = summary
    db.commit()
    if event == "call_started":
        record_event(db, call.id, "call_started", {"channel": payload.get("_channel", "phone")})
    elif event == "call_ended":
        record_event(db, call.id, "call_ended", {"duration": call.duration})
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
