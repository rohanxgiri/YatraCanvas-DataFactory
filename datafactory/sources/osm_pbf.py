import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import httpx
import osmium

from ..config.settings import get_settings
from ..utils.geo import is_point_in_bbox
from ..utils.text import clean_string, slugify


ZONE_MAP = {
    "rajasthan": "northern-zone-latest.osm.pbf",
    "uttar_pradesh": "northern-zone-latest.osm.pbf",
    "uttar pradesh": "northern-zone-latest.osm.pbf",
    "delhi": "northern-zone-latest.osm.pbf",
    "haryana": "northern-zone-latest.osm.pbf",
    "punjab": "northern-zone-latest.osm.pbf",
    "himachal_pradesh": "northern-zone-latest.osm.pbf",
    "uttarakhand": "northern-zone-latest.osm.pbf",
    "jammu_and_kashmir": "northern-zone-latest.osm.pbf",
    "maharashtra": "western-zone-latest.osm.pbf",
    "gujarat": "western-zone-latest.osm.pbf",
    "goa": "western-zone-latest.osm.pbf",
    "tamil_nadu": "southern-zone-latest.osm.pbf",
    "karnataka": "southern-zone-latest.osm.pbf",
    "kerala": "southern-zone-latest.osm.pbf",
    "andhra_pradesh": "southern-zone-latest.osm.pbf",
    "telangana": "southern-zone-latest.osm.pbf",
    "west_bengal": "eastern-zone-latest.osm.pbf",
    "bihar": "eastern-zone-latest.osm.pbf",
    "odisha": "eastern-zone-latest.osm.pbf",
    "madhya_pradesh": "central-zone-latest.osm.pbf",
}

GEOFABRIK_BASE_URL = "https://download.geofabrik.de/asia/india/"


class OSMTravelHandler(osmium.SimpleHandler):
    """Fast libosmium streaming handler for travel-relevant POIs inside a bounding box."""

    def __init__(self, bbox: Tuple[float, float, float, float]):
        super().__init__()
        self.min_lon, self.min_lat, self.max_lon, self.max_lat = bbox
        self.places: List[Dict[str, Any]] = []

    def node(self, n):
        try:
            lat = n.location.lat
            lon = n.location.lon
        except Exception:
            return

        if not (self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon):
            return

        tags = {t.k: t.v for t in n.tags}
        if not self._is_travel_relevant(tags):
            return

        name = tags.get("name:en") or tags.get("name")
        if not name:
            return

        self.places.append(self._build_place_record(f"node/{n.id}", lat, lon, tags))

    def _is_travel_relevant(self, tags: Dict[str, str]) -> bool:
        if "tourism" in tags:
            return True
        if "historic" in tags:
            return True
        if "leisure" in tags and tags["leisure"] in ("park", "garden", "nature_reserve", "stadium", "sports_centre"):
            return True
        if "amenity" in tags and tags["amenity"] in (
            "place_of_worship", "restaurant", "cafe", "theatre", "cinema",
            "marketplace", "fast_food", "bar", "pub", "bus_station"
        ):
            return True
        if "natural" in tags and tags["natural"] in ("water", "peak", "beach"):
            return True
        if "railway" in tags and tags["railway"] == "station":
            return True
        if "aeroway" in tags and tags["aeroway"] in ("aerodrome", "terminal"):
            return True
        return False

    def _build_place_record(self, osm_id: str, lat: float, lon: float, tags: Dict[str, str]) -> Dict[str, Any]:
        name = tags.get("name")
        name_en = tags.get("name:en")
        name_hi = tags.get("name:hi")

        primary_name = name_en or name or ""

        # Collect alternate names
        alternate_names = []
        if name and name != primary_name:
            alternate_names.append(name)
        if name_hi and name_hi != primary_name and name_hi not in alternate_names:
            alternate_names.append(name_hi)
        for k, v in tags.items():
            if k.startswith("name:") and v and v != primary_name and v not in alternate_names:
                alternate_names.append(v)
        if tags.get("alt_name") and tags["alt_name"] not in alternate_names:
            alternate_names.append(tags["alt_name"])
        if tags.get("official_name") and tags["official_name"] not in alternate_names:
            alternate_names.append(tags["official_name"])

        # Address
        addr_parts = []
        for k in ["addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode"]:
            if tags.get(k):
                addr_parts.append(tags[k])
        address = ", ".join(addr_parts) if addr_parts else None

        # Websites / Phones
        website = tags.get("website") or tags.get("contact:website") or tags.get("url")
        phone = tags.get("phone") or tags.get("contact:phone")

        return {
            "source": "openstreetmap",
            "id": osm_id,
            "source_id": osm_id,
            "name": primary_name,
            "name_en": name_en,
            "name_hi": name_hi,
            "alternate_names": alternate_names,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "tags": tags,
            "tourism": tags.get("tourism"),
            "historic": tags.get("historic"),
            "amenity": tags.get("amenity"),
            "leisure": tags.get("leisure"),
            "natural": tags.get("natural"),
            "opening_hours": tags.get("opening_hours"),
            "website": website,
            "phone": phone,
            "address": address,
            "wikidata": tags.get("wikidata"),
            "wikidata_id": tags.get("wikidata"),
            "wikipedia": tags.get("wikipedia"),
            "wikimedia_commons": tags.get("wikimedia_commons"),
        }


class OSMPbfSource:
    """
    Local OpenStreetMap extractor using cached Geofabrik regional PBF files.
    Eliminates flaky public Overpass endpoints and extracts full travel tags locally.
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = self.settings.source_cache_dir / "osm"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_zone_pbf_path(self, state_name: str) -> Path:
        norm_state = state_name.lower().replace(" ", "_")
        zone_filename = ZONE_MAP.get(norm_state, "northern-zone-latest.osm.pbf")
        return self.cache_dir / zone_filename

    def ensure_zone_pbf(self, state_name: str) -> Optional[Path]:
        pbf_path = self.get_zone_pbf_path(state_name)
        if pbf_path.exists() and pbf_path.stat().st_size > 1000000:
            return pbf_path

        zone_filename = pbf_path.name
        download_url = GEOFABRIK_BASE_URL + zone_filename

        print(f"[OSM] Downloading regional Geofabrik PBF for {state_name}: {download_url}...")
        try:
            with httpx.Client(timeout=300.0, follow_redirects=True) as client:
                with client.stream("GET", download_url) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    with open(pbf_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0 and downloaded % (20 * 1024 * 1024) < (1024 * 1024):
                                print(f"       Downloaded {downloaded // (1024*1024)}MB / {total // (1024*1024)}MB...")

            print(f"[OSM] Cached {pbf_path.name} ({pbf_path.stat().st_size // (1024*1024)}MB) to {self.cache_dir}")
            return pbf_path
        except Exception as e:
            print(f"[OSM] Warning: Could not download Geofabrik PBF: {e}")
            if pbf_path.exists():
                pbf_path.unlink()
            return None

    def extract_city_places(
        self,
        bbox: Tuple[float, float, float, float],
        state_name: str,
        city_slug: str,
        output_raw_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract travel-relevant OSM places inside bbox from local cached PBF.
        If PBF is not yet downloaded and existing raw JSON exists, seamlessly loads it.
        """
        # Check if output_raw_path or city cache already exists
        city_cached = self.cache_dir / f"{city_slug}_places.json"
        if output_raw_path and output_raw_path.exists():
            print(f"[OSM] Loading raw OSM places from {output_raw_path}")
            return self._load_from_json(output_raw_path)

        if city_cached.exists():
            print(f"[OSM] Loading raw OSM places from cache: {city_cached}")
            places = self._load_from_json(city_cached)
            if output_raw_path:
                output_raw_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_raw_path, "w", encoding="utf-8") as f:
                    json.dump({"elements": [p.get("tags", {}) for p in places]}, f)
            return places

        # Try to ensure and parse local PBF
        pbf_path = self.ensure_zone_pbf(state_name)
        if pbf_path and pbf_path.exists():
            print(f"[OSM] Streaming local PBF extraction from {pbf_path.name} for bbox {bbox}...")
            handler = OSMTravelHandler(bbox)
            try:
                handler.apply_file(str(pbf_path))
                places = handler.places
                print(f"[OSM] Extracted {len(places)} travel places from local PBF.")

                # Cache city places
                with open(city_cached, "w", encoding="utf-8") as f:
                    json.dump(places, f, ensure_ascii=False, indent=2)

                if output_raw_path:
                    output_raw_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_raw_path, "w", encoding="utf-8") as f:
                        json.dump({"elements": places}, f, ensure_ascii=False, indent=2)

                return places
            except Exception as e:
                print(f"[OSM] Error during osmium extraction: {e}")

        # Fallback: if raw JSON exists in data/raw/... from previous runs, load and normalize it
        if output_raw_path and output_raw_path.exists():
            return self._load_from_json(output_raw_path)

        print("[OSM] No local PBF or cached data found.")
        return []

    def _load_from_json(self, path: Path) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            elements = data
        elif isinstance(data, dict):
            elements = data.get("elements", [])
        else:
            elements = []

        places = []
        for el in elements:
            if "source" in el and el["source"] == "openstreetmap":
                places.append(el)
                continue

            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name")
            if not name:
                continue

            lat = el.get("lat")
            lon = el.get("lon")
            if lat is None and "center" in el:
                lat = el["center"].get("lat")
                lon = el["center"].get("lon")

            if lat is None or lon is None:
                continue

            osm_id = f"{el.get('type', 'node')}/{el.get('id', '')}"
            primary_name = tags.get("name:en") or tags.get("name", "")

            alts = []
            if tags.get("name") and tags["name"] != primary_name:
                alts.append(tags["name"])
            if tags.get("name:hi"):
                alts.append(tags["name:hi"])
            if tags.get("alt_name"):
                alts.append(tags["alt_name"])

            addr_parts = [tags[k] for k in ["addr:street", "addr:city"] if tags.get(k)]
            address = ", ".join(addr_parts) if addr_parts else None

            places.append({
                "source": "openstreetmap",
                "id": osm_id,
                "source_id": osm_id,
                "name": primary_name,
                "name_en": tags.get("name:en"),
                "name_hi": tags.get("name:hi"),
                "alternate_names": alts,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "tags": tags,
                "tourism": tags.get("tourism"),
                "historic": tags.get("historic"),
                "amenity": tags.get("amenity"),
                "leisure": tags.get("leisure"),
                "natural": tags.get("natural"),
                "opening_hours": tags.get("opening_hours"),
                "website": tags.get("website") or tags.get("contact:website"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "address": address,
                "wikidata": tags.get("wikidata"),
                "wikidata_id": tags.get("wikidata"),
                "wikipedia": tags.get("wikipedia"),
                "wikimedia_commons": tags.get("wikimedia_commons"),
            })

        return places
