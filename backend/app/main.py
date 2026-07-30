# backend/app/main.py
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import AppConfig
from app.core.cache import AppCache
from app.api import model1, model2, champions, matches, stats, admin, agent as agent_router

logger = logging.getLogger(__name__)

cache = AppCache()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cache-refresh")


def _sync_refresh() -> None:
    """Chạy cache.refresh() đồng bộ trong thread pool."""
    try:
        logger.info("Background cache refresh bắt đầu...")
        ok = cache.refresh()
        if ok:
            logger.info("Background cache refresh hoàn thành.")
        else:
            logger.warning("Background cache refresh hoàn thành một phần (xem log chi tiết).")
    except Exception as exc:
        logger.error("Background cache refresh thất bại: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler: khởi động nhanh, cache load bất đồng bộ trong nền.
    """
    logger.info("Server starting — cache sẽ load trong nền...")
    loop = asyncio.get_running_loop()
    loop.run_in_executor(_executor, _sync_refresh)
    yield
    _executor.shutdown(wait=False)


# ─── App + Middleware ─────────────────────────────────────────────────────────
app = FastAPI(title="T1 Analytics API", lifespan=lifespan)

# CORS — cấu hình các origin hợp lệ từ AppConfig
app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Cache vào app.state
app.state.cache = cache

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(model1.router,       prefix="/api/model1",  tags=["model1"])
app.include_router(model2.router,       prefix="/api/model2",  tags=["model2"])
app.include_router(champions.router,    prefix="/api",         tags=["champions"])
app.include_router(matches.router,      prefix="/api/matches", tags=["matches"])
app.include_router(stats.router,        prefix="/api/stats",   tags=["stats"])
app.include_router(admin.router,        prefix="/api/admin",   tags=["admin"])
app.include_router(agent_router.router, prefix="/api/agent",   tags=["agent"])


# ─── Utility endpoints ───────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "T1 Analytics API"}


@app.get("/api/health")
def health():
    """Health check — dùng để kiểm tra server và trạng thái cache."""
    return {
        "status": "ok",
        "cache": {
            "champions_ready": cache.is_champions_ready(),
            "champions_count": len(cache.champions) if cache.is_champions_ready() else 0,
            "timeseries_ready": cache.timeseries is not None,
            "model1_ready": cache.model1_artifact is not None,
        },
    }


@app.post("/api/refresh-cache")
def refresh_cache(request: Request):
    """Rebuild cache trong background — không block response."""
    loop = asyncio.get_running_loop()
    loop.run_in_executor(_executor, _sync_refresh)
    return {"status": "cache refresh đang chạy trong nền"}
