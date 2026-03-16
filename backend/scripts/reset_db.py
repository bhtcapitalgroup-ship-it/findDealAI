#!/usr/bin/env python3
"""Reset the RealDeal AI database — drops all tables and re-runs migrations.

Usage:
    python scripts/reset_db.py           # run from backend/
    make reset-db                         # run from project root via Makefile

WARNING: This destroys ALL data. Use only in development.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Ensure backend package is importable
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from app.core.database import engine
from app.models.base import Base

# Import all models so metadata is fully populated
import app.models  # noqa: F401


async def drop_all_tables() -> None:
    """Drop every table known to the ORM metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def run_migrations() -> None:
    """Execute `alembic upgrade head` from the backend directory."""
    alembic_ini = _backend_root / "alembic.ini"
    if not alembic_ini.exists():
        print("[!] alembic.ini not found — creating tables via ORM metadata instead.")
        asyncio.run(_create_tables_fallback())
        return

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(_backend_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[!] Alembic migration failed:")
        print(result.stderr)
        print("[*] Falling back to ORM metadata.create_all ...")
        asyncio.run(_create_tables_fallback())
    else:
        print(result.stdout)
        print("[+] Migrations applied successfully.")


async def _create_tables_fallback() -> None:
    """Create tables directly from SQLAlchemy metadata (no Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("[+] Tables created via metadata.create_all.")


def main() -> None:
    env = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))
    if env not in ("development", "test", "local"):
        print(f"[!!] REFUSING to reset database in '{env}' environment.")
        print("     Set ENVIRONMENT=development to proceed.")
        sys.exit(1)

    print("=" * 60)
    print("  RealDeal AI — Database Reset")
    print("=" * 60)
    print()
    print("[*] Dropping all tables ...")
    asyncio.run(drop_all_tables())
    print("[+] All tables dropped.")
    print()
    print("[*] Running migrations ...")
    run_migrations()
    print()
    print("=" * 60)
    print("  Database reset complete.")
    print("  Run `make seed` to re-populate demo data.")
    print("=" * 60)


if __name__ == "__main__":
    main()
