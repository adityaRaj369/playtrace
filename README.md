# LILA BLACK Player Journey Visualizer

Browser-based visualization tool for LILA BLACK gameplay telemetry. It lets a level designer inspect real player and bot movement, combat, loot, storm deaths, and map traffic directly on the provided minimaps.

## Live Demo

Live app: https://playtrace-gules.vercel.app/

The app is fully static after build. It does not need a backend server in production.

## What This Tool Does

- Loads and parses the provided `.nakama-0` Parquet telemetry files.
- Reconstructs matches by grouping files with the same `match_id`.
- Renders player and bot paths on the correct minimap.
- Maps world `(x, z)` coordinates to minimap pixels using the dataset README's scale/origin formula.
- Distinguishes humans and bots visually.
- Shows `Kill`, `Killed`, `BotKill`, `BotKilled`, `KilledByStorm`, and `Loot` as distinct map markers.
- Filters by map, date, match, and player type.
- Plays a match timeline over time with scrub, restart, speed, and replay-from-end behavior.
- Displays heatmaps for traffic, human traffic, kill zones, death zones, storm deaths, and loot.
- Includes three level-design insights with supporting evidence in `INSIGHTS.md`.

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite |
| Rendering | HTML Canvas |
| Data preprocessing | Python |
| Parquet parsing | Custom zero-dependency reader in `tools/parquet_reader.py` |
| Runtime data | Static JSON in `web/public/data` |
| Deployment | GitHub Pages workflow included; Vercel/Netlify also work |

## Project Structure

```text
GameDataVisualizer/
├── README.md
├── ARCHITECTURE.md
├── INSIGHTS.md
├── package.json                  # one-command setup/test/build scripts
├── player_data/                 # raw assignment data kept in repo
│   ├── February_10/
│   ├── February_11/
│   ├── February_12/
│   ├── February_13/
│   ├── February_14/
│   ├── minimaps/
│   └── README.md
├── tools/
│   ├── parquet_reader.py         # reads the raw Parquet subset used by this dataset
│   ├── build_dataset.py          # raw player_data -> web/public/data
│   └── verify_project.py         # repo readiness + data/docs checks
└── web/
    ├── public/
    │   ├── data/                 # generated JSON consumed by the app
    │   └── minimaps/             # generated/copied minimap assets
    ├── src/
    │   ├── components/
    │   └── lib/
    ├── package.json
    └── vite.config.js
```

## Data Included

The repo contains the raw assignment dataset and the generated static app data.

- Raw Parquet files: `1,243`
- Event rows: `89,104`
- Matches: `796`
- Maps: `AmbroseValley`, `GrandRift`, `Lockdown`
- Date range: February 10–14, 2026

The deployed app reads from `web/public/data` and `web/public/minimaps`, so production hosting does not need Python or Parquet parsing.

## Setup

```bash
cd "/Users/aditya/personal Project/GameDataVisualizer"
npm run setup
npm --prefix web run dev
```

Open the local URL printed by Vite, usually `http://127.0.0.1:5173/` or `http://127.0.0.1:5174/`.

## Regenerate Data

Run this from the repository root:

```bash
python3 tools/build_dataset.py
```

This reads `player_data/`, writes JSON into `web/public/data`, and copies minimaps into `web/public/minimaps`.

No Python packages are required.

## Test and Build

```bash
cd "/Users/aditya/personal Project/GameDataVisualizer"
npm run verify
```

`npm run verify` runs one terminal command that prints pass/fail status for:

- repository readiness checks in `tools/verify_project.py`
- frontend unit tests
- production build

The frontend tests cover:

- coordinate conversion against the dataset README example
- heatmap filtering by metric/date/player type
- audience match selection for All/Humans/Bots
- map/date match filtering and selected-match fallback
- playback replay behavior after a timeline finishes

## Walkthrough

1. Choose **Single match** to inspect one match.
2. Pick a map and date.
3. Select a match from the dropdown. The label shows humans, bots, and kill count.
4. Use **All / Humans / Bots** to switch player visibility. If the current match does not contain the selected audience, the app jumps to a compatible match when one exists.
5. Toggle path, player, and event layers from the left panel.
6. Use the timeline to scrub or play the match progression.
7. Switch to **Heatmap** to inspect traffic, kill zones, death zones, storm deaths, or loot.
8. Read `INSIGHTS.md` for three actionable observations found using the tool.

## Deployment

### GitHub Pages

1. Push this folder as a GitHub repository.
2. In GitHub, open **Settings → Pages**.
3. Set **Source** to **GitHub Actions**.
4. Push to `main`; `.github/workflows/deploy.yml` builds `web/` and publishes `web/dist`.

### Vercel or Netlify

- Project root/base directory: `web`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variables: none

## Notes

- Humans are detected by UUID-like `user_id`; bots are detected by numeric `user_id`.
- `event` values are decoded from bytes during preprocessing.
- The app uses `x` and `z` for 2D plotting. The dataset's `y` field is elevation and is not used for minimap placement.
- Raw data is included so reviewers can inspect or regenerate the processed JSON.
