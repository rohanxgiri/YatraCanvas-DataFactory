"""Local diagnostics, with downloads strictly opt-in and no cloud router."""
import io
import time
from PIL import Image, ImageDraw
from .config import LocalConfig
from .media import SigLIPBackend
from .duplicates import DuplicateIndex
from .text import LocalTextSimilarity
from .geometry import polygon_evidence
from .hours import validate_hours


def local_ai_status(config=None):
    config = config or LocalConfig()
    report = {"siglip_configured": config.local_media_enabled, "model": config.local_media_model,
              "device": config.local_media_device, "model_cached_locally": False, "model_load": "FAIL", "inference_test": "FAIL"}
    if config.local_media_enabled:
        try:
            backend = SigLIPBackend(config.model_copy(update={"local_media_allow_download": False}))
            report["model_cached_locally"] = True
        except Exception as exc:
            report["error"] = f"{type(exc).__name__}: {exc}"
            backend = None
        if backend is None and config.local_media_allow_download:
            try:
                backend = SigLIPBackend(config)
                report.update(model_cached_locally=True, downloaded_or_reused=True)
                report.pop("error", None)
            except Exception as exc:
                report["error"] = f"{type(exc).__name__}: {exc}"
        if backend is not None:
            report.update(model_load="PASS", load_seconds=backend.load_seconds, cache_dir=str(backend.cache_dir))
            try:
                image = Image.new("RGB", (224, 224), "green")
                started = time.perf_counter()
                scores = backend.score([image], ["a photo of a garden", "a photo of a car"])
                report.update(inference_test="PASS" if len(scores[0]) == 2 and all(0 <= v <= 1 for v in scores[0]) else "FAIL",
                              inference_seconds=time.perf_counter()-started, scores=scores)
                image.close()
            except Exception as exc:
                report["inference_error"] = f"{type(exc).__name__}: {exc}"
    image = Image.new("RGB", (400, 300), "green")
    ImageDraw.Draw(image).rectangle((40, 40, 140, 240), fill="blue")
    stream = io.BytesIO(); image.save(stream, "PNG"); image.close()
    pool = DuplicateIndex(); first = pool.check(stream.getvalue()); second = pool.check(stream.getvalue())
    report["duplicate_detector"] = "PASS" if not first["duplicate"] and second["duplicate"] else "FAIL"
    text = LocalTextSimilarity(config).compare("Govind Dev Ji Temple", "Govind Devji Temple")
    report.update(text_similarity="PASS" if text["fuzzy"] > .8 else "FAIL", text_details=text)
    shape = {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}
    report["geometry_engine"] = "PASS" if polygon_evidence(.5, .5, shape).get("inside") else "FAIL"
    report["hours_validator"] = "PASS" if validate_hours("Mo-Fr 09:00-17:00")["valid"] and not validate_hours("Mo 99:00-17:00")["valid"] else "FAIL"
    report["cloud_calls"] = 0
    return report
