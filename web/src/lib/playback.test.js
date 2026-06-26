import { test } from "node:test";
import assert from "node:assert";
import { nextPlayState } from "./playback.js";

test("play from finished timeline restarts at zero", () => {
  assert.deepEqual(
    nextPlayState({ time: 120, maxTime: 120, playing: false }),
    { time: 0, playing: true }
  );
});

test("play while paused before the end resumes from current time", () => {
  assert.deepEqual(
    nextPlayState({ time: 42, maxTime: 120, playing: false }),
    { time: 42, playing: true }
  );
});

test("clicking while playing pauses without changing time", () => {
  assert.deepEqual(
    nextPlayState({ time: 42, maxTime: 120, playing: true }),
    { time: 42, playing: false }
  );
});
