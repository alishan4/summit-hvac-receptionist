"""Thin Retell REST client for the demo site. The API key lives here, server-side, never in the browser."""
from __future__ import annotations

import httpx

from app.settings import get_settings

BASE = "https://api.retellai.com"


class RetellApiError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"retell {status}: {detail}")
        self.status = status
        self.detail = detail


class RetellApi:
    def __init__(self, api_key: str) -> None:
        self._key = api_key

    def _post(self, path: str, body: dict) -> dict:
        try:
            r = httpx.post(BASE + path, json=body, headers={"Authorization": f"Bearer {self._key}"}, timeout=25)
        except httpx.HTTPError as exc:
            raise RetellApiError(502, f"network: {type(exc).__name__}") from exc
        if r.status_code >= 400:
            raise RetellApiError(r.status_code, r.text[:300])
        return r.json() if r.content else {}

    def create_web_call(self, agent_id: str, max_duration_ms: int, dynamic_variables: dict[str, str]) -> dict:
        """POST /v3/create-web-call -> {call_id, access_token, transport, ice_servers, expires_at}."""
        return self._post("/v3/create-web-call", {
            "agent_id": agent_id,
            "metadata": {"source": "demo-site"},
            "retell_llm_dynamic_variables": dynamic_variables,
            # per-call cap: real phone calls on the same agent stay unrestricted
            "agent_override": {"agent": {"max_call_duration_ms": max_duration_ms}},
        })

    def create_chat(self, agent_id: str, dynamic_variables: dict[str, str]) -> dict:
        return self._post("/create-chat", {
            "agent_id": agent_id,
            "metadata": {"source": "demo-site"},
            "retell_llm_dynamic_variables": dynamic_variables,
        })

    def create_chat_completion(self, chat_id: str, content: str) -> dict:
        return self._post("/create-chat-completion", {"chat_id": chat_id, "content": content})

    def end_chat(self, chat_id: str) -> None:
        self._post(f"/end-chat/{chat_id}", {})


def get_retell_api() -> RetellApi:
    return RetellApi(get_settings().retell_api_key)
