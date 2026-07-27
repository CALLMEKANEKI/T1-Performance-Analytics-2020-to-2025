# T1 Performance Analytics (2020–2025)

ML-powered analytics platform phân tích 903 trận đấu của T1 (League of Legends, LCK) từ 2020 đến 2025 — kết hợp 4 ML models, Text-to-SQL agent, và dashboard tương tác đầy đủ.

🔗 **Live Demo:** [t1-performance-analytics-2020-to-20.vercel.app](https://t1-performance-analytics-2020-to-20.vercel.app)

---

## Tổng quan

Dự án này không chỉ build model mà tập trung vào **việc đặt đúng câu hỏi nghiên cứu và đọc đúng kết quả** — kể cả khi kết quả là "model này không nên được dùng để predict outcome."

**Stack:** PostgreSQL (Neon) · Python (Pandas, LightGBM, XGBoost, SHAP, scikit-learn) · FastAPI · React + Tailwind CSS · Groq/Claude/OpenAI (Text-to-SQL Agent)

**Deploy:** Neon (DB) · Render (Backend) · Vercel (Frontend)

---

## Data

- **Nguồn:** Match history thủ công thu thập, 2020–2025, chỉ các trận T1 tham gia
- **Quy mô:** 903 games · 362 series · 338 players · 334 champions · 80 patches · 45 tournaments
- **Schema:** Normalized 9 bảng (tournaments → series → games → game_teams → game_players, bans riêng)

---

## 4 ML Models

### Model 1: Win Prediction from Draft + Player Form

**Hypothesis:** Liệu draft, meta context và player form có đủ để predict T1 thắng/thua?

**Approach:**
- 314 features: champion one-hot, side, patch, rolling win rate 84-day window (Bayesian smoothing α=3), player-champion mastery
- LightGBM + XGBoost, evaluate bằng `TimeSeriesSplit` 5-fold (không dùng random split vì temporal dependency)
- SHAP values để explain model

**Kết quả:**

| Metric | LightGBM | XGBoost | Naive Baseline |
|--------|----------|---------|----------------|
| AUC (avg 5-fold) | 0.533 | 0.523 | 0.50 |
| Accuracy | 55.7% | 54.7% | **64.45%** |

**Model thua naive baseline** — đây là kết luận, không phải lỗi. SHAP analysis chỉ ra player form quan trọng hơn champion pick, consistent với quan điểm pro community về T1.

---

### Model 2: Meta Shift Detection

**Hypothesis:** Có thể detect được khi nào champion trải qua "meta shift" không?

**Approach:**
- Time series: mỗi champion × bucket 2 tuần → pick/ban/win rate, presence rate
- Anomaly detection: composite Z-score = √(z_winrate² + z_presence²) so với rolling baseline 12 tuần
- Volume filter: ≥5 picks+bans/bucket, ≥15 trong baseline
- Consecutive event merging

**Kết quả:** 5,178 champion-bucket data points → 302 raw events → **254 merged events**

**Top finding:** Renekton (2024-07), win rate 75%, presence 31%, kéo dài 4 tuần — pattern rõ của buff/meta change.

---

### Model 3: Player Career Clustering

**Hypothesis:** Có thể phân nhóm T1 players theo career profile không?

**Approach:**
- KMeans K=3, features: overall/blue/red winrate, yearly winrate, champion pool stats, HHI specialization, career trend
- RobustScaler + PCA(2D) để visualize
- Silhouette Score: **0.76**

**Kết quả:**

| Cluster | Players | Avg Win Rate | Avg Games |
|---------|---------|-------------|-----------|
| Core Roster | Faker, Keria, Oner, Zeus, Gumayusi... | 65.7% | 709 |
| Veteran | Effort, Doran | 64.2% | 145 |
| Outlier | Smash | 53.6% | 28 |

---

### Model 4: Champion Synergy Network

**Hypothesis:** Champion nào T1 hay pick cùng nhau và synergy ra sao?

**Approach:**
- Generate pairs từ itertools.combinations(5 picks, 2) mỗi game
- Synergy score: Bayesian smoothed win rate + lift = synergy_wr / global_baseline_wr (64.5%)
- Lift > 1.0 = synergy dương so với baseline T1

**Kết quả:** **527 unique pairs** · Top: Azir + Varus (lift 1.27) · Anti: Kindred + Nautilus (lift 0.42)

---

## Text-to-SQL Agent

Natural language query vào database — hỗ trợ nhiều LLM providers:

```
User: "Top 5 champion T1 pick nhiều nhất năm 2023?"
Agent: SELECT c.name, COUNT(*) ... → Azir (42), Xayah (28), Sejuani (27)...
```

**Providers:** Groq · Claude · OpenAI · OpenRouter · Ollama (local)

**Config qua `.env`:**
```
AGENT_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## Features

- **Overview:** Win rate theo patch (area chart), Blue/Red side stats, meta shift events, head-to-head history
- **Match History:** Tournament → Series → Game (3-level expand), filter date/tournament
- **Players:** Career stats, champion pool (stacked bar + win rate line), yearly trend, vs-opponent matchup analysis, career clustering (PCA scatter plot)
- **Meta Shifts:** Time series win rate + presence rate, shift event detection và table
- **Win Prediction:** SHAP importance chart, fold timeline, insight cards
- **Synergy Network:** Lift-based scoring table, type badges, anti-synergy analysis
- **Analytics Agent:** Chat interface, SQL viewer với copy button, data table
- **Admin:** Import Excel + CRUD master data (champions, players, teams, tournaments)

---

## Kiến trúc

```
Excel Data (903 games)
    ↓ ETL (Python/SQLAlchemy)
PostgreSQL (Neon serverless)
    ↓ Feature Engineering
    ├── Model 1: LightGBM/XGBoost (win prediction)
    ├── Model 2: Z-score anomaly (meta shift)
    ├── Model 3: KMeans clustering (player profiles)
    └── Model 4: Synergy graph (champion pairs)
    ↓ FastAPI (cache layer, 9 routers)
    ↓ React + Tailwind CSS (8 pages)
```

---

## Chạy local

```bash
# 1. Start PostgreSQL
docker compose up postgres -d

# 2. Import data
python backend/app/etl.py \
  --file "data/csv/T1MatchHistory_2020-2025.xlsx" \
  --db-url "postgresql://t1_user:password@localhost:5433/t1_analytics"

# 3. Build ML models
cd backend
python -m app.pipeline.features
python -m app.pipeline.train_model1
python -m app.pipeline.model2_meta_shift
python -m app.pipeline.model3_player_clustering
python -m app.pipeline.model4_synergy_network

# 4. Start backend
uvicorn app.main:app --reload --port 8000

# 5. Start frontend
cd frontend
npm install && npm run dev
```

---

## API Endpoints

```
GET  /api/champions
GET  /api/model1/info
GET  /api/model1/shap-importance
GET  /api/model2/timeseries/{champion_id}
GET  /api/model2/shift-events
GET  /api/model2/top-presence
GET  /api/matches/tournaments
GET  /api/matches/{series_id}/games
GET  /api/matches/game/{game_id}/detail
GET  /api/stats/winrate-by-patch
GET  /api/stats/winrate-by-tournament
GET  /api/stats/winrate-by-side
GET  /api/stats/player-winrates
GET  /api/stats/player/{player_id}
GET  /api/stats/head-to-head
GET  /api/stats/opponents
GET  /api/stats/player/{player_id}/vs-opponent
GET  /api/stats/player-clusters
GET  /api/stats/synergy
GET  /api/stats/synergy/top-pairs
POST /api/agent/ask
POST /api/admin/import/preview
POST /api/admin/import
GET  /api/admin/import/template
GET  /api/refresh-cache
```

---

## Những gì học được

- **Negative result là kết quả hợp lệ** — biết tại sao model fail quan trọng hơn ép accuracy cao
- **TimeSeriesSplit** thay vì random split khi data có temporal dependency
- **Volume threshold** trong anomaly detection — Z-score trên sample nhỏ cho kết quả cực đoan giả tạo
- **Schema mismatch debugging** — silent fail khi tên cột sai case, chỉ phát hiện qua cross-check nhiều bước
- **Bayesian smoothing** để tránh noise từ champion ít picks
- **Multi-provider LLM architecture** — abstract base class cho phép switch provider không cần sửa code chính

---

## Roadmap

- [ ] Player-level meta shift detection
- [ ] Thêm data LCK 2026 (real-time update)
- [ ] Champion counter-pick analysis
- [x] Deploy production (Neon + Render + Vercel)
- [x] Text-to-SQL Agent
- [x] Admin panel với import Excel
