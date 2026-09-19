import csv
import io
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import zipfile
import httpx

from ..config.settings import get_settings
from ..models.city import CityMetadata
from ..utils.geo import expand_bbox
from ..utils.text import slugify, normalize_name, fuzzy_name_similarity


class GeoNamesBulkSource:
    """
    GeoNames bulk data source adapter.
    Downloads and caches cities15000.zip and admin1CodesASCII.txt under data/source_cache/geonames/.
    Resolves canonical city entities, coordinates, alternate names, state/country hierarchy,
    timezones, and bounding boxes completely locally without live Nominatim queries.
    """

    CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
    ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"

    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = self.settings.source_cache_dir / "geonames"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cities_tsv_path = self.cache_dir / "cities15000.txt"
        self.admin1_path = self.cache_dir / "admin1CodesASCII.txt"
        self._cities_cache: Optional[List[Dict[str, Any]]] = None
        self._admin1_map: Optional[Dict[str, str]] = None

    def ensure_data(self) -> None:
        """Download and unpack GeoNames files if not present."""
        if not self.admin1_path.exists():
            print(f"[GeoNames] Downloading administrative hierarchy from {self.ADMIN1_URL}...")
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(self.ADMIN1_URL)
                resp.raise_for_status()
                with open(self.admin1_path, "wb") as f:
                    f.write(resp.content)
            print(f"[GeoNames] Cached admin1 codes to {self.admin1_path}")

        if not self.cities_tsv_path.exists():
            zip_path = self.cache_dir / "cities15000.zip"
            if not zip_path.exists():
                print(f"[GeoNames] Downloading cities dataset from {self.CITIES_URL}...")
                with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                    resp = client.get(self.CITIES_URL)
                    resp.raise_for_status()
                    with open(zip_path, "wb") as f:
                        f.write(resp.content)
                print(f"[GeoNames] Downloaded {zip_path.stat().st_size} bytes.")

            print(f"[GeoNames] Unpacking {zip_path.name}...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract("cities15000.txt", path=self.cache_dir)
            print(f"[GeoNames] Extracted cities15000.txt to {self.cities_tsv_path}")

    def _load_admin1(self) -> Dict[str, str]:
        if self._admin1_map is not None:
            return self._admin1_map

        self.ensure_data()
        mapping = {}
        with open(self.admin1_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    code, name = parts[0], parts[1]
                    mapping[code] = name
        self._admin1_map = mapping
        return mapping

    def _load_cities(self) -> List[Dict[str, Any]]:
        if self._cities_cache is not None:
            return self._cities_cache

        self.ensure_data()
        admin1_map = self._load_admin1()
        cities = []

        with open(self.cities_tsv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) < 19:
                    continue
                # row columns:
                # 0: geonameid, 1: name, 2: asciiname, 3: alternatenames, 4: latitude, 5: longitude
                # 8: country_code, 10: admin1_code, 14: population, 17: timezone
                try:
                    geoname_id = row[0]
                    name = row[1]
                    asciiname = row[2]
                    alt_names_raw = row[3]
                    lat = float(row[4])
                    lon = float(row[5])
                    cc = row[8]
                    admin1_code = row[10]
                    pop = int(row[14]) if row[14].isdigit() else 0
                    tz = row[17]

                    admin1_key = f"{cc}.{admin1_code}"
                    state_name = admin1_map.get(admin1_key, "")

                    alt_names = [a.strip() for a in alt_names_raw.split(",") if a.strip()] if alt_names_raw else []

                    cities.append({
                        "geoname_id": geoname_id,
                        "name": name,
                        "asciiname": asciiname,
                        "alternate_names": alt_names,
                        "latitude": lat,
                        "longitude": lon,
                        "country_code": cc,
                        "admin1_code": admin1_code,
                        "state": state_name,
                        "population": pop,
                        "timezone": tz,
                    })
                except Exception:
                    continue

        self._cities_cache = cities
        return cities

    def resolve_city(
        self,
        city_name: str,
        state_name: Optional[str] = None,
        country_name: str = "India"
    ) -> CityMetadata:
        """
        Find and resolve canonical city entity from local GeoNames data.
        Calculates canonical bounding box and hierarchy without requiring manual bbox input.
        """
        cities = self._load_cities()
        norm_city = normalize_name(city_name)
        norm_state = normalize_name(state_name) if state_name else None
        is_india = country_name.lower() in ("india", "in")
        target_cc = "IN" if is_india else None

        candidates = []
        for c in cities:
            if target_cc and c["country_code"] != target_cc:
                continue

            # Check primary names
            c_name_norm = normalize_name(c["name"])
            c_ascii_norm = normalize_name(c["asciiname"])

            name_match = (norm_city == c_name_norm or norm_city == c_ascii_norm)
            alt_match = False
            if not name_match:
                for alt in c["alternate_names"]:
                    if norm_city == normalize_name(alt):
                        alt_match = True
                        break

            if name_match or alt_match:
                state_match = True
                if norm_state and c["state"]:
                    c_state_norm = normalize_name(c["state"])
                    if norm_state not in c_state_norm and c_state_norm not in norm_state:
                        state_match = False

                score = 0
                if name_match:
                    score += 100
                elif alt_match:
                    score += 70
                if state_match:
                    score += 50
                # prefer higher population for metropolitan areas
                score += min(50, c["population"] // 100000)

                candidates.append((score, c))

        if not candidates:
            # Fallback: fuzzy search if exact match not found
            for c in cities:
                if target_cc and c["country_code"] != target_cc:
                    continue
                sim = fuzzy_name_similarity(city_name, c["name"])
                if sim >= 0.85:
                    candidates.append((int(sim * 80), c))

        if not candidates:
            raise ValueError(f"GeoNames could not resolve city '{city_name}', '{state_name}', '{country_name}'")

        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0][1]

        # Calculate bounding box automatically based on city population / metropolitan scale
        # Metropolitan (>2M): ~22km radius (~0.20 deg)
        # Large city (>500k): ~15km radius (~0.14 deg)
        # Mid city (>100k): ~10km radius (~0.09 deg)
        pop = best["population"]
        if pop >= 2000000:
            deg_delta = 0.17
        elif pop >= 500000:
            deg_delta = 0.12
        else:
            deg_delta = 0.08

        lat, lon = best["latitude"], best["longitude"]
        bbox: Tuple[float, float, float, float] = (
            round(lon - deg_delta, 6),
            round(lat - deg_delta, 6),
            round(lon + deg_delta, 6),
            round(lat + deg_delta, 6),
        )

        import datetime
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        city_slug = slugify(city_name)

        # Retain Hindi / regional alternate names
        cleaned_alts = []
        for alt in best["alternate_names"]:
            if alt.lower() != city_name.lower() and alt not in cleaned_alts:
                cleaned_alts.append(alt)

        return CityMetadata(
            id=city_slug,
            name=best["name"],
            state=best["state"] or (state_name.title() if state_name else ""),
            country=country_name.title(),
            iso_country=best["country_code"],
            center=(lat, lon),
            bbox=bbox,
            alternate_names=cleaned_alts[:10],
            timezone=best["timezone"],
            osm_place_id=None,
            geonames_id=int(best["geoname_id"]) if str(best["geoname_id"]).isdigit() else None,
            dataset_version="2.0.0",
            generated_at=now_iso,
        )
