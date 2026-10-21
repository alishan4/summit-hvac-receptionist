"""Run side effects (SMS, owner alerts, emails) after the response - or inline on serverless.

Vercel may freeze the function as soon as the response is sent, which would silently drop
BackgroundTasks (and an emergency alert is the last thing we can afford to lose). So on
serverless we run them inline, before responding. Elsewhere we keep the low-latency path.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks

from app.settings import get_settings

log = logging.getLogger(__name__)


def defer(background: BackgroundTasks, fn: Callable[..., Any], *args: Any) -> None:
    if not get_settings().serverless:
        background.add_task(fn, *args)
        return
    try:
        fn(*args)
    except Exception:  # a failed side effect must never fail the tool/webhook response
        log.exception("inline task failed", extra={"task": fn.__name__})
