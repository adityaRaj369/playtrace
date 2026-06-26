import React from "react";

function fmt(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export default function Timeline({
  time, maxTime, playing, setPlaying, setTime, speed, setSpeed, onRestart, onTogglePlayback,
}) {
  return (
    <div className="timeline">
      <button type="button" className="play" onClick={onTogglePlayback} title="Play / pause">
        {playing ? "❚❚" : "►"}
      </button>
      <button type="button" className="play ghost" onClick={onRestart} title="Restart">⟲</button>
      <span className="clock">{fmt(time)}</span>
      <input
        type="range"
        min={0}
        max={maxTime || 1}
        step={1}
        value={Math.min(time, maxTime || 1)}
        onChange={(e) => { setPlaying(false); setTime(Number(e.target.value)); }}
        className="scrub"
      />
      <span className="clock">{fmt(maxTime || 0)}</span>
      <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="speed">
        {[1, 2, 4, 8, 16].map((s) => (
          <option key={s} value={s}>{s}×</option>
        ))}
      </select>
    </div>
  );
}
