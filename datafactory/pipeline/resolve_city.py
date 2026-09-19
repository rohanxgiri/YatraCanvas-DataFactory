import json
from pathlib import Path
from typing import Optional
import yaml

from ..config.settings import get_settings
from ..models.city import CityMetadata
from ..sources.geonames_bulk import GeoNamesBulkSource
from ..sources.geonames import CityResolver
from ..utils.text import slugify


def run_resolve_city(
    city_name: str,
    state_name: str,
    country_name: str = "India",
    resume: bool = False
) -> CityMetadata:
    settings = get_settings()
    c_slug = slugify(country_name)
    s_slug = slugify(state_name)
    city_slug = slugify(city_name)

    city_raw_dir = settings.raw_dir / c_slug / s_slug / city_slug
    city_raw_dir.mkdir(parents=True, exist_ok=True)
    city_resolved_path = city_raw_dir / "city_resolved.json"

    if resume and city_resolved_path.exists():
        print(f"[Stage 1] Loading existing city resolution from {city_resolved_path}")
        with open(city_resolved_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CityMetadata(**data)

    print(f"[Stage 1/20] Resolving canonical city entity: {city_name}, {state_name}, {country_name}...")
    try:
        bulk_resolver = GeoNamesBulkSource()
        city_meta = bulk_resolver.resolve_city(city_name, state_name, country_name)
    except Exception as e:
        print(f"[GeoNames Bulk] Warning: Bulk resolution failed ({e}); falling back to Nominatim...")
        resolver = CityResolver()
        city_meta = resolver.resolve(city_name, state_name, country_name)

    # Save to immutable raw path
    with open(city_resolved_path, "w", encoding="utf-8") as f:
        json.dump(city_meta.model_dump(), f, ensure_ascii=False, indent=2)

    # Save generated city config
    city_cfg_path = settings.config_dir / "generated_cities" / f"{city_slug}.yaml"
    city_cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(city_cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(city_meta.model_dump(), f, sort_keys=False)

    print(f"       City resolved: {city_meta.name} (center: {city_meta.center}, bbox: {city_meta.bbox})")
    return city_meta
