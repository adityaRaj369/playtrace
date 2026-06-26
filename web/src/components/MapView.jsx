import React, { useEffect, useRef } from "react";
import { worldToCanvas } from "../lib/coords.js";
import { useImage } from "../lib/useImage.js";
import { minimapURL } from "../lib/api.js";
import { buildDensityGrid, heatColor } from "../lib/heatmap.js";
import { EVENT_STYLE } from "../lib/events.js";

const DIM = 1024; // internal canvas resolution = minimap reference resolution

const HUMAN_COLOR = "#36d6ff";
const BOT_COLOR = "#f6a13c";

// position along a path [[t,x,z],...] at time t (linear interp)
function posAtTime(path, t) {
  if (!path.length) return null;
  if (t <= path[0][0]) return { x: path[0][1], z: path[0][2] };
  if (t >= path[path.length - 1][0]) {
    const p = path[path.length - 1];
    return { x: p[1], z: p[2] };
  }
  for (let i = 1; i < path.length; i++) {
    if (path[i][0] >= t) {
      const a = path[i - 1], b = path[i];
      const f = (t - a[0]) / (b[0] - a[0] || 1);
      return { x: a[1] + (b[1] - a[1]) * f, z: a[2] + (b[2] - a[2]) * f };
    }
  }
  return null;
}

function drawMarker(ctx, x, y, style, r = 7) {
  ctx.save();
  ctx.fillStyle = style.color;
  ctx.strokeStyle = "rgba(0,0,0,0.85)";
  ctx.lineWidth = 2;
  ctx.shadowColor = "rgba(0,0,0,0.6)";
  ctx.shadowBlur = 3;
  switch (style.shape) {
    case "triangle":
      ctx.beginPath();
      ctx.moveTo(x, y - r);
      ctx.lineTo(x + r, y + r);
      ctx.lineTo(x - r, y + r);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      break;
    case "diamond":
      ctx.beginPath();
      ctx.moveTo(x, y - r);
      ctx.lineTo(x + r, y);
      ctx.lineTo(x, y + r);
      ctx.lineTo(x - r, y);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      break;
    case "x":
      ctx.lineWidth = 3.5;
      ctx.strokeStyle = style.color;
      ctx.beginPath();
      ctx.moveTo(x - r, y - r);
      ctx.lineTo(x + r, y + r);
      ctx.moveTo(x + r, y - r);
      ctx.lineTo(x - r, y + r);
      ctx.stroke();
      break;
    default: // dot
      ctx.beginPath();
      ctx.arc(x, y, r - 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
  }
  ctx.restore();
}

export default function MapView({
  cfg, mapImage, mode, match, aggPoints, layers, audience, time, maxTime,
}) {
  const canvasRef = useRef(null);
  const img = useImage(mapImage ? minimapURL(mapImage) : null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, DIM, DIM);

    // background minimap
    if (img) {
      ctx.globalAlpha = mode === "heatmap" ? 0.55 : 1;
      ctx.drawImage(img, 0, 0, DIM, DIM);
      ctx.globalAlpha = 1;
    } else {
      ctx.fillStyle = "#0d1117";
      ctx.fillRect(0, 0, DIM, DIM);
    }

    if (!cfg) return;

    if (mode === "heatmap") {
      drawHeatmap(ctx, aggPoints || []);
    } else if (match) {
      drawMatch(ctx, cfg, match, layers, audience, time);
    }
  }, [img, cfg, mode, match, aggPoints, layers, audience, time]);

  return (
    <div className="mapview">
      <canvas ref={canvasRef} width={DIM} height={DIM} className="map-canvas" />
    </div>
  );

  function drawHeatmap(ctx, points) {
    if (!points.length) return;
    const grid = 110;
    const { cells, max } = buildDensityGrid(points, grid);
    if (max === 0) return;
    // render density to a small offscreen canvas, then scale up smoothly
    const off = document.createElement("canvas");
    off.width = grid;
    off.height = grid;
    const octx = off.getContext("2d");
    const imgData = octx.createImageData(grid, grid);
    // log scaling so dense hotspots don't wash out sparse traffic
    const denom = Math.log(max + 1);
    for (let i = 0; i < cells.length; i++) {
      const v = cells[i];
      const t = v > 0 ? Math.log(v + 1) / denom : 0;
      const [r, g, b] = heatColor(t);
      const o = i * 4;
      imgData.data[o] = r;
      imgData.data[o + 1] = g;
      imgData.data[o + 2] = b;
      imgData.data[o + 3] = v > 0 ? Math.min(235, 70 + t * 185) : 0;
    }
    octx.putImageData(imgData, 0, 0);
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.globalAlpha = 0.8;
    ctx.drawImage(off, 0, 0, DIM, DIM);
    ctx.restore();
  }

  function drawMatch(ctx, cfg, match, layers, audience, time) {
    const T = time == null ? Infinity : time;
    for (const p of match.players) {
      if (audience === "human" && p.bot) continue;
      if (audience === "bot" && !p.bot) continue;
      const isBot = p.bot;
      if ((isBot && !layers.bots) || (!isBot && !layers.humans)) continue;

      // ---- path polyline up to T ----
      if (layers.paths && p.path.length) {
        ctx.save();
        ctx.strokeStyle = isBot ? BOT_COLOR : HUMAN_COLOR;
        ctx.globalAlpha = isBot ? 0.5 : 0.85;
        ctx.lineWidth = isBot ? 1.5 : 2.5;
        ctx.lineJoin = "round";
        ctx.beginPath();
        let started = false;
        for (const [t, x, z] of p.path) {
          if (t > T) break;
          const { cx, cy } = worldToCanvas(x, z, cfg, DIM);
          if (!started) { ctx.moveTo(cx, cy); started = true; }
          else ctx.lineTo(cx, cy);
        }
        ctx.stroke();
        ctx.restore();

        // current head position
        if (time != null) {
          const pos = posAtTime(p.path, T);
          if (pos) {
            const { cx, cy } = worldToCanvas(pos.x, pos.z, cfg, DIM);
            ctx.save();
            ctx.fillStyle = isBot ? BOT_COLOR : HUMAN_COLOR;
            ctx.strokeStyle = "#000";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, isBot ? 4 : 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.restore();
          }
        }
      }

      // ---- event markers up to T ----
      if (layers.events) {
        for (const [t, x, z, ev] of p.events) {
          if (t > T) continue;
          const style = EVENT_STYLE[ev];
          if (!style || layers[ev] === false) continue;
          const { cx, cy } = worldToCanvas(x, z, cfg, DIM);
          drawMarker(ctx, cx, cy, style);
        }
      }
    }
  }
}
