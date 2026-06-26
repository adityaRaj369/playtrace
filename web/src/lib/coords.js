// World <-> minimap coordinate conversion.
//
// Mapping (from player_data/README.md, validated against its worked example):
//   u = (x - originX) / scale
//   v = (z - originZ) / scale
//   pixelX = u * size
//   pixelY = (1 - v) * size        // Y is flipped: image origin is top-left
//
// `size` is the reference minimap resolution (1024). We express results in a
// 0..1 normalized space so the canvas can scale to any display size while the
// mapping stays exact.

/** World (x, z) -> normalized image coords in [0,1], origin top-left. */
export function worldToNorm(x, z, cfg) {
  const u = (x - cfg.originX) / cfg.scale;
  const v = (z - cfg.originZ) / cfg.scale;
  return { nx: u, ny: 1 - v };
}

/** World (x, z) -> pixel coords on a `size`x`size` image (default 1024). */
export function worldToPixel(x, z, cfg, size = cfg.size || 1024) {
  const { nx, ny } = worldToNorm(x, z, cfg);
  return { px: nx * size, py: ny * size };
}

/** World (x, z) -> canvas pixel coords for a canvas of width/height `dim`. */
export function worldToCanvas(x, z, cfg, dim) {
  const { nx, ny } = worldToNorm(x, z, cfg);
  return { cx: nx * dim, cy: ny * dim };
}
