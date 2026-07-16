import logging
import math  # Thêm thư viện math chuẩn của Python để kiểm tra NaN/Inf nhanh gọn
import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import create_engine, text

from app.pipeline.features import DB_URL

logger = logging.getLogger(__name__)
router = APIRouter()


def clean_val(val):
    """Làm sạch từng giá trị: Chuyển NaN, inf, -inf thành None (null trong JSON)."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
    return val


def clean_records(records: list) -> list:
    """Quét qua danh sách các bản ghi (dict) để làm sạch toàn bộ dữ liệu trước khi serialize sang JSON."""
    if not records:
        return []
    return [
        {k: clean_val(v) for k, v in record.items()}
        for record in records
    ]


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
        raw_records = cache.champions.to_dict(orient="records")
        return clean_records(raw_records)  # Đã được làm sạch!

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

        # Chuyển đổi hàng sang dạng list dict thuần Python để xử lý
        raw_records = [dict(r) for r in rows]

        # Điền vào cache cho các request tiếp theo
        cache.champions = pd.DataFrame(raw_records)
        logger.info("/api/champions: fallback thành công, đã cập nhật cache (%d rows).", len(raw_records))

        return clean_records(raw_records)  # Đã được làm sạch!

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("/api/champions fallback FAILED: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Không thể kết nối database. Vui lòng thử lại sau.",
        )