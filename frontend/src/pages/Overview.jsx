import { useEffect, useState } from "react";
import { TrendingUp, AlertTriangle } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import { api } from "../lib/api";
import StatCard from "../components/StatCard";
import Panel from "../components/Panel";

const COLORS = { Blue: "#3B82F6", Red: "#E0144C" };

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
        // Gom patch có ít game (< 3) vào nhóm khác để chart không quá rối
        setPatchStats(patch.filter((p) => p.total_games >= 3));
        setSideStats(side);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) return (
    <div className="flex items-center gap-2 text-loss text-sm bg-loss/10 border border-loss/30 rounded-md px-4 py-3">
      <AlertTriangle size={16} />
      Không kết nối được API. Kiểm tra backend đang chạy ở localhost:8000.
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
      <div>
        <h1 className="font-display font-bold text-2xl text-text">Tổng quan</h1>
        <p className="text-textMuted text-sm mt-1">
          Phân tích 903 trận đấu của T1 từ 2020 đến 2025.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Tổng số trận" value="903" sublabel="2020 — 2025" />
        <StatCard label="T1 win rate" value="64.45%" sublabel="582 thắng / 321 thua" accent />
        <StatCard label="Blue side WR" value={`${(blueWR * 100).toFixed(1)}%`} sublabel="437 trận Blue side" />
        <StatCard label="Red side WR" value={`${(redWR * 100).toFixed(1)}%`} sublabel="466 trận Red side" />
      </div>

      {/* Win rate theo patch */}
      <Panel
        title="Win rate theo patch"
        subtitle="Chỉ hiển thị patch có ≥ 3 game — đường kẻ ngang 50% là baseline"
      >
        {loading ? <Skeleton h={240} /> : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={patchStats} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
              <XAxis
                dataKey="patch"
                tick={{ fontSize: 10, fill: "#7C7C8A" }}
                tickLine={false}
                axisLine={{ stroke: "#2A2A38" }}
                interval={Math.floor(patchStats.length / 10)}
              />
              <YAxis
                domain={[0, 1]}
                tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 10, fill: "#7C7C8A" }}
                tickLine={false}
                axisLine={{ stroke: "#2A2A38" }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: "#1A1A24", border: "1px solid #2A2A38", borderRadius: 6, fontSize: 12 }}
                formatter={(v, _, p) => [`${(v * 100).toFixed(1)}% (${p.payload.total_games} games)`, "Win rate"]}
                labelStyle={{ color: "#F5F3EE" }}
              />
              {/* Baseline 50% */}
              <Line type="monotone" dataKey={() => 0.5} stroke="#2A2A38" strokeDasharray="4 2" dot={false} legendType="none" />
              <Line
                type="monotone"
                dataKey="win_rate"
                stroke="#E0144C"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#E0144C" }}
                name="Win rate"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Panel>

      {/* Row 3: side stats + top presence + top events */}
      <div className="grid grid-cols-3 gap-6">
        <Panel title="Blue vs Red side">
          {loading ? <Skeleton h={160} /> : (
            <div className="flex flex-col items-center gap-3">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={65}
                    dataKey="value"
                    paddingAngle={3}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={COLORS[entry.name]} />
                    ))}
                  </Pie>
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    formatter={(v, e) => (
                      <span className="text-xs text-textMuted">
                        {v} — WR {(e.payload.win_rate * 100).toFixed(1)}%
                      </span>
                    )}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1A1A24", border: "1px solid #2A2A38", borderRadius: 6, fontSize: 12, color: "#F5F3EE" }}
                    labelStyle={{ color: "#F5F3EE" }}
                    itemStyle={{ color: "#F5F3EE" }}
                    formatter={(v, n, p) => [`${v} games · WR ${(p.payload.win_rate * 100).toFixed(1)}%`, n]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel title="Champion presence cao nhất" subtitle="Trung bình toàn dataset">
          {loading ? <Skeleton h={160} /> : (
            <div className="space-y-3">
              {topPresence.map((c, i) => (
                <div key={c.champion_id} className="flex items-center gap-3">
                  <span className="text-textMuted font-mono text-xs w-4">{i + 1}</span>
                  <span className="flex-1 text-sm text-text">{c.name}</span>
                  <div className="flex items-center gap-2 w-32">
                    <div className="flex-1 h-1.5 bg-bg rounded-full overflow-hidden">
                      <div className="h-full bg-accent rounded-full" style={{ width: `${c.presence_rate * 100}%` }} />
                    </div>
                    <span className="font-mono text-xs text-textMuted w-10 text-right">
                      {(c.presence_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Meta shift gần đây" subtitle="Composite score cao nhất">
          {loading ? <Skeleton h={160} /> : (
            <div className="space-y-3">
              {topEvents.map((e) => (
                <div key={`${e.champion_id}-${e.start_bucket}`} className="flex items-center gap-3">
                  <TrendingUp size={14} className="text-accent shrink-0" />
                  <span className="flex-1 text-sm text-text">{e.name}</span>
                  <span className="text-xs text-textMuted font-mono">{e.start_bucket}</span>
                  <span className="font-mono text-xs text-accent w-12 text-right">
                    {e.max_composite_score.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* About */}
      <Panel title="Về dự án">
        <p className="text-sm text-textMuted leading-relaxed">
          Model 1 (win prediction từ draft) đạt AUC 0.53, thấp hơn naive baseline 64.45% —
          kết luận rằng micro-factors trong gameplay quan trọng hơn draft-level features.
          Model 2 (meta shift detection) phát hiện 254 events có ý nghĩa thống kê sau khi lọc nhiễu.
        </p>
      </Panel>
    </div>
  );
}

function Skeleton({ h }) {
  return <div className={`h-[${h}px] bg-surfaceHover rounded animate-pulse`} style={{ height: h }} />;
}