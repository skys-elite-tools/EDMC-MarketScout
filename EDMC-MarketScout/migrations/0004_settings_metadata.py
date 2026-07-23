"""Add metadata columns to the generic settings store."""
from __future__ import annotations

MIGRATION_ID = "0004_settings_metadata"
DESCRIPTION = "Add metadata columns to settings"


def column_exists(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def apply(conn) -> None:
    if not column_exists(conn, "settings", "updated_datetime"):
        conn.execute("ALTER TABLE settings ADD COLUMN updated_datetime TEXT")
        conn.execute(
            """
            UPDATE settings
            SET updated_datetime = COALESCE(updated_datetime, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            """
        )
    if not column_exists(conn, "settings", "schema_version"):
        conn.execute("ALTER TABLE settings ADD COLUMN schema_version INTEGER DEFAULT 1")
        conn.execute("UPDATE settings SET schema_version = COALESCE(schema_version, 1)")
