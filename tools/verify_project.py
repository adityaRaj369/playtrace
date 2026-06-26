#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DAYS = ["February_10", "February_11", "February_12", "February_13", "February_14"]
EXPECTED_MAPS = {"AmbroseValley", "GrandRift", "Lockdown"}
EVENT_CODES_REQUIRED = set(range(8))


class Verifier:
    def __init__(self):
        self.failures = []
        self.warnings = []

    def pass_(self, message):
        print(f"PASS  {message}")

    def fail(self, message):
        self.failures.append(message)
        print(f"FAIL  {message}")

    def warn(self, message):
        self.warnings.append(message)
        print(f"WARN  {message}")

    def check(self, condition, message):
        if condition:
            self.pass_(message)
        else:
            self.fail(message)


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def read_text(path):
    return path.read_text(encoding="utf-8")


def verify_docs(v):
    for name in ["README.md", "ARCHITECTURE.md", "INSIGHTS.md"]:
        v.check((ROOT / name).is_file(), f"{name} exists")

    readme = read_text(ROOT / "README.md")
    architecture = read_text(ROOT / "ARCHITECTURE.md")
    insights = read_text(ROOT / "INSIGHTS.md")

    for phrase in ["Tech Stack", "Setup", "Test and Build", "Deployment", "Regenerate Data"]:
        v.check(phrase in readme, f"README documents {phrase}")

    for phrase in ["Data Flow", "Coordinate Mapping", "Assumptions", "Tradeoffs"]:
        v.check(phrase in architecture, f"ARCHITECTURE.md covers {phrase}")

    insight_count = len(re.findall(r"^##\s+\d+\.", insights, flags=re.MULTILINE))
    v.check(insight_count == 3, "INSIGHTS.md contains exactly three numbered insights")
    for phrase in ["What caught my eye", "The evidence", "Actionable?", "Why a Level Designer should care"]:
        v.check(phrase in insights, f"INSIGHTS.md covers {phrase}")

    placeholder_pattern = re.compile(r"TODO|TBD|placeholder|\[three-pane layout", re.IGNORECASE)
    v.check(not placeholder_pattern.search(readme + architecture + insights), "docs contain no placeholder text")
    if "not deployed yet" in readme.lower():
        v.warn("README still says no live deployment URL; update it after hosting")


def verify_data(v):
    raw_files = list(ROOT.glob("player_data/February_*/*.nakama-0"))
    raw_days = sorted(path.name for path in (ROOT / "player_data").glob("February_*") if path.is_dir())
    v.check(len(raw_files) == 1243, "raw player_data contains 1,243 .nakama-0 files")
    v.check(raw_days == EXPECTED_DAYS, "raw player_data contains all five expected days")

    raw_minimaps = {path.name for path in (ROOT / "player_data/minimaps").glob("*") if path.is_file()}
    public_minimaps = {path.name for path in (ROOT / "web/public/minimaps").glob("*") if path.is_file()}
    v.check(len(raw_minimaps) == 3, "raw minimaps for three maps are present")
    v.check(raw_minimaps == public_minimaps, "public minimaps match raw minimap assets")

    index_path = ROOT / "web/public/data/index.json"
    v.check(index_path.is_file(), "generated index.json exists")
    if not index_path.is_file():
        return

    index = read_json(index_path)
    summary = index.get("summary", {})
    matches = index.get("matches", [])
    map_config = index.get("mapConfig", {})
    days = index.get("days", [])

    v.check(summary.get("files") == len(raw_files), "index summary file count matches raw files")
    v.check(summary.get("rows", 0) > 0, "index summary has event rows")
    v.check(summary.get("matches") == len(matches), "index summary match count matches metadata")
    v.check(set(map_config.keys()) == EXPECTED_MAPS, "index contains all three map configs")
    v.check(days == EXPECTED_DAYS, "index contains all five expected days")

    for map_name, cfg in map_config.items():
        required = {"scale", "originX", "originZ", "size", "image"}
        v.check(required.issubset(cfg.keys()), f"{map_name} config has coordinate mapping fields")
        v.check((ROOT / "web/public/minimaps" / cfg["image"]).is_file(), f"{map_name} minimap asset exists")

    match_files = list((ROOT / "web/public/data/matches").glob("*.json"))
    v.check(len(match_files) == summary.get("matches"), "generated match JSON count matches index")

    sample_match = read_json(match_files[0]) if match_files else {}
    v.check(bool(sample_match.get("players")), "sample match JSON contains player paths/events")

    all_codes = set()
    agg_dir = ROOT / "web/public/data/agg"
    for map_name in EXPECTED_MAPS:
        agg_path = agg_dir / f"{map_name}.json"
        v.check(agg_path.is_file(), f"{map_name} aggregate heatmap JSON exists")
        if not agg_path.is_file():
            continue
        agg = read_json(agg_path)
        lengths = {len(agg.get(key, [])) for key in ["e", "x", "z", "bot", "d"]}
        v.check(len(lengths) == 1 and next(iter(lengths), 0) > 0, f"{map_name} aggregate arrays are aligned")
        all_codes.update(agg.get("e", []))

    v.check(EVENT_CODES_REQUIRED.issubset(all_codes), "generated data includes all required event codes")


def verify_source(v):
    required_files = [
        "tools/build_dataset.py",
        "tools/parquet_reader.py",
        "web/src/App.jsx",
        "web/src/components/Controls.jsx",
        "web/src/components/MapView.jsx",
        "web/src/components/Timeline.jsx",
        "web/src/components/InfoPanel.jsx",
        "web/src/lib/coords.js",
        "web/src/lib/events.js",
        "web/src/lib/heatmap.js",
        "web/src/lib/playback.js",
        "web/src/lib/audience.js",
        "web/src/lib/matches.js",
        ".github/workflows/deploy.yml",
    ]
    for relative_path in required_files:
        v.check((ROOT / relative_path).is_file(), f"{relative_path} exists")

    package = read_json(ROOT / "package.json")
    web_package = read_json(ROOT / "web/package.json")
    v.check(package.get("scripts", {}).get("verify") == "npm test && npm run build", "root npm run verify is configured")
    v.check("node --test" in web_package.get("scripts", {}).get("test", ""), "web unit test command is configured")

    test_files = list((ROOT / "web/src/lib").glob("*.test.js"))
    v.check(len(test_files) >= 5, "web lib has functional unit test coverage")


def main():
    v = Verifier()
    print(f"Verifying {ROOT}")
    verify_docs(v)
    verify_data(v)
    verify_source(v)

    print()
    if v.failures:
        print(f"RESULT FAIL: {len(v.failures)} failure(s), {len(v.warnings)} warning(s)")
        return 1
    print(f"RESULT PASS: 0 failures, {len(v.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
