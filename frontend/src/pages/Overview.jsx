import { useEffect, useState } from "react";
import { TrendingUp, AlertTriangle, Trophy, Swords, Activity } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";
import { api } from "../lib/api";
import StatCard from "../components/StatCard";
import Panel from "../components/Panel";

const COLORS = { Blue: "#3B82F6", Red: "#E0144C" };

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
};

export default function Overview() {
  const [topPresence, setTopPresence] = useState([]);
  const [topEvents, setTopEvents] = useState([]);
  const [patchStats, setPatchStats] = useState([]);
  const [sideStats, setSideStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.model2TopPresence(5),
      api.model2ShiftEvents({ limit: 5 }),
      api.statsByPatch(),
      api.statsBySide(),
    ])
      .then(([presence, events, patch, side]) => {
        setTopPresence(presence);
        setTopEvents(events);
        setPatchStats(patch.filter((p) => p.total_games >= 3));
        setSideStats(side);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) return (
    <div className="flex items-center gap-2 text-loss text-sm bg-loss/10 border border-loss/30 rounded-xl px-4 py-3 animate-fade-in">
      <AlertTriangle size={16} />
      Không kết nối được API.
    </div>
  );

  const blueWR = sideStats.find((s) => s.side === "Blue")?.win_rate ?? 0;
  const redWR = sideStats.find((s) => s.side === "Red")?.win_rate ?? 0;
  const pieData = sideStats.map((s) => ({
    name: s.side,
    value: s.total_games,
    win_rate: s.win_rate,
  }));

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">Tổng quan</h1>
        <p className="text-textMuted text-sm mt-1">Phân tích 903 trận đấu của T1 từ 2020 đến 2025.</p>
      </div>

      <div className="grid grid-cols-4 gap-4 stagger-children">
        <StatCard label="Tổng số trận" value="903" sublabel="2020 — 2025" />
        <StatCard label="T1 win rate" value="64%" sublabel="582 thắng / 321 thua" accent />
        <StatCard label="Blue side WR" value={`${(blueWR * 100).toFixed(0)}%`} sublabel="437 trận Blue side" />
        <StatCard label="Red side WR" value={`${(redWR * 100).toFixed(0)}%`} sublabel="466 trận Red side" />
      </div>

      <Panel title="Win rate theo patch" subtitle="Chỉ hiển thị patch có ≥ 3 game" loading={loading}>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={patchStats} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="wrGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#E0144C" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#E0144C" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
            <XAxis dataKey="patch" tick={{ fontSize: 10, fill: "#7C7C8A" }} tickLine={false} axisLine={{ stroke: "#2A2A38" }} interval={Math.floor(patchStats.length / 10)} />
            <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 10, fill: "#7C7C8A" }} tickLine={false} axisLine={{ stroke: "#2A2A38" }} />
            <Tooltip {...TOOLTIP_STYLE} formatter={(v, _, p) => [`${(v * 100).toFixed(1)}% (${p.payload.total_games} games)`, "Win rate"]} />
            <Area type="monotone" dataKey="win_rate" stroke="#E0144C" strokeWidth={2} fill="url(#wrGradient)" dot={false} activeDot={{ r: 4, fill: "#E0144C" }} name="Win rate" />
          </AreaChart>
        </ResponsiveContainer>
      </Panel>

      <div className="grid grid-cols-3 gap-6">
        <Panel title="Blue vs Red side" loading={loading}>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={65} dataKey="value" paddingAngle={3} animationBegin={0} animationDuration={800}>
                {pieData.map((entry) => <Cell key={entry.name} fill={COLORS[entry.name]} />)}
              </Pie>
              <Legend iconType="circle" iconSize={8} formatter={(v, e) => <span className="text-xs text-textMuted">{v} — WR {(e.payload.win_rate * 100).toFixed(1)}%</span>} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v, n, p) => [`${v} games · WR ${(p.payload.win_rate * 100).toFixed(1)}%`, n]} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Champion presence cao nhất" subtitle="Trung bình toàn dataset" loading={loading}>
          <div className="space-y-3">
            {topPresence.map((c, i) => (
              <div key={c.champion_id} className="flex items-center gap-3 animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                <span className="text-textMuted font-mono text-xs w-4">{i + 1}</span>
                <span className="flex-1 text-sm text-text">{c.name}</span>
                <div className="flex items-center gap-2 w-32">
                  <div className="flex-1 h-1.5 bg-bg rounded-full overflow-hidden">
                    <div className="h-full bg-accent rounded-full transition-all duration-700" style={{ width: `${c.presence_rate * 100}%` }} />
                  </div>
                  <span className="font-mono text-xs text-textMuted w-10 text-right">{(c.presence_rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Meta shift gần đây" subtitle="Composite score cao nhất" loading={loading}>
          <div className="space-y-3">
            {topEvents.map((e, i) => (
              <div key={`${e.champion_id}-${e.start_bucket}`} className="flex items-center gap-3 animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                <TrendingUp size={14} className="text-accent shrink-0" />
                <span className="flex-1 text-sm text-text">{e.name}</span>
                <span className="text-xs text-textMuted font-mono">{e.start_bucket}</span>
                <span className="font-mono text-xs text-accent w-12 text-right">{e.max_composite_score.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Panel variant="accent">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center shrink-0">
              <Trophy size={18} className="text-accent" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-widest text-textMuted mb-0.5">Worlds vô địch</div>
              <div className="font-display font-bold text-xl text-text">6 lần</div>
              <div className="text-xs text-textMuted">2023, 2024, 2025 gần nhất</div>
            </div>
          </div>
        </Panel>

        <Panel variant="accent">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-win/10 flex items-center justify-center shrink-0">
              <Activity size={18} className="text-win" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-widest text-textMuted mb-0.5">Meta shift events</div>
              <div className="font-display font-bold text-xl text-text">254</div>
              <div className="text-xs text-textMuted">Sau volume filter</div>
            </div>
          </div>
        </Panel>

        <Panel variant="accent">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center shrink-0">
              <Swords size={18} className="text-accent" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-widest text-textMuted mb-0.5">Champion pool</div>
              <div className="font-display font-bold text-xl text-text">172</div>
              <div className="text-xs text-textMuted">Unique champions</div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Về dự án" variant="glass">
        <p className="text-sm text-textMuted leading-relaxed">
          Model 1 (win prediction từ draft) đạt AUC 0.53, thấp hơn naive baseline 64.45%.
          Model 2 (meta shift detection) phát hiện 254 events có ý nghĩa thống kê.
          Model 3 (player clustering) phân nhóm 13 T1 players thành 3 career tiers.
          Model 4 (champion synergy) phân tích 527 cặp champion với lift-based scoring.
        </p>
      </Panel>
    </div>
  );
}
