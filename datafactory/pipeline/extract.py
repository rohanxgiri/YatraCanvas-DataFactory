import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from ..config.settings import get_settings
from ..models.city import CityMetadata
from ..sources.overture import OverturePlacesSource
from ..sources.osm_pbf import OSMPbfSource
from ..sources.wikivoyage import WikivoyageSource
from ..sources.wikidata import WikidataEnricher
from ..sources.foursquare_os import FoursquareOSSource
from ..sources.alltheplaces import AllThePlacesSource
from ..utils.geo import expand_bbox
from ..utils.text import slugify


def run_extract(
    city_meta: CityMetadata,
    resume: bool = False
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Autonomous multi-source discovery extractor.
    Independently queries:
    1. Wikivoyage (curated sights, hours, images)
    2. Wikidata (spatial attraction discovery)
    3. OpenStreetMap Local PBF (full travel tags & hours)
    4. Overture Maps (broad businesses & venues)
    5. Foursquare OS (optional, graceful skip)
    6. AllThePlaces (optional supplementary)
    """
    settings = get_settings()
    c_slug = slugify(city_meta.country)
    s_slug = slugify(city_meta.state)
    city_slug = slugify(city_meta.name)

    raw_base = settings.raw_dir / c_slug / s_slug / city_slug
    overture_raw_path = raw_base / "overture" / "places_raw.parquet"
    osm_raw_path = raw_base / "osm" / "places_raw.json"

    # Expand city bbox slightly (3%) to capture border attractions (e.g. Amber Fort, Jaigarh)
    search_bbox = expand_bbox(city_meta.bbox, margin_ratio=0.03)

    discovered_sources: Dict[str, List[Dict[str, Any]]] = {}

    # Source 1: Wikivoyage Travel Listings
    print(f"[Stage 2/20] Discovering Wikivoyage travel listings for {city_meta.name}...")
    wv_source = WikivoyageSource()
    wv_places = wv_source.fetch_city_listings(city_meta.name, search_bbox)
    discovered_sources["wikivoyage"] = wv_places
    print(f"       Wikivoyage listings: {len(wv_places)}")

    # Source 2: Wikidata Spatial Attractions Discovery
    print(f"[Stage 3/20] Discovering Wikidata spatial travel attractions for {city_meta.name}...")
    wiki_enricher = WikidataEnricher()
    wd_places = wiki_enricher.discover_city_attractions(search_bbox, city_meta.name)
    discovered_sources["wikidata"] = wd_places
    print(f"       Wikidata spatial attractions: {len(wd_places)}")

    # Source 3: OpenStreetMap Local PBF Extraction
    print(f"[Stage 4/20] Extracting OpenStreetMap local travel POIs for {city_meta.name}...")
    osm_source = OSMPbfSource()
    osm_places = osm_source.extract_city_places(search_bbox, city_meta.state, city_slug, osm_raw_path)
    discovered_sources["openstreetmap"] = osm_places
    print(f"       OSM places candidates: {len(osm_places)}")

    # Source 4: Overture Maps Places
    print(f"[Stage 5/20] Extracting Overture Maps places for {city_meta.name}...")
    overture_source = OverturePlacesSource()
    overture_places = overture_source.fetch_places(search_bbox, overture_raw_path)
    discovered_sources["overture"] = overture_places
    print(f"       Overture places candidates: {len(overture_places)}")

    # Source 5: Foursquare OS Places (Optional)
    print(f"[Stage 6/20] Checking Foursquare OS Places for {city_meta.name}...")
    fsq_source = FoursquareOSSource()
    fsq_places = fsq_source.fetch_places(search_bbox, city_meta.name)
    if fsq_places:
        discovered_sources["foursquare"] = fsq_places
        print(f"       Foursquare places: {len(fsq_places)}")

    # Source 6: AllThePlaces (Optional)
    atp_source = AllThePlacesSource()
    atp_places = atp_source.extract_places(search_bbox, city_slug)
    if atp_places:
        discovered_sources["alltheplaces"] = atp_places
        print(f"       AllThePlaces: {len(atp_places)}")

    total_discovered = sum(len(v) for v in discovered_sources.values())
    sources_count = {k: len(v) for k, v in discovered_sources.items()}
    print(f"[Extract Summary] Total candidates discovered across {len(discovered_sources)} independent sources: {total_discovered}")
    return discovered_sources, sources_count

