# EDMC-MarketScout Project Notes

These notes are intended as a handoff/reference document for future development conversations. The repository is the source of truth; this file summarizes the architecture, product decisions, privacy constraints, and current workflows.

## Project purpose

EDMC-MarketScout is an Elite Dangerous Market Connector (EDMC) plugin for local market scouting. It helps identify profitable commodity buying opportunities, especially temporary low-price/high-supply “jackpots,” while allowing the user to keep a short private scouting window before optionally publishing data through EDMC/EDDN/Inara/EDSM.

Primary goals:

- Record visited systems, stations, BGS/state/economy context, and market data locally.
- Store full commodity market data when available.
- Compute and display Best Buy opportunities from locally stored market data and configured commodity stats.
- Track jackpot history over time so the user can see how fast opportunities decay.
- Track a trade ledger with buy/sell events, Journal-based profit, and optional LIFO statistics.
- Provide a modern browser-based local Web UI while keeping the original Tk/classic UI as fallback.
- Never upload data from MarketScout itself unless a future feature is explicitly opt-in.

## Privacy rules

MarketScout itself should remain local-only by default.

Current privacy assumptions:

- MarketScout writes to local SQLite only.
- MarketScout’s Web UI server binds to `127.0.0.1` only.
- MarketScout must not send data to EDDN, Inara, EDSM, Spansh, Discord, or any other remote service unless a future feature explicitly opts in.
- Candidate import should use CSV/manual import, not scraping.
- Scraping public websites should not be added.
- Users can control EDMC’s own upload settings separately. For private scouting windows, disable EDMC EDDN station data and system/scan data, plus other uploader plugins if desired.

If future Discord/webhook/overlay/network features are added, they should be optional, clearly labeled, rate-limited where appropriate, and should never log secrets such as webhook URLs.

## Runtime and packaging rules

End users should not need frontend build tools.

- EDMC runtime uses Python and static files already built into `EDMC-MarketScout/web/`.
- Vue/Vite/Node/npm are development/build-time tools only.
- Release packages must include a ready-to-serve `web/` directory.
- Do not include `node_modules/` in releases or patches.
- Do not include runtime/local data such as `marketscout.sqlite3`, `marketscout-ui.json`, `marketscout-economy-presets.json`, logs, or `__pycache__/`.

## Repository structure

Important files/directories:

```text
EDMC-MarketScout/
  load.py                    # EDMC plugin entry point and main legacy/Tk/plugin logic
  marketscout_importer.py    # CSV import logic, currently including Spansh templates
  marketscout_ledger.py      # Trade ledger logic and LIFO/statistics calculations
  marketscout_web.py         # Local HTTP server and JSON API endpoints
  commodities.csv            # Commodity catalog/stats input loaded on startup
  README.md
  web/                       # Prebuilt static Web UI served at runtime
  web-src/                   # Vue 3 + Vite source for developers
    package.json
    package-lock.json
    vite.config.js
    src/
      App.vue
      main.js
      style.css
      utils.js
      components/
        TopBar.vue
        ViewControls.vue
        StationsTable.vue
        StationDetails.vue
        CommoditySettings.vue
        JackpotHistory.vue
        LedgerView.vue
        FooterBar.vue
DEVELOPERS.md                # Build/development instructions
PROJECT_NOTES.md             # This file
```

## Web UI architecture

The Web UI is Vue 3 + Vite, built into static files in `web/`.

Layout structure:

1. Top bar: logo/title placeholder, navigation, status, future donation/link placeholders.
2. View controls: controls/filters/settings for the active view.
3. Main view: active content.
4. Footer: about/link/donation placeholders.

Current views:

- `Stations`: filters + current station table + details pane.
- `Jackpots`: placeholder/future controls + jackpot history.
- `Ledger`: placeholder/future controls + ledger table/filters.

The Python local web server provides JSON endpoints; Vue should not know about SQLite directly.

### Economy filter presets

The Stations view Economy filter is intentionally empty by default so general users are not forced into the original `Extraction, Refinery` scouting workflow. The field supports saved presets through the local Web API. Presets are stored in `marketscout-economy-presets.json` in the plugin folder, not browser storage, so they survive browser changes. The default preset list is supplied by `marketscout_web.py` and includes single-value economy names plus `Extraction, Refinery`. User-saved presets are merged with the default list and shown alphabetically.

### Stations default ordering

The Stations API should default to a freshness-first order: newest `market_updated` first, newest `station_visit` second, strongest `best_buy_score` third, then system and station name alphabetically. This keeps the page focused on the newest information while relying on row highlights to make good deals obvious without adding another sort-mode control. Keep the SQL `ORDER BY` and the defensive post-dedupe Python sort in sync.

## Frontend development workflow

From the repo root:

```bash
cd EDMC-MarketScout/web-src
npm install
npm run build
```

The build output should be written into `EDMC-MarketScout/web/`. Commit both source changes under `web-src/` and built output under `web/` when preparing a release or patch for end-user testing.

If npm behaves oddly, remove partial install artifacts and try again:

```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

If `package-lock.json` is deliberately changed, commit it. Do not commit `node_modules/`.

## Database concepts

The local database is `marketscout.sqlite3` and is intentionally ignored from git.

Main data concepts:

- Systems: system-level data such as name/address, coordinates, population, security, economy/state context.
- Stations: station-level data such as name, market ID, station type, pad size, economies, faction/state, source, source timestamps, fleet carrier flag.
- Market prices: commodity rows per market/station. Current direction is to store all commodities, not just a fixed metal list.
- Commodity global stats: catalog/config table populated from `commodities.csv` with commodity display name, `max_sell`, and `min_buy`.
- Jackpot events/samples: static jackpot context plus event-driven time-series samples.
- Trade events/lots: ledger rows for MarketBuy/MarketSell, Journal profit fields, and optional LIFO details.

## Commodity model

Use a stable canonical commodity key internally and a display name separately.

Reason: Frontier/localized names and rare commodities can collide if matched loosely. A previous bug mapped `Sothis Crystalline Gold` as normal `Gold`, which overwrote Gold prices. Commodity matching must avoid suffix/substring collisions.

Current design intent:

- Store all commodity data from market captures.
- Use `commodity_global_stats`/`commodities.csv` as the authoritative catalog for the Web UI commodity selector.
- Watched commodities control which commodity-specific columns are shown.
- Best Buy calculation is independent of watched commodities and should consider all commodities with `max_sell` in `commodity_global_stats` that are present at a station.

Default `commodities.csv` includes at least:

```csv
commodity_name,max_sell,min_buy
Palladium,71000,
Gold,67000,
Silver,49000,
```

Best Buy scoring:

```text
commodityBuyScore = (max_sell - current_buy_price) * min(current_supply, 1000)
```

The highest score wins.

## Market data capture

MarketScout currently records market data through two paths:

1. EDMC/CAPI `cmdr_data()` market data where available.
2. Local `Market.json` fallback from the Journal directory when the game writes it.

The `Market.json` path has been important for reliable market price capture.

Market data should update on each fresh market capture for the same station. It should merge into the same physical station rather than creating duplicate station rows.

## Candidate import

Current import direction:

- CSV import only.
- Spansh CSV is supported via `marketscout_importer.py`.
- No scraping.
- Imported candidates should use `source`/`source_pulled_datetime` metadata.
- Fleet Carriers should be detected/flagged and excluded by default in UI filters unless “Include fleet carriers” is enabled.
- Imported candidate rows may have less data than local visits. Later local visits should merge/update those rows instead of creating duplicates.

## Jackpot history

Jackpot detection is event-driven, not timer-based.

Rules/intent:

- When fresh market data is recorded, check whether the station qualifies as jackpot according to current thresholds.
- Default jackpot logic evolved from hard-coded Palladium/Gold/Silver; future direction should use watched/configured commodities or a configurable subset.
- Sampling interval is 30 minutes by code constant, not a background timer.
- If a qualifying station is still a jackpot and enough time has passed since the previous sample, add a new sample.
- If a previously active jackpot no longer qualifies, add a final ended sample and close the event.
- Main Stations view should show the current/latest station only once. Older changes belong in Jackpot History.

## Ledger

Ledger is implemented separately in `marketscout_ledger.py`.

Trade capture:

- Records Journal `MarketBuy` and `MarketSell` events.
- Stores system, station, commodity, quantity, unit price, total, and timestamp.
- For sells, Journal `AvgPricePaid` is the primary profit source when available.
- LIFO lot-based calculations are retained as optional/statistical details, not the default display.
- Ledger UI defaults to Journal-based profit and hides LIFO details unless enabled.

Credits/hour calculation:

- Based on sale cadence, not holding time.
- When a sale is recorded, find the previous sale within the last 60 minutes.
- If present:

```text
timePerSaleInSeconds = current_sale_time - previous_sale_time
numSalesPerHour = 3600 / timePerSaleInSeconds
creditsPerHour = current_sale_profit * numSalesPerHour
```

- If no previous sale within 60 minutes, Cr/hr is blank.

Ledger also snapshots market-side quantity at trade time:

- BUY rows show Supply under the commodity name.
- SELL rows show Demand under the commodity name.

This is based on latest known market data at the time of the trade, usually before the trade rather than after.

## UI/readability decisions

- Web UI is the primary modern UI.
- Classic Tk UI remains as fallback and should not be heavily modified unless explicitly requested.
- Source column is hidden by default but available in details/optional contexts.
- Station name should stand out visually from system name, because multiple stations in the same system are common.
- The Web UI should favor compact tables plus details panes rather than extremely wide tables.
- Watched commodity columns are user-configurable. Users may choose Buy and Sell columns separately.

## Possible future features

Ideas discussed but not yet implemented:

- Efficient scouting route planner based on stored/imported candidate stations and current position.
- Overlay integration with EDMC-ModernOverlay/EDMCOverlay, likely optional and modular in `marketscout_overlay.py`.
- Discord webhook jackpot notifications, optional and privacy-aware, likely modular in `marketscout_discord.py`.
- Remote/bridge overlay was considered but is probably not needed.
- Better saved presets for filters/scouting modes.
- More formal tests/migration checks.

## Patch/baseline workflow

The repo is the source of truth. Chat context is only convenience.

Recommended workflow:

- Establish a baseline commit/zip periodically.
- For small changes, exchange patches:

```bash
git diff <baseline>..HEAD > my-changes.patch
```

- For multiple commits as patch files:

```bash
git format-patch <baseline>..HEAD
```

- For uncommitted edits:

```bash
git diff > my-uncommitted-changes.patch
```

- Send a fresh full repo zip when many patches have accumulated, after large refactors, when generated `web/` assets change significantly, or when there is any doubt about file state.

Recommended zip exclusions:

```text
node_modules/
__pycache__/
*.pyc
*.log
marketscout.sqlite3
marketscout-ui.json
web-src/dist/
```

Including `.git/` is useful if the archive stays reasonably small.

## Current baseline note

As of the component refactor, the current relevant commit created during this workflow was:

```text
f864b01 Refactor Vue UI into components
```

If a newer baseline is established, update this section.
