"""Shared FastAPI dependencies."""

from fastapi import Header, HTTPException

from app.config import AppConfig


def verify_admin_key(x_admin_key: str = Header(default="", alias="X-Admin-Key")) -> None:
    """Production bắt buộc ADMIN_API_KEY; dev cho phép khi key chưa cấu hình."""
    expected = AppConfig.ADMIN_API_KEY
    env = AppConfig.ENV.lower()
    if env in ("production", "prod"):
        if not expected or x_admin_key != expected:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif expected and x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
