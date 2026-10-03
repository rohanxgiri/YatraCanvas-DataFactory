"""Mature schedule validation. Preserve source syntax; never silently repair it."""
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from .config import LocalConfig


@lru_cache(maxsize=2048)
def _validate(text: str, backend: str):
    if not text or len(text) > 2048:
        return {"valid": False, "status": "INVALID", "backend": backend}
    if backend == "javascript":
        node = shutil.which("node")
        if not node:
            return {"valid": False, "status": "UNAVAILABLE", "backend": backend}
        try:
            run = subprocess.run([node, str(Path(__file__).with_name("hours.cjs"))],
                                 input=json.dumps({"schedule": text}), text=True,
                                 capture_output=True, timeout=5, check=True)
            return json.loads(run.stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            return {"valid": False, "status": "UNAVAILABLE", "backend": backend}
    if backend != "python":
        return {"valid": False, "status": "UNAVAILABLE", "backend": backend}
    try:
        from opening_hours import OpeningHours
        OpeningHours(text)
        return {"valid": True, "status": "VALID", "backend": "opening-hours-py", "schedule": text}
    except ImportError:
        return {"valid": False, "status": "UNAVAILABLE", "backend": backend}
    except Exception:
        return {"valid": False, "status": "INVALID", "backend": "opening-hours-py"}


def validate_hours(text, backend=None):
    if not isinstance(text, str):
        return {"valid": False, "status": "INVALID"}
    return dict(_validate(text, backend or LocalConfig().hours_validator_backend))
