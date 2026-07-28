"""Track the baseline timestamp used for trip route progress."""
from __future__ import annotations

MIGRATION_ID = "0011_trip_route_progress_started"
DESCRIPTION = "Add trip route progress start timestamp"


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply(conn) -> None:
    add_column_if_missing(conn, "trip_routes", "progress_started_datetime", "TEXT")
    conn.execute(
        """
        UPDATE trip_routes
        SET progress_started_datetime = COALESCE(progress_started_datetime, imported_datetime)
        """
    )
