import pandas as pd
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

# DataFrame rỗng dùng làm fallback khi cache chưa load xong
_EMPTY_DF = pd.DataFrame()


def _require_timeseries(cache) -> pd.DataFrame:
    """Trả timeseries hoặc raise 503 nếu cache chưa sẵn sàng."""
    if cache.timeseries is None:
        raise HTTPException(
            status_code=503,
            detail="Cache đang khởi tạo, vui lòng thử lại sau vài giây.",
        )
    return cache.timeseries


def _require_merged_events(cache) -> pd.DataFrame:
    """Trả merged_events hoặc raise 503 nếu cache chưa sẵn sàng."""
    if cache.merged_events is None:
        raise HTTPException(
            status_code=503,
            detail="Cache đang khởi tạo, vui lòng thử lại sau vài giây.",
        )
    return cache.merged_events


@router.get("/timeseries/{champion_id}")
def get_champion_timeseries(champion_id: int, request: Request):
    """Full time series (picks, bans, win_rate, presence_rate) của 1 champion."""
    cache = request.app.state.cache
    ts = _require_timeseries(cache)

    df = ts[ts["champion_id"] == champion_id].copy()
    if df.empty:
        raise HTTPException(status_code=404, detail="Champion không có data")

    df = df.replace({float("nan"): None})  # JSON không hiểu NaN
    df["bucket"] = df["bucket"].astype(str)
    return df.to_dict(orient="records")


@router.get("/shift-events")
def get_shift_events(
    request: Request,
    champion_id: int | None = None,
    min_score: float = 0,
    limit: int = 50,
):
    """
    Merged shift events (đã gộp các bucket liên tiếp).
    Filter theo champion_id và/hoặc min_score nếu cần.
    """
    cache = request.app.state.cache
    df = _require_merged_events(cache).copy()

    if champion_id is not None:
        df = df[df["champion_id"] == champion_id]
    df = df[df["max_composite_score"] >= min_score]
    df = df.sort_values("max_composite_score", ascending=False).head(limit)

    # Join tên champion (champions luôn có fallback DataFrame rỗng, không cần guard)
    df = df.merge(cache.champions, on="champion_id", how="left")

    for col in ["start_bucket", "end_bucket", "peak_bucket"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
    df = df.fillna(0)
    return df.to_dict(orient="records")


@router.get("/top-presence")
def get_top_presence(request: Request, top_n: int = 10):
    """Top champion theo presence_rate trung bình toàn dataset."""
    cache = request.app.state.cache
    ts = _require_timeseries(cache)

    top = (
        ts.groupby("champion_id", as_index=False)["presence_rate"]
        .mean()
        .sort_values("presence_rate", ascending=False)
        .head(top_n)
        .merge(cache.champions, on="champion_id", how="left")
    )
    return top.to_dict(orient="records")