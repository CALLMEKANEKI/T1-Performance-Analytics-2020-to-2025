const BASE_URL = "http://localhost:8000/api";

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  champions: () => get("/champions"),

  model1Info: () => get("/model1/info"),
  model1ShapImportance: (topN = 20) => get(`/model1/shap-importance?top_n=${topN}`),

  model2Timeseries: (championId) => get(`/model2/timeseries/${championId}`),
  model2ShiftEvents: ({ championId, minScore = 0, limit = 50 } = {}) => {
    const params = new URLSearchParams();
    if (championId) params.set("champion_id", championId);
    if (minScore) params.set("min_score", minScore);
    params.set("limit", limit);
    return get(`/model2/shift-events?${params.toString()}`);
  },
  model2TopPresence: (topN = 10) => get(`/model2/top-presence?top_n=${topN}`),

  matches: ({ tournamentId, opponentId, page = 1, pageSize = 20 } = {}) => {
    const params = new URLSearchParams();
    if (tournamentId) params.set("tournament_id", tournamentId);
    if (opponentId) params.set("opponent_id", opponentId);
    params.set("page", page);
    params.set("page_size", pageSize);
    return get(`/matches?${params.toString()}`);
  },
  seriesDetail: (seriesId) => get(`/matches/${seriesId}`),
  gameDetail: (gameId) => get(`/matches/game/${gameId}`),

  // Stats
  statsByPatch: () => get("/stats/winrate-by-patch"),
  statsByTournament: () => get("/stats/winrate-by-tournament"),
  statsBySide: () => get("/stats/winrate-by-side"),
  playerWinrates: () => get("/stats/player-winrates"),
  playerDetail: (playerId) => get(`/stats/player/${playerId}`),
};

export const STATIC_BASE = "http://localhost:8000";