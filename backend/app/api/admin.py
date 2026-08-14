"""
Admin endpoints:
- POST /api/admin/import         → upload Excel, chạy ETL, trả kết quả
- POST /api/admin/import/preview → preview data trước khi import (không write DB)
- GET  /api/admin/champions      → list champions
- GET  /api/admin/players        → list players
- GET  /api/admin/teams          → list teams
- GET  /api/admin/tournaments    → list tournaments
- PUT  /api/admin/champions/{id} → sửa champion
- PUT  /api/admin/players/{id}   → sửa player
"""

import io
import logging
import os
import tempfile
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import AppConfig
from app.core.cache_jobs import submit_cache_refresh
from app.core.database import engine
from app.core.deps import verify_admin_key

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/import/preview")
async def preview_import(file: UploadFile = File(...)):
    """
    Đọc Excel, trả về preview 5 dòng đầu của sheet chính. Không write gì vào DB.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx hoặc .xls")

    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents), sheet_name="LolMatchHistory_2020-2025")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được file: {e}")

    return {
        "total_rows": len(df),
        "columns": list(df.columns),
        "preview": df.head(5).to_dict(orient="records"),
    }


@router.post("/import")
async def import_excel(request: Request, file: UploadFile = File(...)):
    """
    Upload Excel → chạy ETL → trả về số records đã import.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx hoặc .xls")

    contents = await file.read()

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        from app.etl import run_etl
        run_etl(tmp_path, AppConfig.DATABASE_URL)
    except Exception as e:
        logger.error("ETL import failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"ETL lỗi: {e}")
    finally:
        os.unlink(tmp_path)

    # Đếm records sau import bằng 1 query duy nhất (tránh N+1 query)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM games) as games,
                    (SELECT COUNT(*) FROM players) as players,
                    (SELECT COUNT(*) FROM champions) as champions,
                    (SELECT COUNT(*) FROM teams) as teams,
                    (SELECT COUNT(*) FROM tournaments) as tournaments
            """)).mappings().first()
            counts = dict(row) if row else {}
        submit_cache_refresh(request.app.state.cache)
        return {"status": "success", "record_counts": counts}
    except Exception as exc:
        logger.error("Failed to query post-import counts: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi khi truy vấn thống kê dữ liệu sau import.")


# ── Master data: list ─────────────────────────────────────────────────────────

@router.get("/champions")
def list_champions(
    search: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        params = {"limit": limit, "offset": offset, "search": f"%{search}%"}
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id_champion, name, image_url FROM champions WHERE name ILIKE :search ORDER BY name LIMIT :limit OFFSET :offset"),
                params,
            ).mappings().all()
            total = conn.execute(
                text("SELECT COUNT(*) FROM champions WHERE name ILIKE :search"),
                {"search": f"%{search}%"},
            ).scalar()
        return {"total": total, "data": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tải danh sách champions.")


@router.get("/players")
def list_players(
    search: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        params = {"limit": limit, "offset": offset, "search": f"%{search}%"}
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT p.id_player, p.ingame_name, p.full_name, p.position,
                           p.country, p.birth_date, t.name as team_name
                    FROM players p
                    LEFT JOIN teams t ON p.team_id = t.id_team
                    WHERE p.ingame_name ILIKE :search OR p.full_name ILIKE :search
                    ORDER BY p.ingame_name
                    LIMIT :limit OFFSET :offset
                """),
                params,
            ).mappings().all()
            total = conn.execute(
                text("SELECT COUNT(*) FROM players WHERE ingame_name ILIKE :search OR full_name ILIKE :search"),
                {"search": f"%{search}%"},
            ).scalar()
        return {"total": total, "data": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tải danh sách tuyển thủ.")


@router.get("/teams")
def list_teams(
    search: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        params = {"limit": limit, "offset": offset, "search": f"%{search}%"}
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id_team, name, region, logo_url FROM teams WHERE name ILIKE :search ORDER BY name LIMIT :limit OFFSET :offset"),
                params,
            ).mappings().all()
            total = conn.execute(
                text("SELECT COUNT(*) FROM teams WHERE name ILIKE :search"),
                {"search": f"%{search}%"},
            ).scalar()
        return {"total": total, "data": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tải danh sách đội tuyển.")


@router.get("/tournaments")
def list_tournaments_admin(
    search: str = Query("", max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    try:
        params = {"limit": limit, "offset": offset, "search": f"%{search}%"}
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT id_tournament, name, year, region, ist1winner, winner
                    FROM tournaments
                    WHERE name ILIKE :search
                    ORDER BY year DESC, name
                    LIMIT :limit OFFSET :offset
                """),
                params,
            ).mappings().all()
            total = conn.execute(
                text("SELECT COUNT(*) FROM tournaments WHERE name ILIKE :search"),
                {"search": f"%{search}%"},
            ).scalar()
        return {"total": total, "data": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tải danh sách giải đấu.")


# ── Master data: update ───────────────────────────────────────────────────────

@router.put("/champions/{champion_id}")
def update_champion(champion_id: int, body: dict):
    allowed = {"name", "image_url"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Không có field hợp lệ để update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = champion_id

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(f"UPDATE champions SET {set_clause} WHERE id_champion = :id RETURNING id_champion, name"),
                updates,
            )
            row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Champion không tồn tại")
        return {"id_champion": row[0], "name": row[1]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Cập nhật champion thất bại.")


@router.put("/players/{player_id}")
def update_player(player_id: int, body: dict):
    allowed = {"ingame_name", "full_name", "position", "country", "photo_url"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Không có field hợp lệ để update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = player_id

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(f"UPDATE players SET {set_clause} WHERE id_player = :id RETURNING id_player, ingame_name"),
                updates,
            )
            row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Player không tồn tại")
        return {"id_player": row[0], "ingame_name": row[1]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Cập nhật player thất bại.")


@router.put("/teams/{team_id}")
def update_team(team_id: int, body: dict):
    allowed = {"name", "region", "logo_url"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Không có field hợp lệ để update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = team_id

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(f"UPDATE teams SET {set_clause} WHERE id_team = :id RETURNING id_team, name"),
                updates,
            )
            row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Team không tồn tại")
        return {"id_team": row[0], "name": row[1]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Cập nhật team thất bại.")


class ChampionCreate(BaseModel):
    name: str
    image_url: Optional[str] = None

class PlayerCreate(BaseModel):
    ingame_name: str
    full_name: Optional[str] = None
    position: Optional[str] = None
    country: Optional[str] = None
    team_id: Optional[int] = None

class TeamCreate(BaseModel):
    name: str
    region: Optional[str] = None
    logo_url: Optional[str] = None

class TournamentCreate(BaseModel):
    name: str
    year: int
    region: Optional[str] = None
    ist1winner: Optional[str] = None
    winner: Optional[str] = None


# ── CREATE ────────────────────────────────────────────────────────────────────

@router.post("/champions")
def create_champion(body: ChampionCreate):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO champions (name, image_url) VALUES (:name, :image_url) RETURNING id_champion"),
                body.model_dump()
            )
            return {"status": "created", "id": result.fetchone()[0]}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Champion với tên này đã tồn tại.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tạo champion mới.")


@router.post("/players")
def create_player(body: PlayerCreate):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO players (ingame_name, full_name, position, country, team_id) VALUES (:ingame_name, :full_name, :position, :country, :team_id) RETURNING id_player"),
                body.model_dump()
            )
            return {"status": "created", "id": result.fetchone()[0]}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Dữ liệu player không hợp lệ hoặc vi phạm ràng buộc dữ liệu.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tạo player mới.")


@router.post("/teams")
def create_team(body: TeamCreate):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO teams (name, region, logo_url) VALUES (:name, :region, :logo_url) RETURNING id_team"),
                body.model_dump()
            )
            return {"status": "created", "id": result.fetchone()[0]}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Team với tên này đã tồn tại.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tạo team mới.")


@router.post("/tournaments")
def create_tournament(body: TournamentCreate):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO tournaments (name, year, region, ist1winner, winner) VALUES (:name, :year, :region, :ist1winner, :winner) RETURNING id_tournament"),
                body.model_dump()
            )
            return {"status": "created", "id": result.fetchone()[0]}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Dữ liệu tournament không hợp lệ.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Không thể tạo tournament mới.")


# ── DELETE ────────────────────────────────────────────────────────────────────

@router.delete("/champions/{champion_id}")
def delete_champion(champion_id: int):
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM champions WHERE id_champion = :id"), {"id": champion_id})
        return {"status": "deleted", "id": champion_id}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Không thể xóa champion này vì đang có dữ liệu trận đấu liên quan.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Lỗi khi xóa champion.")


@router.delete("/players/{player_id}")
def delete_player(player_id: int):
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM players WHERE id_player = :id"), {"id": player_id})
        return {"status": "deleted", "id": player_id}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Không thể xóa player này vì đang có dữ liệu lịch sử trận đấu.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Lỗi khi xóa player.")


@router.delete("/teams/{team_id}")
def delete_team(team_id: int):
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM teams WHERE id_team = :id"), {"id": team_id})
        return {"status": "deleted", "id": team_id}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Không thể xóa team này vì đang có dữ liệu lịch sử thi đấu liên quan.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Lỗi khi xóa team.")


@router.delete("/tournaments/{tournament_id}")
def delete_tournament(tournament_id: int):
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM tournaments WHERE id_tournament = :id"), {"id": tournament_id})
        return {"status": "deleted", "id": tournament_id}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Không thể xóa tournament này vì đang chứa các series trận đấu.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Lỗi khi xóa tournament.")


@router.get("/import/template")
def download_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(columns=[
            "Index", "Year", "Match Date", "Event Name", "Patch",
            "Result", "Side", "T1 Players", "Opponent Team",
            "Opponent Players", "Bans Team 1", "Bans Team 2",
            "Team 1 Champs", "Team 2 Champs", "Link"
        ]).to_excel(writer, sheet_name="LolMatchHistory_2020-2025", index=False)

        pd.DataFrame(columns=["Index", "Icon", "Name"]).to_excel(writer, sheet_name="Champion", index=False)
        pd.DataFrame(columns=["Index", "Avatar", "Name", "Nickname", "Role"]).to_excel(writer, sheet_name="Player", index=False)
        pd.DataFrame(columns=["Index", "Icon", "Name", "Region"]).to_excel(writer, sheet_name="Team", index=False)
        pd.DataFrame(columns=["Index", "Name", "Date", "Is T1 winner", "Winner", "Region"]).to_excel(writer, sheet_name="Tournament", index=False)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=T1_import_template.xlsx"}
    )