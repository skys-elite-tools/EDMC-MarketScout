"""SQLite migration runner for EDMC-MarketScout.

Migration files live in `migrations/` and expose:

    MIGRATION_ID = "0001_baseline"
    DESCRIPTION = "..."
    def apply(conn): ...

Each migration must be safe to run once on a user's local SQLite database.
The runner records successful migrations in `schema_migrations`.
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List

MIGRATIONS_TABLE = "schema_migrations"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migrations_dir() -> Path:
    return Path(__file__).resolve().parent / "migrations"


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            migration_id TEXT PRIMARY KEY,
            description TEXT,
            applied_datetime TEXT NOT NULL
        )
        """
    )


def applied_migrations(conn: sqlite3.Connection) -> set[str]:
    ensure_migrations_table(conn)
    return {
        str(row[0])
        for row in conn.execute(f"SELECT migration_id FROM {MIGRATIONS_TABLE}").fetchall()
    }


def migration_files() -> List[Path]:
    root = migrations_dir()
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.glob("*.py")
        if path.name != "__init__.py" and not path.name.startswith("_")
    )


def load_migration(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(f"marketscout_migration_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load migration {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not getattr(module, "MIGRATION_ID", ""):
        raise ValueError(f"Migration {path.name} is missing MIGRATION_ID")
    if not callable(getattr(module, "apply", None)):
        raise ValueError(f"Migration {path.name} is missing apply(conn)")
    return module


def run_migrations(conn: sqlite3.Connection) -> List[str]:
    """Run unapplied migrations and return the applied migration ids."""
    ensure_migrations_table(conn)
    applied = applied_migrations(conn)
    newly_applied: List[str] = []

    for path in migration_files():
        migration = load_migration(path)
        migration_id = str(migration.MIGRATION_ID)
        if migration_id in applied:
            continue
        description = str(getattr(migration, "DESCRIPTION", ""))
        with conn:
            migration.apply(conn)
            conn.execute(
                f"""
                INSERT INTO {MIGRATIONS_TABLE}(migration_id, description, applied_datetime)
                VALUES (?, ?, ?)
                """,
                (migration_id, description, now_utc_iso()),
            )
        applied.add(migration_id)
        newly_applied.append(migration_id)

    return newly_applied
