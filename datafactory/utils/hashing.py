import hashlib
from pathlib import Path
from typing import Optional
from .text import slugify

STATE_CODE_MAP = {
    "rajasthan": "rj",
    "maharashtra": "mh",
    "delhi": "dl",
    "uttar pradesh": "up",
    "karnataka": "ka",
    "tamil nadu": "tn",
    "kerala": "kl",
    "gujarat": "gj",
    "west bengal": "wb",
    "goa": "ga",
    "madhya pradesh": "mp",
    "punjab": "pb",
    "haryana": "hr",
    "himachal pradesh": "hp",
    "uttarakhand": "uk",
    "bihar": "br",
    "odisha": "od",
    "assam": "as",
    "telangana": "ts",
    "andhra pradesh": "ap",
}


def get_state_code(state_name: str) -> str:
    cleaned = state_name.strip().lower()
    return STATE_CODE_MAP.get(cleaned, slugify(cleaned)[:2])


def get_country_code(country_name: str) -> str:
    cleaned = country_name.strip().lower()
    if cleaned in ("india", "in"):
        return "in"
    return slugify(cleaned)[:2]


def generate_canonical_place_id(
    country: str,
    state: str,
    city: str,
    name: str,
    disambiguator: Optional[str] = None
) -> str:
    """
    Generate a deterministic, human-readable canonical place ID.
    Example: yc_in_rj_jaipur_hawa_mahal
    """
    c_code = get_country_code(country)
    s_code = get_state_code(state)
    city_slug = slugify(city)
    name_slug = slugify(name)

    base_id = f"yc_{c_code}_{s_code}_{city_slug}_{name_slug}"
    if disambiguator:
        d_slug = slugify(disambiguator)[:8]
        return f"{base_id}_{d_slug}"
    return base_id


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hex digest for a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()
