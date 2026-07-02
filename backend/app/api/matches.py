"""
Match History endpoints:
- GET /api/matches              -> list series (paginated, filter theo tournament/opponent)
- GET /api/matches/{series_id}  -> chi tiết series, các game con
- GET /api/matches/game/{game_id} -> chi tiết 1 game: lineup, bans, picks (cho expand UI)
"""

from sqlalchemy import create_engine, text
from fastapi import APIRouter, HTTPException, Request, Query

from app.pipeline.features import DB_URL

router = APIRouter()
engine = create_engine(DB_URL)


@router.get("")
def list_matches(
    tournament_id: int | None = None,
    opponent_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """List series, mới nhất trước, có filter + phân trang."""
    offset = (page - 1) * page_size

    where_clauses = []
    params = {"limit": page_size, "offset": offset}

    if tournament_id is not None:
        where_clauses.append("s.tournament_id = :tournament_id")
        params["tournament_id"] = tournament_id
    if opponent_id is not None:
        where_clauses.append("s.team_opponent_id = :opponent_id")
        params["opponent_id"] = opponent_id

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = text(f"""
        SELECT
            s.id_series,
            s.match_date,
            s.best_of,
            t.name AS tournament_name,
            opp.name AS opponent_name,
            opp.id_team AS opponent_id,
            opp.logo_url AS opponent_logo,
            COUNT(DISTINCT g.id_game) AS total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) AS t1_wins,
            SUM(CASE WHEN gt.result = 'LOSS' THEN 1 ELSE 0 END) AS t1_losses
        FROM series s
        JOIN tournaments t ON s.tournament_id = t.id_tournament
        JOIN teams opp ON s.team_opponent_id = opp.id_team
        JOIN games g ON g.series_id = s.id_series
        JOIN game_teams gt ON gt.game_id = g.id_game AND gt.team_id = 1
        {where_sql}
        GROUP BY s.id_series, s.match_date, s.best_of, t.name, opp.name, opp.id_team, opp.logo_url
        ORDER BY s.match_date DESC
        LIMIT :limit OFFSET :offset
    """)

    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    return [dict(r) for r in rows]

@router.get("/tournaments")
def list_tournaments(
    start_date: str | None = None,
    end_date: str | None = None,
    tournament_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
):
    engine = create_engine(DB_URL)
    
    filters = []
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    
    if start_date:
        filters.append("MIN(g.date_played) >= :start_date")
        params["start_date"] = start_date
    if end_date:
        filters.append("MAX(g.date_played) <= :end_date")
        params["end_date"] = end_date
    if tournament_id:
            filters.append("t.id_tournament = :tournament_id")
            params["tournament_id"] = tournament_id
    
    having_clause = f"HAVING {' AND '.join(filters)}" if filters else ""
    
    query = f"""
        SELECT
            t.id_tournament,
            t.name as tournament_name,
            t.year,
            MIN(g.date_played) as start_date,
            MAX(g.date_played) as end_date,
            COUNT(DISTINCT s.id_series) as total_series,
            COUNT(DISTINCT g.id_game) as total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) as t1_wins
        FROM tournaments t
        JOIN series s ON s.tournament_id = t.id_tournament
        JOIN games g ON g.series_id = s.id_series
        JOIN game_teams gt ON gt.game_id = g.id_game AND gt.team_id = 1
        GROUP BY t.id_tournament, t.name, t.year
        {having_clause}
        ORDER BY MIN(g.date_played) DESC
        LIMIT :limit OFFSET :offset
    """
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]

@router.get("/{series_id}")
def get_series_detail(series_id: int):
    """Chi tiết 1 series: thông tin chung + list các game con (chưa kèm lineup)."""
    with engine.connect() as conn:
        series_row = conn.execute(
            text("""
                SELECT s.id_series, s.match_date, s.best_of,
                       t.name AS tournament_name,
                       opp.name AS opponent_name, opp.id_team AS opponent_id
                FROM series s
                JOIN tournaments t ON s.tournament_id = t.id_tournament
                JOIN teams opp ON s.team_opponent_id = opp.id_team
                WHERE s.id_series = :sid
            """),
            {"sid": series_id},
        ).mappings().first()

        if not series_row:
            raise HTTPException(status_code=404, detail="Series không tồn tại")

        games = conn.execute(
            text("""
                SELECT
                    g.id_game, g.game_number, g.patch, g.link, g.date_played,
                    t1.side AS t1_side, t1.result AS t1_result
                FROM games g
                JOIN game_teams t1 ON t1.game_id = g.id_game AND t1.team_id = 1
                WHERE g.series_id = :sid
                ORDER BY g.game_number
            """),
            {"sid": series_id},
        ).mappings().all()

    return {**dict(series_row), "games": [dict(g) for g in games]}


@router.get("/game/{game_id}")
def get_game_detail(game_id: int):
    """
    Chi tiết đầy đủ 1 game: lineup 2 bên (player + champion + ảnh), bans 2 bên.
    Dùng cho expand UI khi click vào 1 game cụ thể.
    """
    with engine.connect() as conn:
        teams = conn.execute(
            text("""
                SELECT gt.id_game_team, gt.team_id, gt.side, gt.result, te.name AS team_name
                FROM game_teams gt
                JOIN teams te ON gt.team_id = te.id_team
                WHERE gt.game_id = :gid
            """),
            {"gid": game_id},
        ).mappings().all()

        if not teams:
            raise HTTPException(status_code=404, detail="Game không tồn tại")

        lineups = conn.execute(
            text("""
                SELECT
                    gp.game_team_id, gp.pick_order,
                    p.id_player, p.ingame_name, p.position,
                    c.id_champion, c.name AS champion_name
                FROM game_players gp
                JOIN players p ON gp.player_id = p.id_player
                JOIN champions c ON gp.champion_id = c.id_champion
                WHERE gp.game_team_id = ANY(:team_ids)
                ORDER BY gp.game_team_id, gp.pick_order
            """),
            {"team_ids": [t["id_game_team"] for t in teams]},
        ).mappings().all()

        bans = conn.execute(
            text("""
                SELECT b.team_id, b.ban_order, c.id_champion, c.name AS champion_name
                FROM bans b
                JOIN champions c ON b.champion_id = c.id_champion
                WHERE b.game_id = :gid
                ORDER BY b.team_id, b.ban_order
            """),
            {"gid": game_id},
        ).mappings().all()

    teams_out = []
    for t in teams:
        team_lineup = [dict(l) for l in lineups if l["game_team_id"] == t["id_game_team"]]
        team_bans = [dict(b) for b in bans if b["team_id"] == t["team_id"]]
        teams_out.append({**dict(t), "lineup": team_lineup, "bans": team_bans})

    return {"game_id": game_id, "teams": teams_out}

