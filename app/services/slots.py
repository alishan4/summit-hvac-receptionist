"""Pure slot logic: no I/O, fully unit-testable. Calendar busy times are passed in."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.company import DAYS, CompanyConfig

Interval = tuple[datetime, datetime]


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime

    def overlaps(self, busy: Interval) -> bool:
        return self.start < busy[1] and busy[0] < self.end


def _hour_12(t: datetime) -> str:
    h = t.hour % 12 or 12
    suffix = "AM" if t.hour < 12 else "PM"
    return f"{h}" + (f":{t.minute:02d}" if t.minute else "") + f" {suffix}"


def spoken_label(slot: Slot) -> str:
    """e.g. 'Tuesday, October 21, between 8 AM and 10 AM'."""
    return (
        f"{slot.start.strftime('%A, %B')} {slot.start.day}, "
        f"between {_hour_12(slot.start)} and {_hour_12(slot.end)}"
    )


def candidate_windows(cfg: CompanyConfig, now: datetime, start_day: date | None = None) -> list[Slot]:
    """Every arrival window the business rules allow, ignoring the calendar."""
    sch = cfg.scheduling
    tz = cfg.tz
    now = now.astimezone(tz)
    earliest = now + timedelta(hours=sch.min_lead_hours)
    first_day = max(start_day or now.date(), now.date())
    out: list[Slot] = []
    for offset in range(sch.max_days_ahead + 1):
        day = first_day + timedelta(days=offset)
        hours = sch.business_hours.get(DAYS[day.weekday()])
        if not hours:
            continue
        open_t, close_t = hours
        cursor = datetime.combine(day, open_t, tzinfo=tz)
        close = datetime.combine(day, close_t, tzinfo=tz)
        width = timedelta(hours=sch.window_hours)
        while cursor + width <= close:
            if cursor >= earliest:
                out.append(Slot(cursor, cursor + width))
            cursor += timedelta(hours=sch.window_step_hours)
    return out


def available_slots(
    cfg: CompanyConfig,
    now: datetime,
    busy: list[Interval],
    start_day: date | None = None,
    limit: int | None = None,
) -> list[Slot]:
    """Next open windows, spread across days (max_slots_per_day) when possible."""
    free = [s for s in candidate_windows(cfg, now, start_day) if not any(s.overlaps(b) for b in busy)]
    limit = limit or cfg.scheduling.slots_to_offer
    cap = cfg.scheduling.max_slots_per_day
    picked: list[Slot] = []
    per_day: dict[date, int] = {}
    for s in free:
        if len(picked) >= limit:
            break
        d = s.start.date()
        if per_day.get(d, 0) < cap:
            picked.append(s)
            per_day[d] = per_day.get(d, 0) + 1
    if len(picked) < limit:  # backfill if the spread rule left us short
        for s in free:
            if len(picked) >= limit:
                break
            if s not in picked:
                picked.append(s)
    return sorted(picked, key=lambda s: s.start)


def find_slot(
    cfg: CompanyConfig, now: datetime, busy: list[Interval], start: datetime
) -> Slot | None:
    """Return the matching bookable slot if `start` is a valid, still-free window."""
    start = start.astimezone(cfg.tz)
    for s in candidate_windows(cfg, now, start.date()):
        if s.start == start:
            return None if any(s.overlaps(b) for b in busy) else s
    return None


def search_range(cfg: CompanyConfig, now: datetime) -> Interval:
    """Time range to query the calendar for (covers all candidate windows)."""
    now = now.astimezone(cfg.tz)
    end = datetime.combine(
        now.date() + timedelta(days=cfg.scheduling.max_days_ahead + 1), time(0), tzinfo=cfg.tz
    )
    return now, end
