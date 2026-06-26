// Heatmap construction.
//
// filterAggregate: given the per-map columnar cloud + a metric + date filter +
// human/bot filter, return the list of normalized points to plot.
//
// buildDensityGrid: bin normalized points into a grid and return max density,
// used both for canvas rendering and for the headless unit tests.

import { worldToNorm } from "./coords.js";
import { HEATMAP_METRICS } from "./events.js";

/**
 * @param {object} agg  columnar cloud: {e:[],x:[],z:[],bot:[],d:[]}
 * @param {object} opts {metric, cfg, dateIdx (null=all), audience: 'all'|'human'|'bot'}
 * @returns {Array<{nx:number, ny:number}>}
 */
export function filterAggregate(agg, { metric, cfg, dateIdx = null, audience = "all" }) {
  const codes = new Set(HEATMAP_METRICS[metric].codes);
  const pts = [];
  const n = agg.x.length;
  for (let i = 0; i < n; i++) {
    if (!codes.has(agg.e[i])) continue;
    if (dateIdx != null && agg.d[i] !== dateIdx) continue;
    if (audience === "human" && agg.bot[i] === 1) continue;
    if (audience === "bot" && agg.bot[i] === 0) continue;
    const { nx, ny } = worldToNorm(agg.x[i], agg.z[i], cfg);
    if (nx < -0.05 || nx > 1.05 || ny < -0.05 || ny > 1.05) continue; // off-map guard
    pts.push({ nx, ny });
  }
  return pts;
}

/**
 * Bin normalized points into a `grid`x`grid` density matrix.
 * Returns { grid, cells:Float32Array, max }.
 */
export function buildDensityGrid(points, grid = 64) {
  const cells = new Float32Array(grid * grid);
  for (const p of points) {
    const gx = Math.min(grid - 1, Math.max(0, Math.floor(p.nx * grid)));
    const gy = Math.min(grid - 1, Math.max(0, Math.floor(p.ny * grid)));
    cells[gy * grid + gx] += 1;
  }
  let max = 0;
  for (let i = 0; i < cells.length; i++) if (cells[i] > max) max = cells[i];
  return { grid, cells, max };
}

// Turbo-ish color ramp for density value t in [0,1] -> [r,g,b].
export function heatColor(t) {
  t = Math.max(0, Math.min(1, t));
  const stops = [
    [0.0, [0, 0, 80]],
    [0.25, [0, 120, 255]],
    [0.5, [0, 220, 130]],
    [0.7, [240, 230, 40]],
    [0.85, [255, 140, 0]],
    [1.0, [220, 30, 30]],
  ];
  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i][0]) {
      const [t0, c0] = stops[i - 1];
      const [t1, c1] = stops[i];
      const f = (t - t0) / (t1 - t0);
      return [
        Math.round(c0[0] + (c1[0] - c0[0]) * f),
        Math.round(c0[1] + (c1[1] - c0[1]) * f),
        Math.round(c0[2] + (c1[2] - c0[2]) * f),
      ];
    }
  }
  return [220, 30, 30];
}
