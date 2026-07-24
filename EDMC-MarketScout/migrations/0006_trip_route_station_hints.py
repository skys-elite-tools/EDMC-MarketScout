"""Add optional station hints to imported trip route stops."""
from __future__ import annotations

MIGRATION_ID = "0006_trip_route_station_hints"
DESCRIPTION = "Add station hint fields to trip route stops"


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    existing = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply(conn) -> None:
    add_column_if_missing(conn, "trip_route_stops", "station_hint_name", "TEXT")
    add_column_if_missing(conn, "trip_route_stops", "station_hint_type", "TEXT")
    add_column_if_missing(conn, "trip_route_stops", "station_hint_distance_to_arrival_ls", "REAL")
    add_column_if_missing(conn, "trip_route_stops", "station_hint_large_pads", "INTEGER")
    add_column_if_missing(conn, "trip_route_stops", "station_hint_market_id", "INTEGER")
