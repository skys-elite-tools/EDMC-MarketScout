"""Rename visited system table for clarity."""
from __future__ import annotations

MIGRATION_ID = "0009_rename_systems_to_systems_visited"
DESCRIPTION = "Rename systems table to systems_visited"


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def apply(conn) -> None:
    if table_exists(conn, "systems") and not table_exists(conn, "systems_visited"):
        conn.execute("ALTER TABLE systems RENAME TO systems_visited")

    if table_exists(conn, "systems_visited"):
        conn.execute("DROP INDEX IF EXISTS idx_systems_name")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_systems_visited_name ON systems_visited(system_name)")
