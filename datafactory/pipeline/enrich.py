import datetime
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..config.settings import get_settings
from ..sources.wikidata import WikidataEnricher
from ..utils.geo import haversine_distance_meters
from ..utils.text import slugify, fuzzy_name_similarity


def run_enrich(
    places: List[Dict[str, Any]],
    city_name: str,
) -> List[Dict[str, Any]]:
    """
    Enrich canonical places with Wikidata, Wikipedia, Commons category,
    official website, and structured opening hours with field-level provenance.
    Uses local in-memory spatial index from cached city attractions before live API fallback.
    """
    settings = get_settings()
    enricher = WikidataEnricher()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    city_slug = slugify(city_name)
    cached_attractions_path = settings.source_cache_dir / "wikidata" / f"{city_slug}_attractions.json"
    spatial_attractions: List[Dict[str, Any]] = []
    if cached_attractions_path.exists():
        try:
            with open(cached_attractions_path, "r", encoding="utf-8") as f:
                spatial_attractions = json.load(f)
        except Exception:
            pass

    enriched_places = []
    wikidata_matches = 0
    opening_hours_count = 0

    print(f"[Stage 10/20] Enriching places with Wikidata claims and structured hours...", flush=True)

    for p in places:
        item = dict(p)
        item.setdefault("field_provenance", [])

        tier = item.get("tier", "discovery")
        qid = item.get("wikidata_id")
        lat = item.get("latitude")
        lon = item.get("longitude")
        name = item.get("name", "")

        # 1. If entity already has Wikidata QID (from Wikivoyage, OSM, or Wikidata discovery),
        # ensure all structured claims (P18, commons category, website, wikipedia) are populated
        if qid:
            details = enricher.get_entity_details(qid)
            if details:
                wikidata_matches += 1
                if details.get("p18_image") and not item.get("wikidata_p18"):
                    item["wikidata_p18"] = details["p18_image"]
                if details.get("commons_category") and not item.get("commons_category"):
                    item["commons_category"] = details["commons_category"]
                if details.get("wikipedia_url") and not item.get("wikipedia_url"):
                    item["wikipedia_url"] = details["wikipedia_url"]
                if details.get("official_website") and not item.get("website"):
                    item["website"] = details["official_website"]
                if details.get("label_hi") and not item.get("name_hi"):
                    item["name_hi"] = details["label_hi"]

                item["field_provenance"].append({
                    "field_name": "wikidata_id",
                    "value": qid,
                    "source": "wikidata",
                    "source_id": qid,
                    "retrieved_at": now_iso,
                    "confidence": 1.0,
                })

        # 2. If entity lacks Wikidata QID, match against local in-memory spatial attractions index
        elif spatial_attractions and lat is not None and lon is not None:
            matched_ent = None
            for sa in spatial_attractions:
                sa_lat = sa.get("latitude")
                sa_lon = sa.get("longitude")
                if sa_lat is None or sa_lon is None:
                    continue
                if abs(lat - sa_lat) > 0.01 or abs(lon - sa_lon) > 0.01:
                    continue
                dist = haversine_distance_meters(lat, lon, sa_lat, sa_lon)
                sim = fuzzy_name_similarity(name, sa.get("name", ""))
                if (dist <= 300 and sim >= 0.70) or (dist <= 30 and sim >= 0.50):
                    matched_ent = sa
                    break

            if matched_ent:
                wikidata_matches += 1
                item["wikidata_id"] = matched_ent["wikidata_id"]
                if matched_ent.get("wikidata_p18") and not item.get("wikidata_p18"):
                    item["wikidata_p18"] = matched_ent["wikidata_p18"]
                if matched_ent.get("commons_category") and not item.get("commons_category"):
                    item["commons_category"] = matched_ent["commons_category"]
                if matched_ent.get("wikipedia_url") and not item.get("wikipedia_url"):
                    item["wikipedia_url"] = matched_ent["wikipedia_url"]
                if matched_ent.get("website") and not item.get("website"):
                    item["website"] = matched_ent["website"]

                item["field_provenance"].append({
                    "field_name": "wikidata_id",
                    "value": matched_ent["wikidata_id"],
                    "source": "wikidata",
                    "source_id": matched_ent["wikidata_id"],
                    "retrieved_at": now_iso,
                    "confidence": 0.95,
                })

            # Fallback for Core Destinations only if still missing QID
            elif tier == "core_destination":
                wiki_ent = enricher.resolve_entity(
                    name=name,
                    city_name=city_name,
                    lat=lat,
                    lon=lon,
                )
                if wiki_ent:
                    wikidata_matches += 1
                    item["wikidata_id"] = wiki_ent.get("wikidata_id")
                    if wiki_ent.get("p18_image"):
                        item["wikidata_p18"] = wiki_ent["p18_image"]
                    if wiki_ent.get("commons_category"):
                        item["commons_category"] = wiki_ent["commons_category"]
                    if wiki_ent.get("wikipedia_url") and not item.get("wikipedia_url"):
                        item["wikipedia_url"] = wiki_ent["wikipedia_url"]
                    if wiki_ent.get("official_website") and not item.get("website"):
                        item["website"] = wiki_ent["official_website"]
                    if wiki_ent.get("label_hi") and not item.get("name_hi"):
                        item["name_hi"] = wiki_ent["label_hi"]

                    item["field_provenance"].append({
                        "field_name": "wikidata_id",
                        "value": wiki_ent.get("wikidata_id"),
                        "source": "wikidata",
                        "source_id": wiki_ent.get("wikidata_id"),
                        "retrieved_at": now_iso,
                        "confidence": 0.90,
                    })

        # 3. Structured Opening Hours
        raw_hours = item.get("opening_hours")
        hours_source = item.get("opening_hours_source") or "osm"
        if raw_hours:
            opening_hours_count += 1
            item["opening_hours_record"] = {
                "raw": raw_hours,
                "normalized": raw_hours,
                "source": hours_source,
                "retrieved_at": now_iso,
                "confidence": 0.90 if hours_source in ("wikivoyage", "openstreetmap") else 0.70,
                "verified": hours_source == "wikivoyage",
                "conflicts": [],
            }
            item["field_provenance"].append({
                "field_name": "opening_hours",
                "value": raw_hours,
                "source": hours_source,
                "source_id": item.get("canonical_id"),
                "retrieved_at": now_iso,
                "confidence": 0.90,
            })
        else:
            item["opening_hours_record"] = {
                "raw": None,
                "normalized": None,
                "source": None,
                "retrieved_at": None,
                "confidence": 0.0,
                "verified": False,
                "conflicts": [],
            }

        enriched_places.append(item)

    print(f"       Total places with Wikidata linked: {wikidata_matches}", flush=True)
    print(f"       Total places with verified opening hours: {opening_hours_count}", flush=True)
    return enriched_places
