"""Validated inputs for Retell custom functions."""
from __future__ import annotations

import re
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


def normalize_phone(raw: str) -> str | None:
    """US-centric normalisation to E.164. Returns None when it can't be a valid number."""
    raw = raw.strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        return f"+{digits}" if 8 <= len(digits) <= 15 else None
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+{digits}"
    return None


class IssueType(StrEnum):
    NO_HEAT = "no_heat"
    NO_COOLING = "no_cooling"
    NOISE_LEAK = "noise_leak"
    MAINTENANCE = "maintenance"
    NEW_SYSTEM_QUOTE = "new_system_quote"
    OTHER = "other"


class Urgency(StrEnum):
    ROUTINE = "routine"
    URGENT = "urgent"


class Hazard(StrEnum):
    GAS_SMELL = "gas_smell"
    CO_ALARM = "co_alarm"
    SMOKE = "smoke"
    SPARKS = "sparks"
    BURNING_SMELL = "burning_smell"
    OTHER = "other"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class CheckServiceAreaArgs(_Strict):
    zip: str = Field(min_length=3, max_length=12)


class GetSlotsArgs(_Strict):
    preferred_date: date | None = None  # YYYY-MM-DD, optional


class BookAppointmentArgs(_Strict):
    customer_name: Name
    phone: str | None = None  # defaults to caller ID
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=255)]
    zip: str = Field(min_length=5, max_length=12)
    issue_type: IssueType
    issue_description: ShortText | None = None
    urgency: Urgency = Urgency.ROUTINE
    system_info: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    slot_start: datetime

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        n = normalize_phone(v)
        if n is None:
            raise ValueError("phone number is not valid")
        return n


class FlagEmergencyArgs(_Strict):
    hazard: Hazard
    details: ShortText | None = None
    caller_name: Name | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None


class RequestCallbackArgs(_Strict):
    caller_name: Name
    callback_number: str | None = None  # defaults to caller ID
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    best_time: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None

    @field_validator("callback_number")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        n = normalize_phone(v)
        if n is None:
            raise ValueError("callback number is not valid")
        return n
