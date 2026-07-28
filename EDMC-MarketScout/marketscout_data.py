"""Data access helpers for EDMC-MarketScout.

This module owns database reads/writes that are not inherently tied to EDMC or
HTTP request handling. Keep web responses and notifications in
`marketscout_web.py`; keep SQL and import persistence here.
"""
from __future__ import annotations

import csv
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


def contiguous_trip_progress_index(conn: sqlite3.Connection, route_id: int, current_index: int, baseline: str) -> int:
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
                AND s.last_visit_datetime >= ?
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
        (baseline, route_id, current_index),
    ).fetchall()

    for row in stop_rows:
        if not int(row["stop_skipped"] or 0) and not int(row["was_visited"] or 0):
            break
        next_index = int(row["stop_index"])
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


def upsert_route_stop_system_data(conn: sqlite3.Connection, stop: Dict[str, Any], imported_at: str) -> None:
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
            "spansh_tourist_route",
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
