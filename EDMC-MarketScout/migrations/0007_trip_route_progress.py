"""Track progress through imported trip routes."""
from __future__ import annotations

MIGRATION_ID = "0007_trip_route_progress"
DESCRIPTION = "Add progress marker fields to trip routes"


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply(conn) -> None:
    add_column_if_missing(conn, "trip_routes", "progress_stop_index", "INTEGER DEFAULT 0")
    add_column_if_missing(conn, "trip_routes", "progress_updated_datetime", "TEXT")
    conn.execute("UPDATE trip_routes SET progress_stop_index = COALESCE(progress_stop_index, 0)")
    conn.execute(
        """
        UPDATE trip_routes
        SET progress_updated_datetime = COALESCE(progress_updated_datetime, imported_datetime)
        """
    )
