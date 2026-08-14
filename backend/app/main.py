# backend/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import AppConfig
from app.core.cache import AppCache
from app.core.cache_jobs import shutdown_executor, submit_cache_refresh, sync_refresh
from app.core.deps import verify_admin_key
from app.api import model1, model2, champions, matches, stats, admin, agent as agent_router

logger = logging.getLogger(__name__)

cache = AppCache()


def _cache_is_ready() -> bool:
    return (
        cache.is_champions_ready()
        and cache.timeseries is not None
        and cache.model1_artifact is not None
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: warmup cache (blocking on production by default)."""
    loop = asyncio.get_running_loop()
    if AppConfig.CACHE_WARMUP_BLOCKING:
        logger.info("Server starting — cache warmup (blocking)...")
        await loop.run_in_executor(None, sync_refresh, cache)
    else:
        logger.info("Server starting — cache sẽ load trong nền...")
        submit_cache_refresh(cache)
    yield
    shutdown_executor()


app = FastAPI(title=AppConfig.APP_TITLE, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key"],
)

AppConfig.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=AppConfig.STATIC_DIR), name="static")

app.state.cache = cache

app.include_router(model1.router,       prefix="/api/model1",  tags=["model1"])
app.include_router(model2.router,       prefix="/api/model2",  tags=["model2"])
app.include_router(champions.router,    prefix="/api",         tags=["champions"])
app.include_router(matches.router,      prefix="/api/matches", tags=["matches"])
app.include_router(stats.router,        prefix="/api/stats",   tags=["stats"])
app.include_router(admin.router,        prefix="/api/admin",   tags=["admin"])
app.include_router(agent_router.router, prefix="/api/agent",   tags=["agent"])


@app.get("/")
def root():
    return {"status": "ok", "message": AppConfig.APP_TITLE}


@app.get("/api/health")
def health():
    """Health check — dùng để kiểm tra server và trạng thái cache."""
    ready = _cache_is_ready()
    return {
        "status": "ok" if ready else "warming_up",
        "cache": {
            "ready": ready,
            "champions_ready": cache.is_champions_ready(),
            "champions_count": len(cache.champions) if cache.is_champions_ready() else 0,
            "timeseries_ready": cache.timeseries is not None,
            "model1_ready": cache.model1_artifact is not None,
        },
    }


@app.post("/api/refresh-cache", dependencies=[Depends(verify_admin_key)])
def refresh_cache():
    """Rebuild cache trong background — không block response."""
    submit_cache_refresh(cache)
    return {"status": "cache refresh đang chạy trong nền"}
