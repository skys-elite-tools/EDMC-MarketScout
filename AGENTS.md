# AGENTS.md

## Project
EDMC-MarketScout is a local-only EDMarketConnector plugin for scouting Elite Dangerous market opportunities.

## Non-negotiable privacy rules
- Do not add network uploads, telemetry, scraping, or third-party reporting.
- The local web UI must bind only to 127.0.0.1 unless explicitly changed by the maintainer.
- Do not leak station, market, commander, journal, or route data.
- Optional future integrations such as Discord webhooks must be opt-in and clearly isolated.

## Repo layout
- `EDMC-MarketScout/load.py`: EDMC plugin entry point and core journal/CAPI handling.
- `EDMC-MarketScout/marketscout_web.py`: local HTTP API and static web server.
- `EDMC-MarketScout/marketscout_ledger.py`: trade ledger.
- `EDMC-MarketScout/marketscout_importer.py`: SHA-256-gated rawdata CSV imports.
- `EDMC-MarketScout/rawdata/`: release-bundled CSV inputs for commodities, rare commodities, engineers, and systems data.
- `EDMC-MarketScout/web-src/`: Vue 3 + Vite source.
- `EDMC-MarketScout/web/`: prebuilt static web UI served at runtime.
- `local-tools/`: maintainer parsers/generators for rawdata files; these are not runtime tools.
- `PROJECT_NOTES.md`: architecture notes and project decisions.
- `DEVELOPERS.md`: developer/build notes.

## Runtime/build rules
- End users must not need Node/npm.
- If changing `web-src/`, run `npm run build` and include the updated `web/` output.
- Do not commit `node_modules/`, runtime SQLite databases, logs, or local UI/preset JSON files.
- The classic Tk MarketScout window was intentionally removed for the beta; keep new UI work in the Web UI.
- `marketscout.config` is runtime-local and should not be committed. Defaults are loopback-only plus an optional user-enabled LAN listener.
- Keep rawdata imports deterministic and local. Large external dumps, such as Spansh JSON, must be streamed by maintainer tools and reduced to small CSVs before release.

## Verification
After Python changes:
`python3 -m py_compile EDMC-MarketScout/load.py EDMC-MarketScout/marketscout_web.py EDMC-MarketScout/marketscout_ledger.py EDMC-MarketScout/marketscout_importer.py`

After frontend changes:
`cd EDMC-MarketScout/web-src && npm run build`

## UX conventions
- Keep the Web UI modular Vue components.
- Keep filters simple for general users.
- Prefer visible highlights over extra sort-mode toggles.
- Default Stations sort is newest `market_updated`, then newest `station_visit`, then best buy score, then system/station.
- The Stations page has typeahead text filters for visited systems/stations, a Clear action that restores default station filters, watched commodity settings, and a Best Buy ignore list.
- Carrier Trade Announcements is browser-only: drafts, uploaded images, and custom text layouts live in localStorage.

## Handoff
- Make small, focused commits.
- Summarize changed files and tests run.
- Prefer patches for handoff/review.
