import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from ..config.settings import get_settings
from ..utils.geo import is_point_in_bbox, expand_bbox, haversine_distance_meters
from ..utils.text import fuzzy_name_similarity


def run_validate_and_quarantine(
    places: List[Dict[str, Any]],
    city_bbox: Tuple[float, float, float, float],
    quarantine_output_path: Path,
    media_dir: Path
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate canonical places against quality, coordinate, schema, and semantic rules.
    Quarantines suspicious, conflicting, or invalid records to quarantine_output_path.
    """
    settings = get_settings()
    q_cfg = settings.quality_config
    threshold = q_cfg.get("thresholds", {}).get("quarantine_threshold", 0.25)
    cat_cfg = settings.categories_config
    valid_categories = set(cat_cfg.get("canonical_categories", {}).keys())

    allowed_bbox = expand_bbox(city_bbox, margin_ratio=0.10)

    seen_ids: Set[str] = set()
    seen_wikidata_ids: Dict[str, str] = {}  # wikidata_id -> canonical_id
    accepted_places: List[Dict[str, Any]] = []
    quarantined_places: List[Dict[str, Any]] = []

    for p in places:
        cid = p.get("canonical_id")
        name = p.get("name", "")
        name_lower = name.lower()
        lat = p.get("latitude")
        lon = p.get("longitude")
        cat = p.get("category")
        subcat = p.get("subcategory")
        quality = p.get("quality", {})
        overall_quality = quality.get("overall", 0.0)
        anomaly_score = p.get("anomaly_score", 0.0)
        qid = p.get("wikidata_id")

        quarantine_reasons = []

        # Rule 1: ID uniqueness
        if not cid:
            quarantine_reasons.append("missing_canonical_id")
        elif cid in seen_ids:
            quarantine_reasons.append("duplicate_canonical_id")
        else:
            seen_ids.add(cid)

        # Rule 2: Non-empty name
        if not name or len(name.strip()) < 2:
            quarantine_reasons.append("invalid_or_empty_name")

        # Rule 3: Valid coordinates
        if lat is None or lon is None:
            quarantine_reasons.append("missing_coordinates")
        elif not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            quarantine_reasons.append("out_of_range_coordinates")
        elif not is_point_in_bbox(lat, lon, allowed_bbox):
            quarantine_reasons.append("coordinates_outside_city_boundary")

        # Rule 4: Valid category
        if not cat or cat not in valid_categories:
            quarantine_reasons.append(f"invalid_category:{cat}")

        # Rule 5: Semantic category conflicts
        # A. Lake with Palace or Station in name
        if cat == "nature" and subcat == "lake":
            if any(w in name_lower for w in ["palace", "hotel", "resort", "station", "junction", "metro"]):
                quarantine_reasons.append("semantic_conflict:lake_classified_with_palace_or_transit_keyword")

        # B. Heritage with lodging in name
        if cat == "heritage" and any(w in name_lower for w in ["oyo", "resort", "inn", "hotel", "guest house"]):
            quarantine_reasons.append("semantic_conflict:heritage_classified_with_lodging_keyword")

        # C. Transport node classified as heritage
        if cat == "heritage" and any(w in name_lower for w in ["metro station", "railway station", "airport", "bus stand"]):
            quarantine_reasons.append("semantic_conflict:transport_classified_as_heritage")

        # Rule 6: Duplicate Wikidata ID across distinct places
        if qid:
            if qid in seen_wikidata_ids:
                existing_cid = seen_wikidata_ids[qid]
                quarantine_reasons.append(f"duplicate_wikidata_assignment:{qid}_already_used_by_{existing_cid}")
            else:
                seen_wikidata_ids[qid] = cid

        # Rule 7: Quality threshold
        if overall_quality < threshold:
            quarantine_reasons.append(f"low_quality_score:{overall_quality}<{threshold}")

        # Rule 8: Severe anomaly threshold
        if anomaly_score >= 0.65:
            quarantine_reasons.append(f"high_anomaly_score:{anomaly_score}")

        # Rule 9: Image file existence check
        img_meta = p.get("image_metadata")
        if img_meta:
            primary_rel = img_meta.get("local_path")
            if primary_rel:
                full_path = media_dir / primary_rel.replace("images/", "")
                if not full_path.exists():
                    quarantine_reasons.append(f"missing_image_file_on_disk:{primary_rel}")

        if quarantine_reasons:
            quarantined_places.append({
                "place": p,
                "reasons": quarantine_reasons
            })
        else:
            accepted_places.append(p)

    # Rule 10: Near-duplicate core places check (< 30m with near-identical names)
    core_accepted = [p for p in accepted_places if p.get("tier") == "core_destination"]
    deduped_accepted = []
    quarantined_proximity_ids = set()

    for idx1, p1 in enumerate(core_accepted):
        if p1.get("canonical_id") in quarantined_proximity_ids:
            continue
        lat1, lon1 = p1.get("latitude"), p1.get("longitude")
        for idx2 in range(idx1 + 1, len(core_accepted)):
            p2 = core_accepted[idx2]
            lat2, lon2 = p2.get("latitude"), p2.get("longitude")
            if lat1 and lon1 and lat2 and lon2:
                dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
                if dist <= 25:
                    sim = fuzzy_name_similarity(p1.get("name", ""), p2.get("name", ""))
                    if sim >= 0.85:
                        # Near-duplicate core destination! Keep higher quality, quarantine other
                        q1 = p1.get("quality", {}).get("overall", 0.0)
                        q2 = p2.get("quality", {}).get("overall", 0.0)
                        inferior_p = p2 if q1 >= q2 else p1
                        quarantined_proximity_ids.add(inferior_p["canonical_id"])
                        quarantined_places.append({
                            "place": inferior_p,
                            "reasons": [f"near_duplicate_core_destination_{int(dist)}m_name_sim_{sim}"]
                        })

    final_accepted = [p for p in accepted_places if p.get("canonical_id") not in quarantined_proximity_ids]

    # Write quarantined records
    quarantine_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(quarantine_output_path, "w", encoding="utf-8") as f:
        for q in quarantined_places:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"[Stage 10/10] Semantic Validation & Quarantine complete:")
    print(f"       Accepted places: {len(final_accepted)}")
    print(f"       Quarantined places: {len(quarantined_places)} (saved to {quarantine_output_path.name})")

    return final_accepted, quarantined_places


def validate_release_package(release_path: Path) -> Dict[str, Any]:
    """
    Performs full structural and semantic validation on a versioned City Pack folder.
    Returns audit dictionary with pipeline_health, data_quality, source_coverage statuses.
    """
    required_files = [
        "city.json",
        "places.json",
        "places.jsonl",
        "places.parquet",
        "image_manifest.json",
        "source_manifest.json",
        "license_manifest.json",
        "checksums.json",
        "yatracanvas.db",
        "manifest.json",
    ]
    for fn in required_files:
        fp = release_path / fn
        if not fp.exists():
            raise FileNotFoundError(f"Missing required release file: {fn}")

    # Load manifest and places
    with open(release_path / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(release_path / "places.json", "r", encoding="utf-8") as f:
        places = json.load(f)

    # 1. SQLite Verification
    db_path = release_path / "yatracanvas.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM places;")
    row_count = cur.fetchone()[0]
    conn.close()

    if row_count != len(places):
        raise ValueError(f"SQLite row count ({row_count}) does not match places.json ({len(places)})")

    # 2. Semantic Checks across places
    core_places = [p for p in places if p.get("tier") == "core_destination"]
    core_count = len(core_places)

    core_with_wiki = sum(1 for p in core_places if p.get("external_ids", {}).get("wikidata_id"))
    core_with_img = sum(1 for p in core_places if p.get("images", {}).get("primary"))
    core_with_hours = sum(1 for p in core_places if p.get("opening_hours", {}).get("raw"))

    # Semantic errors counter
    semantic_errors = 0
    seen_qids = set()
    for p in places:
        c = p.get("classification", {}).get("category")
        sc = p.get("classification", {}).get("subcategory")
        nm = p.get("name", "").lower()
        qid = p.get("external_ids", {}).get("wikidata_id")

        if c == "nature" and sc == "lake" and any(w in nm for w in ["palace", "station", "junction"]):
            semantic_errors += 1
        if c == "heritage" and any(w in nm for w in ["hotel", "oyo", "resort"]):
            semantic_errors += 1
        if qid:
            if qid in seen_qids:
                semantic_errors += 1
            seen_qids.add(qid)

    # 3. Determine 3-dimension quality gates
    # A. Pipeline Health (PASS, WARN, FAIL)
    pipeline_health = "PASS"
    if row_count == 0:
        pipeline_health = "FAIL"

    # B. Data Quality (PASS, WARN, FAIL)
    data_quality = "PASS"
    if semantic_errors > 0:
        data_quality = "WARN" if semantic_errors <= 5 else "FAIL"

    # C. Source Coverage (PASS, WARN, FAIL)
    source_coverage = "PASS"
    if core_count >= 20:
        wiki_ratio = core_with_wiki / core_count
        img_ratio = core_with_img / core_count
        if wiki_ratio < 0.20 or img_ratio < 0.08:
            source_coverage = "FAIL"
        elif wiki_ratio < 0.50 or img_ratio < 0.25:
            source_coverage = "WARN"

    return {
        "total_places": row_count,
        "core_count": core_count,
        "core_with_wikidata": core_with_wiki,
        "core_with_image": core_with_img,
        "core_with_hours": core_with_hours,
        "semantic_errors": semantic_errors,
        "pipeline_health": pipeline_health,
        "data_quality": data_quality,
        "source_coverage": source_coverage,
    }
