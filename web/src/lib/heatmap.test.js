import { test } from "node:test";
import assert from "node:assert";
import { filterAggregate, buildDensityGrid, heatColor } from "./heatmap.js";
import { EVENT_CODE } from "./events.js";

const cfg = { scale: 900, originX: -370, originZ: -473, size: 1024 };

// tiny synthetic cloud
const agg = {
  // 2 human positions, 1 bot position, 1 storm death, 1 loot
  e: [EVENT_CODE.Position, EVENT_CODE.Position, EVENT_CODE.BotPosition,
      EVENT_CODE.KilledByStorm, EVENT_CODE.Loot],
  x: [-300, -300, -300, -100, -200],
  z: [-300, -300, -300, -100, -200],
  bot: [0, 0, 1, 0, 0],
  d: [0, 1, 0, 0, 2],
};

test("traffic metric includes human + bot positions", () => {
  const pts = filterAggregate(agg, { metric: "traffic", cfg });
  assert.equal(pts.length, 3);
});

test("humanTraffic excludes bot positions", () => {
  const pts = filterAggregate(agg, { metric: "humanTraffic", cfg });
  assert.equal(pts.length, 2);
});

test("audience=bot keeps only bot rows", () => {
  const pts = filterAggregate(agg, { metric: "traffic", cfg, audience: "bot" });
  assert.equal(pts.length, 1);
});

test("date filter narrows points", () => {
  const pts = filterAggregate(agg, { metric: "traffic", cfg, dateIdx: 0 });
  assert.equal(pts.length, 2); // one human(d0) + one bot(d0)
});

test("storm metric isolates storm deaths", () => {
  const pts = filterAggregate(agg, { metric: "storm", cfg });
  assert.equal(pts.length, 1);
});

test("density grid accumulates and reports max", () => {
  const pts = filterAggregate(agg, { metric: "traffic", cfg });
  const { cells, max } = buildDensityGrid(pts, 64);
  assert.equal(max, 3); // all 3 traffic pts share the same world coord/cell
  assert.equal(cells.reduce((a, b) => a + b, 0), 3);
});

test("heatColor returns rgb in range and ramps", () => {
  for (const t of [0, 0.3, 0.6, 1]) {
    const c = heatColor(t);
    assert.equal(c.length, 3);
    for (const ch of c) assert.ok(ch >= 0 && ch <= 255);
  }
  assert.deepEqual(heatColor(2), heatColor(1)); // clamps
});
