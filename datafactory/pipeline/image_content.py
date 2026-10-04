"""Bounded primary-frame decoding; only confirmed MPO receives normalization."""
import hashlib
import io
from PIL import Image, ImageOps


MAX_MEDIA_BYTES = 20_000_000
MAX_MEDIA_PIXELS = 40_000_000


class ImageContentError(ValueError):
    pass


def normalize_primary_frame(content, *, max_bytes=MAX_MEDIA_BYTES, max_pixels=MAX_MEDIA_PIXELS, long_edge=1920):
    if len(content) > max_bytes:
        raise ImageContentError("IMAGE_BYTES_EXCEEDED")
    try:
        with Image.open(io.BytesIO(content)) as original:
            if original.width * original.height > max_pixels:
                raise ImageContentError("IMAGE_DECODE_BUDGET_EXCEEDED")
            if original.format != "MPO":
                return content, []
            if not 1 <= original.n_frames <= 16:
                raise ImageContentError("MPO_FRAME_COUNT_INVALID")
            original.seek(0)
            if original.width * original.height > max_pixels:
                raise ImageContentError("IMAGE_DECODE_BUDGET_EXCEEDED")
            original.load()
            if original.width < 350 or original.height < 250:
                raise ImageContentError("ACTUAL_IMAGE_TOO_SMALL")
            if not .35 <= original.width / original.height <= 3:
                raise ImageContentError("ACTUAL_ASPECT_RATIO")
            with ImageOps.exif_transpose(original).convert("RGB") as image:
                image.thumbnail((long_edge, long_edge))
                stream = io.BytesIO()
                image.save(stream, "WEBP", quality=90)
            normalized = stream.getvalue()
            if len(normalized) > max_bytes:
                raise ImageContentError("IMAGE_BYTES_EXCEEDED")
            # A successful encoder is still checked by the normal format decoder.
            with Image.open(io.BytesIO(normalized)) as decoded:
                decoded.load()
                if decoded.format != "WEBP" or decoded.width * decoded.height > max_pixels:
                    raise ImageContentError("MPO_NORMALIZATION_FAILED")
            return normalized, ["MPO_PRIMARY_FRAME_NORMALIZED"]
    except ImageContentError:
        raise
    except Exception:
        raise ImageContentError("IMAGE_DECODE_FAILED") from None


def content_identity(content):
    return hashlib.sha256(content).hexdigest()
