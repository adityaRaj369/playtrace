import React from "react";
import { EVENT_STYLE } from "../lib/events.js";

const DATE_LABEL = (d) => d.replace("February_", "Feb ");

// Right-hand panel: legend + contextual stats for the current selection.
export default function InfoPanel({ view, match, matchMeta, summary }) {
  return (
    <div className="info">
      <div className="section">
        <div className="section-title">Legend</div>
        <LegendRow swatch="#36d6ff" label="Human path / player" line />
        <LegendRow swatch="#f6a13c" label="Bot path / player" line />
        {Object.values(EVENT_STYLE).map((s) => (
          <LegendRow key={s.label} swatch={s.color} label={s.label} />
        ))}
      </div>

      {view === "match" && matchMeta && (
        <div className="section">
          <div className="section-title">This match</div>
          <Stat k="Map" v={matchMeta.map} />
          <Stat k="Date" v={DATE_LABEL(matchMeta.date)} />
          <Stat k="Duration" v={`${Math.floor(matchMeta.duration / 60)}m ${matchMeta.duration % 60}s`} />
          <Stat k="Humans" v={matchMeta.humans} />
          <Stat k="Bots" v={matchMeta.bots} />
          <Stat k="Kills" v={matchMeta.kills} />
          <Stat k="Deaths" v={matchMeta.deaths} />
          <Stat k="Storm deaths" v={matchMeta.stormDeaths} />
          <Stat k="Loot pickups" v={matchMeta.loot} />
        </div>
      )}

      <div className="section">
        <div className="section-title">Dataset</div>
        <Stat k="Matches" v={summary.matches} />
        <Stat k="Files (player-journeys)" v={summary.files} />
        <Stat k="Event rows" v={summary.rows.toLocaleString()} />
      </div>
    </div>
  );
}

function LegendRow({ swatch, label, line }) {
  return (
    <div className="legend-row">
      <span className={"swatch" + (line ? " line" : "")} style={{ background: swatch }} />
      {label}
    </div>
  );
}

function Stat({ k, v }) {
  return (
    <div className="stat">
      <span className="stat-k">{k}</span>
      <span className="stat-v">{v}</span>
    </div>
  );
}
