"""Typed loader for config/company.yaml - the single source of client-specific values."""
from __future__ import annotations

import re
from datetime import time
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class CompanyInfo(BaseModel):
    name: str
    spoken_name: str
    location: str
    timezone: str
    assistant_name: str

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        ZoneInfo(v)  # raises if invalid
        return v


class ServiceArea(BaseModel):
    description: str
    zips: list[str]

    @field_validator("zips")
    @classmethod
    def _zips(cls, v: list[str]) -> list[str]:
        for z in v:
            if not re.fullmatch(r"\d{5}", z):
                raise ValueError(f"invalid ZIP in config: {z!r}")
        return v


class Scheduling(BaseModel):
    business_hours: dict[str, tuple[time, time]]
    window_hours: int = Field(2, ge=1, le=8)
    window_step_hours: int = Field(2, ge=1, le=8)
    min_lead_hours: int = Field(2, ge=0)
    max_days_ahead: int = Field(7, ge=1, le=60)
    slots_to_offer: int = Field(3, ge=1, le=10)
    max_slots_per_day: int = Field(2, ge=1, le=10)

    @field_validator("business_hours", mode="before")
    @classmethod
    def _hours(cls, v: dict) -> dict:
        for day in v:
            if day not in DAYS:
                raise ValueError(f"unknown day key {day!r}; use {DAYS}")
        return v


class Pricing(BaseModel):
    dispatch_fee_usd: float = Field(ge=0)
    dispatch_fee_note: str = ""

    @property
    def fee_spoken(self) -> str:
        f = self.dispatch_fee_usd
        return f"${f:.0f}" if f == int(f) else f"${f:.2f}"


class Owner(BaseModel):
    name: str
    phone: str
    email: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not _E164.match(v):
            raise ValueError("owner.phone must be E.164, e.g. +13035550100")
        return v


class Emergency(BaseModel):
    gas_utility_name: str
    gas_utility_phone: str
    keywords_note: str = ""


class Urgency(BaseModel):
    freezing_temp_f: int = 32


class CompanyConfig(BaseModel):
    company: CompanyInfo
    greeting: str
    service_area: ServiceArea
    scheduling: Scheduling
    pricing: Pricing
    owner: Owner
    emergency: Emergency
    urgency: Urgency = Urgency()

    @model_validator(mode="after")
    def _check(self) -> "CompanyConfig":
        for day, (start, end) in self.scheduling.business_hours.items():
            if end <= start:
                raise ValueError(f"business_hours.{day}: end must be after start")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.company.timezone)

    def prompt_variables(self) -> dict[str, str]:
        """Flat values available as {{name}} in prompts/agent_prompt.md."""
        s = self.scheduling
        return {
            "company_name": self.company.name,
            "spoken_name": self.company.spoken_name,
            "location": self.company.location,
            "timezone": self.company.timezone,
            "assistant_name": self.company.assistant_name,
            "greeting": " ".join(self.greeting.split()),
            "service_area_description": self.service_area.description,
            "dispatch_fee": self.pricing.fee_spoken,
            "dispatch_fee_note": self.pricing.dispatch_fee_note,
            "window_hours": str(s.window_hours),
            "slots_to_offer": str(s.slots_to_offer),
            "gas_utility_name": self.emergency.gas_utility_name,
            "gas_utility_phone": self.emergency.gas_utility_phone,
            "freezing_temp_f": str(self.urgency.freezing_temp_f),
            "owner_name": self.owner.name,
        }


def load_company(path: str | Path) -> CompanyConfig:
    with open(path, encoding="utf-8") as fh:
        return CompanyConfig.model_validate(yaml.safe_load(fh))


@lru_cache
def get_company() -> CompanyConfig:
    from app.settings import get_settings

    return load_company(get_settings().company_config_path)
