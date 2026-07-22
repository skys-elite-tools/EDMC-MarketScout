"""Add rare commodity history."""
from __future__ import annotations

MIGRATION_ID = "0002_rare_commodity_history"
DESCRIPTION = "Add rare commodity history"


def apply(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rare_commodities_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity TEXT NOT NULL,
            supply INTEGER,
            seen_datetime TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_rare_history_commodity_time
            ON rare_commodities_history(commodity, seen_datetime);
        CREATE INDEX IF NOT EXISTS idx_rare_history_commodity_supply
            ON rare_commodities_history(commodity, supply);

        INSERT INTO rare_commodities_history(commodity, supply, seen_datetime)
        SELECT rc.commodity, mp.supply, mp.market_price_update_datetime
        FROM market_prices mp
        JOIN rare_commodities rc
          ON lower(replace(replace(replace(replace(mp.commodity, char(160), ''), ' ', ''), '-', ''), '_', '')) =
             lower(replace(replace(replace(replace(rc.commodity, char(160), ''), ' ', ''), '-', ''), '_', ''))
        WHERE mp.supply IS NOT NULL
          AND mp.market_price_update_datetime IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM rare_commodities_history rch
              WHERE rch.commodity = rc.commodity
                AND rch.seen_datetime = mp.market_price_update_datetime
          );
        """
    )
