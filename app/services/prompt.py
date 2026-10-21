"""Render prompts/agent_prompt.md from company.yaml. Syntax: {{name}} (no logic, no dependencies)."""
from __future__ import annotations

import re
from pathlib import Path

from app.company import CompanyConfig

_VAR = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
# Resolved by Retell at call time, so they must survive our rendering untouched.
RETELL_RUNTIME_VARS = {"user_number", "agent_number", "call_id"}


def render_prompt(template: str, cfg: CompanyConfig) -> str:
    values = cfg.prompt_variables()
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


def load_and_render(path: str | Path, cfg: CompanyConfig) -> str:
    return render_prompt(Path(path).read_text(encoding="utf-8"), cfg)
