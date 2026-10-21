"""Runtime/secret configuration from environment (.env). Company values live in YAML."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"
    public_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./summit.db"
    company_config_path: str = "config/company.yaml"
    prompt_path: str = "prompts/agent_prompt.md"

    # Retell
    retell_api_key: str = ""
    retell_verify_signature: bool = True
    retell_voice_id: str = "11labs-Adrian"
    retell_llm_model: str = ""  # empty = Retell default

    # Calendar
    calendar_backend: Literal["google", "fake"] = "google"
    google_calendar_id: str = ""
    google_service_account_file: str = ""
    google_service_account_json: str = ""  # alternative: raw JSON (for containers)

    # SMS
    sms_backend: Literal["twilio", "log"] = "twilio"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Email
    email_backend: Literal["smtp", "resend", "log"] = "smtp"
    email_from: str = "receptionist@example.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    resend_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
