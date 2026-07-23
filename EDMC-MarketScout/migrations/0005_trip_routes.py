"""Add imported trip route storage."""
from __future__ import annotations

MIGRATION_ID = "0005_trip_routes"
DESCRIPTION = "Add Spansh tourist trip route tables"


def apply(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS trip_routes (
            route_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT NOT NULL,
            source TEXT,
            spansh_job_id TEXT,
            spansh_search_id TEXT,
            source_system TEXT,
            final_destination_system TEXT,
            jump_range_ly REAL,
            loop_route INTEGER DEFAULT 0,
            imported_datetime TEXT NOT NULL,
            active INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS trip_route_stops (
            route_id INTEGER NOT NULL,
            stop_index INTEGER NOT NULL,
            system_address INTEGER,
            system_name_snapshot TEXT NOT NULL,
            leg_distance_ly REAL,
            jumps INTEGER,
            x REAL,
            y REAL,
            z REAL,
            PRIMARY KEY(route_id, stop_index),
            FOREIGN KEY(route_id) REFERENCES trip_routes(route_id)
        );

        CREATE INDEX IF NOT EXISTS idx_trip_routes_active ON trip_routes(active, imported_datetime);
        CREATE INDEX IF NOT EXISTS idx_trip_route_stops_system ON trip_route_stops(system_address, system_name_snapshot);
        """
    )
