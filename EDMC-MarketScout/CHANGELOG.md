# Changelog

## Unreleased

- Added a read-only top status bar indicator for EDMC's EDDN station-data setting.

## 0.2.8 Beta

- Fixed Stations auto-refresh after live station/market updates by using an explicit Web UI data-version signal instead of relying only on SQLite database file modification time.
- Fixed Stations watched Buy and Best Buy displays so commodities with zero supply are not treated as available buy opportunities; watched Buy cells now show zero supply as low/empty stock instead of green.

## 0.2.7 Beta

- Refactored Carrier Trade Announcements into focused components for the form, poster editor, announcement outputs, and template editor.
- Renamed the view source file from `CarrierTradeAlertView.vue` to `CarrierTradeAnnouncementsView.vue`.
- Moved page-level Web UI screens into `web-src/src/views/`, keeping reusable and child UI pieces in `web-src/src/components/`.
- Extracted shared `MetricCard.vue`, `ModalShell.vue`, and `CopyablePanel.vue` UI components.
- Fixed Carrier Trade Announcements image export so poster text capitalization and spacing better match the Web preview.

## 0.2.6 Beta

- Improved the Carrier Trade Calculator's `Rare Commodities: Station to Station` section for Community Goal style rare trading.
- Target stations now list visited stations that have at least one commodity with a positive sell price, ordered by most recent station visit first.
- Renamed station-trade price labels so buy/sell wording is consistently from the player's perspective.
- Replaced the single Origin Stock input with supply source buttons: Usual, Most Recent, and Custom.
- Added browser-local custom rare commodity supply overrides.
- Added Ship Cargo Capacity and changed `Agg. Profit/Trip` to estimate aggregated profit per ship trip using carrier capacity, origin supply, and load/unload trip counts.
- Hardened the rare station-trade options endpoint against SQLite temporary I/O errors by using in-memory temp storage and Python-side sorting.
- Updated rare commodity `usual_supply` values from the master allocation source where available.
- Refactored the Carrier Trade Calculator into separate tab components and extracted a reusable autocomplete/dropdown component.

## 0.2.5 Beta

- Refactored database migrations into dedicated migration files with a `schema_migrations` table, plus a developer helper for creating new migrations.
- Extracted the changelog into this standalone `CHANGELOG.md` file.
- Improved Carrier Trade Announcements custom templates so Loading and Unloading trades can have separate saved title/body templates.
- The Custom Announcement output and editor now show an accented `Carrier Loading Template` or `Carrier Unloading Template` label.

## 0.2.4 Beta

- Added the GitHub release update checker and one-click updater.
- The Web UI shows a prominent update button when a newer release is available.
- Automatic updates download the release zip, create a backup in `EDMC-MarketScout-backups.disabled/`, apply the new plugin files, and ask the user to restart EDMC.

## 0.2.3 Beta

0.2.3 adds the Carrier Trade Calculator and groups carrier-focused tools under a new `Carrier Tools` top navigation menu. The calculator includes station-to-station trade splitting and rare commodity carrier sale calculations with live carrier/hauler profit outputs.

## 0.2.2 Beta

0.2.2 improves the Carrier Trade Announcements text color control by replacing the browser-native color picker with a bundled Coloris picker. This gives commanders a full color selector with swatches and hex entry while avoiding viewport clipping near the right edge of the page.

## 0.2.1 Beta

0.2.1 fixes a Web UI view-switching bug where rows from a previously opened table, especially Ledger rows, could briefly leak into another table view such as Commodities. Table loads now clear stale rows immediately and ignore late responses from older view requests.

## 0.2.0 Beta

0.2.0 is the first public beta release of MarketScout.

Highlights:

- The classic Tk UI has been removed; MarketScout is now focused on the local browser Web UI.
- Added Commodities, Rare Commodities, and Analyze Commodities views.
- Added rare commodity and engineer unlock imports, including engineering-only filtering and distance context where coordinate data is available.
- Added Carrier Trade Announcements with draggable image text, custom announcement templates, saved local layouts, and PNG/JPG downloads.
- Added fixed local web configuration with optional LAN access and QR-code sharing.
- Added Stations page quality-of-life improvements, including visited System/Station suggestions, Clear filters, watched commodity settings, and a Best Buy ignore list.
- Added release packaging support and bundled local rawdata imports for commodity stats, rare commodities, engineer unlocks, and relevant system coordinates.

Additional feature notes:

- MarketScout imports `rawdata/engineers-unlock.csv` into `engineers_unlock` on startup when the file SHA-256 changes.
- The importer marks `is_rare_commodity` by matching required commodities against `rare_commodities`.
- MarketScout imports `rawdata/commodities_rare.csv` into `rare_commodities` with source station/system, usual supply, buy price, and optional galactic average price.
- The Web UI has a `Rare Commodities` view with an engineering-only filter and fleet-carrier maximum sale profit estimate.
- MarketScout imports `rawdata/systems_data.csv` into `systems_data` on startup when the file SHA-256 changes.
- Journal events with `StarPos` also upsert coordinates into `systems_data`; the existing `systems` table remains for visited/candidate system records.
- The Carrier Trade Announcements Web UI state is stored in browser localStorage, including form values, active page, uploaded image data URL when storage quota allows, and saved text layouts.
- Built-in text layouts are protected from overwrite; custom layouts can be saved, updated, selected, and deleted locally.
- The image generator is client-side only and does not upload images or announcements.

## 0.1.22

0.1.22 improves the Web UI station identity display: system name is smaller/muted and station name is larger and accented, making multiple stations in the same system easier to distinguish.

## 0.1.18

- Adds a legacy commodity-name dedupe migration for `market_prices`.
- MarketScout now uses a canonical commodity key for matching and the `commodity_global_stats` / `rawdata/commodities.csv` catalogue for display names when possible.
- This prevents duplicate rows such as `Agronomic Treatment` and `Agronomictreatment` for the same market, and merges existing legacy duplicates by keeping the newest market snapshot.

## 0.1.17

- Ledger trade events now snapshot the latest known station-side quantity at trade time.
- Buy rows show Supply under the commodity name.
- Sell rows show Demand under the commodity name.
- Existing historical trade rows will show blank supply/demand until new trades are recorded.

## 0.1.15

- The Web UI Commodities settings list is now populated from `commodity_global_stats`, which is refreshed from `rawdata/commodities.csv` on startup.
- This makes `rawdata/commodities.csv` / `commodity_global_stats` the authoritative commodity catalog for selectable watched commodities and Buy/Sell columns.
- If `commodity_global_stats` is empty, the UI falls back to commodities discovered in recorded market data.

## 0.1.14

- MarketScout now stores all commodities seen in market data, not just the original metals.
- The Web UI has a Commodities settings panel. Watched commodities affect highlighting/details, while Buy/Sell table columns can be selected separately.
- Added `commodity_global_stats` and Best Buy scoring. On startup, MarketScout looks for `rawdata/commodities.csv` in the plugin folder and refreshes stats when the file SHA-256 differs from the last imported hash. Current catalog columns are `commodity_name`, `category`, `inara_id`, `avg_sell`, `avg_buy`, `avg_profit`, `max_sell`, `min_buy`, and `max_profit`. Defaults include Palladium 71000, Gold 67000, Silver 49000.
- Source remains available in details/API but is not shown as a default table column.

## 0.1.13

- Fixed commodity normalization so rare commodities like Sothis Crystalline Gold no longer overwrite normal Gold market rows.
- Normal commodity matching now requires exact commodity symbols after Frontier localization cleanup.

## 0.1.11

- Changed Ledger credits/hour to use sale cadence: if a previous sell exists within 60 minutes, credits/hour is current sale profit scaled by elapsed time between the two sell events.
- LIFO profit/hour remains available as optional LIFO/statistics detail.

## 0.1.8

0.1.8 adds event-driven jackpot history tracking. When fresh market data is recorded, MarketScout checks Palladium, Gold, and Silver against the current highlight thresholds. If any metal has buy price at or below the price threshold and supply at or above the supply threshold, a static jackpot event is created with the system/station/BGS/economy context, and a time-series sample is stored. Additional samples are added only when fresh market data arrives and at least `JACKPOT_SAMPLE_INTERVAL_MINUTES` has elapsed since the previous sample. The default interval is 30 minutes and is easy to change near the top of `marketscout_app.py`.

No background timer is used. No data is uploaded.

Jackpot data is stored in:

- `jackpot_events`: static context at detection time.
- `jackpot_samples`: timestamped Palladium/Gold/Silver buy price and supply snapshots.

The Web UI includes a `Jackpot History` button that displays the stored samples.

## 0.1.6

0.1.6 fixes false cheap-row highlighting by ignoring zero/unavailable buy prices and limiting highlight checks to the primary scouting metals: Palladium, Gold, and Silver. It also changes the default metal column order to Palladium, Gold, Silver; adds compact two-line columns such as `Palladium Buy` showing buy price above supply; and adds compact location display with system above station/pad.

## 0.1.5

0.1.5 adds targeted market-data debugging and a local `Market.json` fallback. When EDMC calls `cmdr_data()`, MarketScout writes a concise payload summary to `marketscout-market-debug.log`. When a Journal `Market` event arrives, MarketScout also tries to read the game's local `Market.json` from EDMC's configured Journal directory and stores only the configured tracked commodities.

If market prices are still not stored, open the commodity market once, then inspect `marketscout-market-debug.log` and `marketscout-error.log` in the plugin folder.

## 0.1.4

- Added Spansh CSV candidate import, source/source-pulled metadata, optional sell/demand columns, Fleet Carrier flag/filter, and more robust CAPI marketdata parsing.
- Spansh CSV import supports the richer station-search export columns, including station type, pad counts, planetary flag, source update timestamps, market source timestamp, system primary/secondary economy, station secondary economy, carrier name/access fields, and marketplace where present.
- No scraping or network access is used.

## 0.1.2

- Added configurable cheap-metal row highlighting and a Flag column.

## 0.1.1

- Added a selectable column chooser and remembers visible columns in `marketscout-ui.json`.

## 0.1.0

- Initial prototype.
