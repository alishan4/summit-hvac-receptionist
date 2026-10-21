"""Turn a caller's own words ("tomorrow morning", "friday afternoon", "oct 24") into a search window.

The agent does not know today's date, and a model asked for a calendar date will invent one (a live test
passed 2025-02-15). So the tool takes the caller's words and this module resolves them against the
company's clock.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
PARTS = {"morning": (0, 12), "afternoon": (12, 17), "evening": (16, 24)}  # window START hour ranges


@dataclass(frozen=True)
class WhenPref:
    day: date | None = None          # earliest day to search from (None = as soon as possible)
    part: str | None = None          # morning | afternoon | evening
    matched: str = ""                # what we understood, echoed back to the agent

    def hour_range(self) -> tuple[int, int] | None:
        return PARTS.get(self.part) if self.part else None


def parse_when(text: str | None, now: datetime) -> WhenPref:
    """Best effort. Unrecognised text means 'no preference' (earliest slots), never an error."""
    if not text or not text.strip():
        return WhenPref()
    low = text.lower()
    today = now.date()
    part = next((p for p in PARTS if p in low), None)
    if re.search(r"\bnoon\b|\blunch", low):
        part = part or "afternoon"
    day: date | None = None
    label: list[str] = []

    if m := re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", low):
        try:
            day = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            day = None
    if day is None and re.search(r"day after tomorrow", low):
        day = today + timedelta(days=2)
    elif day is None and re.search(r"\btomorrow\b", low):
        day = today + timedelta(days=1)
    elif day is None and re.search(r"\b(today|tonight|this (morning|afternoon|evening))\b", low):
        day = today
    if day is None:
        for i, name in enumerate(WEEKDAYS):
            if re.search(rf"\b{name}\b|\b{name[:3]}\b(?!\w)", low):
                ahead = (i - today.weekday()) % 7
                day = today + timedelta(days=ahead or 7)  # a bare weekday means the next one, not today
                break
    if day is None:
        for i, name in enumerate(MONTHS):
            if m := re.search(rf"\b({name}|{name[:3]})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", low):
                try:
                    cand = date(today.year, i + 1, int(m.group(2)))
                except ValueError:
                    break
                day = cand if cand >= today else cand.replace(year=today.year + 1)
                break
    if day is not None:
        day = max(day, today)  # never search the past
        label.append(day.strftime("%A %b %d"))
    if part:
        label.append(part)
    return WhenPref(day, part, " ".join(label))
