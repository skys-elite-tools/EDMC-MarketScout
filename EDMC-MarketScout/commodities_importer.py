"""Local commodities.csv importer for EDMC-MarketScout.

This module is deliberately local-only: it reads the bundled/user-provided
commodities.csv file and writes commodity stats to SQLite. It performs no
network access, scraping, or reporting.
"""
from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Sequence

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
    "profit": "INTEGER",
    "total_sell_price": "INTEGER",
    "updated_datetime": "TEXT",
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = " ".join(str(value).strip().split())
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    return s


def get(row: Dict[str, Any], *names: str) -> Optional[str]:
    lower = {str(k).strip().lower(): k for k in row.keys()}
    for name in names:
        key = lower.get(name.strip().lower())
        if key is not None:
            return clean_text(row.get(key))
    return None


def first_int(*values: Any) -> Optional[int]:
    for value in values:
        value = clean_text(value)
        if value is None:
            continue
        try:
            return int(value)
        except Exception:
            try:
                return int(float(value))
            except Exception:
                pass
    return None


def first_float(*values: Any) -> Optional[float]:
    for value in values:
        value = clean_text(value)
        if value is None:
            continue
        try:
            return float(value.replace(",", ""))
        except Exception:
            pass
    return None


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def column_exists(conn, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_db(conn) -> None:
    for column, definition in COMMODITY_GLOBAL_STATS_COLUMNS.items():
        add_column_if_missing(conn, "commodity_global_stats", column, definition)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS imports (
            data_name TEXT PRIMARY KEY,
            last_sha256 TEXT NOT NULL,
            imported_datetime TEXT NOT NULL
        )
        """
    )
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
            profit INTEGER,
            total_sell_price INTEGER,
            updated_datetime TEXT
        )
        """
    )
    for column, definition in RARE_COMMODITY_COLUMNS.items():
        add_column_if_missing(conn, "rare_commodities", column, definition)


def last_import_sha(conn, data_name: str) -> Optional[str]:
    row = conn.execute("SELECT last_sha256 FROM imports WHERE data_name=?", (data_name,)).fetchone()
    return str(row[0]) if row and row[0] else None


def record_import(conn, data_name: str, digest: str, ts: str) -> None:
    conn.execute(
        """
        INSERT INTO imports(data_name, last_sha256, imported_datetime)
        VALUES (?, ?, ?)
        ON CONFLICT(data_name) DO UPDATE SET
            last_sha256=excluded.last_sha256,
            imported_datetime=excluded.imported_datetime
        """,
        (data_name, digest, ts),
    )


def ensure_default_commodity_global_stats(conn, defaults: Dict[str, Dict[str, Any]]) -> None:
    migrate_db(conn)
    ts = now_utc_iso()
    for commodity, vals in defaults.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO commodity_global_stats(
                commodity, category, inara_id, avg_sell, avg_buy, avg_profit,
                max_sell, min_buy, max_profit, updated_datetime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                commodity,
                vals.get("category"),
                vals.get("inara_id"),
                vals.get("avg_sell"),
                vals.get("avg_buy"),
                vals.get("avg_profit"),
                vals.get("max_sell"),
                vals.get("min_buy"),
                vals.get("max_profit"),
                ts,
            ),
        )


def refresh_commodity_global_stats_from_csv(
    conn,
    plugin_dir: str,
    defaults: Dict[str, Dict[str, Any]],
    normalize_commodity_name: Optional[Callable[[Any], Optional[str]]] = None,
) -> Dict[str, int]:
    """Refresh commodity_global_stats from optional commodities.csv.

    Supported CSV columns:
    commodity_name, category, inara_id, avg_sell, avg_buy, avg_profit,
    max_sell, min_buy, max_profit.
    """
    ensure_default_commodity_global_stats(conn, defaults)
    path = os.path.join(plugin_dir, "rawdata", "commodities.csv")
    if not os.path.exists(path):
        legacy_path = os.path.join(plugin_dir, "commodities.csv")
        path = legacy_path if os.path.exists(legacy_path) else path
    if not os.path.exists(path):
        conn.commit()
        return {"imported": 0, "skipped": 0}

    digest = sha256_file(path)
    if last_import_sha(conn, "commodities") == digest:
        conn.commit()
        return {"imported": 0, "skipped": 0, "unchanged": 1}

    ts = now_utc_iso()
    imported = 0
    skipped = 0
    conn.execute("DELETE FROM commodity_global_stats")
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            commodity = get(row, "commodity_name", "commodity", "name")
            if not commodity and normalize_commodity_name is not None:
                commodity = normalize_commodity_name(row.get("commodity_name") or row.get("commodity") or row.get("name"))
            if not commodity:
                skipped += 1
                continue

            values = {
                "category": get(row, "category"),
                "inara_id": first_int(get(row, "inara_id", "inaraId")),
                "avg_sell": first_int(get(row, "avg_sell", "avgSell")),
                "avg_buy": first_int(get(row, "avg_buy", "avgBuy")),
                "avg_profit": first_int(get(row, "avg_profit", "avgProfit")),
                "max_sell": first_int(get(row, "max_sell", "commodityMaxSellPrice", "maxSell")),
                "min_buy": first_int(get(row, "min_buy", "minBuy")),
                "max_profit": first_int(get(row, "max_profit", "maxProfit")),
            }
            conn.execute(
                """
                INSERT INTO commodity_global_stats(
                    commodity, category, inara_id, avg_sell, avg_buy, avg_profit,
                    max_sell, min_buy, max_profit, updated_datetime
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(commodity) DO UPDATE SET
                    category=excluded.category,
                    inara_id=excluded.inara_id,
                    avg_sell=excluded.avg_sell,
                    avg_buy=excluded.avg_buy,
                    avg_profit=excluded.avg_profit,
                    max_sell=excluded.max_sell,
                    min_buy=excluded.min_buy,
                    max_profit=excluded.max_profit,
                    updated_datetime=excluded.updated_datetime
                """,
                (
                    commodity,
                    values["category"],
                    values["inara_id"],
                    values["avg_sell"],
                    values["avg_buy"],
                    values["avg_profit"],
                    values["max_sell"],
                    values["min_buy"],
                    values["max_profit"],
                    ts,
                ),
            )
            imported += 1
    record_import(conn, "commodities", digest, ts)
    conn.commit()
    return {"imported": imported, "skipped": skipped, "unchanged": 0}


def placeholders(values: Sequence[object]) -> str:
    return ",".join("?" for _ in values)


def refresh_rare_commodities_from_csv(conn, plugin_dir: str) -> Dict[str, int]:
    """Refresh rare_commodities from optional rawdata/commodities_rare.csv."""
    migrate_db(conn)
    path = os.path.join(plugin_dir, "rawdata", "commodities_rare.csv")
    if not os.path.exists(path):
        conn.commit()
        return {"imported": 0, "skipped": 0}

    digest = sha256_file(path)
    if last_import_sha(conn, "rare_commodities") == digest:
        conn.commit()
        return {"imported": 0, "skipped": 0, "unchanged": 1}

    ts = now_utc_iso()
    imported = 0
    skipped = 0
    seen: list[str] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            commodity = get(row, "commodity_name", "commodity", "name")
            if not commodity:
                skipped += 1
                continue
            seen.append(commodity)
            conn.execute(
                """
                INSERT INTO rare_commodities(
                    commodity, inara_commodity_id, station_name, system_name, inara_location_id,
                    station_distance_ls, distance_from_sol_ly, usual_supply, buy_price,
                    profit, total_sell_price, updated_datetime
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(commodity) DO UPDATE SET
                    inara_commodity_id=excluded.inara_commodity_id,
                    station_name=excluded.station_name,
                    system_name=excluded.system_name,
                    inara_location_id=excluded.inara_location_id,
                    station_distance_ls=rare_commodities.station_distance_ls,
                    distance_from_sol_ly=rare_commodities.distance_from_sol_ly,
                    usual_supply=excluded.usual_supply,
                    buy_price=excluded.buy_price,
                    profit=excluded.profit,
                    total_sell_price=excluded.total_sell_price,
                    updated_datetime=excluded.updated_datetime
                """,
                (
                    commodity,
                    first_int(get(row, "inara_commodity_id", "inaraCommodityId")),
                    get(row, "station_name", "station"),
                    get(row, "system_name", "system"),
                    first_int(get(row, "inara_location_id", "inaraLocationId")),
                    first_float(get(row, "station_distance_ls", "st_dist", "st dist")),
                    first_float(get(row, "distance_from_sol_ly", "distance")),
                    first_int(get(row, "usual_supply", "supply")),
                    first_int(get(row, "buy_price", "buy price")),
                    first_int(get(row, "profit")),
                    first_int(get(row, "total_sell_price", "total sell price")),
                    ts,
                ),
            )
            imported += 1

    if seen:
        conn.execute(
            f"DELETE FROM rare_commodities WHERE commodity NOT IN ({placeholders(seen)})",
            seen,
        )
    else:
        conn.execute("DELETE FROM rare_commodities")
    record_import(conn, "rare_commodities", digest, ts)
    conn.commit()
    return {"imported": imported, "skipped": skipped, "unchanged": 0}
