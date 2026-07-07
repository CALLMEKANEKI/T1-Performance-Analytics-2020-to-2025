import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import Panel from "../components/Panel";

// ─── Constants ────────────────────────────────────────────────────────────────
const YEARS = ["All", 2020, 2021, 2022, 2023, 2024, 2025];

const LIFT_COLS = [
  { key: "champion_a",  label: "Champion A",  mono: false },
  { key: "champion_b",  label: "Champion B",  mono: false },
  { key: "co_games",   label: "Games",        mono: true  },
  { key: "synergy_wr", label: "Win Rate",     mono: true  },
  { key: "lift",       label: "Lift",         mono: true  },
];

// ─── Lift Badge ───────────────────────────────────────────────────────────────
function LiftBadge({ value }) {
  if (value == null) return <span className="text-textMuted">—</span>;
  const isPos = value >= 1.0;
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded font-mono text-xs font-semibold ${
        isPos
          ? "bg-emerald-500/15 text-emerald-400"
          : "bg-rose-500/15 text-rose-400"
      }`}
    >
      {value.toFixed(3)}
    </span>
  );
}

// ─── Synergy Table ────────────────────────────────────────────────────────────
function SynergyTable({ data, mode, loading }) {
  const isTop = mode === "synergy";
  const accentColor = isTop ? "text-emerald-400" : "text-rose-400";
  const borderColor = isTop ? "border-emerald-500/20" : "border-rose-500/20";

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-9 bg-surfaceHover rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="py-12 text-center text-textMuted text-sm">
        Không có dữ liệu với bộ filter hiện tại.
      </div>
    );
  }

  return (
    <div className={`rounded-lg border ${borderColor} overflow-hidden`}>
      {/* Header */}
      <div className="grid grid-cols-[1fr_1fr_56px_72px_72px] gap-0 border-b border-border bg-bg px-4 py-2">
        {LIFT_COLS.map((col) => (
          <div key={col.key} className={`text-[11px] text-textMuted font-medium uppercase tracking-wide ${accentColor === "text-emerald-400" && col.key === "lift" ? accentColor : ""}`}>
            {col.label}
          </div>
        ))}
      </div>

      {/* Rows */}
      <div className="divide-y divide-border">
        {data.map((row, i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_1fr_56px_72px_72px] gap-0 px-4 py-2.5 hover:bg-surfaceHover transition-colors"
          >
            <span className="text-sm text-text font-medium truncate pr-2">{row.champion_a}</span>
            <span className="text-sm text-text font-medium truncate pr-2">{row.champion_b}</span>
            <span className="text-xs font-mono text-textMuted">{row.co_games}</span>
            <span className="text-xs font-mono text-textMuted">
              {row.synergy_wr != null ? `${(row.synergy_wr * 100).toFixed(1)}%` : "—"}
            </span>
            <LiftBadge value={row.lift} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Synergy() {
  const [topPairs, setTopPairs]       = useState([]);
  const [antiPairs, setAntiPairs]     = useState([]);
  const [filtered, setFiltered]       = useState([]);
  const [loading, setLoading]         = useState(true);
  const [filterLoading, setFilterLoading] = useState(false);

  // Filter state
  const [year, setYear]           = useState("All");
  const [minGames, setMinGames]   = useState(5);
  const [champion, setChampion]   = useState("");

  // Load top/anti pairs khi mount (all-time, không thay đổi)
  useEffect(() => {
    Promise.all([
      api.synergyTopPairs({ limit: 15, mode: "synergy" }),
      api.synergyTopPairs({ limit: 15, mode: "anti" }),
    ])
      .then(([top, anti]) => {
        setTopPairs(top);
        setAntiPairs(anti);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Fetch filtered list khi filter thay đổi
  const fetchFiltered = useCallback(() => {
    setFilterLoading(true);
    const params = {
      minGames: Number(minGames) || 5,
      ...(year !== "All" ? { year: Number(year) } : {}),
      ...(champion.trim() ? { champion: champion.trim() } : {}),
    };
    api.synergy(params)
      .then(setFiltered)
      .catch(() => setFiltered([]))
      .finally(() => setFilterLoading(false));
  }, [year, minGames, champion]);

  useEffect(() => {
    fetchFiltered();
  }, [fetchFiltered]);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="font-display font-bold text-2xl text-text">Champion Synergy Network</h1>
        <p className="text-textMuted text-sm mt-1 max-w-2xl">
          Phân tích synergy giữa các cặp champion T1 pick cùng team.{" "}
          <span className="text-text font-medium">Lift &gt; 1.0</span> = combo mạnh hơn baseline T1 win rate (64.5%).{" "}
          Dùng Bayesian smoothing để tránh noise khi ít games.
        </p>
      </div>

      {/* Filter bar */}
      <Panel>
        <div className="flex flex-wrap items-end gap-4">
          {/* Year */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-textMuted font-medium uppercase tracking-wide">Năm</label>
            <select
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="bg-bg border border-border rounded px-3 py-1.5 text-sm text-text focus:outline-none focus:border-accent"
            >
              {YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          {/* Min games */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-textMuted font-medium uppercase tracking-wide">Min Games</label>
            <input
              type="number"
              min={1}
              max={50}
              value={minGames}
              onChange={(e) => setMinGames(e.target.value)}
              className="w-24 bg-bg border border-border rounded px-3 py-1.5 text-sm text-text focus:outline-none focus:border-accent font-mono"
            />
          </div>

          {/* Champion search */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-textMuted font-medium uppercase tracking-wide">Champion</label>
            <input
              type="text"
              placeholder="Azir, Faker..."
              value={champion}
              onChange={(e) => setChampion(e.target.value)}
              className="w-40 bg-bg border border-border rounded px-3 py-1.5 text-sm text-text placeholder-textMuted focus:outline-none focus:border-accent"
            />
          </div>

          {/* Result count */}
          <div className="flex flex-col gap-1 ml-auto">
            <div className="text-xs text-textMuted">Kết quả</div>
            <div className="text-sm font-mono text-text">
              {filterLoading ? "..." : `${filtered.length} pairs`}
            </div>
          </div>
        </div>
      </Panel>

      {/* Filtered results khi có champion search hoặc filter khác ngoài All */}
      {(champion.trim() || year !== "All") && (
        <Panel
          title={`Kết quả lọc${year !== "All" ? ` — ${year}` : ""}${champion.trim() ? ` — ${champion}` : ""}`}
          subtitle={`Sort theo lift DESC · min ${minGames} games`}
        >
          <SynergyTable data={filtered} mode="synergy" loading={filterLoading} />
        </Panel>
      )}

      {/* Top/Anti bảng song song — All-time */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top synergy */}
        <Panel
          title="Top Synergy Pairs"
          subtitle="All-time · lift cao nhất — combo T1 dominant"
        >
          <SynergyTable data={topPairs} mode="synergy" loading={loading} />
        </Panel>

        {/* Anti synergy */}
        <Panel
          title="Anti-Synergy Pairs"
          subtitle="All-time · lift thấp nhất — combo T1 underperform"
        >
          <SynergyTable data={antiPairs} mode="anti" loading={loading} />
        </Panel>
      </div>

      {/* Info footer */}
      <div className="text-[11px] text-textMuted leading-relaxed px-1">
        <span className="font-mono">synergy_wr</span> = Bayesian smoothed win rate (α=3) ·{" "}
        <span className="font-mono">lift</span> = synergy_wr / T1 baseline (64.5%) ·{" "}
        Chỉ hiện pairs có co_games ≥ min_games threshold.
      </div>
    </div>
  );
}
