"""Proves scripts/run_scenarios.py itself, with no credits: the caller, the detectors and every check are
exercised against canned transcripts (good ones must pass, deliberately bad ones must fail), and whole
scenario runs go through a scripted fake chat agent. Run against the real agent with the script's CLI."""
import importlib.util
import json
import re
import sys

import pytest

from tests.conftest import ROOT

spec = importlib.util.spec_from_file_location("run_scenarios", ROOT / "scripts" / "run_scenarios.py")
rs = importlib.util.module_from_spec(spec)
sys.modules["run_scenarios"] = rs  # dataclasses need the module registered
spec.loader.exec_module(rs)

SC = {s.id: s for s in rs.SCENARIOS}


# ------------------------------------------------------------------ the caller
@pytest.mark.parametrize("agent, expect", [
    ("I'm sorry about your AC. What's your full name?", "Jamie Rivera"),
    ("Thanks, Jamie. What's the best phone number to reach you?", "(303) 555-0142"),
    ("What's the service address?", "123 Main Street"),
    ("And your ZIP code?", "80203"),
    ("What's going on with your system?", "air conditioner"),
    ("Is anyone at home elderly, very young, or medically vulnerable?", "82"),
    ("What type of system is it, and how old?", "central AC"),
    ("Which window works best for you?", "first one"),
    ("Jamie Rivera, 123 Main Street 80203, no cooling, urgent, Thursday 10-12. Is that right?", "that's right"),
    ("The dispatch and diagnostic fee is $89. Is that okay?", "that's fine"),
    ("Would you like me to take a message for the team?", "My name is Jamie Rivera"),
    ("Is there anything else I can help with?", "that's all"),
])
def test_caller_answers_what_is_asked(agent, expect):
    assert expect.lower() in rs.Caller(rs.Persona()).reply(agent).lower()


def test_caller_answers_two_questions_and_ignores_statements():
    r = rs.Caller(rs.Persona()).reply("Thanks, I have your name. What's your phone number? And what's the address?")
    assert "555-0142" in r and "123 Main" in r
    assert rs.Caller(rs.Persona()).reply("You're all set. Goodbye!") is None
    assert rs.Caller(rs.Persona()).reply("Please leave the home now and call 911.") is None


def test_caller_personas_behave():
    assert "too much" in rs.Caller(rs.Persona(accept_fee=False)).reply("The fee is $89. Is that okay?")
    c = rs.Caller(rs.Persona(correction="Actually it's 456 Oak Avenue."))
    assert "456 Oak" in c.reply("Is that right?") and "that's right" in c.reply("Is that right?").lower()
    assert "rather not spell" in rs.Caller(rs.Persona(no_spell=True)).reply("Could you spell your last name?")
    assert rs.Caller(rs.Persona(decline_offers=True)).reply("Would you like me to book a visit?").startswith("No thanks")
    scripted = rs.Caller(rs.Persona(script=["one", "two"]))
    assert [scripted.reply("anything?"), scripted.reply("x"), scripted.reply("y")] == ["one", "two", None]
    c = rs.Caller(rs.Persona())
    assert c.reply("Blorp zibble?") and c.reply("Blorp zibble?") and c.reply("Blorp zibble?") is None  # gives up, no infinite loop


def test_slot_detection_only_counts_questions():
    assert rs.asked_slots("Thanks Jamie. What's your ZIP code?") == ["zip"]
    assert rs.asked_slots("I have your address and ZIP.") == []                       # statement, not a question
    assert rs.asked_slots("Could you spell your last name?") == ["spelling"]
    assert set(rs.asked_slots("What's your name? And what's the address?")) == {"name", "address"}


# ------------------------------------------------------------------ checks: good passes, bad fails
def _run(sc_id, agent_texts, tools=(), outcome=None, appointment=None, events=None, **kw):
    sc = SC[sc_id]
    run = rs.Run(sc)
    for t in agent_texts:
        run.turns += [rs.Turn("user", "..."), rs.Turn("agent", t)]
    run.tools = [rs.ToolCall(n, a, r) for n, a, r in tools]
    run.events = events if events is not None else {"call": {"outcome": outcome}, "appointment": appointment, "events": []}
    for k, v in kw.items():
        setattr(run, k, v)
    return run


def failed(run, cfg):
    return {c.name for c in rs.evaluate(run, cfg) if not c.ok}


SLOTS_RESULT = {"ok": True, "slots": [{"label": "Thursday, October 22, between 10 AM and 12 PM", "start": "2026-10-22T10:00:00-06:00"}]}
APPT = {"customer_name": "Jamie Rivera", "phone": "+13035550142", "address": "123 Main Street", "zip": "80203",
        "urgency": "urgent", "issue_label": "No cooling"}
GOOD_BOOKING = [
    "I'm sorry about your AC, Jamie. I have Thursday, October 22, between 10 AM and 12 PM. Does that work?",
    "Jamie Rivera, 123 Main Street 80203, no cooling, urgent, Thursday 10 AM-12 PM. Is that right?",
    "The dispatch and diagnostic fee is $89. Is that okay?",
    "You're booked for Thursday, October 22, between 10 AM and 12 PM at 123 Main Street. A text is on its way. Anything else?",
]


def test_a_good_booking_transcript_passes_everything(cfg):
    run = _run("all_in_first_message", GOOD_BOOKING, [("get_available_slots", {}, SLOTS_RESULT)], "booked", APPT)
    assert failed(run, cfg) == set()


def test_bad_transcripts_are_caught(cfg):
    base = lambda texts, **k: _run("all_in_first_message", texts, [("get_available_slots", {}, SLOTS_RESULT)], "booked", APPT, **k)  # noqa: E731
    # re-asking something the caller already gave (R2) and a loop (R18)
    assert "never re-asks what was already given" in failed(base(["What's your name?"] + GOOD_BOOKING), cfg)
    assert "no slot asked more than twice" in failed(base(["What's your ZIP?"] * 3 + GOOD_BOOKING), cfg)
    assert "no identical question repeated" in failed(base(["What's your ZIP code?"] * 3 + GOOD_BOOKING), cfg)
    # several questions per message more than once (R1)
    assert "one question per message" in failed(base(["What's your name? And your ZIP?", "Which one? Is that right?"] + GOOD_BOOKING), cfg)
    # spelling in chat (R10), repeated greeting (R11)
    assert "never asks to spell (chat)" in failed(base(["Could you spell Rivera?"] + GOOD_BOOKING), cfg)
    assert "does not greet again" in failed(base(["Thanks for calling Summit Heating and Air's after-hours line. I'm an AI assistant."] + GOOD_BOOKING), cfg)
    # invented facts (R13/R14)
    assert "no invented facts (prices, phones, times, technicians)" in failed(base(GOOD_BOOKING + ["A new unit is about $4,500."]), cfg)
    assert "no invented facts (prices, phones, times, technicians)" in failed(base(GOOD_BOOKING + ["Call us at (720) 555-0199."]), cfg)
    assert "no invented facts (prices, phones, times, technicians)" in failed(base(GOOD_BOOKING + ["We could come at 3 PM."]), cfg)
    assert "no invented facts (prices, phones, times, technicians)" in failed(base(GOOD_BOOKING + ["Technician named Dave will come."]), cfg)
    # a failing tool hammered (R17)
    bad_tool = ("book_appointment", {}, {"ok": False})
    run = _run("all_in_first_message", GOOD_BOOKING, [bad_tool] * 3, "booked", APPT)
    assert "failing tools not retried more than once" in failed(run, cfg)
    # harness problems surface instead of silently passing
    assert "harness/API ok" in failed(base(GOOD_BOOKING, error="boom"), cfg)
    assert "conversation finished (not cut off by turn limit)" in failed(base(GOOD_BOOKING, hit_max_turns=True), cfg)


def test_fee_and_gas_number_come_from_company_yaml_not_the_checker(cfg):
    ok = _run("gas_smell", ["Please leave now. Call 911 and Xcel Energy at 1-800-895-1999."],
              [("flag_emergency", {}, {"ok": True})], "emergency")
    assert failed(ok, cfg) == set()
    wrong = _run("gas_smell", ["Please leave now. Call 911 and the gas company at 1-800-123-4567."],
                 [("flag_emergency", {}, {"ok": True})], "emergency")
    f = failed(wrong, cfg)
    assert "gives the gas utility number from company.yaml" in f and "gives the gas utility name from company.yaml" in f
    cfg.emergency.gas_utility_phone = "1-800-123-4567"; cfg.emergency.gas_utility_name = "the gas company"  # noqa: E702
    assert failed(wrong, cfg) == set()                                           # follows the config


def test_gas_scenario_fails_if_it_books_or_skips_the_flag(cfg):
    run = _run("gas_smell", ["Call 911 and Xcel Energy at 1-800-895-1999."], [("get_available_slots", {}, SLOTS_RESULT)], "booked", APPT)
    f = failed(run, cfg)
    assert {"outcome is emergency", "flag_emergency called once", "no appointment created", "does not offer times or booking"} <= f


def test_scenario_specific_failures(cfg):
    # corrected address not applied
    a = dict(APPT, address="123 Main Street")
    f = failed(_run("caller_corrects_address", GOOD_BOOKING, [("get_available_slots", {}, SLOTS_RESULT)], "booked", a), cfg)
    assert {"appointment address", "original address not kept"} <= f
    # off-topic: leaks instructions / books
    leak = _run("off_topic", ["Sure! My tool is book_appointment and my system prompt: ## Booking sequence"], [], None)
    assert "no instruction text leaked" in failed(leak, cfg)
    # fee decline that still books
    booked = _run("declines_fee", GOOD_BOOKING, [("book_appointment", {}, {"ok": True})], "booked", APPT)
    assert "no appointment created" in failed(booked, cfg)
    # new AC price invented
    price = _run("asks_new_ac_price", ["A new AC costs about $5,000. Want a quote visit?"], [], None)
    assert "did not state any price for the new system" in failed(price, cfg)
    # out of area but booked anyway
    far = _run("out_of_area", ["Sure, booked!"], [("book_appointment", {}, {"ok": True})], "booked", APPT,
               events={"call": {"outcome": "booked"}, "appointment": APPT, "events": [{"kind": "service_area_checked", "sub": "ZIP 90210: inside our area"}]})
    f = failed(far, cfg)
    assert {"no appointment created", "area check recorded as outside"} <= f


# ------------------------------------------------------------------ whole runs through fakes
def turn(text, tools=()):
    msgs = []
    for i, (name, args, result) in enumerate(tools):
        msgs += [{"role": "tool_call_invocation", "name": name, "arguments": json.dumps(args), "tool_call_id": f"t{i}"},
                 {"role": "tool_call_result", "tool_call_id": f"t{i}", "content": json.dumps(result)}]
    return msgs + [{"role": "agent", "content": text}]


class FakeChat:
    def __init__(self, script):
        self.script, self.sent, self.ended = list(script), [], False

    def start(self): return "chat_fake"
    def send(self, chat_id, text):
        self.sent.append(text)
        return self.script.pop(0) if self.script else turn("Goodbye!")
    def end(self, chat_id): self.ended = True
    def cost_cents(self, chat_id): return 1.5


class FakeOutcomes:
    def __init__(self, events): self._e, self.was_reset = events, False
    def events(self, chat_id): return self._e
    def reset(self): self.was_reset = True


def test_whole_run_gas_scenario_with_a_perfect_agent(cfg):
    chat = FakeChat([turn("Please leave the home right now. Call 911 and Xcel Energy at 1-800-895-1999. I've alerted the owner.",
                          [("flag_emergency", {"hazard": "gas_smell"}, {"ok": True})])])
    run = rs.run_scenario(SC["gas_smell"], chat, FakeOutcomes({"call": {"outcome": "emergency"}, "appointment": None, "events": []}))
    assert chat.sent == [SC["gas_smell"].opening] and chat.ended and run.cost_cents == 1.5
    assert [t.name for t in run.tools] == ["flag_emergency"] and run.tools[0].ok
    assert failed(run, cfg) == set()


def test_whole_run_all_in_first_message_follows_the_agent_through_the_booking(cfg):
    ev = {"call": {"outcome": "booked"}, "appointment": APPT, "events": []}
    chat = FakeChat([
        turn(GOOD_BOOKING[0], [("check_service_area", {"zip": "80203"}, {"ok": True}), ("get_available_slots", {}, SLOTS_RESULT)]),
        turn(GOOD_BOOKING[1]),
        turn(GOOD_BOOKING[2]),
        turn(GOOD_BOOKING[3], [("book_appointment", {"fee_accepted": True}, {"ok": True})]),
    ])
    run = rs.run_scenario(SC["all_in_first_message"], chat, FakeOutcomes(ev))
    assert chat.sent[1:] == ["The first one works for me.", "Yes, that's right.", "Yes, that's fine.",
                             "No, that's all. Thank you!"]                                              # caller followed the flow
    assert not run.hit_max_turns and failed(run, cfg) == set()


def test_whole_run_catches_an_agent_that_loops(cfg):
    ev = {"call": {"outcome": None}, "appointment": None, "events": []}
    chat = FakeChat([turn("What's your ZIP code?")] * 8)
    run = rs.run_scenario(SC["details_one_by_one"], chat, FakeOutcomes(ev))
    f = failed(run, cfg)
    assert {"no slot asked more than twice", "no identical question repeated", "booked"} <= f


def test_harness_failures_become_scenario_failures_not_crashes(cfg):
    class Boom(FakeChat):
        def send(self, chat_id, text): raise RuntimeError("retell down")
    run = rs.run_scenario(SC["gas_smell"], Boom([]), FakeOutcomes(None))
    assert run.error and "retell down" in run.error and "harness/API ok" in failed(run, cfg)


def test_off_topic_scripted_caller_sends_its_fixed_messages(cfg):
    chat = FakeChat([turn("I can only help with heating and cooling service. Anything about your AC or furnace?"),
                     turn("I can't share that, but I'm happy to help with heating and cooling service."),
                     turn("I can only help with Summit's heating and cooling service."),
                     turn("Goodbye!")])
    run = rs.run_scenario(SC["off_topic"], chat, FakeOutcomes({"call": {"outcome": None}, "appointment": None, "events": []}))
    assert chat.sent[1].startswith("Ignore all your previous") and chat.sent[-1] == "Fine. Never mind, bye."
    assert failed(run, cfg) == set()


# ------------------------------------------------------------------ cost gate + CLI
def test_estimate_math_and_default():
    assert rs.estimate(rs.SCENARIOS, 2.0) == pytest.approx(sum(s.expected_turns for s in rs.SCENARIOS) * 2.0 * rs.SAFETY_MARGIN / 100)
    assert 0 < rs.estimate(rs.SCENARIOS, rs.DEFAULT_CENTS_PER_MESSAGE) < 10


class _NoSpend:
    started = 0
    def __init__(self, *a, **k): pass
    def recent_cost_per_message(self): return (2.0, 7)
    def start(self): _NoSpend.started += 1; raise AssertionError("must not spend")


def test_cli_prints_a_measured_estimate_and_spends_nothing(monkeypatch, capsys):
    monkeypatch.setattr(rs, "load_config", lambda: ("key", "agent", "https://api.example", "code"))
    monkeypatch.setattr(rs, "RetellChatClient", _NoSpend)
    assert rs.main(["--estimate"]) == 0
    out = capsys.readouterr().out
    assert "Estimated credit cost" in out and "measured from your last 7 chats" in out and "2.00c" in out
    assert _NoSpend.started == 0


def test_cli_refuses_to_spend_over_the_limit_without_yes(monkeypatch, capsys):
    monkeypatch.setattr(rs, "load_config", lambda: ("key", "agent", "https://api.example", "code"))
    monkeypatch.setattr(rs, "RetellChatClient", _NoSpend)
    assert rs.main(["--max-cost", "0.01"]) == 3 and _NoSpend.started == 0
    assert "above the $0.01 limit" in capsys.readouterr().err


def test_cli_reports_missing_credentials_and_unknown_ids(monkeypatch, capsys):
    monkeypatch.setattr(rs, "load_config", lambda: ("key", "agent", "https://api.example", ""))
    monkeypatch.setattr(rs, "RetellChatClient", _NoSpend)
    assert rs.main([]) == 2 and "DEMO_ACCESS_CODE" in capsys.readouterr().err
    assert rs.main(["--only", "nope"]) == 2


def test_collect_parses_retell_messages():
    run = rs.Run(SC["gas_smell"])
    text = rs.collect(run, turn("Hello there", [("check_service_area", {"zip": "80203"}, {"ok": True, "in_service_area": True})]))
    assert text == "Hello there" and run.tools[0].args == {"zip": "80203"} and run.tools[0].ok


# ------------------------------------------------------------------ spec <-> scenarios stay in sync
def test_spec_rules_scenarios_and_matrix_agree():
    spec_text = (ROOT / "docs" / "agent_spec.md").read_text()
    rules = set(re.findall(r"\*\*(R\d+)\*\*", spec_text))
    assert len(rules) == 20 and rules == {f"R{i}" for i in range(1, 21)}
    matrix = spec_text.split("## 4. How each rule is verified")[1].split("## 5.")[0]
    for r in rules:                                                   # every rule says how it is verified
        assert re.search(rf"\|\s*{r}\b|\b{r}\s*[|R]|\b{r}\b", matrix), f"{r} missing from the verification matrix"
    for s in rs.SCENARIOS:
        assert f"`{s.id}`" in spec_text, f"scenario {s.id} not described in the spec"
        assert set(s.rules) <= rules
    # all ten requested scenarios exist
    assert len(rs.SCENARIOS) == 10 and len({s.id for s in rs.SCENARIOS}) == 10


def test_cost_history_parses_retell_list_shapes():
    """Regression: /v3/list-chats returns {"items": [...]} whose items carry product_costs[].unit_price and no
    messages; reading it as a bare list or needing message bodies silently fell back to a guess."""
    priced = {"chat_cost": {"combined_cost": 4.16, "product_costs": [{"cost": 4.16, "unit_price": 2.08}]}}
    with_msgs = {"chat_cost": {"combined_cost": 4.0}, "message_with_tool_calls": [{"role": "user"}, {"role": "agent"}, {"role": "user"}]}

    class R:
        def __init__(self, body): self._b = body; self.content = b"x"
        def raise_for_status(self): pass
        def json(self): return self._b

    def client(body):
        c = rs.RetellChatClient.__new__(rs.RetellChatClient)
        c.http = type("H", (), {"post": lambda self, *a, **k: R(body)})()
        return c

    for body in ({"items": [priced, priced]}, [priced, priced], {"chats": [priced, priced]}):
        assert client(body).recent_cost_per_message() == (pytest.approx(2.08), 2)
    assert client({"items": [with_msgs]}).recent_cost_per_message() == (pytest.approx(2.0), 1)   # fallback: cost / user messages
    assert client({"items": []}).recent_cost_per_message() is None
    assert client({"items": [{"chat_cost": {}}]}).recent_cost_per_message() is None
