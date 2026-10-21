"""Parse the request Retell sends to a custom function.

Voice calls send ``{"name", "call": {"call_id", "from_number", ...}, "args": {...}}``. Chat sessions are
not documented to look identical: the session may be under ``call`` or ``chat``, keyed ``chat_id`` or
``call_id``, or sit at the top level, and ``args`` can arrive as a JSON string. Rather than guess one
shape we accept all of them, and when none matches we describe the *structure* (key names only, never
values: they hold caller PII) so a rejected request can be diagnosed from the logs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

ID_KEYS = ("call_id", "chat_id")
NON_ARG_KEYS = {"call", "chat", "name", "args", *ID_KEYS}


@dataclass
class Envelope:
    call_id: str | None
    from_number: str | None
    args: dict
    transcript_source: dict = field(default_factory=dict)  # the call/chat object (for transcript snapshots)
    shape: dict = field(default_factory=dict)  # key names only, safe to log


def _containers(data: dict) -> list[dict]:
    named = [data[k] for k in ("call", "chat") if isinstance(data.get(k), dict)]
    nested = [v for k, v in data.items() if isinstance(v, dict) and k not in ("call", "chat", "args")]
    return [*named, data, *nested]


def describe_shape(data: Any) -> dict:
    """Structure only: top-level keys, and the keys of each nested object."""
    if not isinstance(data, dict):
        return {"type": type(data).__name__}
    return {
        "keys": sorted(data),
        "nested": {k: sorted(v) for k, v in data.items() if isinstance(v, dict)},
        "args_type": type(data.get("args")).__name__ if "args" in data else None,
    }


def _args(data: dict) -> dict:
    raw = data.get("args")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):  # some senders stringify the arguments
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except ValueError:
            pass
    # "Payload: args only" mode: the body *is* the arguments
    return {k: v for k, v in data.items() if k not in NON_ARG_KEYS}


def parse_envelope(data: Any) -> Envelope:
    if not isinstance(data, dict):
        return Envelope(None, None, {}, shape=describe_shape(data))
    call_id = from_number = None
    source: dict = {}
    for c in _containers(data):
        if call_id is None:
            for key in ID_KEYS:
                v = c.get(key)
                if isinstance(v, str) and v:
                    call_id, source = v, c
                    break
        if from_number is None and isinstance(c.get("from_number"), str):
            from_number = c["from_number"]
    return Envelope(call_id, from_number, _args(data), source, describe_shape(data))
