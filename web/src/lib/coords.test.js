import { test } from "node:test";
import assert from "node:assert";
import { worldToPixel, worldToNorm } from "./coords.js";

const ambrose = { scale: 900, originX: -370, originZ: -473, size: 1024 };

test("matches README worked example (AmbroseValley)", () => {
  // README: x=-301.45, z=-355.55 -> pixel (78, 890)
  const { px, py } = worldToPixel(-301.45, -355.55, ambrose);
  assert.equal(Math.round(px), 78);
  assert.equal(Math.round(py), 890);
});

test("origin maps to bottom-left corner", () => {
  // world (originX, originZ) -> u=0,v=0 -> nx=0, ny=1 (bottom-left)
  const { nx, ny } = worldToNorm(ambrose.originX, ambrose.originZ, ambrose);
  assert.equal(nx, 0);
  assert.equal(ny, 1);
});

test("Y axis is flipped (higher z is higher on image)", () => {
  const low = worldToNorm(0, ambrose.originZ, ambrose); // v=0 -> ny=1 (bottom)
  const high = worldToNorm(0, ambrose.originZ + ambrose.scale, ambrose); // v=1 -> ny=0 (top)
  assert.ok(high.ny < low.ny);
});
