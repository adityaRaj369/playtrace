import { test } from "node:test";
import assert from "node:assert";
import { matchSupportsAudience, chooseMatchForAudience } from "./audience.js";

const matches = [
  { matchId: "human-only", humans: 1, bots: 0 },
  { matchId: "bot-only", humans: 0, bots: 12 },
  { matchId: "mixed", humans: 1, bots: 8 },
];

test("audience=all accepts any match", () => {
  assert.equal(matchSupportsAudience(matches[0], "all"), true);
  assert.equal(matchSupportsAudience(matches[1], "all"), true);
});

test("human and bot audiences require matching players", () => {
  assert.equal(matchSupportsAudience(matches[0], "human"), true);
  assert.equal(matchSupportsAudience(matches[0], "bot"), false);
  assert.equal(matchSupportsAudience(matches[1], "human"), false);
  assert.equal(matchSupportsAudience(matches[1], "bot"), true);
});

test("chooses a compatible match when current match does not contain selected audience", () => {
  assert.equal(chooseMatchForAudience("human-only", matches, "bot"), "bot-only");
  assert.equal(chooseMatchForAudience("bot-only", matches, "human"), "human-only");
});

test("keeps current match when it already supports selected audience", () => {
  assert.equal(chooseMatchForAudience("mixed", matches, "bot"), "mixed");
  assert.equal(chooseMatchForAudience("mixed", matches, "human"), "mixed");
});

test("falls back to current match when no compatible match exists", () => {
  assert.equal(chooseMatchForAudience("human-only", [matches[0]], "bot"), "human-only");
});
