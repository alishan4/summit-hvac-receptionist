from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEST_KEY = "key_test_secret"

# Must be set before app modules read settings.
os.environ.update(
    {
        "COMPANY_CONFIG_PATH": str(ROOT / "config" / "company.yaml"),
        "PROMPT_PATH": str(ROOT / "prompts" / "agent_prompt.md"),
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", "sqlite://"),  # opt-in: run the suite on Postgres
        "CALENDAR_BACKEND": "fake",
        "SMS_BACKEND": "log",
        "EMAIL_BACKEND": "log",
        "RETELL_API_KEY": TEST_KEY,
        "RETELL_VERIFY_SIGNATURE": "true",
    }
)

DENVER = ZoneInfo("America/Denver")


@pytest.fixture
def cfg():
    from app.company import load_company

    return load_company(ROOT / "config" / "company.yaml")


@pytest.fixture
def monday_9am():
    # Monday 2026-10-19 09:00 Denver
    return datetime(2026, 10, 19, 9, 0, tzinfo=DENVER)


def signed_post(client, path: str, body: dict, key: str = TEST_KEY):
    import json

    from app.security import sign

    raw = json.dumps(body).encode()
    return client.post(
        path, content=raw, headers={"content-type": "application/json", "x-retell-signature": sign(raw, key)}
    )


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.db import Base, get_engine
    from app.main import app
    from app.services import email, sms
    from app.services.calendar import get_calendar

    with TestClient(app) as c:  # runs lifespan (init_db)
        Base.metadata.drop_all(get_engine())
        Base.metadata.create_all(get_engine())
        cal = get_calendar()
        cal.events.clear()
        cal.external_busy.clear()
        cal.fail_create = False
        sms.SENT_LOG.clear()
        email.SENT_LOG.clear()
        yield c


def tool_body(call_id: str, name: str, args: dict, from_number: str = "+13035551234") -> dict:
    return {"name": name, "args": args, "call": {"call_id": call_id, "from_number": from_number}}
