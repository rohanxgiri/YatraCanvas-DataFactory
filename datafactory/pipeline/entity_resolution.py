import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional
from collections import defaultdict

from ..config.settings import get_settings
from ..utils.geo import haversine_distance_meters, is_point_in_bbox
from ..utils.text import normalize_name, fuzzy_name_similarity, clean_string
from ..utils.hashing import generate_canonical_place_id


class CanonicalPlaceGraph:
    """
    Multi-source canonical entity resolution graph with Conflict Auditing.
    Merges candidates across Wikivoyage, Wikidata, OSM, Overture, Foursquare, and AllThePlaces.
    Maintains complete merge evidence in staging/entity_merges.jsonl
    and logs all detected entity conflicts into reports/entity_conflicts.jsonl.
    """

    def __init__(self, city_name: str, state_name: str, country_name: str):
        self.city_name = city_name
        self.state_name = state_name
        self.country_name = country_name
        self.merges_log: List[Dict[str, Any]] = []
        self.conflicts_log: List[Dict[str, Any]] = []
        self.alias_conflicts_count = 0
        self.category_conflicts_count = 0
        self.coordinate_conflicts_count = 0

    def resolve(
        self,
        candidates: List[Dict[str, Any]],
        merges_output_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Merge candidate records across all providers using the strict evidence hierarchy.
        Audits conflicts and rejects false merges.
        """
        settings = get_settings()

        # Authority order: Wikivoyage (10.0), Wikidata (9.0), OSM (7.0), Overture (4.0), Foursquare (3.0), AllThePlaces (2.0)
        def authority_score(c: Dict[str, Any]) -> float:
            score = 0.0
            src = c.get("source")
            if src == "wikivoyage":
                score += 10.0
            elif src == "wikidata":
                score += 9.0
            elif src == "openstreetmap":
                score += 7.0
            elif src == "overture":
                score += 4.0
            elif src == "foursquare":
                score += 3.0
            elif src == "alltheplaces":
                score += 2.0

            if c.get("wikidata_id"):
                score += 5.0
            if c.get("wikipedia_url") or c.get("wikipedia") or c.get("wikipedia_title"):
                score += 3.0
            if c.get("commons_image") or c.get("wikidata_p18"):
                score += 3.0
            if c.get("opening_hours"):
                score += 2.0
            if c.get("website"):
                score += 1.5
            return score

        sorted_candidates = sorted(candidates, key=authority_score, reverse=True)
        merged_indices: Set[int] = set()

        # Build indexes
        qid_index = defaultdict(list)
        grid_size = 0.005
        grid = defaultdict(list)
        website_index = defaultdict(list)

        for idx, c in enumerate(sorted_candidates):
            qid = c.get("wikidata_id") or c.get("wikidata")
            if qid and qid.startswith("Q"):
                qid_index[qid].append(idx)

            lat = c.get("latitude")
            lon = c.get("longitude")
            if lat is not None and lon is not None:
                cell = (int(lat / grid_size), int(lon / grid_size))
                grid[cell].append(idx)

            site = c.get("website")
            if site:
                clean_site = re.sub(r"^https?://(www\.)?", "", site.lower()).rstrip("/")
                if len(clean_site) > 5 and not any(p in clean_site for p in ["facebook.com", "instagram.com", "twitter.com"]):
                    website_index[clean_site].append(idx)

        canonical_entities = []

        for i in range(len(sorted_candidates)):
            if i in merged_indices:
                continue

            base = dict(sorted_candidates[i])
            base_id = base.get("source_id") or base.get("id") or str(i)
            base_name = base.get("name", "")
            base_lat = base.get("latitude")
            base_lon = base.get("longitude")
            base_qid = base.get("wikidata_id") or base.get("wikidata")
            base_site = base.get("website")

            match_candidates: Set[int] = set()

            if base_qid and base_qid in qid_index:
                for match_idx in qid_index[base_qid]:
                    if match_idx > i:
                        match_candidates.add(match_idx)

            if base_site:
                clean_site = re.sub(r"^https?://(www\.)?", "", base_site.lower()).rstrip("/")
                if clean_site in website_index:
                    for match_idx in website_index[clean_site]:
                        if match_idx > i:
                            match_candidates.add(match_idx)

            if base_lat is not None and base_lon is not None:
                c_lat_cell = int(base_lat / grid_size)
                c_lon_cell = int(base_lon / grid_size)
                for d_lat in (-1, 0, 1):
                    for d_lon in (-1, 0, 1):
                        cell = (c_lat_cell + d_lat, c_lon_cell + d_lon)
                        for match_idx in grid.get(cell, []):
                            if match_idx > i:
                                match_candidates.add(match_idx)

            for j in sorted(list(match_candidates)):
                if j in merged_indices:
                    continue

                cand = sorted_candidates[j]
                cand_id = cand.get("source_id") or cand.get("id") or str(j)
                cand_name = cand.get("name", "")

                is_dup, reason, conf, conflict_info = self._check_entity_agreement(base, cand)

                if conflict_info:
                    self.conflicts_log.append(conflict_info)

                if is_dup:
                    merged_indices.add(j)
                    self.merges_log.append({
                        "discarded_id": cand_id,
                        "discarded_source": cand.get("source"),
                        "discarded_name": cand_name,
                        "merged_into_id": base_id,
                        "merged_into_source": base.get("source"),
                        "merged_into_name": base_name,
                        "evidence": reason,
                        "confidence": conf,
                    })
                    self._merge_attributes(base, cand, reason, conf)

            canonical = self._build_canonical_record(base)
            canonical_entities.append(canonical)

        # Write staging entity merges
        merges_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(merges_output_path, "w", encoding="utf-8") as f:
            for m in self.merges_log:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

        # Write reports/entity_conflicts.jsonl
        conflicts_file = settings.reports_dir / "entity_conflicts.jsonl"
        conflicts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(conflicts_file, "a", encoding="utf-8") as f:
            for c in self.conflicts_log:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

        print(f"[EntityResolution] Canonical entities: {len(canonical_entities)} (Merged {len(self.merges_log)} duplicates, Audited {len(self.conflicts_log)} conflicts)")
        return canonical_entities

    def _check_entity_agreement(
        self,
        base: Dict[str, Any],
        cand: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], float, Optional[Dict[str, Any]]]:
        """
        Calculates multi-signal agreement across name, coordinates, category, and IDs.
        Detects conflicts and returns (is_dup, reason, confidence, conflict_record).
        """
        base_name = base.get("name", "")
        cand_name = cand.get("name", "")
        base_lat = base.get("latitude")
        base_lon = base.get("longitude")
        cand_lat = cand.get("latitude")
        cand_lon = cand.get("longitude")
        base_qid = base.get("wikidata_id") or base.get("wikidata")
        cand_qid = cand.get("wikidata_id") or cand.get("wikidata")
        base_site = base.get("website")
        cand_site = cand.get("website")

        # Calculate max name similarity across names and known aliases
        names_base = [base_name] + base.get("alternate_names", [])
        names_cand = [cand_name] + cand.get("alternate_names", [])

        max_sim = 0.0
        for nb in names_base:
            for nc in names_cand:
                sim = fuzzy_name_similarity(nb, nc)
                if sim > max_sim:
                    max_sim = sim

        dist = None
        if base_lat is not None and base_lon is not None and cand_lat is not None and cand_lon is not None:
            dist = haversine_distance_meters(base_lat, base_lon, cand_lat, cand_lon)

        # -------------------------------------------------------------
        # 1. External ID Conflict Check (e.g. Sankat Mochan vs Durga Mandir)
        # -------------------------------------------------------------
        if base_qid and cand_qid and base_qid == cand_qid:
            # If QIDs match, but name similarity is low and no distinctive token overlaps
            generic_tokens = {
                "temple", "mandir", "masjid", "mosque", "church", "gurudwara",
                "hotel", "palace", "museum", "park", "garden", "lake", "fort",
                "station", "gate", "road", "street", "marg", "bhawan", "house",
                "residency", "resort", "restaurant", "cafe", "bazaar", "market",
                "center", "centre", "complex", "international", "national",
                "uttar", "pradesh", "rajasthan", "india",
                getattr(self, "city_name", "").lower(),
                getattr(self, "state_name", "").lower(),
                getattr(self, "country_name", "").lower(),
            }
            tokens_b = {w for w in normalize_name(base_name).split() if len(w) > 2 and w not in generic_tokens}
            tokens_c = {w for w in normalize_name(cand_name).split() if len(w) > 2 and w not in generic_tokens}
            distinctive_overlap = bool(tokens_b & tokens_c)
            sim_canonical = fuzzy_name_similarity(base_name, cand_name)

            if (max_sim < 0.50 or sim_canonical < 0.50) and not distinctive_overlap:
                # CONFLICT: Corrupted external ID (e.g. Wikivoyage listing carrying wrong QID)
                conflict_record = {
                    "canonical_id": base.get("source_id") or base.get("id"),
                    "source_records_involved": [
                        {"source": base.get("source"), "id": base.get("source_id"), "name": base_name, "qid": base_qid},
                        {"source": cand.get("source"), "id": cand.get("source_id"), "name": cand_name, "qid": cand_qid},
                    ],
                    "names": [base_name, cand_name],
                    "alternate_names": [base.get("alternate_names", []), cand.get("alternate_names", [])],
                    "coordinates": [(base_lat, base_lon), (cand_lat, cand_lon)],
                    "categories": [base.get("category"), cand.get("category")],
                    "external_ids": {"wikidata_id": base_qid},
                    "reason_for_conflict": "shared_wikidata_id_with_severe_name_mismatch",
                    "name_similarity": round(max_sim, 3),
                    "confidence": 0.20,
                    "recommended_automated_resolution": "split_entities_and_strip_unverified_qid",
                }
                # Cleanse the incorrect QID from the candidate that does not match the Wikidata label
                if cand.get("source") == "wikidata":
                    base["wikidata_id"] = None
                elif base.get("source") == "wikidata":
                    cand["wikidata_id"] = None
                else:
                    base["wikidata_id"] = None
                    cand["wikidata_id"] = None

                return False, None, 0.0, conflict_record

            # High-confidence agreed match
            return True, f"shared_wikidata_id:{base_qid}", 1.0, None

        # -------------------------------------------------------------
        # 2. Shared Website Check
        # -------------------------------------------------------------
        if base_site and cand_site and dist is not None:
            site1 = re.sub(r"^https?://(www\.)?", "", base_site.lower()).rstrip("/")
            site2 = re.sub(r"^https?://(www\.)?", "", cand_site.lower()).rstrip("/")
            if site1 == site2 and len(site1) > 6:
                if dist <= 300 and max_sim >= 0.50:
                    return True, f"shared_website_and_dist_{int(dist)}m", 0.95, None
                elif dist > 1000:
                    # Chain store or shared organizational portal
                    self.coordinate_conflicts_count += 1
                    return False, None, 0.0, None

        # -------------------------------------------------------------
        # 3. Spatial Proximity + Name Agreement
        # -------------------------------------------------------------
        if dist is not None:
            # Check category compatibility
            base_cat = base.get("category")
            cand_cat = cand.get("category")
            base_sub = base.get("subcategory")
            cand_sub = cand.get("subcategory")

            # Completely incompatible categories cannot merge (e.g. hotel vs railway station, or food vs museum)
            is_compat = True
            if base_cat and cand_cat:
                if (base_cat == "transport" and cand_cat != "transport") or (cand_cat == "transport" and base_cat != "transport"):
                    is_compat = False
                elif (base_cat == "hotel" and cand_cat in ("religious", "park", "nature", "transport")):
                    is_compat = False

            if not is_compat:
                self.category_conflicts_count += 1
                return False, None, 0.0, None

            is_heritage = base_cat == "heritage" or cand_cat == "heritage"
            max_dist = 350 if is_heritage else 120

            if dist <= max_dist and max_sim >= 0.80:
                return True, f"spatial_proximity_{int(dist)}m_name_sim_{round(max_sim, 2)}", round(max_sim, 2), None
            elif dist <= 25 and max_sim >= 0.70:
                return True, f"very_close_dist_{int(dist)}m_name_sim_{round(max_sim, 2)}", 0.90, None
            elif dist <= 25 and max_sim < 0.40:
                # Two distinct entities within 25m (e.g. two neighboring shops or temples)
                return False, None, 0.0, None

        return False, None, 0.0, None

    def _merge_attributes(
        self,
        base: Dict[str, Any],
        cand: Dict[str, Any],
        merge_reason: str,
        conf: float
    ) -> None:
        """
        Merges attributes safely. Attaches source provenance to alternate names
        and only accepts high-confidence aliases.
        """
        # Alternate names with provenance
        alts = base.setdefault("alternate_names", [])
        alt_records = base.setdefault("alternate_name_records", [])
        cand_source = cand.get("source", "unknown")

        # Candidate's own name as alternate if different
        cand_name = cand.get("name")
        if cand_name and cand_name != base.get("name"):
            name_sim = fuzzy_name_similarity(base.get("name", ""), cand_name)
            # Safe multilingual rule: only accept if merge confidence is high
            if conf >= 0.80 or name_sim >= 0.60:
                if cand_name not in alts:
                    alts.append(cand_name)
                alt_records.append({
                    "name": cand_name,
                    "source": cand_source,
                    "confidence": conf,
                    "evidence": merge_reason,
                })
            else:
                self.alias_conflicts_count += 1

        # Candidate's existing alternate names
        for alt in cand.get("alternate_names", []):
            if alt and alt != base.get("name"):
                name_sim = fuzzy_name_similarity(base.get("name", ""), alt)
                if conf >= 0.80 or name_sim >= 0.60:
                    if alt not in alts:
                        alts.append(alt)
                    alt_records.append({
                        "name": alt,
                        "source": cand_source,
                        "confidence": conf,
                        "evidence": merge_reason,
                    })
                else:
                    self.alias_conflicts_count += 1

        # Multilingual names: only adopt when confidence is high
        if not base.get("name_hi") and cand.get("name_hi") and conf >= 0.80:
            base["name_hi"] = cand["name_hi"]
        if not base.get("name_en") and cand.get("name_en") and conf >= 0.80:
            base["name_en"] = cand["name_en"]

        # External IDs
        if not base.get("wikidata_id") and cand.get("wikidata_id") and conf >= 0.70:
            base["wikidata_id"] = cand["wikidata_id"]
        if not base.get("foursquare_id") and cand.get("foursquare_id"):
            base["foursquare_id"] = cand["foursquare_id"]
        if not base.get("alltheplaces_id") and cand.get("alltheplaces_id"):
            base["alltheplaces_id"] = cand["alltheplaces_id"]

        # Opening hours propagation
        if not base.get("opening_hours") and cand.get("opening_hours"):
            base["opening_hours"] = cand["opening_hours"]
            base["opening_hours_source"] = cand.get("source")

        # Contact & Web
        if not base.get("website") and cand.get("website"):
            base["website"] = cand["website"]
        if not base.get("phone") and cand.get("phone"):
            base["phone"] = cand["phone"]
        if not base.get("address") and cand.get("address"):
            base["address"] = cand["address"]

        # Images
        if not base.get("commons_image") and cand.get("commons_image"):
            base["commons_image"] = cand["commons_image"]
        if not base.get("wikidata_p18") and cand.get("wikidata_p18"):
            base["wikidata_p18"] = cand["wikidata_p18"]
        if not base.get("commons_category") and cand.get("commons_category"):
            base["commons_category"] = cand["commons_category"]
        if not base.get("wikipedia_url") and cand.get("wikipedia_url"):
            base["wikipedia_url"] = cand["wikipedia_url"]

        # Accumulate Category votes for voting engine
        cat_votes = base.setdefault("category_votes", [])
        if cand.get("category"):
            cand_weight = 2.0
            if cand_source == "wikidata":
                cand_weight = 4.0
            elif cand_source == "openstreetmap":
                cand_weight = 3.5
            elif cand_source == "wikivoyage":
                cand_weight = 3.0
            cat_votes.append({
                "category": cand.get("category"),
                "subcategory": cand.get("subcategory"),
                "source": cand_source,
                "weight": cand_weight,
            })

        # Track external IDs
        ext_ids = base.setdefault("external_ids", {})
        cand_src_id = cand.get("source_id") or cand.get("id")
        if cand_source and cand_src_id:
            ext_ids.setdefault(f"{cand_source}_ids", []).append(cand_src_id)

        # Merge source provenance
        prov = base.setdefault("sources_provenance", [])
        cand_prov = cand.get("sources_provenance")
        if cand_prov:
            prov.extend(cand_prov)
        else:
            prov.append({
                "source": cand_source,
                "source_id": cand_src_id,
                "retrieved_at": cand.get("retrieved_at"),
            })

    def _build_canonical_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        name = clean_string(raw.get("name", ""))
        canonical_id = generate_canonical_place_id(
            country=self.country_name,
            state=self.state_name,
            city=self.city_name,
            name=name
        )

        tier = self._classify_place_tier(raw)

        ext = raw.get("external_ids", {})
        src = raw.get("source")
        src_id = raw.get("source_id") or raw.get("id")
        if src and src_id:
            ext.setdefault(f"{src}_ids", [])
            if src_id not in ext[f"{src}_ids"]:
                ext[f"{src}_ids"].append(src_id)

        prov = raw.get("sources_provenance", [])
        if not prov and src:
            prov.append({
                "source": src,
                "source_id": src_id,
                "retrieved_at": raw.get("retrieved_at"),
            })

        return {
            "canonical_id": canonical_id,
            "name": name,
            "name_en": raw.get("name_en") or name,
            "name_hi": raw.get("name_hi"),
            "alternate_names": raw.get("alternate_names", []),
            "alternate_name_records": raw.get("alternate_name_records", []),
            "latitude": raw.get("latitude"),
            "longitude": raw.get("longitude"),
            "category": raw.get("category", "experience"),
            "subcategory": raw.get("subcategory"),
            "category_votes": raw.get("category_votes", []),
            "tier": tier,
            "address": raw.get("address"),
            "website": raw.get("website"),
            "phone": raw.get("phone"),
            "email": raw.get("email"),
            "opening_hours": raw.get("opening_hours"),
            "opening_hours_source": raw.get("opening_hours_source") or raw.get("source"),
            "wikidata_id": raw.get("wikidata_id") or raw.get("wikidata"),
            "wikipedia_url": raw.get("wikipedia_url") or (f"https://en.wikipedia.org/wiki/{raw['wikipedia_title'].replace(' ', '_')}" if raw.get("wikipedia_title") else None),
            "wikidata_p18": raw.get("wikidata_p18"),
            "commons_image": raw.get("commons_image"),
            "commons_category": raw.get("commons_category"),
            "tags": raw.get("tags", []),
            "prose": raw.get("prose"),
            "external_ids": ext,
            "sources_provenance": prov,
            "confidence": raw.get("confidence", 0.70),
        }

    def _classify_place_tier(self, p: Dict[str, Any]) -> str:
        """
        Assign place to one of 4 tiers: core_destination, recommended, discovery, support.
        Enforces strict de-inflation: generic commercial records without strong travel signals
        can NEVER be promoted to core_destination.
        """
        cat = p.get("category")
        subcat = p.get("subcategory")
        listing_type = p.get("listing_type")
        sources = [s.get("source") for s in p.get("sources_provenance", [])]
        name_lower = p.get("name", "").lower()

        # 1. Support tier (logistics, hotels, transit)
        if cat in ("hotel", "transport", "railway_station", "airport", "bus_station"):
            return "support"
        if subcat in ("hotel", "resort", "railway_station", "bus_station", "airport", "parking"):
            return "support"
        if listing_type in ("sleep", "go"):
            return "support"

        # Exclude commercial/lodging terms from becoming core_destination
        is_commercial = any(w in name_lower for w in [
            "hotel", "oyo", "residency", "inn", "guest house", "resort",
            "apartment", "apartments", "complex", "colony", "mairrage garden",
            "marriage garden", "chauraha", "tiraha", "bypass", "dhaba",
            "sweets", "bhandar", "store", "shop", "deluxe", "dry cleaners", "laundromat"
        ])
        if is_commercial:
            if cat == "food":
                return "recommended" if len(sources) > 1 else "discovery"
            return "support" if cat == "hotel" else "discovery"

        # 2. Strict Core Destination Promotion
        # A candidate MUST have at least ONE strong travel signal:
        # - Wikivoyage see/do listing
        # - Travel-relevant Wikidata class / entity
        # - OSM tourism or historic tag
        # - Official heritage status
        # - Agreement between at least 2 independent strong sources
        has_wikivoyage_see = (listing_type in ("see", "do") or "wikivoyage" in sources)
        has_wikidata = bool(p.get("wikidata_id") or p.get("wikidata_p18"))
        has_heritage = bool(p.get("heritage"))
        has_osm_travel = any(s in ("openstreetmap",) for s in sources) and cat in ("heritage", "museum", "religious")
        has_multi_source = len(set(sources)) >= 2 and cat in ("heritage", "museum", "religious", "park", "nature", "arts_culture")

        is_strong_travel_candidate = (
            has_wikivoyage_see or
            has_wikidata or
            has_heritage or
            has_osm_travel or
            has_multi_source
        )

        if is_strong_travel_candidate and cat in ("heritage", "museum", "arts_culture", "religious", "nature", "viewpoint", "park"):
            # Major categories qualify for core destination
            if cat in ("heritage", "museum", "viewpoint") or has_wikivoyage_see or (has_wikidata and cat != "religious"):
                return "core_destination"
            if cat == "religious" and (has_wikidata or has_heritage or has_wikivoyage_see):
                return "core_destination"
            if cat == "nature" and (has_wikidata or has_wikivoyage_see):
                return "core_destination"
            return "recommended"

        # 3. Recommended tier
        if cat in ("religious", "park", "food", "cafe", "shopping", "arts_culture"):
            return "recommended"
        if len(sources) > 1:
            return "recommended"

        # 4. Discovery tier
        return "discovery"
