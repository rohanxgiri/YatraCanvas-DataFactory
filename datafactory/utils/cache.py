import json
import time
import hashlib
from pathlib import Path
from typing import Any, Optional
from ..config.settings import get_settings


class DiskCache:
    def __init__(self, cache_subdir: str = "http", *, create=True):
        self.settings = get_settings()
        self.cache_dir = self.settings.cache_dir / cache_subdir
        if create:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = self.settings.cache_ttl_seconds

    def _get_path(self, key: str) -> Path:
        safe_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._get_path(key)
        if not path.exists():
            # Preserve existing caches during migration to collision-free hashed keys.
            legacy = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
            if len(legacy) > 180:
                return None
            path = self.cache_dir / f"{legacy}.json"
            if not path.exists():
                return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_at = data.get("_cached_at", 0)
            if time.time() - cached_at > self.ttl:
                return None
            return data.get("payload")
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._get_path(key)
        try:
            from .atomic import atomic_json
            atomic_json(path, {
                    "_cached_at": time.time(),
                    "payload": value
                })
        except Exception:
            pass
