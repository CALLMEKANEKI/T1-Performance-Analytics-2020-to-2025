from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from app.config import AppConfig

# Tạo single engine instance toàn cục với connection pool cấu hình sẵn
engine: Engine = create_engine(
    AppConfig.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

def get_db():
    """Dependency Provider cho FastAPI routes nếu cần dùng session/connection."""
    with engine.connect() as connection:
        yield connection
