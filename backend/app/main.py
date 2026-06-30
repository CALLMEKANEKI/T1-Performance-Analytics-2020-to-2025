"""
FastAPI app: T1 Analytics
- Model 1 (win prediction) và Model 2 (meta shift) đều cache trong RAM lúc startup
- Endpoint /api/refresh-cache để rebuild cache không cần restart server
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.cache import AppCache
from app.api import model1, model2, champions

cache = AppCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading cache on startup...")
    cache.refresh()
    print("Cache ready.")
    yield


app = FastAPI(title="T1 Analytics API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đưa cache vào app.state để các router truy cập được
app.state.cache = cache

app.include_router(model1.router, prefix="/api/model1", tags=["model1"])
app.include_router(model2.router, prefix="/api/model2", tags=["model2"])
app.include_router(champions.router, prefix="/api", tags=["champions"])


@app.get("/")
def root():
    return {"status": "ok", "message": "T1 Analytics API"}


@app.post("/api/refresh-cache")
def refresh_cache():
    cache.refresh()
    return {"status": "cache refreshed"}