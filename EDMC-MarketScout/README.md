# EDMC-MarketScout

Local-only EDMarketConnector plugin for scouting station market/BGS conditions, commodity prices, rare commodities, engineer unlocks, trade ledger entries, and Fleet Carrier trade announcements.

## What it does

- Adds one small `MarketScout` button to EDMC's main window.
- Records system visits from Journal events.
- Records station visits from Journal events.
- Stores commodity market prices from EDMC CAPI data when available, with a local `Market.json` fallback.
- Stores everything locally in `marketscout.sqlite3` inside the plugin folder.
- Opens a local browser Web UI served from `127.0.0.1`.
- Shows Stations, Jackpots, Ledger, Commodities, Rare Commodities, Analyze Commodities, Carrier Trade Announcements, and Carrier Trade Calculator views.
- Supports watched commodity columns and a Best Buy ignore list.
- Imports candidate stations from supported CSV exports, currently Spansh station-search CSVs.
- Imports maintained rawdata CSV files for commodity stats, rare commodities, engineer unlock requirements, and relevant system coordinates.
- Tracks row/source metadata such as `local_visit` or `spansh`.
- Can hide Fleet Carrier rows by default with an `Include fleet carriers` checkbox.
- Provides a local Fleet Carrier trade announcement image/text generator with downloadable PNG/JPG output.
- Checks GitHub releases for MarketScout updates and can download/apply a release zip after the user clicks the update button.

## Privacy

MarketScout does not upload commander, journal, route, station, or market data. It writes gameplay data to a local SQLite database and serves bundled Web UI assets on `127.0.0.1` by default.

The only built-in external network feature is the update checker. On startup it checks the public GitHub release metadata for `skys-elite-tools/EDMC-MarketScout`; if the user clicks the update button, it downloads the release zip from GitHub. This sends a normal HTTPS request to GitHub, but no MarketScout database or game data is included.

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

## Updates

MarketScout checks the latest GitHub release tag on startup. When a newer release is available, the Web UI status bar shows an update button.

If the release includes the standard installable zip, clicking the button downloads it, backs up the current plugin folder to a sibling `EDMC-MarketScout-backups.disabled/` directory, copies the new `EDMC-MarketScout/` files over the current plugin files, and then asks you to restart EDMC. If automatic updating fails, MarketScout shows the backup path so you can manually restore the previous working plugin folder.

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
- `Carrier Trade Calculator`: calculate Fleet Carrier buy/sell prices and profit splits for station-to-station trades and rare commodity trading.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Notes / limitations

- Largest pad is inferred from station type when no explicit field is available.
- Station faction state is read from the Journal if available; if Frontier/EDMC omits it for a specific event, it may remain blank until a later event provides it.
- Market prices are stored for all captured commodities.
- Candidate imports from Spansh have no market prices until you actually visit/update the station.
- No route planner yet.

