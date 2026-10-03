"""Region-aware geographic decisions based on source evidence, never model coordinates."""
import math
from ..utils.geo import haversine_distance_meters, is_point_in_bbox


def coordinates(place):
    location = place.get("location", place)
    return location.get("latitude"), location.get("longitude")


def valid_coordinates(lat, lon):
    return (isinstance(lat, (int, float)) and not isinstance(lat, bool)
            and isinstance(lon, (int, float)) and not isinstance(lon, bool)
            and math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180)


def geography(place: dict, city: dict, max_distance_km=120) -> dict:
    lat, lon = coordinates(place)
    result = {"original_coordinates": [lat, lon], "city_bbox": city["bbox"],
              "region_bbox": city.get("region_bbox"), "evidence": []}
    if not valid_coordinates(lat, lon):
        return {**result, "status": "INVALID", "reason_codes": ["COORDINATES_INVALID"]}
    distance = haversine_distance_meters(lat, lon, *city["center"]) / 1000
    result["distance_from_center_km"] = round(distance, 3)
    boundary = city.get("boundary_geometry")
    inside = is_point_in_bbox(lat, lon, city["bbox"])
    if boundary:
        from ..local_intelligence.geometry import polygon_evidence
        result["municipal_geometry"] = polygon_evidence(lat, lon, boundary, city.get("boundary_buffer_m", 0))
        if result["municipal_geometry"]["status"] != "OK":
            return {**result, "status": "SUSPICIOUS", "reason_codes": ["MUNICIPAL_GEOMETRY_INVALID"]}
        inside = result["municipal_geometry"]["inside"]
    if inside:
        return {**result, "status": "VALID", "reason_codes": ["INSIDE_CITY_BOUNDARY"]}
    associations = place.get("region_associations", [])
    supported = [a for a in associations if a.get("source") in {"wikidata", "wikivoyage", "openstreetmap", "official_website"}
                 and a.get("source_id") and a.get("city_id") == city["id"]
                 and a.get("relationship") in {"administrative_region", "destination_listing", "travel_region"}]
    region_bbox = city.get("region_bbox")
    region_inside = not region_bbox or is_point_in_bbox(lat, lon, region_bbox)
    if city.get("region_geometry"):
        from ..local_intelligence.geometry import polygon_evidence
        result["regional_geometry"] = polygon_evidence(lat, lon, city["region_geometry"], city.get("region_buffer_m", 0))
        region_inside = result["regional_geometry"].get("within_buffer", False)
    if supported and distance <= max_distance_km and region_inside:
        return {**result, "evidence": supported, "status": "VALID", "reason_codes": ["SOURCE_ASSOCIATED_TRAVEL_REGION"]}
    if distance > max_distance_km:
        return {**result, "status": "INVALID", "reason_codes": ["DISTANT_WRONG_REGION"]}
    return {**result, "status": "SUSPICIOUS", "reason_codes": ["OUTLYING_REGION_ASSOCIATION_UNVERIFIED"]}


def coordinate_audit(place: dict, evidence: list[dict], agreement_m=100, minor_m=300, conflict_m=2000) -> dict:
    """Only identity-matched authoritative points participate in corroboration/repair."""
    original = coordinates(place)
    points = [p for p in evidence if p.get("source") in {"openstreetmap", "wikidata", "official_website"}
              and p.get("source_id") and p.get("identity_match") is True
              and valid_coordinates(p.get("latitude"), p.get("longitude"))]
    pairs = []
    for i, a in enumerate(points):
        for b in points[i+1:]:
            if a["source"] != b["source"]:
                pairs.append({"a": a, "b": b, "distance_m": round(haversine_distance_meters(a["latitude"], a["longitude"], b["latitude"], b["longitude"]), 1)})
    distances = [p["distance_m"] for p in pairs]
    original_comparisons = [{"source": p["source"], "source_id": p["source_id"],
        "distance_m": round(haversine_distance_meters(*original, p["latitude"], p["longitude"]), 1)}
        for p in points] if valid_coordinates(*original) else []
    if not distances:
        drift = max((p["distance_m"] for p in original_comparisons), default=0)
        status = "CONFLICT" if drift > conflict_m else "SUSPICIOUS" if drift > minor_m else "UNVERIFIED"
    elif max(distances) <= agreement_m:
        status = "CORROBORATED"
    elif max(distances) <= minor_m:
        status = "MINOR_VARIANCE"
    elif max(distances) <= conflict_m:
        status = "SUSPICIOUS"
    else:
        status = "CONFLICT"
    result = {"status": status, "original_coordinates": list(original), "source_coordinates": points,
              "distance_comparisons": pairs, "original_source_comparisons": original_comparisons,
              "action": "UNRESOLVED" if status == "UNVERIFIED" else "REVIEW"}
    # Two independent sources agree; ALL participating sources must be consistent.
    if status == "CORROBORATED":
        preferred = sorted(points, key=lambda p: p["source"] != "openstreetmap")[0]
        drift = haversine_distance_meters(*original, preferred["latitude"], preferred["longitude"]) if valid_coordinates(*original) else float("inf")
        result["action"] = "AUTO_APPLY" if drift > minor_m else "NO_CHANGE"
        if drift > minor_m:
            result["replacement"] = {"latitude": preferred["latitude"], "longitude": preferred["longitude"],
                "source": preferred["source"], "source_id": preferred["source_id"],
                "corroborated_by": sorted({p["source"] for p in points} - {preferred["source"]}), "confidence": 0.99}
    return result
