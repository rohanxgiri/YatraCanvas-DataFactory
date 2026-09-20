import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


def audit_data_correctness(
    city_name: str,
    state_name: str,
    country_name: str = "India",
    version: str = "v3",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Audits released places for semantic consistency, coordinate bounds, duplicate external IDs,
    tier/category compatibility, and verifies image file existence on disk with licensing.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    city_slug = city_name.lower().replace(" ", "_")
    state_slug = state_name.lower().replace(" ", "_")
    country_slug = country_name.lower().replace(" ", "_")

    release_dir = project_root / "releases" / country_slug / state_slug / city_slug / version
    places_file = release_dir / "places.json"
    city_file = release_dir / "city.json"

    if not places_file.exists():
        return {
            "city": city_name,
            "status": "NOT_FOUND",
            "high_severity_issues": ["places_json_missing"],
            "high_severity_issues_count": 1,
            "minor_warnings": [],
            "minor_warnings_count": 0,
            "total_places_checked": 0,
            "coordinates_out_of_bounds": [],
            "duplicate_wikidata_ids": {},
            "duplicate_osm_ids": {},
            "image_audit": {
                "total_images": 0,
                "verified_on_disk": 0,
                "missing_on_disk": [],
                "missing_license": [],
                "category_fallbacks": [],
                "disk_verification_pct": 0.0,
            },
        }

    with open(places_file, "r", encoding="utf-8") as f:
        places: List[Dict[str, Any]] = json.load(f)

    bbox = None
    if city_file.exists():
        try:
            with open(city_file, "r", encoding="utf-8") as f:
                bbox = json.load(f).get("bbox")
        except Exception:
            pass

    high_severity_issues = []
    minor_warnings = []

    # Tracking for duplicate external IDs
    wikidata_to_places = defaultdict(list)

    # Image Audit Stats
    total_images_checked = 0
    images_verified_on_disk = 0
    images_missing_on_disk = []
    images_missing_license = []
    category_fallback_images = []

    for p in places:
        pid = p.get("id") or p.get("canonical_id")
        p_name = p.get("name", "")
        tier = p.get("tier", "discovery")
        cat = p.get("classification", {}).get("category") or p.get("category", "")
        subcat = p.get("classification", {}).get("subcategory") or p.get("subcategory", "")

        # 1. Coordinate check
        loc = p.get("location", {})
        lat = loc.get("latitude") or p.get("latitude")
        lon = loc.get("longitude") or p.get("longitude")

        if lat is None or lon is None:
            high_severity_issues.append({
                "place_id": pid,
                "name": p_name,
                "issue": "missing_coordinates",
            })
        elif not (-90 <= lat <= 90 and -180 <= lon <= 180):
            high_severity_issues.append({
                "place_id": pid,
                "name": p_name,
                "issue": "invalid_coordinates",
                "lat": lat,
                "lon": lon,
            })
        elif bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            # Allow 10% tolerance for border attractions
            d_lat = (max_lat - min_lat) * 0.10
            d_lon = (max_lon - min_lon) * 0.10
            if not (min_lat - d_lat <= lat <= max_lat + d_lat and min_lon - d_lon <= lon <= max_lon + d_lon):
                minor_warnings.append({
                    "place_id": pid,
                    "name": p_name,
                    "issue": "coordinate_outside_expanded_bbox",
                    "lat": lat,
                    "lon": lon,
                })

        # 2. Duplicate Wikidata IDs
        qid = p.get("wikidata_id") or p.get("external_ids", {}).get("wikidata_id")
        if qid:
            wikidata_to_places[qid].append((pid, p_name))

        # 3. Tier & Category Compatibility
        p_name_lower = p_name.lower()
        if cat in ("hotel", "transport") and tier in ("core_destination", "recommended"):
            minor_warnings.append({
                "place_id": pid,
                "name": p_name,
                "issue": f"{cat}_in_{tier}_tier",
            })
        if cat == "nature" and any(w in p_name_lower for w in ["hotel", "inn", "palace", "metro station", "railway station"]):
            high_severity_issues.append({
                "place_id": pid,
                "name": p_name,
                "issue": "category_semantic_conflict_nature_named_hotel_or_palace",
            })

        # 4. Image Audit (Section I)
        images_info = p.get("images", {})
        primary_img = images_info.get("primary") if isinstance(images_info, dict) else None
        if not primary_img and p.get("image_metadata"):
            primary_img = p.get("image_metadata")

        if primary_img:
            total_images_checked += 1
            local_path = primary_img.get("local_path")
            if local_path:
                full_img_path = release_dir / local_path
                if full_img_path.exists() and full_img_path.stat().st_size > 0:
                    images_verified_on_disk += 1
                else:
                    images_missing_on_disk.append({"place_id": pid, "path": local_path})
            else:
                images_missing_on_disk.append({"place_id": pid, "path": "none"})

            # Check license
            lic = primary_img.get("license")
            if not lic or lic.lower() in ("unknown", "unspecified", "all rights reserved"):
                images_missing_license.append({"place_id": pid, "license": lic})

            # Check for generic category placeholder images
            orig_file = (primary_img.get("original_file") or "").lower()
            if any(term in orig_file for term in ["placeholder", "default_category", "generic_hotel", "stock_temple"]):
                category_fallback_images.append({"place_id": pid, "file": orig_file})

    # Check for duplicate Wikidata IDs assigned to unrelated places
    for qid, place_list in wikidata_to_places.items():
        if len(place_list) > 1:
            names = [name for _, name in place_list]
            high_severity_issues.append({
                "wikidata_id": qid,
                "places_involved": place_list,
                "issue": "duplicate_wikidata_id_across_canonical_places",
            })

    image_audit_report = {
        "total_images_checked": total_images_checked,
        "images_verified_on_disk": images_verified_on_disk,
        "images_missing_on_disk_count": len(images_missing_on_disk),
        "images_missing_license_count": len(images_missing_license),
        "category_fallback_images_detected": len(category_fallback_images),
        "disk_verification_pct": round((images_verified_on_disk / max(1, total_images_checked)) * 100, 1) if total_images_checked else 100.0,
    }

    status = "PASS"
    if high_severity_issues:
        status = "FAIL"
    elif len(minor_warnings) > 10:
        status = "WARN"

    return {
        "city": city_name,
        "status": status,
        "total_places_audited": len(places),
        "high_severity_issues_count": len(high_severity_issues),
        "high_severity_issues": high_severity_issues,
        "minor_warnings_count": len(minor_warnings),
        "minor_warnings": minor_warnings[:10],
        "image_audit": image_audit_report,
    }
