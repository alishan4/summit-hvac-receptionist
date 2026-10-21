"""Demo-site API: guarded session creation (protects Retell credits) + live read models for the UI.

Everything except /demo/branding* needs the access code (X-Demo-Code header).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.branding import LOGO_TYPES, Branding, get_branding
from app.company import CompanyConfig, get_company
from app.db import get_db
from app.models import Appointment, Call, CallEvent, DemoHit, Outcome
from app.services import slots as slot_logic
from app.services.booking import confirmation_sms_text
from app.services.calendar import CalendarClient, get_calendar
from app.services.calls import get_or_create_call
from app.services.events import record_event
from app.services.notify import build_call_summary, build_emergency_alert
from app.services.retell_api import RetellApi, RetellApiError, get_retell_api
from app.settings import Settings, get_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/demo", tags=["demo"])
HOUR = timedelta(hours=1)


def _err(status: int, code: str, message: str, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": code, "message": message}, headers=headers)


# ---------------------------------------------------------------- guards
def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def ip_hash(request: Request, s: Settings) -> str:
    return hashlib.sha256(f"{client_ip(request)}|{s.retell_api_key}".encode()).hexdigest()[:16]


def _count(db: Session, kind: str, since: datetime, ip: str | None = None, ref: str | None = None) -> int:
    q = select(func.count()).select_from(DemoHit).where(DemoHit.kind.in_(kind.split(",")), DemoHit.created_at >= since)
    if ip:
        q = q.where(DemoHit.ip_hash == ip)
    if ref:
        q = q.where(DemoHit.ref == ref)
    return db.scalar(q) or 0


def _hit(db: Session, kind: str, ip: str, ref: str | None = None) -> None:
    db.add(DemoHit(kind=kind, ip_hash=ip, ref=ref))
    db.commit()


def require_code(
    request: Request,
    x_demo_code: str | None = Header(default=None),
    db: Session = Depends(get_db),
    s: Settings = Depends(get_settings),
) -> str:
    """Returns the caller's hashed IP when the access code is valid."""
    if not s.demo_access_code:
        raise _err(503, "demo_disabled", "The demo is not enabled on this server (DEMO_ACCESS_CODE is unset).")
    ip = ip_hash(request, s)
    now = datetime.now(UTC)
    if _count(db, "bad_code", now - HOUR, ip) >= s.demo_bad_codes_per_hour:
        raise _err(429, "too_many_attempts", "Too many incorrect codes. Try again later.", {"Retry-After": "3600"})
    supplied = (x_demo_code or "").encode()
    if not hmac.compare_digest(supplied, s.demo_access_code.encode()):
        _hit(db, "bad_code", ip)
        raise _err(401, "invalid_code", "That access code isn't right.")
    return ip


def _need_agent(agent_id: str, s: Settings) -> None:
    if not s.retell_api_key or not agent_id:
        raise _err(503, "retell_not_configured",
                   "Retell isn't configured yet: run scripts/setup_retell_agent.py and set RETELL_AGENT_ID / "
                   "RETELL_CHAT_AGENT_ID.")


def _guard_budget(db: Session, ip: str, kind: str, per_hour: int, s: Settings) -> None:
    now = datetime.now(UTC)
    if _count(db, "web_call,chat", now - timedelta(days=1)) >= s.demo_max_calls_per_day:
        raise _err(429, "daily_budget", "The demo's daily session budget is used up. Try again tomorrow.",
                   {"Retry-After": "3600"})
    if _count(db, kind, now - HOUR, ip) >= per_hour:
        raise _err(429, "rate_limited", f"Limit of {per_hour} per hour reached for this network. "
                   "Please try again later.", {"Retry-After": "600"})


# ---------------------------------------------------------------- public: branding
@router.get("/branding")
def branding(b: Branding = Depends(get_branding), cfg: CompanyConfig = Depends(get_company),
             s: Settings = Depends(get_settings)) -> dict:
    return {
        "agency": b.agency.model_dump(),
        "badge": b.badge,
        "tagline": b.tagline,
        "accent_color": b.accent_color,
        "logo_url": "/demo/branding/logo",
        "scenarios": [sc.model_dump() for sc in b.scenarios],
        "demo_tips": b.demo_tips,
        "site": b.site.model_dump(),
        "dashboard": b.dashboard.model_dump(),
        "service_area": {"description": cfg.service_area.description, "zips": cfg.service_area.zips},
        "company": {
            "name": cfg.company.name,
            "location": cfg.company.location,
            "timezone": cfg.company.timezone,
            "greeting": " ".join(cfg.greeting.split()),
            "dispatch_fee": cfg.pricing.fee_spoken,
            "business_hours": {d: [t[0].strftime("%H:%M"), t[1].strftime("%H:%M")]
                               for d, t in cfg.scheduling.business_hours.items()},
        },
        "limits": {"max_call_seconds": s.demo_max_call_seconds},
    }


@router.get("/branding/logo")
def logo(b: Branding = Depends(get_branding)) -> Response:
    from pathlib import Path

    p = Path(b.logo_path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="logo not found")
    return Response(p.read_bytes(), media_type=LOGO_TYPES[p.suffix.lower()],
                    headers={"Cache-Control": "public, max-age=300"})


# ---------------------------------------------------------------- gated: session + sessions creation
@router.get("/session")
def session(_ip: str = Depends(require_code), s: Settings = Depends(get_settings)) -> dict:
    return {"ok": True, "voice_ready": bool(s.retell_api_key and s.retell_agent_id),
            "chat_ready": bool(s.retell_api_key and s.retell_chat_agent_id)}


@router.post("/web-call")
def web_call(
    ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    s: Settings = Depends(get_settings),
    retell: RetellApi = Depends(get_retell_api),
) -> dict:
    _need_agent(s.retell_agent_id, s)
    _guard_budget(db, ip, "web_call", s.demo_web_calls_per_hour, s)
    try:
        res = retell.create_web_call(
            s.retell_agent_id, s.demo_max_call_seconds * 1000, {"user_number": "unknown"})
    except RetellApiError as exc:
        log.error("retell create_web_call failed", extra={"status": exc.status})
        raise _err(502, "retell_error", "Couldn't start the call. Check Retell credits and agent settings.")
    _hit(db, "web_call", ip)
    call = get_or_create_call(db, res["call_id"])
    record_event(db, call.id, "call_started", {"channel": "web"})
    log.info("demo web call created", extra={"call_id": res["call_id"]})
    return {
        "call_id": res["call_id"],
        "access_token": res["access_token"],
        "transport": res.get("transport"),
        "ice_servers": res.get("ice_servers"),
        "expires_at": res.get("expires_at"),
        "max_seconds": s.demo_max_call_seconds,
    }


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)


@router.post("/chat")
def chat_create(
    ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    s: Settings = Depends(get_settings),
    retell: RetellApi = Depends(get_retell_api),
) -> dict:
    _need_agent(s.retell_chat_agent_id, s)
    _guard_budget(db, ip, "chat", s.demo_chats_per_hour, s)
    try:
        res = retell.create_chat(s.retell_chat_agent_id, {"user_number": "unknown"})
    except RetellApiError as exc:
        log.error("retell create_chat failed", extra={"status": exc.status})
        raise _err(502, "retell_error", "Couldn't start the chat. Check Retell credits and agent settings.")
    _hit(db, "chat", ip)
    call = get_or_create_call(db, res["chat_id"])
    record_event(db, call.id, "call_started", {"channel": "chat"})
    return {"chat_id": res["chat_id"], "max_seconds": s.demo_max_call_seconds,
            "max_messages": s.demo_max_chat_messages}


def _live_chat(db: Session, chat_id: str, s: Settings, retell: RetellApi) -> Call:
    call = db.scalar(select(Call).where(Call.retell_call_id == chat_id))
    if call is None:
        raise _err(404, "unknown_chat", "That chat session doesn't exist.")
    if datetime.now(UTC) - call.created_at > timedelta(seconds=s.demo_max_call_seconds):
        try:
            retell.end_chat(chat_id)
        except RetellApiError:
            pass
        raise _err(410, "session_expired", "This chat reached the demo time limit. Start a new one.")
    return call


@router.post("/chat/{chat_id}/message")
def chat_message(
    chat_id: str,
    body: ChatMessageIn,
    ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    s: Settings = Depends(get_settings),
    retell: RetellApi = Depends(get_retell_api),
) -> dict:
    _live_chat(db, chat_id, s, retell)
    if _count(db, "chat_msg", datetime.now(UTC) - timedelta(days=1), ref=chat_id) >= s.demo_max_chat_messages:
        raise _err(429, "message_limit", "This chat reached its message limit. Start a new one.")
    _hit(db, "chat_msg", ip, ref=chat_id)
    try:
        res = retell.create_chat_completion(chat_id, body.content.strip())
    except RetellApiError as exc:
        log.error("retell chat completion failed", extra={"status": exc.status})
        raise _err(502, "retell_error", "The receptionist didn't respond. Try again.")
    msgs = res.get("messages") or []
    return {
        "replies": [m["content"] for m in msgs if m.get("role") == "agent" and m.get("content")],
        "tools": [m["name"] for m in msgs if m.get("role") == "tool_call_invocation" and m.get("name")],
    }


@router.post("/chat/{chat_id}/end")
def chat_end(
    chat_id: str,
    _ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    retell: RetellApi = Depends(get_retell_api),
) -> dict:
    if db.scalar(select(Call).where(Call.retell_call_id == chat_id)) is None:
        raise _err(404, "unknown_chat", "That chat session doesn't exist.")
    try:
        retell.end_chat(chat_id)
    except RetellApiError as exc:
        log.warning("retell end_chat failed", extra={"status": exc.status})
    return {"ok": True}


# ---------------------------------------------------------------- gated: live read models
class EventOut(BaseModel):
    id: int
    kind: str
    label: str
    sub: str | None = None
    tone: str = "neutral"  # neutral | success | warn | danger
    at: str


def describe(ev: CallEvent) -> tuple[str, str | None, str]:
    d = ev.detail or {}
    k = ev.kind
    if k == "call_started":
        ch = d.get("channel", "phone")
        return {"web": "Voice call started", "chat": "Chat started"}.get(ch, "Phone call started"), None, "neutral"
    if k == "service_area_checked":
        ok = d.get("in_area")
        return ("Service area checked", f"ZIP {d.get('zip')}: " + ("inside our area" if ok else "outside our area"),
                "success" if ok else "warn")
    if k == "slots_found":
        n = d.get("count", 0)
        return ("Available slots found" if n else "No open slots found",
                f"{n} windows, earliest {d.get('first')}" if n else None, "neutral" if n else "warn")
    if k == "appointment_booked":
        return "Appointment booked", d.get("when"), "success"
    if k == "booking_failed":
        return "Booking problem", (d.get("status") or "").replace("_", " "), "warn"
    if k == "confirmation_sms_sent":
        return "Confirmation text sent to caller", None, "success"
    if k == "emergency_flagged":
        return "Emergency flagged", f"Hazard: {(d.get('hazard') or '').replace('_', ' ')}. No booking made.", "danger"
    if k == "emergency_alert_sent":
        chans = " + ".join(c for c, on in (("SMS", d.get("sms")), ("email", d.get("email"))) if on)
        return "Owner alerted immediately", chans or None, "danger"
    if k == "callback_requested":
        return "Callback requested", "Message saved for the team", "warn"
    if k == "summary_email_sent":
        return "Owner notified", "Call summary emailed", "success"
    if k == "summary_ready":
        return "Call summary ready", None, "success"
    if k == "call_ended":
        dur = d.get("duration")
        return "Call ended", f"{dur}s" if dur else None, "neutral"
    return k.replace("_", " ").capitalize(), None, "neutral"


def transcript_turns(text: str | None) -> list[dict]:
    """'Agent: hi\nUser: hello' -> [{role, content}] (continuation lines join the previous turn)."""
    turns: list[dict] = []
    for line in (text or "").splitlines():
        head, sep, rest = line.partition(":")
        if sep and head.strip().lower() in ("agent", "user"):
            turns.append({"role": head.strip().lower(), "content": rest.strip()})
        elif turns and line.strip():
            turns[-1]["content"] += " " + line.strip()
    return turns


def is_in_progress(call: Call, channel: str, ended: bool, s: Settings) -> bool:
    """A demo web/chat session whose tab was simply closed never gets an 'ended' event. Past its time cap
    (+ grace for Retell's end-of-call webhook) it is treated as finished so the dashboard stops showing
    it as live. Real phone calls have no cap here and are unaffected."""
    if ended:
        return False
    if channel in ("web", "chat"):
        return datetime.now(UTC) - call.created_at <= timedelta(seconds=s.demo_max_call_seconds + 90)
    return True


def appointment_out(cfg: CompanyConfig, a: Appointment) -> dict:
    start, end = a.slot_start.astimezone(cfg.tz), a.slot_end.astimezone(cfg.tz)
    return {
        "id": a.id,
        "customer_name": a.customer_name,
        "phone": a.phone,
        "address": a.address,
        "zip": a.zip,
        "issue_type": a.issue_type,
        "issue_label": a.issue_type.replace("_", " ").capitalize(),
        "issue_description": a.issue_description,
        "system_info": a.system_info,
        "urgency": a.urgency,
        "slot_start": start.isoformat(),
        "slot_end": end.isoformat(),
        "window_label": slot_logic.spoken_label(slot_logic.Slot(start, end)),
        "short_label": f"{start:%a} {slot_logic.window_label(slot_logic.Slot(start, end))}",
        "sms_sent": a.sms_sent,
        "added_to_calendar": bool(a.calendar_event_id),
    }


@router.get("/calls/{call_id}/events")
def call_events(
    call_id: str,
    _ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    cfg: CompanyConfig = Depends(get_company),
    s: Settings = Depends(get_settings),
) -> dict:
    call = db.scalar(select(Call).where(Call.retell_call_id == call_id))
    if call is None:
        raise _err(404, "unknown_call", "No such call yet.")
    events = list(db.scalars(select(CallEvent).where(CallEvent.call_id == call.id).order_by(CallEvent.id)))
    kinds = {e.kind for e in events}
    out_events = []
    for e in events:
        label, sub, tone = describe(e)
        out_events.append(EventOut(id=e.id, kind=e.kind, label=label, sub=sub, tone=tone,
                                   at=e.created_at.isoformat()).model_dump())

    appt = max(call.appointments, key=lambda a: a.id) if call.appointments else None
    notifications: dict = {"confirmation_sms": None, "owner_alert": None, "owner_summary": None}
    if appt:
        notifications["confirmation_sms"] = {"to": appt.phone, "body": confirmation_sms_text(cfg, appt),
                                             "sent": appt.sms_sent}
    if call.outcome == Outcome.EMERGENCY or "emergency_flagged" in kinds:
        flag = next((e for e in events if e.kind == "emergency_flagged"), None)
        fd = (flag.detail or {}) if flag else {}
        subject, body = build_emergency_alert(cfg, call, fd.get("details"), fd.get("address"))
        notifications["owner_alert"] = {
            "sms": {"to": cfg.owner.phone, "body": f"{cfg.company.name} {body}", "sent": call.emergency_notified},
            "email": {"to": cfg.owner.email, "subject": subject, "body": body, "sent": call.emergency_notified},
        }
    if call.outcome or call.summary:
        subject, body = build_call_summary(cfg, call)
        notifications["owner_summary"] = {"to": cfg.owner.email, "subject": subject, "body": body,
                                          "final": "summary_ready" in kinds, "sent": call.summary_emailed}
    return {
        "call": {
            "call_id": call.retell_call_id,
            "status": "in_progress" if is_in_progress(
                call, next((e.detail or {}).get("channel", "phone") for e in events if e.kind == "call_started")
                if "call_started" in kinds else "phone", "call_ended" in kinds, s) else "ended",
            "outcome": call.outcome,
            "urgency": call.urgency,
            "duration": call.duration,
            "summary": call.summary,
            "summary_ready": "summary_ready" in kinds,
            "transcript": transcript_turns(call.transcript),
        },
        "events": out_events,
        "appointment": appointment_out(cfg, appt) if appt else None,
        "notifications": notifications,
    }


def _local_day_bounds(cfg: CompanyConfig, day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time(0), tzinfo=cfg.tz)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


@router.get("/appointments")
def appointments(
    date_: date | None = Query(default=None, alias="date"),
    _ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    cfg: CompanyConfig = Depends(get_company),
) -> dict:
    day = date_ or datetime.now(cfg.tz).date()
    lo, hi = _local_day_bounds(cfg, day)
    rows = list(db.scalars(select(Appointment).where(Appointment.slot_start >= lo, Appointment.slot_start < hi)
                           .order_by(Appointment.slot_start)))
    booked = {a.slot_start: a for a in rows}
    now = datetime.now(UTC)
    windows = []
    for w in slot_logic.day_windows(cfg, day):
        a = booked.get(w.start.astimezone(UTC))
        windows.append({
            "start": w.start.isoformat(), "end": w.end.isoformat(),
            "label": slot_logic.window_label(w),
            "status": "booked" if a else ("past" if w.end.astimezone(UTC) < now else "open"),
            "appointment": appointment_out(cfg, a) if a else None,
        })
    return {"date": day.isoformat(), "timezone": cfg.company.timezone, "closed": not windows, "windows": windows,
            "appointments": [appointment_out(cfg, a) for a in rows]}


@router.get("/stats")
def stats(_ip: str = Depends(require_code), db: Session = Depends(get_db),
          cfg: CompanyConfig = Depends(get_company), b: Branding = Depends(get_branding)) -> dict:
    lo, hi = _local_day_bounds(cfg, datetime.now(cfg.tz).date())
    base = select(func.count()).select_from(Call).where(Call.created_at >= lo, Call.created_at < hi)

    def n(outcome: Outcome) -> int:
        return db.scalar(base.where(Call.outcome == outcome.value)) or 0

    booked = n(Outcome.BOOKED)
    avg = b.dashboard.average_job_value
    return {"calls_today": db.scalar(base) or 0, "booked": booked,
            "emergencies": n(Outcome.EMERGENCY), "callbacks": n(Outcome.CALLBACK),
            "average_job_value": avg, "revenue_protected": round(booked * avg, 2)}


@router.get("/calls")
def calls(
    _ip: str = Depends(require_code),
    db: Session = Depends(get_db),
    cfg: CompanyConfig = Depends(get_company),
    limit: int = Query(default=30, ge=1, le=100),
    s: Settings = Depends(get_settings),
) -> dict:
    """Today's calls/chats, newest first (the dashboard's call list)."""
    lo, hi = _local_day_bounds(cfg, datetime.now(cfg.tz).date())
    rows = list(db.scalars(select(Call).where(Call.created_at >= lo, Call.created_at < hi)
                           .order_by(Call.created_at.desc(), Call.id.desc()).limit(limit)))
    ids = [c.id for c in rows]
    evs = list(db.scalars(select(CallEvent).where(CallEvent.call_id.in_(ids),
                                                  CallEvent.kind.in_(["call_started", "call_ended"])))) if ids else []
    channel = {e.call_id: (e.detail or {}).get("channel", "phone") for e in evs if e.kind == "call_started"}
    ended = {e.call_id for e in evs if e.kind == "call_ended"}
    out = []
    for c in rows:
        appt = max(c.appointments, key=lambda a: a.id) if c.appointments else None
        out.append({
            "call_id": c.retell_call_id,
            "channel": channel.get(c.id, "phone"),
            "started_at": c.created_at.isoformat(),
            "status": "in_progress" if is_in_progress(c, channel.get(c.id, "phone"), c.id in ended, s) else "ended",
            "outcome": c.outcome,
            "urgency": c.urgency,
            "caller": c.caller_name or c.caller_number,
            "duration": c.duration,
            "summary": c.summary,
            "appointment": appointment_out(cfg, appt)["short_label"] if appt else None,
        })
    return {"calls": out}


@router.post("/reset")
def reset(_ip: str = Depends(require_code), db: Session = Depends(get_db),
          cal: CalendarClient = Depends(get_calendar)) -> dict:
    """Wipe demo calls, bookings and their calendar events. The rate-limit ledger is kept on purpose,
    so a reset can't be used to dodge the credit limits."""
    appts = list(db.scalars(select(Appointment)))
    removed_events = 0
    for a in appts:
        if a.calendar_event_id:
            try:
                cal.delete_event(a.calendar_event_id)
                removed_events += 1
            except Exception:
                log.exception("calendar delete failed during reset", extra={"appointment_id": a.id})
    calls = db.scalar(select(func.count()).select_from(Call)) or 0
    db.execute(delete(CallEvent))
    db.execute(delete(Appointment))
    db.execute(delete(Call))
    db.commit()
    log.warning("demo reset", extra={"calls": calls, "appointments": len(appts)})
    return {"ok": True, "calls_deleted": calls, "appointments_deleted": len(appts),
            "calendar_events_deleted": removed_events}
