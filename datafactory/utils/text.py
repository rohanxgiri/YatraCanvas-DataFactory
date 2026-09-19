import re
import unicodedata
from rapidfuzz import fuzz


def clean_string(text: str) -> str:
    """Normalize unicode and strip excessive whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def slugify(text: str) -> str:
    """Convert a string to a clean URL/ID friendly slug."""
    text = clean_string(text).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def normalize_name(name: str) -> str:
    """Standardize place name for comparison (lowercased, punctuation removed)."""
    clean = clean_string(name).lower()
    # Remove common suffixes/prefixes if needed, but keep core tokens
    clean = re.sub(r"[^\w\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def fuzzy_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two names using token_sort_ratio and token_set_ratio from RapidFuzz.
    Returns a score between 0.0 and 1.0.
    """
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0

    sort_score = fuzz.token_sort_ratio(n1, n2) / 100.0
    set_score = fuzz.token_set_ratio(n1, n2) / 100.0

    # If one string is fully contained in the other as a phrase, give higher weight
    if n1 in n2 or n2 in n1:
        return max(sort_score, set_score)

    return max(sort_score, set_score * 0.9)
