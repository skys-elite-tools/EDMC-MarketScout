"""Local commodities.csv importer for EDMC-MarketScout.

This module is deliberately local-only: it reads the bundled/user-provided
commodities.csv file and writes commodity stats to SQLite. It performs no
network access, scraping, or reporting.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

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


def column_exists(conn, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    if not column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_db(conn) -> None:
    for column, definition in COMMODITY_GLOBAL_STATS_COLUMNS.items():
        add_column_if_missing(conn, "commodity_global_stats", column, definition)


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
    path = os.path.join(plugin_dir, "commodities.csv")
    if not os.path.exists(path):
        conn.commit()
        return {"imported": 0, "skipped": 0}

    ts = now_utc_iso()
    imported = 0
    skipped = 0
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
    conn.commit()
    return {"imported": imported, "skipped": skipped}
