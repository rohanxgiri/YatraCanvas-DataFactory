import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..utils.text import normalize_name


def audit_high_value_missing(
    city_name: str,
    state_name: str,
    country_name: str = "India",
    version: str = "v3",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Investigates every missing high-value source candidate from Wikivoyage see/do
    and Wikidata travel attractions, classifying the exact outcome:
      - merged_into_existing
      - duplicate
      - outside_city_boundary
      - invalid_identity
      - low_confidence
      - quarantined
      - category_filtered
      - missing_name
      - coordinate_problem
      - pipeline_bug
      - other
    Generates reports/<city>/coverage/high_value_missing.json.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    city_slug = city_name.lower().replace(" ", "_")
    state_slug = state_name.lower().replace(" ", "_")
    country_slug = country_name.lower().replace(" ", "_")

    release_dir = project_root / "releases" / country_slug / state_slug / city_slug / version
    staging_dir = project_root / "data" / "staging" / country_slug / state_slug / city_slug
    source_cache_dir = project_root / "data" / "source_cache"

    # 1. Load Released Places
    released_places = []
    places_file = release_dir / "places.json"
    if places_file.exists():
        with open(places_file, "r", encoding="utf-8") as f:
            released_places = json.load(f)

    # Pre-index released places
    released_qids = set()
    released_wv_ids = set()
    released_names = {}
    for p in released_places:
        ext = p.get("external_ids") or {}
        if ext.get("wikidata_id"):
            released_qids.add(ext.get("wikidata_id"))
        if ext.get("wikivoyage_listing_id"):
            released_wv_ids.add(ext.get("wikivoyage_listing_id"))
        p_name_norm = normalize_name(p.get("name", "")).lower()
        if p_name_norm:
            released_names[p_name_norm] = p.get("id")

    # 2. Load Quarantined Records
    quarantined = []
    q_file = staging_dir / "quarantine" / "quarantined_places.jsonl"
    if q_file.exists():
        with open(q_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        quarantined.append(json.loads(line))
                    except Exception:
                        pass

    # 3. Load Rejected Records
    rejected = []
    r_file = staging_dir / "rejected_places.jsonl"
    if r_file.exists():
        with open(r_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rejected.append(json.loads(line))
                    except Exception:
                        pass

    # 4. Load Duplicates
    duplicates = []
    d_file = staging_dir / "duplicates.jsonl"
    if d_file.exists():
        with open(d_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        duplicates.append(json.loads(line))
                    except Exception:
                        pass

    # 5. Load Wikivoyage see/do
    wv_file = source_cache_dir / "wikivoyage" / f"{city_slug}_listings.json"
    wv_see_do = []
    if wv_file.exists():
        with open(wv_file, "r", encoding="utf-8") as f:
            wv_all = json.load(f)
            wv_see_do = [item for item in wv_all if item.get("listing_type") in ("see", "do")]

    # 6. Load Wikidata attractions
    wd_file = source_cache_dir / "wikidata" / f"{city_slug}_attractions.json"
    wd_attractions = []
    if wd_file.exists():
        with open(wd_file, "r", encoding="utf-8") as f:
            wd_attractions = json.load(f)

    # Evaluate Wikivoyage
    missing_wv = []
    for item in wv_see_do:
        sid = item.get("source_id")
        qid = item.get("wikidata_id")
        name = item.get("name", "")
        name_norm = normalize_name(name).lower()
        lat = item.get("latitude")
        lon = item.get("longitude")

        # Check if survived
        if sid in released_wv_ids or (qid and qid in released_qids) or name_norm in released_names:
            continue

        # Classify outcome
        outcome = "other"
        details = ""

        # Check coordinates
        if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
            outcome = "coordinate_problem"
            details = "Wikivoyage listing lacks latitude/longitude coordinates (sub-listing or un-geolocated activity)"
        else:
            # Check quarantine
            q_match = [q for q in quarantined if q.get("place", {}).get("canonical_id") == sid or q.get("place", {}).get("name") == name]
            if q_match:
                reasons = q_match[0].get("reasons", [])
                if "missing_coordinates" in reasons:
                    outcome = "coordinate_problem"
                    details = "Quarantined due to missing coordinates"
                elif any("boundary" in r for r in reasons):
                    outcome = "outside_city_boundary"
                    details = "Quarantined outside resolved city bounding envelope"
                elif any("conflict" in r for r in reasons):
                    outcome = "quarantined"
                    details = f"Quarantined due to semantic conflicts: {reasons}"
                else:
                    outcome = "quarantined"
                    details = f"Quarantined: {reasons}"
            else:
                # Check duplicates
                d_match = [d for d in duplicates if d.get("duplicate_id") == sid or d.get("canonical_id") == sid]
                if d_match:
                    outcome = "duplicate"
                    details = f"Merged into canonical place {d_match[0].get('canonical_id')}"
                else:
                    # Check rejected
                    r_match = [r for r in rejected if r.get("source_id") == sid or r.get("name") == name]
                    if r_match:
                        outcome = "category_filtered"
                        details = f"Rejected: {r_match[0].get('rejection_reason')}"

        missing_wv.append({
            "name": name,
            "source": "wikivoyage",
            "source_id": sid,
            "wikidata_id": qid,
            "coordinates": [lat, lon],
            "outcome": outcome,
            "details": details,
        })

    # Evaluate Wikidata
    missing_wd = []
    for item in wd_attractions:
        qid = item.get("wikidata_id")
        name = item.get("name", "")
        name_norm = normalize_name(name).lower()
        lat = item.get("latitude")
        lon = item.get("longitude")
        desc = item.get("description") or ""

        if qid in released_qids or name_norm in released_names:
            continue

        outcome = "other"
        details = ""

        # Check coordinates
        if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
            outcome = "coordinate_problem"
            details = "Wikidata entity lacks valid coordinates"
        else:
            # Check quarantine
            q_match = [q for q in quarantined if q.get("place", {}).get("wikidata_id") == qid or q.get("place", {}).get("name") == name]
            if q_match:
                reasons = q_match[0].get("reasons", [])
                if any("lodging" in r or "lake" in r or "conflict" in r for r in reasons):
                    outcome = "pipeline_bug" if "semantic_conflict" in str(reasons) else "quarantined"
                    details = f"Quarantined: {reasons} (Entity desc: '{desc}')"
                elif any("boundary" in r for r in reasons):
                    outcome = "outside_city_boundary"
                    details = "Quarantined outside resolved city bounding envelope"
                else:
                    outcome = "quarantined"
                    details = f"Quarantined: {reasons}"
            else:
                d_match = [d for d in duplicates if d.get("duplicate_id") == qid or d.get("canonical_id") == qid]
                if d_match:
                    outcome = "merged_into_existing"
                    details = f"Merged into canonical place {d_match[0].get('canonical_id')}"
                else:
                    r_match = [r for r in rejected if r.get("wikidata_id") == qid or r.get("name") == name]
                    if r_match:
                        outcome = "category_filtered"
                        details = f"Rejected: {r_match[0].get('rejection_reason')}"

        missing_wd.append({
            "name": name,
            "source": "wikidata",
            "source_id": qid,
            "wikidata_id": qid,
            "description": desc,
            "coordinates": [lat, lon],
            "outcome": outcome,
            "details": details,
        })

    # Summary by outcome
    summary_by_outcome = {}
    for item in missing_wv + missing_wd:
        out = item["outcome"]
        summary_by_outcome[out] = summary_by_outcome.get(out, 0) + 1

    report = {
        "city": city_name,
        "state": state_name,
        "country": country_name,
        "version": version,
        "summary": {
            "wikivoyage_total_see_do": len(wv_see_do),
            "wikivoyage_missing_count": len(missing_wv),
            "wikidata_total_attractions": len(wd_attractions),
            "wikidata_missing_count": len(missing_wd),
            "by_outcome": summary_by_outcome,
        },
        "missing_wikivoyage_listings": missing_wv,
        "missing_wikidata_attractions": missing_wd,
    }

    # Save to reports/<city>/coverage/high_value_missing.json
    out_dir = project_root / "reports" / city_slug / "coverage"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "high_value_missing.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report
