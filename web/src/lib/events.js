// Shared event metadata: codes, display names, colors, grouping.
// Codes must match tools/build_dataset.py EVENT_CODES.

export const EVENT_CODE = {
  Position: 0,
  BotPosition: 1,
  Kill: 2,
  Killed: 3,
  BotKill: 4,
  BotKilled: 5,
  KilledByStorm: 6,
  Loot: 7,
};

export const CODE_EVENT = Object.fromEntries(
  Object.entries(EVENT_CODE).map(([k, v]) => [v, k])
);

// Marker styling for discrete (non-position) events.
export const EVENT_STYLE = {
  Kill: { label: "Kill (PvP)", color: "#ff4d4d", shape: "triangle" },
  BotKill: { label: "Bot kill", color: "#ff9f43", shape: "triangle" },
  Killed: { label: "Death (PvP)", color: "#c0392b", shape: "x" },
  BotKilled: { label: "Death to bot", color: "#8e44ad", shape: "x" },
  KilledByStorm: { label: "Storm death", color: "#4dc3ff", shape: "diamond" },
  Loot: { label: "Loot", color: "#ffd93d", shape: "dot" },
};

export const POSITION_CODES = new Set([EVENT_CODE.Position, EVENT_CODE.BotPosition]);

// Logical categories used by the heatmap "metric" selector.
export const HEATMAP_METRICS = {
  traffic: {
    label: "Traffic (all positions)",
    codes: [EVENT_CODE.Position, EVENT_CODE.BotPosition],
  },
  humanTraffic: {
    label: "Human traffic",
    codes: [EVENT_CODE.Position],
  },
  kills: {
    label: "Kill zones",
    codes: [EVENT_CODE.Kill, EVENT_CODE.BotKill],
  },
  deaths: {
    label: "Death zones",
    codes: [EVENT_CODE.Killed, EVENT_CODE.BotKilled, EVENT_CODE.KilledByStorm],
  },
  storm: {
    label: "Storm deaths",
    codes: [EVENT_CODE.KilledByStorm],
  },
  loot: {
    label: "Loot pickups",
    codes: [EVENT_CODE.Loot],
  },
};

export function isBotEventName(name) {
  return name === "BotPosition" || name === "BotKill" || name === "BotKilled";
}
