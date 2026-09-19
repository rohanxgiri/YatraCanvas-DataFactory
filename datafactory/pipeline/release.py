import datetime
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from ..config.settings import get_settings
from ..models.city import CityMetadata, CityRef
from ..models.place import (
    Place,
    PlaceTier,
    PlaceLocation,
    PlaceClassification,
    PlacePlanning,
    PlaceContact,
    PlaceOpeningHours,
    PlaceExternalIds,
    QualityScore,
)
from ..models.image import PlaceImages, ImageMetadata
from ..models.provenance import SourceRecord, FieldProvenance
from ..models.manifest import CityManifest, ManifestRecordCounts
from ..exporters.json_exporter import (
    export_places_json,
    export_places_jsonl,
    export_city_json,
    export_images_manifest,
    export_sources_json,
)
from ..exporters.parquet_exporter import export_places_parquet
from ..exporters.sqlite_exporter import export_sqlite
from ..reports.html_reporter import generate_html_report
from ..reports.breakdown import generate_core_breakdown, generate_image_failure_breakdown
from ..utils.hashing import compute_sha256, slugify


def run_release(
    city_meta: CityMetadata,
    accepted_records: List[Dict[str, Any]],
    images_manifest: Dict[str, Any],
    total_raw_count: int,
    rejected_count: int,
    quarantined_count: int,
    duplicate_merges_count: int,
    sources_count: Dict[str, int],
    category_conflicts_count: int = 0,
    entity_conflicts_count: int = 0,
    alias_conflicts_count: int = 0,
    coordinate_conflicts_count: int = 0,
    version: str = "v3",
) -> Tuple[Path, CityManifest]:
    settings = get_settings()
    c_slug = slugify(city_meta.country)
    s_slug = slugify(city_meta.state)
    city_slug = slugify(city_meta.name)

    release_dir = settings.releases_dir / c_slug / s_slug / city_slug / version
    release_dir.mkdir(parents=True, exist_ok=True)
    release_images_dir = release_dir / "images"
    release_images_dir.mkdir(parents=True, exist_ok=True)

    city_ref = CityRef(
        id=city_meta.id,
        name=city_meta.name,
        state=city_meta.state,
        country=city_meta.country,
    )

    canonical_places: List[Place] = []
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Track by-tier statistics
    tier_counts = defaultdict(int)
    tier_stats = {
        "core_destination": {"count": 0, "with_wikidata": 0, "with_wikipedia": 0, "with_image": 0, "with_hours": 0, "with_website": 0, "multi_source": 0},
        "recommended": {"count": 0, "with_wikidata": 0, "with_wikipedia": 0, "with_image": 0, "with_hours": 0, "with_website": 0, "multi_source": 0},
        "discovery": {"count": 0, "with_wikidata": 0, "with_wikipedia": 0, "with_image": 0, "with_hours": 0, "with_website": 0, "multi_source": 0},
        "support": {"count": 0, "with_wikidata": 0, "with_wikipedia": 0, "with_image": 0, "with_hours": 0, "with_website": 0, "multi_source": 0},
    }

    for r in accepted_records:
        primary_img = None
        gallery_imgs = []
        if r.get("image_metadata"):
            primary_img = ImageMetadata(**r["image_metadata"])

            # Copy media files to release folder
            src_media = settings.media_dir / r["canonical_id"]
            dst_media = release_images_dir / r["canonical_id"]
            if src_media.exists() and not dst_media.exists():
                shutil.copytree(src_media, dst_media)

        for g in r.get("gallery_metadata", []):
            gallery_imgs.append(ImageMetadata(**g))

        # Sources records
        sources_list = []
        for s in r.get("sources_provenance", []):
            if isinstance(s, dict):
                sources_list.append(SourceRecord(
                    source=s.get("source", "overture"),
                    source_id=str(s.get("source_id") or r.get("canonical_id")),
                    retrieved_at=s.get("retrieved_at", now_iso),
                ))
            else:
                sources_list.append(SourceRecord(
                    source="overture",
                    source_id=str(r.get("source_id")),
                    retrieved_at=now_iso,
                ))

        # Provenance records
        prov_list = []
        for f in r.get("field_provenance", []):
            prov_list.append(FieldProvenance(**f))

        # Tier
        raw_tier = r.get("tier", "discovery")
        try:
            place_tier = PlaceTier(raw_tier)
        except ValueError:
            place_tier = PlaceTier.DISCOVERY

        tier_str = place_tier.value
        tier_counts[tier_str] += 1
        st = tier_stats.setdefault(tier_str, {"count": 0, "with_wikidata": 0, "with_wikipedia": 0, "with_image": 0, "with_hours": 0, "with_website": 0, "multi_source": 0})
        st["count"] += 1
        if r.get("wikidata_id"):
            st["with_wikidata"] += 1
        if r.get("wikipedia_url"):
            st["with_wikipedia"] += 1
        if primary_img:
            st["with_image"] += 1
        if r.get("opening_hours") or (r.get("opening_hours_record", {}).get("raw")):
            st["with_hours"] += 1
        if r.get("website"):
            st["with_website"] += 1
        if len(r.get("sources_provenance", [])) > 1:
            st["multi_source"] += 1

        ext_ids = r.get("external_ids", {})
        p = Place(
            id=r["canonical_id"],
            name=r["name"],
            name_en=r.get("name_en") or r["name"],
            name_hi=r.get("name_hi"),
            alternate_names=r.get("alternate_names", []),
            alternate_name_records=r.get("alternate_name_records", []),
            city=city_ref,
            location=PlaceLocation(
                latitude=r["latitude"],
                longitude=r["longitude"],
                address=r.get("address"),
            ),
            classification=PlaceClassification(
                category=r["category"],
                subcategory=r.get("subcategory"),
                tags=r.get("planning", {}).get("tags", r.get("tags", [])),
            ),
            tier=place_tier,
            travel_relevance_score=r.get("travel_relevance_score", 0.0),
            prominence_score=r.get("prominence_score", 0.0),
            anomaly_score=r.get("anomaly_score", 0.0),
            anomaly_flags=r.get("anomaly_flags", []),
            planning=PlacePlanning(
                recommended_visit_minutes=r.get("planning", {}).get("recommended_visit_minutes", 60),
                visit_duration_source=r.get("planning", {}).get("visit_duration_source", "category_heuristic"),
                rule_version=r.get("planning", {}).get("rule_version", "3.0"),
                tourism_priority=r.get("planning", {}).get("tourism_priority", 0.50),
                planning_priority=r.get("planning", {}).get("planning_priority", 0.50),
                indoor_outdoor=r.get("planning", {}).get("indoor_outdoor", "both"),
                interest_tags=r.get("planning", {}).get("interest_tags", []),
                family_friendly=r.get("planning", {}).get("family_friendly", True),
                best_time=r.get("planning", {}).get("best_time", "all_day"),
            ),
            contact=PlaceContact(
                website=r.get("website"),
                phone=r.get("phone"),
                email=r.get("email"),
            ),
            opening_hours=PlaceOpeningHours(
                raw=r.get("opening_hours") or (r.get("opening_hours_record", {}).get("raw")),
                normalized=r.get("opening_hours") or (r.get("opening_hours_record", {}).get("normalized")),
                source=r.get("opening_hours_source") or (r.get("opening_hours_record", {}).get("source")),
                retrieved_at=r.get("opening_hours_record", {}).get("retrieved_at"),
                confidence=r.get("opening_hours_record", {}).get("confidence", 0.8),
                verified=r.get("opening_hours_record", {}).get("verified", False),
            ),
            images=PlaceImages(
                primary=primary_img,
                gallery=gallery_imgs,
            ),
            external_ids=PlaceExternalIds(
                overture_id=ext_ids.get("overture_ids", [None])[0] if ext_ids.get("overture_ids") else None,
                osm_id=ext_ids.get("openstreetmap_ids", [None])[0] if ext_ids.get("openstreetmap_ids") else None,
                wikidata_id=r.get("wikidata_id"),
                foursquare_id=ext_ids.get("foursquare_ids", [None])[0] if ext_ids.get("foursquare_ids") else None,
                wikivoyage_listing_id=ext_ids.get("wikivoyage_ids", [None])[0] if ext_ids.get("wikivoyage_ids") else None,
                alltheplaces_id=ext_ids.get("alltheplaces_ids", [None])[0] if ext_ids.get("alltheplaces_ids") else None,
            ),
            quality=QualityScore(**r.get("quality", {
                "overall": 0.5,
                "identity_confidence": 0.5,
                "coordinate_confidence": 0.5,
                "image_confidence": 0.0,
                "metadata_completeness": 0.5,
            })),
            sources=sources_list,
            provenance_records=prov_list,
            generated_at=now_iso,
            schema_version="3.0",
        )
        canonical_places.append(p)

    # 1. Export JSON / JSONL
    places_json_path = release_dir / "places.json"
    places_jsonl_path = release_dir / "places.jsonl"
    city_json_path = release_dir / "city.json"
    images_manifest_path = release_dir / "image_manifest.json"
    images_manifest_legacy = release_dir / "images_manifest.json"
    sources_json_path = release_dir / "sources.json"

    export_places_json(canonical_places, places_json_path)
    export_places_jsonl(canonical_places, places_jsonl_path)
    export_city_json(city_meta, city_json_path)
    export_images_manifest(images_manifest, images_manifest_path)
    export_images_manifest(images_manifest, images_manifest_legacy)

    # 2. Source Manifest & Licensing Isolation
    source_manifest_path = release_dir / "source_manifest.json"
    license_manifest_path = release_dir / "license_manifest.json"

    source_manifest_data = {
        "generated_at": now_iso,
        "city": city_meta.name,
        "state": city_meta.state,
        "country": city_meta.country,
        "sources": {
            "geonames": {
                "source": "GeoNames",
                "dataset_name": "cities15000",
                "license": "CC-BY-4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution": "GeoNames (geonames.org)",
                "role": "Canonical administrative hierarchy, boundary and coordinates",
            },
            "wikivoyage": {
                "source": "Wikivoyage",
                "dataset_name": "Wikivoyage Travel Guides",
                "license": "CC-BY-SA-4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Wikivoyage contributors",
                "role": "Curated tourist sights, structured opening hours, and travel listing metadata",
            },
            "wikidata": {
                "source": "Wikidata",
                "dataset_name": "Wikidata Knowledge Base",
                "license": "CC0-1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "attribution": "Wikidata contributors",
                "role": "Spatial travel destination discovery and verified entity claims",
            },
            "openstreetmap": {
                "source": "OpenStreetMap",
                "dataset_name": "Geofabrik Regional PBF",
                "license": "ODbL-1.0",
                "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
                "attribution": "© OpenStreetMap contributors",
                "role": "Local travel tags, opening hours, contact details, and coordinates",
            },
            "overture": {
                "source": "Overture Maps",
                "dataset_name": "Overture Places",
                "license": "CDLA-Permissive-2.0",
                "license_url": "https://cdla.dev/permissive-2-0/",
                "attribution": "Overture Maps Foundation",
                "role": "Broad commercial venues, discovery venues, and validation",
            },
            "wikimedia_commons": {
                "source": "Wikimedia Commons",
                "dataset_name": "Wikimedia Commons Media",
                "license": "Per-file open licenses (CC-BY, CC-BY-SA, CC0, Public Domain)",
                "license_url": "https://commons.wikimedia.org/",
                "attribution": "Individual photographers as recorded in image_manifest.json",
                "role": "Verified landmark WebP photography (primary.webp, thumbnail.webp)",
            },
        },
        "license_isolation_policy": "Factual non-copyrightable data merged into canonical permissive dataset. Wikivoyage prose and Commons imagery maintain exact author attribution and license provenance.",
    }
    with open(source_manifest_path, "w", encoding="utf-8") as f:
        json.dump(source_manifest_data, f, ensure_ascii=False, indent=2)

    license_manifest_data = {
        "city_pack_version": version,
        "canonical_data_license": "Permissive / Attribution Required",
        "attributions": [
            "OpenStreetMap: © OpenStreetMap contributors under ODbL 1.0",
            "Wikivoyage: © Wikivoyage contributors under CC-BY-SA 4.0",
            "GeoNames: Data provided by GeoNames under CC-BY 4.0",
            "Wikidata: Data provided by Wikidata under CC0 1.0 Universal",
            "Overture Maps: Data provided by Overture Maps Foundation under CDLA Permissive 2.0",
            "Wikimedia Commons: Individual media licenses tracked per file in image_manifest.json",
        ],
    }
    with open(license_manifest_path, "w", encoding="utf-8") as f:
        json.dump(license_manifest_data, f, ensure_ascii=False, indent=2)

    # 3. Export Parquet
    places_parquet_path = release_dir / "places.parquet"
    export_places_parquet(canonical_places, places_parquet_path)

    # 4. Export SQLite
    sqlite_path = release_dir / "yatracanvas.db"
    export_sqlite(city_meta, canonical_places, sqlite_path)

    # 5. Generate Checksums
    checksums = {}
    release_files = [
        "city.json",
        "places.json",
        "places.jsonl",
        "places.parquet",
        "image_manifest.json",
        "source_manifest.json",
        "license_manifest.json",
        "yatracanvas.db",
    ]
    for fn in release_files:
        fp = release_dir / fn
        if fp.exists():
            checksums[fn] = compute_sha256(fp)

    checksums_path = release_dir / "checksums.json"
    with open(checksums_path, "w", encoding="utf-8") as f:
        json.dump(checksums, f, ensure_ascii=False, indent=2)

    # 6. Build Manifest
    category_counts = defaultdict(int)
    places_with_images = sum(1 for p in canonical_places if p.images.primary is not None)
    places_with_hours = sum(1 for p in canonical_places if p.opening_hours.raw is not None)
    places_with_wiki = sum(1 for p in canonical_places if p.external_ids.wikidata_id is not None)

    for p in canonical_places:
        category_counts[p.classification.category] += 1

    # Determine 3-dimension quality gates
    core_cnt = tier_stats.get("core_destination", {}).get("count", 0)
    core_wiki = tier_stats.get("core_destination", {}).get("with_wikidata", 0)
    core_img = tier_stats.get("core_destination", {}).get("with_image", 0)

    pipeline_health = "PASS"
    data_quality = "PASS"
    if entity_conflicts_count > 0 or alias_conflicts_count > 0 or category_conflicts_count > 0:
        data_quality = "WARN"

    source_coverage = "PASS"
    if core_cnt >= 20:
        wiki_ratio = core_wiki / core_cnt
        img_ratio = core_img / core_cnt
        if wiki_ratio < 0.20 or img_ratio < 0.08:
            source_coverage = "FAIL"
        elif wiki_ratio < 0.50 or img_ratio < 0.25:
            source_coverage = "WARN"

    manifest_counts = ManifestRecordCounts(
        total_raw_candidates=total_raw_count,
        accepted=len(canonical_places),
        rejected=rejected_count,
        quarantined=quarantined_count,
        duplicate_merges=duplicate_merges_count,
        with_images=places_with_images,
        with_opening_hours=places_with_hours,
        with_wikidata=places_with_wiki,
        category_conflicts=category_conflicts_count,
        entity_conflicts=entity_conflicts_count,
        alias_conflicts=alias_conflicts_count,
        image_conflicts=0,
        coordinate_conflicts=coordinate_conflicts_count,
        by_tier=dict(tier_counts),
        by_tier_stats=tier_stats,
        by_category=dict(category_counts),
    )

    city_manifest = CityManifest(
        schema_version="3.0",
        city_pack_version=version,
        city_id=city_meta.id,
        city_name=city_meta.name,
        state=city_meta.state,
        country=city_meta.country,
        generated_at=now_iso,
        pipeline_health=pipeline_health,
        data_quality=data_quality,
        source_coverage=source_coverage,
        source_versions={k: str(v) for k, v in sources_count.items()},
        counts=manifest_counts,
        checksums=checksums,
    )

    manifest_path = release_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(city_manifest.model_dump(), f, ensure_ascii=False, indent=2)

    # 7. Generate Core and Image Breakdown Reports
    generate_core_breakdown(city_slug, accepted_records, settings.reports_dir)
    generate_image_failure_breakdown(city_slug, accepted_records, settings.reports_dir)

    # 8. Generate Quality Reports
    report_html_path = release_dir / "quality_report.html"
    reports_latest_dir = settings.reports_dir / city_slug / "latest"
    reports_latest_dir.mkdir(parents=True, exist_ok=True)

    generate_html_report(
        city_meta=city_meta,
        places=canonical_places,
        manifest=city_manifest,
        output_path=report_html_path,
    )
    # Copy report to reports/latest
    shutil.copy(report_html_path, reports_latest_dir / "report.html")

    summary_data = {
        "city": city_meta.name,
        "state": city_meta.state,
        "country": city_meta.country,
        "version": version,
        "total_raw_candidates": total_raw_count,
        "sources_count": sources_count,
        "accepted_places": len(canonical_places),
        "rejected_places": rejected_count,
        "quarantined_places": quarantined_count,
        "duplicate_merges": duplicate_merges_count,
        "by_tier": dict(tier_counts),
        "by_tier_stats": tier_stats,
        "image_coverage_pct": round(places_with_images / len(canonical_places) * 100, 1) if canonical_places else 0.0,
        "with_images_count": places_with_images,
        "opening_hours_coverage_pct": round(places_with_hours / len(canonical_places) * 100, 1) if canonical_places else 0.0,
        "with_opening_hours_count": places_with_hours,
        "wikidata_coverage_pct": round(places_with_wiki / len(canonical_places) * 100, 1) if canonical_places else 0.0,
        "with_wikidata_count": places_with_wiki,
        "category_breakdown": dict(category_counts),
        "generated_at": now_iso,
    }
    with open(reports_latest_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"[Stage 20/20] City Pack release complete:")
    print(f"       Release bundle: {release_dir}")
    print(f"       Total accepted places: {len(canonical_places)}")
    print(f"       Core destinations: {tier_counts.get('core_destination', 0)}")
    print(f"       Recommended: {tier_counts.get('recommended', 0)}")
    print(f"       Discovery: {tier_counts.get('discovery', 0)}")
    print(f"       Support: {tier_counts.get('support', 0)}")
    print(f"       Places with exact images: {places_with_images}")
    print(f"       Places with verified Wikidata: {places_with_wiki}")
    print(f"       Places with opening hours: {places_with_hours}")

    return release_dir, city_manifest
