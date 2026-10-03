from ..utils.text import fuzzy_name_similarity, normalize_name
from .geographic_assurance import coordinates, valid_coordinates
from ..utils.geo import haversine_distance_meters


def compact_identity(place: dict):
    return {"id": place.get("id") or place.get("canonical_id"), "name": place.get("name"),
            "aliases": place.get("alternate_names", [])[:8], "coordinates": list(coordinates(place)),
            "city": place.get("city"), "category": place.get("category") or place.get("classification", {}).get("category"),
            "external_ids": place.get("external_ids", {}), "sources": place.get("sources", place.get("sources_provenance", []))}


def identity_decision(a: dict, b: dict, router=None, text_similarity=None):
    ac, bc = a.get("city", {}), b.get("city", {})
    if ac and bc and any(ac.get(k) and bc.get(k) and ac[k] != bc[k] for k in ("id", "name", "state", "country")):
        return {"decision": "SAFE_DIFFERENT_PLACE", "confidence": 1.0, "reason_codes": ["DIFFERENT_CITY_CONTEXT"], "action": "NO_MERGE"}
    aq = a.get("wikidata_id") or a.get("external_ids", {}).get("wikidata_id")
    bq = b.get("wikidata_id") or b.get("external_ids", {}).get("wikidata_id")
    ap, bp = coordinates(a), coordinates(b)
    distance = haversine_distance_meters(*ap, *bp) if valid_coordinates(*ap) and valid_coordinates(*bp) else None
    an = [a.get("name", "")] + a.get("alternate_names", [])
    bn = [b.get("name", "")] + b.get("alternate_names", [])
    similarity = max(fuzzy_name_similarity(x, y) for x in an for y in bn)
    category_a = a.get("category") or a.get("classification", {}).get("category")
    category_b = b.get("category") or b.get("classification", {}).get("category")
    evidence = {"distance_m": distance, "name_similarity": similarity, "qids": [aq, bq], "categories": [category_a, category_b]}
    source_ids = {key: value for key, value in a.get("external_ids", {}).items()
                  if value and key != "wikidata_id" and b.get("external_ids", {}).get(key) == value}
    evidence["matching_source_ids"] = source_ids
    if aq and bq and aq != bq:
        return {**evidence, "decision": "SAFE_DIFFERENT_PLACE", "confidence": 0.99, "reason_codes": ["DIFFERENT_AUTHORITATIVE_QIDS"], "action": "NO_MERGE"}
    if aq and aq == bq and distance is not None and distance <= 100 and similarity >= 0.85 and category_a == category_b:
        return {**evidence, "decision": "SAFE_SAME_PLACE", "confidence": 0.99, "reason_codes": ["QID_NAME_COORDINATE_CATEGORY_AGREE"], "action": "AUTO_APPLY"}
    if source_ids and distance is not None and distance <= 100 and similarity >= .85 and category_a == category_b:
        return {**evidence, "decision": "SAFE_SAME_PLACE", "confidence": .98,
                "reason_codes": ["SOURCE_ID_NAME_COORDINATE_CATEGORY_AGREE"], "action": "AUTO_APPLY"}
    if text_similarity is not None and similarity < .85:
        evidence["local_text"] = text_similarity.compare(a.get("name", ""), b.get("name", ""))
    result = {**evidence, "decision": "UNRESOLVED", "confidence": 0.0, "reason_codes": ["INSUFFICIENT_IDENTITY_CORROBORATION"], "action": "REVIEW"}
    if router:
        result["ai"] = router.analyze({"pair": [compact_identity(a), compact_identity(b)]}, "identity_audit", evidence, important=True)
        # Model opinions are review suggestions; missing corroboration cannot be waived.
    return result


def conflict_groups(places: list[dict]):
    by_name, by_qid, by_id = {}, {}, {}
    for p in places:
        by_name.setdefault(normalize_name(p.get("name", "")), []).append(p)
        by_id.setdefault(p["id"], []).append(p)
        qid = p.get("external_ids", {}).get("wikidata_id")
        if qid:
            by_qid.setdefault(qid, []).append(p)
    seen, groups = set(), []
    for kind, mapping in [("canonical_id", by_id), ("name", by_name), ("qid", by_qid)]:
        for key, group in mapping.items():
            if len(group) < 2:
                continue
            signature = tuple(sorted((p["id"], *coordinates(p)) for p in group))
            if signature not in seen:
                seen.add(signature)
                groups.append({"kind": kind, "key": key, "places": group})
    return groups
