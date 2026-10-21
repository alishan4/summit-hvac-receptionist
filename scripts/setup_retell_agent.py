#!/usr/bin/env python
"""Create or update the Retell LLM + agent from company.yaml, the prompt template and tool definitions.

    python scripts/setup_retell_agent.py            # create (first run) / update (later runs)
    python scripts/setup_retell_agent.py --dry-run  # print payloads, call nothing

IDs are kept in .retell_agent.json so re-running updates in place instead of duplicating.
Re-run after any change to company.yaml, the prompt, or PUBLIC_BASE_URL (new ngrok URL).
Attaching the phone number to the agent is done in the Retell dashboard (see README).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.company import load_company  # noqa: E402
from app.services.prompt import load_and_render  # noqa: E402
from app.services.retell_tools import build_tools  # noqa: E402
from app.settings import get_settings  # noqa: E402

API = "https://api.retellai.com"
STATE = ROOT / ".retell_agent.json"


def build_payloads(llm_id: str | None = None, chat_llm_id: str | None = None) -> tuple[dict, dict, dict, dict]:
    s = get_settings()
    cfg = load_company(s.company_config_path)
    llm: dict = {
        "general_prompt": load_and_render(s.prompt_path, cfg),
        "begin_message": " ".join(cfg.greeting.split()),
        "general_tools": build_tools(s.public_base_url),
    }
    if s.retell_llm_model:
        llm["model"] = s.retell_llm_model
    # Chat gets its own copy of the LLM: same tools, same prompt except the opening. Retell's chat emits the
    # LLM's begin_message on the first turn (which swallowed the visitor's first message), and the website
    # already shows the greeting, so the chat LLM waits for the visitor and never greets.
    chat_llm: dict = {
        **llm,
        "general_prompt": load_and_render(s.prompt_path, cfg, channel="chat"),
        "begin_message": "",
    }
    agent: dict = {
        "agent_name": f"{cfg.company.name} - After Hours",
        "voice_id": s.retell_voice_id,
        "language": "en-US",
        "webhook_url": f"{s.public_base_url.rstrip('/')}/webhooks/retell",
        "webhook_events": ["call_started", "call_ended", "call_analyzed"],
        "interruption_sensitivity": 0.8,
        "enable_backchannel": True,
        "end_call_after_silence_ms": 30000,
        "max_call_duration_ms": s.phone_max_call_seconds * 1000,
        "response_engine": {"type": "retell-llm", "llm_id": llm_id or "<llm_id>"},
    }
    # Text chat agent: runs the chat LLM above (same tools as voice).
    chat: dict = {
        "agent_name": f"{cfg.company.name} - After Hours (chat)",
        "language": "en-US",
        "webhook_url": f"{s.public_base_url.rstrip('/')}/webhooks/retell",
        "webhook_events": ["chat_started", "chat_ended", "chat_analyzed"],
        "response_engine": {"type": "retell-llm", "llm_id": chat_llm_id or "<chat_llm_id>"},
    }
    return llm, agent, chat, chat_llm


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-chat", action="store_true", help="skip the text-chat agent (demo site chat tab)")
    args = ap.parse_args()
    s = get_settings()

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    llm_payload, agent_payload, chat_payload, chat_llm_payload = build_payloads(state.get("llm_id"), state.get("chat_llm_id"))

    if args.dry_run:
        print(json.dumps({"llm": llm_payload, "agent": agent_payload, "chat_llm": chat_llm_payload, "chat_agent": chat_payload}, indent=2))
        return 0
    if not s.retell_api_key:
        print("RETELL_API_KEY is not set", file=sys.stderr)
        return 1
    if not s.public_base_url.startswith("https://"):
        print("PUBLIC_BASE_URL must be a public https URL (e.g. your ngrok URL)", file=sys.stderr)
        return 1

    with httpx.Client(base_url=API, headers={"Authorization": f"Bearer {s.retell_api_key}"}, timeout=30) as http:
        def call(method: str, path: str, body: dict) -> dict:
            r = http.request(method, path, json=body)
            if r.status_code >= 400:
                print(f"{method} {path} -> {r.status_code}: {r.text}", file=sys.stderr)
                r.raise_for_status()
            return r.json()

        if llm_id := state.get("llm_id"):
            call("PATCH", f"/update-retell-llm/{llm_id}", llm_payload)
            print(f"updated LLM {llm_id}")
        else:
            llm_id = call("POST", "/create-retell-llm", llm_payload)["llm_id"]
            print(f"created LLM {llm_id}")
        agent_payload["response_engine"]["llm_id"] = llm_id

        if agent_id := state.get("agent_id"):
            call("PATCH", f"/update-agent/{agent_id}", agent_payload)
            print(f"updated agent {agent_id}")
        else:
            agent_id = call("POST", "/create-agent", agent_payload)["agent_id"]
            print(f"created agent {agent_id}")

        chat_agent_id = state.get("chat_agent_id")
        chat_llm_id = state.get("chat_llm_id")
        if not args.no_chat:
            if chat_llm_id:
                call("PATCH", f"/update-retell-llm/{chat_llm_id}", chat_llm_payload)
                print(f"updated chat LLM {chat_llm_id}")
            else:
                chat_llm_id = call("POST", "/create-retell-llm", chat_llm_payload)["llm_id"]
                print(f"created chat LLM {chat_llm_id}")
            chat_payload["response_engine"]["llm_id"] = chat_llm_id
            if chat_agent_id:
                call("PATCH", f"/update-chat-agent/{chat_agent_id}", chat_payload)
                print(f"updated chat agent {chat_agent_id}")
            else:
                chat_agent_id = call("POST", "/create-chat-agent", chat_payload)["agent_id"]
                print(f"created chat agent {chat_agent_id}")

    STATE.write_text(json.dumps({"llm_id": llm_id, "chat_llm_id": chat_llm_id, "agent_id": agent_id, "chat_agent_id": chat_agent_id}, indent=2))
    print(f"\nNext: in the Retell dashboard, set agent '{agent_payload['agent_name']}' as the inbound agent "
          "for your imported Twilio number.")
    print("\nFor the demo website, set these env vars on the API project (Vercel) and redeploy:")
    print(f"  RETELL_AGENT_ID={agent_id}")
    if chat_agent_id:
        print(f"  RETELL_CHAT_AGENT_ID={chat_agent_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
