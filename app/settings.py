"""Runtime/secret configuration from environment (.env). Company values live in YAML."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    vercel: str = ""  # set automatically by Vercel ("1"); selects serverless-safe behaviour
    log_level: str = "INFO"
    public_base_url: str = "http://localhost:8000"
    # Postgres (Neon pooled string) in prod. The SQLite default is for local dev/tests only.
    database_url: str = "sqlite:///./summit.db"
    company_config_path: str = "config/company.yaml"
    prompt_path: str = "prompts/agent_prompt.md"

    # Retell
    retell_api_key: str = ""
    retell_verify_signature: bool = True
    retell_voice_id: str = "11labs-Adrian"
    retell_llm_model: str = ""  # empty = Retell default

    # Demo site (/demo endpoints). Unset DEMO_ACCESS_CODE = demo endpoints disabled.
    demo_access_code: str = ""
    demo_allowed_origins: str = ""  # comma-separated, e.g. https://summit-demo.vercel.app
    retell_agent_id: str = ""  # voice agent (printed by scripts/setup_retell_agent.py)
    retell_chat_agent_id: str = ""  # chat agent sharing the same LLM
    demo_max_call_seconds: int = 240
    phone_max_call_seconds: int = 900  # real phone calls: Retell agent cap (setup script) and dashboard staleness
    demo_web_calls_per_hour: int = 5  # per IP
    demo_chats_per_hour: int = 10  # per IP
    demo_max_calls_per_day: int = 30  # global ceiling on paid sessions (voice + chat)
    demo_max_chat_messages: int = 30  # per chat session
    demo_bad_codes_per_hour: int = 10  # per IP, brute-force guard
    branding_config_path: str = "config/branding.yaml"

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


    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.demo_allowed_origins.split(",") if o.strip()]

    @property
    def serverless(self) -> bool:
        return bool(self.vercel)


@lru_cache
def get_settings() -> Settings:
    return Settings()
