"""Trade ledger support for EDMC-MarketScout.

Records MarketBuy/MarketSell journal events into a local SQLite ledger and
calculates sell profit using a LIFO inventory model from previously-recorded
buys of the same commodity.

This module is intentionally local-only. It performs no network I/O.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

SALES_CADENCE_WINDOW_MINUTES = 60


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
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

        CREATE INDEX IF NOT EXISTS idx_trade_events_time ON trade_events(event_datetime);
        CREATE INDEX IF NOT EXISTS idx_trade_events_commodity_time ON trade_events(commodity, event_datetime);
        CREATE INDEX IF NOT EXISTS idx_trade_lots_open ON trade_lots(commodity, remaining_quantity, buy_datetime);
        """
    )

    ensure_columns(conn, "trade_events", {
        "journal_avg_price_paid": "REAL",
        "journal_profit": "INTEGER",
        "journal_profit_per_unit": "REAL",
        "ledger_avg_buy_price": "REAL",
        "ledger_profit": "INTEGER",
        "ledger_profit_per_hour": "REAL",
        "cost_basis_method": "TEXT",
        "supply_at_trade": "INTEGER",
        "demand_at_trade": "INTEGER",
    })
    conn.execute("UPDATE trade_events SET journal_avg_price_paid=avg_buy_price WHERE journal_avg_price_paid IS NULL AND avg_buy_price IS NOT NULL")
    conn.execute("UPDATE trade_events SET journal_profit=profit WHERE journal_profit IS NULL AND profit IS NOT NULL")
    conn.execute("UPDATE trade_events SET ledger_avg_buy_price=avg_buy_price WHERE ledger_avg_buy_price IS NULL AND avg_buy_price IS NOT NULL")
    conn.execute("UPDATE trade_events SET ledger_profit=profit WHERE ledger_profit IS NULL AND profit IS NOT NULL")
    conn.execute("UPDATE trade_events SET ledger_profit_per_hour=profit_per_hour WHERE ledger_profit_per_hour IS NULL AND profit_per_hour IS NOT NULL")


def ensure_columns(conn: sqlite3.Connection, table: str, columns: Dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, decl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def record_trade_event(conn: sqlite3.Connection, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]) -> Optional[int]:
    event = entry.get("event")
    if event not in ("MarketBuy", "MarketSell"):
        return None

    event_time = str(entry.get("timestamp") or now_utc_iso())
    trade_type = "buy" if event == "MarketBuy" else "sell"
    commodity = normalize_commodity_name(entry.get("Type_Localised") or entry.get("Type") or entry.get("Commodity"))
    if not commodity:
        return None

    quantity = first_int(entry.get("Count"), entry.get("Quantity")) or 0
    if quantity <= 0:
        return None

    system_name = first_text(entry.get("StarSystem"), state.get("SystemName"), system)
    station_name = first_text(entry.get("StationName"), state.get("StationName"), station)
    system_address = first_int(entry.get("SystemAddress"), state.get("SystemAddress"))
    market_id = first_int(entry.get("MarketID"), state.get("MarketID"))
    supply_at_trade, demand_at_trade = lookup_market_quantities(conn, market_id, commodity)

    if trade_type == "buy":
        unit_price = first_int(entry.get("BuyPrice"), entry.get("Price"))
        total = first_int(entry.get("TotalCost"))
        if unit_price is None and total is not None and quantity:
            unit_price = int(round(total / quantity))
        if total is None and unit_price is not None:
            total = unit_price * quantity
        trade_id = insert_trade_event(
            conn, event_time, trade_type, system_address, system_name, market_id, station_name,
            commodity, quantity, unit_price, total, None, None, None, None, 0, None, None, None, None, None, None, "none", supply_at_trade, demand_at_trade, [], entry,
        )
        if unit_price is not None:
            conn.execute(
                """
                INSERT INTO trade_lots(
                    commodity, buy_datetime, system_address, system_name, market_id, station_name,
                    original_quantity, remaining_quantity, unit_price, total_cost, source_trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    commodity, event_time, system_address, system_name, market_id, station_name,
                    quantity, quantity, int(unit_price), int(total if total is not None else unit_price * quantity), trade_id,
                ),
            )
        return trade_id

    unit_price = first_int(entry.get("SellPrice"), entry.get("Price"))
    total = first_int(entry.get("TotalSale"), entry.get("Total"))
    if unit_price is None and total is not None and quantity:
        unit_price = int(round(total / quantity))
    if total is None and unit_price is not None:
        total = unit_price * quantity

    ledger_avg_buy, known_cost, covered_qty, consumed = consume_lifo_lots(conn, commodity, quantity, event_time)
    ledger_profit: Optional[int] = None
    ledger_profit_per_hour: Optional[float] = None
    if unit_price is not None and known_cost is not None and covered_qty > 0:
        # LIFO/statistical view: only calculate for the quantity whose purchase history is known.
        ledger_profit = int((unit_price * covered_qty) - known_cost)
        weighted_hours = weighted_holding_hours(consumed, event_time)
        if weighted_hours and weighted_hours > 0:
            ledger_profit_per_hour = ledger_profit / weighted_hours

    journal_avg = first_float(entry.get("AvgPricePaid"), entry.get("AveragePricePaid"), entry.get("AvgPrice"))
    journal_profit: Optional[int] = None
    journal_profit_per_unit: Optional[float] = None
    if journal_avg is not None and quantity > 0:
        if total is not None:
            journal_profit = int(round(total - (journal_avg * quantity)))
        elif unit_price is not None:
            journal_profit = int(round((unit_price - journal_avg) * quantity))
        if unit_price is not None:
            journal_profit_per_unit = float(unit_price) - float(journal_avg)

    primary_avg = journal_avg if journal_avg is not None else ledger_avg_buy
    primary_profit = journal_profit if journal_profit is not None else ledger_profit
    # Primary credits/hour is based on sale cadence, not cargo holding time:
    # if another sale happened within the previous SALES_CADENCE_WINDOW_MINUTES,
    # estimate how much current-sale profit would scale to one hour.
    primary_profit_per_hour = sale_cadence_profit_per_hour(conn, event_time, primary_profit)
    method = "journal_avg_price_paid" if journal_avg is not None else "lifo"

    trade_id = insert_trade_event(
        conn, event_time, trade_type, system_address, system_name, market_id, station_name,
        commodity, quantity, unit_price, total, primary_avg, known_cost, primary_profit, primary_profit_per_hour,
        covered_qty, journal_avg, journal_profit, journal_profit_per_unit, ledger_avg_buy,
        ledger_profit, ledger_profit_per_hour, method, supply_at_trade, demand_at_trade, consumed, entry,
    )
    return trade_id


def insert_trade_event(
    conn: sqlite3.Connection,
    event_time: str,
    event_type: str,
    system_address: Optional[int],
    system_name: Optional[str],
    market_id: Optional[int],
    station_name: Optional[str],
    commodity: str,
    quantity: int,
    unit_price: Optional[int],
    total_credits: Optional[int],
    avg_buy_price: Optional[float],
    known_cost: Optional[int],
    profit: Optional[int],
    profit_per_hour: Optional[float],
    covered_quantity: int,
    journal_avg_price_paid: Optional[float],
    journal_profit: Optional[int],
    journal_profit_per_unit: Optional[float],
    ledger_avg_buy_price: Optional[float],
    ledger_profit: Optional[int],
    ledger_profit_per_hour: Optional[float],
    cost_basis_method: Optional[str],
    supply_at_trade: Optional[int],
    demand_at_trade: Optional[int],
    lots: List[Dict[str, Any]],
    journal: Dict[str, Any],
) -> int:
    cur = conn.execute(
        """
        INSERT INTO trade_events(
            event_datetime, event_type, system_address, system_name, market_id, station_name,
            commodity, quantity, unit_price, total_credits, avg_buy_price, known_cost,
            profit, profit_per_hour, covered_quantity, journal_avg_price_paid, journal_profit,
            journal_profit_per_unit, ledger_avg_buy_price, ledger_profit, ledger_profit_per_hour,
            cost_basis_method, supply_at_trade, demand_at_trade, lots_json, journal_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_time, event_type, system_address, system_name, market_id, station_name,
            commodity, quantity, unit_price, total_credits, avg_buy_price, known_cost,
            profit, profit_per_hour, covered_quantity, journal_avg_price_paid, journal_profit,
            journal_profit_per_unit, ledger_avg_buy_price, ledger_profit, ledger_profit_per_hour,
            cost_basis_method, supply_at_trade, demand_at_trade, json.dumps(lots), json.dumps(journal, default=str),
        ),
    )
    return int(cur.lastrowid)


def lookup_market_quantities(conn: sqlite3.Connection, market_id: Optional[int], commodity: str) -> Tuple[Optional[int], Optional[int]]:
    """Return the latest known market supply/demand for this commodity at this station.

    This is a trade-time snapshot of what MarketScout currently knows. In normal
    ED gameplay this is usually the market state from the most recent market
    capture before the buy/sell event, not guaranteed to be after the trade.
    """
    if market_id is None or not commodity:
        return None, None
    try:
        row = conn.execute(
            """
            SELECT supply, demand
            FROM market_prices
            WHERE market_id=? AND commodity=?
            """,
            (market_id, commodity),
        ).fetchone()
        if not row:
            return None, None
        return first_int(row["supply"]), first_int(row["demand"])
    except Exception:
        return None, None


def consume_lifo_lots(conn: sqlite3.Connection, commodity: str, sell_qty: int, sell_time: str) -> Tuple[Optional[float], Optional[int], int, List[Dict[str, Any]]]:
    remaining = sell_qty
    known_cost = 0
    covered_qty = 0
    consumed: List[Dict[str, Any]] = []

    rows = conn.execute(
        """
        SELECT * FROM trade_lots
        WHERE commodity=? AND remaining_quantity > 0
        ORDER BY buy_datetime DESC, lot_id DESC
        """,
        (commodity,),
    ).fetchall()

    for row in rows:
        if remaining <= 0:
            break
        take = min(int(row["remaining_quantity"]), remaining)
        if take <= 0:
            continue
        unit_price = int(row["unit_price"])
        lot_cost = take * unit_price
        new_remaining = int(row["remaining_quantity"]) - take
        conn.execute(
            """
            UPDATE trade_lots
            SET remaining_quantity=?, closed_datetime=CASE WHEN ?=0 THEN ? ELSE closed_datetime END
            WHERE lot_id=?
            """,
            (new_remaining, new_remaining, sell_time, row["lot_id"]),
        )
        known_cost += lot_cost
        covered_qty += take
        remaining -= take
        consumed.append({
            "lot_id": row["lot_id"],
            "quantity": take,
            "unit_price": unit_price,
            "cost": lot_cost,
            "buy_datetime": row["buy_datetime"],
            "system_name": row["system_name"],
            "station_name": row["station_name"],
        })

    if covered_qty <= 0:
        return None, None, 0, []
    return known_cost / covered_qty, known_cost, covered_qty, consumed


def sale_cadence_profit_per_hour(conn: sqlite3.Connection, sell_time: str, sale_profit: Optional[int]) -> Optional[float]:
    """Estimate credits/hour from the elapsed time since the previous sell event.

    This intentionally uses the current sale's profit and the cadence between the
    current sell and the most recent previous sell. It is not based on cargo
    holding time. If no previous sell exists within SALES_CADENCE_WINDOW_MINUTES,
    return None.
    """
    if sale_profit is None:
        return None
    try:
        current_dt = parse_dt(sell_time)
    except Exception:
        return None

    try:
        rows = conn.execute(
            """
            SELECT event_datetime
            FROM trade_events
            WHERE event_type='sell' AND event_datetime < ?
            ORDER BY event_datetime DESC, trade_id DESC
            LIMIT 10
            """,
            (sell_time,),
        ).fetchall()
    except Exception:
        return None

    for row in rows:
        try:
            previous_dt = parse_dt(str(row["event_datetime"]))
            elapsed_seconds = (current_dt - previous_dt).total_seconds()
        except Exception:
            continue
        if elapsed_seconds <= 0:
            continue
        if elapsed_seconds <= SALES_CADENCE_WINDOW_MINUTES * 60:
            return float(sale_profit) * (3600.0 / elapsed_seconds)
        return None
    return None


def weighted_holding_hours(consumed: List[Dict[str, Any]], sell_time: str) -> Optional[float]:
    try:
        sell_dt = parse_dt(sell_time)
        total_qty = 0
        weighted = 0.0
        for item in consumed:
            qty = int(item.get("quantity") or 0)
            if qty <= 0:
                continue
            buy_dt = parse_dt(str(item.get("buy_datetime")))
            hours = max((sell_dt - buy_dt).total_seconds() / 3600.0, 0.0)
            total_qty += qty
            weighted += hours * qty
        if total_qty <= 0:
            return None
        return weighted / total_qty
    except Exception:
        return None


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_commodity_name(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("$") and s.endswith(";"):
        s = s[1:-1]
    if s.lower().endswith("_name"):
        s = s[:-5]
    if s.lower().startswith("commodity_"):
        s = s[len("commodity_"):]
    s = s.replace("_", " ").strip()
    # Keep common title casing, but don't destroy abbreviations too much.
    return " ".join(part.capitalize() for part in s.split())


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def first_text(*values: Any) -> Optional[str]:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return None


def first_float(*values: Any) -> Optional[float]:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except Exception:
            pass
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
