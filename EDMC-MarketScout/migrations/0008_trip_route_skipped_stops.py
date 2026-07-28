"""Allow trip route stops to be soft-skipped."""
from __future__ import annotations

MIGRATION_ID = "0008_trip_route_skipped_stops"
DESCRIPTION = "Add soft-skip fields to trip route stops"


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply(conn) -> None:
    add_column_if_missing(conn, "trip_route_stops", "stop_skipped", "INTEGER DEFAULT 0")
    add_column_if_missing(conn, "trip_route_stops", "stop_skipped_datetime", "TEXT")
    conn.execute("UPDATE trip_route_stops SET stop_skipped = COALESCE(stop_skipped, 0)")
