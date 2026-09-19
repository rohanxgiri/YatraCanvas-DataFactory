import math
from typing import Tuple, List


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def is_point_in_bbox(lat: float, lon: float, bbox: Tuple[float, float, float, float]) -> bool:
    """
    Check if a point (lat, lon) is within a bounding box.
    Bbox format: (min_lon, min_lat, max_lon, max_lat).
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def expand_bbox(bbox: Tuple[float, float, float, float], margin_ratio: float = 0.05) -> Tuple[float, float, float, float]:
    """Expand a bounding box (min_lon, min_lat, max_lon, max_lat) by a given margin ratio."""
    min_lon, min_lat, max_lon, max_lat = bbox
    d_lon = (max_lon - min_lon) * margin_ratio
    d_lat = (max_lat - min_lat) * margin_ratio
    return (
        round(min_lon - d_lon, 6),
        round(min_lat - d_lat, 6),
        round(max_lon + d_lon, 6),
        round(max_lat + d_lat, 6),
    )
