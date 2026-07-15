"""
Cấu hình trung tâm cho ứng dụng T1 Analytics.
Đọc biến môi trường, cung cấp giá trị mặc định cho local dev.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Database ───────────────────────────────────────────────────────────────
_raw_url = os.getenv("DATABASE_URL", "postgresql://t1_user:t1_password@localhost:5433/t1_analytics")
# Render cung cấp URL bắt đầu bằng "postgres://" (legacy), SQLAlchemy 2.0 yêu cầu "postgresql://"
DATABASE_URL: str = _raw_url.replace("postgres://", "postgresql://", 1) if _raw_url.startswith("postgres://") else _raw_url

# ─── App ─────────────────────────────────────────────────────────────────────
APP_TITLE: str = os.getenv("APP_TITLE", "T1 Analytics API")
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
