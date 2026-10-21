from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.db import session_scope
from app.models import Appointment, Call, CallEvent, DemoHit
from app.services import sms
from app.services.calendar import get_calendar
from app.services.retell_api import RetellApiError, get_retell_api
from app.settings import Settings, get_settings
from tests.conftest import TEST_KEY, signed_post, tool_body
from tests.test_booking import ADDR, book, slots

CODE = {"X-Demo-Code": "letmein"}


class FakeRetell:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.fail = False
        self.n = 0

    def _go(self, name, *a):
        self.calls.append((name, *a))
        if self.fail:
            raise RetellApiError(402, "out of credit")
        self.n += 1

    def create_web_call(self, agent_id, max_duration_ms, dynamic_variables):
        self._go("web", agent_id, max_duration_ms, dynamic_variables)
        return {"call_id": f"web_{self.n}", "access_token": "tok", "transport": "gateway",
                "ice_servers": [], "expires_at": 1}

    def create_chat(self, agent_id, dynamic_variables):
        self._go("chat", agent_id, dynamic_variables)
        return {"chat_id": f"chat_{self.n}"}

    def create_chat_completion(self, chat_id, content):
        self._go("completion", chat_id, content)
        return {"messages": [{"role": "tool_call_invocation", "name": "check_service_area"},
                             {"role": "agent", "content": "Happy to help. What's your ZIP?"}]}

    def end_chat(self, chat_id):
        self.calls.append(("end", chat_id))


def make_settings(**kw):
    base = dict(demo_access_code="letmein", retell_api_key=TEST_KEY, retell_agent_id="agent_voice",
                retell_chat_agent_id="agent_chat")
    return Settings(**{**base, **kw})


@pytest.fixture
def demo(client):
    from app.main import app

    fake = FakeRetell()
    state = {"settings": make_settings()}
    app.dependency_overrides[get_settings] = lambda: state["settings"]
    app.dependency_overrides[get_retell_api] = lambda: fake
    yield SimpleNamespace(c=client, retell=fake, state=state)
    app.dependency_overrides.clear()


# ------------------------------------------------------------------ access code
def test_everything_but_branding_needs_the_code(demo):
    gated = [("get", "/demo/session"), ("post", "/demo/web-call"), ("post", "/demo/chat"),
             ("post", "/demo/chat/x/message"), ("post", "/demo/chat/x/end"), ("get", "/demo/calls/x/events"),
             ("get", "/demo/appointments"), ("get", "/demo/stats"), ("post", "/demo/reset")]
    for method, path in gated:
        kw = {"json": {"content": "hi"}} if path.endswith("message") else {}
        r = getattr(demo.c, method)(path, **kw)
        assert r.status_code == 401, path
        assert r.json()["detail"]["error"] == "invalid_code"
    assert demo.retell.calls == []  # nothing reached Retell
    assert demo.c.get("/demo/branding").status_code == 200


def test_wrong_code_rejected_right_code_accepted(demo):
    assert demo.c.get("/demo/session", headers={"X-Demo-Code": "nope"}).status_code == 401
    r = demo.c.get("/demo/session", headers=CODE)
    assert r.status_code == 200 and r.json() == {"ok": True, "voice_ready": True, "chat_ready": True}


def test_demo_disabled_when_no_code_configured(demo):
    demo.state["settings"] = make_settings(demo_access_code="")
    r = demo.c.post("/demo/web-call", headers={"X-Demo-Code": ""})
    assert r.status_code == 503 and r.json()["detail"]["error"] == "demo_disabled"
    assert demo.retell.calls == []


def test_brute_force_lockout(demo):
    demo.state["settings"] = make_settings(demo_bad_codes_per_hour=3)
    for _ in range(3):
        assert demo.c.get("/demo/session", headers={"X-Demo-Code": "x"}).status_code == 401
    r = demo.c.get("/demo/session", headers=CODE)  # even the right code is locked out now
    assert r.status_code == 429 and r.json()["detail"]["error"] == "too_many_attempts"


# ------------------------------------------------------------------ web call
def test_web_call_creates_capped_call_and_never_leaks_key(demo):
    r = demo.c.post("/demo/web-call", headers=CODE)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["call_id"] == "web_1" and body["access_token"] == "tok" and body["max_seconds"] == 240
    assert TEST_KEY not in r.text
    name, agent, max_ms, dyn = demo.retell.calls[0]
    assert (name, agent, max_ms) == ("web", "agent_voice", 240_000) and dyn == {"user_number": "unknown"}
    ev = demo.c.get("/demo/calls/web_1/events", headers=CODE).json()
    assert [e["label"] for e in ev["events"]] == ["Voice call started"]


def test_web_call_rate_limited_per_ip(demo):
    for _ in range(5):
        assert demo.c.post("/demo/web-call", headers=CODE).status_code == 200
    r = demo.c.post("/demo/web-call", headers=CODE)
    assert r.status_code == 429 and r.json()["detail"]["error"] == "rate_limited"
    assert "retry-after" in r.headers
    assert len(demo.retell.calls) == 5  # the blocked attempt never reached Retell
    # a different network is unaffected
    r2 = demo.c.post("/demo/web-call", headers={**CODE, "x-forwarded-for": "203.0.113.9"})
    assert r2.status_code == 200


def test_global_daily_budget(demo):
    demo.state["settings"] = make_settings(demo_max_calls_per_day=2)
    demo.c.post("/demo/web-call", headers=CODE)
    demo.c.post("/demo/chat", headers=CODE)
    r = demo.c.post("/demo/web-call", headers={**CODE, "x-forwarded-for": "198.51.100.7"})
    assert r.status_code == 429 and r.json()["detail"]["error"] == "daily_budget"
    assert len(demo.retell.calls) == 2


def test_retell_failure_is_502_and_not_counted(demo):
    demo.retell.fail = True
    r = demo.c.post("/demo/web-call", headers=CODE)
    assert r.status_code == 502 and r.json()["detail"]["error"] == "retell_error"
    with session_scope() as db:
        assert db.scalars(select(DemoHit)).first() is None  # failed attempts don't burn the quota


def test_not_configured(demo):
    demo.state["settings"] = make_settings(retell_agent_id="")
    r = demo.c.post("/demo/web-call", headers=CODE)
    assert r.status_code == 503 and r.json()["detail"]["error"] == "retell_not_configured"
    assert demo.retell.calls == []


# ------------------------------------------------------------------ chat
def test_chat_roundtrip(demo):
    cid = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]
    r = demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "My AC is broken"})
    assert r.status_code == 200
    assert r.json() == {"replies": ["Happy to help. What's your ZIP?"], "tools": ["check_service_area"]}
    assert ("completion", cid, "My AC is broken") in demo.retell.calls
    assert demo.c.post(f"/demo/chat/{cid}/end", headers=CODE).json() == {"ok": True}
    assert ("end", cid) in demo.retell.calls


def test_chat_message_validation_and_unknown_session(demo):
    cid = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]
    assert demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": ""}).status_code == 422
    assert demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "x" * 501}).status_code == 422
    r = demo.c.post("/demo/chat/chat_nope/message", headers=CODE, json={"content": "hi"})
    assert r.status_code == 404
    assert not [c for c in demo.retell.calls if c[0] == "completion"]


def test_chat_message_cap_and_time_limit(demo):
    demo.state["settings"] = make_settings(demo_max_chat_messages=2)
    cid = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]
    for _ in range(2):
        assert demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "hi"}).status_code == 200
    r = demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "hi"})
    assert r.status_code == 429 and r.json()["detail"]["error"] == "message_limit"

    demo.state["settings"] = make_settings()
    cid2 = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]
    with session_scope() as db:
        call = db.scalar(select(Call).where(Call.retell_call_id == cid2))
        call.created_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    r = demo.c.post(f"/demo/chat/{cid2}/message", headers=CODE, json={"content": "hi"})
    assert r.status_code == 410 and r.json()["detail"]["error"] == "session_expired"
    assert ("end", cid2) in demo.retell.calls


# ------------------------------------------------------------------ timeline + previews
def test_booking_timeline_appointment_and_notification_previews(demo):
    cid = "web_demo1"
    signed_post(demo.c, "/webhooks/retell", {"event": "call_started", "call": {
        "call_id": cid, "from_number": "+13035551234", "start_timestamp": 1_760_000_000_000}})
    signed_post(demo.c, "/tools/check_service_area", tool_body(cid, "x", {"zip": "80203"}))
    s = slots(demo.c, cid)[0]
    assert book(demo.c, cid, s["start"], urgency="urgent", issue_description="AC died")["status"] == "booked"

    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    assert [e["kind"] for e in ev["events"]] == [
        "call_started", "service_area_checked", "slots_found", "appointment_booked", "confirmation_sms_sent"]
    assert ev["events"][1]["sub"] == "ZIP 80203: inside our area"
    assert ev["call"]["status"] == "in_progress" and ev["call"]["outcome"] == "booked"
    a = ev["appointment"]
    assert (a["customer_name"], a["urgency"], a["added_to_calendar"], a["sms_sent"]) == ("Jamie Rivera", "urgent", True, True)
    assert "between" in a["window_label"]
    n = ev["notifications"]
    assert "$89" in n["confirmation_sms"]["body"] and n["confirmation_sms"]["to"] == "+13035551234"
    assert n["owner_summary"]["final"] is False and "Jamie Rivera" in n["owner_summary"]["body"]

    signed_post(demo.c, "/webhooks/retell", {"event": "call_ended", "call": {
        "call_id": cid, "start_timestamp": 1_760_000_000_000, "end_timestamp": 1_760_000_090_000,
        "transcript_object": [{"role": "agent", "content": "hi"}, {"role": "user", "content": "hello"}]}})
    signed_post(demo.c, "/webhooks/retell", {"event": "call_analyzed", "call": {
        "call_id": cid, "call_analysis": {"call_summary": "Booked an urgent AC visit."}}})
    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    kinds = [e["kind"] for e in ev["events"]]
    assert kinds[-3:] == ["call_ended", "summary_email_sent", "summary_ready"]
    assert ev["call"]["status"] == "ended" and ev["call"]["summary_ready"] is True
    assert ev["notifications"]["owner_summary"]["final"] is True


def test_emergency_timeline_has_owner_alert_preview(demo):
    cid = "web_gas"
    signed_post(demo.c, "/tools/flag_emergency", tool_body(cid, "x", {
        "hazard": "gas_smell", "details": "rotten eggs", "address": "9 Elm St"}, from_number=None))
    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    assert [e["kind"] for e in ev["events"]] == ["emergency_flagged", "emergency_alert_sent"]
    assert ev["events"][0]["tone"] == "danger" and ev["call"]["outcome"] == "emergency"
    alert = ev["notifications"]["owner_alert"]
    assert alert["sms"]["to"] == "+13035550100" and "9 Elm St" in alert["email"]["body"]
    assert alert["email"]["subject"].startswith("[EMERGENCY]")
    assert ev["appointment"] is None


def test_unknown_call_is_404(demo):
    r = demo.c.get("/demo/calls/nope/events", headers=CODE)
    assert r.status_code == 404 and r.json()["detail"]["error"] == "unknown_call"


# ------------------------------------------------------------------ sessions without caller ID
def test_web_session_needs_a_phone_number_to_book(demo):
    cid = "web_nophone"
    s = signed_post(demo.c, "/tools/get_available_slots",
                    tool_body(cid, "x", {}, from_number=None)).json()["slots"][0]  # no caller ID, like a web call
    args = {**ADDR, "slot_start": s["start"]}
    r = signed_post(demo.c, "/tools/book_appointment", tool_body(cid, "x", args, from_number=None)).json()
    assert r["ok"] is False and r["status"] == "phone_required" and "phone" in r["message"]
    with session_scope() as db:
        assert db.scalars(select(Appointment)).first() is None
    r = signed_post(demo.c, "/tools/book_appointment",
                    tool_body(cid, "x", {**args, "phone": "(303) 555-0142"}, from_number=None)).json()
    assert r["status"] == "booked"
    with session_scope() as db:
        assert db.scalar(select(Appointment)).phone == "+13035550142"


def test_callback_without_any_number_asks_for_one(demo):
    args = {"caller_name": "Sam Lee", "message": "call me"}
    r = signed_post(demo.c, "/tools/request_callback", tool_body("web_cb", "x", args, from_number=None)).json()
    assert r["ok"] is False and r["error"] == "callback_number_required"
    r = signed_post(demo.c, "/tools/request_callback", tool_body(
        "web_cb", "x", {**args, "callback_number": "3035550177"}, from_number=None)).json()
    assert r["ok"] is True


def test_chat_envelope_and_chat_webhooks(demo):
    cid = "chat_abc"
    body = {"name": "check_service_area", "args": {"zip": "80203"}, "call": {"chat_id": cid}}
    assert signed_post(demo.c, "/tools/check_service_area", body).json()["in_service_area"] is True
    signed_post(demo.c, "/webhooks/retell", {"event": "chat_started", "chat": {"chat_id": cid}})
    signed_post(demo.c, "/webhooks/retell", {"event": "chat_ended", "chat": {
        "chat_id": cid, "start_timestamp": 1_760_000_000_000, "end_timestamp": 1_760_000_060_000,
        "message_with_tool_calls": [{"role": "agent", "content": "hi"}, {"role": "user", "content": "zip 80203"},
                                    {"role": "tool_call_invocation", "name": "x"}]}})
    signed_post(demo.c, "/webhooks/retell", {"event": "chat_analyzed", "chat": {
        "chat_id": cid, "chat_analysis": {"chat_summary": "Asked about service area."}}})
    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    assert ev["call"]["summary_ready"] and ev["call"]["duration"] == 60
    assert "Chat started" in [e["label"] for e in ev["events"]]
    with session_scope() as db:
        c = db.scalar(select(Call).where(Call.retell_call_id == cid))
        assert c.summary == "Asked about service area." and "user: zip 80203" in c.transcript


# ------------------------------------------------------------------ day view, stats, reset
def test_day_view_marks_booked_window(demo):
    cid = "web_day"
    s = slots(demo.c, cid)[0]
    book(demo.c, cid, s["start"])
    day = datetime.fromisoformat(s["start"]).date().isoformat()
    r = demo.c.get(f"/demo/appointments?date={day}", headers=CODE).json()
    assert r["date"] == day and not r["closed"] and len(r["appointments"]) == 1
    booked = [w for w in r["windows"] if w["status"] == "booked"]
    assert len(booked) == 1 and booked[0]["start"] == s["start"]
    assert booked[0]["appointment"]["customer_name"] == "Jamie Rivera"
    assert {w["status"] for w in r["windows"]} <= {"booked", "open", "past"}


def test_day_view_closed_day_and_bad_date(demo):
    r = demo.c.get("/demo/appointments?date=2026-10-25", headers=CODE).json()  # a Sunday
    assert r["closed"] is True and r["windows"] == []
    assert demo.c.get("/demo/appointments?date=banana", headers=CODE).status_code == 422
    assert demo.c.get("/demo/appointments", headers=CODE).status_code == 200  # defaults to today


def test_stats_count_todays_outcomes(demo):
    assert demo.c.get("/demo/stats", headers=CODE).json() == {
        "calls_today": 0, "booked": 0, "emergencies": 0, "callbacks": 0}
    s = slots(demo.c, "c_book")[0]
    book(demo.c, "c_book", s["start"])
    signed_post(demo.c, "/tools/flag_emergency", tool_body("c_gas", "x", {"hazard": "co_alarm"}))
    signed_post(demo.c, "/tools/request_callback", tool_body("c_cb", "x", {"caller_name": "Pat", "message": "hi"}))
    signed_post(demo.c, "/tools/check_service_area", tool_body("c_info", "x", {"zip": "80301"}))
    assert demo.c.get("/demo/stats", headers=CODE).json() == {
        "calls_today": 4, "booked": 1, "emergencies": 1, "callbacks": 1}


def test_reset_clears_demo_data_and_calendar_but_keeps_rate_limits(demo):
    demo.c.post("/demo/web-call", headers=CODE)
    s = slots(demo.c, "c_book")[0]
    book(demo.c, "c_book", s["start"])
    assert len(get_calendar().events) == 1
    assert demo.c.post("/demo/reset").status_code == 401  # needs the code

    r = demo.c.post("/demo/reset", headers=CODE).json()
    assert r["ok"] and r["appointments_deleted"] == 1 and r["calendar_events_deleted"] == 1
    assert get_calendar().events == {}
    with session_scope() as db:
        assert db.scalars(select(Call)).first() is None
        assert db.scalars(select(Appointment)).first() is None
        assert db.scalars(select(CallEvent)).first() is None
        assert db.scalars(select(DemoHit)).first() is not None  # ledger survives
    # the freed slot can be sold again
    assert book(demo.c, "c_again", s["start"])["status"] == "booked"
    assert demo.c.get("/demo/stats", headers=CODE).json()["calls_today"] == 1


# ------------------------------------------------------------------ branding + CORS
def test_branding_is_public_and_contains_no_secrets(demo):
    r = demo.c.get("/demo/branding")
    b = r.json()
    assert b["company"]["name"] == "Summit Heating & Air" and b["accent_color"].startswith("#")
    assert [s["id"] for s in b["scenarios"]] == ["urgent-booking", "gas-emergency", "out-of-area"]
    assert b["limits"]["max_call_seconds"] == 240 and b["company"]["dispatch_fee"] == "$89"
    for secret in (TEST_KEY, "letmein", "agent_voice", "owner@"):
        assert secret not in r.text
    logo = demo.c.get(b["logo_url"])
    assert logo.status_code == 200 and logo.headers["content-type"] == "image/svg+xml"


def test_branding_validation(tmp_path):
    from app.branding import load_branding

    bad = (tmp_path / "b.yaml")
    bad.write_text("agency: {name: A}\nbadge: b\ntagline: t\naccent_color: blue\nlogo_path: x.svg\nscenarios: []\n")
    with pytest.raises(ValueError, match="accent_color"):
        load_branding(bad)


def test_cors_only_for_the_demo_site(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main

    monkeypatch.setattr(main, "get_settings", lambda: make_settings(demo_allowed_origins="https://demo.example.com/"))
    c = TestClient(main.create_app())
    ok = c.options("/demo/session", headers={"Origin": "https://demo.example.com",
                                             "Access-Control-Request-Method": "GET",
                                             "Access-Control-Request-Headers": "x-demo-code"})
    assert ok.headers.get("access-control-allow-origin") == "https://demo.example.com"
    assert "x-demo-code" in ok.headers.get("access-control-allow-headers", "").lower()
    bad = c.options("/demo/session", headers={"Origin": "https://evil.example.com",
                                              "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_transcript_snapshots_from_tool_calls_give_a_near_live_transcript(demo):
    cid = "web_live"
    body = tool_body(cid, "check_service_area", {"zip": "80203"})
    body["call"]["transcript"] = "Agent: Hi, how can I help?\nUser: my AC died"
    signed_post(demo.c, "/tools/check_service_area", body)
    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    assert ev["call"]["transcript"] == [{"role": "agent", "content": "Hi, how can I help?"},
                                        {"role": "user", "content": "my AC died"}]
    # a later, longer snapshot replaces it; a shorter/stale one never does
    body["call"]["transcript"] += "\nAgent: What's your ZIP?"
    signed_post(demo.c, "/tools/check_service_area", body)
    body["call"]["transcript"] = "Agent: Hi"
    signed_post(demo.c, "/tools/check_service_area", body)
    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    assert len(ev["call"]["transcript"]) == 3
