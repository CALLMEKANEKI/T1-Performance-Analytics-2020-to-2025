from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/champions")
def list_champions(request: Request):
    """List toàn bộ champion, dùng cho dropdown UI."""
    cache = request.app.state.cache
    return cache.champions.to_dict(orient="records")