from sqlalchemy import select

from app.db import session_scope
from app.models import Appointment, Call
from app.services import sms
from app.services.calendar import get_calendar
from tests.conftest import signed_post, tool_body

ADDR = {"customer_name": "Jamie Rivera", "address": "123 Main St", "zip": "80203", "issue_type": "no_heat"}


def slots(client, call_id):
    r = signed_post(client, "/tools/get_available_slots", tool_body(call_id, "get_available_slots", {}))
    assert r.status_code == 200
    return r.json()["slots"]


def book(client, call_id, start, **over):
    args = {**ADDR, "slot_start": start, **over}
    return signed_post(client, "/tools/book_appointment", tool_body(call_id, "book_appointment", args)).json()


def rows():
    with session_scope() as db:
        return list(db.scalars(select(Appointment)))


def test_offers_three_slots_and_fee(client):
    r = signed_post(client, "/tools/get_available_slots", tool_body("c1", "x", {})).json()
    assert len(r["slots"]) == 3 and r["dispatch_fee"] == "$89"


def test_happy_path_books_calendar_db_and_sms(client):
    s = slots(client, "c1")[0]
    res = book(client, "c1", s["start"], urgency="urgent")
    assert res["ok"] and res["status"] == "booked"
    [a] = rows()
    assert a.sms_sent and a.phone == "+13035551234"  # defaulted from caller ID
    assert len(get_calendar().events) == 1
    ev = next(iter(get_calendar().events.values()))
    assert "Jamie Rivera" in ev["description"] and "123 Main St" in ev["location"]
    assert len(sms.SENT_LOG) == 1 and "$89" in sms.SENT_LOG[0][1]
    with session_scope() as db:
        call = db.scalar(select(Call))
        assert call.outcome == "booked" and call.urgency == "urgent"


def test_retry_is_idempotent(client):
    s = slots(client, "c1")[0]
    first = book(client, "c1", s["start"])
    second = book(client, "c1", s["start"])
    third = book(client, "c1", s["start"])
    assert first["status"] == "booked"
    assert second["status"] == third["status"] == "already_booked"
    assert second["appointment_id"] == first["appointment_id"]
    assert len(rows()) == 1
    assert len(get_calendar().events) == 1
    assert len(sms.SENT_LOG) == 1  # no duplicate texts


def test_second_caller_cannot_take_same_slot(client):
    s = slots(client, "c1")[0]
    assert book(client, "c1", s["start"])["ok"]
    res = book(client, "c2", s["start"])
    assert res["ok"] is False and res["status"] == "slot_unavailable"
    assert len(res["alternatives"]) == 3 and s["start"] not in [a["start"] for a in res["alternatives"]]
    assert len(rows()) == 1


def test_db_unique_slot_is_backstop_even_if_calendar_is_stale(client):
    s = slots(client, "c1")[0]
    book(client, "c1", s["start"])
    get_calendar().events.clear()  # simulate freebusy lag: calendar looks free
    res = book(client, "c2", s["start"])
    assert res["status"] == "slot_unavailable"
    assert len(rows()) == 1


def test_calendar_failure_rolls_back(client):
    s = slots(client, "c1")[0]
    get_calendar().fail_create = True
    res = book(client, "c1", s["start"])
    assert res["ok"] is False and res["status"] == "calendar_error"
    assert rows() == [] and sms.SENT_LOG == []
    get_calendar().fail_create = False
    assert book(client, "c1", s["start"])["status"] == "booked"  # retry works after recovery


def test_out_of_area_zip_refused(client):
    s = slots(client, "c1")[0]
    res = book(client, "c1", s["start"], zip="80301")
    assert res["status"] == "out_of_area" and rows() == []


def test_off_grid_slot_refused(client):
    res = book(client, "c1", "2030-01-01T03:17:00-07:00")
    assert res["status"] == "slot_unavailable"


def test_input_validation(client):
    s = slots(client, "c1")[0]
    res = book(client, "c1", s["start"], phone="123", customer_name="")
    assert res["ok"] is False and res["error"] == "invalid_input"
    assert set(res["fields"]) == {"phone", "customer_name"}
    res = book(client, "c1", "not-a-date")
    assert res["error"] == "invalid_input" and "slot_start" in res["fields"]
    assert rows() == []


def test_malformed_envelope_is_400(client):
    r = signed_post(client, "/tools/book_appointment", {"args": {}})
    assert r.status_code == 400


def test_args_at_root_supported(client):
    r = signed_post(client, "/tools/check_service_area", {"call": {"call_id": "c9"}, "zip": "80202"})
    assert r.json()["in_service_area"] is True


def test_out_of_area_check(client):
    r = signed_post(client, "/tools/check_service_area", tool_body("c1", "x", {"zip": "80301"})).json()
    assert r["ok"] and r["in_service_area"] is False and "do not" in r["message"].lower()
