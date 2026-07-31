"""Data access helpers for EDMC-MarketScout.

This module owns database reads/writes that are not inherently tied to EDMC or
HTTP request handling. Keep web responses and notifications in
`marketscout_web.py`; keep SQL and import persistence here.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def coerce_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").strip().split())


def contiguous_trip_progress_index(conn: sqlite3.Connection, route_id: int, current_index: int, baseline: str = "") -> int:
    next_index = current_index
    stop_rows = conn.execute(
        """
        SELECT
            trs.stop_index,
            COALESCE(trs.stop_skipped, 0) AS stop_skipped,
            EXISTS (
              SELECT 1
              FROM systems_visited s
              WHERE s.last_visit_datetime IS NOT NULL
                AND (
                  (trs.system_address IS NOT NULL AND s.system_address = trs.system_address)
                  OR lower(s.system_name) = lower(trs.system_name_snapshot)
                )
              )
            AS was_visited
        FROM trip_route_stops trs
        WHERE trs.route_id = ?
          AND trs.stop_index > ?
        ORDER BY trs.stop_index
        """,
        (route_id, current_index),
    ).fetchall()

    for row in stop_rows:
        if not int(row["stop_skipped"] or 0) and not int(row["was_visited"] or 0):
            break
        next_index = int(row["stop_index"])
    return next_index


def contiguous_trip_progress_index_from_stops(stops: List[Dict[str, Any]], current_index: int) -> int:
    next_index = max(0, current_index)
    for stop in sorted(stops, key=lambda row: coerce_int(row.get("stop_index")) or 0):
        stop_index = coerce_int(stop.get("stop_index"))
        if stop_index is None or stop_index <= next_index:
            continue
        visited = clean_text(stop.get("last_system_visit_datetime"))
        skipped = int(coerce_int(stop.get("stop_skipped")) or 0) == 1
        if not visited and not skipped:
            break
        next_index = stop_index
    return next_index


def advance_active_trip_progress(
    conn: sqlite3.Connection,
    system_name: Optional[str],
    system_address: Optional[int],
    visited_at: str,
) -> bool:
    """Advance the active trip route marker when all intervening stops were visited.

    The marker represents route progress, not simply the latest clicked/visited
    stop. It only moves forward if every stop after the existing marker and up
    to the newly visited stop has a recent system visit.
    """
    name = clean_text(system_name)
    address = coerce_int(system_address)
    if not name and address is None:
        return False

    active = conn.execute(
        """
        SELECT route_id, imported_datetime, progress_started_datetime, progress_stop_index, progress_updated_datetime
        FROM trip_routes
        WHERE active = 1
        ORDER BY imported_datetime DESC, route_id DESC
        LIMIT 1
        """
    ).fetchone()
    if not active:
        return False

    route_id = int(active["route_id"])
    current_index = coerce_int(active["progress_stop_index"]) or 0
    baseline = clean_text(active["progress_started_datetime"] or active["imported_datetime"])

    event_stop = conn.execute(
        """
        SELECT 1
        FROM trip_route_stops
        WHERE route_id = ?
          AND stop_index > ?
          AND (
            (? IS NOT NULL AND system_address = ?)
            OR (? != '' AND lower(system_name_snapshot) = lower(?))
          )
        LIMIT 1
        """,
        (route_id, current_index, address, address, name, name),
    ).fetchone()
    if not event_stop:
        return False

    next_index = contiguous_trip_progress_index(conn, route_id, current_index, baseline)

    if next_index <= current_index:
        return False

    conn.execute(
        """
        UPDATE trip_routes
        SET progress_stop_index = ?,
            progress_updated_datetime = ?
        WHERE route_id = ?
        """,
        (next_index, clean_text(visited_at), route_id),
    )
    return True


def parse_spansh_tourist_route(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    raw_content = payload.get("content")
    if isinstance(raw_content, str):
        data = json.loads(raw_content)
    elif isinstance(payload.get("route"), dict):
        data = payload["route"]
    elif isinstance(payload.get("json"), dict):
        data = payload["json"]
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("Expected a Spansh Tourist Route JSON object")

    parameters = data.get("parameters") if isinstance(data.get("parameters"), dict) else {}
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    system_jumps = result.get("system_jumps")
    if not isinstance(system_jumps, list) or not system_jumps:
        raise ValueError("This does not look like a Spansh Tourist Route JSON file: missing result.system_jumps")

    source_system = clean_text(result.get("source_system") or parameters.get("source"))
    final_destination_system = clean_text(result.get("final_destination_system") or parameters.get("final_destination"))
    route_name = clean_text(payload.get("name"))
    if not route_name:
        if source_system and final_destination_system:
            route_name = f"{source_system} Tourist Loop" if source_system.casefold() == final_destination_system.casefold() else f"{source_system} to {final_destination_system}"
        else:
            route_name = clean_text(payload.get("filename")) or "Spansh Tourist Route"

    route = {
        "route_name": route_name,
        "source": "spansh_tourist_route",
        "spansh_job_id": clean_text(result.get("job") or data.get("job")),
        "spansh_search_id": clean_text(result.get("search") or parameters.get("guid")),
        "source_system": source_system,
        "final_destination_system": final_destination_system,
        "jump_range_ly": coerce_float(result.get("range") or parameters.get("range")),
        "loop_route": 1 if int(coerce_int(parameters.get("loop")) or 0) else 0,
    }

    stops: List[Dict[str, Any]] = []
    for index, item in enumerate(system_jumps):
        if not isinstance(item, dict):
            continue
        system_name = clean_text(item.get("system"))
        system_address = coerce_int(item.get("id64"))
        x = coerce_float(item.get("x"))
        y = coerce_float(item.get("y"))
        z = coerce_float(item.get("z"))
        if not system_name or system_address is None or x is None or y is None or z is None:
            continue
        stops.append(
            {
                "stop_index": index,
                "system_address": system_address,
                "system_name": system_name,
                "leg_distance_ly": coerce_float(item.get("distance")),
                "jumps": coerce_int(item.get("jumps")),
                "x": x,
                "y": y,
                "z": z,
            }
        )

    if not stops:
        raise ValueError("The Spansh Tourist Route did not contain any usable route stops")
    return route, stops


def csv_get(row: Dict[str, Any], *names: str) -> str:
    lower = {str(key or "").strip().casefold(): key for key in row.keys()}
    for name in names:
        key = lower.get(name.strip().casefold())
        if key is not None:
            return clean_text(row.get(key))
    return ""


def station_hint_score(hint: Dict[str, Any]) -> Tuple[int, int, float, str]:
    has_market = 1 if hint.get("has_market") else 0
    large_pads = coerce_int(hint.get("large_pads")) or 0
    distance = coerce_float(hint.get("distance_to_arrival_ls"))
    return (has_market, 1 if large_pads > 0 else 0, -(distance if distance is not None else 10**12), clean_text(hint.get("station_name")).casefold())


def parse_spansh_station_hints(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw_content = payload.get("content")
    if not isinstance(raw_content, str) or not raw_content.strip():
        raise ValueError("Expected a Spansh CSV file")

    reader = csv.DictReader(io.StringIO(raw_content))
    headers = {str(header or "").strip().casefold() for header in (reader.fieldnames or [])}
    if not headers:
        raise ValueError("The station hints CSV has no header row")

    candidates: Dict[str, List[Dict[str, Any]]] = {}
    for row in reader:
        if "system name" in headers:
            system_name = csv_get(row, "System Name")
            station_name = csv_get(row, "Name", "Station Name")
            if not system_name or not station_name:
                continue
            candidates.setdefault(system_name.casefold(), []).append(
                {
                    "system_name": system_name,
                    "station_name": station_name,
                    "station_type": csv_get(row, "Type", "Station Type"),
                    "distance_to_arrival_ls": coerce_float(csv_get(row, "Distance to Arrival (LS)", "Distance to Arrival")),
                    "large_pads": coerce_int(csv_get(row, "Large Pads")),
                    "market_id": coerce_int(csv_get(row, "Market ID", "Market Id")),
                    "has_market": True,
                }
            )
            continue

        if "stations" in headers:
            system_name = csv_get(row, "Name", "System")
            stations_raw = csv_get(row, "Stations")
            if not system_name or not stations_raw:
                continue
            try:
                stations = json.loads(stations_raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(stations, list):
                continue
            for station in stations:
                if not isinstance(station, dict):
                    continue
                station_name = clean_text(station.get("name"))
                if not station_name:
                    continue
                candidates.setdefault(system_name.casefold(), []).append(
                    {
                        "system_name": system_name,
                        "station_name": station_name,
                        "station_type": clean_text(station.get("type")),
                        "distance_to_arrival_ls": coerce_float(station.get("distance_to_arrival")),
                        "large_pads": coerce_int(station.get("large_pads")),
                        "market_id": coerce_int(station.get("market_id")),
                        "has_market": bool(station.get("has_market")),
                    }
                )

    hints: Dict[str, Dict[str, Any]] = {}
    for system_key, rows in candidates.items():
        if rows:
            hints[system_key] = sorted(rows, key=station_hint_score, reverse=True)[0]

    if not hints:
        raise ValueError("No station hints were found. Use a Spansh Stations Search CSV or a Systems Search CSV with a Stations column.")
    return hints


def upsert_route_stop_system_data(
    conn: sqlite3.Connection,
    stop: Dict[str, Any],
    imported_at: str,
    source: str = "spansh_tourist_route",
) -> None:
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
        (
            stop["system_address"],
            stop["system_name"],
            stop["x"],
            stop["y"],
            stop["z"],
            source,
            imported_at,
        ),
    )


def trip_route_rows(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            tr.route_id,
            tr.route_name,
            tr.source,
            tr.spansh_job_id,
            tr.spansh_search_id,
            tr.source_system,
            tr.final_destination_system,
            tr.jump_range_ly,
            tr.loop_route,
            tr.imported_datetime,
            tr.active,
            COALESCE(tr.progress_stop_index, 0) AS progress_stop_index,
            tr.progress_updated_datetime,
            COUNT(trs.stop_index) AS stop_count,
            COALESCE(SUM(trs.jumps), 0) AS total_jumps,
            COALESCE(SUM(trs.leg_distance_ly), 0) AS total_distance_ly
        FROM trip_routes tr
        LEFT JOIN trip_route_stops trs ON trs.route_id = tr.route_id
        GROUP BY tr.route_id
        ORDER BY tr.active DESC, tr.imported_datetime DESC, tr.route_id DESC
        """
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def trip_route_stop_rows(conn: sqlite3.Connection, route_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            trs.route_id,
            trs.stop_index,
            trs.system_address,
            trs.system_name_snapshot AS system_name,
            trs.leg_distance_ly,
            trs.jumps,
            trs.x,
            trs.y,
            trs.z,
            trs.station_hint_name,
            trs.station_hint_type,
            trs.station_hint_distance_to_arrival_ls,
            trs.station_hint_large_pads,
            trs.station_hint_market_id,
            COALESCE(trs.stop_skipped, 0) AS stop_skipped,
            trs.stop_skipped_datetime,
            s.last_visit_datetime AS last_system_visit_datetime,
            (
                SELECT st.station_name
                FROM stations st
                LEFT JOIN systems_visited ss ON ss.system_address = st.system_address
                WHERE st.last_station_visit_datetime IS NOT NULL
                  AND (
                    st.system_address = trs.system_address
                    OR lower(ss.system_name) = lower(trs.system_name_snapshot)
                  )
                ORDER BY st.last_station_visit_datetime DESC
                LIMIT 1
            ) AS last_station_name,
            (
                SELECT st.last_station_visit_datetime
                FROM stations st
                LEFT JOIN systems_visited ss ON ss.system_address = st.system_address
                WHERE st.last_station_visit_datetime IS NOT NULL
                  AND (
                    st.system_address = trs.system_address
                    OR lower(ss.system_name) = lower(trs.system_name_snapshot)
                  )
                ORDER BY st.last_station_visit_datetime DESC
                LIMIT 1
            ) AS last_station_visit_datetime
        FROM trip_route_stops trs
        LEFT JOIN systems_visited s ON s.system_address = trs.system_address
        WHERE trs.route_id = ?
        ORDER BY trs.stop_index
        """,
        (route_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def active_trip_route(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT route_id
        FROM trip_routes
        WHERE active = 1
        ORDER BY imported_datetime DESC, route_id DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    route_id = int(row["route_id"])
    routes = [route for route in trip_route_rows(conn) if int(route["route_id"]) == route_id]
    if not routes:
        return None
    route = routes[0]
    route["stops"] = trip_route_stop_rows(conn, route_id)
    stored_progress_index = coerce_int(route.get("progress_stop_index")) or 0
    route["progress_stop_index"] = contiguous_trip_progress_index_from_stops(route["stops"], stored_progress_index)
    return route


def trip_routes_response(conn: sqlite3.Connection) -> Dict[str, Any]:
    try:
        routes = trip_route_rows(conn)
        active = active_trip_route(conn)
    except sqlite3.OperationalError:
        routes = []
        active = None
    return {"ok": True, "routes": routes, "active_route": active}


def import_trip_route(conn: sqlite3.Connection, payload: Dict[str, Any], imported_at: str) -> Dict[str, Any]:
    route, stops = parse_spansh_tourist_route(payload)
    conn.execute("UPDATE trip_routes SET active=0")
    cur = conn.execute(
        """
        INSERT INTO trip_routes(
            route_name, source, spansh_job_id, spansh_search_id, source_system,
            final_destination_system, jump_range_ly, loop_route, imported_datetime,
            progress_started_datetime, progress_stop_index, progress_updated_datetime, active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 1)
        """,
        (
            route["route_name"],
            route["source"],
            route["spansh_job_id"],
            route["spansh_search_id"],
            route["source_system"],
            route["final_destination_system"],
            route["jump_range_ly"],
            route["loop_route"],
            imported_at,
            imported_at,
            imported_at,
        ),
    )
    route_id = int(cur.lastrowid)
    for stop in stops:
        upsert_route_stop_system_data(conn, stop, imported_at)
        conn.execute(
            """
            INSERT INTO trip_route_stops(
                route_id, stop_index, system_address, system_name_snapshot,
                leg_distance_ly, jumps, x, y, z
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route_id,
                stop["stop_index"],
                stop["system_address"],
                stop["system_name"],
                stop["leg_distance_ly"],
                stop["jumps"],
                stop["x"],
                stop["y"],
                stop["z"],
            ),
        )
    conn.commit()
    return {"ok": True, "route_id": route_id, "imported_stops": len(stops), "active_route": active_trip_route(conn)}


def import_trip_route_station_hints(conn: sqlite3.Connection, payload: Dict[str, Any], imported_at: str) -> Dict[str, Any]:
    hints = parse_spansh_station_hints(payload)
    route_id = coerce_int(payload.get("route_id"))
    if route_id is None:
        active_row = conn.execute(
            """
            SELECT route_id
            FROM trip_routes
            WHERE active = 1
            ORDER BY imported_datetime DESC, route_id DESC
            LIMIT 1
            """
        ).fetchone()
        if not active_row:
            return {"ok": False, "error": "Import a Tourist Route first, then add station hints to the active route."}
        route_id = int(active_row["route_id"])
    else:
        exists = conn.execute("SELECT 1 FROM trip_routes WHERE route_id=?", (route_id,)).fetchone()
        if not exists:
            return {"ok": False, "error": "Route not found"}

    updated = 0
    for hint in hints.values():
        cur = conn.execute(
            """
            UPDATE trip_route_stops
            SET station_hint_name=?,
                station_hint_type=?,
                station_hint_distance_to_arrival_ls=?,
                station_hint_large_pads=?,
                station_hint_market_id=?
            WHERE route_id=?
              AND lower(system_name_snapshot)=lower(?)
            """,
            (
                hint["station_name"],
                hint.get("station_type") or None,
                hint.get("distance_to_arrival_ls"),
                hint.get("large_pads"),
                hint.get("market_id"),
                route_id,
                hint["system_name"],
            ),
        )
        updated += int(cur.rowcount or 0)
    conn.commit()
    return {
        "ok": True,
        "route_id": route_id,
        "matched_stops": updated,
        "hinted_systems": len(hints),
        "imported_datetime": imported_at,
        "routes": trip_route_rows(conn),
        "active_route": active_trip_route(conn),
    }


def start_trip_route(conn: sqlite3.Connection, payload: Dict[str, Any], started_at: str) -> Dict[str, Any]:
    route_id = coerce_int(payload.get("route_id"))
    if route_id is None:
        return {"ok": False, "error": "Missing route_id"}
    exists = conn.execute("SELECT 1 FROM trip_routes WHERE route_id=?", (route_id,)).fetchone()
    if not exists:
        return {"ok": False, "error": "Route not found"}
    conn.execute("UPDATE trip_routes SET active=0")
    conn.execute(
        """
        UPDATE trip_routes
        SET active=1,
            progress_started_datetime=?,
            progress_stop_index=0,
            progress_updated_datetime=?
        WHERE route_id=?
        """,
        (clean_text(started_at), clean_text(started_at), route_id),
    )
    conn.commit()
    return {"ok": True, "routes": trip_route_rows(conn), "active_route": active_trip_route(conn)}


def set_trip_route_stop_skipped(conn: sqlite3.Connection, payload: Dict[str, Any], updated_at: str) -> Dict[str, Any]:
    route_id = coerce_int(payload.get("route_id"))
    stop_index = coerce_int(payload.get("stop_index"))
    skipped = bool(payload.get("skipped"))
    if route_id is None or stop_index is None:
        return {"ok": False, "error": "Missing route_id or stop_index"}

    route = conn.execute(
        """
        SELECT route_id, active, imported_datetime, progress_started_datetime, progress_stop_index, progress_updated_datetime
        FROM trip_routes
        WHERE route_id = ?
        """,
        (route_id,),
    ).fetchone()
    if not route:
        return {"ok": False, "error": "Route not found"}

    exists = conn.execute(
        "SELECT 1 FROM trip_route_stops WHERE route_id=? AND stop_index=?",
        (route_id, stop_index),
    ).fetchone()
    if not exists:
        return {"ok": False, "error": "Route stop not found"}

    conn.execute(
        """
        UPDATE trip_route_stops
        SET stop_skipped = ?,
            stop_skipped_datetime = ?
        WHERE route_id = ?
          AND stop_index = ?
        """,
        (1 if skipped else 0, clean_text(updated_at) if skipped else None, route_id, stop_index),
    )

    current_index = coerce_int(route["progress_stop_index"]) or 0
    baseline = clean_text(route["progress_started_datetime"] or route["imported_datetime"])
    if skipped:
        next_index = contiguous_trip_progress_index(conn, route_id, current_index, baseline)
        if next_index > current_index:
            conn.execute(
                """
                UPDATE trip_routes
                SET progress_stop_index = ?,
                    progress_updated_datetime = ?
                WHERE route_id = ?
                """,
                (next_index, clean_text(updated_at), route_id),
            )
    elif stop_index <= current_index:
        conn.execute(
            """
            UPDATE trip_routes
            SET progress_stop_index = ?,
                progress_updated_datetime = ?
            WHERE route_id = ?
            """,
            (max(0, stop_index - 1), clean_text(updated_at), route_id),
        )

    conn.commit()
    return {"ok": True, "routes": trip_route_rows(conn), "active_route": active_trip_route(conn)}


def delete_trip_route(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    route_id = coerce_int(payload.get("route_id"))
    if route_id is None:
        return {"ok": False, "error": "Missing route_id"}
    was_active = conn.execute("SELECT active FROM trip_routes WHERE route_id=?", (route_id,)).fetchone()
    conn.execute("DELETE FROM trip_route_stops WHERE route_id=?", (route_id,))
    conn.execute("DELETE FROM trip_routes WHERE route_id=?", (route_id,))
    if was_active and int(was_active["active"] or 0):
        next_route = conn.execute(
            """
            SELECT route_id
            FROM trip_routes
            ORDER BY imported_datetime DESC, route_id DESC
            LIMIT 1
            """
        ).fetchone()
        if next_route:
            conn.execute("UPDATE trip_routes SET active=1 WHERE route_id=?", (int(next_route["route_id"]),))
    conn.commit()
    return {"ok": True, "routes": trip_route_rows(conn), "active_route": active_trip_route(conn)}


def coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    text = clean_text(value).casefold()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return None


def carrier_route_name(filename: str, stops: List[Dict[str, Any]]) -> str:
    desired = [stop["system_name"] for stop in stops if stop.get("is_desired_destination")]
    if desired:
        first_name = stops[0]["system_name"] if stops else "Fleet Carrier"
        final_name = desired[-1]
        if first_name.casefold() != final_name.casefold():
            return f"{first_name} to {final_name}"
        return f"Fleet Carrier route to {final_name}"
    stem = clean_text(filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0])
    return stem.replace("_", " ") or "Fleet Carrier Route"


def parse_spansh_carrier_route(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normalize one Spansh Fleet Carrier CSV or JSON export.

    The JSON export contains richer metadata and per-stop coordinates. The CSV
    export is intentionally accepted as a reduced representation. Both formats
    produce the same ordered stop model; duplicate system names are retained.
    """
    raw_content = payload.get("content")
    if not isinstance(raw_content, str) or not raw_content.strip():
        raise ValueError("Choose one Spansh Fleet Carrier CSV or JSON file")
    if isinstance(payload.get("files"), list) or isinstance(raw_content, (list, tuple)):
        raise ValueError("Import one Spansh Fleet Carrier file at a time")

    filename = clean_text(payload.get("filename"))
    content = raw_content.lstrip("\ufeff \t\r\n")
    is_json = filename.casefold().endswith(".json") or content.startswith("{")
    if filename.casefold().endswith(".csv") and content.startswith("{"):
        raise ValueError("The selected file is JSON content but has a CSV filename")

    metadata: Dict[str, Any] = {
        "model_version": 1,
        "source": "spansh_carrier_json" if is_json else "spansh_carrier_csv",
        "source_filename": filename or None,
        "source_job_id": None,
        "source_system_name": None,
        "source_system_address": None,
        "destination_systems": [],
        "carrier_mass": None,
        "carrier_capacity": None,
        "capacity_used": None,
        "starting_fuel_t": None,
        "starting_tritium_t": None,
    }
    stops: List[Dict[str, Any]] = []

    if is_json:
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse the Spansh Fleet Carrier JSON: {exc.msg}") from exc
        if not isinstance(data, dict):
            raise ValueError("Expected a Spansh Fleet Carrier JSON object")
        parameters = data.get("parameters") if isinstance(data.get("parameters"), dict) else {}
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        raw_stops = result.get("jumps")
        if not isinstance(raw_stops, list) or not raw_stops:
            raise ValueError("This does not look like a Spansh Fleet Carrier route: missing result.jumps")

        metadata.update(
            {
                "source_job_id": clean_text(data.get("job") or result.get("job")) or None,
                "carrier_mass": coerce_float(parameters.get("mass") or result.get("mass")),
                "carrier_capacity": coerce_float(parameters.get("capacity") or result.get("capacity")),
                "capacity_used": coerce_float(parameters.get("capacity_used") or result.get("capacity_used")),
                "starting_fuel_t": coerce_float(parameters.get("current_fuel")),
                "starting_tritium_t": coerce_float(
                    parameters.get("tritium_amount")
                    if parameters.get("tritium_amount") is not None
                    else result.get("tritium_stored")
                ),
            }
        )
        destination_ids = parameters.get("destination_systems") or result.get("destinations") or []
        if isinstance(destination_ids, (str, int)):
            destination_ids = [destination_ids]
        destination_id_set = {coerce_int(value) for value in destination_ids}
        destination_id_set.discard(None)

        for index, item in enumerate(raw_stops):
            if not isinstance(item, dict):
                continue
            system_name = clean_text(item.get("name") or item.get("system"))
            if not system_name:
                continue
            system_address = coerce_int(item.get("id64") or item.get("system_address"))
            desired = coerce_bool(item.get("is_desired_destination")) is True or system_address in destination_id_set
            stops.append(
                {
                    "stop_index": index,
                    "system_address": system_address,
                    "system_name": system_name,
                    "body_name": clean_text(item.get("body")) or None,
                    "leg_distance_ly": coerce_float(item.get("distance")),
                    "distance_remaining_ly": coerce_float(item.get("distance_to_destination")),
                    "tritium_in_tank_t": coerce_float(item.get("fuel_in_tank")),
                    "tritium_in_market_t": coerce_float(item.get("tritium_in_market")),
                    "tritium_used_t": coerce_float(item.get("fuel_used")),
                    "restock_amount_t": coerce_float(item.get("restock_amount")),
                    "has_icy_ring": coerce_bool(item.get("has_icy_ring")),
                    "is_system_pristine": coerce_bool(item.get("is_system_pristine")),
                    "must_restock": coerce_bool(item.get("must_restock")),
                    "is_desired_destination": desired,
                    "x": coerce_float(item.get("x")),
                    "y": coerce_float(item.get("y")),
                    "z": coerce_float(item.get("z")),
                    "source_row": item,
                }
            )
        if not stops:
            raise ValueError("The Spansh Fleet Carrier JSON did not contain usable route stops")
    else:
        reader = csv.DictReader(io.StringIO(raw_content))
        headers = {str(header or "").strip().casefold() for header in (reader.fieldnames or [])}
        if "system name" not in headers:
            raise ValueError("This does not look like a Spansh Fleet Carrier CSV: missing System Name")
        for index, row in enumerate(reader):
            system_name = csv_get(row, "System Name", "Name", "System")
            if not system_name:
                continue
            stops.append(
                {
                    "stop_index": index,
                    "system_address": None,
                    "system_name": system_name,
                    "body_name": None,
                    "leg_distance_ly": coerce_float(csv_get(row, "Distance", "Distance (LY)")),
                    "distance_remaining_ly": coerce_float(csv_get(row, "Distance Remaining")),
                    "tritium_in_tank_t": coerce_float(csv_get(row, "Tritium in tank", "Tritium in Tank")),
                    "tritium_in_market_t": coerce_float(csv_get(row, "Tritium in market", "Tritium in Market")),
                    "tritium_used_t": coerce_float(csv_get(row, "Fuel Used", "Tritium Used")),
                    "restock_amount_t": None,
                    "has_icy_ring": coerce_bool(csv_get(row, "Icy Ring")),
                    "is_system_pristine": coerce_bool(csv_get(row, "Pristine")),
                    "must_restock": coerce_bool(csv_get(row, "Restock Tritium")),
                    "is_desired_destination": False,
                    "x": None,
                    "y": None,
                    "z": None,
                    "source_row": dict(row),
                }
            )
        if not stops:
            raise ValueError("The Spansh Fleet Carrier CSV did not contain usable route stops")
        stops[-1]["is_desired_destination"] = True

    metadata["source_system_name"] = stops[0]["system_name"]
    metadata["source_system_address"] = stops[0].get("system_address")
    destinations: List[Dict[str, Any]] = []
    seen_destinations = set()
    for stop in stops:
        if not stop.get("is_desired_destination"):
            continue
        if len(stops) > 1 and stop["stop_index"] == 0:
            continue
        key = (stop.get("system_address"), stop["system_name"].casefold())
        if key in seen_destinations:
            continue
        seen_destinations.add(key)
        destinations.append(
            {
                "system_address": stop.get("system_address"),
                "system_name": stop["system_name"],
            }
        )
    metadata["destination_systems"] = destinations
    metadata["route_name"] = clean_text(payload.get("name")) or carrier_route_name(filename, stops)
    metadata["total_distance_ly"] = sum(
        coerce_float(stop.get("leg_distance_ly")) or 0.0 for stop in stops
    )
    metadata["total_tritium_t"] = sum(
        coerce_float(stop.get("tritium_used_t")) or 0.0 for stop in stops
    )
    return metadata, stops


def _carrier_trip_route_with_destinations(row: sqlite3.Row) -> Dict[str, Any]:
    route = row_to_dict(row)
    route["model_version"] = 1
    try:
        route["destination_systems"] = json.loads(route.pop("destination_systems_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        route["destination_systems"] = []
    return route


def carrier_trip_route_rows(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            ctr.carrier_trip_id,
            ctr.route_name,
            ctr.source,
            ctr.source_filename,
            ctr.source_sha256,
            ctr.source_job_id,
            ctr.source_system_name,
            ctr.source_system_address,
            ctr.destination_systems_json,
            ctr.carrier_mass,
            ctr.carrier_capacity,
            ctr.capacity_used,
            ctr.starting_fuel_t,
            ctr.starting_tritium_t,
            ctr.total_distance_ly,
            ctr.total_tritium_t,
            ctr.imported_datetime,
            ctr.active,
            COALESCE(ctr.progress_stop_index, 0) AS progress_stop_index,
            ctr.progress_started_datetime,
            ctr.progress_updated_datetime,
            COUNT(cts.stop_index) AS stop_count
        FROM carrier_trip_routes ctr
        LEFT JOIN carrier_trip_stops cts ON cts.carrier_trip_id = ctr.carrier_trip_id
        GROUP BY ctr.carrier_trip_id
        ORDER BY ctr.active DESC, ctr.imported_datetime DESC, ctr.carrier_trip_id DESC
        """
    ).fetchall()
    return [_carrier_trip_route_with_destinations(row) for row in rows]


def carrier_trip_stop_rows(conn: sqlite3.Connection, carrier_trip_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            cts.carrier_trip_id,
            cts.stop_index,
            cts.system_address,
            cts.system_name_snapshot AS system_name,
            cts.body_name,
            cts.leg_distance_ly,
            cts.distance_remaining_ly,
            cts.tritium_in_tank_t,
            cts.tritium_in_market_t,
            cts.tritium_used_t,
            cts.restock_amount_t,
            cts.has_icy_ring,
            cts.is_system_pristine,
            cts.must_restock,
            cts.is_desired_destination,
            cts.x,
            cts.y,
            cts.z,
            COALESCE(cts.stop_skipped, 0) AS stop_skipped,
            cts.stop_skipped_datetime,
            (
                SELECT MAX(sv.last_visit_datetime)
                FROM systems_visited sv
                WHERE (cts.system_address IS NOT NULL AND sv.system_address = cts.system_address)
                   OR lower(sv.system_name) = lower(cts.system_name_snapshot)
            ) AS last_system_visit_datetime
        FROM carrier_trip_stops cts
        WHERE cts.carrier_trip_id = ?
        ORDER BY cts.stop_index
        """,
        (carrier_trip_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def contiguous_carrier_trip_progress_index(
    conn: sqlite3.Connection,
    carrier_trip_id: int,
    current_index: int,
) -> int:
    next_index = max(0, current_index)
    rows = conn.execute(
        """
        SELECT
            cts.stop_index,
            COALESCE(cts.stop_skipped, 0) AS stop_skipped,
            EXISTS (
                SELECT 1
                FROM systems_visited sv
                WHERE sv.last_visit_datetime IS NOT NULL
                  AND (
                      (cts.system_address IS NOT NULL AND sv.system_address = cts.system_address)
                      OR lower(sv.system_name) = lower(cts.system_name_snapshot)
                  )
            ) AS was_visited
        FROM carrier_trip_stops cts
        WHERE cts.carrier_trip_id = ?
          AND cts.stop_index > ?
        ORDER BY cts.stop_index
        """,
        (carrier_trip_id, current_index),
    ).fetchall()
    for row in rows:
        if not int(row["stop_skipped"] or 0) and not int(row["was_visited"] or 0):
            break
        next_index = int(row["stop_index"])
    return next_index


def _carrier_trip_full_route(
    conn: sqlite3.Connection,
    route: Dict[str, Any],
) -> Dict[str, Any]:
    carrier_trip_id = int(route["carrier_trip_id"])
    route["stops"] = carrier_trip_stop_rows(conn, carrier_trip_id)
    route["progress_stop_index"] = contiguous_carrier_trip_progress_index(
        conn,
        carrier_trip_id,
        coerce_int(route.get("progress_stop_index")) or 0,
    )
    return route


def active_carrier_trips(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    routes_by_id = {
        int(route["carrier_trip_id"]): route
        for route in carrier_trip_route_rows(conn)
    }
    active_ids = conn.execute(
        """
        SELECT carrier_trip_id
        FROM carrier_trip_routes
        WHERE active = 1
        ORDER BY imported_datetime ASC, carrier_trip_id ASC
        """
    ).fetchall()
    return [
        _carrier_trip_full_route(conn, routes_by_id[int(row["carrier_trip_id"])])
        for row in active_ids
        if int(row["carrier_trip_id"]) in routes_by_id
    ]


def active_carrier_trip(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    active_routes = active_carrier_trips(conn)
    return active_routes[0] if active_routes else None


def carrier_trip_routes_response(conn: sqlite3.Connection) -> Dict[str, Any]:
    try:
        routes = carrier_trip_route_rows(conn)
        active_routes = active_carrier_trips(conn)
    except sqlite3.OperationalError:
        routes = []
        active_routes = []
    return {
        "ok": True,
        "routes": routes,
        "active_routes": active_routes,
        "active_route": active_routes[0] if active_routes else None,
    }


def import_carrier_trip(conn: sqlite3.Connection, payload: Dict[str, Any], imported_at: str) -> Dict[str, Any]:
    route, stops = parse_spansh_carrier_route(payload)
    source_content = str(payload.get("content") or "")
    source_sha256 = hashlib.sha256(source_content.encode("utf-8")).hexdigest()
    cur = conn.execute(
        """
        INSERT INTO carrier_trip_routes(
            route_name, source, source_filename, source_sha256, source_job_id,
            source_system_name, source_system_address, destination_systems_json,
            carrier_mass, carrier_capacity, capacity_used, starting_fuel_t,
            starting_tritium_t, total_distance_ly, total_tritium_t, imported_datetime,
            active, progress_started_datetime, progress_stop_index, progress_updated_datetime
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0, ?)
        """,
        (
            route["route_name"],
            route["source"],
            route["source_filename"],
            source_sha256,
            route["source_job_id"],
            route["source_system_name"],
            route["source_system_address"],
            json.dumps(route["destination_systems"], separators=(",", ":")),
            route["carrier_mass"],
            route["carrier_capacity"],
            route["capacity_used"],
            route["starting_fuel_t"],
            route["starting_tritium_t"],
            route["total_distance_ly"],
            route["total_tritium_t"],
            imported_at,
            imported_at,
            imported_at,
        ),
    )
    carrier_trip_id = int(cur.lastrowid)
    for stop in stops:
        if stop.get("system_address") is not None and all(stop.get(axis) is not None for axis in ("x", "y", "z")):
            upsert_route_stop_system_data(conn, stop, imported_at, source="spansh_carrier_route")
        conn.execute(
            """
            INSERT INTO carrier_trip_stops(
                carrier_trip_id, stop_index, system_address, system_name_snapshot,
                body_name, leg_distance_ly, distance_remaining_ly, tritium_in_tank_t,
                tritium_in_market_t, tritium_used_t, restock_amount_t, has_icy_ring,
                is_system_pristine, must_restock, is_desired_destination, x, y, z,
                source_row_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                carrier_trip_id,
                stop["stop_index"],
                stop["system_address"],
                stop["system_name"],
                stop["body_name"],
                stop["leg_distance_ly"],
                stop["distance_remaining_ly"],
                stop["tritium_in_tank_t"],
                stop["tritium_in_market_t"],
                stop["tritium_used_t"],
                stop["restock_amount_t"],
                None if stop["has_icy_ring"] is None else int(stop["has_icy_ring"]),
                None if stop["is_system_pristine"] is None else int(stop["is_system_pristine"]),
                None if stop["must_restock"] is None else int(stop["must_restock"]),
                int(bool(stop["is_desired_destination"])),
                stop["x"],
                stop["y"],
                stop["z"],
                json.dumps(stop["source_row"], separators=(",", ":")),
            ),
        )
    conn.commit()
    return {
        "ok": True,
        "carrier_trip_id": carrier_trip_id,
        "imported_stops": len(stops),
        "active_routes": active_carrier_trips(conn),
        "active_route": active_carrier_trip(conn),
    }


def start_carrier_trip(conn: sqlite3.Connection, payload: Dict[str, Any], started_at: str) -> Dict[str, Any]:
    carrier_trip_id = coerce_int(payload.get("carrier_trip_id"))
    if carrier_trip_id is None:
        return {"ok": False, "error": "Missing carrier_trip_id"}
    exists = conn.execute(
        "SELECT 1 FROM carrier_trip_routes WHERE carrier_trip_id=?",
        (carrier_trip_id,),
    ).fetchone()
    if not exists:
        return {"ok": False, "error": "Carrier trip not found"}
    conn.execute(
        """
        UPDATE carrier_trip_routes
        SET active=1,
            progress_started_datetime=COALESCE(progress_started_datetime, ?),
            progress_stop_index=COALESCE(progress_stop_index, 0),
            progress_updated_datetime=?
        WHERE carrier_trip_id=?
        """,
        (clean_text(started_at), clean_text(started_at), carrier_trip_id),
    )
    conn.commit()
    active_routes = active_carrier_trips(conn)
    return {
        "ok": True,
        "routes": carrier_trip_route_rows(conn),
        "active_routes": active_routes,
        "active_route": active_routes[0] if active_routes else None,
    }


def stop_carrier_trip(conn: sqlite3.Connection, payload: Dict[str, Any], stopped_at: str) -> Dict[str, Any]:
    carrier_trip_id = coerce_int(payload.get("carrier_trip_id"))
    if carrier_trip_id is None:
        return {"ok": False, "error": "Missing carrier_trip_id"}
    updated = conn.execute(
        """
        UPDATE carrier_trip_routes
        SET active=0, progress_updated_datetime=?
        WHERE carrier_trip_id=?
        """,
        (clean_text(stopped_at), carrier_trip_id),
    )
    if updated.rowcount < 1:
        return {"ok": False, "error": "Carrier trip not found"}
    conn.commit()
    active_routes = active_carrier_trips(conn)
    return {
        "ok": True,
        "routes": carrier_trip_route_rows(conn),
        "active_routes": active_routes,
        "active_route": active_routes[0] if active_routes else None,
    }


def set_carrier_trip_stop_skipped(
    conn: sqlite3.Connection,
    payload: Dict[str, Any],
    updated_at: str,
) -> Dict[str, Any]:
    carrier_trip_id = coerce_int(payload.get("carrier_trip_id"))
    stop_index = coerce_int(payload.get("stop_index"))
    if carrier_trip_id is None or stop_index is None:
        return {"ok": False, "error": "Missing carrier_trip_id or stop_index"}
    route = conn.execute(
        """
        SELECT carrier_trip_id, active, imported_datetime, progress_started_datetime,
               progress_stop_index, progress_updated_datetime
        FROM carrier_trip_routes
        WHERE carrier_trip_id=?
        """,
        (carrier_trip_id,),
    ).fetchone()
    if not route:
        return {"ok": False, "error": "Carrier trip not found"}
    exists = conn.execute(
        "SELECT 1 FROM carrier_trip_stops WHERE carrier_trip_id=? AND stop_index=?",
        (carrier_trip_id, stop_index),
    ).fetchone()
    if not exists:
        return {"ok": False, "error": "Carrier trip stop not found"}
    skipped = bool(payload.get("skipped"))
    conn.execute(
        """
        UPDATE carrier_trip_stops
        SET stop_skipped=?, stop_skipped_datetime=?
        WHERE carrier_trip_id=? AND stop_index=?
        """,
        (1 if skipped else 0, clean_text(updated_at) if skipped else None, carrier_trip_id, stop_index),
    )
    current_index = coerce_int(route["progress_stop_index"]) or 0
    if skipped:
        next_index = contiguous_carrier_trip_progress_index(conn, carrier_trip_id, current_index)
        if next_index > current_index:
            conn.execute(
                """
                UPDATE carrier_trip_routes
                SET progress_stop_index=?, progress_updated_datetime=?
                WHERE carrier_trip_id=?
                """,
                (next_index, clean_text(updated_at), carrier_trip_id),
            )
    elif stop_index <= current_index:
        conn.execute(
            """
            UPDATE carrier_trip_routes
            SET progress_stop_index=?, progress_updated_datetime=?
            WHERE carrier_trip_id=?
            """,
            (max(0, stop_index - 1), clean_text(updated_at), carrier_trip_id),
        )
    conn.commit()
    active_routes = active_carrier_trips(conn)
    return {
        "ok": True,
        "routes": carrier_trip_route_rows(conn),
        "active_routes": active_routes,
        "active_route": active_routes[0] if active_routes else None,
    }


def advance_active_carrier_trip_progress(
    conn: sqlite3.Connection,
    system_name: Optional[str],
    system_address: Optional[int],
    visited_at: str,
) -> bool:
    name = clean_text(system_name)
    address = coerce_int(system_address)
    if not name and address is None:
        return False
    active_rows = conn.execute(
        """
        SELECT carrier_trip_id, progress_stop_index
        FROM carrier_trip_routes
        WHERE active=1
        ORDER BY imported_datetime ASC, carrier_trip_id ASC
        """
    ).fetchall()
    if not active_rows:
        return False
    changed = False
    for active in active_rows:
        carrier_trip_id = int(active["carrier_trip_id"])
        current_index = coerce_int(active["progress_stop_index"]) or 0
        event_stop = conn.execute(
            """
            SELECT 1
            FROM carrier_trip_stops
            WHERE carrier_trip_id=? AND stop_index>?
              AND ((? IS NOT NULL AND system_address=?)
                   OR (? != '' AND lower(system_name_snapshot)=lower(?)))
            LIMIT 1
            """,
            (carrier_trip_id, current_index, address, address, name, name),
        ).fetchone()
        if not event_stop:
            continue
        next_index = contiguous_carrier_trip_progress_index(conn, carrier_trip_id, current_index)
        if next_index <= current_index:
            continue
        conn.execute(
            """
            UPDATE carrier_trip_routes
            SET progress_stop_index=?, progress_updated_datetime=?
            WHERE carrier_trip_id=?
            """,
            (next_index, clean_text(visited_at), carrier_trip_id),
        )
        changed = True
    if changed:
        conn.commit()
    return changed


def delete_carrier_trip(conn: sqlite3.Connection, payload: Dict[str, Any]) -> Dict[str, Any]:
    carrier_trip_id = coerce_int(payload.get("carrier_trip_id"))
    if carrier_trip_id is None:
        return {"ok": False, "error": "Missing carrier_trip_id"}
    conn.execute("DELETE FROM carrier_trip_stops WHERE carrier_trip_id=?", (carrier_trip_id,))
    conn.execute("DELETE FROM carrier_trip_routes WHERE carrier_trip_id=?", (carrier_trip_id,))
    conn.commit()
    active_routes = active_carrier_trips(conn)
    return {
        "ok": True,
        "routes": carrier_trip_route_rows(conn),
        "active_routes": active_routes,
        "active_route": active_routes[0] if active_routes else None,
    }
