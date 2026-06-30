# T1 Performance Analytics (2020–2025)

ML-powered analytics pipeline phân tích 903 trận đấu của T1 (League of Legends, LCK) từ 2020 đến 2025 — kết hợp draft prediction, player form tracking, và meta shift detection.

## Tổng quan

Dự án này không chỉ build model, mà tập trung vào **việc đặt đúng câu hỏi nghiên cứu và đọc đúng kết quả** — kể cả khi kết quả là "model này không nên được dùng để predict outcome."

Stack: PostgreSQL (Docker) · Python (Pandas, LightGBM, XGBoost, SHAP) · FastAPI · React (đang phát triển)

---

## Data

- **Nguồn**: Match history thủ công thu thập, 2020–2025, chỉ các trận T1 tham gia (không phải toàn bộ LCK)
- **Quy mô**: 903 games, 362 series, 338 players, 334 champions, 80 patches
- **Schema**: Normalized 9 bảng (tournaments → series → games → game_teams → game_players, bans riêng)

---

## Model 1: Win Prediction from Draft + Player Form

### Hypothesis
Liệu draft (champion pick/ban), meta context (rolling win rate theo patch), và player form (rolling performance) có đủ để predict T1 thắng/thua?

### Approach
- Features: 314 cols — champion one-hot encoding, side, patch, rolling win rate (84-day window, Bayesian smoothing α=3) cho cả champion và player, player-champion mastery
- Model: LightGBM + XGBoost, evaluate bằng `TimeSeriesSplit` (5 folds) — không dùng random split vì data có temporal dependency
- Explainability: SHAP values để hiểu feature nào đóng góp nhiều nhất

### Kết quả

| Metric | LightGBM | XGBoost | Naive Baseline (luôn đoán T1 thắng) |
|---|---|---|---|
| AUC (avg 5-fold) | 0.533 | 0.523 | 0.50 |
| Accuracy (avg 5-fold) | 55.7% | 54.7% | **64.45%** |

**Model thua naive baseline.** Đây là kết luận, không phải lỗi.

### Phân tích nguyên nhân

1. **Fold 1 (giai đoạn 2020-2021) sụp mạnh nhất** (AUC ~0.33) — trùng với giai đoạn SKT → T1 rebrand, roster thay đổi liên tục, khiến `player_rolling_wr` chưa ổn định.
2. **SHAP top features** đều là rolling stats (`avg_player_wr`, `avg_champ_wr`, `side`) — model đã học đúng signal có sẵn, nhưng signal đó không đủ mạnh.
3. **Kết luận domain**: Esports outcome bị chi phối bởi micro-factors (individual mechanical skill, real-time decision making, draft order cụ thể) mà draft-level aggregation không capture được. Một model đạt AUC cao từ draft alone sẽ đáng nghi hơn là đáng tin.

### Giá trị của finding này
Thay vì optimize tiếp để "ép" accuracy lên, dự án dừng lại và chuyển hướng phân tích sang nơi data thực sự phù hợp — đó là lý do Model 2 ra đời.

---

## Model 2: Meta Shift Detection

### Hypothesis
Thay vì predict outcome, có thể detect được khi nào 1 champion trải qua "meta shift" (tăng/giảm đột biến về sức mạnh hoặc độ phổ biến) hay không?

### Approach
- Time series: mỗi champion × bucket 2 tuần → `picks`, `bans`, `win_rate`, `presence_rate` (= (picks+bans) / tổng game×2)
- Anomaly detection: composite Z-score kết hợp cả win_rate và presence_rate so với rolling baseline 12 tuần trước
  ```
  composite_score = sqrt(z_winrate² + z_presence²)
  ```
- Volume filter: loại bỏ false positive từ low-sample noise (yêu cầu ≥5 picks+bans trong bucket hiện tại, ≥15 trong baseline)
- Event merging: gộp các bucket liên tiếp thành 1 event để tránh đếm trùng

### Kết quả
- **5,178** champion-bucket data points → **302** raw shift events (sau volume filter) → **254** merged events
- Top finding: **Renekton** (2024-07), win rate 75%, presence 31%, kéo dài 2 bucket liên tiếp (4 tuần) — pattern rõ ràng của 1 buff/meta change
- **Senna** xuất hiện liên tiếp 3 bucket (6 tuần, cùng giai đoạn 2024-07) — gợi ý 1 patch lớn ảnh hưởng nhiều champion support cùng lúc

### Bài học kỹ thuật quan trọng
Lần đầu chạy không có volume filter, top events toàn là noise (composite_score 30-48 nhưng chỉ từ 1-2 picks). Đây là minh chứng cho lý do tại sao **domain knowledge + sanity check kết quả quan trọng hơn việc tin tưởng tuyệt đối vào con số thống kê.**

---

## Kiến trúc kỹ thuật

```
PostgreSQL (Docker)
    ↓ SQLAlchemy
ETL pipeline (etl.py) — parse Excel, normalize, insert
    ↓
Feature engineering (Pandas) — rolling window, Bayesian smoothing
    ↓
Model training (LightGBM/XGBoost + SHAP) | Anomaly detection (Z-score)
    ↓
FastAPI — cache layer (load 1 lần lúc startup, refresh qua endpoint)
    ↓
React dashboard (đang phát triển)
```

### API Endpoints

```
GET  /api/champions
GET  /api/model1/info
GET  /api/model1/shap-importance
GET  /api/model2/timeseries/{champion_id}
GET  /api/model2/shift-events
GET  /api/model2/top-presence
POST /api/refresh-cache
```

---

## Chạy thử local

```bash
docker compose up postgres -d
python backend/etl.py --file data/csv/T1MatchHistory_2020-2025.xlsx --db-url postgresql://t1_user:t1_password@localhost:5433/t1_analytics

cd backend
python app/pipeline/features.py
python app/pipeline/train_model1.py
python app/pipeline/model2_meta_shift.py

uvicorn app.main:app --reload --port 8000
```

---

## Những gì học được

- **Negative result là kết quả hợp lệ** — biết tại sao model không hoạt động quan trọng hơn là ép nó hoạt động.
- **TimeSeriesSplit thay vì random split** khi data có temporal dependency, nếu không sẽ leak thông tin tương lai vào quá khứ.
- **Volume threshold trong anomaly detection** — Z-score trên sample nhỏ luôn cho kết quả cực đoan giả tạo.
- **Schema mismatch debugging thực tế** — cột tên sai (`name` vs `Name`) silent fail và insert sai dữ liệu, chỉ phát hiện qua cross-checking số liệu ở nhiều bước khác nhau, không phải qua code review.

---

## Roadmap

- [ ] React dashboard hiển thị time series + shift events
- [ ] Text-to-SQL agent (natural language query vào database)
- [ ] Player-level meta shift detection (mở rộng từ champion-level)
- [ ] Deploy (Railway/Render)