"""Redis-backed fixed-window rate limiter with a local fallback.

Notes:
- Uses request headers (X-Forwarded-For) when available to better detect
  client IP behind proxies. This is still not a production-grade limiter —
  replace with Redis + fixed window or token-bucket when scaling.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # Redis remains optional for local development.
    Redis = None

    class RedisError(Exception):
        pass

from app.config import AppConfig

_buckets: dict[str, list[float]] = defaultdict(list)
_redis_client: Redis | None = None
_redis_failed = False
logger = logging.getLogger(__name__)


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


def _get_redis() -> Redis | None:
    global _redis_client, _redis_failed
    if Redis is None or not AppConfig.REDIS_URL or _redis_failed:
        return None
    if _redis_client is None:
        _redis_client = Redis.from_url(AppConfig.REDIS_URL, decode_responses=True)
    return _redis_client


def _check_redis(key: str, limit: int, window_sec: int) -> bool | None:
    client = _get_redis()
    if client is None:
        return None
    try:
        redis_key = f"t1:rate:{key}:{int(time.time() // window_sec)}"
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, window_sec)
        return count <= limit
    except RedisError as exc:
        global _redis_failed
        _redis_failed = True
        logger.warning("Redis rate limiter unavailable; using local fallback: %s", exc)
        return None


def check_rate_limit(request: Request, limit: int, window_sec: int = 60) -> None:
    if limit <= 0:
        return
    key = _resolve_client_ip(request)
    redis_allowed = _check_redis(key, limit, window_sec)
    if redis_allowed is not None:
        if not redis_allowed:
            raise HTTPException(status_code=429, detail="Too many requests")
        return

    now = time.time()
    window = [t for t in _buckets[key] if now - t < window_sec]
    if len(window) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    window.append(now)
    _buckets[key] = window
