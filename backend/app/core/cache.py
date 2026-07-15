"""
Cache layer: load model + data 1 lần, giữ trong RAM.
Refresh bằng cách gọi lại .refresh() (qua endpoint /api/refresh-cache).

Thiết kế an toàn:
- Mỗi bước refresh được bọc try/except riêng → 1 bước fail không crash toàn bộ cache.
- Nếu DB chưa sẵn sàng lúc startup, champions trả về [] thay vì None → tránh AttributeError.
- refresh_champions() có thể gọi độc lập (lightweight, không cần rebuild toàn bộ).
"""

import logging
import pickle
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from app.pipeline.features import DB_URL, load_raw_data
from app.pipeline.model2_meta_shift import (
    build_champion_timeseries,
    detect_meta_shifts,
    load_ban_data,
    merge_consecutive_events,
)

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL1_PATH = BACKEND_DIR / "data" / "model1_lgbm.pkl"

# DataFrame rỗng dùng làm fallback khi DB chưa sẵn sàng
_EMPTY_CHAMPIONS = pd.DataFrame(columns=["champion_id", "name", "image_url"])


class AppCache:
    def __init__(self):
        self.model1_artifact: dict | None = None
        self.timeseries: pd.DataFrame | None = None
        self.shift_events: pd.DataFrame | None = None
        self.merged_events: pd.DataFrame | None = None
        # Khởi tạo với DataFrame rỗng thay vì None → tránh AttributeError khi DB chưa sẵn sàng
        self.champions: pd.DataFrame = _EMPTY_CHAMPIONS.copy()

    # ─── PUBLIC API ──────────────────────────────────────────────────────────

    def refresh(self) -> bool:
        """
        Re-query DB + rebuild toàn bộ cache.
        Trả về True nếu thành công hoàn toàn, False nếu có lỗi một phần.
        Mỗi bước được thực hiện độc lập: 1 bước fail không ảnh hưởng bước khác.
        """
        success = True

        # Bước 1: Load danh sách champion (nhẹ, thực hiện trước)
        if not self._load_champions():
            success = False

        # Bước 2: Load model1 artifact từ pickle
        if not self._load_model1():
            success = False

        # Bước 3: Rebuild Model 2 time series + shift detection
        if not self._load_model2():
            success = False

        if success:
            logger.info("AppCache.refresh() hoàn thành — tất cả bước thành công.")
        else:
            logger.warning("AppCache.refresh() hoàn thành một phần — xem log để biết chi tiết.")

        return success

    def refresh_champions(self) -> bool:
        """Lightweight refresh: chỉ load lại bảng champions từ DB."""
        return self._load_champions()

    def is_champions_ready(self) -> bool:
        return self.champions is not None and not self.champions.empty

    # ─── PRIVATE HELPERS ─────────────────────────────────────────────────────

    def _load_champions(self) -> bool:
        """Load bảng champions từ DB. Trả về True nếu thành công."""
        try:
            engine = create_engine(DB_URL)
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id_champion AS champion_id, name, image_url FROM champions")
                )
                df = pd.DataFrame(result.mappings().all())

            if df.empty:
                logger.warning("Bảng champions trống trong DB.")
            else:
                self.champions = df
                logger.info("Champions loaded: %d rows", len(df))
            return True

        except Exception as exc:
            logger.error("_load_champions FAILED: %s", exc, exc_info=True)
            # Giữ nguyên giá trị cũ (không ghi đè bằng None)
            return False

    def _load_model1(self) -> bool:
        """Load model1 artifact từ pickle file."""
        try:
            if MODEL1_PATH.exists():
                with open(MODEL1_PATH, "rb") as f:
                    self.model1_artifact = pickle.load(f)
                logger.info("Model1 artifact loaded từ %s", MODEL1_PATH)
            else:
                self.model1_artifact = None
                logger.warning("Model1 pickle không tồn tại tại %s", MODEL1_PATH)
            return True
        except Exception as exc:
            logger.error("_load_model1 FAILED: %s", exc, exc_info=True)
            self.model1_artifact = None
            return False

    def _load_model2(self) -> bool:
        """Rebuild champion time series + meta shift detection từ DB."""
        try:
            picks_df = load_raw_data(DB_URL)
            bans_df = load_ban_data(DB_URL)
            ts = build_champion_timeseries(picks_df, bans_df)
            shift_df = detect_meta_shifts(ts)
            merged = merge_consecutive_events(shift_df)

            self.timeseries = ts
            self.shift_events = shift_df[shift_df["is_shift_event"]].copy()
            self.merged_events = merged
            logger.info("Model2 time series loaded: %d champion buckets", len(ts))
            return True
        except Exception as exc:
            logger.error("_load_model2 FAILED: %s", exc, exc_info=True)
            # Giữ nguyên giá trị cũ nếu đã có, không ghi đè bằng None
            return False