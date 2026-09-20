import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx

from ..config.settings import get_settings
from ..utils.geo import is_point_in_bbox
from ..utils.text import clean_string, slugify


class FoursquareOSSource:
    """
    Foursquare Open Source Places adapter.
    Gracefully checks for FSQ_TOKEN environment variable.
    If missing or invalid, cleanly skips without breaking the pipeline.
    When available, extracts open-source POIs with quality and closure filtering.
    """

    API_URL = "https://api.foursquare.com/v3/places/search"

    def __init__(self):
        self.settings = get_settings()
        self.token = os.getenv("FSQ_TOKEN") or os.getenv("FOURSQUARE_API_KEY")
        self.cache_dir = self.settings.source_cache_dir / "foursquare"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        return bool(self.token and len(self.token.strip()) > 5)

    def fetch_places(
        self,
        bbox: Tuple[float, float, float, float],
        city_name: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        if not self.is_available():
            print("[Foursquare OS] No FSQ_TOKEN configured; cleanly skipping Foursquare source.")
            return []

        city_slug = slugify(city_name)
        cached_file = self.cache_dir / f"{city_slug}_places.json"
        if cached_file.exists():
            print(f"[Foursquare OS] Loading cached places from {cached_file}")
            with open(cached_file, "r", encoding="utf-8") as f:
                return json.load(f)

        min_lon, min_lat, max_lon, max_lat = bbox
        center_lat = round((min_lat + max_lat) / 2.0, 6)
        center_lon = round((min_lon + max_lon) / 2.0, 6)

        headers = {
            "Accept": "application/json",
            "Authorization": self.token.strip(),
        }
        params = {
            "ll": f"{center_lat},{center_lon}",
            "radius": 15000,
            "limit": limit,
            "fields": "fsq_id,name,geocodes,location,categories,tel,website,closed_bucket,verified",
        }

        print(f"[Foursquare OS] Querying FSQ Places around ({center_lat}, {center_lon})...")
        try:
            with httpx.Client(headers=headers, timeout=20.0) as client:
                resp = client.get(self.API_URL, params=params)
                if resp.status_code != 200:
                    print(f"[Foursquare OS] API returned status {resp.status_code}; skipping.")
                    return []
                data = resp.json()
        except Exception as e:
            print(f"[Foursquare OS] Request failed: {e}; skipping.")
            return []

        results = data.get("results", [])
        places = []

        for r in results:
            # Check closures
            closed_bucket = r.get("closed_bucket", "").lower()
            if closed_bucket in ("very_likely_closed", "permanently_closed"):
                continue

            geo = r.get("geocodes", {}).get("main", {})
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            if lat is None or lon is None or not is_point_in_bbox(lat, lon, bbox):
                continue

            name = clean_string(r.get("name", ""))
            if not name:
                continue

            cats = r.get("categories", [])
            primary_cat_name = cats[0].get("name") if cats else "commercial"
            cat_id = cats[0].get("id") if cats else None

            # Map category
            cat = "food" if any(k in primary_cat_name.lower() for k in ["restaurant", "dining", "bakery"]) else "discovery"
            if "hotel" in primary_cat_name.lower():
                cat = "hotel"
            elif "coffee" in primary_cat_name.lower() or "cafe" in primary_cat_name.lower():
                cat = "cafe"

            loc = r.get("location", {})
            addr = loc.get("formatted_address") or loc.get("address")

            places.append({
                "source": "foursquare",
                "source_id": r.get("fsq_id"),
                "foursquare_id": r.get("fsq_id"),
                "name": name,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "category": cat,
                "subcategory": primary_cat_name.lower().replace(" ", "_"),
                "suggested_tier": "discovery" if cat != "hotel" else "support",
                "address": addr,
                "phone": r.get("tel"),
                "website": r.get("website"),
                "fsq_category_id": cat_id,
            })

        with open(cached_file, "w", encoding="utf-8") as f:
            json.dump(places, f, ensure_ascii=False, indent=2)

        print(f"[Foursquare OS] Discovered and cached {len(places)} places.")
        return places
