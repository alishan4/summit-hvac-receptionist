"""White-label branding for the demo site (config/branding.yaml)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
LOGO_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
              ".jpeg": "image/jpeg", ".webp": "image/webp"}


class Agency(BaseModel):
    name: str
    show_powered_by: bool = True


class Scenario(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    tone: Literal["urgent", "emergency", "neutral"] = "neutral"
    script: str

    @field_validator("script")
    @classmethod
    def _clean(cls, v: str) -> str:
        return " ".join(v.split())


class Branding(BaseModel):
    agency: Agency
    badge: str
    tagline: str
    accent_color: str
    logo_path: str
    scenarios: list[Scenario]
    demo_tips: list[str] = []

    @field_validator("accent_color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not _HEX.match(v):
            raise ValueError("accent_color must be a #RRGGBB hex colour")
        return v

    @field_validator("logo_path")
    @classmethod
    def _logo(cls, v: str) -> str:
        if Path(v).suffix.lower() not in LOGO_TYPES:
            raise ValueError(f"logo must be one of {sorted(LOGO_TYPES)}")
        return v


def load_branding(path: str | Path) -> Branding:
    with open(path, encoding="utf-8") as fh:
        return Branding.model_validate(yaml.safe_load(fh))


@lru_cache
def get_branding() -> Branding:
    from app.settings import get_settings

    return load_branding(get_settings().branding_config_path)
