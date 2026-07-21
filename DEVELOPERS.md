# EDMC-MarketScout developer notes

EDMC-MarketScout is an EDMC plugin with a Python backend and a prebuilt browser UI.

End users do **not** need Node.js, npm, Vite, or Vue. Releases include a ready-to-go `EDMC-MarketScout/web/` directory that EDMC serves through the plugin's local web server.

## Repository layout

```text
EDMC-MarketScout/
  load.py                    # Thin EDMC plugin adapter
  marketscout_app.py         # Core plugin lifecycle and journal/CAPI orchestration
  marketscout_migrations.py  # SQLite migration runner
  migrations/                # Python schema migration files
  marketscout_importer.py    # CSV/import logic
  marketscout_ledger.py      # trade ledger logic
  marketscout_web.py         # local web server + JSON API
  rawdata/commodities.csv    # commodity stats catalog used at startup
  rawdata/commodities_rare.csv
  rawdata/engineers-unlock.csv
  rawdata/systems_data.csv
  web/                       # compiled Web UI served at runtime; include in releases
  web-src/                   # Vue 3 + Vite source for the Web UI
```

## Runtime requirements for users

Users only need EDMC and the files in `EDMC-MarketScout/`. The Web UI is served from the already-built `web/` directory.

Do not make EDMC runtime depend on Node/npm or network-hosted JavaScript libraries.

## Web UI development

The Web UI source lives in `EDMC-MarketScout/web-src/` and is built with Vue 3 + Vite.

Install frontend dependencies once:

```bash
cd EDMC-MarketScout/web-src
npm install
```

Run a Vite development server while editing the frontend:

```bash
npm run dev
```

The Vite dev server is only for frontend development. It will not replace EDMC's API server. For API-backed testing, run EDMC/MarketScout normally and use the built plugin Web UI, or point requests at the EDMC local server as needed.

Build the ready-to-ship frontend:

```bash
cd EDMC-MarketScout/web-src
npm run build
```

The build output is written to:

```text
EDMC-MarketScout/web/
```

Commit both the source changes in `web-src/` and the compiled `web/` output so users get a ready-to-go plugin.

Current top-level Web UI views are:

- Stations
- Jackpots
- Ledger
- Commodities
- Rare Commodities
- Analyze Commodities
- Carrier Trade Announcements
- Carrier Trade Calculator
- Config

Browser-only personal state uses localStorage for convenience, including the active view, Analyze Commodities pasted input, Carrier Trade Announcements drafts/custom text layouts, and Carrier Trade Calculator inputs.

The Web UI has a responsive top navigation. Commodities, Rare Commodities, and Analyze Commodities are grouped under the Commodities menu on wider layouts; the navigation collapses to a hamburger menu on narrower windows. The footer provides About and Help modals.

## Python backend development

The local Web UI API is implemented in `marketscout_web.py`. It starts with a loopback listener and can optionally start a separate LAN listener when enabled in runtime configuration.

The runtime config file is `marketscout.config` in the plugin folder. It is created on startup if missing, ignored by git, and defaults to:

```ini
app.bind_address=127.0.0.1
app.bind_port=40595
app.lan_enabled=0
app.lan_bind_address=
```

The Web UI Config page edits the loopback address, shared port, and optional LAN address. Address/port changes require restarting EDMC. QR-code sharing appears only for enabled non-loopback LAN IPv4 addresses.

Important privacy rule: MarketScout itself must not upload data to EDDN, Inara, EDSM, Discord, or any other remote service unless an explicit opt-in feature is added later. The update checker may read GitHub release metadata and download a release zip after the user clicks update, but it must not include commander, journal, route, station, or market data in those requests. Current Web UI assets must be bundled locally; no CDN scripts/styles.

## Database migrations

Schema migrations live in `EDMC-MarketScout/migrations/` and are run by `marketscout_migrations.py` during plugin startup. Applied migrations are recorded in the local SQLite `schema_migrations` table, so each migration runs once per database.

Migration files are Python files so they can use SQLite safety checks and small data transforms when needed. Use this shape:

```python
MIGRATION_ID = "0002_short_name"
DESCRIPTION = "Short human-readable description"

def apply(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS ...")
```

Use a zero-padded numeric prefix and keep migration ids stable forever. Migrations should be forward-only and safe for real user databases. Do not put schema DDL in `marketscout_app.py`, `commodities_importer.py`, or feature modules.

To create the next migration stub:

```bash
tools/create-migration "add carrier bookmarks"
```

This creates the next numbered file in `EDMC-MarketScout/migrations/` with matching `MIGRATION_ID` and `DESCRIPTION` values.

Useful Web API areas:

- `/api/status`: status strip data, latest Journal metadata, and database version.
- `/api/stations`: Stations table data, watched columns, Best Buy calculations, and filters.
- `/api/station-filter-options`: visited system/station suggestions for Stations filters.
- `/api/jackpots`, `/api/ledger`, `/api/rare-commodities`, `/api/commodity-stats`: view data.
- `/api/analyze-commodities`: splits pasted commodity lists into regular and rare matches.
- `/api/commodities`, `/api/settings`, `/api/economy-presets`, `/api/config`: catalogs/settings/config helpers.

## Local testing checklist

After backend or Web UI changes:

1. Install/replace the plugin folder in EDMC's plugin directory.
2. Restart EDMC.
3. Click `MarketScout` in the EDMC plugin button row.
4. Verify the browser UI loads from `http://127.0.0.1:<port>/`.
5. Check these views:
   - Stations
   - Stations System/Station typeahead suggestions and Clear filters
   - Jackpots
   - Ledger
   - Commodities
   - Rare Commodities
   - Analyze Commodities
   - Carrier Trade Announcements
   - Config
   - Commodities settings
   - Best Buy ignore list
6. If market data is involved, dock/open a market or use a known `Market.json` test case.

For Carrier Trade Announcements changes, verify:

- form edits update the image text and announcement text
- uploaded image preview persists after refresh when localStorage quota allows
- text layers can be dragged
- custom layouts can be saved, updated, selected, deleted, and closed by clicking outside the menu
- PNG/JPG downloads render the visible text layout

For rawdata/import changes, run the relevant parser under `local-tools/`, then restart MarketScout or run importer-oriented checks against a disposable database. Large Spansh JSON dumps must be streamed rather than loaded into memory.

## Packaging

Before packaging, make sure the frontend is built:

```bash
cd EDMC-MarketScout/web-src
npm run build
```

Then create a zip that includes `web/` and `web-src/`, but excludes development/runtime clutter such as:

```text
node_modules/
__pycache__/
*.pyc
*.log
marketscout.sqlite3
marketscout.config
marketscout-ui.json
marketscout-economy-presets.json
```

The repo's `.gitignore` should keep those files out of commits.

Rawdata CSV files under `EDMC-MarketScout/rawdata/` are release inputs and should be included. Maintainer-only source data under `local-*` directories is local scratch/input material and should not be required by end users.

## Local release helper

The repo includes a maintainer convenience script:

```bash
tools/local-release
```

It reads local paths from `.env`, builds `EDMC-MarketScout/web-src`, backs up the currently installed plugin if present, and rsyncs `EDMC-MarketScout/` into the configured EDMC plugins directory. Copy `.env.example` to `.env` and fill in:

```ini
EDMC_PLUGINS_DIR=
PLUGIN_BACKUP_ARCHIVES_DIR=
```

`.env` is intentionally ignored because it contains machine-local paths.

## GitHub releases

GitHub Actions builds and publishes a release automatically when a tag with the canonical release shape is pushed:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow accepts only tags matching `vMAJOR.MINOR.PATCH`, such as `v0.1.0`. Semantic Versioning itself is `MAJOR.MINOR.PATCH`; the leading `v` is the common Git tag convention used by this project.

The release workflow builds the Web UI, runs the Python syntax check, packages only the installable `EDMC-MarketScout/` plugin folder, and attaches `EDMC-MarketScout-vX.Y.Z.zip` to the GitHub Release.

## Git workflow

Recommended baseline workflow:

```bash
git status
git add .
git commit -m "Describe the MarketScout change"
```

For sharing manual edits, either send the full repo zip or a patch:

```bash
git diff > my-edits.patch
```

For changes that should be a commit patch:

```bash
git format-patch -1 HEAD
```
