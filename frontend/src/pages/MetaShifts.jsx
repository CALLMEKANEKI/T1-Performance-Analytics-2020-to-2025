import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { Search, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { api } from "../lib/api";
import Panel from "../components/Panel";
import clsx from "clsx";

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

function LiftBadge({ lift }) {
  if (!lift) return null;
  const positive = lift >= 1.05;
  const negative = lift < 0.95;
  return (
    <span className={clsx(
      "flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded-full",
      positive ? "bg-win/10 text-win border border-win/20"
        : negative ? "bg-loss/10 text-loss border border-loss/20"
          : "bg-surface text-textMuted border border-border"
    )}>
      {positive ? <TrendingUp size={10} /> : negative ? <TrendingDown size={10} /> : <Minus size={10} />}
      {lift.toFixed(2)}
    </span>
  );
}

export default function MetaShifts() {
  const [champions, setChampions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [timeseries, setTimeseries] = useState([]);
  const [events, setEvents] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.champions().then(setChampions);
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.model2Timeseries(selected.champion_id).then(setTimeseries);
    api.model2ShiftEvents({ championId: selected.champion_id, limit: 20 }).then(setEvents);
  }, [selected]);

  const filtered = champions.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  const chartData = timeseries.map((t) => ({
    bucket: t.bucket,
    win_rate: t.win_rate !== null ? +(t.win_rate * 100).toFixed(1) : null,
    presence_rate: +(t.presence_rate * 100).toFixed(1),
  }));

  const shiftBuckets = new Set(events.map((e) => e.peak_bucket));

  // Stats tổng hợp
  const avgWR = timeseries.length
    ? (timeseries.reduce((s, t) => s + (t.win_rate ?? 0), 0) / timeseries.filter(t => t.win_rate !== null).length * 100).toFixed(1)
    : null;
  const totalPicks = timeseries.reduce((s, t) => s + (t.picks ?? 0), 0);
  const totalBans = timeseries.reduce((s, t) => s + (t.bans ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">Meta Shift Detection</h1>
        <p className="text-textMuted text-sm mt-1">
          Anomaly detection trên win rate & presence rate · bucket 2 tuần · volume filter ≥5.
        </p>
      </div>

      <div className="grid grid-cols-[280px_1fr] gap-6">
        {/* Champion list */}
        <Panel title="Champions" className="h-fit">
          <div className="relative mb-3">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-textMuted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm champion..."
              className="w-full bg-bg border border-border rounded-lg pl-8 pr-3 py-1.5 text-sm text-text placeholder:text-textMuted focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          <div className="max-h-[520px] overflow-y-auto space-y-0.5">
            {filtered.map((c) => (
              <button
                key={c.champion_id}
                onClick={() => setSelected(c)}
                className={clsx(
                  "w-full text-left px-3 py-2 rounded-lg text-sm transition-all",
                  selected?.champion_id === c.champion_id
                    ? "bg-accent/10 text-accent font-medium"
                    : "text-textMuted hover:bg-surfaceHover hover:text-text"
                )}
              >
                {c.name}
              </button>
            ))}
          </div>
        </Panel>

        {/* Main content */}
        <div className="space-y-6">
          {!selected ? (
            <Panel>
              <div className="py-20 text-center">
                <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center mx-auto mb-3">
                  <TrendingUp size={20} className="text-textMuted" />
                </div>
                <p className="text-textMuted text-sm">Chọn 1 champion từ danh sách để xem time series chi tiết.</p>
              </div>
            </Panel>
          ) : (
            <>
              {/* Quick stats */}
              {timeseries.length > 0 && (
                <div className="grid grid-cols-3 gap-4 animate-fade-in">
                  <div className="bg-surface border border-border rounded-xl px-4 py-3">
                    <div className="text-xs uppercase tracking-widest text-textMuted mb-1">Avg Win Rate</div>
                    <div className="font-display font-bold text-2xl text-text">{avgWR}%</div>
                  </div>
                  <div className="bg-surface border border-border rounded-xl px-4 py-3">
                    <div className="text-xs uppercase tracking-widest text-textMuted mb-1">Total Picks</div>
                    <div className="font-display font-bold text-2xl text-text">{totalPicks}</div>
                  </div>
                  <div className="bg-surface border border-border rounded-xl px-4 py-3">
                    <div className="text-xs uppercase tracking-widest text-textMuted mb-1">Shift Events</div>
                    <div className="font-display font-bold text-2xl text-accent">{events.length}</div>
                  </div>
                </div>
              )}

              {/* Chart */}
              <Panel
                title={selected.name}
                subtitle="Win rate & presence rate theo bucket 2 tuần (2020–2025) · Đường đỏ dọc = shift event"
              >
                {timeseries.length === 0 ? (
                  <div className="py-12 text-center text-textMuted text-sm">
                    Champion này không có đủ data trong khoảng thời gian phân tích.
                  </div>
                ) : (
                  <>
                    <ResponsiveContainer width="100%" height={280}>
                      <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" />
                        <XAxis
                          dataKey="bucket"
                          tick={{ fontSize: 10, fill: "#7C7C8A" }}
                          tickLine={false}
                          axisLine={{ stroke: "#2A2A38" }}
                          interval={Math.floor(chartData.length / 8)}
                        />
                        <YAxis
                          tick={{ fontSize: 10, fill: "#7C7C8A" }}
                          tickLine={false}
                          axisLine={{ stroke: "#2A2A38" }}
                          unit="%"
                        />
                        <Tooltip {...TOOLTIP_STYLE} />
                        <Legend
                          iconType="circle"
                          iconSize={8}
                          formatter={(v) => <span className="text-xs text-textMuted">
                            {v === "win_rate" ? "Win rate" : "Presence rate"}
                          </span>}
                        />
                        {[...shiftBuckets].map((b) => (
                          <ReferenceLine
                            key={b}
                            x={b}
                            stroke="#E0144C"
                            strokeDasharray="4 2"
                            strokeOpacity={0.6}
                            strokeWidth={1.5}
                          />
                        ))}
                        <Line
                          type="monotone"
                          dataKey="win_rate"
                          stroke="#34D399"
                          strokeWidth={2}
                          dot={false}
                          name="win_rate"
                          connectNulls
                        />
                        <Line
                          type="monotone"
                          dataKey="presence_rate"
                          stroke="#E0144C"
                          strokeWidth={2}
                          dot={false}
                          name="presence_rate"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                    <div className="flex items-center gap-4 mt-3 text-xs text-textMuted">
                      <span className="flex items-center gap-1.5">
                        <span className="w-3 h-0.5 bg-win inline-block rounded" /> Win rate
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-3 h-0.5 bg-accent inline-block rounded" /> Presence rate
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-3 h-px bg-accent/50 inline-block border-t border-dashed border-accent" /> Shift event
                      </span>
                    </div>
                  </>
                )}
              </Panel>

              {/* Events table */}
              <Panel
                title="Shift events"
                subtitle={`${events.length} events detected cho ${selected.name}`}
              >
                {events.length === 0 ? (
                  <div className="text-sm text-textMuted py-6 text-center">
                    Không có shift event nào đạt threshold cho champion này.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          {["Giai đoạn", "Kéo dài", "Win rate TB", "Score"].map((h) => (
                            <th key={h} className="text-left text-xs text-textMuted uppercase tracking-widest pb-3 pr-6 font-medium">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="font-mono">
                        {events.map((e) => (
                          <tr key={`${e.champion_id}-${e.start_bucket}`} className="border-b border-border/50 last:border-0 hover:bg-surfaceHover/30 transition-colors">
                            <td className="py-3 pr-6 text-text">
                              {e.start_bucket}
                              {e.start_bucket !== e.end_bucket && (
                                <span className="text-textMuted"> → {e.end_bucket}</span>
                              )}
                            </td>
                            <td className="py-3 pr-6 text-textMuted">{e.duration_buckets} bucket</td>
                            <td className="py-3 pr-6 text-textMuted">
                              {e.avg_win_rate !== null ? `${(e.avg_win_rate * 100).toFixed(0)}%` : "—"}
                            </td>
                            <td className="py-3">
                              <span className="text-accent font-medium">{e.max_composite_score.toFixed(2)}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}