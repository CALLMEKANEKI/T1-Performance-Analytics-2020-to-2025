"""Legacy re-exports — prefer ``from app.config import AppConfig`` for new code."""

from app.config import AppConfig

DATABASE_URL: str = AppConfig.DATABASE_URL
APP_TITLE: str = AppConfig.APP_TITLE
DEBUG: bool = AppConfig.DEBUG
