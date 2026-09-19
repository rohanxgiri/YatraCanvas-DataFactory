import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import httpx

from ..config.settings import get_settings
from ..utils.cache import DiskCache
from ..utils.retry import retry_with_backoff


class OSMPlacesSource:
    def __init__(self):
        self.settings = get_settings()
        self.cache = DiskCache("osm_raw")
        self.sources_cfg = self.settings.sources_config.get("sources", {}).get("osm_overpass", {})
        self.endpoints = self.sources_cfg.get("endpoints", [
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"
        ])
        self.timeout = self.sources_cfg.get("timeout_seconds", 30.0)

    def fetch_places(
        self,
        bbox: Tuple[float, float, float, float],
        output_raw_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Fetch OSM places for the given bbox (min_lon, min_lat, max_lon, max_lat).
        Saves raw immutable data to output_raw_path.
        """
        if output_raw_path.exists():
            print(f"Loading raw OSM places from cache: {output_raw_path}")
            with open(output_raw_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._parse_elements(data.get("elements", []))

        min_lon, min_lat, max_lon, max_lat = bbox
        # Overpass bbox order: (min_lat, min_lon, max_lat, max_lon)
        overpass_bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"

        query = f"""[out:json][timeout:35];
(
  node["tourism"]({overpass_bbox});
  way["tourism"]({overpass_bbox});
  relation["tourism"]({overpass_bbox});

  node["historic"]({overpass_bbox});
  way["historic"]({overpass_bbox});
  relation["historic"]({overpass_bbox});

  node["amenity"~"place_of_worship|restaurant|cafe|theatre|cinema|marketplace"]({overpass_bbox});
  way["amenity"~"place_of_worship|restaurant|cafe|theatre|cinema|marketplace"]({overpass_bbox});

  node["leisure"~"park|garden|nature_reserve"]({overpass_bbox});
  way["leisure"~"park|garden|nature_reserve"]({overpass_bbox});
);
out center tags;
"""

        print(f"Querying OpenStreetMap (Overpass) for bbox: {overpass_bbox}...")
        raw_data = self._query_endpoints(query)
        if not raw_data or "elements" not in raw_data:
            print("Warning: OSM query returned no elements or failed.")
            return []

        # Write immutable raw JSON
        output_raw_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(raw_data['elements'])} raw OSM elements to {output_raw_path}")
        return self._parse_elements(raw_data["elements"])

    def _query_endpoints(self, query: str) -> Optional[Dict[str, Any]]:
        headers = {"User-Agent": self.settings.user_agent}
        for ep in self.endpoints:
            try:
                print(f"  Attempting Overpass endpoint: {ep}...")
                with httpx.Client(headers=headers, timeout=self.timeout) as client:
                    resp = client.post(ep, data={"data": query})
                    if resp.status_code == 200:
                        return resp.json()
                    else:
                        print(f"  Endpoint {ep} returned status {resp.status_code}")
            except Exception as e:
                print(f"  Endpoint {ep} error: {e}")
            time.sleep(1.0)
        return None

    def _parse_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        places = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name")
            if not name:
                continue

            # Determine coordinates
            lat, lon = None, None
            if el.get("type") == "node":
                lat, lon = el.get("lat"), el.get("lon")
            elif "center" in el:
                lat, lon = el["center"].get("lat"), el["center"].get("lon")

            if lat is None or lon is None:
                continue

            # Alternate names
            alternate_names = []
            for k in ["name", "alt_name", "loc_name", "official_name", "int_name"]:
                v = tags.get(k)
                if v and v != name and v not in alternate_names:
                    alternate_names.append(v)

            # Contact & hours
            website = tags.get("website") or tags.get("contact:website")
            phone = tags.get("phone") or tags.get("contact:phone")
            opening_hours = tags.get("opening_hours")
            wikidata = tags.get("wikidata")
            wikipedia = tags.get("wikipedia")

            # Address
            addr_parts = [
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:suburb"),
                tags.get("addr:city"),
                tags.get("addr:postcode"),
            ]
            address = ", ".join(p for p in addr_parts if p) or None

            places.append({
                "source": "openstreetmap",
                "id": f"{el.get('type')}/{el.get('id')}",
                "name": name,
                "alternate_names": alternate_names,
                "latitude": round(float(lat), 6),
                "longitude": round(float(lon), 6),
                "tags": tags,
                "website": website,
                "phone": phone,
                "opening_hours": opening_hours,
                "wikidata_id": wikidata,
                "wikipedia_url": f"https://en.wikipedia.org/wiki/{wikipedia}" if wikipedia and not wikipedia.startswith("http") else wikipedia,
                "address": address,
            })

        return places
