"""
Stats endpoints: winrate theo patch, theo giải đấu, theo side.
Dùng cho Overview dashboard.
"""

from fastapi import APIRouter, Request
from sqlalchemy import create_engine, text

from app.pipeline.features import DB_URL

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
            COUNT(*) as total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(
                SUM(CASE WHEN gt.result = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3
            ) as win_rate
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        JOIN players p ON gp.player_id = p.id_player
        WHERE gt.team_id = :t1_id
        GROUP BY p.id_player, p.ingame_name, p.position
        HAVING COUNT(*) >= 5
        ORDER BY total_games DESC
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
        FROM players WHERE id_player = :pid
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
        info = conn.execute(text(info_query), {"pid": player_id}).mappings().first()
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