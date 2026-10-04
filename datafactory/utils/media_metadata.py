"""Finite legal metadata equivalence and Commons file identity, never fuzzy trust."""
import re
import unicodedata
from urllib.parse import unquote, urlsplit


VERSIONS = ("1.0", "2.0", "2.5", "3.0", "4.0")
LICENSES = {"CC0": "CC0 1.0", "CC0 1.0": "CC0 1.0",
            "CREATIVE COMMONS CC0 1.0": "CC0 1.0", "PUBLIC DOMAIN": "Public Domain",
            "PUBLIC DOMAIN MARK": "Public Domain Mark 1.0",
            "PUBLIC DOMAIN MARK 1.0": "Public Domain Mark 1.0",
            "CC BY": "CC BY", "CC BY SA": "CC BY-SA"}
for _version in VERSIONS:
    LICENSES[f"CC BY {_version}"] = f"CC BY {_version}"
    LICENSES[f"CC BY SA {_version}"] = f"CC BY-SA {_version}"


def creator_key(value):
    return unicodedata.normalize("NFC", value).strip() if isinstance(value, str) else None


def canonical_license_url(value):
    """Only enumerated CC host/path families may upgrade HTTP to HTTPS."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or parsed.hostname not in
                {"creativecommons.org", "www.creativecommons.org"} or parsed.username
                or parsed.password or parsed.port not in {None, 80 if parsed.scheme == "http" else 443}
                or parsed.query or parsed.fragment):
            return None
        path = parsed.path.rstrip("/")
        # These are alternative documents for the very same enumerated license.
        for suffix in ("/deed.en", "/deed", "/legalcode.en", "/legalcode"):
            if path.endswith(suffix):
                path = path[:-len(suffix)]
                break
        allowed = {f"/licenses/{family}/{version}" for family in ("by", "by-sa") for version in VERSIONS}
        allowed |= {"/publicdomain/zero/1.0", "/publicdomain/mark/1.0"}
        return "https://creativecommons.org" + path + "/" if path in allowed else None
    except ValueError:
        return None


def canonical_license(value, url=None):
    if not isinstance(value, str):
        return None
    key = re.sub(r"[\s_-]+", " ", value.strip()).upper()
    name = LICENSES.get(key)
    if not name:
        return None
    legal = canonical_license_url(url)
    if legal:
        parts = urlsplit(legal).path.strip("/").split("/")
        linked = (f"CC {'BY-SA' if parts[1] == 'by-sa' else 'BY'} {parts[2]}"
                  if parts[0] == "licenses" else "CC0 1.0" if parts[1] == "zero" else "Public Domain Mark 1.0")
        if name in {"CC BY", "CC BY-SA"}:
            return linked if linked.startswith(name + " ") else None
        if name == "Public Domain" and linked == "Public Domain Mark 1.0":
            return linked
        if name != linked:
            return None
    return name


def commons_filename(value, *, source_url=False):
    """Decode once; preserve punctuation, accents, semicolons and filename case."""
    if not isinstance(value, str) or not value:
        return None
    try:
        if source_url:
            parsed = urlsplit(value)
            if (parsed.scheme != "https" or parsed.hostname != "commons.wikimedia.org"
                    or parsed.username or parsed.password or parsed.port not in {None, 443}
                    or parsed.query or parsed.fragment or not parsed.path.startswith("/wiki/File:")):
                return None
            value = unquote(parsed.path[len("/wiki/File:"):], errors="strict")
        elif value.startswith("File:"):
            value = value[5:]
        value = unicodedata.normalize("NFC", value).replace("_", " ").strip()
        if not value or any(ord(c) < 32 for c in value):
            return None
        # File namespace is first-letter case insensitive; the rest is significant.
        return value[0].upper() + value[1:]
    except (ValueError, UnicodeError):
        return None


def commons_file_key(value):
    return commons_filename(value, source_url=True) if isinstance(value, str) and "://" in value else commons_filename(value)


def canonical_commons_metadata(info):
    result = dict(info)
    result["author"] = creator_key(info.get("author"))
    result["license"] = canonical_license(info.get("license"), info.get("license_url")) or info.get("license")
    result["license_url"] = canonical_license_url(info.get("license_url")) or info.get("license_url")
    return result
