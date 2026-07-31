"""Store the visit timestamp for each Fleet Carrier trip stop."""
from __future__ import annotations

MIGRATION_ID = "0014_carrier_trip_stop_visit_datetime"
DESCRIPTION = "Add trip-specific visit timestamps to Fleet Carrier stops"


def apply(conn) -> None:
    columns = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(carrier_trip_stops)").fetchall()
    }
    if "visited_datetime" not in columns:
        conn.execute("ALTER TABLE carrier_trip_stops ADD COLUMN visited_datetime TEXT")

    # Preserve visit information already known by MarketScout when the route
    # table is upgraded. Future journal events write this field directly.
    conn.execute(
        """
        UPDATE carrier_trip_stops
        SET visited_datetime = (
            SELECT MAX(s.last_visit_datetime)
            FROM systems_visited s
            WHERE (carrier_trip_stops.system_address IS NOT NULL
                   AND s.system_address = carrier_trip_stops.system_address)
               OR lower(s.system_name) = lower(carrier_trip_stops.system_name_snapshot)
        )
        WHERE visited_datetime IS NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_carrier_trip_stops_visited
            ON carrier_trip_stops(carrier_trip_id, visited_datetime)
        """
    )
