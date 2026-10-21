"""'when' resolves the caller's own words on the company clock: the agent must never invent a date
(a live test passed preferred_date=2025-02-15 for 'tomorrow morning')."""
from datetime import date, datetime

import pytest

from app.services.when import parse_when
from tests.conftest import DENVER, signed_post, tool_body

WED = datetime(2026, 10, 21, 15, 0, tzinfo=DENVER)   # Wednesday afternoon


@pytest.mark.parametrize("text, day, part", [
    ("tomorrow morning", date(2026, 10, 22), "morning"),
    ("Tomorrow", date(2026, 10, 22), None),
    ("today", date(2026, 10, 21), None),
    ("this evening", date(2026, 10, 21), "evening"),
    ("the day after tomorrow", date(2026, 10, 23), None),
    ("Friday afternoon", date(2026, 10, 23), "afternoon"),
    ("friday", date(2026, 10, 23), None),
    ("wednesday", date(2026, 10, 28), None),               # a bare weekday means the NEXT one
    ("oct 24th", date(2026, 10, 24), None),
    ("October 24", date(2026, 10, 24), None),
    ("jan 5", date(2027, 1, 5), None),                      # already past this year -> next year
    ("2026-10-27 morning", date(2026, 10, 27), "morning"),
    ("2025-02-15", date(2026, 10, 21), None),               # never the past: clamped to today
    ("morning", None, "morning"),
])
def test_parse_when(text, day, part):
    p = parse_when(text, WED)
    assert (p.day, p.part) == (day, part)


@pytest.mark.parametrize("text", [None, "", "   ", "asap", "as soon as possible", "whenever", "blorp"])
def test_no_preference_means_earliest(text):
    p = parse_when(text, WED)
    assert p.day is None and p.part is None and p.matched == ""


def test_hour_ranges():
    assert parse_when("morning", WED).hour_range() == (0, 12)
    assert parse_when("afternoon", WED).hour_range() == (12, 17)
    assert parse_when("tomorrow", WED).hour_range() is None


def _slots(client, call_id, **args):
    return signed_post(client, "/tools/get_available_slots", tool_body(call_id, "x", args)).json()


def test_when_filters_the_real_tool(client):
    r = _slots(client, "w1", when="tomorrow morning")
    assert r["ok"] and r["slots"]
    today = datetime.now(DENVER).date()
    for s in r["slots"]:
        start = datetime.fromisoformat(s["start"])
        assert start.date() > today and start.hour < 12          # tomorrow or later, mornings only
    assert "These are the earliest after" in r["message"] and "morning" in r["message"]

    afternoon = _slots(client, "w2", when="afternoon")["slots"]
    assert afternoon and all(12 <= datetime.fromisoformat(s["start"]).hour < 17 for s in afternoon)


def test_a_made_up_past_date_is_harmless_and_garbage_is_ignored(client):
    r = _slots(client, "w3", when="2025-02-15")                  # what the live agent actually sent
    assert r["ok"] and all(datetime.fromisoformat(s["start"]).date() >= datetime.now(DENVER).date() for s in r["slots"])
    assert _slots(client, "w4", when="blorp")["ok"] and _slots(client, "w5")["ok"]
    assert _slots(client, "w6", when="x" * 200)["error"] == "invalid_input"        # bounded input


def test_evening_with_nothing_open_falls_back_and_says_so(client):
    r = _slots(client, "w7", when="tomorrow evening")            # business hours end at 18:00: no window starts >= 16 + 2h
    assert r["ok"] and r["slots"]
    assert "Nothing is open in the evening" in r["message"] or all(
        datetime.fromisoformat(s["start"]).hour >= 16 for s in r["slots"])


def test_the_tool_definition_and_prompt_use_when_not_dates():
    from app.services.retell_tools import build_tools
    from tests.conftest import ROOT

    tool = next(t for t in build_tools("https://x") if t["name"] == "get_available_slots")
    assert "when" in tool["parameters"]["properties"] and "preferred_date" not in tool["parameters"]["properties"]
    assert "NEVER compute or guess a calendar date" in tool["parameters"]["properties"]["when"]["description"]
    core = (ROOT / "prompts" / "core.md").read_text()
    assert "pass their own words as `when`" in core and "never work out a date yourself" in core
