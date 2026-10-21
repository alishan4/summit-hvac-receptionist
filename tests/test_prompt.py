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
