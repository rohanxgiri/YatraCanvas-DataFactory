import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ..config.settings import get_settings
from ..utils.geo import is_point_in_bbox
from ..utils.text import clean_string, slugify


class AllThePlacesSource:
    """
    AllThePlaces published dataset adapter.
    Reads published GeoJSON extracts cached under data/source_cache/alltheplaces/.
    Does not run spiders live.
    Provides supplementary business chain locations, addresses, websites, and phones.
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = self.settings.source_cache_dir / "alltheplaces"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_places(
        self,
        bbox: Tuple[float, float, float, float],
        city_slug: str
    ) -> List[Dict[str, Any]]:
        cached_file = self.cache_dir / f"{city_slug}_places.json"
        if cached_file.exists():
            with open(cached_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Look for any GeoJSON files in the cache dir
        geojson_files = list(self.cache_dir.glob("*.geojson"))
        if not geojson_files:
            return []

        places = []
        for gf in geojson_files:
            try:
                with open(gf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                features = data.get("features", [])
                for feat in features:
                    geom = feat.get("geometry", {})
                    props = feat.get("properties", {})
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        lon, lat = float(coords[0]), float(coords[1])
                        if is_point_in_bbox(lat, lon, bbox):
                            name = props.get("name") or props.get("brand")
                            if name:
                                places.append({
                                    "source": "alltheplaces",
                                    "source_id": props.get("ref") or f"atp_{len(places)}",
                                    "alltheplaces_id": props.get("ref"),
                                    "name": clean_string(name),
                                    "latitude": round(lat, 6),
                                    "longitude": round(lon, 6),
                                    "category": "shopping",
                                    "subcategory": "store",
                                    "suggested_tier": "discovery",
                                    "website": props.get("website"),
                                    "phone": props.get("phone"),
                                    "address": props.get("addr:full") or props.get("address"),
                                    "opening_hours": props.get("opening_hours"),
                                })
            except Exception:
                continue

        if places:
            with open(cached_file, "w", encoding="utf-8") as f:
                json.dump(places, f, ensure_ascii=False, indent=2)

        return places
