import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import Panel from "../components/Panel";

export default function MetaShifts() {
  const [champions, setChampions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [timeseries, setTimeseries] = useState([]);
  const [events, setEvents] = useState([]);
  const [allEvents, setAllEvents] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.champions().then(setChampions);
    api.model2ShiftEvents({ limit: 100 }).then(setAllEvents);
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.model2Timeseries(selected.champion_id).then(setTimeseries);
    api
      .model2ShiftEvents({ championId: selected.champion_id, limit: 20 })
      .then(setEvents);
  }, [selected]);

  const filteredChampions = champions.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  const chartData = timeseries.map((t) => ({
    bucket: t.bucket,
    win_rate: t.win_rate !== null ? +(t.win_rate * 100).toFixed(1) : null,
    presence_rate: +(t.presence_rate * 100).toFixed(1),
  }));

  const shiftBuckets = new Set(events.map((e) => e.peak_bucket));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display font-bold text-2xl text-text">Meta Shift Detection</h1>
        <p className="text-textMuted text-sm mt-1">
          Anomaly detection trên win rate &amp; presence rate, bucket 2 tuần, có volume filter để
          loại noise.
        </p>
      </div>

      <div className="grid grid-cols-[280px_1fr] gap-6">
        {/* Champion list */}
        <Panel title="Champions" className="h-fit">
          <div className="relative mb-3">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-textMuted"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm champion..."
              className="w-full bg-bg border border-border rounded-md pl-8 pr-3 py-1.5 text-sm text-text placeholder:text-textMuted focus:outline-none focus:border-accent"
            />
          </div>
          <div className="max-h-[480px] overflow-y-auto space-y-0.5">
            {filteredChampions.map((c) => (
              <button
                key={c.champion_id}
                onClick={() => setSelected(c)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                  selected?.champion_id === c.champion_id
                    ? "bg-accent/10 text-accent"
                    : "text-textMuted hover:bg-surfaceHover hover:text-text"
                }`}
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
              <div className="py-16 text-center text-textMuted text-sm">
                Chọn 1 champion từ danh sách để xem time series chi tiết.
              </div>
            </Panel>
          ) : (
            <>
              <Panel
                title={selected.name}
                subtitle={`Win rate & presence rate theo bucket 2 tuần (2020–2025)`}
              >
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
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1A1A24",
                        border: "1px solid #2A2A38",
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: "#F5F3EE" }}
                    />
                    {[...shiftBuckets].map((b) => (
                      <ReferenceLine
                        key={b}
                        x={b}
                        stroke="#E0144C"
                        strokeDasharray="4 2"
                        strokeOpacity={0.5}
                      />
                    ))}
                    <Line
                      type="monotone"
                      dataKey="win_rate"
                      stroke="#34D399"
                      strokeWidth={2}
                      dot={false}
                      name="Win rate"
                      connectNulls
                    />
                    <Line
                      type="monotone"
                      dataKey="presence_rate"
                      stroke="#E0144C"
                      strokeWidth={2}
                      dot={false}
                      name="Presence rate"
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div className="flex items-center gap-4 mt-3 text-xs text-textMuted">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-0.5 bg-win inline-block" /> Win rate
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-0.5 bg-accent inline-block" /> Presence rate
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-px bg-accent/50 inline-block border-t border-dashed border-accent" />
                    Shift event
                  </span>
                </div>
              </Panel>

              <Panel title="Shift events" subtitle={`${events.length} events detected`}>
                {events.length === 0 ? (
                  <div className="text-sm text-textMuted py-6 text-center">
                    Không có shift event nào đạt threshold cho champion này.
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-textMuted uppercase tracking-wider border-b border-border">
                        <th className="pb-2 font-medium">Giai đoạn</th>
                        <th className="pb-2 font-medium">Kéo dài</th>
                        <th className="pb-2 font-medium">Win rate TB</th>
                        <th className="pb-2 font-medium text-right">Score</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono">
                      {events.map((e) => (
                        <tr
                          key={`${e.champion_id}-${e.start_bucket}`}
                          className="border-b border-border/50 last:border-0"
                        >
                          <td className="py-2.5 text-text">
                            {e.start_bucket}
                            {e.start_bucket !== e.end_bucket && ` → ${e.end_bucket}`}
                          </td>
                          <td className="py-2.5 text-textMuted">{e.duration_buckets} bucket</td>
                          <td className="py-2.5 text-textMuted">
                            {e.avg_win_rate !== null ? `${(e.avg_win_rate * 100).toFixed(0)}%` : "—"}
                          </td>
                          <td className="py-2.5 text-accent text-right">
                            {e.max_composite_score.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
