"""Calendar adapters. One calendar == the technician schedule."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import Protocol

from app.services.slots import Interval
from app.settings import Settings, get_settings

log = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarClient(Protocol):
    def busy(self, start: datetime, end: datetime) -> list[Interval]: ...

    def create_event(
        self, event_id: str, summary: str, description: str, location: str,
        start: datetime, end: datetime, timezone: str,
    ) -> str: ...

    def delete_event(self, event_id: str) -> None: ...


class FakeCalendar:
    """In-memory calendar for tests and credential-free demos."""

    def __init__(self) -> None:
        self.events: dict[str, dict] = {}
        self.external_busy: list[Interval] = []
        self.fail_create = False

    def busy(self, start: datetime, end: datetime) -> list[Interval]:
        own = [(e["start"], e["end"]) for e in self.events.values()]
        return [b for b in own + self.external_busy if b[0] < end and start < b[1]]

    def create_event(self, event_id, summary, description, location, start, end, timezone) -> str:
        if self.fail_create:
            raise RuntimeError("calendar down")
        self.events.setdefault(  # same id twice == same event (idempotent)
            event_id,
            {"summary": summary, "description": description, "location": location, "start": start, "end": end},
        )
        return event_id

    def delete_event(self, event_id: str) -> None:
        self.events.pop(event_id, None)


class GoogleCalendar:
    def __init__(self, settings: Settings) -> None:
        from google.oauth2 import service_account

        if settings.google_service_account_json:
            info = json.loads(settings.google_service_account_json)
            self._creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif settings.google_service_account_file:
            self._creds = service_account.Credentials.from_service_account_file(
                settings.google_service_account_file, scopes=SCOPES
            )
        else:
            raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON")
        if not settings.google_calendar_id:
            raise RuntimeError("GOOGLE_CALENDAR_ID is required")
        self._cal_id = settings.google_calendar_id

    def _svc(self):
        # httplib2 is not thread-safe: build per call (static discovery doc, cheap).
        from googleapiclient.discovery import build

        return build("calendar", "v3", credentials=self._creds, cache_discovery=False)

    def busy(self, start: datetime, end: datetime) -> list[Interval]:
        body = {"timeMin": start.isoformat(), "timeMax": end.isoformat(), "items": [{"id": self._cal_id}]}
        resp = self._svc().freebusy().query(body=body).execute()
        periods = resp["calendars"][self._cal_id].get("busy", [])
        return [
            (datetime.fromisoformat(p["start"].replace("Z", "+00:00")),
             datetime.fromisoformat(p["end"].replace("Z", "+00:00")))
            for p in periods
        ]

    def create_event(self, event_id, summary, description, location, start, end, timezone) -> str:
        from googleapiclient.errors import HttpError

        body = {
            "id": event_id,  # deterministic => a retry cannot create a duplicate
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone},
        }
        try:
            self._svc().events().insert(calendarId=self._cal_id, body=body).execute()
        except HttpError as exc:
            if exc.resp.status == 409:  # already exists: earlier attempt succeeded
                log.info("calendar event already exists", extra={"event_id": event_id})
            else:
                raise
        return event_id

    def delete_event(self, event_id: str) -> None:
        from googleapiclient.errors import HttpError

        try:
            self._svc().events().delete(calendarId=self._cal_id, eventId=event_id).execute()
        except HttpError as exc:
            if exc.resp.status not in (404, 410):
                raise


@lru_cache
def get_calendar() -> CalendarClient:
    s = get_settings()
    return FakeCalendar() if s.calendar_backend == "fake" else GoogleCalendar(s)
