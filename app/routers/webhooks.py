from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.company import get_company
from app.db import get_db, session_scope
from app.models import Call
from app.routers.tools import _notify_emergency_task
from app.security import require_retell_signature
from app.services.calls import apply_webhook, channel_of
from app.services.deferred import defer
from app.services.notify import send_call_summary

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
# Chat sessions fire chat_* events; they flow through the same pipeline as calls.
EVENT_ALIASES = {"chat_started": "call_started", "chat_ended": "call_ended", "chat_analyzed": "call_analyzed"}
HANDLED = {"call_started", "call_ended", "call_analyzed"}


def _summary_task(call_id: int) -> None:
    with session_scope() as db:
        call = db.get(Call, call_id)
        if call:
            send_call_summary(db, get_company(), call)


@router.post("/retell")
def retell_webhook(
    background: BackgroundTasks, body: bytes = Depends(require_retell_signature), db: Session = Depends(get_db)
) -> dict:
    try:
        data = json.loads(body)
        raw_event = data["event"]
        payload = data.get("call") or data.get("chat")
        payload["call_id"] = payload.get("call_id") or payload["chat_id"]  # chats are keyed by chat_id
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail="malformed webhook")
    event = EVENT_ALIASES.get(raw_event, raw_event)
    if event not in HANDLED:
        return {"ok": True, "ignored": raw_event}
    payload["_channel"] = channel_of(raw_event, payload)

    call = apply_webhook(db, event, payload)
    if call.outcome == "emergency" and not call.emergency_notified and event != "call_started":
        defer(background, _notify_emergency_task, call.id, None, None)  # safety net if the tool-time alert failed
    if event == "call_analyzed":
        defer(background, _summary_task, call.id)
    return {"ok": True}
