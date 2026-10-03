"""Openverse discovery preserves original provenance; discovery is not license proof."""
import hashlib
import httpx
from ..config.settings import get_settings
from ..models.media_candidate import MediaCandidate
from ..utils.cache import DiskCache


class OpenverseClient:
    def __init__(self, transport=None, *, read_only=False):
        self.settings = get_settings()
        self.cfg = self.settings.sources_config.get("sources", {}).get("openverse", {})
        self.cache = DiskCache("openverse", create=not read_only)
        self.transport = transport

    def search(self, query: str, limit=3) -> list[MediaCandidate]:
        key = hashlib.sha256(f"{query}|{limit}".encode()).hexdigest()
        data = self.cache.get(key)
        if data is None:
            try:
                with httpx.Client(timeout=self.cfg.get("timeout_seconds", 15), transport=self.transport) as client:
                    response = client.get(self.cfg.get("api_url", "https://api.openverse.org/v1/images/"),
                                          params={"q": query, "page_size": min(limit, 5), "license": "cc0,pdm,by,by-sa"},
                                          headers={"User-Agent": self.settings.user_agent})
                if response.status_code != 200:
                    return []
                data = response.json()
                self.cache.set(key, data)
            except (httpx.HTTPError, ValueError):
                return []
        candidates = []
        if not isinstance(data, dict):
            return []
        for row in data.get("results", []):
            if not isinstance(row, dict):
                continue
            license_name = {"by": "CC BY", "by-sa": "CC BY-SA", "cc0": "CC0", "pdm": "Public Domain"}.get(row.get("license"), "")
            if not license_name:
                continue
            license_name += " " + (row.get("license_version") or "")
            try:
                candidates.append(MediaCandidate(source=f"Openverse/{row.get('source', 'unknown')}",
                    source_url=row.get("foreign_landing_url") or "", media_url=row.get("url") or "",
                    title=row.get("title") or row.get("id") or "", creator=row.get("creator"),
                    license=license_name.strip(), license_url=row.get("license_url"), attribution=row.get("attribution"),
                    width=row.get("width") or 0, height=row.get("height") or 0,
                    source_confidence=0.65, match_method="openverse_contextual_search"))
            except ValueError:
                continue
        return candidates
