"""Local-only browser UI for EDMC-MarketScout.

This module starts a tiny HTTP server bound to 127.0.0.1. It serves the
bundled static web UI and read-only JSON API responses from the local SQLite
DB. It performs no external network requests and exposes no upload endpoints.
"""
from __future__ import annotations

import json
import mimetypes
import os
import socket
import sqlite3
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

_SERVER: Optional[ThreadingHTTPServer] = None
_THREAD: Optional[threading.Thread] = None
_PORT: Optional[int] = None
_CONTEXT: Dict[str, Any] = {}
_LATEST_JOURNAL_EVENT: Optional[Dict[str, Any]] = None
ECONOMY_PRESETS_FILE = "marketscout-economy-presets.json"
DEFAULT_ECONOMY_PRESETS = [
    "Agriculture",
    "Colony",
    "Extraction",
    "Extraction, Refinery",
    "High Tech",
    "Industrial",
    "Military",
    "Refinery",
    "Service",
    "Terraforming",
    "Tourism",
]


def start_server(plugin_dir: str, db_path: str, target_commodities: List[str], primary_metals: List[str]) -> int:
    """Start the local web server if needed and return its port."""
    global _SERVER, _THREAD, _PORT, _CONTEXT
    if _SERVER is not None and _PORT is not None:
        return _PORT

    _CONTEXT = {
        "plugin_dir": plugin_dir,
        "web_dir": os.path.join(plugin_dir, "web"),
        "db_path": db_path,
        "target_commodities": list(target_commodities),
        "primary_metals": list(primary_metals),
    }

    # Bind to port 0 so the OS chooses an available local-only port. This avoids
    # collisions and keeps the server private to this machine.
    server = ThreadingHTTPServer(("127.0.0.1", 0), MarketScoutRequestHandler)
    server.daemon_threads = True
    _PORT = int(server.server_address[1])
    _SERVER = server
    _THREAD = threading.Thread(target=server.serve_forever, name="MarketScoutWeb", daemon=True)
    _THREAD.start()
    return _PORT


def stop_server() -> None:
    global _SERVER, _THREAD, _PORT
    if _SERVER is not None:
        try:
            _SERVER.shutdown()
            _SERVER.server_close()
        except Exception:
            pass
    _SERVER = None
    _THREAD = None
    _PORT = None


def server_url() -> Optional[str]:
    if _PORT is None:
        return None
    return f"http://127.0.0.1:{_PORT}/"


def update_latest_journal_event(event: Dict[str, Any]) -> None:
    """Store the most recent Journal event metadata for the Web UI status strip.

    This intentionally stays in memory instead of writing to SQLite, so routine
    Journal traffic does not force table reloads or mutate the user database.
    """
    global _LATEST_JOURNAL_EVENT
    _LATEST_JOURNAL_EVENT = dict(event)


class MarketScoutRequestHandler(BaseHTTPRequestHandler):
    server_version = "MarketScoutHTTP/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep EDMC logs quiet unless an exception happens.
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib API name
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/status":
                return self.send_json(api_status())
            if path == "/api/stations":
                return self.send_json(api_stations(parse_qs(parsed.query)))
            if path == "/api/jackpots":
                return self.send_json(api_jackpots(parse_qs(parsed.query)))
            if path == "/api/ledger":
                return self.send_json(api_ledger(parse_qs(parsed.query)))
            if path == "/api/ledger/summary":
                return self.send_json(api_ledger_summary(parse_qs(parsed.query)))
            if path == "/api/options":
                return self.send_json(api_options())
            if path == "/api/economy-presets":
                return self.send_json(api_economy_presets())
            if path == "/api/commodities":
                return self.send_json(api_commodities())
            if path == "/api/settings":
                return self.send_json(api_settings())
            return self.serve_static(path)
        except Exception as exc:
            log_web_exception(exc)
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def do_POST(self) -> None:  # noqa: N802 - stdlib API name
        try:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body or "{}")
            if parsed.path == "/api/settings":
                return self.send_json(api_save_settings(payload))
            if parsed.path == "/api/economy-presets":
                return self.send_json(api_save_economy_preset(payload))
            self.send_error(404)
        except Exception as exc:
            log_web_exception(exc)
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def send_json(self, value: Any) -> None:
        body = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        # Prevent path traversal.
        rel = path.lstrip("/")
        if ".." in Path(rel).parts:
            self.send_error(403)
            return
        web_dir = Path(_CONTEXT["web_dir"])
        file_path = web_dir / rel
        if not file_path.is_file():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_CONTEXT["db_path"])
    conn.row_factory = sqlite3.Row
    return conn


def api_status() -> Dict[str, Any]:
    db_path = _CONTEXT.get("db_path")
    version = 0
    if db_path and os.path.exists(db_path):
        version = int(os.path.getmtime(db_path) * 1000)
    return {
        "ok": True,
        "data_version": version,
        "target_commodities": _CONTEXT.get("target_commodities", []),
        "primary_metals": _CONTEXT.get("primary_metals", []),
        "latest_journal_event": _LATEST_JOURNAL_EVENT,
    }


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def setting_get(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
    if row and row[0] is not None:
        try:
            return json.loads(row[0])
        except Exception:
            return default
    return default

def setting_set(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT INTO settings(key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
        (key, json.dumps(value, ensure_ascii=False)),
    )

def watched_commodities(conn: sqlite3.Connection) -> List[str]:
    val = setting_get(conn, "watched_commodities", _CONTEXT.get("primary_metals", ["Palladium", "Gold", "Silver"]))
    return [str(x) for x in val if str(x).strip()] if isinstance(val, list) else ["Palladium", "Gold", "Silver"]

def watched_columns(conn: sqlite3.Connection) -> List[Dict[str, str]]:
    default = [{"commodity": c, "side": "buy"} for c in watched_commodities(conn)]
    val = setting_get(conn, "watched_columns", default)
    out = []
    if isinstance(val, list):
        for item in val:
            if isinstance(item, dict) and item.get("commodity") and item.get("side") in ("buy", "sell"):
                out.append({"commodity": str(item["commodity"]), "side": str(item["side"])})
    return out or default

def api_commodities() -> Dict[str, Any]:
    """Return the selectable commodity catalog for the Web UI.

    commodity_global_stats is the authoritative list of commodities the user
    wants MarketScout to know about. It is populated from commodities.csv on
    startup. If the table is empty, fall back to commodities discovered in
    recorded market data so a fresh/legacy install is still usable.
    """
    with connect() as conn:
        stat_rows = conn.execute(
            "SELECT * FROM commodity_global_stats "
            "WHERE commodity IS NOT NULL AND commodity != '' ORDER BY commodity"
        ).fetchall()
        stats = {r["commodity"]: row_to_dict(r) for r in stat_rows}
        rows = [r["commodity"] for r in stat_rows]
        source = "commodity_global_stats"
        if not rows:
            rows = [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT commodity FROM market_prices "
                    "WHERE commodity IS NOT NULL AND commodity != '' ORDER BY commodity"
                ).fetchall()
            ]
            source = "market_prices_fallback"
    return {"commodities": rows, "stats": stats, "source": source}

def api_settings() -> Dict[str, Any]:
    with connect() as conn:
        return {"watched_commodities": watched_commodities(conn), "watched_columns": watched_columns(conn)}

def api_save_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    with connect() as conn:
        if "watched_commodities" in payload and isinstance(payload["watched_commodities"], list):
            setting_set(conn, "watched_commodities", [str(x) for x in payload["watched_commodities"] if str(x).strip()])
        if "watched_columns" in payload and isinstance(payload["watched_columns"], list):
            cols = []
            for item in payload["watched_columns"]:
                if isinstance(item, dict) and item.get("commodity") and item.get("side") in ("buy", "sell"):
                    cols.append({"commodity": str(item["commodity"]), "side": str(item["side"])})
            setting_set(conn, "watched_columns", cols)
        conn.commit()
    return {"ok": True}


def economy_presets_path() -> Path:
    return Path(_CONTEXT["plugin_dir"]) / ECONOMY_PRESETS_FILE


def normalize_economy_preset(value: Any) -> str:
    # Keep multi-economy presets readable while trimming accidental whitespace.
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return ", ".join(parts)


def sort_presets(values: List[str]) -> List[str]:
    return sorted(set(values), key=lambda item: item.casefold())


def read_economy_presets() -> List[str]:
    presets = [normalize_economy_preset(value) for value in DEFAULT_ECONOMY_PRESETS]
    path = economy_presets_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                values = data.get("presets", [])
            elif isinstance(data, list):
                values = data
            else:
                values = []
            presets.extend(normalize_economy_preset(value) for value in values)
        except Exception as exc:
            log_web_exception(exc)
    return sort_presets([preset for preset in presets if preset])


def write_economy_presets(presets: List[str]) -> None:
    path = economy_presets_path()
    payload = {
        "version": 1,
        "presets": sort_presets([normalize_economy_preset(value) for value in presets if normalize_economy_preset(value)]),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def api_economy_presets() -> Dict[str, Any]:
    return {"presets": read_economy_presets(), "source": ECONOMY_PRESETS_FILE}


def api_save_economy_preset(payload: Dict[str, Any]) -> Dict[str, Any]:
    preset = normalize_economy_preset(payload.get("preset"))
    if not preset:
        return {"ok": False, "error": "Empty preset", "presets": read_economy_presets()}
    presets = read_economy_presets()
    created = preset.casefold() not in {item.casefold() for item in presets}
    if created:
        presets.append(preset)
        write_economy_presets(presets)
    return {"ok": True, "created": created, "preset": preset, "presets": sort_presets(presets)}

def api_options() -> Dict[str, Any]:
    with connect() as conn:
        states = [r[0] for r in conn.execute("SELECT DISTINCT station_faction_state FROM stations WHERE station_faction_state IS NOT NULL AND station_faction_state != '' ORDER BY station_faction_state").fetchall()]
        sources = [r[0] for r in conn.execute("SELECT DISTINCT COALESCE(source, '') FROM stations WHERE source IS NOT NULL AND source != '' ORDER BY source").fetchall()]
    return {"states": states, "sources": sources}


def api_stations(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    with connect() as conn:
        display_cols = watched_columns(conn)
        watched = watched_commodities(conn)

    # Need all displayed commodities plus all stats commodities for Best Buy scoring.
    display_commodities = []
    for col in display_cols:
        if col["commodity"] not in display_commodities:
            display_commodities.append(col["commodity"])

    select_cols = [
        "st.market_id AS market_id",
        "s.system_name AS system",
        "st.station_name AS station",
        "st.station_type AS type",
        "COALESCE(st.largest_pad, 'Unknown') AS pad",
        "COALESCE(st.is_fleet_carrier, 0) AS is_fleet_carrier",
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
        # Best Buy score: (max_sell - current buy) * min(supply, 1000).
        "MAX(CASE WHEN cgs.max_sell IS NOT NULL AND mp.buy_price IS NOT NULL AND mp.buy_price > 0 "
        "THEN (cgs.max_sell - mp.buy_price) * CASE WHEN COALESCE(mp.supply, 0) > 1000 THEN 1000 ELSE COALESCE(mp.supply, 0) END END) AS best_buy_score",
    ]
    # Commodity that produced the max Best Buy score. Ties are not important for scouting.
    select_cols.append(
        "(SELECT mp2.commodity FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 "
        "ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>1000 THEN 1000 ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_commodity"
    )
    select_cols.append(
        "(SELECT mp2.buy_price FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 "
        "ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>1000 THEN 1000 ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_price"
    )
    select_cols.append(
        "(SELECT mp2.supply FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 "
        "ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>1000 THEN 1000 ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_supply"
    )
    for c in display_commodities:
        safe = c.replace("'", "''")
        select_cols.extend([
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.buy_price END) AS '{c}_buy'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.sell_price END) AS '{c}_sell'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.supply END) AS '{c}_supply'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.demand END) AS '{c}_demand'",
        ])
    sql = "SELECT " + ", ".join(select_cols) + " FROM stations st LEFT JOIN systems s ON s.system_address=st.system_address LEFT JOIN market_prices mp ON mp.market_id=st.market_id LEFT JOIN commodity_global_stats cgs ON cgs.commodity=mp.commodity"
    where: List[str] = []
    params: List[Any] = []

    def one(name: str) -> str:
        return (qs.get(name, [""])[0] or "").strip()

    system = one("system")
    station = one("station")
    state = one("state")
    economies = [x.strip() for x in one("economy").split(",") if x.strip()]
    source = one("source")
    include_fc = one("include_fc") in ("1", "true", "yes")

    if system:
        where.append("s.system_name LIKE ?")
        params.append(f"%{system}%")
    if station:
        where.append("st.station_name LIKE ?")
        params.append(f"%{station}%")
    if state:
        where.append("st.station_faction_state LIKE ?")
        params.append(f"%{state}%")
    if economies:
        parts = []
        for term in economies:
            parts.append("COALESCE(st.station_economies_json, st.station_economy, '') LIKE ?")
            params.append(f"%{term}%")
        where.append("(" + " OR ".join(parts) + ")")
    if source and source != "Any":
        if source == "imported":
            where.append("COALESCE(st.source, s.source, '') != 'local_visit'")
        else:
            where.append("COALESCE(st.source, s.source, '') = ?")
            params.append(source)
    if not include_fc:
        where.append("COALESCE(st.is_fleet_carrier, 0) = 0")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY st.market_id"
    sql += " ORDER BY market_updated IS NULL, market_updated DESC, station_visit IS NULL, station_visit DESC, best_buy_score IS NULL, best_buy_score DESC, system ASC, station ASC"
    limit = one("limit")
    try:
        lim = max(1, min(int(limit), 2000)) if limit else 1000
    except Exception:
        lim = 1000
    sql += f" LIMIT {lim}"

    with connect() as conn:
        raw_rows = [row_to_dict(r) for r in conn.execute(sql, params).fetchall()]

    # Defensive collapse: the main Stations view must show one current row per
    # physical station. Older imported/legacy rows or odd joins can otherwise
    # leak through as duplicates even when the stations table itself looks OK.
    def station_key(row):
        return (str(row.get("system") or "").strip().casefold(), str(row.get("station") or "").strip().casefold())

    def row_rank(row):
        # Prefer the freshest station row first, then higher best-buy score.
        # Timestamp strings are stored in ISO-like formats, so lexical ordering
        # matches chronological ordering for our data.
        return (
            str(row.get("market_updated") or ""),
            str(row.get("station_visit") or ""),
            float(row.get("best_buy_score") or -1),
            0 if row.get("source") == "local_visit" else -1,
        )

    deduped = {}
    for row in raw_rows:
        key = station_key(row)
        if not key[0] or not key[1]:
            key = ("__market_id__", str(row.get("market_id") or id(row)))
        prev = deduped.get(key)
        if prev is None or row_rank(row) > row_rank(prev):
            deduped[key] = row
    rows = list(deduped.values())

    # Keep the defensive post-dedupe ordering in sync with the SQL order:
    # newest market updates first, then newest station visits, then strongest
    # best-buy score, followed by stable alphabetical station identity.
    # Use stable sorts so each priority can use its natural direction.
    rows.sort(key=lambda r: (str(r.get("system") or "").casefold(), str(r.get("station") or "").casefold()))
    rows.sort(key=lambda r: float(r.get("best_buy_score") or -1), reverse=True)
    rows.sort(key=lambda r: str(r.get("station_visit") or ""), reverse=True)
    rows.sort(key=lambda r: str(r.get("market_updated") or ""), reverse=True)

    return {"rows": rows, "count": len(rows), "raw_count": len(raw_rows), "display_columns": display_cols, "watched_commodities": watched}



def api_jackpots(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def one(name: str) -> str:
        return (qs.get(name, [""])[0] or "").strip()
    try:
        lim = max(1, min(int(one("limit") or "500"), 2000))
    except Exception:
        lim = 500
    sql = """
        SELECT
            e.jackpot_id, e.market_id, e.detected_datetime, e.ended_datetime, e.active,
            e.trigger_commodities AS event_triggers, e.price_threshold, e.supply_threshold,
            e.system_name, e.station_name, e.largest_pad, e.system_economy,
            e.system_faction_state, e.station_economies_json, e.station_faction_state,
            e.population, e.security, e.source,
            sm.sample_datetime, sm.is_jackpot, sm.trigger_commodities AS sample_triggers,
            sm.palladium_buy, sm.palladium_supply,
            sm.gold_buy, sm.gold_supply,
            sm.silver_buy, sm.silver_supply
        FROM jackpot_samples sm
        JOIN jackpot_events e ON e.jackpot_id=sm.jackpot_id
        ORDER BY sm.sample_datetime DESC, sm.sample_id DESC
        LIMIT ?
    """
    with connect() as conn:
        try:
            rows = [row_to_dict(r) for r in conn.execute(sql, (lim,)).fetchall()]
        except sqlite3.OperationalError:
            rows = []
    return {"rows": rows, "count": len(rows)}


def api_ledger(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def one(name: str) -> str:
        return (qs.get(name, [""])[0] or "").strip()
    try:
        lim = max(1, min(int(one("limit") or "500"), 2000))
    except Exception:
        lim = 500
    commodity = one("commodity")
    event_type = one("event_type")
    system = one("system")
    station = one("station")
    where: List[str] = []
    params: List[Any] = []
    if commodity:
        where.append("commodity LIKE ?")
        params.append(f"%{commodity}%")
    if event_type and event_type != "Any":
        where.append("event_type = ?")
        params.append(event_type)
    if system:
        where.append("system_name LIKE ?")
        params.append(f"%{system}%")
    if station:
        where.append("station_name LIKE ?")
        params.append(f"%{station}%")
    sql = """
        SELECT trade_id, event_datetime, event_type, system_name, station_name,
               commodity, quantity, unit_price, total_credits, avg_buy_price,
               known_cost, profit, profit_per_hour, covered_quantity,
               journal_avg_price_paid, journal_profit, journal_profit_per_unit,
               ledger_avg_buy_price, ledger_profit, ledger_profit_per_hour,
               cost_basis_method, supply_at_trade, demand_at_trade, lots_json
        FROM trade_events
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY event_datetime DESC, trade_id DESC LIMIT ?"
    params.append(lim)
    with connect() as conn:
        try:
            rows = [row_to_dict(r) for r in conn.execute(sql, params).fetchall()]
            for row in rows:
                # Backward-compatible alias for older Web UI code; primary field is profit_per_hour.
                if "credits_per_hour" not in row:
                    row["credits_per_hour"] = row.get("profit_per_hour")
        except sqlite3.OperationalError:
            rows = []
    return {"rows": rows, "count": len(rows)}


def api_ledger_summary(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    with connect() as conn:
        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS trades,
                    SUM(CASE WHEN event_type='buy' THEN total_credits ELSE 0 END) AS total_spent,
                    SUM(CASE WHEN event_type='sell' THEN total_credits ELSE 0 END) AS total_sales,
                    SUM(CASE WHEN event_type='sell' THEN journal_profit ELSE 0 END) AS journal_profit,
                    SUM(CASE WHEN event_type='sell' THEN ledger_profit ELSE 0 END) AS ledger_profit,
                    SUM(CASE WHEN event_type='sell' THEN COALESCE(journal_profit, profit, ledger_profit, 0) ELSE 0 END) AS known_profit,
                    SUM(CASE WHEN event_type='sell' THEN covered_quantity ELSE 0 END) AS covered_sold_qty
                FROM trade_events
                """
            ).fetchone()
            open_lots = [row_to_dict(r) for r in conn.execute(
                """
                SELECT commodity, SUM(remaining_quantity) AS remaining_quantity,
                       SUM(remaining_quantity * unit_price) AS remaining_cost
                FROM trade_lots
                WHERE remaining_quantity > 0
                GROUP BY commodity
                ORDER BY commodity
                """
            ).fetchall()]
            summary = row_to_dict(row) if row else {}
        except sqlite3.OperationalError:
            summary = {}
            open_lots = []
    return {"summary": summary, "open_lots": open_lots}

def log_web_exception(exc: BaseException) -> None:
    try:
        path = os.path.join(_CONTEXT.get("plugin_dir") or os.getcwd(), "marketscout-web-error.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write("----- web exception -----\n")
            traceback.print_exc(file=f)
            f.write("\n")
    except Exception:
        pass
