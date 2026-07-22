"""
EDMC-MarketScout
EDMarketConnector plugin adapter.

Keep this file intentionally small: EDMC imports `load.py` directly and calls
the hook functions below. The MarketScout implementation lives in
`marketscout_app.py` so most feature work can stay outside the EDMC adapter.
"""
from __future__ import annotations

import importlib.util
import os
from typing import Any, Dict, Optional

PLUGIN_NAME = "EDMC-MarketScout"
PLUGIN_VERSION = "0.2.6"

APP_MODULE: Any = None


def load_app_module() -> Any:
    """Load the MarketScout implementation without relying on sys.path."""
    global APP_MODULE
    if APP_MODULE is not None:
        return APP_MODULE

    path = os.path.join(os.path.dirname(__file__), "marketscout_app.py")
    spec = importlib.util.spec_from_file_location("marketscout_app_local", path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load marketscout_app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PLUGIN_NAME = PLUGIN_NAME
    module.PLUGIN_VERSION = PLUGIN_VERSION
    APP_MODULE = module
    return module


def plugin_start3(plugin_dir: str) -> str:
    """EDMC plugin entry point."""
    app = load_app_module()
    app.PLUGIN_VERSION = PLUGIN_VERSION
    return app.plugin_start3(plugin_dir)


def plugin_stop() -> None:
    app = load_app_module()
    return app.plugin_stop()


def plugin_app(parent: Any) -> Any:
    app = load_app_module()
    return app.plugin_app(parent)


def journal_entry(
    cmdr: str,
    is_beta: bool,
    system: str,
    station: str,
    entry: Dict[str, Any],
    state: Dict[str, Any],
) -> Optional[str]:
    app = load_app_module()
    return app.journal_entry(cmdr, is_beta, system, station, entry, state)


def cmdr_data(data: Any, is_beta: bool) -> Optional[str]:
    app = load_app_module()
    return app.cmdr_data(data, is_beta)


def cmdr_data_legacy(data: Any, is_beta: bool) -> Optional[str]:
    app = load_app_module()
    if hasattr(app, "cmdr_data_legacy"):
        return app.cmdr_data_legacy(data, is_beta)
    return app.cmdr_data(data, is_beta)
