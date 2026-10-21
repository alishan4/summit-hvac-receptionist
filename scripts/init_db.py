#!/usr/bin/env python
"""Create the database tables (idempotent). Run once per environment, and after schema changes.

    DATABASE_URL='postgresql://...neon.tech/neondb?sslmode=require' python scripts/init_db.py

Uses DATABASE_URL from the environment / .env. Use Neon's *direct* (non-pooled) string for this
one-off if you like; the pooled one works too. Never runs automatically at app startup.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect  # noqa: E402

from app.db import get_engine, init_db  # noqa: E402


def main() -> int:
    init_db()
    tables = sorted(inspect(get_engine()).get_table_names())
    print(f"ok - {get_engine().dialect.name}: tables = {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
