from sqlalchemy import select

from app.db import session_scope
from app.models import Appointment, Call
from app.services import email, sms
from tests.conftest import signed_post, tool_body
from tests.test_booking import ADDR, book, slots

OWNER_PHONE = "+13035550100"


def flag(client, call_id="e1", **over):
    args = {"hazard": "gas_smell", "details": "smells like rotten eggs", "address": "9 Elm St", **over}
    return signed_post(client, "/tools/flag_emergency", tool_body(call_id, "flag_emergency", args))


def test_flag_marks_call_and_alerts_owner_by_sms_and_email(client):
    r = flag(client).json()
    assert r["ok"] and "911" in r["message"] and "Do NOT book" in r["message"]
    with session_scope() as db:
        call = db.scalar(select(Call))
        assert call.outcome == "emergency" and call.urgency == "emergency"
        assert call.emergency_hazard == "gas_smell" and call.emergency_notified
    assert [to for to, _ in sms.SENT_LOG] == [OWNER_PHONE]
    assert "EMERGENCY" in sms.SENT_LOG[0][1]
    assert len(email.SENT_LOG) == 1 and email.SENT_LOG[0][1].startswith("[EMERGENCY]")
    assert "9 Elm St" in email.SENT_LOG[0][2]


def test_flag_is_idempotent_no_duplicate_alerts(client):
    flag(client)
    flag(client)
    assert len(sms.SENT_LOG) == 1 and len(email.SENT_LOG) == 1


def test_booking_refused_after_emergency(client):
    s = slots(client, "e1")[0]
    flag(client, "e1")
    res = book(client, "e1", s["start"])
    assert res["ok"] is False and res["status"] == "emergency_call"
    with session_scope() as db:
        assert list(db.scalars(select(Appointment))) == []


def test_callback_does_not_downgrade_emergency(client):
    flag(client)
    signed_post(client, "/tools/request_callback", tool_body(
        "e1", "request_callback", {"caller_name": "Pat", "message": "call me"}))
    with session_scope() as db:
        assert db.scalar(select(Call)).outcome == "emergency"


def test_invalid_hazard_rejected(client):
    r = flag(client, hazard="aliens").json()
    assert r["ok"] is False and r["error"] == "invalid_input"
    assert sms.SENT_LOG == []


def test_webhook_retries_alert_if_tool_time_alert_failed(client, monkeypatch):
    monkeypatch.setattr("app.services.notify.send_sms", lambda *a, **k: False)
    monkeypatch.setattr("app.services.notify.send_email", lambda *a, **k: False)
    flag(client)
    with session_scope() as db:
        assert db.scalar(select(Call)).emergency_notified is False
    monkeypatch.undo()
    signed_post(client, "/webhooks/retell", {"event": "call_ended", "call": {
        "call_id": "e1", "start_timestamp": 1, "end_timestamp": 31001}})
    assert len(sms.SENT_LOG) == 1
