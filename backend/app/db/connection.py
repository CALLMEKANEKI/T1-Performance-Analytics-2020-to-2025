"""
Database connection helper — dùng chung cho toàn bộ ứng dụng.
Tạo engine một lần, tái sử dụng connection pool.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import DATABASE_URL


def get_engine() -> Engine:
    """Trả về SQLAlchemy Engine được cấu hình từ DATABASE_URL."""
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def test_connection(engine: Engine) -> bool:
    """Kiểm tra kết nối database, trả về True nếu thành công."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
