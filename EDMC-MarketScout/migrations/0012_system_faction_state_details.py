"""Store active, pending, and recovering faction-state details."""
from __future__ import annotations

MIGRATION_ID = "0012_system_faction_state_details"
DESCRIPTION = "Add detailed faction-state snapshots"


def apply(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS system_faction_state_details (
            system_address INTEGER NOT NULL,
            faction_name TEXT NOT NULL,
            state_kind TEXT NOT NULL,
            state_name TEXT NOT NULL,
            trend INTEGER,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (system_address, faction_name, state_kind, state_name),
            FOREIGN KEY(system_address) REFERENCES systems_visited(system_address)
        );

        CREATE INDEX IF NOT EXISTS idx_system_faction_state_details_kind_state
            ON system_faction_state_details(state_kind, state_name);
        CREATE INDEX IF NOT EXISTS idx_system_faction_state_details_faction
            ON system_faction_state_details(system_address, faction_name);
        """
    )
