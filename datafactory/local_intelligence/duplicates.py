"""SHA first, conservative established perceptual hashes for byte variants."""
import hashlib
import io
from PIL import Image, ImageOps, ImageStat


def fingerprints(content: bytes):
    result = {"sha256": hashlib.sha256(content).hexdigest()}
    try:
        import imagehash
        with Image.open(io.BytesIO(content)) as original:
            if original.width * original.height > 40_000_000:
                return result
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((512, 512))
            result.update(phash=str(imagehash.phash(image)), dhash=str(imagehash.dhash(image)),
                          colorhash=str(imagehash.colorhash(image)), aspect=original.width / original.height,
                          informative=max(ImageStat.Stat(image).stddev) >= 8)
    except (ImportError, OSError, ValueError):
        pass
    return result


class DuplicateIndex:
    """Scoped to a candidate pool, never deduplicates unrelated POIs by appearance."""
    def __init__(self, threshold=3):
        self.threshold, self.entries = threshold, []

    def check(self, content: bytes, *, add=True):
        sha = hashlib.sha256(content).hexdigest()
        for previous in self.entries:
            if sha == previous["sha256"]:
                return {"sha256": sha, "duplicate": True, "method": "SHA256"}
        current = fingerprints(content)
        for previous in self.entries:
            if not current.get("informative") or not previous.get("informative"):
                continue
            # Two independent spatial hashes and color agreement avoid treating
            # visually similar buildings or flat images as interchangeable.
            def distance(key):
                return (int(current[key], 16) ^ int(previous[key], 16)).bit_count()
            if (abs(current["aspect"] / previous["aspect"] - 1) <= .08
                    and distance("phash") <= self.threshold
                    and distance("dhash") <= self.threshold + 1
                    and distance("colorhash") <= 1):
                return {**current, "duplicate": True, "method": "PERCEPTUAL"}
        if add:
            self.entries.append(current)
        return {**current, "duplicate": False, "method": None}
