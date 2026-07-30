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

async function get(path) {
  return request(path);
}

async function post(path, body, isFormData = false) {
  const options = { method: "POST" };
  if (isFormData) {
    options.body = body;
  } else {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  return request(path, options);
}

async function put(path, body) {
  return request(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
  matchesTournaments: ({ startDate, endDate, page = 1, pageSize = 20 } = {}) => {
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    params.set("page", page);
    params.set("page_size", pageSize);
    return get(`/matches/tournaments?${params.toString()}`);
  },
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
  headToHead: () => get("/stats/head-to-head"),
  opponents: () => get("/stats/opponents"),
  playerVsOpponent: (playerId, opponentId) =>
    get(`/stats/player/${playerId}/vs-opponent?opponent_id=${opponentId}`),

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
