# Architecture

## What I Built

A static React + Vite web app that visualizes LILA BLACK player journeys on the provided minimaps. The frontend is backed by a Python preprocessing pipeline that converts the raw `.nakama-0` Parquet files into compact JSON files served from `web/public/data`.

## Why This Stack

| Area | Choice | Why |
|---|---|---|
| Frontend | React + Vite | Fast to build, easy to deploy, good fit for stateful filters/playback. |
| Rendering | Canvas 2D | Handles paths, markers, and heatmaps efficiently without thousands of DOM nodes. |
| Data pipeline | Python | Best fit for parsing and reshaping telemetry. |
| Parquet reader | Custom stdlib reader | Keeps regeneration dependency-free; no `pyarrow` or backend required. |
| Hosting | Static site | The tool can run on GitHub Pages, Vercel, or Netlify with no server. |

## Data Flow

```text
player_data/February_*/*.nakama-0
  -> tools/parquet_reader.py
  -> tools/build_dataset.py
  -> web/public/data/index.json
  -> web/public/data/matches/<match_id>.json
  -> web/public/data/agg/<map>.json
  -> React app fetches JSON
  -> Canvas renders minimap, paths, markers, timeline, and heatmaps
```

The raw dataset remains in `player_data/` so reviewers can inspect it or regenerate the processed data. The deployed app only needs the generated JSON and minimap files in `web/public`.

## Coordinate Mapping

The dataset gives world coordinates as `(x, y, z)`. For 2D minimap plotting, only `x` and `z` are used. `y` is elevation.

Each map has `scale`, `originX`, and `originZ` from the dataset README.

```text
u = (x - originX) / scale
v = (z - originZ) / scale
pixelX = u * 1024
pixelY = (1 - v) * 1024
```

The `1 - v` flip is required because image coordinates start at the top-left. This mapping is implemented in `web/src/lib/coords.js` and tested against the README's Ambrose Valley example.

## Runtime Model

- `index.json` loads first and provides map config, summary stats, and match metadata.
- Selecting a match lazy-loads `matches/<match_id>.json`.
- Heatmap mode lazy-loads `agg/<map>.json`.
- Match playback uses match-relative time: `event_ts - match_start_ts`.
- Player type filters use `bot: true/false` generated during preprocessing.

## Assumptions

- Human players have UUID-like `user_id`; bots have numeric `user_id`.
- `Position` and `BotPosition` events form movement paths.
- `Kill`, `Killed`, `BotKill`, `BotKilled`, `KilledByStorm`, and `Loot` are discrete markers.
- Date comes from the source folder name, e.g. `February_10`.
- Some selected matches contain only humans or only bots. When the user selects Humans/Bots, the app switches to a compatible match if one exists for the current map/date filter.

## Tradeoffs

| Decision | Tradeoff |
|---|---|
| Precompute JSON instead of reading Parquet in-browser | Simpler deployment and faster UI, but data must be regenerated after raw data changes. |
| Canvas instead of SVG | Faster rendering for dense paths/heatmaps, but marker hover interactions are harder. |
| Custom Parquet reader | More code to own, but the repo works without Python package installs. |
| Static hosting | No backend cost or ops, but no live querying beyond generated views. |
