"""Build the agent prompts from prompts/core.md + one channel block, filled from company.yaml.

Syntax is {{name}} (no logic, no dependencies). The voice and chat prompts share one core, so a rule
changed there changes both channels; only the channel block and the opening differ.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.company import CompanyConfig

CHANNELS = ("voice", "chat")
_VAR = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
# Resolved by Retell at call time, so they must survive our rendering untouched.
RETELL_RUNTIME_VARS = {"user_number", "agent_number", "call_id"}


def opening_instruction(greeting: str, channel: str) -> str:
    if channel == "chat":
        return (
            f'The chat window has already shown the visitor this greeting: "{greeting}" '
            "Do NOT greet again or repeat it. Reply directly to their first message."
        )
    return (
        f'The call opens with this greeting, already spoken for you: "{greeting}" '
        "Do not say it again. Carry on from whatever the caller says next."
    )


def render_prompt(core: str, channel_block: str, cfg: CompanyConfig, channel: str = "voice") -> str:
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel {channel!r}; use one of {CHANNELS}")
    values = cfg.prompt_variables()
    values["opening"] = opening_instruction(values["greeting"], channel)
    template = core.replace("{{channel_block}}", channel_block.strip())

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


def build_prompt(prompt_dir: str | Path, cfg: CompanyConfig, channel: str = "voice") -> str:
    d = Path(prompt_dir)
    return render_prompt(
        (d / "core.md").read_text(encoding="utf-8"),
        (d / f"{channel}.md").read_text(encoding="utf-8"),
        cfg,
        channel,
    )
