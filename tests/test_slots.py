from datetime import date, datetime, timedelta

from app.services.slots import Slot, available_slots, candidate_windows, find_slot, spoken_label
from tests.conftest import DENVER


def test_offers_three_slots_with_lead_time(cfg, monday_9am):
    slots = available_slots(cfg, monday_9am, busy=[])
    assert len(slots) == 3
    # min lead 2h => 09:00 now -> earliest start 11:00; windows step 8,10,12 -> first is 12:00
    assert slots[0].start == datetime(2026, 10, 19, 12, 0, tzinfo=DENVER)
    assert all(s.end - s.start == timedelta(hours=2) for s in slots)
    assert slots == sorted(slots, key=lambda s: s.start)


def test_spreads_across_days(cfg, monday_9am):
    slots = available_slots(cfg, monday_9am, busy=[])
    per_day = {}
    for s in slots:
        per_day[s.start.date()] = per_day.get(s.start.date(), 0) + 1
    assert max(per_day.values()) <= cfg.scheduling.max_slots_per_day


def test_busy_blocks_overlapping_windows(cfg, monday_9am):
    busy = [(datetime(2026, 10, 19, 12, 30, tzinfo=DENVER), datetime(2026, 10, 19, 13, 0, tzinfo=DENVER))]
    slots = available_slots(cfg, monday_9am, busy, limit=2)
    assert datetime(2026, 10, 19, 12, 0, tzinfo=DENVER) not in [s.start for s in slots]
    assert slots[0].start == datetime(2026, 10, 19, 14, 0, tzinfo=DENVER)


def test_skips_closed_days(cfg):
    # Saturday 2026-10-24 evening -> Sunday is closed -> next is Monday
    now = datetime(2026, 10, 24, 20, 0, tzinfo=DENVER)
    first = candidate_windows(cfg, now)[0]
    assert first.start.date() == date(2026, 10, 26)


def test_saturday_hours_respected(cfg):
    now = datetime(2026, 10, 24, 6, 0, tzinfo=DENVER)
    sat = [s for s in candidate_windows(cfg, now) if s.start.date() == date(2026, 10, 24)]
    assert sat[0].start.hour == 9 and sat[-1].end.hour == 15


def test_preferred_start_day(cfg, monday_9am):
    slots = available_slots(cfg, monday_9am, [], start_day=date(2026, 10, 21))
    assert slots[0].start.date() == date(2026, 10, 21)


def test_find_slot_valid_and_taken(cfg, monday_9am):
    start = datetime(2026, 10, 19, 14, 0, tzinfo=DENVER)
    assert find_slot(cfg, monday_9am, [], start) == Slot(start, start + timedelta(hours=2))
    busy = [(start, start + timedelta(hours=1))]
    assert find_slot(cfg, monday_9am, busy, start) is None


def test_find_slot_rejects_off_grid_and_past(cfg, monday_9am):
    assert find_slot(cfg, monday_9am, [], datetime(2026, 10, 19, 14, 30, tzinfo=DENVER)) is None
    assert find_slot(cfg, monday_9am, [], datetime(2026, 10, 19, 8, 0, tzinfo=DENVER)) is None


def test_spoken_label(cfg, monday_9am):
    s = available_slots(cfg, monday_9am, [], limit=1)[0]
    assert spoken_label(s) == "Monday, October 19, between 12 PM and 2 PM"


def test_window_label_compact(cfg, monday_9am):
    from app.services.slots import window_label

    morning = Slot(datetime(2026, 10, 19, 8, 0, tzinfo=DENVER), datetime(2026, 10, 19, 10, 0, tzinfo=DENVER))
    crossing = Slot(datetime(2026, 10, 19, 11, 0, tzinfo=DENVER), datetime(2026, 10, 19, 13, 0, tzinfo=DENVER))
    assert window_label(morning) == "8–10 AM"
    assert window_label(crossing) == "11 AM–1 PM"
