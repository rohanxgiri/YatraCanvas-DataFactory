import copy
import json
import uuid
import re
from collections import Counter
from pathlib import Path
from ..ai.router import AIRouter, digest
from ..config.settings import get_settings
from ..models.media_candidate import MediaCandidate
from ..utils.atomic import atomic_json
from ..utils.hashing import slugify
from .source_evidence import SourceEvidenceIndex
from .geographic_assurance import coordinate_audit, geography
from .identity_assurance import conflict_groups, identity_decision
from .media_assurance import MediaAssurance, deterministic_filter, local_asset
from .media_policy import media_policy, MediaPolicy
from .metadata_assurance import extract_hours, extract_description
from .fallbacks import FallbackPools, fallback_distribution, fallback_strategy, retire_factory_fallbacks
from .usability import usability


def candidate_from_existing(metadata):
    return MediaCandidate(source=metadata.get("source", ""), source_url=metadata.get("source_page") or "",
        media_url=metadata.get("source_page") or "", title=metadata.get("original_file") or "",
        creator=metadata.get("author"), license=metadata.get("license") or "", license_url=metadata.get("license_url"),
        attribution=metadata.get("attribution"), width=metadata.get("width") or 0, height=metadata.get("height") or 0,
        mime_type="image/webp", source_confidence=metadata.get("match_confidence") or 0,
        match_method=metadata.get("match_method") or "legacy", original_license_verified=metadata.get("source") == "Wikimedia Commons")


def city_context(city):
    return {k: city.get(k) for k in ("id", "name", "state", "country", "alternate_names", "center", "bbox", "timezone", "administrative_ids", "source_identifiers", "boundary_geometry", "region_bbox", "region_geometry", "boundary_buffer_m", "region_buffer_m")}


def human_field_locks(settings, city):
    """Existing verified curation remains authoritative during assurance repair."""
    from .curation import _records, _identifier
    root = settings.curated_dir / city["id"]
    if not root.is_dir():
        root = settings.curated_dir / slugify(city["name"])
    locks = {}
    for path, data in _records(root / "overrides"):
        if data.get("verified") is True:
            locks[_identifier(data, path)] = {key for key, value in data.items() if value is not None}
    return locks


def linked_field_repairs(place, evidence, occupied_qids):
    """Recover exact linked-source values only after name and location corroboration."""
    rows = [r for r in evidence["matches"] if r.get("identity_match") is True]
    results = []
    for field, candidates in [
        ("external_ids.wikidata_id", [(r, r.get("wikidata_id") or (r.get("source_id") if r.get("source") == "wikidata" else None)) for r in rows]),
        ("location.address", [(r, r.get("address")) for r in rows if r.get("source") == "openstreetmap"]),
    ]:
        parent, key = field.split(".")
        if place.get(parent, {}).get(key):
            continue
        candidates = [(r, v) for r, v in candidates if isinstance(v, str) and v.strip()]
        values = {v for _, v in candidates}
        if len(values) != 1:
            continue
        row, value = candidates[0]
        if key == "wikidata_id" and (not re.fullmatch(r"Q[1-9]\d*", value) or value in occupied_qids):
            continue
        if key == "wikidata_id":
            # An OSM tag alone can point at a similarly named entity in another
            # city. The Wikidata entity's own label/coordinates must also match.
            verified = [r for r in rows if r.get("source") == "wikidata" and r.get("source_id") == value]
            linked = [r for r in rows if r.get("source") in {"openstreetmap", "wikivoyage"} and r.get("wikidata_id") == value]
            if not verified or not linked:
                continue
            row = verified[0]
        results.append({"field": field, "value": value, "action": "AUTO_APPLY", "confidence": .99,
            "provenance": {"field": field, "source": row["source"], "source_id": row["source_id"],
                           "retrieved_at": row.get("retrieved_at"), "source_value": value},
            "reason_codes": ["LINKED_SOURCE_IDENTITY_NAME_COORDINATES_AGREE"]})
    return results


def run_repair(source_pack: Path, *, apply=False, allow_network=False, output_version="v3-offline", router=None):
    settings = get_settings()
    city = json.loads((source_pack / "city.json").read_text(encoding="utf-8"))
    original = json.loads((source_pack / "places.json").read_text(encoding="utf-8"))
    places = copy.deepcopy(original)
    context = city_context(city)
    scope = Path(slugify(city["country"])) / slugify(city["state"]) / slugify(city["name"])
    report_dir = settings.reports_dir / scope / "assurance"
    work = settings.staging_dir / scope / "assurance"
    router = router or AIRouter(context, settings.cache_dir / "ai")
    cfg = settings.load_yaml("assurance.yaml")
    strategy = fallback_strategy(cfg)
    retired = retire_factory_fallbacks(places) if strategy == "app" else []
    index = SourceEvidenceIndex(city, allow_network)
    media = MediaAssurance(city, router, work, allow_network)
    locks = human_field_locks(settings, city)
    if apply:
        work = work / "runs" / uuid.uuid4().hex
    pools = FallbackPools(settings.project_root / cfg.get("fallbacks", {}).get("directory", "assets/fallbacks")) if strategy == "bundled" else None
    authoring = pools.authoring_manifest(places, report_dir / "fallback_authoring.json") if pools else {
        "enabled":False, "strategy":"app", "reason":"YatraCanvas app supplies fallback presentation",
        "external_generation_required":False, "categories":[]}
    if not pools:
        atomic_json(report_dir / "fallback_authoring.json", authoring)
    before = usability(original, city, source_pack)
    assurance, decisions, field_provenance, media_rows = {}, [], [], []
    identities = []
    from ..local_intelligence.text import LocalTextSimilarity
    text_similarity = LocalTextSimilarity()
    identity_blockers = set()
    for group in conflict_groups(places):
        members = group["places"]
        for i, a in enumerate(members):
            for b in members[i+1:]:
                decision = identity_decision(a, b, router, text_similarity)
                item = {"group_kind": group["kind"], "key": group["key"], "place_ids": [a["id"], b["id"]], **decision}
                if group["kind"] == "canonical_id":
                    item.update(decision="UPSTREAM_CANONICAL_ID_BUG", action="REVIEW")
                identities.append(item)
                if item["decision"] not in {"SAFE_DIFFERENT_PLACE"}:
                    identity_blockers.update([a["id"], b["id"]])
                # Existing published-ID merges require downstream migration. Keep review evidence.
                if item["decision"] == "SAFE_SAME_PLACE":
                    item["action"] = "REVIEW_PUBLISHED_ID_MERGE"
    # Diagnose canonical-ID failures upstream of publication without reviving quarantined records.
    quarantine = settings.staging_dir / scope / "quarantine" / "quarantined_places.jsonl"
    published_by_id = {p["id"]: p for p in places}
    seen_upstream = set()
    if quarantine.exists():
        for line in quarantine.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            raw = entry.get("place", {})
            pid = raw.get("canonical_id")
            if pid not in published_by_id:
                continue
            signature = digest({"id": pid, "latitude": raw.get("latitude"), "longitude": raw.get("longitude"), "sources": raw.get("sources_provenance", [])})
            if signature in seen_upstream:
                continue
            seen_upstream.add(signature)
            decision = identity_decision(published_by_id[pid], raw, router)
            identities.append({"origin": "upstream_quarantine", "group_kind": "canonical_id", "key": pid,
                               "place_ids": [pid, pid], "decision": "UPSTREAM_CANONICAL_ID_BUG",
                               "identity_assessment": decision, "action": "REVIEW",
                               "published": published_by_id[pid], "quarantined": raw,
                               "reason_codes": ["DISTINCT_SOURCE_ENTITIES_SHARED_NAME_BASED_ID"]})
    summary = Counter(REAL_REQUIRED=0, already_valid=0, recovered=0, rejected_candidates=0, still_unresolved=0,
                      candidate_images_found=0, wikimedia_candidates=0, openverse_candidates=0,
                      hours_recovered=0, descriptions_recovered=0, coordinate_repairs=0, entity_links_recovered=0)
    occupied_qids = {p.get("external_ids", {}).get("wikidata_id") for p in places}
    network_discoveries = 0
    def priority(place):
        required = media_policy(place) == MediaPolicy.REAL_REQUIRED
        image = place.get("images", {}).get("primary") or {}
        missing = not local_asset(source_pack,image.get("local_path"))
        return (0 if required and missing else 1 if required else 2, -place.get("prominence_score",0))
    # Process references in priority order while preserving published export order.
    for place in sorted(places,key=priority):
        pid = place["id"]
        locked = locks.get(pid, set())
        policy = media_policy(place)
        evidence = index.research(place)
        for result in linked_field_repairs(place, evidence, occupied_qids):
            parent, key = result["field"].split(".")
            if key in locked:
                continue
            decisions.append({"place_id": pid, **result})
            field_provenance.append({"place_id": pid, **result["provenance"]})
            if apply:
                place[parent][key] = result["value"]
            if key == "wikidata_id":
                occupied_qids.add(result["value"])
            summary["entity_links_recovered" if key == "wikidata_id" else "addresses_recovered"] += 1
        assessment = {"media_policy": policy.value, "identity_blocker": pid in identity_blockers}
        place["region_associations"] = evidence["region_associations"]
        coord = coordinate_audit(place, evidence["coordinate_evidence"], cfg.get("coordinate_agreement_m", 100),
                                 cfg.get("coordinate_minor_variance_m", 300), cfg.get("coordinate_conflict_m", 2000))
        assessment["coordinate"] = coord
        if coord.get("replacement") and not {"latitude", "longitude"}.intersection(locked):
            proposed = {**place, "location": {**place["location"], **{k: coord["replacement"][k] for k in ("latitude", "longitude")}}}
            if geography(proposed, city, cfg.get("region_max_distance_km", 120))["status"] == "VALID":
                decisions.append({"place_id": pid, "field": "location", **coord})
                if apply:
                    place["location"] = proposed["location"]
                field_provenance.append({"place_id": pid, "field": "location", "previous_value": coord["original_coordinates"], **coord["replacement"]})
                summary["coordinate_repairs"] += 1
            else:
                coord["action"] = "REVIEW"
        elif coord.get("replacement"):
            coord.update(action="REVIEW", reason_codes=["HUMAN_COORDINATES_PRESERVED"])
        assessment["geography"] = geography(place, city, cfg.get("region_max_distance_km", 120))
        current = place.get("images", {}).get("primary")
        human_media = bool(current and current.get("match_method") == "verified_human_curation")
        required = policy == MediaPolicy.REAL_REQUIRED
        verified = False
        assessments = []
        discovered_count, discovery_attempted = None, False
        if required:
            summary["REAL_REQUIRED"] += 1
        if current and current.get("image_type", "real") == "real":
            path = local_asset(source_pack, current.get("local_path"))
            candidate = candidate_from_existing(current)
            if not candidate.attribution and candidate.creator and candidate.creator.lower() != "unknown":
                candidate.attribution = f"{candidate.creator} / {candidate.source} / {candidate.license}"
                decisions.append({"place_id": pid, "field": "images.primary.attribution", "action": "AUTO_APPLY", "value": candidate.attribution})
                if apply:
                    current["attribution"] = candidate.attribution
            if path:
                content = path.read_bytes()
                checks = deterministic_filter(candidate, content)
                if required and checks["accepted"]:
                    # Only source relationships actually supplied for this identity may boost linkage.
                    if candidate.title == evidence["media"].get("wikidata_p18"):
                        candidate.source_confidence = 0.99
                        candidate.match_method = "wikidata_p18"
                        candidate.related_entity_id = place.get("external_ids", {}).get("wikidata_id")
                    elif candidate.title == evidence["media"].get("commons_image"):
                        candidate.source_confidence = 0.95
                    elif current.get("match_method") == "commons_category" and evidence["media"].get("commons_category"):
                        candidate.source_confidence = 0.92
                    assessed = media.assess(place, candidate, content)
                    assessed["existing"] = True
                    assessments.append(assessed)
                    verified = assessed["action"] == "AUTO_APPLY"
                elif not checks["accepted"]:
                    assessments.append({"candidate": candidate.model_dump(), "checks": checks, "action": "REJECT", "reason_codes": checks["reason_codes"], "existing": True})
                    if apply and not human_media:
                        place["images"]["primary"] = None
                        current = None
            else:
                assessments.append({"action": "REJECT", "reason_codes": ["LOCAL_ASSET_MISSING"], "existing": True})
                if apply and not human_media:
                    place["images"]["primary"] = None
                    current = None
        if required and not verified and not human_media:
            cached_candidates = media.cached_discovery(place,evidence["media"])
            # Source/download budgets are independent of cloud inference budgets:
            # a verified P18 can still succeed after the LLM budget is exhausted.
            media.allow_network = allow_network and network_discoveries < cfg.get("media_discovery_max_places", 20)
            if media.allow_network:
                network_discoveries += 1
            candidates = cached_candidates if cached_candidates is not None else media.discover(place, evidence["media"])
            discovered_count, discovery_attempted = len(candidates), True
            summary["candidate_images_found"] += len(candidates)
            summary["wikimedia_candidates"] += sum(c.source == "Wikimedia Commons" for c in candidates)
            summary["openverse_candidates"] += sum(c.source.startswith("Openverse/") for c in candidates)
            ranked, rejected = media.prepare(place, candidates)
            assessments.extend(rejected)
            finalists = 0
            for ranked_candidate in ranked:
                candidate = ranked_candidate["candidate"]
                content = media.download(candidate)
                if content is None:
                    assessments.append({"candidate": candidate.model_dump(), "action": "UNRESOLVED", "reason_codes": ["DOWNLOAD_UNAVAILABLE"]})
                    continue
                if finalists >= cfg.get("media", {}).get("finalists", 3):
                    break
                assessed = media.assess(place, candidate, content, local=ranked_candidate["local"])
                assessments.append(assessed)
                if assessed["checks"]["accepted"]:
                    finalists += 1
                if assessed["action"] == "AUTO_APPLY":
                    if apply:
                        installed = media.apply(place, candidate, assessed, work / "images")
                        if installed:
                            place["images"]["primary"] = installed
                            # Processor paths begin images/: work root owns that directory.
                            verified = True
                        else:
                            assessed.update(action="UNRESOLVED", reason_codes=["ASSET_INSTALL_FAILED"])
                    else:
                        verified = True
                    if verified:
                        break
        if verified:
            summary["already_valid" if any(a.get("existing") and a["action"] == "AUTO_APPLY" for a in assessments) else "recovered"] += bool(required)
        elif required:
            summary["still_unresolved"] += 1
        summary["rejected_candidates"] += sum(a["action"] == "REJECT" for a in assessments)
        from .identity_assurance import compact_identity
        assessment["media"] = {"verified": verified, "identity_hash": digest(compact_identity(place)) if verified else None,
                               "reason_codes": [] if verified else ["CORE_MEDIA_UNRESOLVED"] if required else [], "candidates": assessments,
                               "discovery_attempted": discovery_attempted, "discovered_candidates": discovered_count}
        if required:
            media_rows.append({"place_id": pid, "name": place["name"], "verified": verified,
                               "final_action": "AUTO_APPLY" if verified else "UNRESOLVED", "candidates": assessments})
        if "description" not in locked and not place.get("description") and place.get("tier") in {"core_destination", "recommended"} and evidence["description_evidence"]:
            result = extract_description(place, evidence["description_evidence"][0], router)
            decisions.append({"place_id": pid, "field": "description", **result})
            if result["action"] == "AUTO_APPLY":
                if apply:
                    place["description"] = result["value"]
                field_provenance.append({"place_id": pid, **result["provenance"]})
                summary["descriptions_recovered"] += 1
        if "opening_hours" not in locked and not place.get("opening_hours", {}).get("normalized") and evidence["hours_evidence"]:
            # Sources may disagree: do not silently take whichever appears first.
            texts = {e["text"] for e in evidence["hours_evidence"]}
            result = extract_hours(place, evidence["hours_evidence"][0], router, cfg.get("hours_freshness_days", 90)) if len(texts) == 1 else {"action": "REVIEW", "reason_codes": ["HOURS_SOURCE_CONFLICT"], "evidence": evidence["hours_evidence"]}
            decisions.append({"place_id": pid, "field": "opening_hours", **result})
            if result["action"] == "AUTO_APPLY":
                if apply:
                    place["opening_hours"] = result["value"]
                field_provenance.append({"place_id": pid, **result["provenance"]})
                summary["hours_recovered"] += 1
        if pools and not required and not place.get("images", {}).get("primary"):
            selected = pools.choose(place)
            if selected:
                decisions.append({"place_id": pid, "field": "images.primary", "action": "AUTO_APPLY", "image_type": "fallback", "asset_id": selected["id"]})
                if apply:
                    place["images"]["primary"] = pools.apply(place, work)
        assurance[pid] = assessment
    # Source pack is read-only; simulate metrics separately from actual exported metrics.
    after = usability(places, city, work if apply else source_pack, assurance)
    if apply:
        # Existing real assets are referenced from the original release until final bundling.
        for place in places:
            image = place.get("images", {}).get("primary")
            if image and image.get("image_type", "real") == "real" and not local_asset(work, image.get("local_path")):
                import shutil
                for rel in (image.get("local_path"), image.get("thumbnail_path")):
                    source_asset = local_asset(source_pack, rel)
                    if source_asset:
                        target = work / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source_asset, target)
        after = usability(places, city, work, assurance)
    report = {"city": context, "mode": "APPLY" if apply else "DRY_RUN", "source_pack": str(source_pack),
              "summary": dict(summary), "ai_usage": router.report(), "identity_conflicts": identities,
              "decisions": decisions, "field_provenance": field_provenance, "assurance": assurance,
              "media_assurance": media_rows, "usability_before": before, "usability_after": after,
              "fallback_before": fallback_distribution(original), "fallback_after": fallback_distribution(places),
              "fallback_strategy": strategy, "retired_factory_fallbacks": retired,
              "fallback_authoring": authoring, "source_requests_enabled": allow_network,
              "local_intelligence": {**dict(media.stats), "ranker": dict(media.ranker.stats),
                                     "groq_calls": router.stats["groq_calls"], "gemini_calls": router.stats["gemini_calls"]},
              "source_research_places": index.network_researches, "network_media_discovery_places": network_discoveries,
              "dry_run_predictions": {"AUTO_APPLY": sum(d.get("action") == "AUTO_APPLY" for d in decisions) + summary["recovered"],
                                      "REVIEW": sum(d.get("action") == "REVIEW" for d in decisions) + len(identities),
                                      "UNRESOLVED": summary["still_unresolved"],
                                      "vision_jobs_needed": summary["REAL_REQUIRED"]-summary["already_valid"],
                                      "gemini_escalations_upper_bound": router.config.limits.get("escalations", 5)}}
    if apply:
        if len({p["id"] for p in places}) != len(places):
            raise ValueError("Severe anomaly: duplicate published IDs require reviewed migration")
        from .offline_export import export_offline
        output, actual_usability = export_offline(source_pack, source_pack.parent / output_version, places, work, report)
        report["output_pack"] = str(output)
        report["usability_after"] = actual_usability
    from ..research.export import make_tasks
    inventory = make_tasks(places, city, Path(report.get("output_pack", source_pack)), assurance, include_optional=True)
    report["research_inventory"] = inventory
    report["research_tasks"] = [task for task in inventory if task["priority"] in {"P0", "P1", "P2"}]
    report["research_worthiness_summary"] = dict(Counter(task["research_worthiness"] for task in inventory))
    report["research_handoff_count"] = len(report["research_tasks"])
    name = "ai_repair" if apply else "ai_repair_dry_run"
    atomic_json(report_dir / f"{name}.json", report)
    atomic_json(report_dir / "media_assurance.json", media_rows)
    atomic_json(report_dir / "usability.json", report["usability_after"])
    report_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {city['name']} AI Repair {'Apply' if apply else 'Dry Run'}", "", f"Published: {len(places)}",
             f"REAL_REQUIRED: {summary['REAL_REQUIRED']}; verified existing: {summary['already_valid']}; recovered: {summary['recovered']}; unresolved: {summary['still_unresolved']}",
             f"Usable: {report['usability_after']['overall_usable_count']} / {len(places)} ({report['usability_after']['overall_usable_percentage']}%)",
             f"SOURCE_DATA_READY: {report['usability_after']['SOURCE_DATA_READY']}",
             f"AI_MODE: {router.config.mode}; paid providers: 0; paid features: 0", "",
             "| Place ID | Name | Required photo verified | Action |", "|---|---|---|---|"]
    lines += [f"| {r['place_id']} | {r['name'].replace('|', '/')} | {r['verified']} | {r['final_action']} |" for r in media_rows]
    (report_dir / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
