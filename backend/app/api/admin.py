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
import tempfile
import os

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from typing import Optional
from app.pipeline.features import DB_URL

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_engine():
    return create_engine(DB_URL)


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/import/preview")
async def preview_import(file: UploadFile = File(...)):
    """
    Đọc Excel, trả về preview 5 dòng đầu của sheet chính.
    Không write gì vào DB.
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
async def import_excel(file: UploadFile = File(...)):
    """
    Upload Excel → chạy ETL → trả về số records đã import.
    ETL dùng get_or_create nên an toàn khi chạy nhiều lần (không duplicate).
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx hoặc .xls")

    contents = await file.read()

    # Lưu tạm ra file để ETL đọc (ETL dùng pd.read_excel với path)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        from app.etl import run_etl
        run_etl(tmp_path, DB_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL lỗi: {e}")
    finally:
        os.unlink(tmp_path)

    # Đếm records sau import
    engine = get_engine()
    with engine.connect() as conn:
        counts = {}
        for table in ["games", "players", "champions", "teams", "tournaments"]:
            row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            counts[table] = row[0]

    return {"status": "success", "record_counts": counts}


# ── Master data: list ─────────────────────────────────────────────────────────

@router.get("/champions")
def list_champions(search: str = "", limit: int = 50, offset: int = 0):
    engine = get_engine()
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


@router.get("/players")
def list_players(search: str = "", limit: int = 50, offset: int = 0):
    engine = get_engine()
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


@router.get("/teams")
def list_teams(search: str = "", limit: int = 50, offset: int = 0):
    engine = get_engine()
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


@router.get("/tournaments")
def list_tournaments_admin(search: str = "", limit: int = 50, offset: int = 0):
    engine = get_engine()
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


# ── Master data: update ───────────────────────────────────────────────────────

@router.put("/champions/{champion_id}")
def update_champion(champion_id: int, body: dict):
    allowed = {"name", "image_url"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Không có field hợp lệ để update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = champion_id

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(f"UPDATE champions SET {set_clause} WHERE id_champion = :id RETURNING id_champion, name"),
            updates,
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Champion không tồn tại")
    return {"id_champion": row[0], "name": row[1]}


@router.put("/players/{player_id}")
def update_player(player_id: int, body: dict):
    allowed = {"ingame_name", "full_name", "position", "country", "photo_url"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Không có field hợp lệ để update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = player_id

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(f"UPDATE players SET {set_clause} WHERE id_player = :id RETURNING id_player, ingame_name"),
            updates,
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Player không tồn tại")
    return {"id_player": row[0], "ingame_name": row[1]}


@router.put("/teams/{team_id}")
def update_team(team_id: int, body: dict):
    allowed = {"name", "region", "logo_url"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Không có field hợp lệ để update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = team_id

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(f"UPDATE teams SET {set_clause} WHERE id_team = :id RETURNING id_team, name"),
            updates,
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Team không tồn tại")
    return {"id_team": row[0], "name": row[1]}

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
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO champions (name, image_url) VALUES (:name, :image_url) RETURNING id_champion"),
            body.model_dump()
        )
        return {"status": "created", "id": result.fetchone()[0]}

@router.post("/players")
def create_player(body: PlayerCreate):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO players (ingame_name, full_name, position, country, team_id) VALUES (:ingame_name, :full_name, :position, :country, :team_id) RETURNING id_player"),
            body.model_dump()
        )
        return {"status": "created", "id": result.fetchone()[0]}

@router.post("/teams")
def create_team(body: TeamCreate):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO teams (name, region, logo_url) VALUES (:name, :region, :logo_url) RETURNING id_team"),
            body.model_dump()
        )
        return {"status": "created", "id": result.fetchone()[0]}

@router.post("/tournaments")
def create_tournament(body: TournamentCreate):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO tournaments (name, year, region, ist1winner, winner) VALUES (:name, :year, :region, :ist1winner, :winner) RETURNING id_tournament"),
            body.model_dump()
        )
        return {"status": "created", "id": result.fetchone()[0]}

# ── DELETE ────────────────────────────────────────────────────────────────────

@router.delete("/champions/{champion_id}")
def delete_champion(champion_id: int):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM champions WHERE id_champion = :id"), {"id": champion_id})
    return {"status": "deleted", "id": champion_id}

@router.delete("/players/{player_id}")
def delete_player(player_id: int):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM players WHERE id_player = :id"), {"id": player_id})
    return {"status": "deleted", "id": player_id}

@router.delete("/teams/{team_id}")
def delete_team(team_id: int):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM teams WHERE id_team = :id"), {"id": team_id})
    return {"status": "deleted", "id": team_id}

@router.delete("/tournaments/{tournament_id}")
def delete_tournament(tournament_id: int):
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM tournaments WHERE id_tournament = :id"), {"id": tournament_id})
    return {"status": "deleted", "id": tournament_id}