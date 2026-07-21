import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Zap, Shield, Swords, Filter } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import Panel from "../components/Panel";
import StatCard from "../components/StatCard";

const TYPE_COLORS = {
  carry_damage: "#E0144C",
  tank_engage: "#3B82F6",
  utility_support: "#A78BFA",
  assassin_skirmisher: "#F59E0B",
  poke_control: "#34D399",
  unknown: "#7C7C8A",
};

const TYPE_LABELS = {
  carry_damage: "Carry",
  tank_engage: "Tank",
  utility_support: "Support",
  assassin_skirmisher: "Assassin",
  poke_control: "Poke",
  unknown: "Unknown",
};

function TypeBadge({ type }) {
  const color = TYPE_COLORS[type] ?? TYPE_COLORS.unknown;
  const label = TYPE_LABELS[type] ?? type;
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
      style={{ color, backgroundColor: `${color}18`, border: `1px solid ${color}30` }}
    >
      {label}
    </span>
  );
}

function LiftBar({ lift }) {
  const pct = Math.min(Math.abs((lift - 1) * 100), 30);
  const positive = lift >= 1.0;
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-bg rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-500", positive ? "bg-win" : "bg-loss")}
          style={{ width: `${(pct / 30) * 100}%` }}
        />
      </div>
      <span className={clsx("font-mono text-xs font-medium", positive ? "text-win" : "text-loss")}>
        {positive ? "+" : ""}{((lift - 1) * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function PairRow({ pair, rank }) {
  const positive = pair.lift >= 1.0;
  return (
    <tr className="border-b border-border/50 last:border-0 hover:bg-surfaceHover/30 transition-colors group">
      <td className="py-3 pl-4 pr-2">
        <span className="text-xs font-mono text-textMuted">{rank}</span>
      </td>
      <td className="py-3 pr-3">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-text">{pair.champion_a}</span>
            <TypeBadge type={pair.type_a} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm text-textMuted">{pair.champion_b}</span>
            <TypeBadge type={pair.type_b} />
          </div>
        </div>
      </td>
      <td className="py-3 pr-3">
        <span className="text-xs font-mono text-textMuted">{pair.co_games} games</span>
      </td>
      <td className="py-3 pr-3">
        <span className={clsx(
          "text-xs font-mono px-2 py-0.5 rounded-full",
          pair.synergy_wr >= 0.65 ? "bg-win/10 text-win" : pair.synergy_wr <= 0.45 ? "bg-loss/10 text-loss" : "text-textMuted"
        )}>
          {(pair.synergy_wr * 100).toFixed(0)}%
        </span>
      </td>
      <td className="py-3 pr-4">
        <LiftBar lift={pair.lift} />
      </td>
    </tr>
  );
}

export default function Synergy() {
  const [topPairs, setTopPairs] = useState([]);
  const [antiPairs, setAntiPairs] = useState([]);
  const [year, setYear] = useState("");
  const [minGames, setMinGames] = useState(5);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("synergy");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.synergyTopPairs(20, "synergy", minGames, year || null),
      api.synergyTopPairs(20, "anti", minGames, year || null),
    ])
      .then(([top, anti]) => {
        setTopPairs(top);
        setAntiPairs(anti);
      })
      .finally(() => setLoading(false));
  }, [year, minGames]);

  const displayed = activeTab === "synergy" ? topPairs : antiPairs;

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">Champion Synergy Network</h1>
        <p className="text-textMuted text-sm mt-1">
          Lift-based scoring · Bayesian smoothed win rate · 527 unique pairs từ 903 games T1.
        </p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-4 stagger-children">
        <StatCard label="Unique pairs" value="527" sublabel="Sau filter ≥5 games" />
        <StatCard
          label="Top synergy"
          value={topPairs[0] ? `${((topPairs[0].lift - 1) * 100).toFixed(0)}%` : "—"}
          sublabel={topPairs[0] ? `${topPairs[0].champion_a} + ${topPairs[0].champion_b}` : "Loading..."}
          accent
        />
        <StatCard
          label="Global T1 baseline"
          value="64.5%"
          sublabel="Win rate tổng, dùng làm baseline lift"
        />
      </div>

      {/* Giải thích */}
      <Panel variant="glass" title="Về Synergy Score">
        <div className="grid grid-cols-3 gap-6 text-xs text-textMuted leading-relaxed">
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Zap size={13} className="text-accent" />
              <span className="font-medium text-text">Lift Score</span>
            </div>
            <p>Lift = synergy_wr / global_baseline_wr (64.5%). Lift &gt; 1.0 có nghĩa combo này thắng cao hơn mức trung bình T1.</p>
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Shield size={13} className="text-win" />
              <span className="font-medium text-text">Bayesian Smoothing</span>
            </div>
            <p>Win rate được smooth về 50% khi ít data (α=3), tránh noise từ combo chỉ xuất hiện 1-2 lần.</p>
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Swords size={13} className="text-textMuted" />
              <span className="font-medium text-text">Cross-lane Synergy</span>
            </div>
            <p>is_cross_lane = True khi 2 champion thuộc khác type — thể hiện synergy giữa các role thay vì cùng role.</p>
          </div>
        </div>
      </Panel>

      {/* Filter + Tab */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 border-b border-border">
          {[
            { id: "synergy", label: "Top Synergy", icon: TrendingUp, color: "text-win" },
            { id: "anti", label: "Anti Synergy", icon: TrendingDown, color: "text-loss" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
                activeTab === tab.id
                  ? tab.id === "synergy" ? "border-win text-win" : "border-loss text-loss"
                  : "border-transparent text-textMuted hover:text-text"
              )}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-xs text-textMuted">
          <Filter size={12} />
          <span>Min games:</span>
          <select
            value={minGames}
            onChange={(e) => setMinGames(Number(e.target.value))}
            className="bg-surface border border-border rounded-lg px-2 py-1 text-xs text-text focus:outline-none focus:border-accent"
          >
            {[5, 8, 10, 15, 20].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <Panel loading={loading}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {["#", "Champion Pair", "Games", "Win Rate", "Lift"].map((h) => (
                  <th key={h} className={clsx(
                    "text-left text-xs text-textMuted uppercase tracking-widest pb-3 font-medium",
                    h === "#" ? "pl-4 pr-2 w-8" : "pr-3"
                  )}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayed.map((pair, i) => (
                <PairRow
                  key={`${pair.champion_a}-${pair.champion_b}`}
                  pair={pair}
                  rank={i + 1}
                />
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Type distribution insight */}
      <Panel title="Champion type breakdown" subtitle="Phân phối type trong top synergy pairs">
        <div className="flex flex-wrap gap-2">
          {Object.entries(TYPE_COLORS).filter(([k]) => k !== "unknown").map(([type, color]) => {
            const count = topPairs.filter(
              (p) => p.type_a === type || p.type_b === type
            ).length;
            if (count === 0) return null;
            return (
              <div
                key={type}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl border"
                style={{ borderColor: `${color}30`, backgroundColor: `${color}10` }}
              >
                <span className="text-xs font-medium" style={{ color }}>{TYPE_LABELS[type]}</span>
                <span className="text-xs font-mono text-textMuted">{count}</span>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}