"""Infer source quality from bounded, public identifiers, never claimed labels."""
import ipaddress
from urllib.parse import urlparse
from ..pipeline.media_assurance import public_url


def public_source(url):
    if not isinstance(url, str) or not public_url(url):
        return False
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.query or parsed.fragment or "." not in host or host.endswith((".local", ".internal")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return not host.endswith((".localhost", ".test", ".invalid")) and host != "localhost"


def source_quality(source, place):
    url = source.get("url")
    if not public_source(url):
        # An existing structured identifier can stand in for a public URL.
        value = source.get("source_id")
        matched = value and value in [v for v in place.get("external_ids", {}).values() if v]
        return ("STRUCTURED_OPEN_DATA", .90) if not url and matched else ("UNKNOWN", 0.0)
    host = urlparse(url).hostname
    website = place.get("contact", {}).get("website")
    official = urlparse(website).hostname if website and public_source(website) else None
    if official and host == official:
        return "OFFICIAL", .95
    if host.endswith((".gov", ".gov.in", ".nic.in", ".gouv.fr", ".gov.uk")):
        return "GOVERNMENT", .95
    if host in {"www.wikidata.org", "www.openstreetmap.org", "openstreetmap.org"}:
        ids = place.get("external_ids", {})
        key = "wikidata_id" if host == "www.wikidata.org" else "osm_id"
        value = ids.get(key)
        if value and urlparse(url).path.rstrip("/").endswith("/" + value) and source.get("source_id") in {None, value}:
            return "STRUCTURED_OPEN_DATA", .90
        return "STRUCTURED_OPEN_DATA", .70
    if host == "commons.wikimedia.org" or host.endswith((".wikipedia.org", ".wikivoyage.org")):
        return "CURATED_REFERENCE", .85
    return "SECONDARY", .60
