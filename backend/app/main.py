# backend/app/main.py
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.cache import AppCache
from app.api import model1, model2, champions, matches, stats, admin, agent as agent_router

# Khởi tạo instance cache toàn cục
cache = AppCache()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading cache on startup...")
    try:
        # Nạp cache lần đầu khi server start.
        # Nếu DB chưa sẵn sàng (cold start trên Render), server vẫn khởi động được.
        # Cache sẽ được điền sau qua fallback hoặc /api/refresh-cache.
        cache.refresh()
        print("Cache ready.")
    except Exception as exc:
        # Log lỗi nhưng KHÔNG re-raise — đảm bảo server luôn start thành công
        print(f"[WARNING] Cache khởi tạo thất bại: {exc}. Server vẫn start, cache sẽ được điền sau.", flush=True)
    yield



app = FastAPI(title="T1 Analytics API", lifespan=lifespan)

# === Cấu hình CORS tối ưu cho cả local và production ===
origins = [
    "https://t1-performance-analytics-2020-to-20.vercel.app",  # Production Frontend trên Vercel
    "http://localhost:5173",                                    # React/Vite local dev
    "http://localhost:3000",                                    # Next.js/React local alternative
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đảm bảo thư mục static tồn tại trước khi mount để tránh crash app nếu thiếu thư mục
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Đưa cache vào app.state để các router truy cập một cách đồng bộ
app.state.cache = cache

# Đăng ký các router
app.include_router(model1.router, prefix="/api/model1", tags=["model1"])
app.include_router(model2.router, prefix="/api/model2", tags=["model2"])
app.include_router(champions.router, prefix="/api", tags=["champions"])
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(agent_router.router, prefix="/api/agent", tags=["agent"])


@app.get("/")
def root():
    return {"status": "ok", "message": "T1 Analytics API"}


@app.post("/api/refresh-cache")
def refresh_cache(request: Request):
    """
    Endpoint rebuild lại cache trực tiếp trong RAM mà không cần khởi động lại server.
    Truy cập qua request.app.state để đảm bảo đồng bộ hoàn toàn với các API endpoints khác.
    """
    request.app.state.cache.refresh()
    return {"status": "cache refreshed"}