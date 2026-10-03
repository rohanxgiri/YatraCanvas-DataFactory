"""City-scoped evidence index; legacy snapshots require matching resolved city lineage."""
import json
from collections import defaultdict
from pathlib import Path
from ..config.settings import get_settings
from ..utils.hashing import slugify
from ..utils.text import fuzzy_name_similarity
from ..utils.geo import haversine_distance_meters
from ..utils.cache import DiskCache
from .geographic_assurance import coordinates, valid_coordinates


class SourceEvidenceIndex:
    def __init__(self, city: dict, allow_network=False):
        self.city, self.allow_network = city, allow_network
        self.network_researches = 0
        settings = get_settings()
        self.settings = settings
        self.scope = Path(slugify(city["country"])) / slugify(city["state"]) / slugify(city["name"])
        self.by_id, self.rows = defaultdict(list), []
        resolved = settings.raw_dir / self.scope / "city_resolved.json"
        legacy_valid = False
        if resolved.exists():
            meta = json.loads(resolved.read_text(encoding="utf-8"))
            legacy_valid = all(meta.get(k, "").casefold() == city[k].casefold() for k in ("name", "state", "country"))
        for source in ("wikidata", "wikivoyage"):
            suffix = "attractions" if source == "wikidata" else "listings"
            path = settings.source_cache_dir / source / self.scope / f"{slugify(city['name'])}_{suffix}.json"
            if not path.exists() and legacy_valid:
                path = settings.source_cache_dir / source / f"{slugify(city['name'])}_{suffix}.json"
            if path.exists():
                rows = json.loads(path.read_text(encoding="utf-8"))
                for row in rows if isinstance(rows, list) else []:
                    self._add({**row, "source": source})
        osm = settings.raw_dir / self.scope / "osm" / "places_raw.json"
        if osm.exists():
            payload = json.loads(osm.read_text(encoding="utf-8"))
            rows = payload.get("elements", []) if isinstance(payload, dict) else payload
            for row in rows:
                if row.get("source") == "openstreetmap" and "latitude" in row:
                    self._add({**row, "source_id": row.get("source_id") or row.get("id")})
                    continue
                tags = row.get("tags", {})
                center = row.get("center", row)
                self._add({"source": "openstreetmap", "source_id": f"{row.get('type', 'node')}/{row.get('id')}",
                    "name": tags.get("name:en") or tags.get("name", ""), "alternate_names": [tags.get("alt_name", "")],
                    "latitude": center.get("lat"), "longitude": center.get("lon"), "wikidata_id": tags.get("wikidata"),
                    "opening_hours": tags.get("opening_hours"), "check_date": tags.get("check_date:opening_hours"),
                    "address": tags.get("addr:full"), "website": tags.get("website"),
                    "retrieved_at": payload.get("osm3s", {}).get("timestamp_osm_base") if isinstance(payload, dict) else None})

    def _add(self, row):
        self.rows.append(row)
        for key in (row.get("source_id"), row.get("wikidata_id")):
            if key:
                self.by_id[str(key)].append(row)

    def matches(self, place):
        ids = place.get("external_ids", {})
        found, seen = [], set()
        for key in list(ids.values()) + [s.get("source_id") for s in place.get("sources", [])]:
            if not isinstance(key, str):
                continue
            for row in self.by_id.get(key, []):
                signature = (row["source"], row.get("source_id"))
                if signature in seen:
                    continue
                seen.add(signature)
                # QIDs in corrupt source listings can be wrong. Require names/aliases and distance too.
                names = [place["name"]] + place.get("alternate_names", [])
                aliases = [row.get("name", "")] + row.get("alternate_names", [])
                similarity = max(fuzzy_name_similarity(a, b) for a in names for b in aliases)
                pcoords, rcoords = coordinates(place), coordinates(row)
                distance = haversine_distance_meters(*pcoords, *rcoords) if valid_coordinates(*pcoords) and valid_coordinates(*rcoords) else None
                if similarity >= 0.8:
                    found.append({**row, "identity_match": distance is not None and distance <= 300,
                                  "identity_name_match": True, "distance_m": distance})
        return found

    def research(self, place):
        matches = self.matches(place)
        qid = place.get("external_ids", {}).get("wikidata_id")
        if not qid:
            linked = {r.get("wikidata_id") for r in matches if r.get("identity_match") and r.get("wikidata_id")}
            if len(linked) == 1:
                qid = next(iter(linked))
        if qid:
            cache = DiskCache("wikidata")
            metadata = cache.get(f"entity_{qid}")
            if metadata is None and self.allow_network:
                limit = self.settings.load_yaml("assurance.yaml").get("source_research_max_places", 20)
                if self.network_researches < limit:
                    self.network_researches += 1
                    from ..sources.wikidata import WikidataEnricher
                    metadata = WikidataEnricher().get_entity_details(qid)
            if isinstance(metadata, dict):
                coords = metadata.get("coordinates") or [None, None]
                similarity = max(fuzzy_name_similarity(name, metadata.get("label") or "") for name in [place["name"]] + place.get("alternate_names", []))
                distance = haversine_distance_meters(*coordinates(place), *coords) if valid_coordinates(*coordinates(place)) and valid_coordinates(*coords) else None
                matches.append({**metadata, "source": "wikidata", "source_id": qid, "name": metadata.get("label"),
                    "latitude": coords[0], "longitude": coords[1], "identity_match": similarity >= 0.8 and distance is not None and distance <= 300,
                    "identity_name_match": similarity >= 0.8, "wikidata_p18": metadata.get("p18_image")})
        # For repairs, independently corroborated distant coordinates can be used after name and QID gates.
        source_coordinates = [{**r, "identity_match": bool(r.get("identity_name_match"))} for r in matches
                              if r.get("source") in {"wikidata", "openstreetmap"}
                              and (r.get("source") != "wikidata" or place.get("external_ids", {}).get("wikidata_id") or r.get("identity_match"))]
        media = {}
        snippets = []
        hours = []
        associations = []
        for row in matches:
            if not row.get("identity_match"):
                continue
            source = row["source"]
            source_id = row.get("source_id") or row.get("wikidata_id")
            source_url = (f"https://www.wikidata.org/wiki/{source_id}" if source == "wikidata" else
                          f"https://www.openstreetmap.org/{source_id}" if source == "openstreetmap" else
                          row.get("prose", {}).get("source_article"))
            provenance = {"source": source, "source_id": source_id, "source_url": source_url,
                          "retrieved_at": row.get("retrieved_at"), "check_date": row.get("check_date") or row.get("lastedit")}
            for key in ("wikidata_p18", "commons_image", "commons_category", "wikipedia_url"):
                if row.get(key):
                    media.setdefault(key, row[key])
            if row.get("description"):
                snippets.append({**provenance, "text": row["description"], "license": {"wikidata":"CC0", "wikivoyage":"CC BY-SA", "openstreetmap":"ODbL"}.get(source)})
            if row.get("prose", {}).get("text"):
                snippets.append({**provenance, "text": row["prose"]["text"], "license": row["prose"].get("license")})
            if row.get("opening_hours"):
                hours.append({**provenance, "text": row["opening_hours"]})
            if source == "wikivoyage" and source_url:
                associations.append({"source": source, "source_id": source_id, "city_id": self.city["id"], "relationship": "destination_listing", "source_url": source_url})
            administrative_ids = {v for v in (self.city.get("administrative_ids") or {}).values() if v}
            if self.city.get("wikidata_id"):
                administrative_ids.add(self.city["wikidata_id"])
            if source == "wikidata" and administrative_ids.intersection(row.get("location_hierarchy") or []):
                associations.append({"source": source, "source_id": source_id, "city_id": self.city["id"],
                                     "relationship": "administrative_region", "source_url": source_url})
        wikipedia_url = media.get("wikipedia_url")
        if wikipedia_url:
            from ..sources.wikipedia import WikipediaClient
            client = WikipediaClient()
            title = client._extract_title(wikipedia_url)
            text = client.get_summary(wikipedia_url) if self.allow_network else client.cache.get(f"wp_extract_{title.lower()}")
            if isinstance(text, str):
                # Legacy cache lacks retrieval date: do not fabricate one.
                snippets.insert(0, {"source": "wikipedia", "source_id": title, "source_url": wikipedia_url,
                                   "retrieved_at": None, "license": "CC BY-SA", "text": text})
        return {"matches": matches, "media": media, "coordinate_evidence": source_coordinates,
                "description_evidence": snippets, "hours_evidence": hours, "region_associations": associations}
