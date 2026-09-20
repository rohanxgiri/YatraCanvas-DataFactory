from datafactory.utils.geo import haversine_distance_meters, is_point_in_bbox, expand_bbox


def test_haversine_distance():
    # Distance between Hawa Mahal (26.9239, 75.8267) and City Palace Jaipur (26.9258, 75.8237)
    # is roughly 360-400 meters
    dist = haversine_distance_meters(26.9239, 75.8267, 26.9258, 75.8237)
    assert 300 <= dist <= 500


def test_bbox_containment():
    bbox = (75.7, 26.8, 75.9, 27.0)  # min_lon, min_lat, max_lon, max_lat
    assert is_point_in_bbox(26.9, 75.8, bbox) is True
    assert is_point_in_bbox(28.0, 75.8, bbox) is False


def test_expand_bbox():
    bbox = (75.0, 26.0, 76.0, 27.0)
    expanded = expand_bbox(bbox, margin_ratio=0.1)
    assert expanded[0] < 75.0
    assert expanded[1] < 26.0
    assert expanded[2] > 76.0
    assert expanded[3] > 27.0
