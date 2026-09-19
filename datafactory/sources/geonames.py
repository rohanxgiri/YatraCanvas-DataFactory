import datetime
from typing import Optional, Tuple
import httpx
from ..config.settings import get_settings
from ..models.city import CityMetadata, CityRef
from ..utils.cache import DiskCache
from ..utils.text import slugify


class CityResolver:
    def __init__(self):
        self.settings = get_settings()
        self.cache = DiskCache("city_resolution")
        self.sources_cfg = self.settings.sources_config.get("sources", {}).get("nominatim", {})
        self.user_agent = self.sources_cfg.get("user_agent", self.settings.user_agent)

    def resolve(self, city_name: str, state_name: str, country_name: str = "India") -> CityMetadata:
        cache_key = f"{slugify(country_name)}_{slugify(state_name)}_{slugify(city_name)}"
        cached = self.cache.get(cache_key)
        if cached:
            return CityMetadata(**cached)

        query = f"{city_name}, {state_name}, {country_name}"
        search_url = self.sources_cfg.get("search_url", "https://nominatim.openstreetmap.org/search")

        with httpx.Client(headers={"User-Agent": self.user_agent}, timeout=15.0) as client:
            resp = client.get(
                search_url,
                params={"q": query, "format": "json", "addressdetails": 1, "limit": 1}
            )
            resp.raise_for_status()
            results = resp.json()

        if not results:
            # Try just city and country if state is not found
            with httpx.Client(headers={"User-Agent": self.user_agent}, timeout=15.0) as client:
                resp = client.get(
                    search_url,
                    params={"q": f"{city_name}, {country_name}", "format": "json", "addressdetails": 1, "limit": 1}
                )
                resp.raise_for_status()
                results = resp.json()

        if not results:
            raise ValueError(f"Could not resolve city: {query}")

        item = results[0]
        # Nominatim returns bbox as [min_lat, max_lat, min_lon, max_lon]
        raw_bbox = [float(x) for x in item["boundingbox"]]
        min_lat, max_lat, min_lon, max_lon = raw_bbox
        # Our standard bbox is (min_lon, min_lat, max_lon, max_lat)
        bbox: Tuple[float, float, float, float] = (
            round(min_lon, 6),
            round(min_lat, 6),
            round(max_lon, 6),
            round(max_lat, 6),
        )

        center_lat = round(float(item["lat"]), 6)
        center_lon = round(float(item["lon"]), 6)
        city_slug = slugify(city_name)

        meta = CityMetadata(
            id=city_slug,
            name=city_name.title(),
            state=state_name.title(),
            country=country_name.title(),
            iso_country="IN" if country_name.lower() in ("india", "in") else None,
            center=(center_lat, center_lon),
            bbox=bbox,
            alternate_names=[n for n in [item.get("display_name", "").split(",")[0]] if n and n.lower() != city_name.lower()],
            osm_place_id=item.get("place_id"),
            dataset_version="1.0.0",
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        self.cache.set(cache_key, meta.model_dump())
        return meta
