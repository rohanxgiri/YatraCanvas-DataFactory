import re
import urllib.parse
from typing import Optional, Dict, Any, Tuple
import httpx
from ..config.settings import get_settings
from ..utils.cache import DiskCache
from ..utils.retry import retry_with_backoff
from ..utils.text import slugify, fuzzy_name_similarity


class WikipediaClient:
    """
    Client for extracting clean Wikipedia lead summaries and Wikidata short descriptions.
    Uses disk caching to ensure determinism and zero network calls on repeated runs.
    """

    def __init__(self, timeout: float = 15.0):
        self.settings = get_settings()
        self.timeout = timeout
        self.cache = DiskCache("wikipedia")
        self.api_url = "https://en.wikipedia.org/w/api.php"

    def _extract_title(self, title_or_url: str) -> str:
        """Extract clean Wikipedia article title from full URL or title string."""
        if not title_or_url:
            return ""
        clean = title_or_url.strip()
        if "wikipedia.org/wiki/" in clean:
            clean = clean.split("wikipedia.org/wiki/")[-1]
            clean = urllib.parse.unquote(clean)
            # Remove any fragment/anchor
            clean = clean.split("#")[0]
        return clean.replace("_", " ").strip()

    def _clean_extract(self, raw_text: str) -> Optional[str]:
        """
        Clean raw extract into a concise, readable 1-2 paragraph description
        suitable for travel planning. Trims references, excess brackets, and cap to ~500 chars.
        """
        if not raw_text:
            return None

        text = raw_text.strip()
        # Remove reference markers like [1], [2], etc.
        text = re.sub(r"\[\d+\]", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) < 15:
            return None

        # Take first 1-2 sentences or up to ~450 characters at sentence boundary
        if len(text) > 450:
            match = re.search(r"(\.[ \n]|\.\Z)", text[250:500])
            if match:
                end_pos = 250 + match.end()
                text = text[:end_pos].strip()
            else:
                text = text[:450].rsplit(" ", 1)[0].strip() + "..."

        return text if len(text) >= 15 else None

    def get_summary(self, title_or_url: str) -> Optional[str]:
        """
        Retrieve clean introductory extract for a Wikipedia page.
        Returns None if article not found or offline.
        """
        title = self._extract_title(title_or_url)
        if not title:
            return None

        cache_key = f"wp_extract_{title.lower()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
            "format": "json",
            "redirects": "1",
        }
        headers = {"User-Agent": self.settings.user_agent}

        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page in pages.items():
                        if page_id == "-1":
                            continue
                        raw_extract = page.get("extract", "")
                        clean = self._clean_extract(raw_extract)
                        if clean:
                            self.cache.set(cache_key, clean)
                            return clean
        except Exception:
            pass

        self.cache.set(cache_key, None)
        return None

    def search_summary(self, query: str, city_name: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """
        Search Wikipedia for a place and retrieve its clean lead summary and canonical URL.
        Guards against false matches by validating title similarity and context.
        Returns (summary, wikipedia_url) or None.
        """
        if not query or len(query.strip()) < 3:
            return None

        clean_q = query.strip()
        search_term = f"{clean_q} {city_name}".strip() if city_name else clean_q
        cache_key = f"wp_search_{slugify(search_term)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            if isinstance(cached, dict) and "summary" in cached and "url" in cached:
                return cached["summary"], cached["url"]
            return None

        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "srlimit": "3",
            "format": "json",
        }
        headers = {"User-Agent": self.settings.user_agent}

        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("query", {}).get("search", [])
                    for res in results:
                        title = res.get("title", "")
                        sim = fuzzy_name_similarity(clean_q, title)
                        if sim >= 0.65 or clean_q.lower() in title.lower() or (city_name and city_name.lower() in title.lower() and sim >= 0.45):
                            summary = self.get_summary(title)
                            if summary:
                                wp_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                                self.cache.set(cache_key, {"summary": summary, "url": wp_url})
                                return summary, wp_url
        except Exception:
            pass

        self.cache.set(cache_key, None)
        return None

