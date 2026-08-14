"""Background cache refresh jobs."""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.cache import AppCache

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cache-refresh")


def sync_refresh(cache: AppCache) -> bool:
    try:
        logger.info("Background cache refresh bắt đầu...")
        ok = cache.refresh()
        if ok:
            logger.info("Background cache refresh hoàn thành.")
        else:
            logger.warning("Background cache refresh hoàn thành một phần (xem log chi tiết).")
        return ok
    except Exception as exc:
        logger.error("Background cache refresh thất bại: %s", exc, exc_info=True)
        return False


def submit_cache_refresh(cache: AppCache) -> None:
    _executor.submit(sync_refresh, cache)


def shutdown_executor() -> None:
    _executor.shutdown(wait=True)
