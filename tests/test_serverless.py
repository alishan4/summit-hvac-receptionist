import json

import pytest
from sqlalchemy.pool import NullPool

from app import db
from app.services import deferred
from app.settings import Settings
from tests.conftest import ROOT, signed_post
from tests.test_emergency import flag
from app.services import email, sms


def patched(monkeypatch, **env):
    monkeypatch.setattr(db, "get_settings", lambda: Settings(**env))


@pytest.mark.parametrize(
    "raw",
    ["postgres://u:p@h/db?sslmode=require", "postgresql://u:p@h/db?sslmode=require"],
)
def test_postgres_urls_use_psycopg_driver(raw):
    assert db.normalize_database_url(raw).startswith("postgresql+psycopg://u:p@h/db")
    assert db.normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"


def test_postgres_engine_is_serverless_safe(monkeypatch):
    patched(monkeypatch, database_url="postgresql://u:p@ep-x-pooler.neon.tech/db?sslmode=require", vercel="1")
    engine = db.get_engine.__wrapped__()
    assert engine.dialect.driver == "psycopg"
    assert isinstance(engine.pool, NullPool)  # no connections kept between invocations
    engine.dispose()


def test_sqlite_refused_on_vercel(monkeypatch):
    patched(monkeypatch, database_url="sqlite:///./summit.db", vercel="1")
    with pytest.raises(RuntimeError, match="Neon"):
        db.get_engine.__wrapped__()


def test_defer_runs_inline_on_serverless_and_swallows_errors(monkeypatch):
    monkeypatch.setattr(deferred, "get_settings", lambda: Settings(vercel="1"))
    calls = []

    class Boom:
        def add_task(self, *a):
            raise AssertionError("must not use BackgroundTasks on serverless")

    deferred.defer(Boom(), calls.append, 1)

    def fail():
        raise RuntimeError("sms down")

    deferred.defer(Boom(), fail)  # logged, not raised
    assert calls == [1]


def test_defer_uses_background_tasks_elsewhere(monkeypatch):
    monkeypatch.setattr(deferred, "get_settings", lambda: Settings(vercel=""))
    queued = []

    class BG:
        def add_task(self, fn, *a):
            queued.append((fn, a))

    deferred.defer(BG(), print, "x")
    assert queued == [(print, ("x",))]


def test_emergency_alert_sent_before_response_on_serverless(client, monkeypatch):
    monkeypatch.setattr(deferred, "get_settings", lambda: Settings(vercel="1"))
    r = flag(client)
    assert r.json()["ok"]
    assert len(sms.SENT_LOG) == 1 and len(email.SENT_LOG) == 1


def test_vercel_config_does_not_rewrite_paths():
    """A rewrite/route to another file makes the runtime hand FastAPI the *rewritten* path
    (e.g. /api/index) so every route 404s. Vercel's FastAPI zero-config routes originals."""
    cfg = json.loads((ROOT / "vercel.json").read_text())
    assert "rewrites" not in cfg and "routes" not in cfg
    assert not (ROOT / "api").exists(), "api/ files become their own functions and shadow the app"
    fn = cfg["functions"]["app/main.py"]
    assert "config" in fn["includeFiles"] and "prompts" in fn["includeFiles"]


def test_vercel_entrypoint_resolves_to_asgi_app():
    import importlib
    import tomllib

    ep = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["vercel"]["entrypoint"]
    module, attr = ep.split(":")
    assert (ROOT / (module.replace(".", "/") + ".py")).exists()
    app = getattr(importlib.import_module(module), attr)
    assert {"/health", "/tools/book_appointment", "/webhooks/retell"} <= set(app.openapi()["paths"])


@pytest.mark.parametrize("path,status", [("/health", 200), ("/api/index", 404), ("/api/index/health", 404)])
def test_asgi_routes_by_original_path_only(client, path, status):
    """Simulates the platform: FastAPI must be given the original path. If the runtime passes a
    rewrite destination instead, nothing matches - which is the bug this config avoids."""
    assert client.get(path).status_code == status


def test_no_runtime_filesystem_writes_in_app_code():
    """App package must not open files for writing or create dirs (Vercel FS is read-only)."""
    import re

    pattern = re.compile(r"open\([^)]*['\"][wax]\+?b?['\"]|write_text|write_bytes|mkdir|makedirs|FileHandler")
    offenders = [str(p) for p in (ROOT / "app").rglob("*.py") if pattern.search(p.read_text())]
    assert offenders == []
