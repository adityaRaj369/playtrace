import React, { useEffect, useMemo, useRef, useState } from "react";
import { loadIndex, loadMatch, loadAggregate } from "./lib/api.js";
import { filterAggregate } from "./lib/heatmap.js";
import Controls from "./components/Controls.jsx";
import MapView from "./components/MapView.jsx";
import Timeline from "./components/Timeline.jsx";
import InfoPanel from "./components/InfoPanel.jsx";
import { nextPlayState } from "./lib/playback.js";
import { chooseMatchForAudience } from "./lib/audience.js";
import { chooseDefaultMatchId, filterMatches } from "./lib/matches.js";

const DEFAULT_LAYERS = { paths: true, humans: true, bots: true, events: true };

export default function App() {
  const [index, setIndex] = useState(null);
  const [error, setError] = useState(null);

  const [view, setView] = useState("match");
  const [map, setMap] = useState(null);
  const [dateIdx, setDateIdx] = useState(null);
  const [audience, setAudience] = useState("all");

  const [matchId, setMatchId] = useState(null);
  const [match, setMatch] = useState(null);

  const [agg, setAgg] = useState(null);
  const [metric, setMetric] = useState("traffic");

  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const setLayer = (k) => setLayers((s) => ({ ...s, [k]: !(s[k] ?? true) }));

  // playback
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);
  const raf = useRef(0);
  const last = useRef(0);

  // ---- initial load ----
  useEffect(() => {
    loadIndex()
      .then((idx) => {
        setIndex(idx);
        setMap(Object.keys(idx.mapConfig)[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // ---- matches for current map/date ----
  const matches = useMemo(() => {
    if (!index || !map) return [];
    return filterMatches(index.matches, {
      map,
      day: dateIdx == null ? null : index.days[dateIdx],
    });
  }, [index, map, dateIdx]);

  // keep a valid selected match
  useEffect(() => {
    const nextMatchId = chooseDefaultMatchId(matchId, matches);
    if (nextMatchId !== matchId) {
      setMatchId(nextMatchId);
    }
  }, [matches, matchId]);

  // If the user switches to Humans/Bots while the current match has none,
  // jump to the first compatible match in the same map/date filter.
  useEffect(() => {
    if (!matches.length || view !== "match") return;
    const nextMatchId = chooseMatchForAudience(matchId, matches, audience);
    if (nextMatchId && nextMatchId !== matchId) {
      setMatchId(nextMatchId);
    }
  }, [audience, matches, matchId, view]);

  // ---- load match detail ----
  useEffect(() => {
    if (!matchId || view !== "match") return;
    let cancelled = false;
    loadMatch(matchId).then((m) => {
      if (cancelled) return;
      setMatch(m);
      setTime(m.duration);
      setPlaying(false);
    });
    return () => { cancelled = true; };
  }, [matchId, view]);

  // ---- load aggregate when map changes (for heatmap) ----
  useEffect(() => {
    if (!map) return;
    loadAggregate(map).then(setAgg).catch((e) => setError(String(e)));
  }, [map]);

  const cfg = index && map ? index.mapConfig[map] : null;
  const matchMeta = matches.find((m) => m.matchId === matchId) || null;

  // ---- heatmap points ----
  const aggPoints = useMemo(() => {
    if (view !== "heatmap" || !agg || !cfg) return [];
    return filterAggregate(agg, { metric, cfg, dateIdx, audience });
  }, [view, agg, cfg, metric, dateIdx, audience]);

  // ---- playback loop ----
  useEffect(() => {
    if (!playing) { cancelAnimationFrame(raf.current); return; }
    last.current = performance.now();
    const tick = (now) => {
      const dt = (now - last.current) / 1000;
      last.current = now;
      setTime((t) => {
        const nt = t + dt * speed;
        if (match && nt >= match.duration) { setPlaying(false); return match.duration; }
        return nt;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, speed, match]);

  const restart = () => { setTime(0); setPlaying(true); };
  const togglePlayback = () => {
    const next = nextPlayState({ time, maxTime: match?.duration || 0, playing });
    setTime(next.time);
    setPlaying(next.playing);
  };

  if (error) return <div className="fatal">Failed to load data: {error}</div>;
  if (!index) return <div className="loading">Loading telemetry…</div>;

  return (
    <div className="app">
      <Controls
        index={index} view={view} setView={setView}
        map={map} setMap={setMap} dateIdx={dateIdx} setDateIdx={setDateIdx}
        matches={matches} matchId={matchId} setMatchId={setMatchId}
        layers={layers} setLayer={setLayer} audience={audience} setAudience={setAudience}
        metric={metric} setMetric={setMetric}
      />

      <main className="stage">
        <MapView
          cfg={cfg}
          mapImage={cfg?.image}
          mode={view}
          match={view === "match" ? match : null}
          aggPoints={aggPoints}
          layers={layers}
          audience={audience}
          time={view === "match" ? time : null}
          maxTime={match?.duration || 0}
        />
        {view === "match" && match && (
          <Timeline
            time={time} maxTime={match.duration} playing={playing}
            setPlaying={setPlaying} setTime={setTime} speed={speed} setSpeed={setSpeed}
            onTogglePlayback={togglePlayback}
            onRestart={restart}
          />
        )}
      </main>

      <InfoPanel view={view} match={match} matchMeta={matchMeta} summary={index.summary} />
    </div>
  );
}
