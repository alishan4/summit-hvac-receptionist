from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.settings import get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Neon/Heroku-style 'postgres://' and plain 'postgresql://' -> psycopg v3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    url = normalize_database_url(s.database_url)
    if url.startswith("sqlite"):
        if s.serverless:  # read-only filesystem, and a file DB would not be shared across instances
            raise RuntimeError("SQLite cannot be used on Vercel. Set DATABASE_URL to your Neon pooled connection string.")
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    # Postgres: Neon's pooled endpoint (PgBouncer, transaction mode) does the pooling, so we keep
    # no connections between invocations. PgBouncer in transaction mode can't do server-side
    # prepared statements, hence prepare_threshold=None.
    return create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})


@lru_cache
def _factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)


def init_db() -> None:
    """Create tables. Called by scripts/init_db.py and tests - never at app startup."""
    from app import models  # noqa: F401  (register tables)

    Base.metadata.create_all(get_engine())


def get_db() -> Iterator[Session]:
    with _factory()() as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    """For background tasks outside the request dependency graph."""
    with _factory()() as session:
        yield session
