# EDMC-MarketScout

Local-only EDMarketConnector plugin for scouting station market/BGS conditions, commodity prices, rare commodities, engineer unlocks, trade ledger entries, and Fleet Carrier trade announcements.

## What it does

- Adds one small `MarketScout` button to EDMC's main window.
- Records system visits from Journal events.
- Records station visits from Journal events.
- Stores commodity market prices from EDMC CAPI data when available, with a local `Market.json` fallback.
- Stores everything locally in `marketscout.sqlite3` inside the plugin folder.
- Opens a local browser Web UI served from `127.0.0.1`.
- Shows Stations, Jackpots, Ledger, Commodities, Rare Commodities, Analyze Commodities, and Carrier Trade Announcements views.
- Supports watched commodity columns and a Best Buy ignore list.
- Imports candidate stations from supported CSV exports, currently Spansh station-search CSVs.
- Imports maintained rawdata CSV files for commodity stats, rare commodities, engineer unlock requirements, and relevant system coordinates.
- Tracks row/source metadata such as `local_visit` or `spansh`.
- Can hide Fleet Carrier rows by default with an `Include fleet carriers` checkbox.
- Provides a local Fleet Carrier trade announcement image/text generator with downloadable PNG/JPG output.

## Privacy

MarketScout itself has no network/upload code. It writes to a local SQLite database and serves local bundled Web UI assets on `127.0.0.1`.

For a private scouting window, disable EDMC's own EDDN upload settings while scouting:

- `Send Station Data to Elite Dangerous Data Network`
- `Send System and Scan Data to Elite Dangerous Data Network`

Re-enable them later when you are ready to contribute data.

## Configuration

On startup, MarketScout creates `marketscout.config` in the plugin folder if it does not already exist. The default file is:

```ini
app.bind_address=127.0.0.1
app.bind_port=40595
app.lan_enabled=0
app.lan_bind_address=
```

MarketScout always uses a loopback address for same-computer access. The fixed default port keeps browser localStorage state, such as Carrier Trade Announcements layouts, available across EDMC/browser restarts. Users may edit this file if they need a different loopback address, a different port, or an additional LAN listener. Restart EDMC after changing it.

The Web UI also has a `Config` page at the end of the top navigation. It can edit the local loopback address, the shared port, and the optional LAN listener. Local quick-fill options only include loopback addresses such as `127.0.0.1`, `localhost`, and `127.0.1.1` when detected. It shows a QR code only when LAN access is enabled with a shareable IPv4 address, so another same-network device can open the UI more easily. Restart EDMC after saving listening changes.

Keep `app.lan_enabled=0` if you want MarketScout reachable only from this computer. Enabling LAN access can make the Web UI reachable from other devices on your local network.

## Install

1. In EDMC, open `File` > `Settings` > `Plugins` > `Open`.
2. Copy the entire `MarketScout` folder into that plugins directory.
3. Restart EDMC.
4. You should see a small `MarketScout` button in the EDMC main window.

## CSV import

MarketScout includes local-only support code for importing supported candidate-station CSV exports. The beta UI is web-only, so any future user-facing CSV import flow should be added to the Web UI rather than reintroducing the old classic window.

The Spansh template currently expects columns like:

- `Name`
- `System Name`
- `Distance to Arrival (LS)`
- `Controlling Faction State`
- `Export Commodities`
- `Has Market`
- `Economy`
- `System Population`

Spansh exports do not include Elite market IDs or system addresses, so MarketScout creates stable negative placeholder IDs. When you later actually visit a matching system/station, MarketScout attempts to merge the imported placeholder row into the real visited row.

## Rawdata imports

On startup, MarketScout refreshes selected local CSV data only when the file SHA-256 changes. Current files live under `EDMC-MarketScout/rawdata/`:

- `commodities.csv` -> `commodity_global_stats`
- `commodities_rare.csv` -> `rare_commodities`
- `engineers-unlock.csv` -> `engineers_unlock`
- `systems_data.csv` -> `systems_data`

The helper scripts for regenerating these files live under `local-tools/` in the development workspace.

## Web UI views

- `Stations`: station scouting table, watched commodity columns, Best Buy, filters, and settings.
- `Jackpots`: jackpot history samples.
- `Ledger`: Journal trade ledger with optional LIFO details.
- `Commodities`: global commodity stats.
- `Rare Commodities`: rare commodity source table with engineering unlock labels, usual supply, distance, and 100x galactic-average carrier-sale estimates.
- `Analyze Commodities`: paste a comma-separated commodity list and split matches into regular and rare commodity tables.
- `Carrier Trade Announcements`: create local Fleet Carrier trade announcements with draggable on-image text and copyable Discord/Reddit text.

## Version

0.1.4 adds Spansh CSV candidate import, source/source-pulled metadata, optional sell/demand columns, Fleet Carrier flag/filter, and more robust CAPI marketdata parsing.

0.1.2 adds configurable cheap-metal row highlighting and a Flag column.

0.1.1 adds a selectable column chooser and remembers visible columns in `marketscout-ui.json`.

0.1.0 initial prototype.

## Notes / limitations

- Largest pad is inferred from station type when no explicit field is available.
- Station faction state is read from the Journal if available; if Frontier/EDMC omits it for a specific event, it may remain blank until a later event provides it.
- Market prices are stored for all captured commodities.
- Candidate imports from Spansh have no market prices until you actually visit/update the station.
- No route planner yet.


## 0.1.4 notes

Spansh CSV import now supports the richer station-search export columns, including station type, pad counts, planetary flag, source update timestamps, market source timestamp, system primary/secondary economy, station secondary economy, carrier name/access fields, and marketplace where present. No scraping or network access is used.

## 0.1.5 notes

0.1.5 adds targeted market-data debugging and a local `Market.json` fallback. When EDMC calls `cmdr_data()`, MarketScout writes a concise payload summary to `marketscout-market-debug.log`. When a Journal `Market` event arrives, MarketScout also tries to read the game's local `Market.json` from EDMC's configured Journal directory and stores only the configured tracked commodities.

If market prices are still not stored, open the commodity market once, then inspect `marketscout-market-debug.log` and `marketscout-error.log` in the plugin folder.

## 0.1.6 notes

0.1.6 fixes false cheap-row highlighting by ignoring zero/unavailable buy prices and limiting highlight checks to the primary scouting metals: Palladium, Gold, and Silver. It also changes the default metal column order to Palladium, Gold, Silver; adds compact two-line columns such as `Palladium Buy` showing buy price above supply; and adds compact location display with system above station/pad.

## 0.1.8 notes

0.1.8 adds event-driven jackpot history tracking. When fresh market data is recorded, MarketScout checks Palladium, Gold, and Silver against the current highlight thresholds. If any metal has buy price at or below the price threshold and supply at or above the supply threshold, a static jackpot event is created with the system/station/BGS/economy context, and a time-series sample is stored. Additional samples are added only when fresh market data arrives and at least `JACKPOT_SAMPLE_INTERVAL_MINUTES` has elapsed since the previous sample. The default interval is 30 minutes and is easy to change near the top of `load.py`.

No background timer is used. No data is uploaded.

Jackpot data is stored in:

- `jackpot_events` — static context at detection time.
- `jackpot_samples` — timestamped Palladium/Gold/Silver buy price and supply snapshots.

The Web UI includes a `Jackpot History` button that displays the stored samples.


## 0.1.11

- Changed Ledger credits/hour to use sale cadence: if a previous sell exists within 60 minutes, credits/hour is current sale profit scaled by elapsed time between the two sell events.
- LIFO profit/hour remains available as optional LIFO/statistics detail.


## 0.1.13

- Fixed commodity normalization so rare commodities like Sothis Crystalline Gold no longer overwrite normal Gold market rows.
- Normal commodity matching now requires exact commodity symbols after Frontier localization cleanup.


## 0.1.14 notes

- MarketScout now stores all commodities seen in market data, not just the original metals.
- The Web UI has a Commodities settings panel. Watched commodities affect highlighting/details, while Buy/Sell table columns can be selected separately.
- Added `commodity_global_stats` and Best Buy scoring. On startup, MarketScout looks for `rawdata/commodities.csv` in the plugin folder and refreshes stats when the file SHA-256 differs from the last imported hash. Current catalog columns are `commodity_name`, `category`, `inara_id`, `avg_sell`, `avg_buy`, `avg_profit`, `max_sell`, `min_buy`, and `max_profit`. Defaults include Palladium 71000, Gold 67000, Silver 49000.
- Source remains available in details/API but is not shown as a default table column.


## 0.1.15 notes

- The Web UI Commodities settings list is now populated from `commodity_global_stats`, which is refreshed from `rawdata/commodities.csv` on startup.
- This makes `rawdata/commodities.csv` / `commodity_global_stats` the authoritative commodity catalog for selectable watched commodities and Buy/Sell columns.
- If `commodity_global_stats` is empty, the UI falls back to commodities discovered in recorded market data.


## 0.1.17 notes

- Ledger trade events now snapshot the latest known station-side quantity at trade time.
- Buy rows show Supply under the commodity name.
- Sell rows show Demand under the commodity name.
- Existing historical trade rows will show blank supply/demand until new trades are recorded.

## 0.1.18 notes

- Adds a legacy commodity-name dedupe migration for `market_prices`.
- MarketScout now uses a canonical commodity key for matching and the `commodity_global_stats` / `rawdata/commodities.csv` catalogue for display names when possible.
- This prevents duplicate rows such as `Agronomic Treatment` and `Agronomictreatment` for the same market, and merges existing legacy duplicates by keeping the newest market snapshot.

## Engineer unlock data

- MarketScout imports `rawdata/engineers-unlock.csv` into `engineers_unlock` on startup when the file SHA-256 changes.
- The importer marks `is_rare_commodity` by matching required commodities against `rare_commodities`.

## Rare commodities view

- MarketScout imports `rawdata/commodities_rare.csv` into `rare_commodities` with source station/system, usual supply, buy price, and optional galactic average price.
- The Web UI has a `Rare Commodities` view with an engineering-only filter and fleet-carrier maximum sale profit estimate.

## System coordinate data

- MarketScout imports `rawdata/systems_data.csv` into `systems_data` on startup when the file SHA-256 changes.
- Journal events with `StarPos` also upsert coordinates into `systems_data`; the existing `systems` table remains for visited/candidate system records.

## Carrier Trade Announcements

- The Carrier Trade Announcements Web UI state is stored in browser localStorage, including form values, active page, uploaded image data URL when storage quota allows, and saved text layouts.
- Built-in text layouts are protected from overwrite; custom layouts can be saved, updated, selected, and deleted locally.
- The image generator is client-side only and does not upload images or announcements.


## 0.1.22 notes

0.1.22 improves the Web UI station identity display: system name is smaller/muted and station name is larger and accented, making multiple stations in the same system easier to distinguish.

## 0.2.0 Beta notes

0.2.0 is the first public beta release of MarketScout.

Highlights:

- The classic Tk UI has been removed; MarketScout is now focused on the local browser Web UI.
- Added Commodities, Rare Commodities, and Analyze Commodities views.
- Added rare commodity and engineer unlock imports, including engineering-only filtering and distance context where coordinate data is available.
- Added Carrier Trade Announcements with draggable image text, custom announcement templates, saved local layouts, and PNG/JPG downloads.
- Added fixed local web configuration with optional LAN access and QR-code sharing.
- Added Stations page quality-of-life improvements, including visited System/Station suggestions, Clear filters, watched commodity settings, and a Best Buy ignore list.
- Added release packaging support and bundled local rawdata imports for commodity stats, rare commodities, engineer unlocks, and relevant system coordinates.
