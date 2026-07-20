"""Baseline MarketScout schema through v0.2.4."""
from __future__ import annotations

MIGRATION_ID = "0001_baseline"
DESCRIPTION = "Baseline schema through v0.2.4"


COMMODITY_GLOBAL_STATS_COLUMNS = {
    "category": "TEXT",
    "inara_id": "INTEGER",
    "avg_sell": "INTEGER",
    "avg_buy": "INTEGER",
    "avg_profit": "INTEGER",
    "max_sell": "INTEGER",
    "min_buy": "INTEGER",
    "max_profit": "INTEGER",
    "updated_datetime": "TEXT",
}

RARE_COMMODITY_COLUMNS = {
    "inara_commodity_id": "INTEGER",
    "station_name": "TEXT",
    "system_name": "TEXT",
    "inara_location_id": "INTEGER",
    "station_distance_ls": "REAL",
    "distance_from_sol_ly": "REAL",
    "usual_supply": "INTEGER",
    "buy_price": "INTEGER",
    "galactic_average_price": "INTEGER",
    "updated_datetime": "TEXT",
}

ENGINEERS_UNLOCK_COLUMNS = {
    "engineer_system": "TEXT",
    "is_public_knowledge": "INTEGER",
    "discovered_via": "TEXT",
    "required_commodity": "TEXT",
    "required_commodity_quantity": "INTEGER",
    "other_requirements": "TEXT",
    "is_rare_commodity": "INTEGER DEFAULT 0",
    "updated_datetime": "TEXT",
}


def column_exists(conn, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def table_columns(conn, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")]


def create_rare_commodities_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rare_commodities (
            commodity TEXT PRIMARY KEY,
            inara_commodity_id INTEGER,
            station_name TEXT,
            system_name TEXT,
            inara_location_id INTEGER,
            station_distance_ls REAL,
            distance_from_sol_ly REAL,
            usual_supply INTEGER,
            buy_price INTEGER,
            galactic_average_price INTEGER,
            updated_datetime TEXT
        )
        """
    )


def remove_obsolete_rare_commodity_columns(conn) -> None:
    columns = table_columns(conn, "rare_commodities")
    obsolete = {"profit", "total_sell_price"}
    if not obsolete.intersection(columns):
        return

    desired = ["commodity", *RARE_COMMODITY_COLUMNS.keys()]
    conn.execute("ALTER TABLE rare_commodities RENAME TO rare_commodities_old")
    create_rare_commodities_table(conn)
    old_columns = set(table_columns(conn, "rare_commodities_old"))
    select_exprs = [col if col in old_columns else "NULL" for col in desired]
    conn.execute(
        f"""
        INSERT INTO rare_commodities({", ".join(desired)})
        SELECT {", ".join(select_exprs)}
        FROM rare_commodities_old
        """
    )
    conn.execute("DROP TABLE rare_commodities_old")


def apply(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS systems (
            system_address INTEGER PRIMARY KEY,
            system_name TEXT NOT NULL,
            x REAL,
            y REAL,
            z REAL,
            population INTEGER,
            security TEXT,
            system_faction_state TEXT,
            system_economy TEXT,
            system_economies_json TEXT,
            last_visit_datetime TEXT
        );

        CREATE TABLE IF NOT EXISTS stations (
            market_id INTEGER PRIMARY KEY,
            system_address INTEGER,
            station_name TEXT NOT NULL,
            station_type TEXT,
            largest_pad TEXT,
            station_faction_name TEXT,
            station_faction_state TEXT,
            station_economy TEXT,
            station_economies_json TEXT,
            last_station_visit_datetime TEXT,
            FOREIGN KEY(system_address) REFERENCES systems(system_address)
        );

        CREATE TABLE IF NOT EXISTS market_prices (
            market_id INTEGER NOT NULL,
            commodity TEXT NOT NULL,
            buy_price INTEGER,
            sell_price INTEGER,
            supply INTEGER,
            demand INTEGER,
            market_price_update_datetime TEXT NOT NULL,
            PRIMARY KEY (market_id, commodity),
            FOREIGN KEY(market_id) REFERENCES stations(market_id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value_json TEXT
        );

        CREATE TABLE IF NOT EXISTS systems_data (
            system_address INTEGER PRIMARY KEY,
            system_name TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            z REAL NOT NULL,
            source TEXT,
            recorded_datetime TEXT
        );

        CREATE TABLE IF NOT EXISTS commodity_global_stats (
            commodity TEXT PRIMARY KEY,
            category TEXT,
            inara_id INTEGER,
            avg_sell INTEGER,
            avg_buy INTEGER,
            avg_profit INTEGER,
            max_sell INTEGER,
            min_buy INTEGER,
            max_profit INTEGER,
            updated_datetime TEXT
        );

        CREATE TABLE IF NOT EXISTS jackpot_events (
            jackpot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id INTEGER NOT NULL,
            detected_datetime TEXT NOT NULL,
            ended_datetime TEXT,
            last_sample_datetime TEXT,
            active INTEGER DEFAULT 1,
            trigger_commodities TEXT,
            price_threshold INTEGER,
            supply_threshold INTEGER,
            system_name TEXT,
            system_address INTEGER,
            system_economy TEXT,
            system_economies_json TEXT,
            system_faction_state TEXT,
            population INTEGER,
            security TEXT,
            station_name TEXT,
            station_type TEXT,
            largest_pad TEXT,
            station_economy TEXT,
            station_economies_json TEXT,
            station_faction_name TEXT,
            station_faction_state TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS jackpot_samples (
            sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jackpot_id INTEGER NOT NULL,
            market_id INTEGER NOT NULL,
            sample_datetime TEXT NOT NULL,
            is_jackpot INTEGER NOT NULL,
            trigger_commodities TEXT,
            palladium_buy INTEGER,
            palladium_supply INTEGER,
            gold_buy INTEGER,
            gold_supply INTEGER,
            silver_buy INTEGER,
            silver_supply INTEGER,
            FOREIGN KEY(jackpot_id) REFERENCES jackpot_events(jackpot_id)
        );

        CREATE TABLE IF NOT EXISTS imports (
            data_name TEXT PRIMARY KEY,
            last_sha256 TEXT NOT NULL,
            imported_datetime TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS engineers_unlock (
            engineer TEXT PRIMARY KEY,
            engineer_system TEXT,
            is_public_knowledge INTEGER,
            discovered_via TEXT,
            required_commodity TEXT,
            required_commodity_quantity INTEGER,
            other_requirements TEXT,
            is_rare_commodity INTEGER DEFAULT 0,
            updated_datetime TEXT
        );

        CREATE TABLE IF NOT EXISTS trade_events (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_datetime TEXT NOT NULL,
            event_type TEXT NOT NULL,
            system_address INTEGER,
            system_name TEXT,
            market_id INTEGER,
            station_name TEXT,
            commodity TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price INTEGER,
            total_credits INTEGER,
            avg_buy_price REAL,
            known_cost INTEGER,
            profit INTEGER,
            profit_per_hour REAL,
            covered_quantity INTEGER,
            journal_avg_price_paid REAL,
            journal_profit INTEGER,
            journal_profit_per_unit REAL,
            ledger_avg_buy_price REAL,
            ledger_profit INTEGER,
            ledger_profit_per_hour REAL,
            cost_basis_method TEXT,
            supply_at_trade INTEGER,
            demand_at_trade INTEGER,
            lots_json TEXT,
            journal_json TEXT
        );

        CREATE TABLE IF NOT EXISTS trade_lots (
            lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity TEXT NOT NULL,
            buy_datetime TEXT NOT NULL,
            system_address INTEGER,
            system_name TEXT,
            market_id INTEGER,
            station_name TEXT,
            original_quantity INTEGER NOT NULL,
            remaining_quantity INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            total_cost INTEGER NOT NULL,
            source_trade_id INTEGER,
            closed_datetime TEXT,
            FOREIGN KEY(source_trade_id) REFERENCES trade_events(trade_id)
        );

        CREATE INDEX IF NOT EXISTS idx_stations_state ON stations(station_faction_state);
        CREATE INDEX IF NOT EXISTS idx_stations_economy ON stations(station_economy);
        CREATE INDEX IF NOT EXISTS idx_prices_commodity_buy ON market_prices(commodity, buy_price);
        CREATE INDEX IF NOT EXISTS idx_systems_name ON systems(system_name);
        CREATE INDEX IF NOT EXISTS idx_systems_data_name ON systems_data(system_name);
        CREATE INDEX IF NOT EXISTS idx_jackpot_events_market_active ON jackpot_events(market_id, active);
        CREATE INDEX IF NOT EXISTS idx_jackpot_samples_jackpot_time ON jackpot_samples(jackpot_id, sample_datetime);
        CREATE INDEX IF NOT EXISTS idx_market_prices_commodity ON market_prices(commodity);
        CREATE INDEX IF NOT EXISTS idx_trade_events_time ON trade_events(event_datetime);
        CREATE INDEX IF NOT EXISTS idx_trade_events_commodity_time ON trade_events(commodity, event_datetime);
        CREATE INDEX IF NOT EXISTS idx_trade_lots_open ON trade_lots(commodity, remaining_quantity, buy_datetime);
        """
    )

    add_column_if_missing(conn, "systems", "system_faction_state", "TEXT")
    add_column_if_missing(conn, "systems", "source", "TEXT")
    add_column_if_missing(conn, "systems", "source_pulled_datetime", "TEXT")
    add_column_if_missing(conn, "systems", "source_data_updated_datetime", "TEXT")

    add_column_if_missing(conn, "stations", "source", "TEXT")
    add_column_if_missing(conn, "stations", "source_pulled_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "distance_to_arrival_ls", "REAL")
    add_column_if_missing(conn, "stations", "body_name", "TEXT")
    add_column_if_missing(conn, "stations", "has_market", "INTEGER")
    add_column_if_missing(conn, "stations", "export_commodities_json", "TEXT")
    add_column_if_missing(conn, "stations", "is_fleet_carrier", "INTEGER DEFAULT 0")
    add_column_if_missing(conn, "stations", "source_data_updated_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "market_source_updated_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "carrier_docking_access", "TEXT")
    add_column_if_missing(conn, "stations", "carrier_name", "TEXT")
    add_column_if_missing(conn, "stations", "planetary", "INTEGER")
    add_column_if_missing(conn, "stations", "marketplace", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stations_source ON stations(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stations_fleet ON stations(is_fleet_carrier)")

    for column, definition in COMMODITY_GLOBAL_STATS_COLUMNS.items():
        add_column_if_missing(conn, "commodity_global_stats", column, definition)

    create_rare_commodities_table(conn)
    for column, definition in RARE_COMMODITY_COLUMNS.items():
        add_column_if_missing(conn, "rare_commodities", column, definition)
    remove_obsolete_rare_commodity_columns(conn)

    for column, definition in ENGINEERS_UNLOCK_COLUMNS.items():
        add_column_if_missing(conn, "engineers_unlock", column, definition)

    trade_event_columns = {
        "journal_avg_price_paid": "REAL",
        "journal_profit": "INTEGER",
        "journal_profit_per_unit": "REAL",
        "ledger_avg_buy_price": "REAL",
        "ledger_profit": "INTEGER",
        "ledger_profit_per_hour": "REAL",
        "cost_basis_method": "TEXT",
        "supply_at_trade": "INTEGER",
        "demand_at_trade": "INTEGER",
    }
    for column, definition in trade_event_columns.items():
        add_column_if_missing(conn, "trade_events", column, definition)

    conn.execute("UPDATE trade_events SET journal_avg_price_paid=avg_buy_price WHERE journal_avg_price_paid IS NULL AND avg_buy_price IS NOT NULL")
    conn.execute("UPDATE trade_events SET journal_profit=profit WHERE journal_profit IS NULL AND profit IS NOT NULL")
    conn.execute("UPDATE trade_events SET ledger_avg_buy_price=avg_buy_price WHERE ledger_avg_buy_price IS NULL AND avg_buy_price IS NOT NULL")
    conn.execute("UPDATE trade_events SET ledger_profit=profit WHERE ledger_profit IS NULL AND profit IS NOT NULL")
    conn.execute("UPDATE trade_events SET ledger_profit_per_hour=profit_per_hour WHERE ledger_profit_per_hour IS NULL AND profit_per_hour IS NOT NULL")
