export function filterMatches(matches, { map = null, day = null } = {}) {
  if (!Array.isArray(matches)) return [];
  return matches.filter((match) => {
    if (map && match.map !== map) return false;
    if (day && match.date !== day) return false;
    return true;
  });
}

export function chooseDefaultMatchId(currentMatchId, matches) {
  if (!matches.length) return null;
  const currentStillVisible = matches.some((match) => match.matchId === currentMatchId);
  return currentStillVisible ? currentMatchId : matches[0].matchId;
}
