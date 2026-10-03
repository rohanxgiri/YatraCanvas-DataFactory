"""Shapely geometry in lon/lat with geodesic point-to-nearest-point distances."""
from shapely.geometry import Point, shape
from shapely.ops import nearest_points
from ..utils.geo import haversine_distance_meters


def polygon_evidence(lat, lon, geometry, buffer_m=0):
    try:
        polygon = shape(geometry)
        if polygon.is_empty or not polygon.is_valid or polygon.geom_type not in {"Polygon", "MultiPolygon"}:
            return {"status": "INVALID_GEOMETRY"}
        point = Point(lon, lat)
        inside = polygon.covers(point)
        nearest = nearest_points(point, polygon)[1]
        distance = 0 if inside else haversine_distance_meters(lat, lon, nearest.y, nearest.x)
        return {"status": "OK", "inside": inside, "distance_to_polygon_m": round(distance, 1),
                "within_buffer": distance <= buffer_m}
    except (ValueError, TypeError, KeyError):
        return {"status": "INVALID_GEOMETRY"}
