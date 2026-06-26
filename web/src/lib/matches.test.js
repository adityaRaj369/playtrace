import { test } from "node:test";
import assert from "node:assert";
import { chooseDefaultMatchId, filterMatches } from "./matches.js";

const matches = [
  { matchId: "ambrose-10-a", map: "AmbroseValley", date: "February_10" },
  { matchId: "ambrose-11-a", map: "AmbroseValley", date: "February_11" },
  { matchId: "lockdown-10-a", map: "Lockdown", date: "February_10" },
];

test("filters matches by map", () => {
  assert.deepEqual(
    filterMatches(matches, { map: "AmbroseValley" }).map((match) => match.matchId),
    ["ambrose-10-a", "ambrose-11-a"]
  );
});

test("filters matches by map and date together", () => {
  assert.deepEqual(
    filterMatches(matches, { map: "AmbroseValley", day: "February_10" }).map(
      (match) => match.matchId
    ),
    ["ambrose-10-a"]
  );
});

test("keeps selected match when it remains in the filtered list", () => {
  assert.equal(chooseDefaultMatchId("ambrose-11-a", matches), "ambrose-11-a");
});

test("chooses first filtered match when selected match is invalid", () => {
  assert.equal(chooseDefaultMatchId("missing", matches), "ambrose-10-a");
});

test("returns null when no matches are available", () => {
  assert.equal(chooseDefaultMatchId("missing", []), null);
});
