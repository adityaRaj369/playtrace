"""
Build the web app's data bundle from the raw parquet telemetry.

Reads every `*.nakama-0` parquet file under player_data/, decodes it with the
zero-dependency reader, and emits compact JSON that the React frontend loads:

  web/public/data/index.json         - all matches + summary stats + map config
  web/public/data/matches/<id>.json  - per-match player paths + events (playback)
  web/public/data/agg/<Map>.json     - per-map columnar event cloud (heatmaps/filters)

Also copies the minimap images into web/public/minimaps/.

Run:  python tools/build_dataset.py
No third-party dependencies required.
"""

import os
import json
import glob
import shutil
import datetime as dt
from collections import defaultdict

import parquet_reader as pr  # same tools/ dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "player_data")
OUT = os.path.join(ROOT, "web", "public", "data")
MINIMAP_OUT = os.path.join(ROOT, "web", "public", "minimaps")

DAYS = ["February_10", "February_11", "February_12", "February_13", "February_14"]

# From player_data/README.md "Map Configuration". Minimaps are 1024x1024.
MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "originX": -370, "originZ": -473,
                      "image": "AmbroseValley_Minimap.png", "size": 1024},
    "GrandRift":     {"scale": 581,  "originX": -290, "originZ": -290,
                      "image": "GrandRift_Minimap.png",     "size": 1024},
    "Lockdown":      {"scale": 1000, "originX": -500, "originZ": -500,
                      "image": "Lockdown_Minimap.jpg",      "size": 1024},
}

# Event type -> small integer code (used in the columnar aggregate)
EVENT_CODES = {
    "Position": 0, "BotPosition": 1, "Kill": 2, "Killed": 3,
    "BotKill": 4, "BotKilled": 5, "KilledByStorm": 6, "Loot": 7,
}
POSITION_EVENTS = {"Position", "BotPosition"}


def decode(v):
    return v.decode("utf-8") if isinstance(v, bytes) else v


def is_bot_uid(uid: str) -> bool:
    return uid.isdigit()


def main():
    os.makedirs(os.path.join(OUT, "matches"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "agg"), exist_ok=True)
    os.makedirs(MINIMAP_OUT, exist_ok=True)

    # match_id -> aggregated state
    matches = {}              # match_id -> {map, dates set, players {uid: {...}}}
    agg = defaultdict(lambda: {"e": [], "x": [], "z": [], "bot": [], "d": []})
    date_index = {d: i for i, d in enumerate(DAYS)}

    n_files = 0
    n_rows = 0
    for day in DAYS:
        folder = os.path.join(DATA_DIR, day)
        if not os.path.isdir(folder):
            continue
        for path in sorted(glob.glob(os.path.join(folder, "*.nakama-0"))):
            fname = os.path.basename(path)
            uid = fname.split("_")[0]
            bot = is_bot_uid(uid)
            try:
                cols = pr.read_parquet(path)
            except Exception as e:
                print("  !! failed", fname, e)
                continue
            n_files += 1
            nrows = len(cols["x"])
            n_rows += nrows
            mid = decode(cols["match_id"][0])
            mp = decode(cols["map_id"][0])

            m = matches.setdefault(mid, {"map": mp, "dates": set(), "players": {}})
            m["dates"].add(day)

            # rows for this player, sorted by ts
            rows = sorted(
                zip(cols["ts"], cols["x"], cols["z"],
                    [decode(e) for e in cols["event"]]),
                key=lambda r: r[0],
            )
            p = m["players"].setdefault(
                uid, {"bot": bot, "day": day, "min_ts": rows[0][0],
                      "path": [], "events": []})
            p["min_ts"] = min(p["min_ts"], rows[0][0])

            for ts, x, z, ev in rows:
                rx, rz = round(x, 1), round(z, 1)
                if ev in POSITION_EVENTS:
                    p["path"].append([ts, rx, rz])
                else:
                    p["events"].append([ts, rx, rz, ev])
                # aggregate event cloud for heatmaps
                a = agg[mp]
                a["e"].append(EVENT_CODES.get(ev, -1))
                a["x"].append(rx)
                a["z"].append(rz)
                a["bot"].append(1 if bot else 0)
                a["d"].append(date_index[day])

    # ---- write per-match detail + build index ----
    index_matches = []
    for mid, m in matches.items():
        match_min = min(p["min_ts"] for p in m["players"].values())
        players_out = []
        counts = defaultdict(int)
        n_humans = n_bots = 0
        max_t = 0
        for uid, p in m["players"].items():
            if p["bot"]:
                n_bots += 1
            else:
                n_humans += 1
            path = [[int(ts - match_min), x, z] for ts, x, z in p["path"]]
            events = [[int(ts - match_min), x, z, ev] for ts, x, z, ev in p["events"]]
            for _, _, _, ev in p["events"]:
                counts[ev] += 1
            counts["__pos__"] += len(path)
            if path:
                max_t = max(max_t, path[-1][0])
            if events:
                max_t = max(max_t, events[-1][0])
            players_out.append({"id": uid, "bot": p["bot"],
                                "path": path, "events": events})

        date = sorted(m["dates"])[0]
        with open(os.path.join(OUT, "matches", mid + ".json"), "w") as f:
            json.dump({"matchId": mid, "map": m["map"], "date": date,
                       "duration": max_t, "players": players_out}, f,
                      separators=(",", ":"))

        index_matches.append({
            "matchId": mid,
            "map": m["map"],
            "date": date,
            "duration": max_t,
            "humans": n_humans,
            "bots": n_bots,
            "kills": counts.get("Kill", 0) + counts.get("BotKill", 0),
            "deaths": counts.get("Killed", 0) + counts.get("BotKilled", 0),
            "stormDeaths": counts.get("KilledByStorm", 0),
            "loot": counts.get("Loot", 0),
        })

    index_matches.sort(key=lambda r: (r["map"], r["date"], r["matchId"]))

    summary = {
        "files": n_files,
        "rows": n_rows,
        "matches": len(index_matches),
        "maps": {mp: sum(1 for r in index_matches if r["map"] == mp)
                 for mp in MAP_CONFIG},
    }

    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump({
            "generatedAt": dt.datetime.utcnow().isoformat() + "Z",
            "mapConfig": MAP_CONFIG,
            "eventCodes": EVENT_CODES,
            "days": DAYS,
            "summary": summary,
            "matches": index_matches,
        }, f, separators=(",", ":"))

    # ---- write per-map aggregate clouds ----
    for mp, a in agg.items():
        with open(os.path.join(OUT, "agg", mp + ".json"), "w") as f:
            json.dump({"map": mp, "days": DAYS,
                       "eventCodes": EVENT_CODES, **a},
                      f, separators=(",", ":"))

    # ---- copy minimaps ----
    for mp, cfg in MAP_CONFIG.items():
        src = os.path.join(DATA_DIR, "minimaps", cfg["image"])
        if os.path.exists(src):
            shutil.copy(src, os.path.join(MINIMAP_OUT, cfg["image"]))

    print(f"Done. {n_files} files, {n_rows} rows, {len(index_matches)} matches.")
    print(f"Summary: {summary}")


if __name__ == "__main__":
    main()
