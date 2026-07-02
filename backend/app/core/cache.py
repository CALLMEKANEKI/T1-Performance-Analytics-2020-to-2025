"""
Cache layer: load model + data 1 lần, giữ trong RAM.
Refresh bằng cách gọi lại .refresh() (qua endpoint /api/refresh-cache).
"""

import pickle
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from app.pipeline.features import DB_URL, load_raw_data
from app.pipeline.model2_meta_shift import (
    load_ban_data,
    build_champion_timeseries,
    detect_meta_shifts,
    merge_consecutive_events,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL1_PATH = BACKEND_DIR / "data" / "model1_lgbm.pkl"


class AppCache:
    def __init__(self):
        self.model1_artifact: dict | None = None
        self.timeseries: pd.DataFrame | None = None
        self.shift_events: pd.DataFrame | None = None
        self.merged_events: pd.DataFrame | None = None
        self.champions: pd.DataFrame | None = None

    def refresh(self):
        """Re-query DB + rebuild toàn bộ cache. Gọi khi có data mới."""
        engine = create_engine(DB_URL)

        # Champions lookup (dùng nhiều nơi để map id -> name)
        self.champions = pd.read_sql_query(
            "SELECT id_champion as champion_id, name, image_url FROM champions",
            engine,
        )
        # CHÈN ĐOẠN NÀY ĐỂ DEBUG:
        print(f"--- ĐANG KIỂM TRA ĐƯỜNG DẪN MODEL 1 ---")
        print(f"Đường dẫn tuyệt đối: {MODEL1_PATH.resolve()}")
        print(f"File có tồn tại không?: {MODEL1_PATH.exists()}")
        print(f"----------------------------------------")
        # Model 1 artifact (model đã train sẵn, load từ pickle)
        if MODEL1_PATH.exists():
            with open(MODEL1_PATH, "rb") as f:
                self.model1_artifact = pickle.load(f)
        else:
            self.model1_artifact = None

        # Model 2: rebuild time series + shift detection từ DB
        picks_df = load_raw_data(DB_URL)
        bans_df = load_ban_data(DB_URL)
        ts = build_champion_timeseries(picks_df, bans_df)
        shift_df = detect_meta_shifts(ts)
        merged = merge_consecutive_events(shift_df)

        self.timeseries = ts
        self.shift_events = shift_df[shift_df["is_shift_event"]].copy()
        self.merged_events = merged