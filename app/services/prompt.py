"""Render prompts/agent_prompt.md from company.yaml. Syntax: {{name}} (no logic, no dependencies)."""
from __future__ import annotations

import re
from pathlib import Path

from app.company import CompanyConfig

_VAR = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
# Resolved by Retell at call time, so they must survive our rendering untouched.
RETELL_RUNTIME_VARS = {"user_number", "agent_number", "call_id"}


def opening_instruction(greeting: str, channel: str) -> str:
    if channel == "chat":
        return (
            f'The chat window has already shown the visitor this greeting: "{greeting}" '
            "Do NOT greet again or repeat it. Reply directly to their first message, and ask only for what "
            "you still need. This is a text chat, so keep replies short."
        )
    return (
        f'The call opens with this greeting, already spoken for you: "{greeting}" '
        "Do not say it again. Carry on from whatever the caller says next."
    )


def render_prompt(template: str, cfg: CompanyConfig, channel: str = "voice") -> str:
    values = cfg.prompt_variables()
    values["opening"] = opening_instruction(values["greeting"], channel)
    # Retell's timezone-aware clock; the literal is emitted after substitution (single pass).
    values["current_time_var"] = "{{current_time_" + cfg.company.timezone + "}}"

    missing: set[str] = set()

    def sub(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in values:
            return values[name]
        if name in RETELL_RUNTIME_VARS:
            return m.group(0)
        missing.add(name)
        return m.group(0)

    out = _VAR.sub(sub, template)
    if missing:
        raise ValueError(f"prompt uses variables not defined in company.yaml: {sorted(missing)}")
    return out


def load_and_render(path: str | Path, cfg: CompanyConfig, channel: str = "voice") -> str:
    return render_prompt(Path(path).read_text(encoding="utf-8"), cfg, channel)
