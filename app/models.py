from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, TypeDecorator, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UTCDateTime(TypeDecorator):
    """Stores UTC; always returns tz-aware datetimes (SQLite drops tzinfo)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime not allowed")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=UTC)


class Outcome(enum.StrEnum):
    BOOKED = "booked"
    EMERGENCY = "emergency"
    CALLBACK = "callback"
    INFO_ONLY = "info_only"
    ABANDONED = "abandoned"


# Higher wins when a call hits several outcomes (e.g. callback requested after a failed booking).
OUTCOME_PRIORITY = {
    Outcome.EMERGENCY: 4,
    Outcome.BOOKED: 3,
    Outcome.CALLBACK: 2,
    Outcome.INFO_ONLY: 1,
    Outcome.ABANDONED: 0,
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    retell_call_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    caller_number: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    duration: Mapped[int | None] = mapped_column(Integer)  # seconds
    outcome: Mapped[str | None] = mapped_column(String(16))
    urgency: Mapped[str | None] = mapped_column(String(16))  # routine | urgent | emergency
    summary: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)

    # extras beyond the base spec
    caller_name: Mapped[str | None] = mapped_column(String(120))
    callback_number: Mapped[str | None] = mapped_column(String(32))
    callback_message: Mapped[str | None] = mapped_column(Text)
    emergency_hazard: Mapped[str | None] = mapped_column(String(32))
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    emergency_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    summary_emailed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    appointments: Mapped[list[Appointment]] = relationship(back_populates="call")

    def set_outcome(self, new: Outcome) -> None:
        cur = Outcome(self.outcome) if self.outcome else None
        if cur is None or OUTCOME_PRIORITY[new] > OUTCOME_PRIORITY[cur]:
            self.outcome = new.value


class Appointment(Base):
    __tablename__ = "appointments"
    # One technician calendar => a slot can only be sold once. Swap for a per-tech key later.
    __table_args__ = (UniqueConstraint("slot_start", name="uq_appointment_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))
    address: Mapped[str] = mapped_column(String(255))
    zip: Mapped[str] = mapped_column(String(5))
    issue_type: Mapped[str] = mapped_column(String(32))
    issue_description: Mapped[str | None] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(16), default="routine")
    system_info: Mapped[str | None] = mapped_column(String(255))
    slot_start: Mapped[datetime] = mapped_column(UTCDateTime)
    slot_end: Mapped[datetime] = mapped_column(UTCDateTime)
    calendar_event_id: Mapped[str | None] = mapped_column(String(128))
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    call: Mapped[Call] = relationship(back_populates="appointments")


class CallEvent(Base):
    """Timeline step for the demo UI (one row per thing that happened on a call)."""

    __tablename__ = "call_events"
    __table_args__ = (Index("ix_call_events_call", "call_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id"))
    kind: Mapped[str] = mapped_column(String(40))
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class DemoHit(Base):
    """Rate-limit ledger for /demo endpoints (DB-backed: serverless instances share nothing in memory)."""

    __tablename__ = "demo_hits"
    __table_args__ = (Index("ix_demo_hits_lookup", "kind", "ip_hash", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))  # web_call | chat | chat_msg | bad_code
    ip_hash: Mapped[str] = mapped_column(String(16))
    ref: Mapped[str | None] = mapped_column(String(128))  # e.g. chat id for per-chat message caps
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
