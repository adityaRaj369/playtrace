import React from "react";
import { EVENT_STYLE, HEATMAP_METRICS } from "../lib/events.js";

const DATE_LABEL = (d) => d.replace("February_", "Feb ");

export default function Controls({
  index, view, setView, map, setMap, dateIdx, setDateIdx,
  matches, matchId, setMatchId, layers, setLayer, audience, setAudience,
  metric, setMetric,
}) {
  const maps = Object.keys(index.mapConfig);
  const days = index.days;

  return (
    <div className="controls">
      <div className="brand">
        <span className="brand-mark">LILA</span> BLACK
        <div className="brand-sub">Player Journey Visualizer</div>
      </div>

      <Section title="View">
        <div className="seg">
          <button type="button" className={view === "match" ? "on" : ""} onClick={() => setView("match")}>
            Single match
          </button>
          <button type="button" className={view === "heatmap" ? "on" : ""} onClick={() => setView("heatmap")}>
            Heatmap
          </button>
        </div>
      </Section>

      <Section title="Map">
        <select value={map} onChange={(e) => setMap(e.target.value)}>
          {maps.map((m) => (
            <option key={m} value={m}>
              {m} ({index.summary.maps[m]} matches)
            </option>
          ))}
        </select>
      </Section>

      <Section title="Date">
        <select
          value={dateIdx == null ? "" : dateIdx}
          onChange={(e) => setDateIdx(e.target.value === "" ? null : Number(e.target.value))}
        >
          <option value="">All 5 days</option>
          {days.map((d, i) => (
            <option key={d} value={i}>{DATE_LABEL(d)}</option>
          ))}
        </select>
      </Section>

      <Section title="Players">
        <div className="seg">
          {["all", "human", "bot"].map((a) => (
            <button
              key={a}
              type="button"
              className={audience === a ? "on" : ""}
              onClick={() => setAudience(a)}
            >
              {a === "all" ? "All" : a === "human" ? "Humans" : "Bots"}
            </button>
          ))}
        </div>
      </Section>

      {view === "match" ? (
        <>
          <Section title={`Match (${matches.length})`}>
            <select value={matchId || ""} onChange={(e) => setMatchId(e.target.value)}>
              {matches.map((m) => (
                <option key={m.matchId} value={m.matchId}>
                  {short(m.matchId)} · {m.humans}H/{m.bots}B · {m.kills}K
                </option>
              ))}
            </select>
          </Section>

          <Section title="Layers">
            <Toggle label="Paths" v={layers.paths} on={() => setLayer("paths")} swatch="#36d6ff" />
            <Toggle label="Humans" v={layers.humans} on={() => setLayer("humans")} swatch="#36d6ff" />
            <Toggle label="Bots" v={layers.bots} on={() => setLayer("bots")} swatch="#f6a13c" />
            <Toggle label="Events" v={layers.events} on={() => setLayer("events")} />
            {layers.events && (
              <div className="event-toggles">
                {Object.entries(EVENT_STYLE).map(([k, s]) => (
                  <Toggle
                    key={k}
                    label={s.label}
                    v={layers[k] !== false}
                    on={() => setLayer(k)}
                    swatch={s.color}
                    small
                  />
                ))}
              </div>
            )}
          </Section>
        </>
      ) : (
        <Section title="Heatmap metric">
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {Object.entries(HEATMAP_METRICS).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <p className="hint">
            Brighter = denser. Combine with the Date and Players filters above to
            slice the map by day or by humans vs bots.
          </p>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="section">
      <div className="section-title">{title}</div>
      {children}
    </div>
  );
}

function Toggle({ label, v, on, swatch, small }) {
  return (
    <label className={"toggle" + (small ? " small" : "")}>
      <input type="checkbox" checked={v} onChange={on} />
      {swatch && <span className="swatch" style={{ background: swatch }} />}
      {label}
    </label>
  );
}

const short = (id) => id.split("-")[0];
