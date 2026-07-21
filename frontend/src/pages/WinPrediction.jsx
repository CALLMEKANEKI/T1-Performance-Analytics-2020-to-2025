import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { AlertTriangle, Brain, TrendingDown, Info } from "lucide-react";
import { api } from "../lib/api";
import Panel from "../components/Panel";
import StatCard from "../components/StatCard";
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
  cursor: { fill: "rgba(255,255,255,0.04)" },
};

function formatFeatureName(name) {
  return name
    .replace(/^t1_/, "T1 ")
    .replace(/^opp_/, "Opp ")
    .replace(/_/g, " ")
    .replace(/\bavg\b/, "avg.")
    .replace(/\bwr\b/, "win rate")
    .replace(/^\w/, (c) => c.toUpperCase());
}

function InsightCard({ icon: Icon, title, description, variant = "default" }) {
  const variants = {
    default: "border-border",
    warning: "border-loss/30 bg-loss/5",
    info: "border-accent/30 bg-accent/5",
  };
  return (
    <div className={clsx("bg-surface border rounded-xl p-4", variants[variant])}>
      <div className="flex items-start gap-3">
        <div className={clsx(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
          variant === "warning" ? "bg-loss/10" : variant === "info" ? "bg-accent/10" : "bg-surface border border-border"
        )}>
          <Icon size={15} className={variant === "warning" ? "text-loss" : variant === "info" ? "text-accent" : "text-textMuted"} />
        </div>
        <div>
          <div className="text-sm font-medium text-text mb-1">{title}</div>
          <p className="text-xs text-textMuted leading-relaxed">{description}</p>
        </div>
      </div>
    </div>
  );
}

export default function WinPrediction() {
  const [info, setInfo] = useState(null);
  const [shap, setShap] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.model1Info(), api.model1ShapImportance(15)])
      .then(([i, s]) => { setInfo(i); setShap(s); })
      .finally(() => setLoading(false));
  }, []);

  const chartData = shap
    .slice()
    .reverse()
    .map((s) => ({
      feature: formatFeatureName(s.feature),
      importance: +s.mean_shap.toFixed(3),
    }));

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-display font-bold text-2xl text-text tracking-tight">Win Prediction Model</h1>
        <p className="text-textMuted text-sm mt-1">
          LightGBM trên draft + rolling form features — đánh giá bằng TimeSeriesSplit 5-fold.
        </p>
      </div>

      {/* Banner cảnh báo */}
      <div className="flex items-start gap-3 bg-loss/5 border border-loss/30 rounded-xl px-5 py-4 animate-fade-in">
        <AlertTriangle size={18} className="text-loss shrink-0 mt-0.5" />
        <div>
          <div className="text-sm font-semibold text-text mb-0.5">Model không vượt qua baseline</div>
          <p className="text-xs text-textMuted leading-relaxed">
            AUC 0.53 thấp hơn naive baseline (luôn đoán T1 thắng = 64.45% accuracy). Đây là kết luận phân tích, không phải lỗi kỹ thuật — xem giải thích bên dưới.
          </p>
        </div>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-4 stagger-children">
        <StatCard
          label="LightGBM AUC"
          value="0.53"
          sublabel="Trung bình 5-fold TimeSeriesSplit"
        />
        <StatCard
          label="Accuracy"
          value="55.7%"
          sublabel="Trung bình 5-fold"
          trend={{ value: -8.75, label: "pp vs baseline" }}
        />
        <StatCard
          label="Naive Baseline"
          value="64.45%"
          sublabel="Luôn đoán T1 thắng"
          accent
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* SHAP chart */}
        <Panel
          title="Feature Importance (SHAP)"
          subtitle="Top 15 features đóng góp nhiều nhất vào prediction"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 10, fill: "#7C7C8A" }}
                axisLine={{ stroke: "#2A2A38" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="feature"
                tick={{ fontSize: 11, fill: "#F5F3EE" }}
                width={155}
                axisLine={{ stroke: "#2A2A38" }}
                tickLine={false}
              />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]} name="SHAP importance">
                {chartData.map((_, i) => (
                  <Cell
                    key={i}
                    fill="#E0144C"
                    fillOpacity={0.25 + (i / chartData.length) * 0.75}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        {/* Phân tích */}
        <div className="space-y-4">
          <Panel title="Phân tích kết quả" loading={loading}>
            <div className="space-y-4">
              <InsightCard
                icon={TrendingDown}
                variant="warning"
                title="Fold 1 (2020–2021) sụp mạnh nhất"
                description="AUC ~0.33 trong giai đoạn này — trùng với thời điểm SKT → T1 rebrand và roster thay đổi liên tục. Rolling player form chưa đủ historical data để ổn định."
              />
              <InsightCard
                icon={Brain}
                variant="info"
                title="SHAP top features hợp lý nhưng signal yếu"
                description="Model học đúng signal — rolling win rate của player và champion là features quan trọng nhất. Vấn đề không phải features sai, mà là signal quá yếu so với noise từ in-game execution."
              />
              <InsightCard
                icon={Info}
                title="Kết luận domain"
                description="Esports outcome bị chi phối mạnh bởi micro-factors (mechanical skill, real-time decision making) mà draft-level aggregation không capture được. Đây là irreducible error của bài toán với data hiện có."
              />
            </div>
          </Panel>

          {/* Model info */}
          {info && (
            <Panel title="Model metadata" variant="glass">
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-textMuted">Model type</span>
                  <span className="text-text">{info.model_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-textMuted">Features</span>
                  <span className="text-text">{info.n_features}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-textMuted">Validation</span>
                  <span className="text-text">TimeSeriesSplit (5-fold)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-textMuted">Training data</span>
                  <span className="text-text">903 games (2020–2025)</span>
                </div>
              </div>
            </Panel>
          )}
        </div>
      </div>

      {/* Timeline fold performance */}
      <Panel title="Performance theo fold (temporal)" subtitle="Fold sau = data mới hơn — model cải thiện dần theo thời gian">
        <div className="grid grid-cols-5 gap-3">
          {[
            { fold: 1, auc: 0.35, period: "2020–2021", note: "Cold start" },
            { fold: 2, auc: 0.57, period: "2021–2022", note: "Roster ổn định" },
            { fold: 3, auc: 0.54, period: "2022–2023", note: "—" },
            { fold: 4, auc: 0.59, period: "2023–2024", note: "Tốt nhất" },
            { fold: 5, auc: 0.60, period: "2024–2025", note: "Tốt nhất" },
          ].map((f) => (
            <div key={f.fold} className="bg-bg border border-border rounded-xl p-3 text-center">
              <div className="text-xs text-textMuted mb-1">Fold {f.fold}</div>
              <div className={clsx(
                "font-display font-bold text-xl mb-1",
                f.auc < 0.5 ? "text-loss" : f.auc >= 0.58 ? "text-win" : "text-textMuted"
              )}>
                {f.auc}
              </div>
              <div className="text-[10px] text-textMuted">{f.period}</div>
              {f.note !== "—" && (
                <div className="text-[10px] text-accent mt-1">{f.note}</div>
              )}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}