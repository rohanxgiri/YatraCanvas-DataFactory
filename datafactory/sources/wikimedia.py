import datetime
import io
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import httpx
from PIL import Image
Image.MAX_IMAGE_PIXELS = 400_000_000

from ..config.settings import get_settings
from ..models.image import ImageMetadata
from ..utils.cache import DiskCache
from ..utils.text import clean_string, normalize_name


class WikimediaCommonsClient:
    def __init__(self):
        self.settings = get_settings()
        self.cache = DiskCache("wikimedia_meta")
        self.sources_cfg = self.settings.sources_config.get("sources", {}).get("wikimedia_commons", {})
        self.media_cfg = self.settings.sources_config.get("media", {})
        self.api_url = self.sources_cfg.get("api_url", "https://commons.wikimedia.org/w/api.php")
        self.timeout = self.sources_cfg.get("timeout_seconds", 20.0)
        self.allowed_licenses = set(self.media_cfg.get("allowed_licenses", []))

    def get_image_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Fetch file metadata from Commons MediaWiki API."""
        if not filename:
            return None

        clean_fn = filename.replace("File:", "").replace("file:", "").strip()
        cached = self.cache.get(f"img_{clean_fn}")
        if cached:
            return cached

        params = {
            "action": "query",
            "titles": f"File:{clean_fn}",
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata|mime",
            "format": "json",
        }
        headers = {"User-Agent": self.settings.user_agent}

        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except Exception as e:
            print(f"Wikimedia API error for {filename}: {e}")
            return None

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        page = next(iter(pages.values()))
        imageinfo = page.get("imageinfo", [])
        if not imageinfo:
            return None

        info = imageinfo[0]
        extmetadata = info.get("extmetadata", {})

        # Extract license
        license_name = extmetadata.get("LicenseShortName", {}).get("value", "")
        license_url = extmetadata.get("LicenseUrl", {}).get("value", "")
        artist_html = extmetadata.get("Artist", {}).get("value", "")
        attribution = extmetadata.get("Attribution", {}).get("value")

        # Strip HTML from artist
        artist = clean_string(re.sub(r"<[^>]+>", "", artist_html)) if artist_html else "Unknown"

        res = {
            "original_file": clean_fn,
            "url": info.get("url"),
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "mime": info.get("mime", ""),
            "author": artist,
            "license": license_name or "Unknown",
            "license_url": license_url,
            "attribution": attribution,
            "source_page": f"https://commons.wikimedia.org/wiki/File:{clean_fn.replace(' ', '_')}",
        }

        self.cache.set(f"img_{clean_fn}", res)
        return res

    def is_license_permitted(self, license_name: str) -> bool:
        """Check if license is open/free for redistribution."""
        if not license_name:
            return False
        clean = license_name.strip().upper()
        # Common free open licenses
        if any(allowed.upper() in clean for allowed in self.allowed_licenses):
            return True
        if "CC BY" in clean or "CC-BY" in clean or "PUBLIC DOMAIN" in clean or "CC0" in clean:
            return True
        return False

    def get_wikipedia_lead_image(self, wiki_title_or_url: str) -> Optional[str]:
        """Fetch lead image filename from Wikipedia article using pageprops/pageimages."""
        if not wiki_title_or_url:
            return None

        # Extract title from URL if full URL provided
        title = wiki_title_or_url.split("/wiki/")[-1].replace("_", " ") if "/wiki/" in wiki_title_or_url else wiki_title_or_url
        clean_title = title.strip()
        cached = self.cache.get(f"wp_lead_{clean_title}")
        if cached is not None:
            return cached

        params = {
            "action": "query",
            "titles": clean_title,
            "prop": "pageimages",
            "piprop": "original",
            "format": "json",
            "redirects": "1",
        }
        headers = {"User-Agent": self.settings.user_agent}
        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get("https://en.wikipedia.org/w/api.php", params=params)
                if resp.status_code == 200:
                    pages = resp.json().get("query", {}).get("pages", {})
                    page = next(iter(pages.values()), {})
                    orig = page.get("original", {})
                    src = orig.get("source")
                    if src:
                        # Extract filename from URL
                        fn = src.split("/")[-1]
                        import urllib.parse
                        fn = urllib.parse.unquote(fn)
                        self.cache.set(f"wp_lead_{clean_title}", fn)
                        return fn
        except Exception as e:
            print(f"Error fetching Wikipedia lead image for {clean_title}: {e}")

        self.cache.set(f"wp_lead_{clean_title}", None)
        return None

    def search_category_images(self, category_name: str, limit: int = 3) -> List[str]:
        """Search for images inside a Wikimedia Commons category (Tier 2)."""
        clean_cat = category_name.replace("Category:", "").strip()
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{clean_cat}",
            "cmtype": "file",
            "cmlimit": limit,
            "format": "json",
        }
        headers = {"User-Agent": self.settings.user_agent}
        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    return []
                members = resp.json().get("query", {}).get("categorymembers", [])
                return [m["title"].replace("File:", "") for m in members if m.get("title")]
        except Exception:
            return []

    def search_commons_image(self, entity_name: str, city_name: str) -> Optional[str]:
        """Search Commons for files matching entity name and city with strict keyword validation."""
        if not entity_name or len(entity_name) < 3:
            return None

        query = f'"{entity_name}" {city_name}'
        cache_key = f"commons_sr_{clean_string(query)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",  # File namespace
            "srlimit": 3,
            "format": "json",
        }
        headers = {"User-Agent": self.settings.user_agent}
        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    results = resp.json().get("query", {}).get("search", [])
                    norm_entity = normalize_name(entity_name)
                    for r in results:
                        title = r.get("title", "").replace("File:", "").strip()
                        # Strict validation: title or snippet must contain main entity words
                        norm_title = normalize_name(title)
                        entity_words = [w for w in norm_entity.split() if len(w) > 3]
                        if entity_words and all(w in norm_title for w in entity_words):
                            self.cache.set(cache_key, title)
                            return title
        except Exception:
            pass

        self.cache.set(cache_key, None)
        return None

    def download_and_process_image(
        self,
        file_info: Dict[str, Any],
        place_id: str,
        output_dir: Path,
        match_method: str = "wikidata_p18",
        match_confidence: float = 1.0,
        refresh: bool = False,
    ) -> Optional[ImageMetadata]:
        """
        Download original image, optimize to primary.webp and thumbnail.webp,
        and return ImageMetadata with relative file paths.
        """
        url = file_info.get("url")
        if not url:
            return None

        license_name = file_info.get("license", "")
        if not self.is_license_permitted(license_name):
            file_name = str(file_info.get('original_file', '')).encode('ascii', 'replace').decode('ascii')
            print(f"Rejecting image {file_name} due to non-free license: {license_name}")
            return None

        place_media_dir = output_dir / place_id
        primary_path = place_media_dir / "primary.webp"
        thumb_path = place_media_dir / "thumbnail.webp"

        if primary_path.exists() and thumb_path.exists() and not refresh:
            try:
                with Image.open(primary_path) as im:
                    orig_w, orig_h = im.size
            except Exception:
                orig_w, orig_h = (1280, 800)
            return ImageMetadata(
                source="Wikimedia Commons",
                source_page=file_info.get("source_page"),
                original_file=file_info["original_file"],
                author=file_info.get("author"),
                license=license_name,
                license_url=file_info.get("license_url"),
                attribution=file_info.get("attribution"),
                width=orig_w,
                height=orig_h,
                match_method=match_method,
                match_confidence=match_confidence,
                downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                local_path=f"images/{place_id}/primary.webp",
                thumbnail_path=f"images/{place_id}/thumbnail.webp",
            )

        headers = {"User-Agent": self.settings.user_agent}
        try:
            with httpx.Client(headers=headers, timeout=30.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return None
                img_bytes = resp.content
        except Exception as e:
            print(f"Failed to download image {url}: {e}")
            return None

        try:
            im = Image.open(io.BytesIO(img_bytes))
            # Convert RGBA or Palette to RGB for webp
            if im.mode in ("RGBA", "LA", "P"):
                rgb_im = Image.new("RGB", im.size, (255, 255, 255))
                if im.mode == "P":
                    im = im.convert("RGBA")
                rgb_im.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
                im = rgb_im
            elif im.mode != "RGB":
                im = im.convert("RGB")

            orig_w, orig_h = im.size
            place_media_dir = output_dir / place_id
            place_media_dir.mkdir(parents=True, exist_ok=True)

            # Primary webp (max width 1280)
            max_w_primary = self.media_cfg.get("primary_image_max_width", 1280)
            if orig_w > max_w_primary:
                ratio = max_w_primary / orig_w
                new_h = int(orig_h * ratio)
                primary_im = im.resize((max_w_primary, new_h), Image.Resampling.LANCZOS)
            else:
                primary_im = im

            primary_path = place_media_dir / "primary.webp"
            primary_im.save(primary_path, "WEBP", quality=self.media_cfg.get("webp_quality", 85))

            # Thumbnail webp (max width 400)
            max_w_thumb = self.media_cfg.get("thumbnail_max_width", 400)
            if orig_w > max_w_thumb:
                ratio = max_w_thumb / orig_w
                new_h = int(orig_h * ratio)
                thumb_im = im.resize((max_w_thumb, new_h), Image.Resampling.LANCZOS)
            else:
                thumb_im = im

            thumb_path = place_media_dir / "thumbnail.webp"
            thumb_im.save(thumb_path, "WEBP", quality=80)

            # Relative paths for SQLite and release manifest
            rel_primary = f"images/{place_id}/primary.webp"
            rel_thumb = f"images/{place_id}/thumbnail.webp"

            return ImageMetadata(
                source="Wikimedia Commons",
                source_page=file_info.get("source_page"),
                original_file=file_info["original_file"],
                author=file_info.get("author"),
                license=license_name,
                license_url=file_info.get("license_url"),
                attribution=file_info.get("attribution"),
                width=orig_w,
                height=orig_h,
                match_method=match_method,
                match_confidence=match_confidence,
                downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                local_path=rel_primary,
                thumbnail_path=rel_thumb,
            )
        except Exception as e:
            print(f"Error processing image for {place_id}: {e}")
            return None
