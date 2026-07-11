"""CSV import helpers for EDMC-MarketScout.

Currently supports Spansh station search CSV exports. This module is deliberately
local-only: it performs no network access and no scraping.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    return s


def get(row: Dict[str, Any], *names: str) -> Optional[str]:
    """Case-insensitive CSV column getter."""
    lower = {k.strip().lower(): k for k in row.keys()}
    for name in names:
        key = lower.get(name.strip().lower())
        if key is not None:
            return clean_text(row.get(key))
    return None


def first_int(value: Any) -> Optional[int]:
    value = clean_text(value)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


def first_float(value: Any) -> Optional[float]:
    value = clean_text(value)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def first_bool(value: Any) -> Optional[int]:
    value = clean_text(value)
    if value is None:
        return None
    v = value.lower()
    if v in ("true", "1", "yes", "y"):
        return 1
    if v in ("false", "0", "no", "n"):
        return 0
    return None


def stable_negative_id(*parts: Any) -> int:
    raw = "|".join(str(p or "").lower().strip() for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return -int(digest[:14], 16)


def detect_source(headers: List[str]) -> Optional[str]:
    normalized = {h.strip().lower() for h in headers}
    # Spansh station search exports vary by selected columns. These are enough
    # to identify the template family without requiring every optional column.
    spansh_required = {"name", "system name", "economy", "system population"}
    if spansh_required.issubset(normalized):
        return "spansh"
    return None


def import_candidates_csv(conn, path: str, source: Optional[str] = None) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        if not source or source == "auto":
            source = detect_source(headers)
        if source != "spansh":
            raise ValueError("Unsupported CSV template. Currently supported source: spansh")

        pulled_at = now_utc_iso()
        imported = 0
        skipped = 0
        rows = list(reader)
        for row in rows:
            ok = import_spansh_row(conn, row, pulled_at)
            if ok:
                imported += 1
            else:
                skipped += 1
        conn.commit()
        return {"source": source, "pulled_at": pulled_at, "imported": imported, "skipped": skipped, "rows": len(rows)}


def import_spansh_row(conn, row: Dict[str, Any], pulled_at: str) -> bool:
    station_name = get(row, "Name", "Station Name")
    system_name = get(row, "System Name")
    if not station_name or not system_name:
        return False

    population = first_int(get(row, "System Population"))
    faction_state = get(row, "Controlling Faction State", "State")
    station_economy_primary = get(row, "Economy")
    station_economy_secondary = get(row, "Secondary Economy")
    system_primary_economy = get(row, "System Primary Economy") or station_economy_primary
    system_secondary_economy = get(row, "System Secondary Economy")
    distance_to_arrival = first_float(get(row, "Distance to Arrival (LS)"))
    body_name = get(row, "Body Name")
    has_market = first_bool(get(row, "Has Market"))
    marketplace = get(row, "Marketplace")
    planetary = first_bool(get(row, "Planetary"))
    station_type = get(row, "Type")
    source_updated = get(row, "Last Updated At")
    market_source_updated = get(row, "Market Last Updated At")
    carrier_docking_access = get(row, "Carrier Docking Access")
    carrier_name = get(row, "Carrier Name")
    export_commodities_raw = get(row, "Export Commodities")

    large_pads = first_int(get(row, "Large Pads"))
    medium_pads = first_int(get(row, "Medium Pads"))
    small_pads = first_int(get(row, "Small Pads"))
    largest_pad = infer_largest_pad(large_pads, medium_pads, small_pads, station_type)

    station_economies = unique_clean([station_economy_primary, station_economy_secondary])
    system_economies = unique_clean([system_primary_economy, system_secondary_economy])

    # Prefer an existing real/local system or station row when present. This
    # prevents re-importing a Spansh candidate as a second synthetic station
    # after the commander has already visited the physical station.
    existing_system = conn.execute(
        "SELECT system_address FROM systems WHERE lower(system_name)=lower(?) ORDER BY system_address > 0 DESC LIMIT 1",
        (system_name,),
    ).fetchone()
    system_address = int(existing_system[0]) if existing_system else stable_negative_id("spansh-system", system_name)

    existing_station = conn.execute(
        """
        SELECT st.market_id
        FROM stations st
        LEFT JOIN systems s ON s.system_address=st.system_address
        WHERE lower(st.station_name)=lower(?) AND lower(COALESCE(s.system_name, ?))=lower(?)
        ORDER BY st.market_id > 0 DESC, st.last_station_visit_datetime IS NOT NULL DESC
        LIMIT 1
        """,
        (station_name, system_name, system_name),
    ).fetchone()
    market_id = int(existing_station[0]) if existing_station else stable_negative_id("spansh-station", system_name, station_name)

    conn.execute(
        """
        INSERT INTO systems(system_address, system_name, population, system_economy,
                            system_economies_json, source, source_pulled_datetime,
                            source_data_updated_datetime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(system_address) DO UPDATE SET
            system_name=excluded.system_name,
            population=COALESCE(excluded.population, systems.population),
            system_economy=COALESCE(excluded.system_economy, systems.system_economy),
            system_economies_json=COALESCE(excluded.system_economies_json, systems.system_economies_json),
            source=COALESCE(systems.source, excluded.source),
            source_pulled_datetime=excluded.source_pulled_datetime,
            source_data_updated_datetime=COALESCE(excluded.source_data_updated_datetime, systems.source_data_updated_datetime)
        """,
        (system_address, system_name, population, system_primary_economy, json.dumps(system_economies) if system_economies else None, "spansh", pulled_at, source_updated),
    )

    is_fleet_carrier = int(is_fleet_carrier_name_or_type(station_name, station_type, carrier_name, carrier_docking_access))

    conn.execute(
        """
        INSERT INTO stations(market_id, system_address, station_name, station_type, largest_pad,
                             station_faction_state, station_economy, station_economies_json,
                             source, source_pulled_datetime, source_data_updated_datetime,
                             market_source_updated_datetime, distance_to_arrival_ls,
                             body_name, has_market, export_commodities_json, is_fleet_carrier,
                             carrier_docking_access, carrier_name, planetary, marketplace)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(market_id) DO UPDATE SET
            system_address=COALESCE(excluded.system_address, stations.system_address),
            station_name=excluded.station_name,
            station_type=COALESCE(excluded.station_type, stations.station_type),
            largest_pad=COALESCE(excluded.largest_pad, stations.largest_pad),
            station_faction_state=COALESCE(excluded.station_faction_state, stations.station_faction_state),
            station_economy=COALESCE(excluded.station_economy, stations.station_economy),
            station_economies_json=COALESCE(excluded.station_economies_json, stations.station_economies_json),
            source=COALESCE(stations.source, excluded.source),
            source_pulled_datetime=excluded.source_pulled_datetime,
            source_data_updated_datetime=COALESCE(excluded.source_data_updated_datetime, stations.source_data_updated_datetime),
            market_source_updated_datetime=COALESCE(excluded.market_source_updated_datetime, stations.market_source_updated_datetime),
            distance_to_arrival_ls=COALESCE(excluded.distance_to_arrival_ls, stations.distance_to_arrival_ls),
            body_name=COALESCE(excluded.body_name, stations.body_name),
            has_market=COALESCE(excluded.has_market, stations.has_market),
            export_commodities_json=COALESCE(excluded.export_commodities_json, stations.export_commodities_json),
            is_fleet_carrier=MAX(COALESCE(stations.is_fleet_carrier, 0), COALESCE(excluded.is_fleet_carrier, 0)),
            carrier_docking_access=COALESCE(excluded.carrier_docking_access, stations.carrier_docking_access),
            carrier_name=COALESCE(excluded.carrier_name, stations.carrier_name),
            planetary=COALESCE(excluded.planetary, stations.planetary),
            marketplace=COALESCE(excluded.marketplace, stations.marketplace)
        """,
        (
            market_id, system_address, station_name, station_type, largest_pad,
            faction_state, station_economy_primary, json.dumps(station_economies) if station_economies else None,
            "spansh", pulled_at, source_updated, market_source_updated, distance_to_arrival,
            body_name, has_market, export_commodities_raw, is_fleet_carrier,
            carrier_docking_access, carrier_name, planetary, marketplace,
        ),
    )
    return True


def unique_clean(values: List[Optional[str]]) -> List[str]:
    out: List[str] = []
    for value in values:
        value = clean_text(value)
        if value and value not in out:
            out.append(value)
    return out


def infer_largest_pad(large: Optional[int], medium: Optional[int], small: Optional[int], station_type: Optional[str]) -> Optional[str]:
    if large and large > 0:
        return "L"
    if medium and medium > 0:
        return "M"
    if small and small > 0:
        return "S"
    t = (station_type or "").lower().replace(" ", "")
    if any(x in t for x in ("orbis", "ocellus", "coriolis", "asteroidbase", "surfaceport", "planetaryport", "megaship")):
        return "L"
    if "outpost" in t:
        return "M"
    return None


def is_fleet_carrier_name_or_type(name: Optional[str], station_type: Optional[str], carrier_name: Optional[str] = None, carrier_access: Optional[str] = None) -> bool:
    blob = " ".join(clean_text(x) or "" for x in (name, station_type, carrier_name, carrier_access)).lower().replace("-", " ")
    return "fleet carrier" in blob or "fleetcarrier" in blob or "drake class" in blob or carrier_name is not None
