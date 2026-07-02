import { useEffect, useState } from "react";
import { api, STATIC_BASE } from "../lib/api";
import Panel from "../components/Panel";
import StatCard from "../components/StatCard";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Legend,
} from "recharts";

const POSITION_ORDER = ["TOP", "JUNGLER", "MID", "ADC", "BOT", "SUPPORT"];

const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "#1A1A24",
    border: "1px solid #2A2A38",
    borderRadius: 6,
    fontSize: 12,
    color: "#F5F3EE",
  },
  labelStyle: { color: "#F5F3EE" },
  cursor: { fill: "rgba(255,255,255,0.04)" },
};

export default function Players() {
  const [players, setPlayers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [champLimit, setChampLimit] = useState(20);

  useEffect(() => {
    api.playerWinrates()
      .then((data) => {
        const sorted = [...data].sort((a, b) => {
          const ai = POSITION_ORDER.indexOf(a.position ?? "");
          const bi = POSITION_ORDER.indexOf(b.position ?? "");
          if (ai !== bi) return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
          return b.total_games - a.total_games;
        });
        setPlayers(sorted);
        const faker = sorted.find((p) => p.ingame_name === "Faker");
        if (faker) setSelected(faker);
      })
      .finally(() => setLoadingList(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoadingDetail(true);
    setDetail(null);
    api.playerDetail(selected.id_player)
      .then(setDetail)
      .finally(() => setLoadingDetail(false));
  }, [selected]);

  // Champion pool: lấy tất cả, cắt theo limit
  const allChamps = detail?.champion_pool ?? [];
  const champData = allChamps.slice(0, champLimit).map((c) => ({
    name: c.champion_name,
    wins: c.wins,
    losses: c.games_played - c.wins,
    games: c.games_played,
    win_rate: +(c.win_rate * 100).toFixed(1),
  }));

  const yearlyData = detail?.yearly_stats?.map((y) => ({
    year: String(Math.round(y.year)),
    win_rate: +(y.win_rate * 100).toFixed(1),
    games: y.total_games,
  })) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display font-bold text-2xl text-text">Player Dashboard</h1>
        <p className="text-textMuted text-sm mt-1">
          Stats cá nhân, champion pool và win rate theo mùa giải.
        </p>
      </div>

      <div className="grid grid-cols-[260px_1fr] gap-6">
        {/* Player list */}
        <Panel title="Roster T1" className="h-fit">
          {loadingList ? (
            <div className="space-y-2">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-12 bg-surfaceHover rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-0.5 max-h-[560px] overflow-y-auto">
              {players.map((p) => (
                <button
                  key={p.id_player}
                  onClick={() => setSelected(p)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors text-left ${
                    selected?.id_player === p.id_player
                      ? "bg-accent/10 text-accent"
                      : "hover:bg-surfaceHover text-textMuted hover:text-text"
                  }`}
                >
                  <img
                    src={`${STATIC_BASE}/static/players/${encodeURIComponent(p.ingame_name)}.png`}
                    alt={p.ingame_name}
                    className="w-8 h-8 rounded-full object-cover bg-bg border border-border shrink-0"
                    onError={(e) => { e.currentTarget.style.display = "none"; }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{p.ingame_name}</div>
                    <div className="text-[11px] text-textMuted">{p.position ?? "—"}</div>
                  </div>
                  <span className="font-mono text-xs shrink-0">
                    {(p.win_rate * 100).toFixed(0)}%
                  </span>
                </button>
              ))}
            </div>
          )}
        </Panel>

        {/* Detail */}
        <div className="space-y-6">
          {!selected ? (
            <Panel>
              <div className="py-16 text-center text-textMuted text-sm">
                Chọn 1 player để xem chi tiết.
              </div>
            </Panel>
          ) : loadingDetail ? (
            <Panel><div className="h-40 bg-surfaceHover rounded animate-pulse" /></Panel>
          ) : detail && (
            <>
              {/* Header */}
              <div className="flex items-center gap-5">
                <img
                  src={`${STATIC_BASE}/static/players/${encodeURIComponent(selected.ingame_name)}.png`}
                  alt={selected.ingame_name}
                  className="w-16 h-16 rounded-full object-cover border-2 border-accent bg-bg"
                  onError={(e) => { e.currentTarget.style.display = "none"; }}
                />
                <div>
                  <h2 className="font-display font-bold text-xl text-text">
                    {selected.ingame_name}
                  </h2>
                  <p className="text-textMuted text-sm">{detail.info.full_name ?? "—"}</p>
                  <p className="text-xs text-textMuted mt-0.5">
                    {selected.position ?? "—"} · {detail.info.country ?? "—"}
                  </p>
                </div>
              </div>

              {/* KPI */}
              <div className="grid grid-cols-3 gap-4">
                <StatCard label="Tổng số trận" value={selected.total_games} sublabel="Toàn bộ 2020–2025" />
                <StatCard
                  label="Win rate"
                  value={`${(selected.win_rate * 100).toFixed(1)}%`}
                  sublabel={`${selected.wins} thắng / ${selected.total_games - selected.wins} thua`}
                  accent
                />
                <StatCard label="Champion pool" value={allChamps.length} sublabel="Champions đã chơi" />
              </div>

              {/* Win rate theo năm */}
              <Panel title="Win rate theo năm">
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={yearlyData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
                    <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#7C7C8A" }} tickLine={false} axisLine={{ stroke: "#2A2A38" }} />
                    <YAxis
                      domain={[40, 100]}
                      tickFormatter={(v) => `${v}%`}
                      tick={{ fontSize: 11, fill: "#7C7C8A" }}
                      tickLine={false}
                      axisLine={{ stroke: "#2A2A38" }}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={(v, _, p) => [`${v}% (${p.payload.games} games)`, "Win rate"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="win_rate"
                      stroke="#E0144C"
                      strokeWidth={2}
                      dot={{ fill: "#E0144C", r: 4 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Panel>

              {/* Champion pool */}
              <Panel
                title="Champion pool"
                subtitle={`${allChamps.length} champions — cột chồng thắng/thua, đường = win rate`}
                action={
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-textMuted">Hiển thị</span>
                    <select
                      value={champLimit}
                      onChange={(e) => setChampLimit(Number(e.target.value))}
                      className="bg-bg border border-border rounded px-2 py-1 text-xs text-text focus:outline-none focus:border-accent"
                    >
                      {[10, 20, 30, 50, 999].map((n) => (
                        <option key={n} value={n}>{n === 999 ? "Tất cả" : n}</option>
                      ))}
                    </select>
                    <span className="text-xs text-textMuted">champions</span>
                  </div>
                }
              >
                <div
                  className="overflow-y-auto"
                  style={{ maxHeight: 480 }}
                >
                    <div style={{ height: Math.max(260, champData.length * 48) }}>
                    <ResponsiveContainer
                      width="100%"
                      height="100%"
                    >
                      <ComposedChart
                        data={champData}
                        layout="vertical"
                        margin={{ top: 4, right: 60, left: 80, bottom: 4 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" horizontal={false} />
                        <XAxis
                          type="number"
                          tick={{ fontSize: 10, fill: "#7C7C8A" }}
                          axisLine={{ stroke: "#2A2A38" }}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={{ fontSize: 11, fill: "#F5F3EE" }}
                          axisLine={{ stroke: "#2A2A38" }}
                          tickLine={false}
                          width={76}
                        />
                        <Tooltip
                          {...TOOLTIP_STYLE}
                          formatter={(v, name) => {
                            if (name === "wins") return [`${v} thắng`, "Thắng"];
                            if (name === "losses") return [`${v} thua`, "Thua"];
                            if (name === "win_rate") return [`${v}%`, "Win rate"];
                            return [v, name];
                          }}
                        />
                        <Legend
                          iconType="circle"
                          iconSize={8}
                          formatter={(v) => (
                            <span className="text-xs text-textMuted">
                              {v === "wins" ? "Thắng" : v === "losses" ? "Thua" : "Win rate"}
                            </span>
                          )}
                        />
                        {/* Stacked bars */}
                        <Bar dataKey="wins" stackId="a" fill="#34D399" fillOpacity={0.85} radius={[0, 0, 0, 0]} name="wins" />
                        <Bar dataKey="losses" stackId="a" fill="#E0144C" fillOpacity={0.6} radius={[0, 3, 3, 0]} name="losses" />
                        {/* Win rate line (dùng trục Y riêng) */}
                        <YAxis
                          yAxisId="wr"
                          orientation="right"
                          type="number"
                          domain={[0, 100]}
                          tickFormatter={(v) => `${v}%`}
                          tick={{ fontSize: 10, fill: "#7C7C8A" }}
                          axisLine={{ stroke: "#2A2A38" }}
                          tickLine={false}
                          width={44}
                        />
                        <Line
                          yAxisId="wr"
                          type="monotone"
                          dataKey="win_rate"
                          stroke="#F59E0B"
                          strokeWidth={1.5}
                          dot={false}
                          name="win_rate"
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                    </div>
                  </div>
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}