"""Live-test regressions: chat tool calls 400'd, the greeting was sent twice, and stale calls stayed LIVE.

The Vercel request log for the failing request recorded only `POST /tools/check_service_area -> 400` from
Retell's axios client (the body is not logged). A 400 is returned only AFTER the signature has verified, so
the signature was fine and our envelope parser could not find a session id. The shapes below cover every
place a chat session id can plausibly sit; `test_rejection_logs_structure_not_values` makes any shape we
did not anticipate diagnosable from the logs next time.
"""
import json
import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db import session_scope
from app.models import Call, CallEvent
from app.services.envelope import describe_shape, parse_envelope
from app.services.retell_api import get_retell_api
from tests.conftest import TEST_KEY, signed_post
from tests.test_demo import CODE, FakeRetell, demo, make_settings  # noqa: F401  (demo is a fixture)

CHAT = "chat_766ec2da13d484244caff37ceae"
ARGS = {"zip": "80203"}

SHAPES = {
    "voice (call.call_id)": {"name": "check_service_area", "call": {"call_id": CHAT, "from_number": "+13035551234"}, "args": ARGS},
    "chat under call.chat_id": {"name": "check_service_area", "call": {"chat_id": CHAT, "chat_status": "ongoing"}, "args": ARGS},
    "chat under chat.chat_id": {"name": "check_service_area", "chat": {"chat_id": CHAT, "agent_id": "agent_c"}, "args": ARGS},
    "chat under chat.call_id": {"name": "check_service_area", "chat": {"call_id": CHAT}, "args": ARGS},
    "top-level chat_id": {"name": "check_service_area", "chat_id": CHAT, "args": ARGS},
    "top-level call_id": {"name": "check_service_area", "call_id": CHAT, "args": ARGS},
    "args as a JSON string": {"name": "check_service_area", "call": {"chat_id": CHAT}, "args": json.dumps(ARGS)},
    "id under an unknown key": {"name": "check_service_area", "session": {"chat_id": CHAT}, "args": ARGS},
    "args-only body + chat_id": {"chat_id": CHAT, **ARGS},
}


@pytest.mark.parametrize("name", list(SHAPES))
def test_every_envelope_shape_reaches_the_tool(client, name):
    r = signed_post(client, "/tools/check_service_area", SHAPES[name])
    assert r.status_code == 200, r.text
    assert r.json()["in_service_area"] is True
    with session_scope() as db:
        assert db.scalar(select(Call).where(Call.retell_call_id == CHAT)) is not None


def test_parser_extracts_id_number_args_and_transcript_source():
    env = parse_envelope({"name": "x", "call": {"call_id": "c1", "from_number": "+1303", "transcript": "Agent: hi"},
                          "args": {"a": 1}})
    assert (env.call_id, env.from_number, env.args) == ("c1", "+1303", {"a": 1})
    assert env.transcript_source["transcript"] == "Agent: hi"
    assert parse_envelope("not a dict").call_id is None
    assert parse_envelope({"args": "{broken"}).args == {}  # unparseable string args do not crash


def test_chat_requests_are_signature_checked_like_voice(client):
    body = SHAPES["chat under chat.chat_id"]
    assert client.post("/tools/check_service_area", json=body).status_code == 401                    # unsigned
    assert signed_post(client, "/tools/check_service_area", body, key="wrong").status_code == 401   # bad key
    assert signed_post(client, "/tools/check_service_area", body).status_code == 200                # good


def test_chat_booking_end_to_end_through_the_chat_envelope(client):
    from tests.test_booking import ADDR

    def chat_call(tool, args):
        return signed_post(client, f"/tools/{tool}", {"name": tool, "chat": {"chat_id": CHAT}, "args": args}).json()

    slot = chat_call("get_available_slots", {})["slots"][0]
    assert chat_call("book_appointment", {**ADDR, "slot_start": slot["start"], "phone": "(303) 555-0142"})["status"] == "booked"
    with session_scope() as db:
        kinds = [e.kind for e in db.scalars(select(CallEvent))]
    assert {"slots_found", "appointment_booked"} <= set(kinds)


# ---------------------------------------------------------------- requests with no id at all
def _no_id_request(client):
    return signed_post(client, "/tools/check_service_area", {"name": "check_service_area", "args": ARGS})


def test_unidentified_tool_call_is_attributed_to_the_only_live_demo_session(demo, caplog):
    cid = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]
    with caplog.at_level(logging.WARNING):
        r = _no_id_request(demo.c)
    assert r.status_code == 200 and r.json()["in_service_area"] is True
    ev = demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()
    assert "service_area_checked" in [e["kind"] for e in ev["events"]]
    assert any("attributed to the only live demo session" in rec.message for rec in caplog.records)


def test_unidentified_tool_call_is_rejected_when_ambiguous_or_no_session(demo):
    assert _no_id_request(demo.c).status_code == 400                      # nothing live
    demo.c.post("/demo/chat", headers=CODE)
    demo.c.post("/demo/chat", headers={**CODE, "x-forwarded-for": "203.0.113.5"})
    assert _no_id_request(demo.c).status_code == 400                      # two live: refuse to guess


def test_rejection_logs_structure_not_values(client, caplog):
    secret_body = {"name": "book_appointment", "weird": {"x": 1}, "args": {"customer_name": "Jamie Rivera", "address": "123 Main St"}}
    with caplog.at_level(logging.WARNING):
        r = signed_post(client, "/tools/book_appointment", secret_body)
    assert r.status_code == 400
    rec = next(x for x in caplog.records if "rejected" in x.message)
    assert rec.shape == describe_shape(secret_body)
    assert rec.shape["keys"] == ["args", "name", "weird"]
    assert rec.shape["nested"] == {"weird": ["x"], "args": ["address", "customer_name"]}  # key NAMES only
    logged = json.dumps(rec.shape)
    assert "Jamie" not in logged and "Main St" not in logged  # no PII


# ---------------------------------------------------------------- greeting
class GreetingFirstRetell(FakeRetell):
    """Reproduces the live log: the first completion returns only the begin message and ignores the user."""

    def __init__(self, greeting: str) -> None:
        super().__init__()
        self.greeting = greeting
        self.completions: list[str] = []

    def create_chat_completion(self, chat_id, content):
        self.completions.append(content)
        n = len(self.completions)
        text = self.greeting if n == 1 else f"Sorry to hear that. What's your ZIP? (reply {n})"
        return {"messages": [{"role": "agent", "content": text}]}


def test_first_message_is_answered_and_the_greeting_is_never_repeated(demo, cfg):
    from app.main import app

    fake = GreetingFirstRetell("  ".join(cfg.greeting.split()))
    app.dependency_overrides[get_retell_api] = lambda: fake
    cid = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]

    r = demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "ac is broken"}).json()
    assert fake.completions == ["ac is broken", "ac is broken"]          # asked again once
    assert r["replies"] == ["Sorry to hear that. What's your ZIP? (reply 2)"]   # real answer, no greeting

    r2 = demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "80203"}).json()
    assert len(fake.completions) == 3 and r2["replies"] == ["Sorry to hear that. What's your ZIP? (reply 3)"]


def test_greeting_is_stripped_even_when_the_first_turn_also_answers(demo, cfg):
    from app.main import app

    class Both(FakeRetell):
        def create_chat_completion(self, chat_id, content):
            return {"messages": [{"role": "agent", "content": cfg.greeting}, {"role": "agent", "content": "Got it, what's your ZIP?"}]}

    app.dependency_overrides[get_retell_api] = lambda: Both()
    cid = demo.c.post("/demo/chat", headers=CODE).json()["chat_id"]
    r = demo.c.post(f"/demo/chat/{cid}/message", headers=CODE, json={"content": "hi"}).json()
    assert r["replies"] == ["Got it, what's your ZIP?"]


def test_prompt_opening_differs_by_channel(cfg):
    from app.services.prompt import load_and_render
    from tests.conftest import ROOT

    path = ROOT / "prompts" / "agent_prompt.md"
    voice, chat = load_and_render(path, cfg), load_and_render(path, cfg, channel="chat")
    assert "already spoken for you" in voice and "Do NOT greet again" not in voice
    assert "Do NOT greet again" in chat and "text chat" in chat
    assert voice.replace("already spoken for you", "") != chat   # only the opening differs in intent
    assert "{{opening}}" not in voice and "{{opening}}" not in chat


def test_setup_script_gives_chat_its_own_llm_without_a_begin_message():
    import subprocess
    import sys

    from tests.conftest import ROOT

    r = subprocess.run([sys.executable, "scripts/setup_retell_agent.py", "--dry-run"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    p = json.loads(r.stdout)
    assert p["llm"]["begin_message"] and p["chat_llm"]["begin_message"] == ""      # voice greets, chat does not
    assert p["chat_llm"]["general_tools"] == p["llm"]["general_tools"]              # identical tools
    assert "Do NOT greet again" in p["chat_llm"]["general_prompt"]
    assert p["chat_agent"]["response_engine"]["type"] == "retell-llm"


# ---------------------------------------------------------------- stale LIVE calls + reset
def _age(call_id: str, seconds: int):
    with session_scope() as db:
        c = db.scalar(select(Call).where(Call.retell_call_id == call_id))
        c.created_at = datetime.now(UTC) - timedelta(seconds=seconds)
        db.commit()


def _status(demo, cid):
    return demo.c.get(f"/demo/calls/{cid}/events", headers=CODE).json()["call"]["status"]


def test_phone_call_leaves_live_on_end_event_or_after_the_max_duration(demo):
    for cid in ("ph_ended", "ph_stale", "ph_recent"):
        signed_post(demo.c, "/webhooks/retell", {"event": "call_started", "call": {
            "call_id": cid, "from_number": "+13035551234", "start_timestamp": int(datetime.now(UTC).timestamp() * 1000)}})
    signed_post(demo.c, "/webhooks/retell", {"event": "call_ended", "call": {
        "call_id": "ph_ended", "start_timestamp": 1, "end_timestamp": 2, "transcript_object": []}})
    _age("ph_stale", 20 * 60)   # 20 min, no end event: beyond the 15-min phone cap + grace
    _age("ph_recent", 5 * 60)   # a long but legitimate call
    assert _status(demo, "ph_ended") == "ended"
    assert _status(demo, "ph_stale") == "ended"
    assert _status(demo, "ph_recent") == "in_progress"
    rows = {r["call_id"]: r["status"] for r in demo.c.get("/demo/calls", headers=CODE).json()["calls"]}
    assert rows == {"ph_ended": "ended", "ph_stale": "ended", "ph_recent": "in_progress"}


def test_reset_clears_stale_calls_and_late_webhooks_cannot_resurrect_them(demo):
    old_start = int((datetime.now(UTC) - timedelta(hours=3)).timestamp() * 1000)
    # "Sarah Jenkins": an old phone emergency that never received call_ended
    signed_post(demo.c, "/webhooks/retell", {"event": "call_started", "call": {
        "call_id": "sarah", "from_number": "+13035559999", "start_timestamp": old_start}})
    signed_post(demo.c, "/tools/flag_emergency", {"name": "x", "call": {"call_id": "sarah", "from_number": "+13035559999"},
                                                    "args": {"hazard": "gas_smell", "caller_name": "Sarah Jenkins"}})
    _age("sarah", 3 * 3600)
    row = demo.c.get("/demo/calls", headers=CODE).json()["calls"][0]
    assert (row["caller"], row["outcome"], row["status"]) == ("Sarah Jenkins", "emergency", "ended")  # not LIVE any more

    assert demo.c.post("/demo/reset", headers=CODE).json()["calls_deleted"] == 1
    assert demo.c.get("/demo/calls", headers=CODE).json() == {"calls": []}

    # Retell's late end-of-call webhooks for that old call must not recreate a ghost row
    for ev, extra in (("call_ended", {"end_timestamp": old_start + 60_000}), ("call_analyzed", {"call_analysis": {"call_summary": "x"}})):
        r = signed_post(demo.c, "/webhooks/retell", {"event": ev, "call": {
            "call_id": "sarah", "start_timestamp": old_start, **extra}})
        assert r.json()["ignored"] == "started_before_reset"
    assert demo.c.get("/demo/calls", headers=CODE).json() == {"calls": []}

    # a call that starts after the reset is recorded normally
    signed_post(demo.c, "/webhooks/retell", {"event": "call_started", "call": {
        "call_id": "fresh", "start_timestamp": int(datetime.now(UTC).timestamp() * 1000) + 5000}})
    assert [c["call_id"] for c in demo.c.get("/demo/calls", headers=CODE).json()["calls"]] == ["fresh"]
