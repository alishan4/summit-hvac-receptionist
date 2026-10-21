"""Idempotent appointment booking. Order of operations matters:

1. key = hash(call, slot): a retry of the same request returns the existing row.
2. Re-check the slot against the live calendar (it may have been taken since it was offered).
3. Insert the row first (UNIQUE slot_start + UNIQUE key are the real double-book guards).
4. Create the calendar event with a deterministic id (Google 409 == already created).
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.company import CompanyConfig
from app.models import Appointment, Call, Outcome
from app.schemas import BookAppointmentArgs
from app.services import slots as slot_logic
from app.services.calendar import CalendarClient
from app.services.calls import raise_urgency
from app.services.events import record_event
from app.services.service_area import in_service_area
from app.services.sms import send_sms

log = logging.getLogger(__name__)

Status = Literal[
    "booked", "already_booked", "slot_unavailable", "out_of_area", "emergency_call", "calendar_error",
    "phone_required",
]


@dataclass
class BookingResult:
    status: Status
    appointment: Appointment | None = None
    alternatives: list[slot_logic.Slot] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in ("booked", "already_booked")


def idempotency_key(retell_call_id: str, slot_start: datetime) -> str:
    raw = f"{retell_call_id}|{slot_start.astimezone(UTC).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]  # hex => valid Google event id


def _event_description(appt: Appointment, call: Call) -> str:
    lines = [
        f"Customer: {appt.customer_name}",
        f"Phone: {appt.phone}",
        f"Address: {appt.address}, {appt.zip}",
        f"Issue: {appt.issue_type.replace('_', ' ')}",
        f"Urgency: {appt.urgency}",
    ]
    if appt.issue_description:
        lines.append(f"Details: {appt.issue_description}")
    if appt.system_info:
        lines.append(f"System: {appt.system_info}")
    lines.append(f"Booked by AI receptionist (call {call.retell_call_id})")
    return "\n".join(lines)


def book_appointment(
    db: Session,
    cfg: CompanyConfig,
    cal: CalendarClient,
    call: Call,
    req: BookAppointmentArgs,
    now: datetime | None = None,
) -> BookingResult:
    now = now or datetime.now(UTC)
    if call.outcome == Outcome.EMERGENCY:
        return BookingResult("emergency_call")

    ok, zip5 = in_service_area(cfg, req.zip)
    if not ok or zip5 is None:
        return BookingResult("out_of_area")

    start = req.slot_start if req.slot_start.tzinfo else req.slot_start.replace(tzinfo=cfg.tz)
    start = start.astimezone(cfg.tz)
    key = idempotency_key(call.retell_call_id, start)

    if existing := db.scalar(select(Appointment).where(Appointment.idempotency_key == key)):
        return BookingResult("already_booked", existing)

    phone = req.phone or call.caller_number
    if not phone:  # web/chat sessions have no caller ID: never book a visit we can't confirm
        return BookingResult("phone_required")

    window = slot_logic.search_range(cfg, now)
    busy = cal.busy(*window)
    slot = slot_logic.find_slot(cfg, now, busy, start)
    if slot is None:
        return BookingResult("slot_unavailable", alternatives=slot_logic.available_slots(cfg, now, busy))

    appt = Appointment(
        call_id=call.id,
        idempotency_key=key,
        customer_name=req.customer_name,
        phone=phone,
        address=req.address,
        zip=zip5,
        issue_type=req.issue_type.value,
        issue_description=req.issue_description,
        urgency=req.urgency.value,
        system_info=req.system_info,
        slot_start=slot.start,
        slot_end=slot.end,
    )
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if existing := db.scalar(select(Appointment).where(Appointment.idempotency_key == key)):
            return BookingResult("already_booked", existing)  # concurrent retry won the race
        return BookingResult("slot_unavailable", alternatives=slot_logic.available_slots(cfg, now, busy))

    try:
        appt.calendar_event_id = cal.create_event(
            event_id=key,
            summary=f"{req.issue_type.value.replace('_', ' ').title()} - {appt.customer_name}",
            description=_event_description(appt, call),
            location=f"{appt.address}, {appt.zip}",
            start=slot.start,
            end=slot.end,
            timezone=cfg.company.timezone,
        )
    except Exception:
        log.exception("calendar create failed; rolling back booking", extra={"call_id": call.retell_call_id})
        db.delete(appt)
        db.commit()
        return BookingResult("calendar_error")

    call.set_outcome(Outcome.BOOKED)
    call.caller_name = req.customer_name
    raise_urgency(call, req.urgency.value)
    db.commit()
    log.info("appointment booked", extra={"call_id": call.retell_call_id, "appointment_id": appt.id})
    return BookingResult("booked", appt)


def confirmation_sms_text(cfg: CompanyConfig, appt: Appointment) -> str:
    slot = slot_logic.Slot(appt.slot_start.astimezone(cfg.tz), appt.slot_end.astimezone(cfg.tz))
    return (
        f"{cfg.company.name}: You're booked! A technician will arrive "
        f"{slot_logic.spoken_label(slot).replace(', between', ',')} at {appt.address}. "
        f"Dispatch fee: {cfg.pricing.fee_spoken}. "
        f"Need to change something? Just call this number back."
    )


def send_confirmation_sms(db: Session, cfg: CompanyConfig, appointment_id: int) -> None:
    """Send at most once per appointment (guarded by sms_sent)."""
    appt = db.get(Appointment, appointment_id)
    if appt is None or appt.sms_sent or not appt.phone:
        return
    if send_sms(appt.phone, confirmation_sms_text(cfg, appt)):
        appt.sms_sent = True
        db.commit()
        record_event(db, appt.call_id, "confirmation_sms_sent", {"appointment_id": appt.id})
