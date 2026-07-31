"""Add Fleet Carrier trip plan storage."""
from __future__ import annotations

MIGRATION_ID = "0013_carrier_trip_planner"
DESCRIPTION = "Add imported Fleet Carrier trip plans and ordered stops"


def apply(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS carrier_trip_routes (
            carrier_trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT NOT NULL,
            source TEXT NOT NULL,
            source_filename TEXT,
            source_sha256 TEXT,
            source_job_id TEXT,
            source_system_name TEXT,
            source_system_address INTEGER,
            destination_systems_json TEXT,
            carrier_mass REAL,
            carrier_capacity REAL,
            capacity_used REAL,
            starting_fuel_t REAL,
            starting_tritium_t REAL,
            total_distance_ly REAL,
            total_tritium_t REAL,
            imported_datetime TEXT NOT NULL,
            active INTEGER DEFAULT 0,
            progress_started_datetime TEXT,
            progress_stop_index INTEGER DEFAULT 0,
            progress_updated_datetime TEXT
        );

        CREATE TABLE IF NOT EXISTS carrier_trip_stops (
            carrier_trip_id INTEGER NOT NULL,
            stop_index INTEGER NOT NULL,
            system_address INTEGER,
            system_name_snapshot TEXT NOT NULL,
            body_name TEXT,
            leg_distance_ly REAL,
            distance_remaining_ly REAL,
            tritium_in_tank_t REAL,
            tritium_in_market_t REAL,
            tritium_used_t REAL,
            restock_amount_t REAL,
            has_icy_ring INTEGER,
            is_system_pristine INTEGER,
            must_restock INTEGER,
            is_desired_destination INTEGER,
            x REAL,
            y REAL,
            z REAL,
            source_row_json TEXT,
            stop_skipped INTEGER DEFAULT 0,
            stop_skipped_datetime TEXT,
            PRIMARY KEY(carrier_trip_id, stop_index),
            FOREIGN KEY(carrier_trip_id) REFERENCES carrier_trip_routes(carrier_trip_id)
        );

        CREATE INDEX IF NOT EXISTS idx_carrier_trip_routes_active
            ON carrier_trip_routes(active, imported_datetime);
        CREATE INDEX IF NOT EXISTS idx_carrier_trip_stops_system
            ON carrier_trip_stops(system_address, system_name_snapshot);
        """
    )
