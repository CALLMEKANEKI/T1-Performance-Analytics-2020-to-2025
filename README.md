# T1 Performance Analytics (2020–2025)

Dự án phân tích dữ liệu trận đấu của T1 từ năm 2020 đến 2025 bằng pipeline dữ liệu, mô hình học máy và dashboard trực quan. Mục tiêu không chỉ là dự đoán kết quả, mà còn giúp khám phá xu hướng meta, player form, champion synergy và các thay đổi chiến thuật theo thời gian.

## Tổng quan

Dự án hiện có đầy đủ stack từ ETL, backend API đến frontend dashboard:

- Backend: Python + FastAPI + SQLAlchemy + PostgreSQL
- Frontend: React + Vite + Tailwind CSS + Recharts
- Data pipeline: ETL từ CSV/Excel vào PostgreSQL, feature engineering, model training và clustering

Stack hiện tại: PostgreSQL (Docker) · Python (Pandas, LightGBM, XGBoost, SHAP) · FastAPI · React + Vite

---

## Dữ liệu

- Nguồn: lịch sử trận đấu T1 từ 2020–2025
- Quy mô ước tính: 903 trận, 362 series, 338 players, 334 champions, 80 patches
- Schema: chuẩn hóa theo chuỗi tournaments → series → games → game_teams → game_players, kèm bảng bans và champion metadata
- Lưu ý: roster player được lấy theo bảng players với `team_id = 1` để đảm bảo dashboard hiển thị đúng danh sách T1 hiện tại

---

## Tính năng hiện có

### 1. Overview dashboard
- Win rate theo patch
- Win rate theo giải đấu/tournament
- Win rate theo side (Blue/Red)
- Tổng quan thống kê chung về T1

### 2. Match History
- Xem lịch sử trận đấu chi tiết
- Hiển thị lineup, bans, picks và kết quả từng game

### 3. Player Dashboard
- Danh sách player thuộc roster T1
- Thống kê win rate, tổng số trận, champion pool
- Biểu đồ win rate theo năm
- Player career clustering (PCA + KMeans)

### 4. Meta Shifts
- Phát hiện các champion trải qua meta shift theo thời gian
- Biểu đồ time series và events

### 5. Synergy Network
- Phân tích cặp champion có synergy/anti-synergy
- Hỗ trợ lọc theo năm, số trận tối thiểu và champion cụ thể

### 6. Win Prediction
- Thử nghiệm mô hình dự đoán kết quả dựa trên draft, player form và meta context
- Có thể dùng để nghiên cứu thay vì phục vụ production prediction

### 7. Admin panel
- Quản lý champions, players, teams, tournaments
- Import dữ liệu và xem trước trước khi ghi vào DB

---

## Mô hình và nghiên cứu

### Model 1: Win Prediction from Draft + Player Form

#### Hypothesis
Liệu draft, meta context và player form có đủ để dự đoán kết quả T1 thắng/thua?

#### Approach
- Features: champion one-hot, side, patch, rolling win rate cho player/champion, player-champion mastery
- Model: LightGBM + XGBoost
- Evaluation: TimeSeriesSplit thay vì random split để tránh data leakage
- Explainability: SHAP values

#### Kết quả
- Model không vượt qua naive baseline ở mức độ đáng tin cậy
- Đây là một kết quả nghiên cứu hợp lệ, không phải lỗi kỹ thuật

### Model 2: Meta Shift Detection
- Dùng time-series theo bucket 2 tuần cho champion
- Phát hiện đột biến về win rate và presence rate
- Vận dụng volume filter để giảm false positive

### Model 3: Player Clustering
- Dùng PCA + KMeans để nhóm player theo đặc điểm career pattern
- Trực quan hóa bằng scatter plot trên dashboard

### Model 4: Champion Synergy Network
- Tính toán cặp champion có synergy/anti-synergy theo thời gian

---

## Kiến trúc kỹ thuật

```text
PostgreSQL (Docker)
    ↓ SQLAlchemy
ETL pipeline (etl.py / CSV import)
    ↓
Feature engineering + model training
    ↓
FastAPI backend
    ↓
React + Vite frontend dashboard
```

### API chính

```text
GET /api/champions
GET /api/stats/winrate-by-patch
GET /api/stats/winrate-by-tournament
GET /api/stats/winrate-by-side
GET /api/stats/player-winrates
GET /api/stats/player/{player_id}
GET /api/stats/player-clusters
GET /api/stats/synergy
GET /api/stats/synergy/top-pairs
GET /api/matches
GET /api/matches/{series_id}
GET /api/matches/game/{game_id}
```

---

## Chạy local

### 1. Khởi động database

```bash
docker compose up postgres -d
```

### 2. Cài đặt backend

```bash
cd backend
pip install -r requirements.txt
```

### 3. Chạy ETL / tạo dữ liệu

```bash
python app/etl.py
# hoặc nếu dùng script riêng, chạy các pipeline feature/model tương ứng
```

### 4. Chạy backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend chạy tại `http://localhost:5173`, backend tại `http://localhost:8000`.

---

## Chạy bằng Docker Compose

```bash
docker compose up --build
```

Điều này sẽ khởi động postgres, backend và frontend cùng lúc.

---

## Những bài học chính

- Negative result vẫn là kết quả nghiên cứu hợp lệ
- TimeSeriesSplit quan trọng khi dữ liệu có dependency theo thời gian
- Volume threshold giúp giảm false positive trong anomaly detection
- Debug schema mismatch là phần không thể thiếu trong pipeline dữ liệu thực tế

---

## Roadmap

- [x] Dashboard overview và player analytics
- [x] Match history và champion synergy
- [x] Admin panel cơ bản
- [ ] Tối ưu UI/UX và thêm filter nâng cao
- [ ] Thêm text-to-SQL hoặc natural language query
- [ ] Mở rộng phân tích player-level meta shift
- [ ] Deploy production
