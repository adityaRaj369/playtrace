// Data fetching. All paths are relative to import.meta.env.BASE_URL so the
// app works under any deploy prefix (GitHub Pages /<repo>/, Vercel root, etc).

const BASE = import.meta.env.BASE_URL || "/";

function url(p) {
  return `${BASE}${p}`.replace(/\/{2,}/g, "/");
}

const cache = new Map();

async function getJSON(path) {
  if (cache.has(path)) return cache.get(path);
  const res = await fetch(url(path));
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  const data = await res.json();
  cache.set(path, data);
  return data;
}

export const loadIndex = () => getJSON("data/index.json");
export const loadMatch = (id) => getJSON(`data/matches/${id}.json`);
export const loadAggregate = (map) => getJSON(`data/agg/${map}.json`);
export const minimapURL = (image) => url(`minimaps/${image}`);
