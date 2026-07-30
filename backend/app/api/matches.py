"""
Match History endpoints:
- GET /api/matches              -> list series (paginated, filter theo tournament/opponent)
- GET /api/matches/tournaments  -> list tournaments với filter ngày & id
- GET /api/matches/{series_id}  -> chi tiết series, các game con
- GET /api/matches/game/{game_id} -> chi tiết 1 game: lineup, bans, picks (cho expand UI)
"""

import logging
from sqlalchemy import text
from fastapi import APIRouter, HTTPException, Query

from app.config import AppConfig
from app.core.database import engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
def list_matches(
    tournament_id: int | None = Query(None, description="ID giải đấu"),
    opponent_id: int | None = Query(None, description="ID đối thủ"),
    page: int = Query(1, ge=1, description="Trang (>=1)"),
    page_size: int = Query(20, ge=1, le=100, description="Kích thước trang (1-100)"),
):
    """List series, mới nhất trước, có filter + phân trang an toàn."""
    try:
        offset = (page - 1) * page_size
        where_clauses = []
        params = {
            "limit": page_size,
            "offset": offset,
            "t1_id": AppConfig.T1_ID
        }

        if tournament_id is not None:
            where_clauses.append("s.tournament_id = :tournament_id")
            params["tournament_id"] = tournament_id
        if opponent_id is not None:
            where_clauses.append("s.team_opponent_id = :opponent_id")
            params["opponent_id"] = opponent_id

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query_str = f"""
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
            JOIN game_teams gt ON gt.game_id = g.id_game AND gt.team_id = :t1_id
            {where_sql}
            GROUP BY s.id_series, s.match_date, s.best_of, t.name, opp.name, opp.id_team, opp.logo_url
            ORDER BY s.match_date DESC
            LIMIT :limit OFFSET :offset
        """

        with engine.connect() as conn:
            rows = conn.execute(text(query_str), params).mappings().all()

        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("Lỗi khi truy vấn danh sách trận đấu: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Không thể lấy danh sách trận đấu từ cơ sở dữ liệu.")


@router.get("/tournaments")
def list_tournaments(
    start_date: str | None = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    tournament_id: int | None = Query(None, description="ID giải đấu"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """Lấy danh sách các giải đấu an toàn với HAVING clause được parameterized."""
    try:
        filters = []
        params = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
            "t1_id": AppConfig.T1_ID
        }

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
            JOIN game_teams gt ON gt.game_id = g.id_game AND gt.team_id = :t1_id
            GROUP BY t.id_tournament, t.name, t.year
            {having_clause}
            ORDER BY MIN(g.date_played) DESC
            LIMIT :limit OFFSET :offset
        """
        with engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("Lỗi khi lấy danh sách giải đấu: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi tải giải đấu.")


@router.get("/{series_id}")
def get_series_detail(series_id: int):
    """Chi tiết 1 series: thông tin chung + list các game con."""
    try:
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
                    JOIN game_teams t1 ON t1.game_id = g.id_game AND t1.team_id = :t1_id
                    WHERE g.series_id = :sid
                    ORDER BY g.game_number
                """),
                {"sid": series_id, "t1_id": AppConfig.T1_ID},
            ).mappings().all()

        return {**dict(series_row), "games": [dict(g) for g in games]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Lỗi get_series_detail: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Không thể truy vấn chi tiết trận đấu.")


@router.get("/game/{game_id}")
def get_game_detail(game_id: int):
    """
    Chi tiết đầy đủ 1 game: lineup 2 bên, bans 2 bên.
    """
    try:
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
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Lỗi get_game_detail: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Không thể truy vấn chi tiết game.")
