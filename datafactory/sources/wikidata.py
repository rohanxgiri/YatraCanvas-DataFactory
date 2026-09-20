import datetime
import json
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import httpx

from ..config.settings import get_settings
from ..utils.cache import DiskCache
from ..utils.geo import haversine_distance_meters, is_point_in_bbox
from ..utils.text import fuzzy_name_similarity, clean_string, slugify


class WikidataEnricher:
    """
    Wikidata source adapter supporting TWO core roles:
    1. Independent travel-attraction candidate discovery via spatial bounding-box SPARQL queries.
    2. High-confidence entity enrichment (P18 images, Commons categories, official websites, multilingual labels).
    """

    SPARQL_URL = "https://query.wikidata.org/sparql"

    # Keywords for travel-relevant destinations
    TRAVEL_KEYWORDS = {
        "fort", "palace", "mahal", "museum", "gallery", "monument", "memorial",
        "temple", "mandir", "mosque", "masjid", "dargah", "church", "cathedral",
        "gurudwara", "stepwell", "baori", "ghat", "cenotaph", "chhatri", "stupa",
        "gate", "darwaza", "garden", "bagh", "park", "lake", "sarovar", "talab",
        "observatory", "zoo", "sanctuary", "heritage", "attraction", "tourist",
        "bazaar", "market", "viewpoint"
    }

    REJECT_KEYWORDS = {
        "human", "politician", "cricketer", "actor", "actress", "film", "song",
        "book", "album", "company", "corporation", "district", "constituency",
        "tehsil", "administrative", "village", "suburb"
    }

    def __init__(self):
        self.settings = get_settings()
        self.cache = DiskCache("wikidata")
        self.cache_dir = self.settings.source_cache_dir / "wikidata"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sources_cfg = self.settings.sources_config.get("sources", {}).get("wikidata", {})
        self.api_url = self.sources_cfg.get("api_url", "https://www.wikidata.org/w/api.php")
        self.timeout = self.sources_cfg.get("timeout_seconds", 30.0)

    def discover_city_attractions(
        self,
        bbox: Tuple[float, float, float, float],
        city_name: str
    ) -> List[Dict[str, Any]]:
        """
        Role 1: Independent discovery of travel POIs within city bounding box via Wikidata SPARQL.
        Caches results locally under data/source_cache/wikidata/{city_slug}_attractions.json.
        """
        city_slug = slugify(city_name)
        cached_file = self.cache_dir / f"{city_slug}_attractions.json"

        if cached_file.exists():
            print(f"[Wikidata] Loading cached spatial attractions from {cached_file}")
            with open(cached_file, "r", encoding="utf-8") as f:
                return json.load(f)

        min_lon, min_lat, max_lon, max_lat = bbox

        sparql_query = f"""
SELECT ?item ?itemLabel ?itemDescription ?coord ?p18 ?commons ?site ?sitelink ?heritage WHERE {{
  SERVICE wikibase:box {{
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point({min_lon} {min_lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point({max_lon} {max_lat})"^^geo:wktLiteral .
  }}
  OPTIONAL {{ ?item wdt:P18 ?p18 . }}
  OPTIONAL {{ ?item wdt:P373 ?commons . }}
  OPTIONAL {{ ?item wdt:P856 ?site . }}
  OPTIONAL {{ ?item wdt:P1435 ?heritage . }}
  OPTIONAL {{
    ?sitelink schema:about ?item ;
              schema:isPartOf <https://en.wikipedia.org/> .
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,hi". }}
}}
LIMIT 300
"""
        print(f"[Wikidata] Querying SPARQL spatial box for {city_name} [{bbox}]...")
        headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "application/sparql-results+json"
        }

        bindings = []
        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.SPARQL_URL, params={"query": sparql_query, "format": "json"})
                if resp.status_code == 200:
                    data = resp.json()
                    bindings = data.get("results", {}).get("bindings", [])
                else:
                    print(f"[Wikidata] SPARQL returned status {resp.status_code}")
        except Exception as e:
            print(f"[Wikidata] SPARQL query error: {e}")

        places = []
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for b in bindings:
            item_uri = b.get("item", {}).get("value", "")
            qid = item_uri.split("/")[-1] if "/" in item_uri else item_uri
            if not qid or not qid.startswith("Q"):
                continue

            name = b.get("itemLabel", {}).get("value", "")
            if not name or name == qid:
                continue

            desc = b.get("itemDescription", {}).get("value", "").lower()

            # Reject non-places
            if any(k in desc for k in self.REJECT_KEYWORDS):
                continue

            # Parse coordinates from Point(lon lat)
            coord_wkt = b.get("coord", {}).get("value", "")
            lat, lon = None, None
            m = re.search(r"Point\(([-\d.]+)\s+([-\d.]+)\)", coord_wkt)
            if m:
                lon = round(float(m.group(1)), 6)
                lat = round(float(m.group(2)), 6)

            if lat is None or lon is None:
                continue

            # Check if travel-relevant
            p18 = b.get("p18", {}).get("value")
            p18_fn = p18.split("FilePath/")[-1] if p18 and "FilePath/" in p18 else p18
            if p18_fn:
                import urllib.parse
                p18_fn = urllib.parse.unquote(p18_fn)

            commons_cat = b.get("commons", {}).get("value")
            website = b.get("site", {}).get("value")
            wikipedia = b.get("sitelink", {}).get("value")
            heritage = b.get("heritage", {}).get("value")

            name_lower = name.lower()
            is_travel_relevant = (
                any(k in name_lower for k in self.TRAVEL_KEYWORDS) or
                any(k in desc for k in self.TRAVEL_KEYWORDS) or
                bool(p18_fn) or
                bool(heritage) or
                bool(commons_cat)
            )

            if not is_travel_relevant:
                continue

            # Assign category based on structured terms and description
            cat = "heritage"
            subcat = "attraction"

            # 0. Lodging / Transit Negative Guards (Highest Priority)
            is_lodging = any(k in name_lower or k in desc for k in ["hotel", "resort", "inn", "guest house", "guesthouse", "oyo", "treebo", "fabhotel", "dharamshala", "homestay", "bhavan", "hostel", "motel"])
            is_transit = any(k in name_lower or k in desc for k in ["metro station", "railway station", "bus stand", "bus stop", "bus terminal", "airport", "junction"])

            if is_lodging:
                cat = "hotel"
                subcat = "hotel"
            elif is_transit:
                cat = "transport"
                subcat = "station"
            # 1. Forts, palaces, monuments, heritage buildings (highest priority over geographic tokens like lake)
            elif any(k in name_lower or k in desc for k in ["palace", "mahal", "haveli"]):
                cat = "heritage"
                subcat = "palace"
            elif any(k in name_lower or k in desc for k in ["fort", "garh", "castle"]):
                cat = "heritage"
                subcat = "fort"
            elif any(k in name_lower or k in desc for k in ["stepwell", "baori", "cenotaph", "chhatri", "stupa"]):
                cat = "heritage"
                subcat = "monument"
            elif any(k in name_lower or k in desc for k in ["observatory", "jantar mantar"]):
                cat = "heritage"
                subcat = "observatory"
            # 2. Temples and religious structures
            elif any(k in name_lower or k in desc for k in ["temple", "mandir", "mosque", "masjid", "dargah", "church", "gurudwara", "monastery"]):
                cat = "religious"
                subcat = "place_of_worship"
            # 3. Museums and galleries
            elif any(k in name_lower or k in desc for k in ["museum", "gallery", "sangrahalaya"]):
                cat = "museum"
                subcat = "history_museum"
            # 4. Parks and gardens
            elif any(k in name_lower or k in desc for k in ["garden", "bagh", "udyan", "national park"]):
                cat = "park"
                subcat = "garden"
            # 5. Lakes, water bodies, and ghats (only if not a palace, hotel, or station)
            elif any(k in name_lower or k in desc for k in ["lake", "sarovar", "talab", "waterfall"]):
                cat = "nature"
                subcat = "lake"
            elif any(k in name_lower or k in desc for k in ["ghat"]):
                cat = "heritage"
                subcat = "ghat"

            places.append({
                "source": "wikidata",
                "source_id": qid,
                "wikidata_id": qid,
                "name": name,
                "description": desc or None,
                "latitude": lat,
                "longitude": lon,
                "category": cat,
                "subcategory": subcat,
                "suggested_tier": "support" if (is_lodging or is_transit) else ("core_destination" if (p18_fn or wikipedia or heritage) else "recommended"),
                "website": website,
                "wikipedia_url": wikipedia,
                "commons_category": commons_cat,
                "wikidata_p18": p18_fn,
                "heritage": heritage,
                "retrieved_at": now_iso,
            })

        # Cache discovered places
        with open(cached_file, "w", encoding="utf-8") as f:
            json.dump(places, f, ensure_ascii=False, indent=2)

        print(f"[Wikidata] Discovered and cached {len(places)} travel attractions for {city_name}")
        return places

    def get_entity_details(self, qid: str) -> Optional[Dict[str, Any]]:
        """Fetch structured claims, labels, and sitelinks for a Wikidata QID."""
        if not qid or not qid.startswith("Q"):
            return None

        cached = self.cache.get(f"entity_{qid}")
        if cached:
            return cached

        params = {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims|labels|descriptions|sitelinks",
            "languages": "en|hi",
            "format": "json",
        }
        headers = {"User-Agent": self.settings.user_agent}

        try:
            with httpx.Client(headers=headers, timeout=self.timeout) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except Exception as e:
            print(f"Wikidata API error for {qid}: {e}")
            return None

        ent = data.get("entities", {}).get(qid)
        if not ent or "missing" in ent:
            return None

        claims = ent.get("claims", {})

        # P18: Image
        image_p18 = None
        if "P18" in claims and claims["P18"]:
            val = claims["P18"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(val, str):
                image_p18 = val

        # P625: Coordinate location
        coords = None
        if "P625" in claims and claims["P625"]:
            c_val = claims["P625"][0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(c_val, dict) and "latitude" in c_val and "longitude" in c_val:
                coords = (c_val["latitude"], c_val["longitude"])

        # P373: Commons category
        commons_cat = None
        if "P373" in claims and claims["P373"]:
            val = claims["P373"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(val, str):
                commons_cat = val

        # P856: Official website
        website = None
        if "P856" in claims and claims["P856"]:
            val = claims["P856"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(val, str):
                website = val

        # Wikipedia URL
        sitelinks = ent.get("sitelinks", {})
        wikipedia_url = None
        if "enwiki" in sitelinks:
            title = sitelinks["enwiki"].get("title")
            if title:
                wikipedia_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

        labels = ent.get("labels", {})
        label_en = labels.get("en", {}).get("value")
        label_hi = labels.get("hi", {}).get("value")
        desc = ent.get("descriptions", {}).get("en", {}).get("value")

        res = {
            "wikidata_id": qid,
            "label": label_en or label_hi,
            "label_en": label_en,
            "label_hi": label_hi,
            "description": desc,
            "p18_image": image_p18,
            "coordinates": coords,
            "commons_category": commons_cat,
            "official_website": website,
            "wikipedia_url": wikipedia_url,
        }

        self.cache.set(f"entity_{qid}", res)
        return res

    def resolve_entity(
        self,
        name: str,
        city_name: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        existing_qid: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Resolve place to a Wikidata entity with coordinate verification."""
        if existing_qid:
            details = self.get_entity_details(existing_qid)
            if details:
                return details

        # Search candidates
        search_query = f"{name} {city_name}"
        cache_key = f"search_{clean_string(search_query)}"
        candidates = self.cache.get(cache_key)

        if candidates is None:
            params = {
                "action": "wbsearchentities",
                "search": search_query,
                "language": "en",
                "format": "json",
                "limit": 5,
            }
            headers = {"User-Agent": self.settings.user_agent}
            try:
                with httpx.Client(headers=headers, timeout=self.timeout) as client:
                    resp = client.get(self.api_url, params=params)
                    if resp.status_code == 200:
                        candidates = resp.json().get("search", [])
                        self.cache.set(cache_key, candidates)
                    else:
                        candidates = []
            except Exception:
                candidates = []

        if not candidates:
            return None

        for cand in candidates:
            qid = cand.get("id")
            if not qid:
                continue

            details = self.get_entity_details(qid)
            if not details:
                continue

            cand_coords = details.get("coordinates")
            if lat is not None and lon is not None and cand_coords:
                dist = haversine_distance_meters(lat, lon, cand_coords[0], cand_coords[1])
                sim = fuzzy_name_similarity(name, details.get("label") or cand.get("label", ""))
                # Within 2km and good name similarity
                if dist <= 2000 and sim >= 0.70:
                    return details
            elif cand.get("description") and city_name.lower() in cand.get("description", "").lower():
                sim = fuzzy_name_similarity(name, details.get("label") or cand.get("label", ""))
                if sim >= 0.85:
                    return details

        return None
