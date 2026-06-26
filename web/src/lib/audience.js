export function matchSupportsAudience(match, audience) {
  if (!match) return false;
  if (audience === "human") return match.humans > 0;
  if (audience === "bot") return match.bots > 0;
  return true;
}

export function chooseMatchForAudience(currentMatchId, matches, audience) {
  if (!matches.length) return null;
  const current = matches.find((match) => match.matchId === currentMatchId);
  if (matchSupportsAudience(current, audience)) return currentMatchId;
  const compatible = matches.find((match) => matchSupportsAudience(match, audience));
  return compatible ? compatible.matchId : currentMatchId || matches[0].matchId;
}
