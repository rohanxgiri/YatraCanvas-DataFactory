"""Isolate legacy source adapters without duplicating extraction implementations."""
import json
from pathlib import Path
from .hashing import slugify
from .atomic import atomic_json
from .geo import haversine_distance_meters


def scope_source_cache(adapter, city):
    metadata = city.model_dump() if hasattr(city, "model_dump") else city
    base = adapter.cache_dir
    scope = Path(slugify(metadata["country"])) / slugify(metadata["state"]) / slugify(metadata["name"])
    target = base / scope
    target.mkdir(parents=True, exist_ok=True)
    city_slug = slugify(metadata["name"])
    # Migrate only spatially validated legacy list snapshots. Never adopt name-only decisions.
    for suffix in ("listings", "attractions", "places"):
        legacy, scoped = base / f"{city_slug}_{suffix}.json", target / f"{city_slug}_{suffix}.json"
        if legacy.exists() and not scoped.exists():
            try:
                rows = json.loads(legacy.read_text(encoding="utf-8"))
                if not isinstance(rows, list):
                    continue
                from ..pipeline.geographic_assurance import coordinates, valid_coordinates
                valid_rows = [r for r in rows if valid_coordinates(*coordinates(r))
                              and haversine_distance_meters(*coordinates(r), *metadata["center"]) <= 120_000]
                if valid_rows:
                    atomic_json(scoped, valid_rows)
            except (OSError, ValueError, TypeError):
                pass
    atomic_json(target / "city_context.json", {k: metadata.get(k) for k in ("id", "name", "state", "country", "bbox", "center")})
    adapter.cache_dir = target
    return adapter
