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
from app.services.calls import apply_webhook
from app.services.deferred import defer
from app.services.notify import send_call_summary

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])
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
        event, payload = data["event"], data["call"]
        payload["call_id"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="malformed webhook")
    if event not in HANDLED:
        return {"ok": True, "ignored": event}

    call = apply_webhook(db, event, payload)
    if call.outcome == "emergency" and not call.emergency_notified and event != "call_started":
        defer(background, _notify_emergency_task, call.id, None, None)  # safety net if the tool-time alert failed
    if event == "call_analyzed":
        defer(background, _summary_task, call.id)
    return {"ok": True}
