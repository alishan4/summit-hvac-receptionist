"""Retell custom-function endpoints.

Retell POSTs {"call": {...}, "name": "...", "args": {...}} and feeds our response body to the LLM.
Logical failures therefore return HTTP 200 with ok=false and a `message` the agent can act on;
only a bad signature (401) or malformed envelope (400) uses an error status.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TypeVar

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.company import CompanyConfig, get_company
from app.db import get_db, session_scope
from app.models import Call, Outcome
from app.schemas import (
    BookAppointmentArgs,
    CheckServiceAreaArgs,
    FlagEmergencyArgs,
    GetSlotsArgs,
    RequestCallbackArgs,
)
from app.security import require_retell_signature
from app.services import booking as booking_svc
from app.services import slots as slot_logic
from app.services.calendar import CalendarClient, get_calendar
from app.services.deferred import defer
from app.services.calls import get_or_create_call, raise_urgency
from app.services.notify import notify_emergency
from app.services.service_area import in_service_area
from datetime import UTC, datetime

log = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["retell-tools"])
M = TypeVar("M", bound=BaseModel)


@dataclass
class ToolCall:
    call_id: str
    from_number: str | None
    args: dict


async def tool_call(body: bytes = Depends(require_retell_signature)) -> ToolCall:
    try:
        data = json.loads(body)
        call = data["call"]
        call_id = call["call_id"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="expected Retell envelope with call.call_id")
    args = data["args"] if isinstance(data.get("args"), dict) else {
        k: v for k, v in data.items() if k not in ("call", "name")  # args_at_root mode
    }
    return ToolCall(call_id=call_id, from_number=call.get("from_number"), args=args)


def _parse(model: type[M], tc: ToolCall) -> M | dict:
    try:
        return model.model_validate(tc.args)
    except ValidationError as exc:
        fields = sorted({str(e["loc"][0]) if e["loc"] else "args" for e in exc.errors()})
        log.info("tool input invalid", extra={"call_id": tc.call_id, "fields": fields})
        return {
            "ok": False,
            "error": "invalid_input",
            "fields": fields,
            "message": f"I couldn't use these details: {', '.join(fields)}. Ask the caller to repeat or "
                       "spell them, then try again.",
        }


def _slot_json(cfg: CompanyConfig, s: slot_logic.Slot) -> dict:
    return {"start": s.start.isoformat(), "end": s.end.isoformat(), "label": slot_logic.spoken_label(s)}


@router.post("/check_service_area")
def check_service_area(
    tc: ToolCall = Depends(tool_call), db: Session = Depends(get_db), cfg: CompanyConfig = Depends(get_company)
) -> dict:
    args = _parse(CheckServiceAreaArgs, tc)
    if isinstance(args, dict):
        return args
    get_or_create_call(db, tc.call_id, tc.from_number)
    ok, z = in_service_area(cfg, args.zip)
    if z is None:
        return {"ok": False, "error": "invalid_zip", "message": "That isn't a 5-digit ZIP. Ask the caller to repeat it."}
    log.info("service area check", extra={"call_id": tc.call_id, "in_area": ok})
    if ok:
        return {"ok": True, "in_service_area": True, "zip": z, "message": "ZIP is in our service area."}
    return {
        "ok": True, "in_service_area": False, "zip": z,
        "message": f"ZIP {z} is outside our service area ({cfg.service_area.description}). Apologize, do not "
                   "book, and offer to take a message instead.",
    }


@router.post("/get_available_slots")
def get_available_slots(
    tc: ToolCall = Depends(tool_call),
    db: Session = Depends(get_db),
    cfg: CompanyConfig = Depends(get_company),
    cal: CalendarClient = Depends(get_calendar),
) -> dict:
    args = _parse(GetSlotsArgs, tc)
    if isinstance(args, dict):
        return args
    call = get_or_create_call(db, tc.call_id, tc.from_number)
    call.tool_calls += 1  # intake in progress (used to tell "abandoned" from "info only")
    db.commit()
    now = datetime.now(UTC)
    try:
        busy = cal.busy(*slot_logic.search_range(cfg, now))
    except Exception:
        log.exception("calendar busy lookup failed", extra={"call_id": tc.call_id})
        return {"ok": False, "error": "calendar_unavailable",
                "message": "Scheduling is unavailable right now. Apologize and take a callback request."}
    slots = slot_logic.available_slots(cfg, now, busy, start_day=args.preferred_date)
    if not slots:
        return {"ok": True, "slots": [], "message": "No openings found. Offer to take a callback request."}
    return {
        "ok": True,
        "slots": [_slot_json(cfg, s) for s in slots],
        "dispatch_fee": cfg.pricing.fee_spoken,
        "message": f"Offer these {len(slots)} arrival windows using each label. Pass the chosen start "
                   "value exactly as given to book_appointment.",
    }


@router.post("/book_appointment")
def book_appointment(
    background: BackgroundTasks,
    tc: ToolCall = Depends(tool_call),
    db: Session = Depends(get_db),
    cfg: CompanyConfig = Depends(get_company),
    cal: CalendarClient = Depends(get_calendar),
) -> dict:
    args = _parse(BookAppointmentArgs, tc)
    if isinstance(args, dict):
        return args
    call = get_or_create_call(db, tc.call_id, tc.from_number)
    call.tool_calls += 1
    db.commit()
    res = booking_svc.book_appointment(db, cfg, cal, call, args)
    log.info("book_appointment", extra={"call_id": tc.call_id, "status": res.status})

    if res.ok and res.appointment:
        a = res.appointment
        if res.status == "booked":
            defer(background, _send_sms_task, a.id)
        label = slot_logic.spoken_label(slot_logic.Slot(a.slot_start.astimezone(cfg.tz), a.slot_end.astimezone(cfg.tz)))
        return {
            "ok": True, "status": res.status, "appointment_id": a.id, "when": label,
            "dispatch_fee": cfg.pricing.fee_spoken,
            "message": f"Booked for {label}. A text confirmation is on its way to the caller. "
                       "Confirm verbally, then close politely.",
        }
    if res.status == "slot_unavailable":
        return {
            "ok": False, "status": res.status,
            "alternatives": [_slot_json(cfg, s) for s in res.alternatives],
            "message": "That window was just taken. Apologize briefly and offer these alternatives.",
        }
    if res.status == "out_of_area":
        return {"ok": False, "status": res.status,
                "message": "That ZIP is outside our service area. Do not book. Offer to take a message."}
    if res.status == "emergency_call":
        return {"ok": False, "status": res.status,
                "message": "This call is flagged as a safety emergency. Do NOT book. Repeat the safety instructions."}
    return {"ok": False, "status": res.status,
            "message": "The booking system had a problem. Apologize and take a callback request instead."}


def _send_sms_task(appointment_id: int) -> None:
    with session_scope() as db:
        booking_svc.send_confirmation_sms(db, get_company(), appointment_id)


def _notify_emergency_task(call_id: int, details: str | None, address: str | None) -> None:
    with session_scope() as db:
        call = db.get(Call, call_id)
        if call:
            notify_emergency(db, get_company(), call, details, address)


@router.post("/flag_emergency")
def flag_emergency(
    background: BackgroundTasks, tc: ToolCall = Depends(tool_call), db: Session = Depends(get_db)
) -> dict:
    args = _parse(FlagEmergencyArgs, tc)
    if isinstance(args, dict):
        return args
    call = get_or_create_call(db, tc.call_id, tc.from_number)
    call.set_outcome(Outcome.EMERGENCY)
    call.urgency = "emergency"
    call.emergency_hazard = args.hazard.value
    if args.caller_name:
        call.caller_name = args.caller_name
    db.commit()
    defer(background, _notify_emergency_task, call.id, args.details, args.address)
    log.warning("EMERGENCY flagged", extra={"call_id": tc.call_id, "hazard": args.hazard.value})
    cfg = get_company()
    return {
        "ok": True,
        "message": "Emergency recorded and the owner is being alerted. Tell the caller to leave the home "
                   f"now, not touch switches or flames, and call 911 and {cfg.emergency.gas_utility_name} "
                   f"({cfg.emergency.gas_utility_phone}) from outside. Do NOT book. Then end the call.",
    }


@router.post("/request_callback")
def request_callback(tc: ToolCall = Depends(tool_call), db: Session = Depends(get_db)) -> dict:
    args = _parse(RequestCallbackArgs, tc)
    if isinstance(args, dict):
        return args
    call = get_or_create_call(db, tc.call_id, tc.from_number)
    call.set_outcome(Outcome.CALLBACK)  # never downgrades booked/emergency
    call.caller_name = call.caller_name or args.caller_name
    call.callback_number = args.callback_number or call.caller_number
    note = args.message + (f" (best time: {args.best_time})" if args.best_time else "")
    call.callback_message = note
    raise_urgency(call, call.urgency or "routine")
    db.commit()
    log.info("callback requested", extra={"call_id": tc.call_id})
    return {"ok": True, "message": "Callback request saved. Tell the caller someone will call them back, then close politely."}
