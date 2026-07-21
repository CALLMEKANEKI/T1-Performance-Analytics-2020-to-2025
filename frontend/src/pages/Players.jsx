import { useEffect, useState } from "react";
import { api, STATIC_BASE } from "../lib/api";
import Panel from "../components/Panel";
import StatCard from "../components/StatCard";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, ScatterChart, Scatter, ZAxis, Legend,
} from "recharts";
import clsx from "clsx";

const POSITION_ORDER = ["TOP", "JUNGLER", "MID", "ADC", "SUPPORT"];

const POSITION_COLORS = {
  TOP: "#F59E0B",
  JUNGLER: "#34D399",
  MID: "#3B82F6",
  ADC: "#E0144C",
  SUPPORT: "#A78BFA",
  default: "#7C7C8A",
};

const CLUSTER_COLORS = {
  "Core Roster": "#E0144C",
  "Veteran": "#34D399",
  "Outlier": "#7C7C8A",
};

const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "#1A1A24",
    border: "1px solid #2A2A38",
    borderRadius: 8,
    fontSize: 12,
    color: "#F5F3EE",
  },
  labelStyle: { color: "#F5F3EE" },
  itemStyle: { color: "#F5F3EE" },
  cursor: { fill: "rgba(255,255,255,0.04)" },
};

function PlayerAvatar({ name, size = "md" }) {
  const [imgError, setImgError] = useState(false);
  const sizeClass = size === "lg" ? "w-16 h-16 text-lg" : "w-8 h-8 text-xs";

  if (imgError) {
    return (
      <div className={clsx(
        sizeClass,
        "rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center font-display font-bold text-accent shrink-0"
      )}>
        {name?.charAt(0)?.toUpperCase()}
      </div>
    );
  }

  return (
    <img
      src={`${STATIC_BASE}/static/players/${encodeURIComponent(name)}.png`}
      alt={name}
      className={clsx(sizeClass, "rounded-full object-cover border border-border bg-bg shrink-0")}
      onError={() => setImgError(true)}
    />
  );
}

export default function Players() {
  const [players, setPlayers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [champLimit, setChampLimit] = useState(20);
  const [activeTab, setActiveTab] = useState("stats"); // "stats" | "clustering"

  useEffect(() => {
    Promise.all([api.playerWinrates(), api.playerClusters()])
      .then(([pData, cData]) => {
        const sorted = [...pData].sort((a, b) => {
          const ai = POSITION_ORDER.indexOf(a.position ?? "");
          const bi = POSITION_ORDER.indexOf(b.position ?? "");
          if (ai !== bi) return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
          return b.total_games - a.total_games;
        });
        setPlayers(sorted);
        setClusters(cData || []);
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

  // Scatter plot data từ clusters
  const scatterData = clusters.map((c) => ({
    ...c,
    color: CLUSTER_COLORS[c.cluster_label] ?? "#7C7C8A",
  }));

  const clusterGroups = ["Core Roster", "Veteran", "Outlier"].map((label) => ({
    label,
    color: CLUSTER_COLORS[label],
    data: scatterData.filter((d) => d.cluster_label === label),
  }));

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">Player Dashboard</h1>
        <p className="text-textMuted text-sm mt-1">Stats cá nhân, champion pool và win rate theo mùa giải.</p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 border-b border-border">
        {[{ id: "stats", label: "Player Stats" }, { id: "clustering", label: "Career Clustering" }].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === tab.id
                ? "border-accent text-accent"
                : "border-transparent text-textMuted hover:text-text"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB: Player Stats ── */}
      {activeTab === "stats" && (
        <div className="grid grid-cols-[260px_1fr] gap-6">
          {/* Player list */}
          <Panel title="Roster T1" className="h-fit" loading={loadingList}>
            <div className="space-y-0.5 max-h-[560px] overflow-y-auto">
              {players.map((p) => {
                const posColor = POSITION_COLORS[p.position] ?? POSITION_COLORS.default;
                return (
                  <button
                    key={p.id_player}
                    onClick={() => setSelected(p)}
                    className={clsx(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group",
                      selected?.id_player === p.id_player
                        ? "bg-accent/10 text-accent"
                        : "hover:bg-surfaceHover text-textMuted hover:text-text"
                    )}
                  >
                    <PlayerAvatar name={p.ingame_name} />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium truncate">{p.ingame_name}</div>
                      <div className="text-[11px]" style={{ color: posColor }}>{p.position ?? "—"}</div>
                    </div>
                    <span className="font-mono text-xs shrink-0">{(p.win_rate * 100).toFixed(0)}%</span>
                  </button>
                );
              })}
            </div>
          </Panel>

          {/* Detail */}
          <div className="space-y-6">
            {!selected ? (
              <Panel><div className="py-16 text-center text-textMuted text-sm">Chọn 1 player để xem chi tiết.</div></Panel>
            ) : loadingDetail ? (
              <Panel loading={true}><div className="h-40" /></Panel>
            ) : detail && (
              <>
                {/* Header */}
                <div className="flex items-center gap-5 animate-fade-in">
                  <PlayerAvatar name={selected.ingame_name} size="lg" />
                  <div>
                    <h2 className="font-display font-bold text-xl text-text">{selected.ingame_name}</h2>
                    <p className="text-textMuted text-sm">{detail.info.full_name ?? "—"}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className="text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{
                          color: POSITION_COLORS[selected.position] ?? POSITION_COLORS.default,
                          backgroundColor: `${POSITION_COLORS[selected.position] ?? POSITION_COLORS.default}1A`,
                        }}
                      >
                        {selected.position ?? "—"}
                      </span>
                      <span className="text-xs text-textMuted">{detail.info.country ?? "—"}</span>
                    </div>
                  </div>
                </div>

                {/* KPI */}
                <div className="grid grid-cols-3 gap-4 stagger-children">
                  <StatCard label="Tổng số trận" value={selected.total_games} sublabel="Toàn bộ 2020–2025" />
                  <StatCard
                    label="Win rate"
                    value={`${(selected.win_rate * 100).toFixed(0)}%`}
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
                      <YAxis domain={[40, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: "#7C7C8A" }} tickLine={false} axisLine={{ stroke: "#2A2A38" }} />
                      <Tooltip {...TOOLTIP_STYLE} formatter={(v, _, p) => [`${v}% (${p.payload.games} games)`, "Win rate"]} />
                      <Line type="monotone" dataKey="win_rate" stroke="#E0144C" strokeWidth={2} dot={{ fill: "#E0144C", r: 4 }} activeDot={{ r: 5 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </Panel>

                {/* Champion pool */}
                <Panel
                  title="Champion pool"
                  subtitle={`Top ${champData.length} champions hay chơi nhất`}
                  action={
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-textMuted">Hiển thị</span>
                      <select
                        value={champLimit}
                        onChange={(e) => setChampLimit(Number(e.target.value))}
                        className="bg-bg border border-border rounded-lg px-2 py-1 text-xs text-text focus:outline-none focus:border-accent"
                      >
                        {[10, 20, 30, 50, 999].map((n) => (
                          <option key={n} value={n}>{n === 999 ? "Tất cả" : n}</option>
                        ))}
                      </select>
                    </div>
                  }
                >
                  <div className="overflow-y-auto" style={{ maxHeight: 480 }}>
                    <div style={{ height: Math.max(260, champData.length * 32) }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={champData} layout="vertical" margin={{ top: 4, right: 60, left: 80, bottom: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" horizontal={false} />
                          <XAxis type="number" tick={{ fontSize: 10, fill: "#7C7C8A" }} axisLine={{ stroke: "#2A2A38" }} tickLine={false} />
                          <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#F5F3EE" }} axisLine={{ stroke: "#2A2A38" }} tickLine={false} width={76} />
                          <Tooltip {...TOOLTIP_STYLE} formatter={(v, name) => {
                            if (name === "wins") return [`${v} thắng`, "Thắng"];
                            if (name === "losses") return [`${v} thua`, "Thua"];
                            if (name === "win_rate") return [`${v}%`, "Win rate"];
                            return [v, name];
                          }} />
                          <Legend iconType="circle" iconSize={8} formatter={(v) => (
                            <span className="text-xs text-textMuted">
                              {v === "wins" ? "Thắng" : v === "losses" ? "Thua" : "Win rate"}
                            </span>
                          )} />
                          <Bar dataKey="wins" stackId="a" fill="#34D399" fillOpacity={0.85} name="wins" />
                          <Bar dataKey="losses" stackId="a" fill="#E0144C" fillOpacity={0.6} radius={[0, 3, 3, 0]} name="losses" />
                          <YAxis yAxisId="wr" orientation="right" type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 10, fill: "#7C7C8A" }} axisLine={{ stroke: "#2A2A38" }} tickLine={false} width={44} />
                          <Line yAxisId="wr" type="monotone" dataKey="win_rate" stroke="#F59E0B" strokeWidth={1.5} dot={false} name="win_rate" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </Panel>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── TAB: Career Clustering ── */}
      {activeTab === "clustering" && (
        <div className="space-y-6 animate-fade-in">
          <Panel
            title="Player Career Clustering"
            subtitle="KMeans K=3 · Silhouette Score 0.76 · PCA 2D projection"
          >
            <div className="grid grid-cols-3 gap-4 mb-6">
              {clusterGroups.map((g) => (
                <div key={g.label} className="bg-bg rounded-xl p-4 border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: g.color }} />
                    <span className="text-sm font-medium text-text">{g.label}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {g.data.map((p) => (
                      <span key={p.player_id} className="text-xs px-2 py-0.5 rounded-full border" style={{ color: g.color, borderColor: `${g.color}40`, backgroundColor: `${g.color}10` }}>
                        {p.player_name}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <ResponsiveContainer width="100%" height={380}>
              <ScatterChart margin={{ top: 20, right: 20, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
                <XAxis
                  type="number"
                  dataKey="PC1"
                  name="PC1"
                  tick={{ fontSize: 10, fill: "#7C7C8A" }}
                  tickLine={false}
                  axisLine={{ stroke: "#2A2A38" }}
                  label={{ value: "PC1 (Career Experience)", position: "bottom", offset: 0, fill: "#7C7C8A", fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="PC2"
                  name="PC2"
                  tick={{ fontSize: 10, fill: "#7C7C8A" }}
                  tickLine={false}
                  axisLine={{ stroke: "#2A2A38" }}
                  label={{ value: "PC2", angle: -90, position: "insideLeft", fill: "#7C7C8A", fontSize: 11 }}
                />
                <ZAxis range={[80, 80]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1A1A24", border: "1px solid #2A2A38", borderRadius: 8, fontSize: 12, color: "#F5F3EE" }}
                  cursor={{ stroke: "#2A2A38" }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.[0]) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-surface border border-border rounded-xl px-3 py-2.5 text-xs space-y-1">
                        <div className="font-display font-semibold text-text">{d.player_name}</div>
                        <div className="text-textMuted">{d.cluster_label}</div>
                        <div className="text-textMuted">Win rate: <span className="text-text">{(d.overall_winrate * 100).toFixed(1)}%</span></div>
                        <div className="text-textMuted">Games: <span className="text-text">{d.total_games}</span></div>
                      </div>
                    );
                  }}
                />
                {clusterGroups.map((g) => (
                  <Scatter
                    key={g.label}
                    name={g.label}
                    data={g.data}
                    fill={g.color}
                    fillOpacity={0.85}
                  />
                ))}
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(v) => <span className="text-xs text-textMuted">{v}</span>}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Giải thích clusters" variant="glass">
            <div className="grid grid-cols-3 gap-6 text-sm">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-accent" />
                  <span className="font-medium text-text">Core Roster</span>
                </div>
                <p className="text-textMuted text-xs leading-relaxed">Backbone của T1 qua các mùa giải — nhiều games, win rate cao và ổn định. Faker, Keria, Oner, Zeus, Gumayusi và các players chủ lực.</p>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-win" />
                  <span className="font-medium text-text">Veteran</span>
                </div>
                <p className="text-textMuted text-xs leading-relaxed">Players có career arc khác — không phải core dynasty nhưng đóng góp đáng kể trong các giai đoạn cụ thể. Effort, Doran và cựu tuyển thủ.</p>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-textMuted" />
                  <span className="font-medium text-text">Outlier</span>
                </div>
                <p className="text-textMuted text-xs leading-relaxed">Players với profile khác biệt hoàn toàn về số games và win rate — thường là substitute hoặc trial players trong thời gian ngắn.</p>
              </div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}