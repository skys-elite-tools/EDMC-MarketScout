"""Seed initial rare commodity supply history from usual supply."""
from __future__ import annotations

MIGRATION_ID = "0003_seed_rare_commodity_initial_supply"
DESCRIPTION = "Seed initial rare commodity supply history from usual supply"


def apply(conn) -> None:
    conn.executescript(
        """
        INSERT INTO rare_commodities_history(commodity, supply, seen_datetime)
        SELECT rc.commodity, COALESCE(rc.usual_supply, 0), '1970-01-01T00:00:00+00:00'
        FROM rare_commodities rc
        WHERE rc.commodity IS NOT NULL
          AND trim(rc.commodity) != ''
          AND NOT EXISTS (
              SELECT 1
              FROM rare_commodities_history rch
              WHERE rch.commodity = rc.commodity
                AND COALESCE(rch.supply, 0) > 0
          )
          AND NOT EXISTS (
              SELECT 1
              FROM rare_commodities_history rch
              WHERE rch.commodity = rc.commodity
                AND rch.seen_datetime = '1970-01-01T00:00:00+00:00'
          );
        """
    )
