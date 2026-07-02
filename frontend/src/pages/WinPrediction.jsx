import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { AlertTriangle } from "lucide-react";
import { api } from "../lib/api";
import Panel from "../components/Panel";
import StatCard from "../components/StatCard";

export default function WinPrediction() {
  const [info, setInfo] = useState(null);
  const [shap, setShap] = useState([]);

  useEffect(() => {
    api.model1Info().then(setInfo);
    api.model1ShapImportance(15).then(setShap);
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
      <div>
        <h1 className="font-display font-bold text-2xl text-text">Win Prediction Model</h1>
        <p className="text-textMuted text-sm mt-1">
          LightGBM trên draft + rolling form features — đánh giá bằng TimeSeriesSplit.
        </p>
      </div>

      <div className="flex items-start gap-3 bg-accent/5 border border-accent/30 rounded-lg px-5 py-4">
        <AlertTriangle size={18} className="text-accent shrink-0 mt-0.5" />
        <div className="text-sm text-text leading-relaxed">
          <span className="font-semibold">Model không vượt qua baseline.</span> Đây là kết luận
          chính của phần phân tích này, không phải lỗi kỹ thuật — xem phần giải thích bên dưới.
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="LightGBM AUC" value="0.533" sublabel="Trung bình 5-fold" />
        <StatCard label="LightGBM Accuracy" value="55.7%" sublabel="Trung bình 5-fold" />
        <StatCard
          label="Naive baseline"
          value="64.45%"
          sublabel="Luôn đoán T1 thắng"
          accent
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Panel title="Feature importance (SHAP)" subtitle="Top 15 features đóng góp nhiều nhất">
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A38" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: "#7C7C8A" }} axisLine={{ stroke: "#2A2A38" }} />
              <YAxis
                type="category"
                dataKey="feature"
                tick={{ fontSize: 11, fill: "#F5F3EE" }}
                width={150}
                axisLine={{ stroke: "#2A2A38" }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1A1A24",
                  border: "1px solid #2A2A38",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                cursor={{ fill: "#22222E" }}
              />
              <Bar dataKey="importance" radius={[0, 3, 3, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill="#E0144C" fillOpacity={0.4 + (i / chartData.length) * 0.6} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Phân tích kết quả">
          <div className="space-y-4 text-sm text-textMuted leading-relaxed">
            <div>
              <h4 className="text-text font-medium mb-1">1. Temporal instability</h4>
              <p>
                Fold đầu tiên (giai đoạn 2020–2021) có AUC thấp nhất (~0.33), trùng với giai đoạn
                roster T1 thay đổi liên tục sau khi rebrand từ SKT. Rolling player form chưa đủ
                dữ liệu lịch sử để ổn định.
              </p>
            </div>
            <div>
              <h4 className="text-text font-medium mb-1">2. Top features hợp lý nhưng chưa đủ mạnh</h4>
              <p>
                SHAP cho thấy model học đúng signal — rolling win rate của player và champion là
                features quan trọng nhất. Vấn đề không phải feature sai, mà là signal quá yếu so
                với noise từ in-game execution.
              </p>
            </div>
            <div>
              <h4 className="text-text font-medium mb-1">3. Kết luận</h4>
              <p>
                Esports outcome bị chi phối mạnh bởi micro-factors (mechanical skill, real-time
                decision making) mà draft-level aggregation không capture được. Một model đạt AUC
                cao bất thường từ draft alone sẽ đáng nghi hơn là đáng tin.
              </p>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function formatFeatureName(name) {
  return name
    .replace(/^t1_/, "T1 ")
    .replace(/^opp_/, "Opp ")
    .replace(/_/g, " ")
    .replace(/\bavg\b/, "avg.")
    .replace(/\bwr\b/, "win rate")
    .replace(/^\w/, (c) => c.toUpperCase());
}
