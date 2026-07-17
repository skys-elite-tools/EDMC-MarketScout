# EDMC-MarketScout developer notes

EDMC-MarketScout is an EDMC plugin with a Python backend and a prebuilt browser UI.

End users do **not** need Node.js, npm, Vite, or Vue. Releases include a ready-to-go `EDMC-MarketScout/web/` directory that EDMC serves through the plugin's local web server.

## Repository layout

```text
EDMC-MarketScout/
  load.py                    # EDMC plugin entry point and core recorder logic
  marketscout_importer.py    # CSV/import logic
  marketscout_ledger.py      # trade ledger logic
  marketscout_web.py         # local 127.0.0.1 web server + JSON API
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
- Carrier Trade Alert

Browser-only personal state uses localStorage for convenience, including the active view, Analyze Commodities pasted input, and Carrier Trade Alert drafts/custom text layouts.

## Python backend development

The local Web UI API is implemented in `marketscout_web.py`. It binds to `127.0.0.1` only and should remain local-only.

Important privacy rule: MarketScout itself must not upload data to EDDN, Inara, EDSM, Discord, or any other remote service unless an explicit opt-in feature is added later. Current Web UI assets must be bundled locally; no CDN scripts/styles.

## Local testing checklist

After backend or Web UI changes:

1. Install/replace the plugin folder in EDMC's plugin directory.
2. Restart EDMC.
3. Click `Web` in the EDMC MarketScout button row.
4. Verify the browser UI loads from `http://127.0.0.1:<port>/`.
5. Check these views:
   - Stations
   - Jackpots
   - Ledger
   - Commodities
   - Rare Commodities
   - Analyze Commodities
   - Carrier Trade Alert
   - Commodities settings
   - Best Buy ignore list
6. If market data is involved, dock/open a market or use a known `Market.json` test case.

For Carrier Trade Alert changes, verify:

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
```

The repo's `.gitignore` should keep those files out of commits.

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
