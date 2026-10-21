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


def contrast_with_white(hex_color: str) -> float:
    """WCAG contrast ratio of white text on `hex_color`."""
    def lin(c: int) -> float:
        x = c / 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return 1.05 / (lum + 0.05)


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


class Service(BaseModel):
    icon: str = "wrench"
    title: str
    blurb: str


class Why(BaseModel):
    icon: str = "shield-check"
    title: str
    text: str


class Review(BaseModel):
    name: str
    area: str = ""
    text: str
    rating: int = 5


class Site(BaseModel):
    """Public website content (the homeowner view)."""

    domain: str
    phone: str
    address: str
    hours_text: str
    eyebrow: str = ""
    hero_headline: str
    hero_subline: str
    years_in_business: int
    rating: float
    review_count: int
    services: list[Service]
    why_choose: list[Why]
    reviews: list[Review]
    service_area_names: list[str]
    about: list[str]
    cta_headline: str
    cta_subline: str
    disclaimer: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if len(re.sub(r"\D", "", v)) < 10:
            raise ValueError("site.phone needs at least 10 digits")
        return v


class Dashboard(BaseModel):
    average_job_value: float = 650.0


class Branding(BaseModel):
    agency: Agency
    badge: str
    tagline: str
    accent_color: str
    logo_path: str
    scenarios: list[Scenario]
    site: Site
    dashboard: Dashboard = Dashboard()
    demo_tips: list[str] = []

    @field_validator("accent_color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not _HEX.match(v):
            raise ValueError("accent_color must be a #RRGGBB hex colour")
        ratio = contrast_with_white(v)
        if ratio < 4.5:  # buttons and the widget header put white text on this colour
            raise ValueError(
                f"accent_color {v} has only {ratio:.2f}:1 contrast with white text (WCAG AA needs 4.5:1). "
                "Pick a darker shade."
            )
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
