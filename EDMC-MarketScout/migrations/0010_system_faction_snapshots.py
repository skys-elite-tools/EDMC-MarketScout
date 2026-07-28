"""Store latest known faction states per visited system."""
from __future__ import annotations

MIGRATION_ID = "0010_system_faction_snapshots"
DESCRIPTION = "Add system faction snapshots from journal faction lists"


def apply(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS system_faction_snapshots (
            system_address INTEGER NOT NULL,
            faction_name TEXT NOT NULL,
            faction_state TEXT,
            influence REAL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (system_address, faction_name),
            FOREIGN KEY(system_address) REFERENCES systems_visited(system_address)
        );

        CREATE INDEX IF NOT EXISTS idx_system_faction_snapshots_state
            ON system_faction_snapshots(faction_state);
        CREATE INDEX IF NOT EXISTS idx_system_faction_snapshots_updated
            ON system_faction_snapshots(updated_at);
        """
    )
