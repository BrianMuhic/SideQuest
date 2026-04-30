import hashlib
import json
import time
from pathlib import Path
from typing import Any

from config import config
from core.service.logger import get_logger

log = get_logger()

_CACHE_DIR = Path(config.CACHE_DIR)
_DISABLED = config.CACHE_DISABLED

MISS = object()


def _path_for(key: str) -> Path:
    return _CACHE_DIR / key[:2] / f"{key}.json"


def get(key: str) -> Any:
    """Return the cached value, or MISS sentinel if not found/expired."""
    if _DISABLED:
        return MISS
    path = _path_for(key)
    try:
        entry = json.loads(path.read_text())
        if time.time() > entry["expires"]:
            path.unlink(missing_ok=True)
            log.d(f"cache miss (expired) key={key[:8]}")
            return MISS
        log.d(f"cache hit key={key[:8]}")
        return entry["data"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        log.d(f"cache miss key={key[:8]}")
        return MISS


def set(key: str, value: Any, ttl: int) -> None:
    if _DISABLED:
        return
    path = _path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"expires": time.time() + ttl, "data": value}))


def make_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
