from sqlalchemy import select

from app.db import session_scope
from app.models import Call
from app.services import email
from tests.conftest import signed_post, tool_body
from tests.test_booking import book, slots

T0 = 1_760_000_000_000


def event(client, name, call_id="w1", **extra):
    call = {"call_id": call_id, "from_number": "+13035551234", "start_timestamp": T0, **extra}
    return signed_post(client, "/webhooks/retell", {"event": name, "call": call})


def get_call(call_id="w1"):
    with session_scope() as db:
        return db.scalar(select(Call).where(Call.retell_call_id == call_id))


def convo(*roles):
    return [{"role": r, "content": f"{r} says hi"} for r in roles]


def test_lifecycle_stores_transcript_duration_summary_and_emails_once(client):
    event(client, "call_started")
    event(client, "call_ended", end_timestamp=T0 + 95_000, transcript="Agent: hi\nUser: hello",
          transcript_object=convo("agent", "user"))
    event(client, "call_analyzed", end_timestamp=T0 + 95_000, call_analysis={"call_summary": "Asked about hours."})
    event(client, "call_analyzed", end_timestamp=T0 + 95_000, call_analysis={"call_summary": "Asked about hours."})
    c = get_call()
    assert c.duration == 95 and c.summary == "Asked about hours." and "User: hello" in c.transcript
    assert c.outcome == "info_only" and c.caller_number == "+13035551234"
    assert len(email.SENT_LOG) == 1  # webhook retry did not re-send
    assert email.SENT_LOG[0][1].startswith("[INFO_ONLY]")


def test_hangup_with_no_conversation_is_abandoned(client):
    event(client, "call_ended", end_timestamp=T0 + 4_000, transcript_object=convo("agent"))
    assert get_call().outcome == "abandoned"


def test_hangup_mid_booking_is_abandoned(client):
    slots(client, "w1")  # caller got as far as hearing slots
    event(client, "call_ended", end_timestamp=T0 + 70_000, transcript_object=convo("agent", "user", "agent", "user"))
    assert get_call().outcome == "abandoned"


def test_booked_outcome_survives_call_end_and_summary_lists_appointment(client):
    s = slots(client, "w1")[0]
    book(client, "w1", s["start"])
    event(client, "call_ended", end_timestamp=T0 + 200_000, transcript_object=convo("agent", "user"))
    event(client, "call_analyzed", end_timestamp=T0 + 200_000, call_analysis={"call_summary": "Booked."})
    assert get_call().outcome == "booked"
    subject, body = email.SENT_LOG[-1][1:]
    assert subject.startswith("[BOOKED]") and "Jamie Rivera" in body and "SMS confirmation sent: yes" in body


def test_callback_flow(client):
    r = signed_post(client, "/tools/request_callback", tool_body(
        "w1", "request_callback", {"caller_name": "Sam Lee", "message": "Wants a human about a quote",
                                   "callback_number": "(303) 555-9876", "best_time": "morning"})).json()
    assert r["ok"]
    event(client, "call_ended", end_timestamp=T0 + 60_000, transcript_object=convo("agent", "user"))
    c = get_call()
    assert c.outcome == "callback" and c.callback_number == "+13035559876"
    assert "morning" in c.callback_message


def test_unknown_event_ignored_and_malformed_rejected(client):
    assert event(client, "transcript_updated").json()["ignored"] == "transcript_updated"
    assert signed_post(client, "/webhooks/retell", {"nope": 1}).status_code == 400
