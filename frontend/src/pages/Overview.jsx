import { useEffect, useState } from "react";
import { TrendingUp, AlertTriangle, Trophy, Swords, Activity } from "lucide-react";
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";
import { api } from "../lib/api";
import { CHART_COLORS, LEGEND_PROPS, TOOLTIP_STYLE, legendFormatter } from "../lib/chartUtils";
import StatCard from "../components/StatCard";
import Panel from "../components/Panel";
import ChampionAvatar from "../components/ChampionAvatar";
import { images, IMAGE_FALLBACKS } from "../config/images";

const SIDE_COLORS = { Blue: CHART_COLORS.blue, Red: CHART_COLORS.redSide };

export default function Overview() {
  const [topPresence, setTopPresence] = useState([]);
  const [topEvents, setTopEvents] = useState([]);
  const [patchStats, setPatchStats] = useState([]);
  const [sideStats, setSideStats] = useState([]);
  const [h2h, setH2h] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const ctrl = new AbortController();
    const signal = ctrl.signal;

    Promise.all([
      api.model2TopPresence(5, { signal }),
      api.model2ShiftEvents({ limit: 5 }, { signal }),
      api.statsByPatch({ signal }),
      api.statsBySide({ signal }),
      api.headToHead({ signal }),
    ])
      .then(([presence, events, patch, side, headToHeadData]) => {
        setTopPresence(presence || []);
        setTopEvents(events || []);
        setPatchStats((patch || []).filter((item) => item.total_games >= 3));
        setSideStats(side || []);
        setH2h(headToHeadData || []);
      })
      .catch((e) => {
        if (e?.name === "AbortError") return;
        setError(e.message || String(e));
      })
      .finally(() => setLoading(false));

    return () => ctrl.abort();
  }, []);

  const blueData = sideStats.find((item) => item.side === "Blue");
  const redData = sideStats.find((item) => item.side === "Red");
  const totalGames = sideStats.reduce((sum, item) => sum + (Number(item.total_games) || 0), 0);
  const totalWins = sideStats.reduce((sum, item) => sum + (Number(item.t1_wins) || 0), 0);
  const totalLosses = Math.max(totalGames - totalWins, 0);
  const blueWR = blueData?.win_rate ?? 0;
  const redWR = redData?.win_rate ?? 0;

  const pieData = sideStats.map((item) => ({
    name: item.side,
    value: Number(item.total_games) || 0,
    win_rate: Number(item.win_rate) || 0,
  }));

  const heroStyle = {
    backgroundImage: images.overviewHero
      ? `linear-gradient(90deg, rgba(5,5,10,.96) 0%, rgba(5,5,10,.78) 48%, rgba(5,5,10,.35) 100%), url("${images.overviewHero}")`
      : IMAGE_FALLBACKS.overviewHero,
    backgroundPosition: "center",
    backgroundSize: "cover",
  };

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-loss/40 bg-loss/10 px-4 py-3 text-sm text-loss">
        <AlertTriangle size={16} />
        Không kết nối được API. Vui lòng kiểm tra backend và thử tải lại trang.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section
        className="flex min-h-[116px] items-center rounded-xl border border-border px-6 py-5 sm:px-8"
        style={heroStyle}
      >
        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-accent">T1 Esports · 2020—2025</div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-text sm:text-3xl">Performance Overview</h1>
          <p className="mt-1 text-sm text-textMuted">Tổng quan dữ liệu thi đấu và hiệu suất của T1.</p>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 stagger-children">
        <StatCard
          label="Tổng số trận"
          value={totalGames ? totalGames.toLocaleString() : loading ? "…" : "—"}
          sublabel="Tổng hợp từ Blue + Red side"
        />
        <StatCard
          label="T1 win rate"
          value={totalGames ? `${((totalWins / totalGames) * 100).toFixed(1)}%` : "—"}
          sublabel={totalGames ? `${totalWins} thắng / ${totalLosses} thua` : "Chưa có dữ liệu"}
          accent
        />
        <StatCard
          label="Blue side WR"
          value={blueData ? `${(blueWR * 100).toFixed(1)}%` : "—"}
          sublabel={blueData ? `${blueData.total_games} trận Blue side` : "Chưa có dữ liệu"}
        />
        <StatCard
          label="Red side WR"
          value={redData ? `${(redWR * 100).toFixed(1)}%` : "—"}
          sublabel={redData ? `${redData.total_games} trận Red side` : "Chưa có dữ liệu"}
        />
      </div>

      <Panel title="Win rate theo patch" subtitle="Chỉ hiển thị patch có ≥ 3 game" loading={loading}>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={patchStats} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="wrGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={CHART_COLORS.accent} stopOpacity={0.3} />
                <stop offset="95%" stopColor={CHART_COLORS.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.border} />
            <XAxis dataKey="patch" tick={{ fontSize: 10, fill: CHART_COLORS.textMuted }} tickLine={false} axisLine={{ stroke: CHART_COLORS.border }} interval={Math.max(0, Math.floor(patchStats.length / 10))} />
            <YAxis domain={[0, 1]} tickFormatter={(value) => `${(value * 100).toFixed(0)}%`} tick={{ fontSize: 10, fill: CHART_COLORS.textMuted }} tickLine={false} axisLine={{ stroke: CHART_COLORS.border }} />
            <Tooltip {...TOOLTIP_STYLE} formatter={(value, _name, point) => [`${(value * 100).toFixed(1)}% (${point.payload.total_games} games)`, "Win rate"]} />
            <Area type="monotone" dataKey="win_rate" stroke={CHART_COLORS.accent} strokeWidth={2} fill="url(#wrGradient)" dot={false} activeDot={{ r: 4, fill: CHART_COLORS.accent }} name="Win rate" />
          </AreaChart>
        </ResponsiveContainer>
      </Panel>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Panel title="Blue vs Red side" loading={loading}>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={48} outerRadius={70} dataKey="value" paddingAngle={3} animationBegin={0} animationDuration={800}>
                {pieData.map((entry) => <Cell key={entry.name} fill={SIDE_COLORS[entry.name] || CHART_COLORS.gray} />)}
              </Pie>
              <Legend {...LEGEND_PROPS} formatter={(value, entry) => `${legendFormatter()(value)} — WR ${((entry.payload.win_rate || 0) * 100).toFixed(1)}%`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(value, name, point) => [`${value} games · WR ${((point.payload.win_rate || 0) * 100).toFixed(1)}%`, name]} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Champion presence cao nhất" subtitle="Trung bình toàn dataset" loading={loading}>
          <div className="space-y-3">
            {topPresence.map((champion, index) => (
              <div key={champion.champion_id} className="flex items-center gap-3" >
                <span className="w-4 text-xs font-mono text-textMuted">{index + 1}</span>
                <ChampionAvatar championName={champion.name} size={28} />
                <span className="min-w-0 flex-1 truncate text-sm text-text">{champion.name}</span>
                <div className="flex w-32 items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-bg">
                    <div className="h-full rounded-full bg-accent transition-all duration-700" style={{ width: `${champion.presence_rate * 100}%` }} />
                  </div>
                  <span className="w-10 text-right font-mono text-xs text-textMuted">{(champion.presence_rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
            {!loading && topPresence.length === 0 && <p className="text-sm text-textMuted">Không có dữ liệu champion.</p>}
          </div>
        </Panel>

        <Panel title="Meta shift gần đây" subtitle="Composite score cao nhất" loading={loading}>
          <div className="space-y-3">
            {topEvents.map((event) => (
              <div key={`${event.champion_id}-${event.start_bucket}`} className="flex items-center gap-3">
                <TrendingUp size={14} className="shrink-0 text-accent" />
                <span className="min-w-0 flex-1 truncate text-sm text-text">{event.name}</span>
                <span className="font-mono text-xs text-textMuted">{event.start_bucket}</span>
                <span className="w-12 text-right font-mono text-xs text-accent">{Number(event.max_composite_score).toFixed(1)}</span>
              </div>
            ))}
            {!loading && topEvents.length === 0 && <p className="text-sm text-textMuted">Không có sự kiện meta shift.</p>}
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Panel variant="accent">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/10"><Trophy size={18} className="text-accent" /></div>
            <div>
              <div className="mb-0.5 text-xs uppercase tracking-widest text-textMuted">Worlds vô địch</div>
              <div className="font-display text-xl font-bold text-text">6 lần</div>
              <div className="text-xs text-textMuted">2023, 2024, 2025 gần nhất</div>
            </div>
          </div>
        </Panel>
        <Panel variant="accent">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-win/10"><Activity size={18} className="text-win" /></div>
            <div>
              <div className="mb-0.5 text-xs uppercase tracking-widest text-textMuted">Meta shift events</div>
              <div className="font-display text-xl font-bold text-text">254</div>
              <div className="text-xs text-textMuted">Sau volume filter</div>
            </div>
          </div>
        </Panel>
        <Panel variant="accent">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent/10"><Swords size={18} className="text-accent" /></div>
            <div>
              <div className="mb-0.5 text-xs uppercase tracking-widest text-textMuted">Champion pool</div>
              <div className="font-display text-xl font-bold text-text">172</div>
              <div className="text-xs text-textMuted">Unique champions</div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Lịch sử đối đầu" subtitle="Top 10 đối thủ T1 đã gặp nhiều nhất" loading={loading}>
        <div className="overflow-x-auto rounded-xl border border-border bg-surfaceAlt/50">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-border bg-bg/50">
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-widest text-textMuted">Đối thủ</th>
                <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-widest text-textMuted">Series W-L</th>
                <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-widest text-textMuted">Games</th>
                <th className="px-4 py-3 text-xs font-medium uppercase tracking-widest text-textMuted">Win Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {h2h.slice(0, 10).map((row) => (
                <tr key={row.opponent_id} className="transition-colors hover:bg-surfaceHover/30">
                  <td className="px-4 py-3.5 text-sm font-medium text-text">{row.opponent_name}</td>
                  <td className="px-4 py-3.5 text-center font-mono text-sm">
                    <span className="font-semibold text-win">{row.t1_series_wins}W</span>
                    <span className="mx-1 text-textMuted">—</span>
                    <span className="font-semibold text-loss">{row.total_series - row.t1_series_wins}L</span>
                  </td>
                  <td className="px-4 py-3.5 text-center font-mono text-sm text-textMuted">{row.total_games}</td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex min-w-[64px] items-center justify-center gap-1 rounded-full px-2.5 py-1 font-mono text-xs font-semibold ${
                        row.game_win_rate >= 0.6
                          ? "bg-win/10 text-win"
                          : row.game_win_rate <= 0.45
                          ? "bg-loss/10 text-loss"
                          : "bg-white/5 text-textMuted"
                      }`}>
                        {row.game_win_rate <= 0.45 && <span aria-hidden="true">▼</span>}
                        {(row.game_win_rate * 100).toFixed(1)}%
                      </span>
                      <div className="hidden h-1.5 w-24 shrink-0 overflow-hidden rounded-full border border-border/50 bg-bg sm:block">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            row.game_win_rate >= 0.6 ? "bg-win"
                              : row.game_win_rate <= 0.45 ? "bg-loss"
                              : "bg-textMuted"
                          }`}
                          style={{ width: `${row.game_win_rate * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && h2h.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-sm text-textMuted">Chưa có dữ liệu đối đầu.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Về dự án" variant="glass">
        <p className="text-sm leading-relaxed text-textMuted">
          Model 1 (win prediction từ draft) đạt accuracy 55.7% so với naive baseline 64.45%; AUC đạt 0.533 so với baseline AUC 0.50.
          Model 2 phát hiện 254 meta shift events sau khi gộp các sự kiện liên tiếp.
          Model 3 phân nhóm hồ sơ thi đấu của người chơi T1; Model 4 phân tích 527 cặp champion theo điểm synergy.
          Phân tích chi tiết từng mô hình được trình bày tại các trang chức năng tương ứng.
        </p>
      </Panel>
    </div>
  );
}
