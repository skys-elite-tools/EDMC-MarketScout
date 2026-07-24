"""Local browser UI for EDMC-MarketScout.

This module starts a tiny HTTP server bound to 127.0.0.1 by default. It serves
the bundled static web UI and JSON API responses from the local SQLite DB. The
only external network feature is the GitHub release/update check; no commander,
journal, route, station, or market data is uploaded.
"""
from __future__ import annotations

import datetime
import csv
import io
import json
import math
import mimetypes
import os
import ipaddress
import re
import shutil
import socket
import sqlite3
import tempfile
import threading
import traceback
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

_SERVERS: List[ThreadingHTTPServer] = []
_THREADS: List[threading.Thread] = []
_PORT: Optional[int] = None
_BIND_ADDRESS = "127.0.0.1"
_LAN_BIND_ADDRESS = ""
_LAN_PORT: Optional[int] = None
_LAN_ENABLED = False
_CONTEXT: Dict[str, Any] = {}
_LATEST_JOURNAL_EVENT: Optional[Dict[str, Any]] = None
ECONOMY_PRESETS_FILE = "marketscout-economy-presets.json"
CONFIG_FILE = "marketscout.config"
DEFAULT_BIND_ADDRESS = "127.0.0.1"
DEFAULT_BIND_PORT = 40595
DEFAULT_BEST_BUY_SUPPLY_CAP = 1000
DEFAULT_MINIMUM_POTENTIAL_PROFIT = 10000
GITHUB_REPO = "skys-elite-tools/EDMC-MarketScout"
GITHUB_RELEASES_LATEST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
PLUGIN_FOLDER_NAME = "EDMC-MarketScout"
_PLUGIN_VERSION = "0.0.0"
_UPDATE_LOCK = threading.Lock()
_DATA_VERSION_LOCK = threading.Lock()
_DATA_VERSION = 0
_UPDATE_STATUS: Dict[str, Any] = {
    "checked": False,
    "checking": False,
    "available": False,
    "can_update": False,
    "current_version": _PLUGIN_VERSION,
    "latest_version": "",
    "latest_tag": "",
    "html_url": "",
    "download_url": "",
    "error": "",
    "last_checked": "",
}
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


def load_web_config(plugin_dir: str) -> Dict[str, Any]:
    """Load the tiny MarketScout config file, creating defaults when missing."""
    path = os.path.join(plugin_dir, CONFIG_FILE)
    defaults = {
        "app.bind_address": DEFAULT_BIND_ADDRESS,
        "app.bind_port": str(DEFAULT_BIND_PORT),
        "app.lan_enabled": "0",
        "app.lan_bind_address": "",
    }
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            for key, value in defaults.items():
                f.write(f"{key}={value}\n")
        raw = dict(defaults)
    else:
        raw = dict(defaults)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                raw[key.strip()] = value.strip()

    legacy_bind_address = raw.get("app.bind_address") or DEFAULT_BIND_ADDRESS
    bind_address = legacy_bind_address if is_loopback_host(legacy_bind_address) else DEFAULT_BIND_ADDRESS
    lan_bind_address = raw.get("app.lan_bind_address") or ""
    lan_enabled = str(raw.get("app.lan_enabled") or "0").strip().lower() in {"1", "true", "yes", "on"}
    if legacy_bind_address not in {DEFAULT_BIND_ADDRESS, "localhost"} and not lan_bind_address:
        lan_bind_address = legacy_bind_address
        lan_enabled = True
    try:
        bind_port = int(raw.get("app.bind_port") or DEFAULT_BIND_PORT)
        if bind_port < 1 or bind_port > 65535:
            raise ValueError
    except (TypeError, ValueError):
        bind_port = DEFAULT_BIND_PORT
    return {
        "bind_address": bind_address,
        "bind_port": bind_port,
        "lan_enabled": lan_enabled,
        "lan_bind_address": lan_bind_address,
    }


def save_web_config(plugin_dir: str, bind_address: str, bind_port: int, lan_enabled: bool = False, lan_bind_address: str = "") -> Dict[str, Any]:
    path = os.path.join(plugin_dir, CONFIG_FILE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"app.bind_address={bind_address}\n")
        f.write(f"app.bind_port={bind_port}\n")
        f.write(f"app.lan_enabled={1 if lan_enabled else 0}\n")
        f.write(f"app.lan_bind_address={lan_bind_address}\n")
    return {
        "bind_address": bind_address,
        "bind_port": bind_port,
        "lan_enabled": lan_enabled,
        "lan_bind_address": lan_bind_address,
    }


def is_loopback_host(value: str) -> bool:
    value = str(value or "").strip().lower()
    if value == "localhost":
        return True
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.version == 4 and address.is_loopback


def is_shareable_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(str(value or "").strip())
    except ValueError:
        return False
    return (
        address.version == 4
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_unspecified
    )


def detected_bind_addresses() -> List[str]:
    addresses = ["127.0.0.1", "localhost"]
    seen = set(addresses)

    def add_address(value: str) -> None:
        value = str(value or "").strip()
        if value and value not in seen:
            addresses.append(value)
            seen.add(value)

    try:
        import fcntl
        import struct

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            for _index, name in socket.if_nameindex():
                if_name = name.encode("utf-8")[:15]
                request = struct.pack("256s", if_name)
                try:
                    result = fcntl.ioctl(sock.fileno(), 0x8915, request)
                except OSError:
                    continue
                add_address(socket.inet_ntoa(result[20:24]))
        finally:
            sock.close()
    except Exception:
        pass

    try:
        host = socket.gethostname()
        for value in socket.gethostbyname_ex(host)[2]:
            add_address(value)
        for info in socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM):
            add_address(info[4][0])
    except Exception:
        pass
    return addresses


def detected_loopback_addresses(addresses: List[str]) -> List[str]:
    values = ["127.0.0.1", "localhost"]
    seen = set(values)
    for value in addresses:
        if is_loopback_host(value) and value not in seen:
            values.append(value)
            seen.add(value)
    return values


def detected_lan_addresses(addresses: List[str]) -> List[str]:
    values = []
    seen = set()
    for value in addresses:
        if is_shareable_ipv4(value) and value not in seen:
            values.append(value)
            seen.add(value)
    return values


def start_server(
    plugin_dir: str,
    db_path: str,
    target_commodities: List[str],
    primary_metals: List[str],
    edmc_status_provider: Optional[Callable[[], Dict[str, Any]]] = None,
) -> int:
    """Start the local web server if needed and return its port."""
    global _SERVERS, _THREADS, _PORT, _BIND_ADDRESS, _LAN_BIND_ADDRESS, _LAN_PORT, _LAN_ENABLED, _CONTEXT
    if _SERVERS and _PORT is not None:
        return _PORT

    web_config = load_web_config(plugin_dir)
    _BIND_ADDRESS = str(web_config.get("bind_address") or DEFAULT_BIND_ADDRESS)
    _LAN_BIND_ADDRESS = str(web_config.get("lan_bind_address") or "").strip()
    _LAN_ENABLED = bool(web_config.get("lan_enabled")) and is_shareable_ipv4(_LAN_BIND_ADDRESS)
    _CONTEXT = {
        "plugin_dir": plugin_dir,
        "web_dir": os.path.join(plugin_dir, "web"),
        "db_path": db_path,
        "target_commodities": list(target_commodities),
        "primary_metals": list(primary_metals),
        "web_config": dict(web_config),
        "lan_error": "",
        "edmc_status_provider": edmc_status_provider,
    }

    bind_port = int(web_config["bind_port"])
    server = ThreadingHTTPServer((_BIND_ADDRESS, bind_port), MarketScoutRequestHandler)
    server.daemon_threads = True
    _PORT = int(server.server_address[1])
    _SERVERS.append(server)
    thread = threading.Thread(target=server.serve_forever, name="MarketScoutWebLocal", daemon=True)
    _THREADS.append(thread)
    thread.start()

    if _LAN_ENABLED:
        try:
            lan_server = ThreadingHTTPServer((_LAN_BIND_ADDRESS, bind_port), MarketScoutRequestHandler)
            lan_server.daemon_threads = True
            _LAN_PORT = int(lan_server.server_address[1])
            _SERVERS.append(lan_server)
            lan_thread = threading.Thread(target=lan_server.serve_forever, name="MarketScoutWebLan", daemon=True)
            _THREADS.append(lan_thread)
            lan_thread.start()
        except Exception as exc:
            _LAN_ENABLED = False
            _LAN_PORT = None
            _CONTEXT["lan_error"] = str(exc)
    return _PORT


def stop_server() -> None:
    global _SERVERS, _THREADS, _PORT, _LAN_PORT, _LAN_ENABLED
    for server in _SERVERS:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
    _SERVERS = []
    _THREADS = []
    _PORT = None
    _LAN_PORT = None
    _LAN_ENABLED = False


def server_url() -> Optional[str]:
    if _PORT is None:
        return None
    return f"http://{_BIND_ADDRESS}:{_PORT}/"


def lan_server_url() -> Optional[str]:
    if not _LAN_ENABLED or not _LAN_BIND_ADDRESS or _LAN_PORT is None:
        return None
    return f"http://{_LAN_BIND_ADDRESS}:{_LAN_PORT}/"


def update_latest_journal_event(event: Dict[str, Any]) -> None:
    """Store the most recent Journal event metadata for the Web UI status strip.

    This intentionally stays in memory instead of writing to SQLite, so routine
    Journal traffic does not force table reloads or mutate the user database.
    """
    global _LATEST_JOURNAL_EVENT
    _LATEST_JOURNAL_EVENT = dict(event)


def notify_data_changed() -> int:
    """Bump the Web UI data version after committed SQLite writes.

    The status API used to rely only on the main SQLite file mtime, but WAL
    mode can put fresh writes in the WAL file without immediately changing the
    main database file. An explicit in-memory version makes browser auto-refresh
    react to live station/market updates reliably.
    """
    global _DATA_VERSION
    version = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    with _DATA_VERSION_LOCK:
        _DATA_VERSION = max(_DATA_VERSION + 1, version)
        return _DATA_VERSION


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def set_update_status(**changes: Any) -> Dict[str, Any]:
    with _UPDATE_LOCK:
        _UPDATE_STATUS.update(changes)
        return dict(_UPDATE_STATUS)


def update_status_snapshot() -> Dict[str, Any]:
    with _UPDATE_LOCK:
        return dict(_UPDATE_STATUS)


def normalize_version_tag(value: Any) -> str:
    text = str(value or "").strip()
    return text[1:] if text.lower().startswith("v") else text


def version_tuple(value: Any) -> Tuple[int, int, int]:
    text = normalize_version_tag(value)
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", text)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def github_request(url: str, timeout: int = 12) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"EDMC-MarketScout/{_PLUGIN_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def start_update_check(plugin_dir: str, current_version: str) -> None:
    """Start a background GitHub release check without blocking EDMC startup."""
    global _PLUGIN_VERSION
    _PLUGIN_VERSION = normalize_version_tag(current_version) or "0.0.0"
    set_update_status(current_version=_PLUGIN_VERSION)
    snapshot = update_status_snapshot()
    if snapshot.get("checking"):
        return
    thread = threading.Thread(
        target=check_for_updates,
        name="MarketScoutUpdateCheck",
        daemon=True,
    )
    set_update_status(checking=True, error="")
    thread.start()


def check_for_updates() -> None:
    try:
        payload = json.loads(github_request(GITHUB_RELEASES_LATEST_API).decode("utf-8"))
        latest_tag = str(payload.get("tag_name") or "").strip()
        latest_version = normalize_version_tag(latest_tag)
        assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
        download_url = ""
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            if name.lower().endswith(".zip") and url:
                download_url = url
                break
        available = bool(latest_version) and version_tuple(latest_version) > version_tuple(_PLUGIN_VERSION)
        set_update_status(
            checked=True,
            checking=False,
            available=available,
            can_update=available and bool(download_url),
            current_version=_PLUGIN_VERSION,
            latest_version=latest_version,
            latest_tag=latest_tag,
            html_url=str(payload.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases/latest"),
            download_url=download_url,
            error="",
            last_checked=now_utc(),
        )
    except Exception as exc:
        set_update_status(
            checked=True,
            checking=False,
            available=False,
            can_update=False,
            error=str(exc),
            last_checked=now_utc(),
        )


def download_release_zip(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": f"EDMC-MarketScout/{_PLUGIN_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        with destination.open("wb") as f:
            shutil.copyfileobj(response, f)


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Unsafe zip entry: {member.filename}")
        archive.extractall(destination)


def find_plugin_payload(extracted_dir: Path) -> Path:
    for candidate in extracted_dir.rglob(PLUGIN_FOLDER_NAME):
        if candidate.is_dir() and (candidate / "load.py").is_file():
            return candidate
    if (extracted_dir / "load.py").is_file():
        return extracted_dir
    raise FileNotFoundError(f"Could not find {PLUGIN_FOLDER_NAME} in the downloaded release zip")


def copy_plugin_payload(source_dir: Path, plugin_dir: Path) -> None:
    for item in source_dir.iterdir():
        target = plugin_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def perform_update() -> Dict[str, Any]:
    snapshot = update_status_snapshot()
    if not snapshot.get("available"):
        return {"ok": False, "error": "No MarketScout update is currently available.", "update": snapshot}
    if not snapshot.get("download_url"):
        return {
            "ok": False,
            "error": "The latest GitHub release does not include an installable zip asset.",
            "update": snapshot,
        }

    plugin_dir = Path(_CONTEXT.get("plugin_dir") or "").resolve()
    if not plugin_dir.is_dir() or plugin_dir.name != PLUGIN_FOLDER_NAME:
        return {"ok": False, "error": "Could not identify the current MarketScout plugin directory.", "update": snapshot}

    backup_root = plugin_dir.parent / "EDMC-MarketScout-backups.disabled"
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_root / f"MarketScout-backup-{timestamp}"
    try:
        backup_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(plugin_dir, backup_dir)
        with tempfile.TemporaryDirectory(prefix="marketscout-update-") as tmp:
            tmp_dir = Path(tmp)
            zip_path = tmp_dir / "release.zip"
            extracted_dir = tmp_dir / "extracted"
            extracted_dir.mkdir()
            download_release_zip(str(snapshot["download_url"]), zip_path)
            safe_extract_zip(zip_path, extracted_dir)
            payload_dir = find_plugin_payload(extracted_dir)
            copy_plugin_payload(payload_dir, plugin_dir)
        latest_version = snapshot.get("latest_version") or _PLUGIN_VERSION
        set_update_status(
            available=False,
            can_update=False,
            current_version=latest_version,
            error="",
            update_completed=True,
            backup_path=str(backup_dir),
        )
        return {
            "ok": True,
            "message": "Update Complete. Please restart EDMC to start using the latest version of MarketScout.",
            "backup_path": str(backup_dir),
            "update": update_status_snapshot(),
        }
    except Exception as exc:
        set_update_status(error=str(exc), backup_path=str(backup_dir))
        return {
            "ok": False,
            "error": str(exc),
            "message": "The update could not be completed.",
            "backup_path": str(backup_dir),
            "plugin_dir": str(plugin_dir),
            "update": update_status_snapshot(),
        }


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
            if path == "/api/rare-commodities":
                return self.send_json(api_rare_commodities(parse_qs(parsed.query)))
            if path == "/api/rare-station-trade-options":
                return self.send_json(api_rare_station_trade_options())
            if path == "/api/rare-station-trade":
                return self.send_json(api_rare_station_trade(parse_qs(parsed.query)))
            if path == "/api/commodity-stats":
                return self.send_json(api_commodity_stats(parse_qs(parsed.query)))
            if path == "/api/ledger/summary":
                return self.send_json(api_ledger_summary(parse_qs(parsed.query)))
            if path == "/api/options":
                return self.send_json(api_options())
            if path == "/api/economy-presets":
                return self.send_json(api_economy_presets())
            if path == "/api/commodities":
                return self.send_json(api_commodities())
            if path == "/api/station-filter-options":
                return self.send_json(api_station_filter_options())
            if path == "/api/settings":
                return self.send_json(api_settings())
            if path == "/api/user-data":
                return self.send_json(api_user_data(parse_qs(parsed.query)))
            if path == "/api/trip-routes":
                return self.send_json(api_trip_routes())
            if path == "/api/config":
                return self.send_json(api_config())
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
            if parsed.path == "/api/user-data":
                return self.send_json(api_save_user_data(payload))
            if parsed.path == "/api/trip-routes/import":
                return self.send_json(api_import_trip_route(payload))
            if parsed.path == "/api/trip-routes/import-station-hints":
                return self.send_json(api_import_trip_route_station_hints(payload))
            if parsed.path == "/api/trip-routes/start":
                return self.send_json(api_start_trip_route(payload))
            if parsed.path == "/api/trip-routes/delete":
                return self.send_json(api_delete_trip_route(payload))
            if parsed.path == "/api/economy-presets":
                return self.send_json(api_save_economy_preset(payload))
            if parsed.path == "/api/analyze-commodities":
                return self.send_json(api_analyze_commodities(payload))
            if parsed.path == "/api/config":
                return self.send_json(api_save_config(payload))
            if parsed.path == "/api/update":
                return self.send_json(perform_update())
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
    conn = sqlite3.connect(_CONTEXT["db_path"], timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def api_status() -> Dict[str, Any]:
    db_path = _CONTEXT.get("db_path")
    version = 0
    if db_path and os.path.exists(db_path):
        version = int(os.path.getmtime(db_path) * 1000)
    with _DATA_VERSION_LOCK:
        version = max(version, _DATA_VERSION)
    edmc_status_provider = _CONTEXT.get("edmc_status_provider")
    edmc_status = None
    if callable(edmc_status_provider):
        try:
            edmc_status = edmc_status_provider()
        except Exception as exc:
            edmc_status = {
                "available": False,
                "station_data_enabled": None,
                "label": "EDDN Station: Unknown",
                "detail": f"Could not read EDMC status: {exc}",
            }
    return {
        "ok": True,
        "data_version": version,
        "target_commodities": _CONTEXT.get("target_commodities", []),
        "primary_metals": _CONTEXT.get("primary_metals", []),
        "latest_journal_event": _LATEST_JOURNAL_EVENT,
        "edmc": edmc_status,
        "update": update_status_snapshot(),
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

def setting_set(
    conn: sqlite3.Connection,
    key: str,
    value: Any,
    *,
    updated_datetime: Optional[str] = None,
    only_if_newer: bool = False,
) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    stamp = updated_datetime or now_utc()
    stale_guard = ""
    if only_if_newer:
        stale_guard = """
            WHERE settings.updated_datetime IS NULL
                OR settings.updated_datetime = ''
                OR settings.updated_datetime <= excluded.updated_datetime
        """
    try:
        conn.execute(
            f"""
            INSERT INTO settings(key, value_json, updated_datetime, schema_version)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(key) DO UPDATE SET
                value_json=excluded.value_json,
                updated_datetime=excluded.updated_datetime,
                schema_version=excluded.schema_version
            {stale_guard}
            """,
            (key, payload, stamp),
        )
    except sqlite3.OperationalError:
        conn.execute(
            "INSERT INTO settings(key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
            (key, payload),
        )


def settings_has_metadata(conn: sqlite3.Connection) -> bool:
    try:
        rows = conn.execute("PRAGMA table_info(settings)").fetchall()
        columns = {str(row[1]) for row in rows}
        return "updated_datetime" in columns and "schema_version" in columns
    except sqlite3.Error:
        return False


def user_data_keys_from_query(qs: Dict[str, List[str]]) -> List[str]:
    raw_values = []
    for value in qs.get("keys", []):
        raw_values.extend(str(value or "").split(","))
    return [value.strip() for value in raw_values if value.strip()]


def read_user_data_entries(conn: sqlite3.Connection, keys: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    has_metadata = settings_has_metadata(conn)
    columns = "key, value_json, updated_datetime, schema_version" if has_metadata else "key, value_json"
    params: List[Any] = []
    where = ""
    if keys:
        placeholders = ",".join("?" for _ in keys)
        where = f"WHERE key IN ({placeholders})"
        params = list(keys)
    rows = conn.execute(f"SELECT {columns} FROM settings {where} ORDER BY key", params).fetchall()
    values: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        try:
            value = json.loads(row["value_json"]) if row["value_json"] is not None else None
        except Exception:
            value = None
        values[str(row["key"])] = {
            "value": value,
            "updated_datetime": row["updated_datetime"] if has_metadata else "",
            "schema_version": row["schema_version"] if has_metadata else 1,
        }
    return values

def watched_commodities(conn: sqlite3.Connection) -> List[str]:
    val = setting_get(conn, "watched_commodities", _CONTEXT.get("primary_metals", ["Palladium", "Gold", "Silver"]))
    return [str(x) for x in val if str(x).strip()] if isinstance(val, list) else ["Palladium", "Gold", "Silver"]

def best_buy_ignore_commodities(conn: sqlite3.Connection) -> List[str]:
    val = setting_get(conn, "best_buy_ignore_commodities", [])
    return [str(x) for x in val if str(x).strip()] if isinstance(val, list) else []

def setting_int(conn: sqlite3.Connection, key: str, default: int, min_value: int = 0, max_value: int = 1_000_000_000) -> int:
    try:
        value = int(setting_get(conn, key, default))
    except (TypeError, ValueError):
        return default
    return max(min_value, min(value, max_value))

def best_buy_supply_cap(conn: sqlite3.Connection) -> int:
    return setting_int(conn, "best_buy_supply_cap", DEFAULT_BEST_BUY_SUPPLY_CAP, 1, 1_000_000_000)

def minimum_potential_profit(conn: sqlite3.Connection) -> int:
    return setting_int(conn, "minimum_potential_profit", DEFAULT_MINIMUM_POTENTIAL_PROFIT, 0, 1_000_000_000)

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


def api_commodity_stats(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def one(name: str) -> str:
        return (qs.get(name, [""])[0] or "").strip()
    sort = one("sort") or "commodity_asc"
    order_by = {
        "category_asc": "category IS NULL, category ASC, commodity ASC",
        "max_profit_desc": "max_profit IS NULL, max_profit DESC, commodity ASC",
        "commodity_asc": "commodity ASC",
    }.get(sort, "commodity ASC")
    with connect() as conn:
        try:
            rows = [
                row_to_dict(r)
                for r in conn.execute(
                    f"""
                    SELECT commodity, category, min_buy, avg_buy, max_sell, max_profit
                    FROM commodity_global_stats
                    WHERE commodity IS NOT NULL AND commodity != ''
                    ORDER BY {order_by}
                    """
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            rows = []
    return {"rows": rows, "count": len(rows), "sort": sort}


def api_station_filter_options() -> Dict[str, Any]:
    with connect() as conn:
        try:
            systems = [
                r[0]
                for r in conn.execute(
                    """
                    SELECT DISTINCT system_name
                    FROM systems
                    WHERE system_name IS NOT NULL
                      AND TRIM(system_name) != ''
                      AND (last_visit_datetime IS NOT NULL OR source = 'local_visit')
                    ORDER BY system_name COLLATE NOCASE
                    LIMIT 5000
                    """
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            systems = []
        try:
            stations = [
                r[0]
                for r in conn.execute(
                    """
                    SELECT DISTINCT station_name
                    FROM stations
                    WHERE station_name IS NOT NULL
                      AND TRIM(station_name) != ''
                      AND (last_station_visit_datetime IS NOT NULL OR source = 'local_visit')
                    ORDER BY station_name COLLATE NOCASE
                    LIMIT 5000
                    """
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            stations = []
    return {"systems": systems, "stations": stations}


def api_settings() -> Dict[str, Any]:
    with connect() as conn:
        return {
            "watched_commodities": watched_commodities(conn),
            "watched_columns": watched_columns(conn),
            "best_buy_ignore_commodities": best_buy_ignore_commodities(conn),
            "best_buy_supply_cap": best_buy_supply_cap(conn),
            "minimum_potential_profit": minimum_potential_profit(conn),
        }


def api_user_data(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    keys = user_data_keys_from_query(qs)
    with connect() as conn:
        values = read_user_data_entries(conn, keys or None)
    return {"ok": True, "values": values}


def api_config() -> Dict[str, Any]:
    plugin_dir = _CONTEXT.get("plugin_dir") or os.getcwd()
    config = load_web_config(plugin_dir)
    suggestions = detected_bind_addresses()
    loopback_suggestions = detected_loopback_addresses(suggestions)
    lan_suggestions = detected_lan_addresses(suggestions)
    if config.get("bind_address") and config["bind_address"] not in loopback_suggestions:
        loopback_suggestions.append(config["bind_address"])
    if config.get("lan_bind_address") and config["lan_bind_address"] not in suggestions:
        suggestions.append(config["lan_bind_address"])
    if config.get("lan_bind_address") and config["lan_bind_address"] not in lan_suggestions:
        lan_suggestions.append(config["lan_bind_address"])
    return {
        "ok": True,
        "config": config,
        "active": {
            "bind_address": _BIND_ADDRESS,
            "bind_port": _PORT,
            "url": server_url(),
            "lan_enabled": _LAN_ENABLED,
            "lan_bind_address": _LAN_BIND_ADDRESS,
            "lan_url": lan_server_url(),
            "lan_error": _CONTEXT.get("lan_error") or "",
        },
        "defaults": {
            "bind_address": DEFAULT_BIND_ADDRESS,
            "bind_port": DEFAULT_BIND_PORT,
            "lan_enabled": False,
            "lan_bind_address": "",
        },
        "suggested_bind_addresses": suggestions,
        "suggested_loopback_addresses": loopback_suggestions,
        "suggested_lan_addresses": lan_suggestions,
        "config_file": CONFIG_FILE,
        "mdns": {
            "available": False,
            "name": "marketscout.local",
            "message": "mDNS advertising is not enabled in this beta. It needs a reliable Zeroconf/mDNS implementation.",
        },
    }


def api_save_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    bind_address = str(payload.get("bind_address") or "").strip()
    if not is_loopback_host(bind_address):
        return {"ok": False, "error": "Local address must be localhost or a loopback IPv4 address"}
    lan_enabled = bool(payload.get("lan_enabled"))
    lan_bind_address = str(payload.get("lan_bind_address") or "").strip()
    if lan_bind_address and (any(ch.isspace() for ch in lan_bind_address) or "/" in lan_bind_address):
        return {"ok": False, "error": "Invalid LAN address"}
    if lan_enabled and not is_shareable_ipv4(lan_bind_address):
        return {"ok": False, "error": "LAN sharing needs a non-loopback IPv4 address"}
    try:
        bind_port = int(payload.get("bind_port"))
        if bind_port < 1 or bind_port > 65535:
            raise ValueError
    except (TypeError, ValueError):
        return {"ok": False, "error": "Port must be a number from 1 to 65535"}

    plugin_dir = _CONTEXT.get("plugin_dir") or os.getcwd()
    config = save_web_config(plugin_dir, bind_address, bind_port, lan_enabled, lan_bind_address)
    restart_required = (
        bind_address != _BIND_ADDRESS
        or bind_port != _PORT
        or lan_enabled != _LAN_ENABLED
        or (lan_bind_address if lan_enabled else "") != (_LAN_BIND_ADDRESS if _LAN_ENABLED else "")
    )
    return {
        "ok": True,
        "config": config,
        "restart_required": restart_required,
        "message": "Saved. Restart EDMC to apply the listening configuration." if restart_required else "Saved.",
    }


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
        if "best_buy_ignore_commodities" in payload and isinstance(payload["best_buy_ignore_commodities"], list):
            setting_set(conn, "best_buy_ignore_commodities", [str(x) for x in payload["best_buy_ignore_commodities"] if str(x).strip()])
        if "best_buy_supply_cap" in payload:
            try:
                value = max(1, int(payload["best_buy_supply_cap"]))
            except (TypeError, ValueError):
                value = DEFAULT_BEST_BUY_SUPPLY_CAP
            setting_set(conn, "best_buy_supply_cap", value)
        if "minimum_potential_profit" in payload:
            try:
                value = max(0, int(payload["minimum_potential_profit"]))
            except (TypeError, ValueError):
                value = DEFAULT_MINIMUM_POTENTIAL_PROFIT
            setting_set(conn, "minimum_potential_profit", value)
        conn.commit()
    return {"ok": True}


def api_save_user_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_entries = payload.get("entries")
    raw_values = payload.get("values")
    if raw_entries is None and raw_values is None and payload.get("key"):
        raw_values = {str(payload.get("key")): payload.get("value")}
    if raw_entries is None:
        if not isinstance(raw_values, dict):
            return {"ok": False, "error": "Expected entries or values object"}
        raw_entries = {
            key: {"value": value, "updated_datetime": now_utc()}
            for key, value in raw_values.items()
        }
    if not isinstance(raw_entries, dict):
        return {"ok": False, "error": "Expected entries or values object"}

    clean_entries: Dict[str, Tuple[Any, str]] = {}
    for key, entry in raw_entries.items():
        clean_key = str(key or "").strip()
        if not clean_key:
            continue
        if len(clean_key) > 160:
            return {"ok": False, "error": f"Data key is too long: {clean_key[:40]}..."}
        if isinstance(entry, dict) and "value" in entry:
            value = entry.get("value")
            updated_datetime = str(entry.get("updated_datetime") or now_utc())
        else:
            value = entry
            updated_datetime = now_utc()
        clean_entries[clean_key] = (value, updated_datetime)

    if not clean_entries:
        return {"ok": True, "values": {}}

    with connect() as conn:
        for key, (value, updated_datetime) in clean_entries.items():
            setting_set(conn, key, value, updated_datetime=updated_datetime, only_if_newer=True)
        conn.commit()
        values = read_user_data_entries(conn, list(clean_entries.keys()))
    return {"ok": True, "values": values}


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
            s.last_visit_datetime AS last_system_visit_datetime,
            (
                SELECT st.station_name
                FROM stations st
                LEFT JOIN systems ss ON ss.system_address = st.system_address
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
                LEFT JOIN systems ss ON ss.system_address = st.system_address
                WHERE st.last_station_visit_datetime IS NOT NULL
                  AND (
                    st.system_address = trs.system_address
                    OR lower(ss.system_name) = lower(trs.system_name_snapshot)
                  )
                ORDER BY st.last_station_visit_datetime DESC
                LIMIT 1
            ) AS last_station_visit_datetime
        FROM trip_route_stops trs
        LEFT JOIN systems s ON s.system_address = trs.system_address
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


def api_trip_routes() -> Dict[str, Any]:
    with connect() as conn:
        try:
            routes = trip_route_rows(conn)
            active = active_trip_route(conn)
        except sqlite3.OperationalError:
            routes = []
            active = None
    return {"ok": True, "routes": routes, "active_route": active}


def api_import_trip_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    route, stops = parse_spansh_tourist_route(payload)
    imported_at = now_utc()
    with connect() as conn:
        conn.execute("UPDATE trip_routes SET active=0")
        cur = conn.execute(
            """
            INSERT INTO trip_routes(
                route_name, source, spansh_job_id, spansh_search_id, source_system,
                final_destination_system, jump_range_ly, loop_route, imported_datetime, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
        active = active_trip_route(conn)
    notify_data_changed()
    return {"ok": True, "route_id": route_id, "imported_stops": len(stops), "active_route": active}


def api_import_trip_route_station_hints(payload: Dict[str, Any]) -> Dict[str, Any]:
    hints = parse_spansh_station_hints(payload)
    route_id = coerce_int(payload.get("route_id"))
    imported_at = now_utc()
    with connect() as conn:
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
        for system_key, hint in hints.items():
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
        active = active_trip_route(conn)
        routes = trip_route_rows(conn)
    notify_data_changed()
    return {
        "ok": True,
        "route_id": route_id,
        "matched_stops": updated,
        "hinted_systems": len(hints),
        "imported_datetime": imported_at,
        "routes": routes,
        "active_route": active,
    }


def api_start_trip_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    route_id = coerce_int(payload.get("route_id"))
    if route_id is None:
        return {"ok": False, "error": "Missing route_id"}
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM trip_routes WHERE route_id=?", (route_id,)).fetchone()
        if not exists:
            return {"ok": False, "error": "Route not found"}
        conn.execute("UPDATE trip_routes SET active=0")
        conn.execute("UPDATE trip_routes SET active=1 WHERE route_id=?", (route_id,))
        conn.commit()
        active = active_trip_route(conn)
        routes = trip_route_rows(conn)
    notify_data_changed()
    return {"ok": True, "routes": routes, "active_route": active}


def api_delete_trip_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    route_id = coerce_int(payload.get("route_id"))
    if route_id is None:
        return {"ok": False, "error": "Missing route_id"}
    with connect() as conn:
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
        active = active_trip_route(conn)
        routes = trip_route_rows(conn)
    notify_data_changed()
    return {"ok": True, "routes": routes, "active_route": active}


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
        watched = watched_commodities(conn)
        display_cols = [{"commodity": c, "side": "buy"} for c in watched]
        ignored_best_buy = best_buy_ignore_commodities(conn)
        supply_cap = best_buy_supply_cap(conn)
        min_profit = minimum_potential_profit(conn)

    ignored_sql = ""
    ignored_sql_mp2 = ""
    if ignored_best_buy:
        ignored_names = ", ".join("'" + c.replace("'", "''") + "'" for c in ignored_best_buy)
        ignored_sql = f" AND mp.commodity NOT IN ({ignored_names})"
        ignored_sql_mp2 = f" AND mp2.commodity NOT IN ({ignored_names})"

    # Need all watched commodities in both buy/sell form so the Web UI can
    # switch between Buy Scout and Sell Scout without changing user settings.
    display_commodities = []
    for commodity in watched:
        if commodity not in display_commodities:
            display_commodities.append(commodity)

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
        # Best Buy score: (max_sell - current buy) * min(supply, configured cap).
        "MAX(CASE WHEN cgs.max_sell IS NOT NULL AND mp.buy_price IS NOT NULL AND mp.buy_price > 0 AND COALESCE(mp.supply, 0) > 0 "
        f"AND (cgs.max_sell - mp.buy_price) >= {min_profit} "
        f"{ignored_sql} THEN (cgs.max_sell - mp.buy_price) * CASE WHEN COALESCE(mp.supply, 0) > {supply_cap} THEN {supply_cap} ELSE COALESCE(mp.supply, 0) END END) AS best_buy_score",
    ]
    # Commodity that produced the max Best Buy score. Ties are not important for scouting.
    select_cols.append(
        "(SELECT mp2.commodity FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 AND COALESCE(mp2.supply, 0) > 0 "
        f"AND (cgs2.max_sell - mp2.buy_price) >= {min_profit} "
        f"{ignored_sql_mp2} ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>{supply_cap} THEN {supply_cap} ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_commodity"
    )
    select_cols.append(
        "(SELECT mp2.buy_price FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 AND COALESCE(mp2.supply, 0) > 0 "
        f"AND (cgs2.max_sell - mp2.buy_price) >= {min_profit} "
        f"{ignored_sql_mp2} ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>{supply_cap} THEN {supply_cap} ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_price"
    )
    select_cols.append(
        "(SELECT mp2.supply FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 AND COALESCE(mp2.supply, 0) > 0 "
        f"AND (cgs2.max_sell - mp2.buy_price) >= {min_profit} "
        f"{ignored_sql_mp2} ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>{supply_cap} THEN {supply_cap} ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_supply"
    )
    select_cols.append(
        "(SELECT cgs2.inara_id FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 AND COALESCE(mp2.supply, 0) > 0 "
        f"AND (cgs2.max_sell - mp2.buy_price) >= {min_profit} "
        f"{ignored_sql_mp2} ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>{supply_cap} THEN {supply_cap} ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_inara_id"
    )
    select_cols.append(
        "(SELECT cgs2.max_sell FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 AND COALESCE(mp2.supply, 0) > 0 "
        f"AND (cgs2.max_sell - mp2.buy_price) >= {min_profit} "
        f"{ignored_sql_mp2} ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>{supply_cap} THEN {supply_cap} ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_max_sell"
    )
    select_cols.append(
        "(SELECT CASE WHEN COALESCE(mp2.supply, 0) > 0 THEN (cgs2.max_sell - mp2.buy_price) END FROM market_prices mp2 "
        "JOIN commodity_global_stats cgs2 ON cgs2.commodity=mp2.commodity "
        "WHERE mp2.market_id=st.market_id AND cgs2.max_sell IS NOT NULL AND mp2.buy_price IS NOT NULL AND mp2.buy_price > 0 AND COALESCE(mp2.supply, 0) > 0 "
        f"AND (cgs2.max_sell - mp2.buy_price) >= {min_profit} "
        f"{ignored_sql_mp2} ORDER BY ((cgs2.max_sell - mp2.buy_price) * CASE WHEN COALESCE(mp2.supply,0)>{supply_cap} THEN {supply_cap} ELSE COALESCE(mp2.supply,0) END) DESC LIMIT 1) AS best_buy_potential_profit"
    )
    for c in display_commodities:
        safe = c.replace("'", "''")
        latest_buy_sql = (
            f"(SELECT te.unit_price FROM trade_events te "
            f"WHERE te.commodity='{safe}' AND te.event_type='buy' AND te.unit_price IS NOT NULL AND te.unit_price > 0 "
            f"ORDER BY te.event_datetime DESC, te.trade_id DESC LIMIT 1)"
        )
        select_cols.extend([
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.buy_price END) AS '{c}_buy'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.sell_price END) AS '{c}_sell'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.supply END) AS '{c}_supply'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN mp.demand END) AS '{c}_demand'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN cgs.inara_id END) AS '{c}_inara_id'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN cgs.max_sell END) AS '{c}_max_sell'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN cgs.min_buy END) AS '{c}_min_buy'",
            f"MAX(CASE WHEN mp.commodity='{safe}' THEN {latest_buy_sql} END) AS '{c}_latest_buy_price'",
            f"MAX(CASE WHEN mp.commodity='{safe}' AND mp.sell_price IS NOT NULL AND mp.sell_price > 0 "
            f"AND COALESCE({latest_buy_sql}, cgs.min_buy) IS NOT NULL "
            f"THEN mp.sell_price - COALESCE({latest_buy_sql}, cgs.min_buy) END) AS '{c}_sell_profit'",
            f"MAX(CASE WHEN mp.commodity='{safe}' AND mp.buy_price IS NOT NULL AND mp.buy_price > 0 AND COALESCE(mp.supply, 0) > 0 AND cgs.max_sell IS NOT NULL AND (cgs.max_sell - mp.buy_price) >= {min_profit} THEN cgs.max_sell - mp.buy_price END) AS '{c}_potential_profit'",
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


def api_rare_commodities(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def one(name: str) -> str:
        return (qs.get(name, [""])[0] or "").strip()
    try:
        lim = max(1, min(int(one("limit") or "500"), 2000))
    except Exception:
        lim = 500

    engineering_only = one("engineering_only").lower() in ("1", "true", "yes")
    sort = one("sort") or "profit_desc"
    where: List[str] = []
    if engineering_only:
        where.append("is_engineering_rare = 1")

    sql = """
        SELECT *
        FROM (
            SELECT
                rc.commodity,
                rc.system_name,
                rc.station_name,
                rc.station_distance_ls,
                rc.usual_supply,
                rc.buy_price,
                rc.galactic_average_price,
                (
                    SELECT rch.supply
                    FROM rare_commodities_history rch
                    WHERE rch.commodity = rc.commodity
                    ORDER BY rch.supply IS NULL, rch.supply DESC, rch.seen_datetime DESC
                    LIMIT 1
                ) AS highest_supply,
                (
                    SELECT rch.seen_datetime
                    FROM rare_commodities_history rch
                    WHERE rch.commodity = rc.commodity
                    ORDER BY rch.supply IS NULL, rch.supply DESC, rch.seen_datetime DESC
                    LIMIT 1
                ) AS highest_supply_datetime,
                (
                    SELECT rch.supply
                    FROM rare_commodities_history rch
                    WHERE rch.commodity = rc.commodity
                    ORDER BY rch.seen_datetime DESC
                    LIMIT 1
                ) AS recent_supply,
                (
                    SELECT rch.seen_datetime
                    FROM rare_commodities_history rch
                    WHERE rch.commodity = rc.commodity
                    ORDER BY rch.seen_datetime DESC
                    LIMIT 1
                ) AS recent_supply_datetime,
                sd.x AS system_x,
                sd.y AS system_y,
                sd.z AS system_z,
                CASE
                    WHEN rc.galactic_average_price IS NOT NULL
                    THEN rc.galactic_average_price * 100
                END AS galactic_average_100x,
                CASE
                    WHEN rc.galactic_average_price IS NOT NULL AND rc.buy_price IS NOT NULL
                    THEN rc.galactic_average_price * 100 - rc.buy_price
                END AS carrier_profit,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM engineers_unlock eu
                        WHERE eu.is_rare_commodity=1
                          AND lower(trim(replace(eu.required_commodity, char(160), ' '))) =
                              lower(trim(replace(rc.commodity, char(160), ' ')))
                    )
                    THEN 1 ELSE 0
                END AS is_engineering_rare
            FROM rare_commodities rc
            LEFT JOIN systems_data sd
              ON lower(trim(replace(sd.system_name, char(160), ' '))) =
                 lower(trim(replace(rc.system_name, char(160), ' ')))
        )
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    if sort == "usual_supply_desc":
        sql += " ORDER BY usual_supply IS NULL, usual_supply DESC, commodity ASC LIMIT ?"
    else:
        sql += " ORDER BY carrier_profit IS NULL, carrier_profit DESC, commodity ASC LIMIT ?"
    with connect() as conn:
        try:
            rows = [row_to_dict(r) for r in conn.execute(sql, (lim,)).fetchall()]
            current = latest_current_position(conn)
            engineering = engineering_unlock_map(conn)
            for row in rows:
                row["distance_from_current_ly"] = distance_ly(
                    current,
                    (row.get("system_x"), row.get("system_y"), row.get("system_z")),
                )
                labels: List[str] = []
                has_engineer_distance = False
                for unlock in engineering.get(normalized_name(row.get("commodity")), []):
                    label = unlock["label"]
                    if current is not None:
                        unlock_distance = distance_ly(
                            (row.get("system_x"), row.get("system_y"), row.get("system_z")),
                            unlock.get("coords"),
                        )
                        if unlock_distance is not None:
                            label = f"{label} | {format_ly(unlock_distance)}"
                            has_engineer_distance = True
                    labels.append(label)
                row["engineering_unlocks"] = ", ".join(labels)
                row["engineering_unlocks_title"] = (
                    "Distance from the commodity system to the engineer system."
                    if has_engineer_distance else ""
                )
        except sqlite3.OperationalError:
            rows = []
    return {"rows": rows, "count": len(rows)}


def normalized_commodity_sql(column: str) -> str:
    return f"lower(replace(replace(replace(replace({column}, char(160), ''), ' ', ''), '-', ''), '_', ''))"


def rare_recent_supply_sql() -> str:
    return """
        SELECT rch.supply
        FROM rare_commodities_history rch
        WHERE rch.commodity = rc.commodity
        ORDER BY rch.seen_datetime DESC
        LIMIT 1
    """


def rare_recent_supply_datetime_sql() -> str:
    return """
        SELECT rch.seen_datetime
        FROM rare_commodities_history rch
        WHERE rch.commodity = rc.commodity
        ORDER BY rch.seen_datetime DESC
        LIMIT 1
    """


def api_rare_station_trade_options() -> Dict[str, Any]:
    stage = "connect"
    with connect() as conn:
        try:
            stage = "target_market_ids"
            market_ids = [
                int(r[0])
                for r in conn.execute(
                    """
                    SELECT DISTINCT market_id
                    FROM market_prices
                    WHERE sell_price IS NOT NULL
                      AND sell_price > 0
                      AND market_id IS NOT NULL
                    """
                ).fetchall()
            ]
            if not market_ids:
                return {"rows": [], "count": 0}

            placeholders = ",".join("?" for _ in market_ids)
            stage = "station_lookup"
            rows = [
                row_to_dict(r)
                for r in conn.execute(
                    f"""
                    SELECT
                        st.market_id,
                        COALESCE(s.system_name, '') AS system_name,
                        st.station_name,
                        st.station_type,
                        st.largest_pad,
                        st.last_station_visit_datetime,
                        NULL AS market_updated
                    FROM stations st
                    LEFT JOIN systems s ON s.system_address = st.system_address
                    WHERE st.station_name IS NOT NULL
                      AND trim(st.station_name) != ''
                      AND st.market_id IN ({placeholders})
                    """,
                    market_ids,
                ).fetchall()
            ]
        except sqlite3.OperationalError as exc:
            log_sqlite_diagnostic("api_rare_station_trade_options", stage, exc)
            return {"rows": [], "count": 0, "error": str(exc), "stage": stage}

    rows.sort(key=lambda row: (str(row.get("system_name") or "").lower(), str(row.get("station_name") or "").lower()))
    rows.sort(key=lambda row: row.get("last_station_visit_datetime") or "", reverse=True)
    rows = rows[:1000]
    for index, row in enumerate(rows):
        row["is_current"] = 1 if index == 0 else 0
        row["label"] = f"{row.get('station_name') or 'Unknown station'} in {row.get('system_name') or 'Unknown system'}"
    return {"rows": rows, "count": len(rows)}


def api_rare_station_trade(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def one(name: str) -> str:
        return (qs.get(name, [""])[0] or "").strip()

    try:
        market_id = int(one("market_id") or "0")
    except ValueError:
        market_id = 0
    if market_id == 0:
        return {"rows": [], "count": 0, "station": None}

    rc_key = normalized_commodity_sql("rc.commodity")
    mp_key = normalized_commodity_sql("mp.commodity")
    recent_supply_sql = rare_recent_supply_sql()
    recent_supply_datetime_sql = rare_recent_supply_datetime_sql()
    sql = f"""
        SELECT
            rc.commodity,
            rc.system_name,
            rc.station_name,
            rc.usual_supply,
            rc.buy_price AS origin_buy_price,
            rc.galactic_average_price,
            mp.sell_price,
            mp.market_price_update_datetime,
            ({recent_supply_sql}) AS recent_supply,
            ({recent_supply_datetime_sql}) AS recent_supply_datetime,
            COALESCE(
                ({recent_supply_sql}),
                rc.usual_supply,
                0
            ) AS default_origin_stock
        FROM rare_commodities rc
        JOIN market_prices mp
          ON mp.market_id = ?
         AND {mp_key} = {rc_key}
        WHERE mp.sell_price IS NOT NULL
          AND mp.sell_price > 0
          AND rc.buy_price IS NOT NULL
        ORDER BY rc.commodity ASC
    """
    with connect() as conn:
        try:
            station_row = conn.execute(
                """
                SELECT st.market_id, COALESCE(s.system_name, '') AS system_name,
                       st.station_name, st.station_type, st.largest_pad,
                       st.last_station_visit_datetime
                FROM stations st
                LEFT JOIN systems s ON s.system_address = st.system_address
                WHERE st.market_id=?
                """,
                (market_id,),
            ).fetchone()
            rows = [row_to_dict(r) for r in conn.execute(sql, (market_id,)).fetchall()]
        except sqlite3.OperationalError:
            station_row = None
            rows = []
    return {
        "rows": rows,
        "count": len(rows),
        "station": row_to_dict(station_row) if station_row else None,
    }


def normalized_name(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").strip().split()).casefold()


def latest_current_position(conn: sqlite3.Connection) -> Optional[Tuple[float, float, float]]:
    try:
        row = conn.execute(
            """
            SELECT x, y, z
            FROM systems
            WHERE x IS NOT NULL AND y IS NOT NULL AND z IS NOT NULL
            ORDER BY last_visit_datetime IS NULL, last_visit_datetime DESC
            LIMIT 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if row is None:
        return None
    return (float(row["x"]), float(row["y"]), float(row["z"]))


def engineering_unlock_map(conn: sqlite3.Connection) -> Dict[str, List[Dict[str, Any]]]:
    try:
        rows = conn.execute(
            """
            SELECT eu.engineer, eu.engineer_system, eu.required_commodity,
                   eu.required_commodity_quantity,
                   sd.x AS x, sd.y AS y, sd.z AS z
            FROM engineers_unlock eu
            LEFT JOIN systems_data sd
              ON lower(trim(replace(sd.system_name, char(160), ' '))) =
                 lower(trim(replace(eu.engineer_system, char(160), ' ')))
            WHERE eu.is_rare_commodity=1
              AND eu.required_commodity IS NOT NULL
              AND trim(eu.required_commodity) != ''
            ORDER BY eu.engineer
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        label = str(row["engineer"] or "")
        if row["engineer_system"]:
            label = f"{label} @ {row['engineer_system']}"
        if row["required_commodity_quantity"] is not None:
            try:
                label = f"{label} | x{int(row['required_commodity_quantity'])}"
            except (TypeError, ValueError):
                label = f"{label} | x{row['required_commodity_quantity']}"
        coords = None
        if row["x"] is not None and row["y"] is not None and row["z"] is not None:
            coords = (float(row["x"]), float(row["y"]), float(row["z"]))
        out.setdefault(normalized_name(row["required_commodity"]), []).append({"label": label, "coords": coords})
    return out


def distance_ly(
    a: Optional[Tuple[Any, Any, Any]],
    b: Optional[Tuple[Any, Any, Any]],
) -> Optional[float]:
    if a is None or b is None:
        return None
    try:
        ax, ay, az = float(a[0]), float(a[1]), float(a[2])
        bx, by, bz = float(b[0]), float(b[1]), float(b[2])
    except (TypeError, ValueError):
        return None
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)


def format_ly(value: float) -> str:
    if abs(value) < 0.005:
        return "0 Ly"
    if value < 10:
        return f"{value:.2f} Ly"
    return f"{value:.1f} Ly"


def split_commodity_input(text: str) -> List[str]:
    seen = set()
    out: List[str] = []
    for part in str(text or "").split(","):
        name = " ".join(part.replace("\xa0", " ").strip().split())
        key = normalized_name(name)
        if name and key not in seen:
            seen.add(key)
            out.append(name)
    return out


def api_analyze_commodities(payload: Dict[str, Any]) -> Dict[str, Any]:
    names = split_commodity_input(str(payload.get("text") or ""))
    keys = {normalized_name(name) for name in names}
    if not keys:
        return {"regular": [], "rare": [], "input_count": 0}

    with connect() as conn:
        try:
            regular_rows = [
                row_to_dict(r)
                for r in conn.execute(
                    """
                    SELECT commodity, category, min_buy, max_profit
                    FROM commodity_global_stats
                    WHERE commodity IS NOT NULL AND commodity != ''
                    ORDER BY commodity ASC
                    """
                ).fetchall()
            ]
            rare_rows = [
                row_to_dict(r)
                for r in conn.execute(
                    """
                    SELECT rc.commodity, rc.system_name, rc.station_name, rc.usual_supply,
                           rc.buy_price, rc.galactic_average_price,
                           sd.x AS system_x, sd.y AS system_y, sd.z AS system_z,
                           CASE
                               WHEN rc.galactic_average_price IS NOT NULL
                               THEN rc.galactic_average_price * 100
                           END AS galactic_average_100x
                    FROM rare_commodities rc
                    LEFT JOIN systems_data sd
                      ON lower(trim(replace(sd.system_name, char(160), ' '))) =
                         lower(trim(replace(rc.system_name, char(160), ' ')))
                    WHERE rc.commodity IS NOT NULL AND rc.commodity != ''
                    ORDER BY rc.commodity ASC
                    """
                ).fetchall()
            ]
            current = latest_current_position(conn)
        except sqlite3.OperationalError:
            return {"regular": [], "rare": [], "input_count": len(names)}

    rare_keys = {normalized_name(row.get("commodity")) for row in rare_rows}
    regular = [
        row for row in regular_rows
        if normalized_name(row.get("commodity")) in keys and normalized_name(row.get("commodity")) not in rare_keys
    ]
    rare: List[Dict[str, Any]] = []
    for row in rare_rows:
        if normalized_name(row.get("commodity")) not in keys:
            continue
        row["distance_from_current_ly"] = distance_ly(
            current,
            (row.get("system_x"), row.get("system_y"), row.get("system_z")),
        )
        rare.append(row)
    return {"regular": regular, "rare": rare, "input_count": len(names)}


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


def log_sqlite_diagnostic(where: str, stage: str, exc: BaseException) -> None:
    """Write a small local-only SQLite diagnostic for runtime-only failures."""
    try:
        plugin_dir = _CONTEXT.get("plugin_dir") or os.getcwd()
        db_path = str(_CONTEXT.get("db_path") or "")
        path = os.path.join(plugin_dir, "marketscout-web-error.log")
        probes: Dict[str, Any] = {}
        if db_path:
            for suffix in ("", "-wal", "-shm"):
                candidate = db_path + suffix
                try:
                    probes[f"file{suffix or '-main'}"] = {
                        "exists": os.path.exists(candidate),
                        "size": os.path.getsize(candidate) if os.path.exists(candidate) else None,
                    }
                except OSError as file_exc:
                    probes[f"file{suffix or '-main'}"] = {"error": str(file_exc)}
        try:
            with sqlite3.connect(db_path, timeout=2.0) as probe_conn:
                probe_conn.row_factory = sqlite3.Row
                probe_conn.execute("PRAGMA busy_timeout=2000")
                probe_conn.execute("PRAGMA temp_store=MEMORY")
                probes["database_list"] = [tuple(r) for r in probe_conn.execute("PRAGMA database_list").fetchall()]
                probes["journal_mode"] = probe_conn.execute("PRAGMA journal_mode").fetchone()[0]
                probes["quick_check"] = probe_conn.execute("PRAGMA quick_check").fetchone()[0]
                probes["market_prices_count"] = probe_conn.execute("SELECT COUNT(*) FROM market_prices").fetchone()[0]
                probes["positive_sell_market_count"] = probe_conn.execute(
                    "SELECT COUNT(DISTINCT market_id) FROM market_prices WHERE sell_price IS NOT NULL AND sell_price > 0"
                ).fetchone()[0]
        except Exception as probe_exc:
            probes["probe_error"] = str(probe_exc)
        with open(path, "a", encoding="utf-8") as f:
            f.write("----- sqlite diagnostic -----\n")
            f.write(f"where={where}\n")
            f.write(f"stage={stage}\n")
            f.write(f"error={exc}\n")
            f.write(f"db_path={db_path}\n")
            f.write(f"cwd={os.getcwd()}\n")
            f.write(f"sqlite_version={sqlite3.sqlite_version}\n")
            f.write(json.dumps(probes, indent=2, default=str))
            f.write("\n")
    except Exception:
        pass
