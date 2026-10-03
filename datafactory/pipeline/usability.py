from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image
from ..config.settings import get_settings
from .media_policy import media_policy, MediaPolicy
from .media_assurance import license_allowed, local_asset
from .geographic_assurance import geography, coordinates, valid_coordinates


def usability(places: list[dict], city: dict, root: Path, assurance: dict | None = None):
    assurance = assurance or {}
    cfg = get_settings().load_yaml("assurance.yaml")
    categories = get_settings().categories_config.get("canonical_categories", {})
    ids = Counter(p.get("id") for p in places)
    qids = Counter(p.get("external_ids", {}).get("wikidata_id") for p in places)
    rows, metrics = [], Counter()
    policy_metrics = defaultdict(Counter)
    for place in places:
        pid = place.get("id")
        assessment = assurance.get(pid, {})
        policy = media_policy(place).value
        blockers = []
        image = place.get("images", {}).get("primary")
        kind = (image or {}).get("image_type", "real") if image else "missing"
        identity_valid = bool(pid and ids[pid] == 1 and len(place.get("name", "").strip()) >= 2 and
            any(s.get("source_id") and s.get("source") not in {"groq", "gemini"} for s in place.get("sources", [])))
        qid = place.get("external_ids", {}).get("wikidata_id")
        if assessment.get("identity_blocker") or (qid and qids[qid] > 1):
            identity_valid = False
        if not identity_valid:
            blockers.append("IDENTITY_UNRESOLVED")
        coordinate_valid = valid_coordinates(*coordinates(place))
        coordinate_conflict = assessment.get("coordinate", {}).get("status") in {"CONFLICT", "SUSPICIOUS"}
        if not coordinate_valid or coordinate_conflict:
            blockers.append("COORDINATE_INVALID_OR_CONFLICT")
        classification = place.get("classification", {})
        classification_valid = classification.get("category") in categories
        if not classification_valid:
            blockers.append("CLASSIFICATION_INVALID")
        region = assessment.get("geography") or geography(place, city, cfg.get("region_max_distance_km", 120))
        if region["status"] != "VALID":
            blockers.append("TRAVEL_REGION_" + region["status"])
        renderable = False
        if image:
            path = local_asset(root, image.get("local_path"))
            thumbnail = local_asset(root, image.get("thumbnail_path"))
            if path and thumbnail:
                try:
                    with Image.open(path) as im:
                        im.verify()
                    with Image.open(thumbnail) as im:
                        im.verify()
                    renderable = True
                except Exception:
                    pass
            if not license_allowed(image.get("license", "")) or not image.get("attribution") or not image.get("author") or not image.get("source_page") or not image.get("license_url"):
                blockers.append("MEDIA_PROVENANCE_INCOMPLETE")
        if not renderable and policy != MediaPolicy.NO_IMAGE_REQUIRED:
            blockers.append("MEDIA_NOT_RENDERABLE")
        if policy == MediaPolicy.REAL_REQUIRED:
            if kind != "real" or assessment.get("media", {}).get("verified") is not True:
                blockers.append("CORE_MEDIA_UNRESOLVED")
        if place.get("anomaly_score", 0) >= 0.65:
            blockers.append("CRITICAL_INTEGRITY_ANOMALY")
        metrics.update({"identity_valid": identity_valid, "coordinates_valid": coordinate_valid and not coordinate_conflict,
                        "classification_valid": classification_valid, "region_valid": region["status"] == "VALID",
                        "renderable": renderable, "usable": not blockers,
                        "descriptions": bool(place.get("description")), "opening_hours": bool(place.get("opening_hours", {}).get("raw")),
                        "addresses": bool(place.get("location", {}).get("address"))})
        policy_metrics[policy].update({"total": 1, kind: 1, "verified_real": kind == "real" and renderable and "MEDIA_PROVENANCE_INCOMPLETE" not in blockers and assessment.get("media", {}).get("verified") is True,
                                       "required_unresolved": "CORE_MEDIA_UNRESOLVED" in blockers})
        rows.append({"place_id": pid, "name": place["name"], "media_policy": policy, "image_type": kind,
                     "usable": not blockers, "critical_blockers": sorted(set(blockers)), "geography": region})
    count = len(places)
    pct = round(metrics["usable"] / count * 100, 2) if count else 0
    critical = Counter(code for row in rows for code in row["critical_blockers"])
    required = policy_metrics[MediaPolicy.REAL_REQUIRED.value]
    required_count = required["total"]
    required_coverage = round(required["verified_real"] / required_count * 100, 2) if required_count else 100.0
    source_ready = bool(count and not critical and pct >= cfg.get("target_usability", .95)*100 and required_coverage == 100)
    return {"city": {k: city[k] for k in ("id", "name", "state", "country")}, "published": count,
            **dict(metrics), "media_policies": {k: dict(v) for k, v in policy_metrics.items()},
            "critical_blockers": dict(critical), "critical_blocker_pois": sum(bool(r["critical_blockers"]) for r in rows),
            "overall_usable_count": metrics["usable"], "overall_usable_percentage": pct,
            "GENERAL_USABILITY": pct, "REAL_REQUIRED_MEDIA_COVERAGE": required_coverage,
            "real_required_total": required_count, "real_required_verified": required["verified_real"],
            "target_percentage": cfg.get("target_usability", .95)*100,
            "DRAFT_OFFLINE_READY": bool(count and all(valid_coordinates(*coordinates(p)) for p in places) and all(ids[p["id"]] == 1 for p in places)),
            "CERTIFICATION_READY_SOURCE_DATA": source_ready, "SOURCE_DATA_READY": source_ready,
            "pack_status": "SOURCE_DATA_READY" if source_ready else "DRAFT_OFFLINE_PACK", "places": rows}
