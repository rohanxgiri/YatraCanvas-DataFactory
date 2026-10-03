from enum import Enum


class MediaPolicy(str, Enum):
    REAL_REQUIRED = "REAL_REQUIRED"
    REAL_PREFERRED = "REAL_PREFERRED"
    FALLBACK_ALLOWED = "FALLBACK_ALLOWED"
    NO_IMAGE_REQUIRED = "NO_IMAGE_REQUIRED"


def media_policy(place: dict) -> MediaPolicy:
    tier = place.get("tier", "discovery")
    if tier == "core_destination":
        return MediaPolicy.REAL_REQUIRED
    category = place.get("category") or place.get("classification", {}).get("category")
    if (tier == "recommended" and category in {"food", "cafe", "shopping", "arts_culture", "adventure"}
        and place.get("prominence_score", 0) >= 0.8):
        return MediaPolicy.REAL_REQUIRED
    if tier == "recommended" and category in {"heritage", "museum", "religious", "nature", "park", "viewpoint", "arts_culture"}:
        return MediaPolicy.REAL_PREFERRED
    return MediaPolicy.FALLBACK_ALLOWED
