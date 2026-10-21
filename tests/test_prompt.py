import json
import subprocess
import sys

import pytest

from app.services.prompt import load_and_render, render_prompt
from app.services.retell_tools import build_tools
from tests.conftest import ROOT


def test_prompt_renders_company_values(cfg):
    out = load_and_render(ROOT / "prompts" / "agent_prompt.md", cfg)
    assert "Summit Heating & Air" in out and "$89" in out and "Xcel Energy" in out
    assert "{{current_time_America/Denver}}" in out and "{{user_number}}" in out  # left for Retell
    assert "{{company_name}}" not in out


def test_unknown_variable_fails_loudly(cfg):
    with pytest.raises(ValueError, match="nope"):
        render_prompt("hello {{nope}}", cfg)


def test_tools_match_endpoints():
    tools = build_tools("https://x.example/")
    names = {t["name"] for t in tools}
    assert names == {"check_service_area", "get_available_slots", "book_appointment",
                     "flag_emergency", "request_callback", "end_call"}
    assert {t["url"] for t in tools if t["type"] == "custom"} >= {"https://x.example/tools/flag_emergency"}


def test_setup_script_dry_run():
    r = subprocess.run([sys.executable, "scripts/setup_retell_agent.py", "--dry-run"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["agent"]["webhook_events"] == ["call_started", "call_ended", "call_analyzed"]


def test_prompt_enforces_call_tuning_rules(cfg):
    """Guards the behaviours tuned from test calls so a prompt edit can't silently drop them."""
    out = load_and_render(ROOT / "prompts" / "agent_prompt.md", cfg)
    fee_step = out[out.index("## Step 6"):out.index("## Step 7")]
    assert out.index("## Step 5") < out.index("## Step 6")  # fee comes after the slot is picked
    assert "$89" in fee_step and "even if the caller already mentioned a fee" in fee_step
    assert "clear yes" in fee_step
    assert "$89" not in out[:out.index("## Step 6")]  # not volunteered earlier
    safety = out[out.index("## Step 1"):out.index("## Step 2")]
    assert "Never ask" in safety and "my AC stopped working" in safety
    assert "only for what is missing" in out.lower() or "only ask for what is still missing" in out
