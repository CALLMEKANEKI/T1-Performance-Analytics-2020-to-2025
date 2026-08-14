"""Simple in-memory rate limiter (per client IP).

Notes:
- Uses request headers (X-Forwarded-For) when available to better detect
  client IP behind proxies. This is still not a production-grade limiter —
  replace with Redis + fixed window or token-bucket when scaling.
"""

import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request

_buckets: dict[str, list[float]] = defaultdict(list)


def _resolve_client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For when behind a reverse proxy; fallback to request.client
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        # X-Forwarded-For can contain comma-separated list: client, proxy1, proxy2
        ip = xff.split(",")[0].strip()
        if ip:
            return ip
    client = request.client
    if client and client.host:
        return client.host
    return "unknown"


def check_rate_limit(request: Request, limit: int, window_sec: int = 60) -> None:
    if limit <= 0:
        return
    key = _resolve_client_ip(request)
    now = time.time()
    window = [t for t in _buckets[key] if now - t < window_sec]
    if len(window) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    window.append(now)
    _buckets[key] = window
