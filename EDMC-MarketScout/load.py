"""
EDMC-MarketScout
Local-only EDMarketConnector plugin for recording station/BGS context and selected
commodity market prices for scouting trade opportunities.

Install: copy the MarketScout folder into EDMC's plugins directory and restart EDMC.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import traceback
import importlib.util
import webbrowser
from pathlib import Path as _Path
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from config import config as EDMC_CONFIG
except Exception:
    EDMC_CONFIG = None

PLUGIN_NAME = "EDMC-MarketScout"
PLUGIN_VERSION = "0.1.22"

DEFAULT_HIGHLIGHT_PRICE = 6000
DEFAULT_HIGHLIGHT_SUPPLY = 10000
JACKPOT_SAMPLE_INTERVAL_MINUTES = 30
UI_SCHEMA_VERSION = 2

# Defaults only. From 0.1.14 onward MarketScout stores every commodity it sees.
# These lists control first-run watched columns/highlighting only.
DEFAULT_WATCHED_COMMODITIES = ["Palladium", "Gold", "Silver"]
PRIMARY_METALS = list(DEFAULT_WATCHED_COMMODITIES)
TARGET_COMMODITIES = [
    "Palladium", "Gold", "Silver", "Platinum", "Osmium", "Samarium", "Praseodymium",
]
COMMODITY_KEYWORDS = {c.lower().replace(" ", ""): c for c in TARGET_COMMODITIES}
DEFAULT_COMMODITY_GLOBAL_STATS = {
    "Palladium": {"max_sell": 71000, "min_buy": None},
    "Gold": {"max_sell": 67000, "min_buy": None},
    "Silver": {"max_sell": 49000, "min_buy": None},
}

DB_PATH: Optional[str] = None
CONN: Optional[sqlite3.Connection] = None
ROOT: Optional[tk.Misc] = None
WINDOW: Optional["MarketScoutWindow"] = None
PLUGIN_DIR: Optional[str] = None
WEB_MODULE: Any = None
LEDGER_MODULE: Any = None
COMMODITIES_IMPORTER_MODULE: Any = None
LAST_CURRENT_POS: Optional[Tuple[float, float, float]] = None
LAST_CURRENT_SYSTEM: Optional[str] = None




def load_web_module():
    """Load the local web helper module without relying on sys.path."""
    global WEB_MODULE
    if WEB_MODULE is not None:
        return WEB_MODULE
    path = os.path.join(os.path.dirname(__file__), "marketscout_web.py")
    spec = importlib.util.spec_from_file_location("marketscout_web_local", path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load marketscout_web.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    WEB_MODULE = module
    return module


def load_ledger_module():
    """Load the ledger helper module without relying on sys.path."""
    global LEDGER_MODULE
    if LEDGER_MODULE is not None:
        return LEDGER_MODULE
    path = os.path.join(os.path.dirname(__file__), "marketscout_ledger.py")
    spec = importlib.util.spec_from_file_location("marketscout_ledger_local", path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load marketscout_ledger.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    LEDGER_MODULE = module
    return module


def load_commodities_importer_module():
    """Load the commodity CSV importer without relying on sys.path."""
    global COMMODITIES_IMPORTER_MODULE
    if COMMODITIES_IMPORTER_MODULE is not None:
        return COMMODITIES_IMPORTER_MODULE
    path = os.path.join(os.path.dirname(__file__), "commodities_importer.py")
    spec = importlib.util.spec_from_file_location("commodities_importer_local", path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load commodities_importer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    COMMODITIES_IMPORTER_MODULE = module
    return module

def load_importer_module():
    """Load the helper module from this plugin folder without relying on sys.path."""
    path = os.path.join(os.path.dirname(__file__), "marketscout_importer.py")
    spec = importlib.util.spec_from_file_location("marketscout_importer_local", path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load marketscout_importer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plugin_config_path(filename: str) -> str:
    base = os.path.dirname(DB_PATH or __file__)
    return os.path.join(base, filename)


def load_json_config(filename: str, default: Any) -> Any:
    try:
        path = plugin_config_path(filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_config(filename: str, value: Any) -> None:
    try:
        path = plugin_config_path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, sort_keys=True)
    except Exception:
        log_exception("save_json_config")


def load_ui_config() -> Dict[str, Any]:
    data = load_json_config("marketscout-ui.json", {})
    return data if isinstance(data, dict) else {}


def update_ui_config(**kwargs: Any) -> None:
    data = load_ui_config()
    data.update(kwargs)
    save_json_config("marketscout-ui.json", data)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def event_time(entry: Dict[str, Any]) -> str:
    return str(entry.get("timestamp") or now_utc_iso())


def plugin_start3(plugin_dir: str) -> str:
    """EDMC plugin entry point."""
    global DB_PATH, CONN, PLUGIN_DIR
    PLUGIN_DIR = plugin_dir
    DB_PATH = os.path.join(plugin_dir, "marketscout.sqlite3")
    CONN = sqlite3.connect(DB_PATH)
    CONN.row_factory = sqlite3.Row
    init_db(CONN)
    refresh_rawdata_imports(CONN, plugin_dir)
    deduplicate_market_price_commodities(CONN)
    deduplicate_station_rows(CONN)
    return PLUGIN_NAME


def plugin_stop() -> None:
    global CONN
    try:
        load_web_module().stop_server()
    except Exception:
        pass
    if CONN is not None:
        CONN.commit()
        CONN.close()
        CONN = None


def plugin_app(parent: tk.Frame) -> tk.Widget:
    """Add compact buttons to EDMC's main window."""
    global ROOT
    ROOT = parent
    frame = ttk.Frame(parent)
    ttk.Button(frame, text="Scout", command=open_window).pack(side=tk.LEFT, padx=(0, 2))
    ttk.Button(frame, text="Web", command=open_modern_ui).pack(side=tk.LEFT)
    return frame


def journal_entry(cmdr: str, is_beta: bool, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]) -> Optional[str]:
    """Receive Journal events from EDMC."""
    try:
        if CONN is None:
            return None

        name = entry.get("event")
        update_web_latest_journal_event(name, system, station, entry, state)

        if name in ("Location", "FSDJump", "CarrierJump", "StartUp"):
            record_system_from_event(entry, state)

        if name in ("Location", "Docked", "StartUp"):
            # Location may include Docked:true. Docked has station details.
            if entry.get("Docked") or entry.get("StationName") or state.get("StationName"):
                record_station_from_event(entry, state)

        if name == "Market":
            # Journal Market event is accompanied by Market.json. This gives us
            # a local-only fallback even if EDMC CAPI marketdata is absent.
            record_market_json_from_event(entry, state)

        if name in ("MarketBuy", "MarketSell"):
            load_ledger_module().record_trade_event(CONN, system, station, entry, state)

        CONN.commit()
        if WINDOW is not None:
            WINDOW.status_var.set(f"Last event: {name} at {now_utc_iso()}")
    except Exception:
        log_exception("journal_entry")
    return None


def update_web_latest_journal_event(name: Any, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]) -> None:
    """Expose the latest Journal event metadata to the local Web UI.

    The web module stores this in memory only. It is shown in the status strip
    and does not trigger database writes or table refreshes by itself.
    """
    try:
        event_name = str(name or entry.get("event") or "")
        event_time = str(entry.get("timestamp") or now_utc_iso())
        event_system = first_text(system, entry.get("StarSystem"), state.get("SystemName"), state.get("StarSystem"), LAST_CURRENT_SYSTEM)
        event_station = first_text(station, entry.get("StationName"), state.get("StationName"))
        load_web_module().update_latest_journal_event({
            "event": event_name,
            "timestamp": event_time,
            "system": event_system,
            "station": event_station,
        })
    except Exception:
        # Status reporting should never interfere with Journal processing.
        pass


def cmdr_data(data: Any, is_beta: bool) -> Optional[str]:
    """Receive fresh Frontier CAPI commander/station/market data from EDMC."""
    try:
        if CONN is None:
            return None
        log_market_debug("cmdr_data called", summarize_capi_data(data))
        marketdata = extract_marketdata(data)
        if marketdata:
            inserted = record_marketdata(marketdata, data)
            CONN.commit()
            log_market_debug("cmdr_data marketdata processed", {"tracked_rows_written": inserted})
            if WINDOW is not None:
                WINDOW.status_var.set(f"Market data stored: {inserted} tracked rows at {now_utc_iso()}")
                WINDOW.refresh()
        else:
            log_market_debug("cmdr_data no marketdata found", summarize_capi_data(data))
            if WINDOW is not None:
                WINDOW.status_var.set("No marketdata found in EDMC CAPI payload; see marketscout-market-debug.log")
    except Exception:
        log_exception("cmdr_data")
    return None


def cmdr_data_legacy(data: Any, is_beta: bool) -> Optional[str]:
    return cmdr_data(data, is_beta)


def init_db(conn: sqlite3.Connection) -> None:
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

        CREATE INDEX IF NOT EXISTS idx_stations_state ON stations(station_faction_state);
        CREATE INDEX IF NOT EXISTS idx_stations_economy ON stations(station_economy);
        CREATE INDEX IF NOT EXISTS idx_prices_commodity_buy ON market_prices(commodity, buy_price);
        CREATE INDEX IF NOT EXISTS idx_systems_name ON systems(system_name);
        """
    )
    try:
        load_ledger_module().init_db(conn)
    except Exception:
        log_exception("ledger init_db")
    migrate_db(conn)
    conn.commit()


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_db(conn: sqlite3.Connection) -> None:
    # 0.1.8 jackpot history/system state metadata.
    add_column_if_missing(conn, "systems", "system_faction_state", "TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS systems_data (
            system_address INTEGER PRIMARY KEY,
            system_name TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            z REAL NOT NULL,
            source TEXT,
            recorded_datetime TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_systems_data_name ON systems_data(system_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jackpot_events_market_active ON jackpot_events(market_id, active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jackpot_samples_jackpot_time ON jackpot_samples(jackpot_id, sample_datetime)")
    # 0.1.3 candidate import/source/fleet-carrier metadata.
    add_column_if_missing(conn, "systems", "source", "TEXT")
    add_column_if_missing(conn, "systems", "source_pulled_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "source", "TEXT")
    add_column_if_missing(conn, "stations", "source_pulled_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "distance_to_arrival_ls", "REAL")
    add_column_if_missing(conn, "stations", "body_name", "TEXT")
    add_column_if_missing(conn, "stations", "has_market", "INTEGER")
    add_column_if_missing(conn, "stations", "export_commodities_json", "TEXT")
    add_column_if_missing(conn, "stations", "is_fleet_carrier", "INTEGER DEFAULT 0")
    # 0.1.4 richer Spansh CSV candidate metadata.
    add_column_if_missing(conn, "systems", "source_data_updated_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "source_data_updated_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "market_source_updated_datetime", "TEXT")
    add_column_if_missing(conn, "stations", "carrier_docking_access", "TEXT")
    add_column_if_missing(conn, "stations", "carrier_name", "TEXT")
    add_column_if_missing(conn, "stations", "planetary", "INTEGER")
    add_column_if_missing(conn, "stations", "marketplace", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stations_source ON stations(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stations_fleet ON stations(is_fleet_carrier)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_market_prices_commodity ON market_prices(commodity)")
    try:
        load_commodities_importer_module().migrate_db(conn)
    except Exception:
        log_exception("commodities importer migrate_db")
    ensure_default_settings(conn)
    ensure_default_commodity_global_stats(conn)


def record_system_from_event(entry: Dict[str, Any], state: Dict[str, Any]) -> None:
    global LAST_CURRENT_POS, LAST_CURRENT_SYSTEM
    if CONN is None:
        return

    system_name = first_text(entry.get("StarSystem"), state.get("SystemName"))
    system_address = first_int(entry.get("SystemAddress"), state.get("SystemAddress"))
    if not system_name or system_address is None:
        return

    # If this system was previously imported with a negative placeholder ID,
    # move its candidate stations onto the real Elite system address.
    for old_row in CONN.execute(
        "SELECT system_address FROM systems WHERE lower(system_name)=lower(?) AND system_address < 0",
        (system_name,),
    ).fetchall():
        old_addr = old_row[0]
        CONN.execute("UPDATE stations SET system_address=? WHERE system_address=?", (system_address, old_addr))
        CONN.execute("DELETE FROM systems WHERE system_address=?", (old_addr,))

    pos = entry.get("StarPos") or state.get("StarPos")
    x = y = z = None
    if isinstance(pos, (list, tuple)) and len(pos) >= 3:
        x, y, z = safe_float(pos[0]), safe_float(pos[1]), safe_float(pos[2])
        if x is not None and y is not None and z is not None:
            LAST_CURRENT_POS = (x, y, z)
            LAST_CURRENT_SYSTEM = system_name

    population = first_int(entry.get("Population"), state.get("SystemPopulation"))
    security = localized_or_raw(entry, "SystemSecurity") or entry.get("Security")
    system_faction_state = system_faction_state_from_event(entry)
    sys_economy = localized_or_raw(entry, "SystemEconomy") or localized_or_raw(entry, "Economy")
    sys_economies = economies_from_entry(entry, prefix="System") or economies_from_entry(entry, prefix="")

    CONN.execute(
        """
        INSERT INTO systems(system_address, system_name, x, y, z, population, security, system_faction_state,
                            system_economy, system_economies_json, last_visit_datetime, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(system_address) DO UPDATE SET
            system_name=excluded.system_name,
            x=COALESCE(excluded.x, systems.x),
            y=COALESCE(excluded.y, systems.y),
            z=COALESCE(excluded.z, systems.z),
            population=COALESCE(excluded.population, systems.population),
            security=COALESCE(excluded.security, systems.security),
            system_faction_state=COALESCE(excluded.system_faction_state, systems.system_faction_state),
            system_economy=COALESCE(excluded.system_economy, systems.system_economy),
            system_economies_json=COALESCE(excluded.system_economies_json, systems.system_economies_json),
            last_visit_datetime=excluded.last_visit_datetime,
            source=CASE WHEN systems.source IS NULL OR systems.source != 'local_visit' THEN 'local_visit' ELSE systems.source END
        """,
        (
            system_address,
            system_name,
            x,
            y,
            z,
            population,
            clean_text(security),
            clean_text(system_faction_state),
            clean_text(sys_economy),
            json.dumps(sys_economies) if sys_economies else None,
            event_time(entry),
            "local_visit",
        ),
    )
    if x is not None and y is not None and z is not None:
        upsert_systems_data(CONN, system_name, system_address, x, y, z, "journal", event_time(entry))


def upsert_systems_data(
    conn: sqlite3.Connection,
    system_name: str,
    system_address: Optional[int],
    x: float,
    y: float,
    z: float,
    source: str,
    recorded_datetime: str,
) -> None:
    if system_address is None:
        return
    conn.execute(
        """
        INSERT INTO systems_data(system_address, system_name, x, y, z, source, recorded_datetime)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(system_address) DO UPDATE SET
            system_name=excluded.system_name,
            x=excluded.x,
            y=excluded.y,
            z=excluded.z,
            source=excluded.source,
            recorded_datetime=excluded.recorded_datetime
        """,
        (system_address, system_name, x, y, z, source, recorded_datetime),
    )


def record_station_from_event(entry: Dict[str, Any], state: Dict[str, Any]) -> None:
    if CONN is None:
        return

    market_id = first_int(entry.get("MarketID"), state.get("MarketID"))
    station_name = first_text(entry.get("StationName"), state.get("StationName"))
    system_address = first_int(entry.get("SystemAddress"), state.get("SystemAddress"))
    if market_id is None or not station_name:
        return

    station_type = first_text(entry.get("StationType"), state.get("StationType"))
    station_economy = localized_or_raw(entry, "StationEconomy")
    station_economies = economies_from_entry(entry, prefix="Station")
    faction_name, faction_state = station_faction_from_event(entry)
    largest_pad = infer_largest_pad(station_type)
    is_fc = 1 if is_fleet_carrier(station_type, station_name) else 0

    # Merge a previously imported placeholder station into the real MarketID.
    imported = CONN.execute(
        """
        SELECT market_id FROM stations
        WHERE market_id < 0 AND lower(station_name)=lower(?)
          AND (? IS NULL OR system_address=? OR system_address IN (
              SELECT system_address FROM systems WHERE lower(system_name)=lower(?)
          ))
        LIMIT 1
        """,
        (station_name, system_address, system_address, first_text(entry.get("StarSystem"), state.get("SystemName"), "")),
    ).fetchone()
    if imported is not None and imported[0] != market_id:
        old_market_id = imported[0]
        CONN.execute("UPDATE market_prices SET market_id=? WHERE market_id=?", (market_id, old_market_id))
        CONN.execute("UPDATE stations SET market_id=? WHERE market_id=?", (market_id, old_market_id))

    CONN.execute(
        """
        INSERT INTO stations(market_id, system_address, station_name, station_type, largest_pad,
                             station_faction_name, station_faction_state, station_economy,
                             station_economies_json, last_station_visit_datetime, source, is_fleet_carrier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(market_id) DO UPDATE SET
            system_address=COALESCE(excluded.system_address, stations.system_address),
            station_name=excluded.station_name,
            station_type=COALESCE(excluded.station_type, stations.station_type),
            largest_pad=COALESCE(excluded.largest_pad, stations.largest_pad),
            station_faction_name=COALESCE(excluded.station_faction_name, stations.station_faction_name),
            station_faction_state=COALESCE(excluded.station_faction_state, stations.station_faction_state),
            station_economy=COALESCE(excluded.station_economy, stations.station_economy),
            station_economies_json=COALESCE(excluded.station_economies_json, stations.station_economies_json),
            last_station_visit_datetime=excluded.last_station_visit_datetime,
            source='local_visit',
            is_fleet_carrier=COALESCE(excluded.is_fleet_carrier, stations.is_fleet_carrier)
        """,
        (
            market_id,
            system_address,
            station_name,
            clean_text(station_type),
            largest_pad,
            clean_text(faction_name),
            clean_text(faction_state),
            clean_text(station_economy),
            json.dumps(station_economies) if station_economies else None,
            event_time(entry),
            "local_visit",
            is_fc,
        ),
    )



def setting_get(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    try:
        row = conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        if row and row[0] is not None:
            return json.loads(row[0])
    except Exception:
        pass
    return default

def setting_set(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT INTO settings(key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
        (key, json.dumps(value, ensure_ascii=False)),
    )

def ensure_default_settings(conn: sqlite3.Connection) -> None:
    if setting_get(conn, "watched_commodities") is None:
        setting_set(conn, "watched_commodities", list(DEFAULT_WATCHED_COMMODITIES))
    if setting_get(conn, "watched_columns") is None:
        cols = []
        for c in DEFAULT_WATCHED_COMMODITIES:
            cols.append({"commodity": c, "side": "buy"})
        setting_set(conn, "watched_columns", cols)
    if setting_get(conn, "best_buy_ignore_commodities") is None:
        setting_set(conn, "best_buy_ignore_commodities", [])

def ensure_default_commodity_global_stats(conn: sqlite3.Connection) -> None:
    load_commodities_importer_module().ensure_default_commodity_global_stats(conn, DEFAULT_COMMODITY_GLOBAL_STATS)

def refresh_commodity_global_stats_from_csv(conn: sqlite3.Connection, plugin_dir: str) -> None:
    """Refresh commodity_global_stats from optional commodities.csv.

    This is intentionally manual/local and performs no scraping or network
    activity. The importer module owns the CSV schema and SQLite upsert.
    """
    try:
        load_commodities_importer_module().refresh_commodity_global_stats_from_csv(
            conn,
            plugin_dir,
            DEFAULT_COMMODITY_GLOBAL_STATS,
            normalize_commodity_name,
        )
    except Exception:
        log_exception("refresh_commodity_global_stats_from_csv")

def refresh_rare_commodities_from_csv(conn: sqlite3.Connection, plugin_dir: str) -> None:
    """Refresh rare_commodities from optional rawdata/commodities_rare.csv."""
    try:
        load_commodities_importer_module().refresh_rare_commodities_from_csv(conn, plugin_dir)
    except Exception:
        log_exception("refresh_rare_commodities_from_csv")

def refresh_systems_from_csv(conn: sqlite3.Connection, plugin_dir: str) -> None:
    """Refresh systems_data from optional rawdata/systems_data.csv."""
    try:
        load_commodities_importer_module().refresh_systems_from_csv(conn, plugin_dir)
    except Exception:
        log_exception("refresh_systems_from_csv")

def refresh_engineers_unlock_from_csv(conn: sqlite3.Connection, plugin_dir: str) -> None:
    """Refresh engineers_unlock from optional rawdata/engineers-unlock.csv."""
    try:
        load_commodities_importer_module().refresh_engineers_unlock_from_csv(conn, plugin_dir)
    except Exception:
        log_exception("refresh_engineers_unlock_from_csv")

def refresh_rawdata_imports(conn: sqlite3.Connection, plugin_dir: str) -> None:
    refresh_systems_from_csv(conn, plugin_dir)
    refresh_commodity_global_stats_from_csv(conn, plugin_dir)
    refresh_rare_commodities_from_csv(conn, plugin_dir)
    refresh_engineers_unlock_from_csv(conn, plugin_dir)

def get_watched_commodities(conn: sqlite3.Connection) -> List[str]:
    value = setting_get(conn, "watched_commodities", list(DEFAULT_WATCHED_COMMODITIES))
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()] or list(DEFAULT_WATCHED_COMMODITIES)
    return list(DEFAULT_WATCHED_COMMODITIES)

def record_marketdata(marketdata: Dict[str, Any], data: Any) -> int:
    if CONN is None:
        return 0

    market_id = first_int(
        marketdata.get("id"), marketdata.get("marketid"), marketdata.get("MarketID"), marketdata.get("marketId")
    )
    if market_id is None:
        # Try lastStarport id as fallback.
        starport = as_dict(get_item(data, "lastStarport")) or {}
        market_id = first_int(starport.get("id"), starport.get("marketid"), starport.get("MarketID"))
    if market_id is None:
        log_market_debug("record_marketdata: no market_id", summarize_mapping(marketdata))
        return 0

    update_time = now_utc_iso()
    station_name = first_text(marketdata.get("name"), get_item(get_item(data, "lastStarport"), "name"))
    if station_name:
        CONN.execute(
            """
            INSERT INTO stations(market_id, station_name, last_station_visit_datetime)
            VALUES (?, ?, ?)
            ON CONFLICT(market_id) DO UPDATE SET station_name=COALESCE(stations.station_name, excluded.station_name)
            """,
            (market_id, station_name, update_time),
        )

    commodities = (
        marketdata.get("commodities")
        or marketdata.get("items")
        or marketdata.get("market")
        or marketdata.get("Items")
        or []
    )
    if isinstance(commodities, dict):
        # CAPI commonly uses a dict keyed by commodity symbol. Preserve the key as
        # a fallback commodity name if the item itself lacks one.
        commodities = [dict(as_dict(v) or {}, symbol=k) if as_dict(v) else v for k, v in commodities.items()]

    if not commodities:
        log_market_debug("record_marketdata: no commodities list", summarize_mapping(marketdata))
        return 0

    inserted = 0
    seen_commodities: List[str] = []
    for item in commodities:
        item_dict = as_dict(item)
        if not item_dict:
            continue
        item = item_dict
        commodity = normalize_commodity_name(
            item.get("name") or item.get("commodity") or item.get("symbol") or item.get("Name")
            or item.get("locName") or item.get("commodityName") or item.get("id")
        )
        if not commodity:
            continue
        seen_commodities.append(commodity)
        if commodity in ("Palladium", "Gold", "Silver"):
            log_market_debug("tracked commodity raw fields", {
                "commodity": commodity,
                "name": item.get("name") or item.get("Name") or item.get("symbol"),
                "buyPrice": item.get("buyPrice") or item.get("BuyPrice"),
                "sellPrice": item.get("sellPrice") or item.get("SellPrice"),
                "stock": item.get("stock"),
                "supply": item.get("supply"),
                "Stock": item.get("Stock"),
                "Supply": item.get("Supply"),
                "stockBracket": item.get("stockBracket"),
                "demand": item.get("demand"),
                "Demand": item.get("Demand"),
                "demandBracket": item.get("demandBracket"),
            })
        CONN.execute(
            """
            INSERT INTO market_prices(market_id, commodity, buy_price, sell_price, supply, demand, market_price_update_datetime)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(market_id, commodity) DO UPDATE SET
                buy_price=excluded.buy_price,
                sell_price=excluded.sell_price,
                supply=COALESCE(excluded.supply, market_prices.supply),
                demand=COALESCE(excluded.demand, market_prices.demand),
                market_price_update_datetime=excluded.market_price_update_datetime
            """,
            (
                market_id,
                commodity,
                first_int(item.get("buyPrice"), item.get("buy_price"), item.get("buy"), item.get("BuyPrice"), item.get("buyprice"), item.get("meanPrice")),
                first_int(item.get("sellPrice"), item.get("sell_price"), item.get("sell"), item.get("SellPrice"), item.get("sellprice")),
                # IMPORTANT: stockBracket/demandBracket are bracket/category values, not actual tonnage.
                # Do not use them as supply/demand, or a partial CAPI payload can flatten real
                # quantities (observed especially with Gold) to 0. If a payload lacks real
                # Stock/Supply/Demand fields, preserve the previous known quantity.
                first_int(item.get("stock"), item.get("supply"), item.get("Stock"), item.get("Supply")),
                first_int(item.get("demand"), item.get("Demand")),
                update_time,
            ),
        )
        inserted += 1

    cleared = clear_missing_market_supply(market_id, seen_commodities, update_time)
    if inserted:
        maybe_record_jackpot_history(market_id, update_time)
    log_market_debug("record_marketdata complete", {"market_id": market_id, "commodities_seen": len(commodities), "tracked_rows_written": inserted, "stale_buy_rows_cleared": cleared})
    return inserted


def clear_missing_market_supply(market_id: int, seen_commodities: List[str], update_time: str) -> int:
    """Mark buy-side rows missing from a fresh market snapshot as unavailable."""
    if CONN is None or not seen_commodities:
        return 0

    seen = sorted(set(seen_commodities))
    placeholders = ",".join("?" for _ in seen)
    params: List[Any] = [update_time, market_id] + seen
    cur = CONN.execute(
        f"""
        UPDATE market_prices
        SET buy_price=0,
            supply=0,
            market_price_update_datetime=?
        WHERE market_id=?
          AND commodity NOT IN ({placeholders})
          AND (COALESCE(buy_price, 0) != 0 OR COALESCE(supply, 0) != 0)
        """,
        params,
    )
    return int(cur.rowcount or 0)


def extract_marketdata(data: Any) -> Optional[Dict[str, Any]]:
    # EDMC docs: /profile API response with /market added under marketdata and/or
    # lastStarport augmented. CAPIData is UserDict-like, so also check .data.
    candidates = [data]
    inner = getattr(data, "data", None)
    if inner is not None and inner is not data:
        candidates.append(inner)

    for obj in candidates:
        direct = as_dict(get_item(obj, "marketdata"))
        if direct:
            return direct

    # Some EDMC/CAPI shapes expose commodities at top-level rather than inside
    # marketdata/lastStarport. Build a marketdata-like dict when possible.
    for obj in candidates:
        for key in ("commodities", "items", "Items", "market"):
            val = get_item(obj, key)
            if val:
                starport = as_dict(get_item(obj, "lastStarport")) or {}
                return {
                    "id": get_item(obj, "marketid") or get_item(obj, "MarketID") or get_item(obj, "marketId") or starport.get("id") or starport.get("marketid") or starport.get("MarketID"),
                    "name": get_item(obj, "name") or starport.get("name"),
                    "commodities": val,
                }

    for obj in candidates:
        starport = as_dict(get_item(obj, "lastStarport"))
        if not starport:
            continue
        for key in ("marketdata", "market", "commodities", "Items"):
            val = starport.get(key)
            if val:
                if key in ("commodities", "Items"):
                    return {
                        "id": starport.get("id") or starport.get("marketid") or starport.get("MarketID"),
                        "name": starport.get("name"),
                        "commodities": val,
                    }
                market = as_dict(val)
                if market:
                    if not any(k in market for k in ("id", "marketid", "MarketID", "marketId")):
                        market = dict(market)
                        market["id"] = starport.get("id") or starport.get("marketid") or starport.get("MarketID")
                    return market
    return None



def record_market_json_from_event(entry: Dict[str, Any], state: Dict[str, Any]) -> int:
    """Read the local Market.json created by the game when the market opens."""
    path = find_market_json_path(entry)
    if not path:
        log_market_debug("Market event but Market.json not found", {"entry_keys": sorted(entry.keys()), "journal_dir": get_journal_dir()})
        return 0
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f)
    except Exception:
        log_exception("record_market_json_from_event read")
        log_market_debug("Market.json read failed", {"path": path})
        return 0

    marketdata = as_dict(raw) or {}
    if "Items" in marketdata and "commodities" not in marketdata:
        marketdata = dict(marketdata)
        marketdata["commodities"] = marketdata.get("Items")
    if "MarketID" not in marketdata and entry.get("MarketID") is not None:
        marketdata["MarketID"] = entry.get("MarketID")
    if "name" not in marketdata:
        marketdata["name"] = entry.get("StationName") or state.get("StationName")
    inserted = record_marketdata(marketdata, marketdata)
    log_market_debug("Market.json processed", {"path": path, "tracked_rows_written": inserted})
    return inserted


def get_journal_dir() -> Optional[str]:
    try:
        if EDMC_CONFIG is not None:
            get_str = getattr(EDMC_CONFIG, "get_str", None)
            journaldir = get_str("journaldir") if callable(get_str) else None
            if journaldir:
                return str(journaldir)
            default_dir = getattr(EDMC_CONFIG, "default_journal_dir", None)
            if default_dir:
                return str(default_dir)
    except Exception:
        pass
    return None


def find_market_json_path(entry: Dict[str, Any]) -> Optional[str]:
    filename = entry.get("Filename") or entry.get("filename") or "Market.json"
    candidates: List[str] = []
    if os.path.isabs(str(filename)):
        candidates.append(str(filename))
    journal_dir = get_journal_dir()
    if journal_dir:
        candidates.append(os.path.join(journal_dir, str(filename)))
        candidates.append(os.path.join(journal_dir, "Market.json"))
    # EDMC Flatpak data/log area fallback is not usually where Market.json lives,
    # but this helps if a user symlinks status files there.
    home = os.path.expanduser("~")
    candidates.extend([
        os.path.join(home, "Saved Games", "Frontier Developments", "Elite Dangerous", str(filename)),
        os.path.join(home, "Saved Games", "Frontier Developments", "Elite Dangerous", "Market.json"),
    ])
    seen = set()
    existing = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            if os.path.exists(c):
                existing.append(c)
    if not existing:
        return None
    existing.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return existing[0]


def log_market_debug(where: str, payload: Any = None) -> None:
    try:
        path = plugin_config_path("marketscout-market-debug.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"----- {now_utc_iso()} {where} -----\n")
            if payload is not None:
                f.write(safe_json_dumps(payload))
                f.write("\n")
    except Exception:
        pass


def safe_json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, sort_keys=True, default=str)[:12000]
    except Exception:
        return str(value)[:12000]


def summarize_capi_data(data: Any) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"type": type(data).__name__}
    d = as_dict(data)
    if d:
        summary["top_keys"] = sorted(map(str, d.keys()))[:80]
        for key in ("marketdata", "lastStarport", "commodities", "items", "Items", "market"):
            val = d.get(key)
            if val is not None:
                summary[key] = summarize_value(val)
    else:
        keys = []
        for key in ("marketdata", "lastStarport", "commodities", "items", "Items", "market"):
            val = get_item(data, key)
            if val is not None:
                keys.append(key)
                summary[key] = summarize_value(val)
        summary["detected_keys"] = keys
    return summary


def summarize_mapping(value: Any) -> Dict[str, Any]:
    d = as_dict(value)
    if not d:
        return {"type": type(value).__name__}
    out: Dict[str, Any] = {"keys": sorted(map(str, d.keys()))[:80]}
    for key in ("id", "marketid", "MarketID", "marketId", "name", "commodities", "items", "Items", "market"):
        if key in d:
            out[key] = summarize_value(d[key])
    return out


def summarize_value(value: Any) -> Any:
    if isinstance(value, list):
        return {"type": "list", "len": len(value), "first": summarize_value(value[0]) if value else None}
    if isinstance(value, dict) or isinstance(value, Mapping):
        d = dict(value)
        return {"type": "dict", "keys": sorted(map(str, d.keys()))[:50]}
    inner = getattr(value, "data", None)
    if isinstance(inner, Mapping):
        return {"type": type(value).__name__, "data_keys": sorted(map(str, inner.keys()))[:50]}
    return {"type": type(value).__name__, "repr": str(value)[:500]}

def economies_from_entry(entry: Dict[str, Any], prefix: str) -> List[str]:
    keys = []
    if prefix:
        keys.append(prefix + "Economies")
    else:
        keys.append("Economies")
    out: List[str] = []
    for key in keys:
        value = entry.get(key)
        if isinstance(value, list):
            for econ in value:
                if isinstance(econ, dict):
                    name = econ.get("Name_Localised") or econ.get("Name")
                else:
                    name = econ
                name = clean_text(name)
                if name and name not in out:
                    out.append(name)
    # Fallback singular fields.
    for key in (prefix + "Economy", prefix + "SecondEconomy") if prefix else ("Economy", "SecondEconomy"):
        value = localized_or_raw(entry, key)
        value = clean_text(value)
        if value and value not in out:
            out.append(value)
    return out


def station_faction_from_event(entry: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    sf = entry.get("StationFaction")
    faction_name = None
    faction_state = None
    if isinstance(sf, dict):
        faction_name = sf.get("Name") or sf.get("name")
        faction_state = sf.get("FactionState") or sf.get("State") or sf.get("state")
    elif isinstance(sf, str):
        faction_name = sf
    faction_state = faction_state or entry.get("FactionState") or entry.get("StationFactionState")
    return faction_name, faction_state



def system_faction_state_from_event(entry: Dict[str, Any]) -> Optional[str]:
    sf = entry.get("SystemFaction")
    if isinstance(sf, dict):
        return sf.get("FactionState") or sf.get("State") or sf.get("state")
    # Some events may expose the controlling faction state directly.
    return entry.get("SystemFactionState") or entry.get("FactionState")


def jackpot_thresholds() -> Tuple[int, int]:
    """Use the same editable thresholds as row highlighting when available."""
    ui = load_ui_config()
    price = first_int(ui.get("highlight_price")) or DEFAULT_HIGHLIGHT_PRICE
    supply = first_int(ui.get("highlight_supply")) or DEFAULT_HIGHLIGHT_SUPPLY
    return price, supply


def maybe_record_jackpot_history(market_id: int, sample_time: str) -> None:
    """Event-driven jackpot history sampler.

    This is deliberately not a timer. Fresh market data calls this function. If a
    station qualifies as a jackpot, create a static jackpot event and then append
    a new sample only if JACKPOT_SAMPLE_INTERVAL_MINUTES has passed since the
    previous sample for that active jackpot. If an active jackpot no longer
    qualifies, append one final non-jackpot sample and close the event.
    """
    if CONN is None:
        return
    price_threshold, supply_threshold = jackpot_thresholds()
    prices = get_primary_metal_prices(market_id)
    is_jackpot, triggers = evaluate_jackpot(prices, price_threshold, supply_threshold)
    active = CONN.execute(
        "SELECT * FROM jackpot_events WHERE market_id=? AND active=1 ORDER BY jackpot_id DESC LIMIT 1",
        (market_id,),
    ).fetchone()

    if is_jackpot:
        if active is None:
            jackpot_id = create_jackpot_event(market_id, sample_time, triggers, price_threshold, supply_threshold)
            insert_jackpot_sample(jackpot_id, market_id, sample_time, 1, triggers, prices)
            CONN.execute("UPDATE jackpot_events SET last_sample_datetime=? WHERE jackpot_id=?", (sample_time, jackpot_id))
            log_market_debug("jackpot detected", {"market_id": market_id, "jackpot_id": jackpot_id, "triggers": triggers})
            return
        last_sample = active["last_sample_datetime"] or active["detected_datetime"]
        if should_sample_jackpot(last_sample, sample_time):
            jackpot_id = int(active["jackpot_id"])
            insert_jackpot_sample(jackpot_id, market_id, sample_time, 1, triggers, prices)
            CONN.execute(
                "UPDATE jackpot_events SET last_sample_datetime=?, trigger_commodities=? WHERE jackpot_id=?",
                (sample_time, json.dumps(triggers), jackpot_id),
            )
            log_market_debug("jackpot resampled", {"market_id": market_id, "jackpot_id": jackpot_id, "triggers": triggers})
        return

    # If a station used to be a jackpot and fresh data says it no longer is, add
    # a final sample so the history shows roughly when the deal disappeared.
    if active is not None:
        jackpot_id = int(active["jackpot_id"])
        insert_jackpot_sample(jackpot_id, market_id, sample_time, 0, [], prices)
        CONN.execute(
            "UPDATE jackpot_events SET active=0, ended_datetime=?, last_sample_datetime=? WHERE jackpot_id=?",
            (sample_time, sample_time, jackpot_id),
        )
        log_market_debug("jackpot ended", {"market_id": market_id, "jackpot_id": jackpot_id})


def get_primary_metal_prices(market_id: int) -> Dict[str, Dict[str, Optional[int]]]:
    out: Dict[str, Dict[str, Optional[int]]] = {}
    if CONN is None:
        return out
    rows = CONN.execute(
        """
        SELECT commodity, buy_price, supply
        FROM market_prices
        WHERE market_id=? AND commodity IN ('Palladium', 'Gold', 'Silver')
        """,
        (market_id,),
    ).fetchall()
    for row in rows:
        out[str(row["commodity"])] = {
            "buy": first_int(row["buy_price"]),
            "supply": first_int(row["supply"]),
        }
    return out


def evaluate_jackpot(prices: Dict[str, Dict[str, Optional[int]]], price_threshold: int, supply_threshold: int) -> Tuple[bool, List[str]]:
    triggers: List[str] = []
    for metal in PRIMARY_METALS:
        data = prices.get(metal) or {}
        buy = first_int(data.get("buy"))
        supply = first_int(data.get("supply"))
        if buy is not None and buy > 0 and buy <= price_threshold and supply is not None and supply >= supply_threshold:
            triggers.append(metal)
    return bool(triggers), triggers


def should_sample_jackpot(last_sample: Optional[str], sample_time: str) -> bool:
    if not last_sample:
        return True
    try:
        last = datetime.fromisoformat(str(last_sample).replace("Z", "+00:00"))
        now = datetime.fromisoformat(str(sample_time).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now - last >= timedelta(minutes=JACKPOT_SAMPLE_INTERVAL_MINUTES)
    except Exception:
        return True


def create_jackpot_event(market_id: int, detected_time: str, triggers: List[str], price_threshold: int, supply_threshold: int) -> int:
    if CONN is None:
        return -1
    row = CONN.execute(
        """
        SELECT st.*, s.system_name, s.system_address AS sys_addr, s.population, s.security,
               s.system_economy, s.system_economies_json, s.system_faction_state
        FROM stations st
        LEFT JOIN systems s ON s.system_address=st.system_address
        WHERE st.market_id=?
        """,
        (market_id,),
    ).fetchone()
    vals = {
        "system_name": row["system_name"] if row and "system_name" in row.keys() else None,
        "system_address": row["sys_addr"] if row and "sys_addr" in row.keys() else None,
        "system_economy": row["system_economy"] if row and "system_economy" in row.keys() else None,
        "system_economies_json": row["system_economies_json"] if row and "system_economies_json" in row.keys() else None,
        "system_faction_state": row["system_faction_state"] if row and "system_faction_state" in row.keys() else None,
        "population": row["population"] if row and "population" in row.keys() else None,
        "security": row["security"] if row and "security" in row.keys() else None,
        "station_name": row["station_name"] if row and "station_name" in row.keys() else None,
        "station_type": row["station_type"] if row and "station_type" in row.keys() else None,
        "largest_pad": row["largest_pad"] if row and "largest_pad" in row.keys() else None,
        "station_economy": row["station_economy"] if row and "station_economy" in row.keys() else None,
        "station_economies_json": row["station_economies_json"] if row and "station_economies_json" in row.keys() else None,
        "station_faction_name": row["station_faction_name"] if row and "station_faction_name" in row.keys() else None,
        "station_faction_state": row["station_faction_state"] if row and "station_faction_state" in row.keys() else None,
        "source": row["source"] if row and "source" in row.keys() else None,
    }
    cur = CONN.execute(
        """
        INSERT INTO jackpot_events(
            market_id, detected_datetime, last_sample_datetime, active, trigger_commodities,
            price_threshold, supply_threshold, system_name, system_address, system_economy,
            system_economies_json, system_faction_state, population, security, station_name,
            station_type, largest_pad, station_economy, station_economies_json,
            station_faction_name, station_faction_state, source
        ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            market_id, detected_time, detected_time, json.dumps(triggers), price_threshold, supply_threshold,
            vals["system_name"], vals["system_address"], vals["system_economy"], vals["system_economies_json"],
            vals["system_faction_state"], vals["population"], vals["security"], vals["station_name"],
            vals["station_type"], vals["largest_pad"], vals["station_economy"], vals["station_economies_json"],
            vals["station_faction_name"], vals["station_faction_state"], vals["source"],
        ),
    )
    return int(cur.lastrowid)


def insert_jackpot_sample(jackpot_id: int, market_id: int, sample_time: str, is_jackpot: int, triggers: List[str], prices: Dict[str, Dict[str, Optional[int]]]) -> None:
    if CONN is None:
        return
    def val(metal: str, key: str) -> Optional[int]:
        return first_int((prices.get(metal) or {}).get(key))
    CONN.execute(
        """
        INSERT INTO jackpot_samples(
            jackpot_id, market_id, sample_datetime, is_jackpot, trigger_commodities,
            palladium_buy, palladium_supply, gold_buy, gold_supply, silver_buy, silver_supply
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            jackpot_id, market_id, sample_time, is_jackpot, json.dumps(triggers),
            val("Palladium", "buy"), val("Palladium", "supply"),
            val("Gold", "buy"), val("Gold", "supply"),
            val("Silver", "buy"), val("Silver", "supply"),
        ),
    )

def localized_or_raw(entry: Dict[str, Any], key: str) -> Optional[str]:
    return first_text(entry.get(key + "_Localised"), entry.get(key))


def infer_largest_pad(station_type: Optional[str]) -> Optional[str]:
    if not station_type:
        return None
    t = station_type.lower()
    large_keywords = [
        "coriolis", "orbis", "ocellus", "starport", "bernal", "asteroidbase", "megaship",
        "fleetcarrier", "crateroutpost", "surfaceport", "planetaryport", "civilianoutpost",
    ]
    medium_only = ["outpost", "settlement", "onfoot"]
    if any(k in t for k in large_keywords):
        return "L"
    if any(k in t for k in medium_only):
        return "M"
    return None


def is_fleet_carrier(station_type: Optional[str], station_name: Optional[str] = None) -> bool:
    t = (station_type or "").lower().replace(" ", "")
    return "fleetcarrier" in t or "fleet carrier" in (station_type or "").lower()



def canonical_commodity_key(raw: Any) -> Optional[str]:
    """Return a stable, lower-case commodity key used for matching.

    This deliberately ignores spaces, punctuation and Frontier localisation
    wrappers, so ``Agronomic Treatment`` and ``$agronomictreatment_name;`` both
    become ``agronomictreatment``. The key is used only for matching/merging;
    the database still displays the nice commodity name.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.strip("$;")
    if s.lower().endswith("_name"):
        s = s[:-5]
    key = "".join(ch for ch in s.lower() if ch.isalnum())
    return key or None


def commodity_display_from_stats_key(key: Optional[str]) -> Optional[str]:
    """Return the commodity display name from commodity_global_stats for key.

    commodity_global_stats is the user's commodity catalogue from commodities.csv.
    Using it here prevents duplicate rows such as ``Agronomic Treatment`` and
    ``Agronomictreatment`` for the same station/market.
    """
    if not key or CONN is None:
        return None
    try:
        rows = CONN.execute("SELECT commodity FROM commodity_global_stats").fetchall()
        for row in rows:
            name = row[0]
            if canonical_commodity_key(name) == key:
                return str(name)
    except Exception:
        return None
    return None



def canonical_station_key(value: Optional[str]) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def merge_market_prices(conn: sqlite3.Connection, from_market_id: int, to_market_id: int) -> None:
    """Move price rows from one station to another, keeping the newest row per commodity."""
    rows = conn.execute(
        "SELECT commodity, buy_price, sell_price, supply, demand, market_price_update_datetime FROM market_prices WHERE market_id=?",
        (from_market_id,),
    ).fetchall()
    for row in rows:
        existing = conn.execute(
            "SELECT market_price_update_datetime FROM market_prices WHERE market_id=? AND commodity=?",
            (to_market_id, row["commodity"]),
        ).fetchone()
        if existing is None or (row["market_price_update_datetime"] or "") >= (existing["market_price_update_datetime"] or ""):
            conn.execute(
                """
                INSERT INTO market_prices(market_id, commodity, buy_price, sell_price, supply, demand, market_price_update_datetime)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(market_id, commodity) DO UPDATE SET
                    buy_price=excluded.buy_price,
                    sell_price=excluded.sell_price,
                    supply=excluded.supply,
                    demand=excluded.demand,
                    market_price_update_datetime=excluded.market_price_update_datetime
                """,
                (
                    to_market_id,
                    row["commodity"],
                    row["buy_price"],
                    row["sell_price"],
                    row["supply"],
                    row["demand"],
                    row["market_price_update_datetime"],
                ),
            )
    conn.execute("DELETE FROM market_prices WHERE market_id=?", (from_market_id,))


def deduplicate_station_rows(conn: sqlite3.Connection) -> int:
    """Merge duplicate current station rows that refer to the same physical station.

    Imported candidates can have synthetic negative MarketIDs, while later real visits
    use Frontier MarketIDs. If both rows survive, the main Stations view can show the
    same station twice with different Best Buy values. The current station table should
    contain one row per physical station; jackpot history tables keep historical samples.
    """
    try:
        rows = conn.execute(
            """
            SELECT st.*, s.system_name,
                   (SELECT MAX(market_price_update_datetime) FROM market_prices mp WHERE mp.market_id=st.market_id) AS market_updated
            FROM stations st
            LEFT JOIN systems s ON s.system_address=st.system_address
            WHERE COALESCE(st.is_fleet_carrier, 0)=0
            ORDER BY COALESCE(st.last_station_visit_datetime, '' ) DESC, COALESCE(market_updated, '') DESC
            """
        ).fetchall()
        groups: Dict[Tuple[str, str], List[sqlite3.Row]] = {}
        for row in rows:
            system_key = canonical_station_key(row["system_name"])
            station_key = canonical_station_key(row["station_name"])
            if not system_key or not station_key:
                continue
            groups.setdefault((system_key, station_key), []).append(row)

        changed = 0
        for _key, group in groups.items():
            if len(group) <= 1:
                continue

            def rank(row: sqlite3.Row) -> Tuple[int, str, str, int]:
                # Prefer real/local visited rows, then newest visited/market row, then positive real MarketID.
                local = 1 if row["source"] == "local_visit" or row["last_station_visit_datetime"] else 0
                visit = row["last_station_visit_datetime"] or ""
                market = row["market_updated"] or ""
                real_id = 1 if int(row["market_id"]) > 0 else 0
                return (local, visit, market, real_id)

            keeper = sorted(group, key=rank, reverse=True)[0]
            keeper_id = int(keeper["market_id"])
            for loser in group:
                loser_id = int(loser["market_id"])
                if loser_id == keeper_id:
                    continue

                # Fill missing current metadata from the row we are about to remove.
                conn.execute(
                    """
                    UPDATE stations SET
                        system_address=COALESCE(stations.system_address, ?),
                        station_name=COALESCE(stations.station_name, ?),
                        station_type=COALESCE(stations.station_type, ?),
                        largest_pad=COALESCE(stations.largest_pad, ?),
                        station_faction_name=COALESCE(stations.station_faction_name, ?),
                        station_faction_state=COALESCE(stations.station_faction_state, ?),
                        station_economy=COALESCE(stations.station_economy, ?),
                        station_economies_json=COALESCE(stations.station_economies_json, ?),
                        last_station_visit_datetime=COALESCE(stations.last_station_visit_datetime, ?),
                        source=CASE WHEN stations.source='local_visit' THEN stations.source ELSE COALESCE(stations.source, ?) END,
                        source_pulled_datetime=COALESCE(stations.source_pulled_datetime, ?),
                        distance_to_arrival_ls=COALESCE(stations.distance_to_arrival_ls, ?),
                        body_name=COALESCE(stations.body_name, ?),
                        has_market=COALESCE(stations.has_market, ?),
                        export_commodities_json=COALESCE(stations.export_commodities_json, ?),
                        is_fleet_carrier=MAX(COALESCE(stations.is_fleet_carrier, 0), COALESCE(?, 0)),
                        source_data_updated_datetime=COALESCE(stations.source_data_updated_datetime, ?),
                        market_source_updated_datetime=COALESCE(stations.market_source_updated_datetime, ?),
                        carrier_docking_access=COALESCE(stations.carrier_docking_access, ?),
                        carrier_name=COALESCE(stations.carrier_name, ?),
                        planetary=COALESCE(stations.planetary, ?),
                        marketplace=COALESCE(stations.marketplace, ?)
                    WHERE market_id=?
                    """,
                    (
                        loser["system_address"], loser["station_name"], loser["station_type"], loser["largest_pad"],
                        loser["station_faction_name"], loser["station_faction_state"], loser["station_economy"], loser["station_economies_json"],
                        loser["last_station_visit_datetime"], loser["source"], loser["source_pulled_datetime"], loser["distance_to_arrival_ls"],
                        loser["body_name"], loser["has_market"], loser["export_commodities_json"], loser["is_fleet_carrier"],
                        loser["source_data_updated_datetime"], loser["market_source_updated_datetime"], loser["carrier_docking_access"], loser["carrier_name"],
                        loser["planetary"], loser["marketplace"], keeper_id,
                    ),
                )
                merge_market_prices(conn, loser_id, keeper_id)
                # Preserve jackpot/history by repointing historical rows to the current station row.
                conn.execute("UPDATE jackpot_events SET market_id=? WHERE market_id=?", (keeper_id, loser_id))
                conn.execute("UPDATE jackpot_samples SET market_id=? WHERE market_id=?", (keeper_id, loser_id))
                conn.execute("DELETE FROM stations WHERE market_id=?", (loser_id,))
                changed += 1
        if changed:
            conn.commit()
            log_market_debug("station duplicate dedupe", {"stations_merged": changed})
        return changed
    except Exception:
        log_exception("deduplicate_station_rows")
        return 0


def deduplicate_market_price_commodities(conn: sqlite3.Connection) -> int:
    """Merge legacy duplicate market_prices rows by canonical commodity key.

    Older MarketScout versions sometimes stored a display name from the CSV
    catalogue (``Agronomic Treatment``) and a Frontier symbol-derived name
    (``Agronomictreatment``) as separate commodities for the same market. This
    migration keeps the newest row for each ``market_id + canonical key`` and
    rewrites it to the catalogue display name when available.
    """
    try:
        rows = conn.execute(
            """
            SELECT market_id, commodity, buy_price, sell_price, supply, demand, market_price_update_datetime
            FROM market_prices
            ORDER BY market_id, commodity
            """
        ).fetchall()
        grouped: Dict[Tuple[int, str], List[sqlite3.Row]] = {}
        for row in rows:
            key = canonical_commodity_key(row["commodity"])
            if not key:
                continue
            grouped.setdefault((int(row["market_id"]), key), []).append(row)

        changed = 0
        for (market_id, key), group in grouped.items():
            canonical_name = commodity_display_from_stats_key(key) or normalize_commodity_name(group[0]["commodity"]) or group[0]["commodity"]
            if len(group) == 1 and group[0]["commodity"] == canonical_name:
                continue

            def sort_key(r: sqlite3.Row) -> Tuple[str, int]:
                ts = r["market_price_update_datetime"] or ""
                # Prefer rows with actual prices/supply when timestamps tie.
                quality = 0
                for field in ("buy_price", "sell_price", "supply", "demand"):
                    if r[field] is not None:
                        quality += 1
                return (ts, quality)

            best = sorted(group, key=sort_key, reverse=True)[0]
            conn.execute(
                "DELETE FROM market_prices WHERE market_id=? AND commodity IN (%s)" % ",".join("?" for _ in group),
                [market_id] + [r["commodity"] for r in group],
            )
            conn.execute(
                """
                INSERT INTO market_prices(market_id, commodity, buy_price, sell_price, supply, demand, market_price_update_datetime)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(market_id, commodity) DO UPDATE SET
                    buy_price=excluded.buy_price,
                    sell_price=excluded.sell_price,
                    supply=excluded.supply,
                    demand=excluded.demand,
                    market_price_update_datetime=excluded.market_price_update_datetime
                """,
                (
                    market_id,
                    canonical_name,
                    best["buy_price"],
                    best["sell_price"],
                    best["supply"],
                    best["demand"],
                    best["market_price_update_datetime"],
                ),
            )
            changed += 1
        if changed:
            conn.commit()
            log_market_debug("market_prices legacy commodity dedupe", {"groups_merged": changed})
        return changed
    except Exception:
        log_exception("deduplicate_market_price_commodities")
        return 0


def normalize_commodity_name(raw: Any) -> Optional[str]:
    """Return a display commodity name for any commodity, without suffix collisions.

    Frontier localized names often look like ``$gold_name;``.  We clean those
    into stable display names.  Exact aliases for our common commodities keep
    nice capitalization, but unknown commodities are still stored instead of
    being discarded.  We deliberately do not use suffix matching, so rare goods
    like Sothis Crystalline Gold will not overwrite normal Gold.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.strip("$;")
    if s.lower().endswith("_name"):
        s = s[:-5]
    key = canonical_commodity_key(s)
    if key in COMMODITY_KEYWORDS:
        return COMMODITY_KEYWORDS[key]
    # Prefer the user's commodities.csv catalogue when it has a nice display
    # name for this Frontier symbol. Example: $agronomictreatment_name; ->
    # Agronomic Treatment, not Agronomictreatment.
    catalog_name = commodity_display_from_stats_key(key)
    if catalog_name:
        return catalog_name
    # Convert internal symbols to a readable title. This is intentionally simple
    # and local-only; the original market row remains represented by this name.
    cleaned = s.replace("_", " ").replace("-", " ").strip()
    if not cleaned:
        return None
    # Split camel-ish rare names a little: sothiscrystallinegold -> Sothis Crystalline Gold.
    import re
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    # Known lower-case Frontier symbols have no spaces; keep a readable title.
    if " " not in cleaned and cleaned.islower():
        parts = []
        # Small special cases for names that matter to avoiding confusion.
        special = {"sothiscrystallinegold": "Sothis Crystalline Gold"}
        if key in special:
            return special[key]
    return " ".join(w.capitalize() for w in cleaned.split())

def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Frontier symbols look like "$economy_Extraction;". Keep user-facing part when possible.
    if s.startswith("$") and s.endswith(";"):
        s = s[1:-1]
        for prefix in ("economy_", "government_", "security_", "state_"):
            if s.lower().startswith(prefix):
                s = s[len(prefix):]
        s = s.replace("_name", "")
    return s.replace("_", " ").strip()


def first_text(*values: Any) -> Optional[str]:
    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return None


def first_int(*values: Any) -> Optional[int]:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except Exception:
            try:
                return int(float(value))
            except Exception:
                pass
    return None


def safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def as_dict(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    inner = getattr(value, "data", None)
    if isinstance(inner, dict):
        return inner
    if isinstance(inner, Mapping):
        return dict(inner)
    return None


def get_item(obj: Any, key: str) -> Any:
    try:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(key)
        return obj[key]
    except Exception:
        return None




def open_modern_ui() -> None:
    """Start the local browser UI and open it in the default browser."""
    try:
        if DB_PATH is None or PLUGIN_DIR is None:
            messagebox.showerror("MarketScout", "MarketScout database is not initialized yet.")
            return
        web = load_web_module()
        web.start_server(PLUGIN_DIR, DB_PATH, TARGET_COMMODITIES, PRIMARY_METALS)
        url = web.server_url() or "http://127.0.0.1:40595/"
        webbrowser.open(url)
        if WINDOW is not None:
            WINDOW.status_var.set(f"Opened MarketScout Web UI at {url}")
    except Exception as e:
        log_exception("open_modern_ui")
        messagebox.showerror("MarketScout", f"Could not open Web UI:\n{e}")

def open_window() -> None:
    global WINDOW
    if ROOT is None:
        return
    if WINDOW is None or not WINDOW.exists():
        WINDOW = MarketScoutWindow(ROOT)
    else:
        WINDOW.lift()
        WINDOW.refresh()


def log_exception(where: str) -> None:
    try:
        path = os.path.join(os.path.dirname(DB_PATH or os.getcwd()), "marketscout-error.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"----- {now_utc_iso()} {where} -----\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass


class MarketScoutWindow:
    def __init__(self, parent: tk.Misc) -> None:
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title(f"ED Market Scout {PLUGIN_VERSION}")
        self.win.geometry("1300x700")
        self.status_var = tk.StringVar(value="Local-only recorder. No uploads are performed by this plugin.")
        self.sort_specs: List[Tuple[str, str]] = []
        self.column_headings: Dict[str, str] = {}
        self.visible_columns: List[str] = []
        ui_config = load_ui_config()
        self.highlight_price_var = tk.StringVar(value=str(first_int(ui_config.get("highlight_price")) or DEFAULT_HIGHLIGHT_PRICE))
        self.highlight_supply_var = tk.StringVar(value=str(first_int(ui_config.get("highlight_supply")) or DEFAULT_HIGHLIGHT_SUPPLY))
        self._build_ui()
        self.refresh()

    def exists(self) -> bool:
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False

    def lift(self) -> None:
        self.win.lift()
        self.win.focus_force()

    def _build_ui(self) -> None:
        filter_frame = ttk.LabelFrame(self.win, text="Filters")
        filter_frame.pack(fill=tk.X, padx=6, pady=6)

        self.system_filter = tk.StringVar()
        self.station_filter = tk.StringVar()
        self.economy_filter = tk.StringVar(value="Extraction, Refinery")
        self.state_filter = tk.StringVar()
        self.pad_filter = tk.StringVar(value="Any")
        self.source_filter = tk.StringVar(value="Any")
        self.include_fleet_carriers_var = tk.BooleanVar(value=False)
        self.age_days_filter = tk.StringVar()
        self.min_supply_filter = tk.StringVar()
        self.price_filters: Dict[str, tk.StringVar] = {c: tk.StringVar() for c in TARGET_COMMODITIES[:4]}

        r = 0
        ttk.Label(filter_frame, text="System contains").grid(row=r, column=0, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.system_filter, width=18).grid(row=r, column=1, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="Station contains").grid(row=r, column=2, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.station_filter, width=18).grid(row=r, column=3, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="Economy contains any").grid(row=r, column=4, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.economy_filter, width=24).grid(row=r, column=5, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="State contains").grid(row=r, column=6, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.state_filter, width=22).grid(row=r, column=7, sticky=tk.W, padx=3)

        r += 1
        col = 0
        for commodity, var in self.price_filters.items():
            ttk.Label(filter_frame, text=f"{commodity} buy <=").grid(row=r, column=col, sticky=tk.W)
            ttk.Entry(filter_frame, textvariable=var, width=8).grid(row=r, column=col + 1, sticky=tk.W, padx=3)
            col += 2
        ttk.Label(filter_frame, text="Min supply").grid(row=r, column=col, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.min_supply_filter, width=8).grid(row=r, column=col + 1, sticky=tk.W, padx=3)

        r += 1
        ttk.Label(filter_frame, text="Market age <= days").grid(row=r, column=0, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.age_days_filter, width=8).grid(row=r, column=1, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="Pad").grid(row=r, column=2, sticky=tk.W)
        ttk.Combobox(filter_frame, textvariable=self.pad_filter, values=["Any", "L", "M", "S", "Unknown"], width=10, state="readonly").grid(row=r, column=3, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="Source").grid(row=r, column=4, sticky=tk.W)
        ttk.Combobox(filter_frame, textvariable=self.source_filter, values=["Any", "local_visit", "spansh", "imported"], width=12, state="readonly").grid(row=r, column=5, sticky=tk.W, padx=3)
        ttk.Checkbutton(filter_frame, text="Include fleet carriers", variable=self.include_fleet_carriers_var).grid(row=r, column=6, sticky=tk.W, padx=3)
        ttk.Button(filter_frame, text="Import CSV...", command=self.import_csv).grid(row=r, column=7, sticky=tk.W, padx=3)

        r += 1
        ttk.Button(filter_frame, text="Apply", command=self.refresh).grid(row=r, column=4, sticky=tk.W, padx=3)
        ttk.Button(filter_frame, text="Clear", command=self.clear_filters).grid(row=r, column=5, sticky=tk.W, padx=3)
        ttk.Button(filter_frame, text="Refresh", command=self.refresh).grid(row=r, column=6, sticky=tk.W, padx=3)
        ttk.Button(filter_frame, text="Columns...", command=self.open_column_selector).grid(row=r, column=7, sticky=tk.W, padx=3)

        r += 1
        ttk.Label(filter_frame, text="Highlight price <=").grid(row=r, column=0, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.highlight_price_var, width=8).grid(row=r, column=1, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="Strong supply >=").grid(row=r, column=2, sticky=tk.W)
        ttk.Entry(filter_frame, textvariable=self.highlight_supply_var, width=8).grid(row=r, column=3, sticky=tk.W, padx=3)
        ttk.Label(filter_frame, text="Blue = cheap; green = cheap + high supply").grid(row=r, column=4, columnspan=4, sticky=tk.W, padx=3)

        sort_frame = ttk.LabelFrame(self.win, text="Multi-field sort")
        sort_frame.pack(fill=tk.X, padx=6, pady=(0, 6))
        sort_columns = [
            "market_updated", "station_visit", "source_pulled", "system", "station", "state", "economies",
            "population", "security", "pad", "arrival_ls", "source", "source_updated", "market_source_updated",
        ]
        for commodity in TARGET_COMMODITIES:
            sort_columns.extend([
                f"{commodity}_buy", f"{commodity}_sell", f"{commodity}_supply", f"{commodity}_demand"
            ])
        self.sort_vars: List[tk.StringVar] = []
        self.sort_dir_vars: List[tk.StringVar] = []
        for i in range(3):
            ttk.Label(sort_frame, text=f"Sort {i+1}").grid(row=0, column=i*3, sticky=tk.W, padx=(4, 2))
            sv = tk.StringVar(value="" if i else "market_updated")
            dv = tk.StringVar(value="DESC" if i == 0 else "ASC")
            self.sort_vars.append(sv)
            self.sort_dir_vars.append(dv)
            ttk.Combobox(sort_frame, textvariable=sv, values=[""] + sort_columns, width=18, state="readonly").grid(row=0, column=i*3+1, sticky=tk.W)
            ttk.Combobox(sort_frame, textvariable=dv, values=["ASC", "DESC"], width=6, state="readonly").grid(row=0, column=i*3+2, sticky=tk.W, padx=(2, 8))
        ttk.Button(sort_frame, text="Apply Sort", command=self.refresh).grid(row=0, column=10, sticky=tk.W)

        table_frame = ttk.Frame(self.win)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.columns = [
            "flag", "location", "system", "station", "type", "pad", "fleet_carrier", "state", "economies", "system_economy",
            "security", "population", "arrival_ls", "source", "source_pulled",
            "source_updated", "market_source_updated", "planetary",
            "system_visit", "station_visit", "market_updated",
        ]
        # Compact metal columns display two values in one cell, e.g. buy price on
        # the first line and supply on the second line. This keeps the common
        # scouting view narrow while retaining the detailed single-value columns.
        for c in PRIMARY_METALS:
            self.columns += [f"{c}_buy_compact", f"{c}_sell_compact"]
        # Detailed columns, ordered the way the scouting workflow usually reads:
        # buy/supply first, then sell/demand.
        for c in PRIMARY_METALS:
            self.columns += [f"{c}_buy", f"{c}_supply"]
        for c in PRIMARY_METALS:
            self.columns += [f"{c}_sell", f"{c}_demand"]
        for c in TARGET_COMMODITIES:
            if c not in PRIMARY_METALS:
                self.columns += [f"{c}_buy", f"{c}_supply", f"{c}_sell", f"{c}_demand"]

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.column_headings = {
            "flag": "Flag", "location": "System / Station", "system": "System", "station": "Station", "type": "Type", "pad": "Pad",
            "fleet_carrier": "Fleet Carrier", "state": "Faction State",
            "economies": "Station Economies", "system_economy": "System Econ", "security": "Security", "population": "Population",
            "arrival_ls": "Arrival LS", "source": "Source", "source_pulled": "Source Pulled",
            "source_updated": "Source Updated", "market_source_updated": "Market Src Updated",
            "planetary": "Planetary",
            "system_visit": "System Visit", "station_visit": "Station Visit", "market_updated": "Market Updated",
        }
        for c in TARGET_COMMODITIES:
            self.column_headings[f"{c}_buy"] = f"{c} Buy"
            self.column_headings[f"{c}_supply"] = f"{c} Supply"
            self.column_headings[f"{c}_sell"] = f"{c} Sell"
            self.column_headings[f"{c}_demand"] = f"{c} Demand"
        for c in PRIMARY_METALS:
            self.column_headings[f"{c}_buy_compact"] = f"{c} Buy"
            self.column_headings[f"{c}_sell_compact"] = f"{c} Sell"

        for col in self.columns:
            text = self.column_headings.get(col, col.replace("_", " "))
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by_header(c))
            width = 110
            if col in ("system", "station", "economies", "state"):
                width = 170
            if col == "location":
                width = 260
            if col.endswith(("_buy", "_sell", "_supply", "_demand")) or col in ("pad", "type", "source", "planetary"):
                width = 85
            if col.endswith("_compact"):
                width = 95
            if col in ("source_pulled", "source_updated", "market_source_updated"):
                width = 145
            if col == "flag":
                width = 125
            self.tree.column(col, width=width, stretch=True)

        self.tree.tag_configure("cheap", background="#d8ecff")
        self.tree.tag_configure("strong", background="#d8ffd8")
        # Give compact two-line cells enough vertical room. Some themes may still
        # cap Treeview row height; the Flag column remains as a fallback.
        try:
            ttk.Style().configure("Treeview", rowheight=42)
        except Exception:
            pass

        self.visible_columns = self.load_visible_columns()
        self.apply_visible_columns(save=False)

        status = ttk.Label(self.win, textvariable=self.status_var, anchor=tk.W)
        status.pack(fill=tk.X, padx=6, pady=(0, 6))

    def default_visible_columns(self) -> List[str]:
        # Keep first-run display compact while still useful for cheap-metal scouting.
        preferred = [
            "flag", "location", "state", "economies", "security", "population", "source",
            "station_visit", "market_updated",
            "Palladium_buy_compact", "Gold_buy_compact", "Silver_buy_compact",
            "Palladium_sell_compact", "Gold_sell_compact", "Silver_sell_compact",
        ]
        return [c for c in preferred if c in self.columns]

    def load_visible_columns(self) -> List[str]:
        data = load_ui_config()
        cols = data.get("visible_columns")
        if data.get("ui_schema_version") == UI_SCHEMA_VERSION and isinstance(cols, list):
            valid = [c for c in cols if c in self.columns]
            if valid:
                return valid
        # 0.1.6 introduced compact two-line columns and a new default order.
        # Use the new defaults once after upgrade so users see the new layout.
        update_ui_config(ui_schema_version=UI_SCHEMA_VERSION)
        return self.default_visible_columns()

    def apply_visible_columns(self, save: bool = True) -> None:
        valid = [c for c in self.visible_columns if c in self.columns]
        if not valid:
            valid = self.default_visible_columns() or self.columns[:1]
        self.visible_columns = valid
        try:
            self.tree.configure(displaycolumns=self.visible_columns)
        except Exception:
            self.tree.configure(displaycolumns="#all")
        if save:
            update_ui_config(visible_columns=self.visible_columns, ui_schema_version=UI_SCHEMA_VERSION)
        self.status_var.set(f"Showing {len(self.visible_columns)} of {len(self.columns)} columns. Database: {DB_PATH}")

    def open_column_selector(self) -> None:
        dialog = tk.Toplevel(self.win)
        dialog.title("MarketScout columns")
        dialog.transient(self.win)
        dialog.grab_set()

        outer = ttk.Frame(dialog, padding=8)
        outer.pack(fill=tk.BOTH, expand=True)
        ttk.Label(outer, text="Choose which columns are visible in the table.").pack(anchor=tk.W, pady=(0, 6))

        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0, width=560, height=360)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        vars_by_col: Dict[str, tk.BooleanVar] = {}
        for i, col in enumerate(self.columns):
            var = tk.BooleanVar(value=col in self.visible_columns)
            vars_by_col[col] = var
            label = self.column_headings.get(col, col.replace("_", " "))
            ttk.Checkbutton(inner, text=label, variable=var).grid(row=i // 3, column=i % 3, sticky=tk.W, padx=8, pady=2)

        def set_all(value: bool) -> None:
            for var in vars_by_col.values():
                var.set(value)

        def set_compact() -> None:
            compact = set(self.default_visible_columns())
            for col, var in vars_by_col.items():
                var.set(col in compact)

        def set_core_only() -> None:
            core = {"flag", "location", "state", "economies", "station_visit", "market_updated",
                    "Palladium_buy_compact", "Gold_buy_compact", "Silver_buy_compact"}
            for col, var in vars_by_col.items():
                var.set(col in core)

        def apply_and_close() -> None:
            selected = [col for col in self.columns if vars_by_col[col].get()]
            if not selected:
                messagebox.showwarning("MarketScout", "Select at least one column.", parent=dialog)
                return
            self.visible_columns = selected
            self.apply_visible_columns(save=True)
            dialog.destroy()

        buttons = ttk.Frame(outer)
        buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons, text="All", command=lambda: set_all(True)).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="None", command=lambda: set_all(False)).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Compact", command=set_compact).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Core", command=set_core_only).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=3)
        ttk.Button(buttons, text="Apply", command=apply_and_close).pack(side=tk.RIGHT, padx=3)

    def import_csv(self) -> None:
        if CONN is None:
            return
        path = filedialog.askopenfilename(
            parent=self.win,
            title="Import candidate stations CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
        )
        if not path:
            return
        source_dialog = tk.Toplevel(self.win)
        source_dialog.title("Import source")
        source_dialog.transient(self.win)
        source_dialog.grab_set()
        frame = ttk.Frame(source_dialog, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="CSV source/template").grid(row=0, column=0, sticky=tk.W, padx=3, pady=3)
        source_var = tk.StringVar(value="auto")
        ttk.Combobox(frame, textvariable=source_var, values=["auto", "spansh"], width=16, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=3, pady=3)

        def do_import() -> None:
            try:
                importer = load_importer_module()
                result = importer.import_candidates_csv(CONN, path, source_var.get())
                source_dialog.destroy()
                self.status_var.set(
                    f"Imported {result.get('imported')} {result.get('source')} candidates; skipped {result.get('skipped')}."
                )
                self.refresh()
                messagebox.showinfo(
                    "MarketScout",
                    f"Imported {result.get('imported')} candidate station(s) from {result.get('source')}.\n"
                    f"Skipped: {result.get('skipped')}\nPulled at: {result.get('pulled_at')}",
                    parent=self.win,
                )
            except Exception as e:
                log_exception("import_csv")
                messagebox.showerror("MarketScout", f"Import failed:\n{e}", parent=self.win)

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky=tk.E, pady=(8, 0))
        ttk.Button(buttons, text="Cancel", command=source_dialog.destroy).pack(side=tk.RIGHT, padx=3)
        ttk.Button(buttons, text="Import", command=do_import).pack(side=tk.RIGHT, padx=3)

    def clear_filters(self) -> None:
        self.system_filter.set("")
        self.station_filter.set("")
        self.economy_filter.set("")
        self.state_filter.set("")
        self.pad_filter.set("Any")
        self.source_filter.set("Any")
        self.include_fleet_carriers_var.set(False)
        self.age_days_filter.set("")
        self.min_supply_filter.set("")
        for v in self.price_filters.values():
            v.set("")
        self.refresh()

    def sort_by_header(self, col: str) -> None:
        current = self.sort_vars[0].get()
        if current == col:
            self.sort_dir_vars[0].set("ASC" if self.sort_dir_vars[0].get() == "DESC" else "DESC")
        else:
            self.sort_vars[0].set(col)
            self.sort_dir_vars[0].set("ASC")
        self.refresh()

    def refresh(self) -> None:
        if CONN is None:
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            sql, params = self.build_query()
            self.save_highlight_settings()
            rows = CONN.execute(sql, params).fetchall()
            for row in rows:
                tag, flag = self.row_highlight(row)
                values = []
                keys = row.keys()
                for col in self.columns:
                    if col == "flag":
                        values.append(flag)
                    elif col == "location":
                        values.append(self.format_location(row))
                    elif col.endswith("_buy_compact"):
                        commodity = col[:-12]
                        values.append(self.format_price_pair(row, commodity, "buy_price"))
                    elif col.endswith("_sell_compact"):
                        commodity = col[:-13]
                        values.append(self.format_price_pair(row, commodity, "sell_price"))
                    else:
                        values.append(row[col] if col in keys else "")
                tags = (tag,) if tag else ()
                self.tree.insert("", tk.END, values=values, tags=tags)
            self.status_var.set(f"{len(rows)} rows. Showing {len(self.visible_columns)} of {len(self.columns)} columns. Database: {DB_PATH}")
        except Exception as e:
            log_exception("refresh")
            messagebox.showerror("MarketScout", f"Could not refresh table:\n{e}")

    def format_location(self, row: sqlite3.Row) -> str:
        system = row["system"] if "system" in row.keys() and row["system"] is not None else ""
        station = row["station"] if "station" in row.keys() and row["station"] is not None else ""
        pad = row["pad"] if "pad" in row.keys() and row["pad"] is not None else ""
        second = station
        if pad:
            second = f"{second} | Pad {pad}" if second else f"Pad {pad}"
        return f"{system}\n{second}" if second else str(system)

    def format_price_pair(self, row: sqlite3.Row, commodity: str, price_kind: str) -> str:
        # price_kind: buy_price => show buy + supply; sell_price => show sell + demand
        keys = row.keys()
        price_col = f"{commodity}_buy" if price_kind == "buy_price" else f"{commodity}_sell"
        qty_col = f"{commodity}_supply" if price_kind == "buy_price" else f"{commodity}_demand"
        price = row[price_col] if price_col in keys and row[price_col] is not None else ""
        qty = row[qty_col] if qty_col in keys and row[qty_col] is not None else ""
        if price == "" and qty == "":
            return ""
        if price == "":
            return f"—\n{qty}"
        if qty == "":
            return f"{price}\n—"
        return f"{price}\n{qty}"

    def save_highlight_settings(self) -> None:
        price = first_int(self.highlight_price_var.get())
        supply = first_int(self.highlight_supply_var.get())
        if price is None:
            price = DEFAULT_HIGHLIGHT_PRICE
            self.highlight_price_var.set(str(price))
        if supply is None:
            supply = DEFAULT_HIGHLIGHT_SUPPLY
            self.highlight_supply_var.set(str(supply))
        update_ui_config(highlight_price=price, highlight_supply=supply)

    def row_highlight(self, row: sqlite3.Row) -> Tuple[str, str]:
        price_threshold = first_int(self.highlight_price_var.get()) or DEFAULT_HIGHLIGHT_PRICE
        supply_threshold = first_int(self.highlight_supply_var.get()) or DEFAULT_HIGHLIGHT_SUPPLY

        cheap_commodities: List[str] = []
        strong_commodities: List[str] = []
        keys = row.keys()
        for commodity in PRIMARY_METALS:
            buy_col = f"{commodity}_buy"
            supply_col = f"{commodity}_supply"
            if buy_col not in keys:
                continue
            buy_price = first_int(row[buy_col])
            supply = first_int(row[supply_col]) if supply_col in keys else None
            # ED/CAPI/Market.json can use 0 for unavailable/no-buy commodities.
            # Do not treat 0 or negative values as cheap discoveries.
            if buy_price is not None and buy_price > 0 and buy_price <= price_threshold:
                cheap_commodities.append(commodity)
                if supply is not None and supply >= supply_threshold:
                    strong_commodities.append(commodity)

        if strong_commodities:
            return "strong", "★★ " + ", ".join(strong_commodities)
        if cheap_commodities:
            return "cheap", "★ " + ", ".join(cheap_commodities)
        return "", ""

    def build_query(self) -> Tuple[str, List[Any]]:
        select_cols = [
            "s.system_name AS system",
            "st.station_name AS station",
            "st.station_type AS type",
            "COALESCE(st.largest_pad, 'Unknown') AS pad",
            "CASE WHEN COALESCE(st.is_fleet_carrier, 0)=1 THEN 'Yes' ELSE '' END AS fleet_carrier",
            "st.station_faction_state AS state",
            "COALESCE(st.station_economies_json, st.station_economy) AS economies",
            "s.system_economy AS system_economy",
            "s.security AS security",
            "s.population AS population",
            "st.distance_to_arrival_ls AS arrival_ls",
            "COALESCE(st.source, s.source, CASE WHEN st.last_station_visit_datetime IS NOT NULL THEN 'local_visit' ELSE '' END) AS source",
            "COALESCE(st.source_pulled_datetime, s.source_pulled_datetime) AS source_pulled",
            "COALESCE(st.source_data_updated_datetime, s.source_data_updated_datetime) AS source_updated",
            "st.market_source_updated_datetime AS market_source_updated",
            "CASE WHEN st.planetary=1 THEN 'Yes' WHEN st.planetary=0 THEN '' ELSE '' END AS planetary",
            "s.last_visit_datetime AS system_visit",
            "st.last_station_visit_datetime AS station_visit",
            "MAX(mp.market_price_update_datetime) AS market_updated",
        ]
        for c in TARGET_COMMODITIES:
            select_cols.append(f"MAX(CASE WHEN mp.commodity='{c}' THEN mp.buy_price END) AS {c}_buy")
            select_cols.append(f"MAX(CASE WHEN mp.commodity='{c}' THEN mp.sell_price END) AS {c}_sell")
            select_cols.append(f"MAX(CASE WHEN mp.commodity='{c}' THEN mp.supply END) AS {c}_supply")
            select_cols.append(f"MAX(CASE WHEN mp.commodity='{c}' THEN mp.demand END) AS {c}_demand")

        sql = "SELECT " + ", ".join(select_cols) + " FROM stations st LEFT JOIN systems s ON s.system_address=st.system_address LEFT JOIN market_prices mp ON mp.market_id=st.market_id"
        where: List[str] = []
        having: List[str] = []
        params: List[Any] = []

        if self.system_filter.get().strip():
            where.append("s.system_name LIKE ?")
            params.append(f"%{self.system_filter.get().strip()}%")
        if self.station_filter.get().strip():
            where.append("st.station_name LIKE ?")
            params.append(f"%{self.station_filter.get().strip()}%")
        if self.state_filter.get().strip():
            where.append("st.station_faction_state LIKE ?")
            params.append(f"%{self.state_filter.get().strip()}%")
        econ_terms = [x.strip() for x in self.economy_filter.get().split(",") if x.strip()]
        if econ_terms:
            parts = []
            for term in econ_terms:
                parts.append("COALESCE(st.station_economies_json, st.station_economy, '') LIKE ?")
                params.append(f"%{term}%")
            where.append("(" + " OR ".join(parts) + ")")
        pad = self.pad_filter.get()
        if pad and pad != "Any":
            if pad == "Unknown":
                where.append("st.largest_pad IS NULL")
            else:
                where.append("st.largest_pad = ?")
                params.append(pad)
        if not self.include_fleet_carriers_var.get():
            where.append("COALESCE(st.is_fleet_carrier, 0) = 0")
        source = self.source_filter.get()
        if source and source != "Any":
            if source == "imported":
                where.append("COALESCE(st.source, s.source, '') != 'local_visit'")
            else:
                where.append("COALESCE(st.source, s.source, '') = ?")
                params.append(source)

        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY st.market_id"

        for c, var in self.price_filters.items():
            val = first_int(var.get())
            if val is not None:
                having.append(f"{c}_buy <= ?")
                params.append(val)
        min_supply = first_int(self.min_supply_filter.get())
        if min_supply is not None:
            supply_checks = [f"({c}_supply IS NOT NULL AND {c}_supply >= ?)" for c in TARGET_COMMODITIES]
            having.append("(" + " OR ".join(supply_checks) + ")")
            params.extend([min_supply] * len(TARGET_COMMODITIES))
        age_days = first_int(self.age_days_filter.get())
        if age_days is not None:
            having.append("market_updated >= datetime('now', ?)")
            params.append(f"-{age_days} days")
        if having:
            sql += " HAVING " + " AND ".join(having)

        order_parts = []
        allowed = {c: c for c in self.columns}
        # Compact/display-only columns are not SQL aliases. Map them to a useful
        # sortable backing column when a user clicks their header.
        allowed["location"] = "system"
        for c in PRIMARY_METALS:
            allowed[f"{c}_buy_compact"] = f"{c}_buy"
            allowed[f"{c}_sell_compact"] = f"{c}_sell"
        for sv, dv in zip(self.sort_vars, self.sort_dir_vars):
            col = sv.get().strip()
            if not col:
                continue
            direction = "DESC" if dv.get() == "DESC" else "ASC"
            if col in allowed:
                sql_col = allowed[col]
                order_parts.append(f"{sql_col} IS NULL, {sql_col} {direction}")
        if not order_parts:
            order_parts = ["market_updated IS NULL", "market_updated DESC", "station_visit DESC"]
        sql += " ORDER BY " + ", ".join(order_parts)
        return sql, params
