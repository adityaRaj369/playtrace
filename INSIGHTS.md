# Three things the tool revealed about LILA BLACK

All figures below come from the full 5-day dataset (1,243 player-journeys,
89,104 events, 796 matches) and are reproducible in the tool itself — switch to
the **Heatmap** view or read the per-match stats in the right panel.

---

## 1. In this data, LILA BLACK is played almost entirely as PvE, not PvP

**What caught my eye.** Turning on event markers across matches, I almost never
saw a PvP kill. Switching to the *Kill zones* heatmap, the human-vs-human layer
is essentially empty while bot kills are everywhere.

**The evidence.**

| Kills (player vs player) | Kills (player vs bot) | Ratio |
|---|---|---|
| **3** | **2,415** | **805 : 1** |

Deaths tell the same story: 3 deaths to other players, 700 to bots, 39 to the
storm. And **779 of 796 matches (98%) contain a single human** (mean 1.0 humans
per match, max 2). Players are effectively soloing lobbies full of bots.

**Actionable?** Yes.
- **Metrics affected:** PvP encounter rate, human-players-per-match,
  matchmaking fill time, time-to-first-player-contact.
- **Actions:** If PvP is a core pillar, this is an alarm — investigate
  matchmaking (are humans being spread across too many lobbies / too many
  bots?), or deliberately raise bot difficulty/aggression so PvE still creates
  tension. If the early-funnel experience is *meant* to be PvE onboarding,
  validate that bot encounters are well-paced (see #2).

**Why a Level Designer should care.** You are, in practice, designing for a
solo-PvE flow right now. Sightline and cover decisions tuned for player-vs-player
duels are being spent on bot encounters; level pacing should be validated against
how bots actually engage, not an assumed PvP meta.

---

## 2. Players use only half the map — traffic funnels into a few hotspots

**What caught my eye.** The *Traffic* heatmap on Ambrose Valley lights up a
compact cluster of POIs while large regions stay completely dark.

**The evidence.** Binning all 48,754 Ambrose Valley position samples into a
10×10 grid:

- **48% of grid cells have zero traffic** — roughly half the playable area is
  never walked.
- The **top 10% of cells carry 45% of all movement**. The busiest cell holds
  3,552 samples; the median *occupied* cell holds 807 — a >4× concentration.

**Actionable?** Yes.
- **Metrics affected:** map-area utilization %, loot-per-zone, average rotation
  distance, encounter density.
- **Actions:** Pull loot, objectives, or an extraction point into the cold
  zones to draw players out; or, if the dead space is intentional buffer, trim
  it to tighten rotations and raise encounter density. Re-run the heatmap after
  the change to confirm the cold cells warmed up.

**Why a Level Designer should care.** Dead space is wasted authoring effort and
flattens encounters. Knowing exactly which cells are ignored turns "the map feels
empty in the south" into a targeted, measurable fix.

---

## 3. Storm deaths are rare overall — but Lockdown punishes ~3× harder

**What caught my eye.** The *Storm deaths* heatmap is sparse (the storm isn't a
major killer), yet Lockdown lit up out of proportion to how often it's played.

**The evidence.**

| Map | Storm deaths | Matches | Storm deaths / match |
|---|---|---|---|
| AmbroseValley | 17 | 566 | 0.030 |
| GrandRift | 5 | 59 | 0.085 |
| **Lockdown** | **17** | **171** | **0.099** |

Lockdown kills as many players with the storm as Ambrose Valley does, on **less
than a third of the matches** — a ~3.3× higher per-match storm-death rate. And on
Ambrose Valley, storm deaths cluster around mid-map (normalized centroid ≈
0.43, 0.49), i.e. players caught mid-rotation, not stragglers looting the edge.

**Actionable?** Yes.
- **Metrics affected:** storm-death rate per map, extraction-success rate,
  average time-to-extract on small maps.
- **Actions:** Re-tune Lockdown's storm speed or timing, or widen its extraction
  window — its smaller footprint likely leaves too little time to reposition.
  On Ambrose Valley, the central clustering suggests rotation paths, not the
  perimeter, are the danger; consider a mid-map cover lane or safe corridor.

**Why a Level Designer should care.** Storm deaths are a direct readout of
whether your map's size and rotation routes match the storm's pacing. A 3× outlier
on one map is a concrete, per-map balancing signal — not a vague "Lockdown feels
rushed."

---

*Reproduce any of these: open the tool, pick the map and date, and toggle the
relevant heatmap metric or scrub a match on the timeline.*
