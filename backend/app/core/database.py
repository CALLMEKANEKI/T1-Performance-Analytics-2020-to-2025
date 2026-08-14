from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import AppConfig

engine: Engine = create_engine(
    AppConfig.DATABASE_URL,
    pool_size=AppConfig.DB_POOL_SIZE,
    max_overflow=AppConfig.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=AppConfig.DB_POOL_RECYCLE,
)


def get_db():
    """Dependency Provider cho FastAPI routes nếu cần dùng session/connection."""
    with engine.connect() as connection:
        yield connection
