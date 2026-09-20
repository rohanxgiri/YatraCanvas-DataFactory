import datetime
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx
import wikitextparser as wtp

from ..config.settings import get_settings
from ..utils.geo import haversine_distance_meters, is_point_in_bbox
from ..utils.text import clean_string, normalize_name, slugify


class WikivoyageSource:
    """
    Wikivoyage travel dataset adapter.
    Parses structured listing templates ({{see}}, {{do}}, {{eat}}, {{drink}}, {{buy}}, {{sleep}}, {{listing}})
    extracting high-confidence travel destinations, structured opening hours, Commons images, and Wikidata QIDs.
    Preserves Wikivoyage CC-BY-SA 4.0 license provenance and isolates long text descriptions.
    """

    API_URL = "https://en.wikivoyage.org/w/api.php"
    USER_AGENT = "YatraCanvas-DataFactory/2.0 (travel open data; contact: info@yatracanvas.org)"

    TEMPLATE_TIER_MAPPING = {
        "see": "core_destination",
        "do": "recommended",
        "eat": "discovery",
        "drink": "discovery",
        "buy": "discovery",
        "sleep": "support",
        "go": "support",
        "listing": "recommended",
    }

    TEMPLATE_CATEGORY_MAPPING = {
        "see": ("heritage", "attraction"),
        "do": ("experience", "activity"),
        "eat": ("food", "restaurant"),
        "drink": ("cafe", "coffee_shop"),
        "buy": ("shopping", "bazaar"),
        "sleep": ("hotel", "hotel"),
        "go": ("transport", "station"),
        "listing": ("experience", "attraction"),
    }

    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = self.settings.source_cache_dir / "wikivoyage"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_city_listings(
        self,
        city_name: str,
        city_bbox: Optional[Tuple[float, float, float, float]] = None,
        alternate_names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch or load cached Wikivoyage listings for a city.
        Returns normalized candidate records with provenance and isolated prose.
        """
        city_slug = slugify(city_name)
        cached_file = self.cache_dir / f"{city_slug}_listings.json"

        if cached_file.exists():
            print(f"[Wikivoyage] Loading cached listings from {cached_file}")
            with open(cached_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            return self._filter_by_bbox(records, city_bbox)

        # Resolve article title using generic candidates (canonical, ASCII-folded, alternate names)
        title_res = self.resolve_article_title(city_name, alternate_names)
        if not title_res:
            print(f"[Wikivoyage] No Wikivoyage article found for '{city_name}'")
            return []

        resolved_title, wikitext = title_res

        # Parse listings
        listings = self._parse_wikitext_listings(wikitext, city_name)

        # Cache parsed listings
        with open(cached_file, "w", encoding="utf-8") as f:
            json.dump(listings, f, ensure_ascii=False, indent=2)

        # Also save raw wikitext for provenance
        raw_file = self.cache_dir / f"{city_slug}_raw.wiki"
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write(wikitext)

        print(f"[Wikivoyage] Extracted and cached {len(listings)} structured listings for {city_name} (article: '{resolved_title}')")
        return self._filter_by_bbox(listings, city_bbox)

    def resolve_article_title(
        self,
        city_name: str,
        alternate_names: Optional[List[str]] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Generic title candidate resolution for MediaWiki/Wikivoyage API.
        Tries:
          1. Original canonical name (e.g. Rishīkesh)
          2. ASCII-folded name (e.g. Rishikesh)
          3. Alternate names from metadata
          4. Common aliases
        Caches the resolved article title. Returns (resolved_title, wikitext) or None.
        """
        import unicodedata
        city_slug = slugify(city_name)
        title_cache_file = self.cache_dir / f"{city_slug}_resolved_title.json"

        if title_cache_file.exists():
            try:
                with open(title_cache_file, "r", encoding="utf-8") as f:
                    cached_info = json.load(f)
                cached_title = cached_info.get("resolved_title")
                if cached_title:
                    wikitext = self._fetch_article_wikitext(cached_title)
                    if wikitext:
                        return cached_title, wikitext
            except Exception:
                pass

        # Build ordered candidate list
        candidates = []
        if city_name:
            candidates.append(city_name.strip())

        # ASCII-folded candidate
        folded = unicodedata.normalize("NFKD", city_name).encode("ASCII", "ignore").decode("utf-8").strip()
        if folded and folded not in candidates:
            candidates.append(folded)

        if alternate_names:
            for alt in alternate_names:
                if alt and alt.strip() and alt.strip() not in candidates:
                    candidates.append(alt.strip())
                alt_folded = unicodedata.normalize("NFKD", alt).encode("ASCII", "ignore").decode("utf-8").strip()
                if alt_folded and alt_folded not in candidates:
                    candidates.append(alt_folded)

        for cand in candidates:
            wikitext = self._fetch_article_wikitext(cand)
            if wikitext:
                # Cache the successful title resolution
                try:
                    with open(title_cache_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "requested_name": city_name,
                            "resolved_title": cand,
                            "cached_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        }, f, indent=2)
                except Exception:
                    pass
                return cand, wikitext

        return None


    def _fetch_article_wikitext(self, title: str) -> Optional[str]:
        headers = {"User-Agent": self.USER_AGENT}
        params = {
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvslots": "*",
            "rvprop": "content",
            "format": "json",
            "redirects": "1",
        }
        try:
            with httpx.Client(headers=headers, timeout=30.0) as client:
                resp = client.get(self.API_URL, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except Exception as e:
            print(f"[Wikivoyage] Error querying API for '{title}': {e}")
            return None

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        page = next(iter(pages.values()))
        if "missing" in page:
            return None

        revs = page.get("revisions", [])
        if not revs:
            return None

        return revs[0].get("slots", {}).get("main", {}).get("*")

    def _parse_wikitext_listings(self, wikitext: str, city_name: str) -> List[Dict[str, Any]]:
        parsed = wtp.parse(wikitext)
        listings = []
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        recognized_templates = {"see", "do", "eat", "drink", "buy", "sleep", "go", "listing"}

        for t in parsed.templates:
            t_name = t.name.strip().lower()
            if t_name not in recognized_templates:
                continue

            args = {p.name.strip().lower(): p.value.strip() for p in t.arguments}

            name = clean_string(args.get("name", ""))
            if not name or len(name) < 2:
                continue

            # Strip wikitext markup like [[ ... | ... ]] or '''
            name = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", name)
            name = clean_string(name.replace("'''", "").replace("''", ""))

            alt_name = clean_string(args.get("alt", ""))
            lat_str = args.get("lat")
            lon_str = args.get("long") or args.get("lon")

            lat = None
            lon = None
            if lat_str and lon_str:
                try:
                    lat = round(float(lat_str), 6)
                    lon = round(float(lon_str), 6)
                except ValueError:
                    pass

            address = clean_string(args.get("address", ""))
            directions = clean_string(args.get("directions", ""))
            url = clean_string(args.get("url", ""))
            phone = clean_string(args.get("phone", ""))
            email = clean_string(args.get("email", ""))
            hours = clean_string(args.get("hours", ""))
            price = clean_string(args.get("price", ""))
            content = clean_string(args.get("content", ""))
            image = clean_string(args.get("image", ""))
            wikidata = clean_string(args.get("wikidata", ""))
            wikipedia = clean_string(args.get("wikipedia", ""))
            lastedit = clean_string(args.get("lastedit", ""))

            # Clean image filename: strip File: or Image: prefixes
            if image:
                image = re.sub(r"^(?:File|Image):", "", image, flags=re.I).strip()

            # Clean wikidata QID
            if wikidata and not re.match(r"^Q\d+$", wikidata):
                wikidata = None

            # Determine category and tier mapping
            default_tier = self.TEMPLATE_TIER_MAPPING.get(t_name, "discovery")
            cat, subcat = self.TEMPLATE_CATEGORY_MAPPING.get(t_name, ("experience", "attraction"))

            # Alternate names list
            alt_names = []
            if alt_name and alt_name.lower() != name.lower():
                alt_names.append(alt_name)

            listing_id = f"wv_{slugify(city_name)}_{slugify(name)}"

            listings.append({
                "source": "wikivoyage",
                "source_id": listing_id,
                "name": name,
                "alternate_names": alt_names,
                "latitude": lat,
                "longitude": lon,
                "category": cat,
                "subcategory": subcat,
                "suggested_tier": default_tier,
                "listing_type": t_name,
                "address": address or None,
                "directions": directions or None,
                "website": url or None,
                "phone": phone or None,
                "email": email or None,
                "opening_hours": hours or None,
                "price": price or None,
                "wikidata_id": wikidata or None,
                "wikipedia_title": wikipedia or None,
                "commons_image": image or None,
                "lastedit": lastedit or None,
                # Isolated prose kept separate under CC-BY-SA 4.0 license
                "prose": {
                    "text": content,
                    "license": "CC-BY-SA-4.0",
                    "source_article": f"https://en.wikivoyage.org/wiki/{city_name.replace(' ', '_')}",
                    "retrieved_at": now_iso,
                },
                "retrieved_at": now_iso,
            })

        return listings

    def _filter_by_bbox(
        self,
        listings: List[Dict[str, Any]],
        bbox: Optional[Tuple[float, float, float, float]]
    ) -> List[Dict[str, Any]]:
        if not bbox:
            return listings

        min_lon, min_lat, max_lon, max_lat = bbox
        # Allow small margin around bounding box for sights slightly outside municipal border
        margin = 0.05
        filtered = []
        for l in listings:
            lat = l.get("latitude")
            lon = l.get("longitude")
            if lat is not None and lon is not None:
                if (min_lat - margin <= lat <= max_lat + margin and
                    min_lon - margin <= lon <= max_lon + margin):
                    filtered.append(l)
            else:
                # Retain places without coords as discovery candidates if they have wikidata or clear name
                filtered.append(l)

        return filtered
