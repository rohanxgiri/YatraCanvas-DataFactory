"""Licensed, labelled contextual artwork, assigned by stable full canonical ID."""
import hashlib
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from ..utils.atomic import atomic_json
from .media_policy import media_policy, MediaPolicy


FACTORY_ARTWORK_SOURCE = "YatraCanvas contextual artwork"


def fallback_strategy(config):
    strategy = config.get("fallbacks", {}).get("strategy", "app")
    if strategy not in {"app", "bundled"}:
        raise ValueError("Fallback strategy must be app or bundled")
    return strategy


def retire_factory_fallbacks(places):
    """Clear only factory artwork; preserve photos and verified human choices."""
    removed = []
    for place in places:
        images = place.get("images", {})
        def retired(image, slot):
            if (image and image.get("image_type") == "fallback"
                    and image.get("source") == FACTORY_ARTWORK_SOURCE
                    and image.get("match_method") != "verified_human_curation"):
                removed.append({"place_id":place["id"], "slot":slot,
                                "paths":[p for p in (image.get("local_path"),image.get("thumbnail_path")) if p]})
                return True
            return False
        if retired(images.get("primary"), "primary"):
            images["primary"] = None
        images["gallery"] = [image for image in images.get("gallery", []) if not retired(image, "gallery")]
    return removed


def fallback_category(place):
    classification = place.get("classification", place)
    category, subcategory = classification.get("category", ""), classification.get("subcategory", "") or ""
    for token in ("temple", "mosque", "church", "monastery", "ghat", "fort", "palace", "museum", "lake", "beach", "waterfall", "mountain", "viewpoint", "wildlife", "garden", "market", "sweets"):
        if token in subcategory:
            return token
    return {"religious": "temple", "food": "restaurant", "cafe": "cafe", "shopping": "shopping", "park": "park",
            "nature": "nature", "heritage": "heritage", "arts_culture": "culture", "experience": "experience",
            "viewpoint": "viewpoint", "hotel": "hotel", "transport": "transport", "museum": "museum"}.get(category, "experience")


class FallbackPools:
    def __init__(self, asset_dir: Path):
        self.asset_dir = asset_dir
        manifest = asset_dir / "manifest.json"
        import json
        self.assets = json.loads(manifest.read_text(encoding="utf-8")).get("assets", []) if manifest.exists() else []
        self.pools = defaultdict(list)
        for asset in self.assets:
            path = (asset_dir / asset["path"]).resolve()
            if (path.is_relative_to(asset_dir.resolve()) and path.exists() and asset.get("license") == "CC0"
                and asset.get("creator") and asset.get("attribution") and asset.get("image_type") == "fallback"):
                try:
                    with Image.open(path) as image:
                        image.verify()
                    if hashlib.sha256(path.read_bytes()).hexdigest() != asset.get("sha256"):
                        continue
                except Exception:
                    continue
                self.pools[asset["category"]].append(asset)
        for pool in self.pools.values():
            pool.sort(key=lambda a: a["id"])

    def choose(self, place):
        if media_policy(place) == MediaPolicy.REAL_REQUIRED:
            return None
        pool = self.pools.get(fallback_category(place), [])
        if not pool:
            return None
        canonical_id = place.get("id") or place["canonical_id"]
        return pool[int(hashlib.sha256(canonical_id.encode()).hexdigest(), 16) % len(pool)]

    def apply(self, place, output_root: Path):
        asset = self.choose(place)
        if not asset:
            return None
        pid = place.get("id") or place["canonical_id"]
        dest = output_root / "images" / pid
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.asset_dir / asset["path"], dest / "primary.webp")
        with Image.open(dest / "primary.webp") as image:
            w, h = image.size
            image.thumbnail((400, 400))
            image.save(dest / "thumbnail.webp", "WEBP", quality=85)
        return {"source": "YatraCanvas contextual artwork", "source_page": asset["source_url"],
                "original_file": asset["path"], "author": asset["creator"], "license": asset["license"],
                "license_url": asset["license_url"], "attribution": asset["attribution"], "width": w, "height": h,
                "match_method": "category_fallback", "match_confidence": 0.0,
                "downloaded_at": datetime.now(timezone.utc).isoformat(), "local_path": f"images/{pid}/primary.webp",
                "thumbnail_path": f"images/{pid}/thumbnail.webp", "image_type": "fallback",
                "fallback_category": asset["category"], "fallback_asset_id": asset["id"], "content_sha256": asset["sha256"]}

    def authoring_manifest(self, places, output: Path, desired=8):
        counts = Counter(fallback_category(p) for p in places if media_policy(p) != MediaPolicy.REAL_REQUIRED)
        result = {"optional": True, "external_generation_required": False,
                  "categories": [{"category": c, "published_pois": count, "assets_available": len(self.pools[c]),
                    "additional_artwork_requested": max(0, desired-len(self.pools[c])),
                    "brief": f"Generic {c} contextual travel illustration. No named place, real venue claims, logos or text. Clearly fallback art."} for c, count in sorted(counts.items())]}
        atomic_json(output, result)
        return result


def fallback_distribution(places):
    counts = defaultdict(Counter)
    for place in places:
        image = place.get("images", {}).get("primary") or {}
        if image.get("image_type") == "fallback":
            counts[image.get("fallback_category", fallback_category(place))][image.get("fallback_asset_id", image.get("local_path"))] += 1
    return {category: {"published_using_fallback": sum(pool.values()), "distinct_assets": len(pool),
                       "maximum_sharing": max(pool.values(), default=0), "assignments": dict(pool)} for category, pool in sorted(counts.items())}
