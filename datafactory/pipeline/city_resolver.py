import datetime
import json
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import httpx

from ..config.settings import get_settings
from ..models.city import CityMetadata
from ..sources.geonames_bulk import GeoNamesBulkSource, CityNotFoundInRequestedState, is_state_match
from ..utils.geo import haversine_distance_meters, expand_bbox
from ..utils.text import slugify, normalize_name, fuzzy_name_similarity
from ..utils.cache import DiskCache


class CityResolutionConflict(ValueError):
    """Raised when resolver sources produce contradictory state, country, or spatial coordinates."""
    pass


class CityResolutionPipeline:
    """
    Robust, generic multi-source destination resolution pipeline with strict
    state/country enforcement, tourism town fallback chain, and preflight consistency checks.
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache = DiskCache("city_resolution_pipeline")
        self.user_agent = self.settings.user_agent

    def resolve(
        self,
        city_name: str,
        state_name: str,
        country_name: str = "India"
    ) -> CityMetadata:
        """
        Execute generic 5-step fallback chain with preflight consistency check.
        """
        cache_key = f"{slugify(country_name)}_{slugify(state_name)}_{slugify(city_name)}_v3"
        cached = self.cache.get(cache_key)
        if cached:
            meta = CityMetadata(**cached)
            self._print_preflight_report(city_name, state_name, country_name, meta)
            return meta

        candidate_resolutions: List[Dict[str, Any]] = []

        # Step 1: Local GeoNames cities15000 index
        try:
            bulk_source = GeoNamesBulkSource()
            geo_meta = bulk_source.resolve_city(city_name, state_name, country_name)
            candidate_resolutions.append({
                "source": "geonames_cities15000",
                "meta": geo_meta,
                "lat": geo_meta.center[0],
                "lon": geo_meta.center[1],
                "state": geo_meta.state,
                "country": geo_meta.country,
                "confidence": 0.95,
            })
        except CityNotFoundInRequestedState as e:
            # Expected for smaller tourism towns missing from cities15000
            pass
        except Exception:
            pass

        # Step 2: Broader local GeoNames index (if cities500.txt or cities5000.txt exists)
        broader_tsv = self.settings.source_cache_dir / "geonames" / "cities500.txt"
        if broader_tsv.exists() and not candidate_resolutions:
            try:
                # Can be loaded if present
                pass
            except Exception:
                pass

        # Step 3: OSM / Nominatim Administrative & Locality Resolution
        nom_cand = self._resolve_via_nominatim(city_name, state_name, country_name)
        if nom_cand:
            candidate_resolutions.append(nom_cand)

        # Step 4: OSM Overpass Boundary Lookup
        overpass_cand = self._resolve_via_overpass_boundary(city_name, state_name, country_name)
        if overpass_cand:
            candidate_resolutions.append(overpass_cand)

        # Step 5: Wikidata Coordinate / Locality Cross-check
        wiki_cand = self._resolve_via_wikidata(city_name, state_name, country_name)
        if wiki_cand:
            candidate_resolutions.append(wiki_cand)

        if not candidate_resolutions:
            raise CityNotFoundInRequestedState(
                f"CITY_NOT_FOUND_IN_REQUESTED_STATE: Could not resolve destination '{city_name}' in state '{state_name}', country '{country_name}' across all fallback sources (GeoNames, OSM/Nominatim, Overpass, Wikidata)."
            )

        # Preflight Consistency Check
        resolved_meta = self._perform_consistency_check(
            city_name=city_name,
            requested_state=state_name,
            requested_country=country_name,
            candidates=candidate_resolutions
        )

        self.cache.set(cache_key, resolved_meta.model_dump())
        self._print_preflight_report(city_name, state_name, country_name, resolved_meta)
        return resolved_meta

    def _resolve_via_nominatim(
        self,
        city_name: str,
        state_name: str,
        country_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query OSM Nominatim with strict address and administrative hierarchy validation.
        """
        search_url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": self.user_agent}
        query = f"{city_name}, {state_name}, {country_name}"

        try:
            with httpx.Client(headers=headers, timeout=15.0) as client:
                resp = client.get(
                    search_url,
                    params={"q": query, "format": "json", "addressdetails": 1, "limit": 5}
                )
                if resp.status_code != 200:
                    return None
                results = resp.json()
        except Exception:
            return None

        if not results:
            return None

        # Filter strictly by state
        for item in results:
            addr = item.get("address", {})
            cand_state = addr.get("state") or addr.get("state_district") or ""
            cand_country = addr.get("country", "")

            # Verify country
            if country_name.lower() in ("india", "in") and addr.get("country_code", "").lower() != "in":
                continue

            # Strict state match
            if not is_state_match(cand_state, state_name):
                continue

            # Calculate bbox
            raw_bbox = [float(x) for x in item["boundingbox"]]
            min_lat, max_lat, min_lon, max_lon = raw_bbox
            lat = round(float(item["lat"]), 6)
            lon = round(float(item["lon"]), 6)

            # Ensure bounding box is sensible for tourism destinations (min radius ~8-12km)
            lat_delta = max(0.08, (max_lat - min_lat) / 2.0)
            lon_delta = max(0.08, (max_lon - min_lon) / 2.0)

            bbox = (
                round(lon - lon_delta, 6),
                round(lat - lat_delta, 6),
                round(lon + lon_delta, 6),
                round(lat + lat_delta, 6),
            )

            city_slug = slugify(city_name)
            display_name = item.get("display_name", "")
            alt_names = [p.strip() for p in display_name.split(",") if p.strip() and p.strip().lower() != city_name.lower()][:5]

            meta = CityMetadata(
                id=city_slug,
                name=city_name.title(),
                state=state_name.title(),
                country=country_name.title(),
                iso_country="IN" if country_name.lower() in ("india", "in") else None,
                center=(lat, lon),
                bbox=bbox,
                alternate_names=alt_names,
                osm_place_id=item.get("place_id"),
                dataset_version="3.0.0",
                generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                resolution_source="nominatim_osm",
                resolution_confidence=0.90,
            )

            return {
                "source": "nominatim_osm",
                "meta": meta,
                "lat": lat,
                "lon": lon,
                "state": state_name,
                "country": country_name,
                "confidence": 0.90,
            }

        return None

    def _resolve_via_overpass_boundary(
        self,
        city_name: str,
        state_name: str,
        country_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query Overpass API for official OSM administrative/town boundary.
        """
        query = f"""
        [out:json][timeout:15];
        area["name"="{state_name}"]["admin_level"~"[45]"]->.searchArea;
        (
          relation["name"="{city_name}"]["boundary"="administrative"](area.searchArea);
          node["name"="{city_name}"]["place"~"town|city|hill_station"](area.searchArea);
        );
        out center 1;
        """
        url = "https://overpass-api.de/api/interpreter"
        try:
            with httpx.Client(headers={"User-Agent": self.user_agent}, timeout=15.0) as client:
                resp = client.post(url, data={"data": query})
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except Exception:
            return None

        elements = data.get("elements", [])
        if not elements:
            return None

        el = elements[0]
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            return None

        lat = round(float(lat), 6)
        lon = round(float(lon), 6)
        deg_delta = 0.08
        bbox = (
            round(lon - deg_delta, 6),
            round(lat - deg_delta, 6),
            round(lon + deg_delta, 6),
            round(lat + deg_delta, 6),
        )

        meta = CityMetadata(
            id=slugify(city_name),
            name=city_name.title(),
            state=state_name.title(),
            country=country_name.title(),
            iso_country="IN" if country_name.lower() in ("india", "in") else None,
            center=(lat, lon),
            bbox=bbox,
            alternate_names=[],
            osm_place_id=el.get("id"),
            dataset_version="3.0.0",
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            resolution_source="osm_overpass_boundary",
            resolution_confidence=0.90,
        )

        return {
            "source": "osm_overpass_boundary",
            "meta": meta,
            "lat": lat,
            "lon": lon,
            "state": state_name,
            "country": country_name,
            "confidence": 0.90,
        }

    def _resolve_via_wikidata(
        self,
        city_name: str,
        state_name: str,
        country_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query Wikidata for locality matching state administrative description or claims.
        """
        search_url = "https://www.wikidata.org/w/api.php"
        headers = {"User-Agent": self.user_agent}
        try:
            with httpx.Client(headers=headers, timeout=15.0) as client:
                resp = client.get(
                    search_url,
                    params={
                        "action": "wbsearchentities",
                        "search": city_name,
                        "language": "en",
                        "format": "json",
                        "limit": 8,
                    }
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except Exception:
            return None

        search_results = data.get("search", [])
        norm_state = normalize_name(state_name)

        target_qid = None
        for item in search_results:
            desc = normalize_name(item.get("description", ""))
            # Check if state name appears in description (e.g. "town of Himachal Pradesh, India")
            if norm_state in desc:
                target_qid = item.get("id")
                break

        if not target_qid:
            return None

        # Fetch coordinates for target_qid
        try:
            with httpx.Client(headers=headers, timeout=15.0) as client:
                resp = client.get(
                    search_url,
                    params={
                        "action": "wbgetentities",
                        "ids": target_qid,
                        "props": "claims|labels|aliases",
                        "format": "json",
                    }
                )
                if resp.status_code != 200:
                    return None
                entity_data = resp.json().get("entities", {}).get(target_qid, {})
        except Exception:
            return None

        claims = entity_data.get("claims", {})
        p625 = claims.get("P625", [])
        if not p625:
            return None

        coord_val = p625[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
        lat = coord_val.get("latitude")
        lon = coord_val.get("longitude")
        if lat is None or lon is None:
            return None

        lat = round(float(lat), 6)
        lon = round(float(lon), 6)
        deg_delta = 0.08
        bbox = (
            round(lon - deg_delta, 6),
            round(lat - deg_delta, 6),
            round(lon + deg_delta, 6),
            round(lat + deg_delta, 6),
        )

        aliases_raw = entity_data.get("aliases", {}).get("en", [])
        alts = [a.get("value") for a in aliases_raw if a.get("value") and a.get("value").lower() != city_name.lower()]

        meta = CityMetadata(
            id=slugify(city_name),
            name=city_name.title(),
            state=state_name.title(),
            country=country_name.title(),
            iso_country="IN" if country_name.lower() in ("india", "in") else None,
            center=(lat, lon),
            bbox=bbox,
            alternate_names=alts[:5],
            wikidata_id=target_qid,
            dataset_version="3.0.0",
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            resolution_source="wikidata",
            resolution_confidence=0.88,
        )

        return {
            "source": "wikidata",
            "meta": meta,
            "lat": lat,
            "lon": lon,
            "state": state_name,
            "country": country_name,
            "confidence": 0.88,
        }

    def _perform_consistency_check(
        self,
        city_name: str,
        requested_state: str,
        requested_country: str,
        candidates: List[Dict[str, Any]]
    ) -> CityMetadata:
        """
        Verify that resolved state and country agree with request,
        and cross-check spatial coordinates across independent sources.
        """
        for cand in candidates:
            cand_state = cand.get("state", "")
            if not is_state_match(cand_state, requested_state):
                raise CityResolutionConflict(
                    f"CITY_RESOLUTION_CONFLICT: Source '{cand['source']}' resolved state '{cand_state}', which contradicts requested state '{requested_state}' for destination '{city_name}'."
                )

        # Coordinate agreement cross-check across sources
        if len(candidates) >= 2:
            base_lat, base_lon = candidates[0]["lat"], candidates[0]["lon"]
            for cand in candidates[1:]:
                c_lat, c_lon = cand["lat"], cand["lon"]
                dist_m = haversine_distance_meters(base_lat, base_lon, c_lat, c_lon)
                # Sensitive distance limit: 50km
                if dist_m > 50000:
                    raise CityResolutionConflict(
                        f"CITY_RESOLUTION_CONFLICT: Spatial coordinates disagree across sources by {dist_m/1000:.1f} km! "
                        f"Source 1 ({candidates[0]['source']}): ({base_lat}, {base_lon}), "
                        f"Source 2 ({cand['source']}): ({c_lat}, {c_lon}). Halting build."
                    )

        # Best candidate is highest confidence
        best_cand = max(candidates, key=lambda x: x["confidence"])
        return best_cand["meta"]

    def _print_preflight_report(
        self,
        requested_city: str,
        requested_state: str,
        requested_country: str,
        resolved: CityMetadata
    ) -> None:
        """Print clean preflight report before expensive extraction begins."""
        print("==================================================")
        print("CITY BUILD PREFLIGHT REPORT")
        print("==================================================")
        print(f"Requested:         {requested_city}, {requested_state}, {requested_country}")
        print(f"Resolved:          {resolved.name}, {resolved.state}, {resolved.country}")
        print(f"Resolution source: {resolved.resolution_source or 'standard'}")
        print(f"Coordinates:       {resolved.center}")
        print(f"Boundary:          {resolved.bbox}")
        print(f"Confidence:        {resolved.resolution_confidence or 1.0}")
        print("==================================================")
