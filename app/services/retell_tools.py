"""Retell tool (custom function) definitions. Single source of truth for scripts/setup_retell_agent.py."""
from __future__ import annotations

from app.schemas import Hazard, IssueType, Urgency


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


def build_tools(base_url: str, timeout_ms: int = 15000) -> list[dict]:
    base = base_url.rstrip("/")

    def custom(name: str, description: str, parameters: dict, saying: str | None = None) -> dict:
        tool = {
            "type": "custom",
            "name": name,
            "description": description,
            "url": f"{base}/tools/{name}",
            "parameters": parameters,
            "timeout_ms": timeout_ms,
            "speak_during_execution": bool(saying),
        }
        if saying:
            tool["execution_message_description"] = saying
        return tool

    return [
        custom(
            "check_service_area",
            "Check whether the caller's ZIP code is inside the service area. Call as soon as you have the ZIP.",
            _obj({"zip": {"type": "string", "description": "5-digit ZIP code"}}, ["zip"]),
        ),
        custom(
            "get_available_slots",
            "Get the next open arrival windows from the technician calendar. Only offer what this returns.",
            _obj({"when": {"type": "string", "description": "The caller's own words about timing, e.g. 'tomorrow morning', 'friday afternoon', 'oct 24'. Omit if they have no preference. NEVER compute or guess a calendar date yourself."}}, []),
            "Say a short phrase like 'Let me check the schedule.'",
        ),
        custom(
            "book_appointment",
            "Book the chosen arrival window. Only call after: slot chosen, read-back confirmed, fee accepted. Never set the two confirmation flags to true unless the caller actually said so.",
            _obj(
                {
                    "customer_name": {"type": "string"},
                    "phone": {"type": "string", "description": "Callback number. Omit to use the caller ID."},
                    "address": {"type": "string", "description": "Street address as confirmed with the caller"},
                    "zip": {"type": "string"},
                    "issue_type": {"type": "string", "enum": [e.value for e in IssueType]},
                    "issue_description": {"type": "string", "description": "One or two sentences on the problem"},
                    "urgency": {"type": "string", "enum": [e.value for e in Urgency]},
                    "system_info": {"type": "string", "description": "System type and age, if known"},
                    "slot_start": {"type": "string", "description": "The exact `start` value of the chosen slot"},
                    "details_confirmed": {"type": "boolean", "description": "true only after you read back ALL details and the caller said the read-back is right"},
                    "fee_accepted": {"type": "boolean", "description": "true only after you stated the fee and the caller explicitly said yes"},
                },
                ["customer_name", "address", "zip", "issue_type", "slot_start", "details_confirmed", "fee_accepted"],
            ),
            "Say a short phrase like 'Booking that now.'",
        ),
        custom(
            "flag_emergency",
            "Call IMMEDIATELY if the caller reports a gas smell, CO alarm, smoke, sparks, or burning smell. "
            "Alerts the owner. After calling, give the safety instructions. Never book.",
            _obj(
                {
                    "hazard": {"type": "string", "enum": [e.value for e in Hazard]},
                    "details": {"type": "string"},
                    "caller_name": {"type": "string"},
                    "address": {"type": "string"},
                },
                ["hazard"],
            ),
        ),
        custom(
            "request_callback",
            "Save a message for a human callback: caller wants a person, is out of area and wants a message, "
            "or you can't help.",
            _obj(
                {
                    "caller_name": {"type": "string"},
                    "callback_number": {"type": "string", "description": "Omit to use the caller ID"},
                    "message": {"type": "string"},
                    "best_time": {"type": "string"},
                },
                ["caller_name", "message"],
            ),
        ),
        {
            "type": "end_call",
            "name": "end_call",
            "description": "End the call after a polite goodbye, or after emergency instructions are understood.",
        },
    ]
