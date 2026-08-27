const rawApiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export const BASE_URL = `${rawApiUrl}/api`;
export const STATIC_BASE = rawApiUrl;

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    let errorDetail = `API error ${res.status}: ${path}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) errorDetail = errorData.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return res.json();
}

// Expose a thin raw request helper for ad-hoc endpoints (DELETE, custom POSTs)
export async function requestRaw(path, options = {}) {
  return request(path, options);
}

async function get(path, options = {}) {
  return request(path, options);
}

async function post(path, body, isFormData = false, options = {}) {
  const base = { method: "POST" };
  if (isFormData) {
    base.body = body;
  } else {
    base.headers = { "Content-Type": "application/json", ...(options.headers ?? {}) };
    base.body = JSON.stringify(body);
  }
  return request(path, { ...options, ...base });
}

async function put(path, body, options = {}) {
  const base = {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    body: JSON.stringify(body),
  };
  return request(path, { ...options, ...base });
}

export const api = {
  champions: () => get("/champions"),

  model1Info: () => get("/model1/info"),
  model1ShapImportance: (topN = 20) => get(`/model1/shap-importance?top_n=${topN}`),

  model2Timeseries: (championId) => get(`/model2/timeseries/${championId}`),
  model2ShiftEvents: ({ championId, minScore = 0, limit = 50 } = {}, options = {}) => {
    const params = new URLSearchParams();
    if (championId) params.set("champion_id", championId);
    if (minScore) params.set("min_score", minScore);
    params.set("limit", limit);
    return get(`/model2/shift-events?${params.toString()}`, options);
  },
  model2TopPresence: (topN = 10, options = {}) => get(`/model2/top-presence?top_n=${topN}`, options),
  matchesTournaments: ({ startDate, endDate, tournamentId, page = 1, pageSize = 20 } = {}, options = {}) => {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (tournamentId) params.set("tournament_id", tournamentId);
    params.set("page", page);
    params.set("page_size", pageSize);
    return get(`/matches/tournaments?${params.toString()}`, options);
  },
  matches: ({ tournamentId, opponentId, page = 1, pageSize = 20 } = {}, options = {}) => {
    const params = new URLSearchParams();
    if (tournamentId) params.set("tournament_id", tournamentId);
    if (opponentId) params.set("opponent_id", opponentId);
    params.set("page", page);
    params.set("page_size", pageSize);
    return get(`/matches?${params.toString()}`, options);
  },
  seriesDetail: (seriesId, options = {}) => get(`/matches/${seriesId}`, options),
  gameDetail: (gameId, options = {}) => get(`/matches/game/${gameId}`, options),

  // Stats
  statsByPatch: (options = {}) => get("/stats/winrate-by-patch", options),
  statsByTournament: (options = {}) => get("/stats/winrate-by-tournament", options),
  statsBySide: (options = {}) => get("/stats/winrate-by-side", options),
  playerWinrates: (options = {}) => get("/stats/player-winrates", options),
  playerDetail: (playerId, options = {}) => get(`/stats/player/${playerId}`, options),
  headToHead: (options = {}) => get("/stats/head-to-head", options),
  opponents: (options = {}) => get("/stats/opponents", options),
  playerVsOpponent: (playerId, opponentId, options = {}) =>
    get(`/stats/player/${playerId}/vs-opponent?opponent_id=${opponentId}`, options),

  // Model 3: Player clustering
  playerClusters: () => get("/stats/player-clusters"),

  // Model 4: Champion synergy network
  synergy: ({ year, minGames = 5, champion } = {}) => {
    const params = new URLSearchParams();
    if (year) params.set("year", year);
    params.set("min_games", minGames);
    if (champion) params.set("champion", champion);
    return get(`/stats/synergy?${params.toString()}`);
  },
  synergyTopPairs: (arg1, arg2, arg3, arg4) => {
    let limit = 20;
    let mode = "synergy";
    let minGames = 5;
    let year = null;

    if (typeof arg1 === "object" && arg1 !== null) {
      limit = arg1.limit ?? 20;
      mode = arg1.mode ?? "synergy";
      minGames = arg1.minGames ?? 5;
      year = arg1.year;
    } else {
      if (arg1 !== undefined) limit = arg1;
      if (arg2 !== undefined) mode = arg2;
      if (arg3 !== undefined) minGames = arg3;
      if (arg4 !== undefined) year = arg4;
    }

    const params = new URLSearchParams();
    params.set("limit", limit);
    params.set("mode", mode);
    params.set("min_games", minGames);
    if (year) params.set("year", year);
    return get(`/stats/synergy/top-pairs?${params.toString()}`);
  },

  // Agent API
  askAgent: (question) => post("/agent/ask", { question }),

  // Admin API
  admin: {
    champions: ({ search = "", page = 1, pageSize = 30 } = {}) =>
      get(`/admin/champions?search=${search}&page=${page}&page_size=${pageSize}`),
    players: ({ search = "", page = 1, pageSize = 30 } = {}) =>
      get(`/admin/players?search=${search}&page=${page}&page_size=${pageSize}`),
    teams: ({ search = "", page = 1, pageSize = 30 } = {}) =>
      get(`/admin/teams?search=${search}&page=${page}&page_size=${pageSize}`),
    tournaments: ({ search = "", page = 1, pageSize = 30 } = {}) =>
      get(`/admin/tournaments?search=${search}&page=${page}&page_size=${pageSize}`),
    updateChampion: (id, body) => put(`/admin/champions/${id}`, body),
    updatePlayer: (id, body) => put(`/admin/players/${id}`, body),
    updateTeam: (id, body) => put(`/admin/teams/${id}`, body),
    previewImport: (file) => {
      const form = new FormData();
      form.append("file", file);
      return post("/admin/import/preview", form, true);
    },
    import: (file) => {
      const form = new FormData();
      form.append("file", file);
      return post("/admin/import", form, true);
    },
  },
};

export const CHAMPION_IMAGE_BASE = 
  "https://ddragon.leagueoflegends.com/cdn/16.13.1/img/champion";

export function getChampionImageUrl(championName) {
  const key = championName
    .replace(/'/g, "")
    .replace(/\s+/g, "")
    .replace(/&/g, "")
    .replace(/\./g, "");
  return `${CHAMPION_IMAGE_BASE}/${key}.png`;
}
