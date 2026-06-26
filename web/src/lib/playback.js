export function nextPlayState({ time, maxTime, playing }) {
  if (playing) {
    return { time, playing: false };
  }
  if (maxTime > 0 && time >= maxTime) {
    return { time: 0, playing: true };
  }
  return { time, playing: true };
}
