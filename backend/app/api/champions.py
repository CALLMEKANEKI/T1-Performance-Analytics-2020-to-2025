import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import create_engine, text

from app.pipeline.features import DB_URL

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/champions")
def list_champions(request: Request):
    """
    List toàn bộ champion, dùng cho dropdown UI.

    Chiến lược 2 lớp:
    1. Phục vụ từ in-memory cache (nhanh, không tốn DB connection).
    2. Nếu cache chưa sẵn sàng (empty/None) → fallback tự truy vấn DB trực tiếp.
       Đồng thời kích hoạt refresh_champions() để điền cache cho lần sau.
    """
    cache = request.app.state.cache

    # ── Lớp 1: Phục vụ từ cache ──────────────────────────────────────────────
    if cache.is_champions_ready():
        return cache.champions.to_dict(orient="records")

    # ── Lớp 2: Cache rỗng → fallback truy vấn DB trực tiếp ──────────────────
    logger.warning("/api/champions: cache chưa sẵn sàng, fallback sang DB trực tiếp.")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id_champion AS champion_id, name, image_url FROM champions")
            )
            rows = result.mappings().all()

        if not rows:
            raise HTTPException(status_code=503, detail="Bảng champions trống trong database.")

        # Điền vào cache cho các request tiếp theo
        cache.champions = pd.DataFrame(rows)
        logger.info("/api/champions: fallback thành công, đã cập nhật cache (%d rows).", len(rows))

        return [dict(r) for r in rows]

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("/api/champions fallback FAILED: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Không thể kết nối database. Vui lòng thử lại sau.",
        )