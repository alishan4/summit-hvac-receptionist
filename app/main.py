from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.company import get_company
from app.logging_setup import setup_logging
from app.routers import health, tools, webhooks
from app.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    setup_logging(s.log_level)
    cfg = get_company()  # fail fast on a bad company.yaml. Tables: scripts/init_db.py, never at startup.
    logging.getLogger(__name__).info("started", extra={"company": cfg.company.name, "env": s.app_env})
    yield


app = FastAPI(title="After-hours AI receptionist", lifespan=lifespan)
app.include_router(health.router)
app.include_router(tools.router)
app.include_router(webhooks.router)
