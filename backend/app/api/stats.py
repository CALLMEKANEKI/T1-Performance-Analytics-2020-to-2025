"""
Stats endpoints: winrate theo patch, theo giải đấu, theo side.
Dùng cho Overview dashboard.
Model 3: player clustering (parquet).
Model 4: champion synergy network (parquet).
"""

import math
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import create_engine, text

from app.pipeline.features import DB_URL

# Đường dẫn tới thư mục data (backend/data/)
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

router = APIRouter()
T1_ID = 1


@router.get("/winrate-by-patch")
def winrate_by_patch(request: Request):
    """Win rate T1 theo từng patch — cho line chart Overview."""
    engine = create_engine(DB_URL)
    query = r"""
        SELECT
            g.patch,
            CASE 
                WHEN g.patch ~ '^\d+\.\d+$' 
                THEN CAST(REPLACE(g.patch, '.', '') AS INTEGER)
                ELSE 0
            END as patch_num,
            COUNT(*) as total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as t1_wins,
            ROUND(
                SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3
            ) as win_rate
        FROM games g
        JOIN game_teams gt ON gt.game_id = g.id_game AND gt.team_id = :t1_id
        GROUP BY g.patch
        ORDER BY patch_num
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query), {"t1_id": T1_ID}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/winrate-by-tournament")
def winrate_by_tournament(request: Request):
    """Win rate T1 theo từng giải đấu — cho bar chart Overview."""
    engine = create_engine(DB_URL)
    query = """
        SELECT
            t.id_tournament as tournament_id,
            t.name as tournament_name,
            t.year,
            COUNT(*) as total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as t1_wins,
            ROUND(
                SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3
            ) as win_rate
        FROM games g
        JOIN series s ON g.series_id = s.id_series
        JOIN tournaments t ON s.tournament_id = t.id_tournament
        JOIN game_teams gt ON gt.game_id = g.id_game AND gt.team_id = :t1_id
        GROUP BY t.id_tournament, t.name, t.year
        ORDER BY t.year, t.name
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query), {"t1_id": T1_ID}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/winrate-by-side")
def winrate_by_side(request: Request):
    """Win rate T1 theo Blue/Red side — cho donut chart."""
    engine = create_engine(DB_URL)
    query = """
        SELECT
            gt.side,
            COUNT(*) as total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as t1_wins,
            ROUND(
                SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3
            ) as win_rate
        FROM game_teams gt
        WHERE gt.team_id = :t1_id
        GROUP BY gt.side
        ORDER BY gt.side
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query), {"t1_id": T1_ID}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/player-winrates")
def player_winrates(request: Request):
    engine = create_engine(DB_URL)
    query = """
        SELECT
            p.id_player,
            p.ingame_name,
            p.position,
            COUNT(gt.id_game_team) as total_games,
            COALESCE(SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END), 0) as wins,
            CASE
                WHEN COUNT(gt.id_game_team) > 0 THEN
                    ROUND(
                        COALESCE(SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END), 0)
                        / COUNT(gt.id_game_team),
                        3
                    )
                ELSE NULL
            END as win_rate
        FROM players p
        LEFT JOIN game_players gp ON gp.player_id = p.id_player
        LEFT JOIN game_teams gt
            ON gp.game_team_id = gt.id_game_team
           AND gt.team_id = :t1_id
        WHERE p.team_id = :t1_id
        GROUP BY p.id_player, p.ingame_name, p.position
        ORDER BY COUNT(gt.id_game_team) DESC, p.ingame_name
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query), {"t1_id": T1_ID}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/player/{player_id}")
def player_detail(player_id: int, request: Request):
    """
    Chi tiết 1 player T1:
    - Stats tổng
    - Champion pool (top 10 champions hay chơi nhất)
    - Win rate theo năm
    """
    engine = create_engine(DB_URL)

    # Thông tin cơ bản
    info_query = """
        SELECT id_player, ingame_name, full_name, position, photo_url, country, birth_date
        FROM players
        WHERE id_player = :pid AND team_id = :t1_id
    """

    # Champion pool
    champ_query = """
        SELECT
            c.id_champion,
            c.name as champion_name,
            COUNT(*) as games_played,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3
            ) as win_rate
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        JOIN champions c ON gp.champion_id = c.id_champion
        JOIN players p ON gp.player_id = p.id_player
        WHERE gp.player_id = :pid AND gt.team_id = :t1_id
        GROUP BY c.id_champion, c.name
        ORDER BY games_played DESC
    """

    # Win rate theo năm
    yearly_query = """
        SELECT
            EXTRACT(YEAR FROM g.date_played) as year,
            COUNT(*) as total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3
            ) as win_rate
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        JOIN games g ON gt.game_id = g.id_game
        WHERE gp.player_id = :pid AND gt.team_id = :t1_id
        GROUP BY EXTRACT(YEAR FROM g.date_played)
        ORDER BY year
    """

    with engine.connect() as conn:
        info = conn.execute(text(info_query), {"pid": player_id, "t1_id": T1_ID}).mappings().first()
        champs = conn.execute(text(champ_query), {"pid": player_id, "t1_id": T1_ID}).mappings().all()
        yearly = conn.execute(text(yearly_query), {"pid": player_id, "t1_id": T1_ID}).mappings().all()

    if not info:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Player không tồn tại")

    return {
        "info": dict(info),
        "champion_pool": [dict(r) for r in champs],
        "yearly_stats": [dict(r) for r in yearly],
    }


# ─── Helper: convert NaN → None cho JSON safe ────────────────────────────────
def _nan_to_none(val):
    """Chuyển NaN/inf thành None để JSON không lỗi."""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → list[dict], replace NaN bằng None."""
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    return [
        {k: _nan_to_none(v) for k, v in row.items()}
        for row in records
    ]


# ─── Model 3: Player Clustering ───────────────────────────────────────────────
CLUSTER_LABELS = {0: "Core Roster", 1: "Outlier", 2: "Veteran"}


@router.get("/player-clusters")
def player_clusters():
    """
    Load model3_clusters.parquet và trả về danh sách players
    với cluster label, PCA coordinates và stats.
    """
    parquet_path = DATA_DIR / "model3_clusters.parquet"
    if not parquet_path.exists():
        raise HTTPException(
            status_code=404,
            detail="model3_clusters.parquet chưa được generate. Chạy model3_player_clustering.py trước."
        )

    df = pd.read_parquet(parquet_path)

    # Thêm cluster_label dạng string
    df["cluster_label"] = df["cluster"].map(CLUSTER_LABELS).fillna("Unknown")

    # Chọn các cột cần thiết (bỏ những cột không tồn tại)
    desired_cols = [
        "player_id", "player_name", "cluster", "cluster_label",
        "PC1", "PC2", "overall_winrate", "total_games", "position",
    ]
    cols = [c for c in desired_cols if c in df.columns]
    return _df_to_records(df[cols])


# ─── Model 4: Synergy Network ─────────────────────────────────────────────────
SYNERGY_ALLTIME_PATH = DATA_DIR / "model4_synergy_alltime.parquet"
SYNERGY_BYYEAR_PATH  = DATA_DIR / "model4_synergy_by_year.parquet"

SYNERGY_COLS = [
    "champion_a", "champion_b", "co_games", "co_wins",
    "synergy_wr", "lift", "type_a", "type_b", "is_cross_lane",
]


def _load_synergy(by_year: bool = False) -> pd.DataFrame:
    """Load đúng file parquet theo chế độ."""
    path = SYNERGY_BYYEAR_PATH if by_year else SYNERGY_ALLTIME_PATH
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{path.name} chưa được generate. Chạy model4_synergy_network.py trước."
        )
    return pd.read_parquet(path)


@router.get("/synergy")
def synergy(
    year: Optional[int] = Query(None, description="Lọc theo năm (2020–2025)"),
    min_games: int = Query(5, ge=1, description="Số game tối thiểu của cặp"),
    champion: Optional[str] = Query(None, description="Lọc theo champion_a hoặc champion_b"),
):
    """
    Trả về danh sách champion pairs sort theo lift DESC (max 100).
    Nếu có year → dùng by_year parquet; ngược lại dùng alltime.
    """
    use_year = year is not None
    df = _load_synergy(by_year=use_year)

    # Filter theo năm
    if use_year and "year" in df.columns:
        df = df[df["year"] == year]

    # Filter min_games
    df = df[df["co_games"] >= min_games]

    # Filter theo champion (so sánh case-insensitive)
    if champion:
        champ_lower = champion.strip().lower()
        mask = (
            df["champion_a"].str.lower() == champ_lower
        ) | (
            df["champion_b"].str.lower() == champ_lower
        )
        df = df[mask]

    # Chọn cột output
    extra_cols = ["year"] if (use_year and "year" in df.columns) else []
    cols = [c for c in SYNERGY_COLS + extra_cols if c in df.columns]

    df = df[cols].sort_values("lift", ascending=False).head(100)
    return _df_to_records(df)


@router.get("/synergy/top-pairs")
def synergy_top_pairs(
    limit: int = Query(20, ge=1, le=100, description="Số pairs trả về"),
    mode: str = Query("synergy", description="'synergy' (lift DESC) hoặc 'anti' (lift ASC)"),
    min_games: int = Query(5, ge=1, description="Số game tối thiểu của cặp"),
    year: Optional[int] = Query(None, description="Lọc theo năm (2020–2025)"),
):
    """
    Top N synergy hoặc anti-synergy pairs (all-time hoặc theo năm).
    mode='synergy' → sort lift DESC
    mode='anti'    → sort lift ASC
    """
    if mode not in ("synergy", "anti"):
        raise HTTPException(status_code=400, detail="mode phải là 'synergy' hoặc 'anti'")

    use_year = year is not None
    df = _load_synergy(by_year=use_year)

    if use_year and "year" in df.columns:
        df = df[df["year"] == year]

    df = df[df["co_games"] >= min_games]

    ascending = mode == "anti"
    cols = [c for c in SYNERGY_COLS if c in df.columns]
    df = df[cols].sort_values("lift", ascending=ascending).head(limit)
    return _df_to_records(df)
