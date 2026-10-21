from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.company import get_company
from app.logging_setup import setup_logging
from app.routers import demo, health, tools, webhooks
from app.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    setup_logging(s.log_level)
    cfg = get_company()  # fail fast on a bad company.yaml. Tables: scripts/init_db.py, never at startup.
    logging.getLogger(__name__).info("started", extra={"company": cfg.company.name, "env": s.app_env})
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="After-hours AI receptionist", lifespan=lifespan)
    origins = get_settings().cors_origins
    if origins:  # only the demo site may call /demo from a browser; tools/webhooks are server-to-server
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Demo-Code"],
            max_age=600,
        )
    app.include_router(health.router)
    app.include_router(tools.router)
    app.include_router(webhooks.router)
    app.include_router(demo.router)
    return app


app = create_app()
