"""Validate research against registered immutable tasks, then publish one new pack."""
import copy
import hashlib
import io
import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlsplit, unquote
from PIL import Image
from pydantic import ValidationError, TypeAdapter
from ..ai.router import AIRouter, digest
from ..config.settings import get_settings
from ..local_intelligence.config import LocalConfig
from ..local_intelligence.duplicates import DuplicateIndex
from ..local_intelligence.hours import validate_hours
from ..local_intelligence.media import LocalMediaRanker
from ..pipeline.geographic_assurance import coordinate_audit, geography
from ..pipeline.media_assurance import MediaAssurance, deterministic_filter, local_asset, license_allowed, media_signature
from ..pipeline.repair import human_field_locks, city_context
from ..pipeline.identity_assurance import compact_identity
from ..models.media_candidate import MediaCandidate
from ..utils.atomic import atomic_json
from ..utils.hashing import compute_sha256
from .export import snapshot, city_key, read_assurance, task_id, hours_stale
from .quality import public_source, source_quality
from .schemas import ResearchResult
from .media_evidence import ResearchMediaEvidence, metadata_conflicts
from ..utils.media_metadata import commons_filename, canonical_license, canonical_license_url
from ..pipeline.image_content import ImageContentError


class ReadOnlyRouter:
    def analyze(self, *args, **kwargs):
        return {"status": "MEDIA_VERIFICATION_REQUIRED"}

    def report(self):
        return {"AI_MODE": "FREE_ONLY", "stats": {"calls": 0, "groq_calls": 0, "gemini_calls": 0},
                "paid_providers_invoked": 0, "paid_feature_calls": 0}


def grounded_schedule(schedule, text):
    # Matching sets of tokens do not establish which times belong to which day.
    # Exact structured excerpts can; prose requires existing bounded extraction.
    return schedule == text


def safe_sources(result, place):
    rows = []
    for source in result.sources:
        row = source.model_dump(mode="json")
        row["retrieved_at"] = source.retrieved_at.isoformat()
        quality, confidence = source_quality(row, place)
        if quality == "UNKNOWN":
            continue
        if hours_stale({"retrieved_at": row["retrieved_at"]}, 36500):
            continue
        row.pop("claimed_quality", None)
        row.update(quality=quality, confidence=confidence)
        rows.append(row)
    return rows


def local_file(root, relative):
    if not relative or Path(relative).is_absolute():
        return None
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size > 20_000_000:
        return None
    return path


def image_pool(place, pack, threshold):
    pool = DuplicateIndex(threshold)
    images = place.get("images", {})
    for image in [images.get("primary"), *images.get("gallery", [])]:
        if image and image.get("image_type", "real") == "real":
            path = local_asset(pack, image.get("local_path"))
            if path and path.stat().st_size <= 20_000_000:
                pool.check(path.read_bytes())
    return pool


def evaluate_image(result, place, sources, media, file_root, *, apply, allow_network, pool, evidence=None):
    payload = result.result
    if not all((payload.source_page_url, payload.creator, payload.license, payload.license_url, payload.attribution)):
        return {"action": "REVIEW", "reason_codes": ["IMAGE_LICENSE_OR_ATTRIBUTION_MISSING"]}
    if not re.fullmatch(r"[A-Za-z0-9_-]+", place["id"]):
        return {"action": "REJECT", "reason_codes": ["UNSAFE_PUBLISHED_PLACE_ID"]}
    legal_url = canonical_license_url(payload.license_url) or payload.license_url
    if not canonical_license(payload.license, payload.license_url) or not public_source(legal_url):
        return {"action": "REVIEW", "reason_codes": ["IMAGE_LICENSE_INVALID"]}
    if not public_source(payload.source_page_url) or not any(s.get("url") == payload.source_page_url for s in sources):
        return {"action": "REVIEW", "reason_codes": ["IMAGE_SOURCE_INVALID"]}
    filename = commons_filename(payload.source_page_url, source_url=True)
    if not filename:
        return {"action": "REVIEW", "reason_codes": ["ORIGINAL_SOURCE_UNSUPPORTED"]}
    info = media.commons.get_image_info(filename) if apply and allow_network else media.commons.cached_image_info(filename)
    if not info:
        return {"action": "REVIEW", "reason_codes": ["ORIGINAL_SOURCE_LICENSE_UNVERIFIED"]}
    conflicts = metadata_conflicts(payload, info)
    if conflicts:
        return {"action": "REVIEW", "reason_codes": ["ORIGINAL_SOURCE_METADATA_CONFLICT"], "conflicting_fields": conflicts}
    if evidence:
        candidate, merged = evidence.merge(place, payload, info)
        if candidate is None:
            return {"action": "REVIEW", **merged}
    else:
        candidate, merged = MediaCandidate.from_commons(info, "research_import", .95), {"reason_codes": []}
    path = local_file(file_root, payload.local_file) if payload.local_file else None
    if payload.local_file and path is None:
        return {"action": "REVIEW", "reason_codes": ["LOCAL_IMAGE_MISSING_OR_UNSAFE"]}
    checks = deterministic_filter(candidate)
    if not checks["accepted"]:
        return {"action": "REJECT", "reason_codes": checks["reason_codes"]}
    content = path.read_bytes() if path else media.download(candidate)
    download = media.download_details.get(candidate.media_url, {})
    if content is None:
        return {"action": "REVIEW", "reason_codes": ["MEDIA_DOWNLOAD_OR_VERIFICATION_REQUIRED", *download.get("reason_codes", [])],
                "evidence_merge": merged, "download": download, "candidate": candidate.model_dump()}
    original_sha = hashlib.sha256(content).hexdigest()
    source_bytes_verified = path is None
    if path and apply and allow_network and candidate.match_method == "wikidata_p18":
        remote = media.download(candidate)
        source_bytes_verified = remote is not None and hashlib.sha256(remote).hexdigest() == original_sha
    try:
        content, normalized = media.normalize(content)
    except ImageContentError as exc:
        return {"action": "REJECT", "reason_codes": [str(exc)], "candidate": candidate.model_dump()}
    checks = deterministic_filter(candidate, content)
    if not checks["accepted"]:
        return {"action": "REJECT", "reason_codes": checks["reason_codes"], "checks": checks, "candidate": candidate.model_dump()}
    reuse = evidence.existing(place, candidate, content, original_sha256=original_sha) if evidence else {}
    if reuse.get("conflict"):
        return {"action": "REVIEW", "reason_codes": ["DUPLICATE_IMAGE", reuse["conflict"]] if reuse["conflict"].startswith("DUPLICATE") else [reuse["conflict"]],
                "other_place_ids": reuse.get("other_place_ids", []), "candidate": candidate.model_dump(), "checks": checks}
    if not evidence:
        duplicate = pool.check(content)
        if duplicate["duplicate"]:
            return {"action": "REVIEW", "reason_codes": ["DUPLICATE_IMAGE"], "duplicate": duplicate["method"]}
    trusted_reuse = reuse.get("verified_identity")
    if trusted_reuse and not info.get("attribution") and reuse["asset"]["image"].get("attribution"):
        candidate.attribution = reuse["asset"]["image"]["attribution"]
    if trusted_reuse and reuse["asset"]["image"].get("match_method") == "verified_human_curation":
        candidate.match_method = "verified_human_curation"
    local = None
    deterministic_identity = trusted_reuse or candidate.match_method == "wikidata_p18" and source_bytes_verified
    if (path is None or normalized) and apply and not deterministic_identity:
        path = media.work_dir / "analysis" / (hashlib.sha256(content).hexdigest() + ".webp")
        path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(io.BytesIO(content)) as image:
            image = image.convert("RGB")
            image.thumbnail((media.ranker.config.local_media_thumbnail_size,)*2)
            image.save(path, "WEBP", quality=85)
    if path and not deterministic_identity:
        ranked = media.ranker.rank(place, media.city, [(candidate, path)], persist=apply)
        if ranked:
            local = ranked[0]["local"]
    assessed = media.assess(place, candidate, content, local=local, existing_verification=trusted_reuse,
                           source_bytes_verified=source_bytes_verified)
    decision = {k: assessed[k] for k in ("action", "reason_codes", "checks", "local", "ai", "unmet_requirements", "candidate") if k in assessed}
    decision.update(evidence_merge=merged, download=download, original_content_sha256=original_sha)
    if normalized:
        decision["normalization"] = normalized
    decision["reason_codes"] = list(dict.fromkeys([*decision["reason_codes"], *merged.get("reason_codes", []), *normalized, *download.get("reason_codes", [])]))
    if reuse.get("asset"):
        decision["reuse"] = {"existing_local_path": reuse["asset"]["image"]["local_path"], "same_poi": True}
        decision["reason_codes"].append("EXISTING_ASSET_REUSE")
    if local and local.get("confidence") in {"AMBIGUOUS", "LOW", "UNCALIBRATED"} and assessed["action"] == "REVIEW":
        decision["reason_codes"].append("LOCAL_ASSURANCE_AMBIGUOUS")
    if assessed["action"] == "AUTO_APPLY":
        if evidence:
            evidence.register(place, candidate, content, original_sha)
        if apply:
            image = (evidence.install(reuse["asset"], candidate, assessed, media.work_dir) if reuse.get("asset")
                     else media.apply(place, candidate, assessed, media.work_dir / "images", content=content))
            if not image:
                return {"action": "REVIEW", "reason_codes": ["ASSET_INSTALL_FAILED"]}
            decision.update(field="images.primary", value=image)
            if reuse.get("asset"):
                media.stats["existing_assets_reused"] += 1
        else:
            decision.update(field="images.primary", value=None)
    return decision


def evaluate(result, task, place, city, media, file_root, locks, *, apply, allow_network, pool, evidence=None):
    sources = safe_sources(result, place)
    base = {"sources": sources}
    if result.status != "FOUND":
        return {**base, "action": "REVIEW" if result.status in {"PARTIAL", "CONFLICT"} else "UNRESOLVED",
                "reason_codes": [f"RESEARCH_{result.status}"]}
    if not sources:
        return {**base, "action": "REVIEW", "reason_codes": ["INVALID_OR_MISSING_SOURCE"]}
    locked = locks.get(place["id"], set())
    field = {"OPENING_HOURS": "opening_hours", "REAL_PRIMARY_IMAGE": "images", "WEBSITE": "website",
             "DESCRIPTION": "description", "COORDINATE_RESEARCH": "latitude", "IDENTITY_RESEARCH": "external_ids"}[result.type]
    if field in locked or result.type == "COORDINATE_RESEARCH" and {"location", "longitude"} & locked:
        return {**base, "action": "REVIEW", "reason_codes": ["HUMAN_FIELD_LOCK"]}
    payload = result.result
    if result.type == "REAL_PRIMARY_IMAGE":
        return {**base, **evaluate_image(result, place, sources, media, file_root, apply=apply, allow_network=allow_network, pool=pool, evidence=evidence)}
    if result.type == "IDENTITY_RESEARCH":
        return {**base, "action": "REVIEW", "reason_codes": ["PUBLISHED_IDENTITY_REQUIRES_REVIEW"]}
    if result.type == "COORDINATE_RESEARCH":
        evidence = []
        ids = place.get("external_ids", {})
        for point in payload.coordinate_sources:
            row = point.model_dump(mode="json")
            source = next((s for s in sources if s.get("url") == row["source_url"] and s.get("source_id") == row["source_id"]), None)
            if source is None or source["confidence"] < .90:
                continue
            host = urlparse(row["source_url"]).hostname
            provider = "wikidata" if host == "www.wikidata.org" else "openstreetmap" if host in {"www.openstreetmap.org", "openstreetmap.org"} else "official_website" if source["quality"] == "OFFICIAL" else None
            key = {"wikidata": "wikidata_id", "openstreetmap": "osm_id"}.get(provider)
            matched = bool(key and ids.get(key) == row["source_id"])
            if provider:
                evidence.append({**row, "source": provider, "identity_match": matched})
        audit = coordinate_audit(place, evidence)
        proposed = {**place, "location": {**place["location"], **{k: v for k, v in audit.get("replacement", {}).items() if k in {"latitude", "longitude"}}}}
        if audit.get("replacement") and audit["action"] == "AUTO_APPLY" and geography(proposed, city)["status"] == "VALID":
            return {**base, "action": "AUTO_APPLY", "field": "location", "value": proposed["location"], "reason_codes": ["INDEPENDENT_COORDINATES_CORROBORATED"]}
        return {**base, "action": "REVIEW", "reason_codes": ["COORDINATE_CORROBORATION_OR_REGION_REVIEW"], "coordinate": audit}
    source = max(sources, key=lambda s: s["confidence"])
    if result.type == "OPENING_HOURS":
        schedule = payload.opening_hours
        validation = validate_hours(schedule)
        if not validation["valid"]:
            return {**base, "action": "REVIEW", "reason_codes": ["INVALID_SCHEDULE" if validation["status"] == "INVALID" else "HOURS_VALIDATOR_UNAVAILABLE"]}
        source = next((s for s in sources if (payload.source_url and s.get("url") == payload.source_url)
                       or not payload.source_url and s.get("source_id")), None)
        if source is None or not payload.source_text or not payload.source_name or not payload.retrieved_at:
            return {**base, "action": "REVIEW", "reason_codes": ["HOURS_SOURCE_METADATA_MISSING"]}
        date = payload.retrieved_at.isoformat()
        if source["retrieved_at"] != date or source["source_text"] != payload.source_text:
            return {**base, "action": "REVIEW", "reason_codes": ["HOURS_SOURCE_TEXT_NOT_CORROBORATED"]}
        if hours_stale({"retrieved_at": date}, LocalConfig().hours_research_max_age_days):
            return {**base, "action": "REVIEW", "reason_codes": ["RECHECK_RECOMMENDED"]}
        if not grounded_schedule(schedule, payload.source_text):
            if validate_hours(payload.source_text)["valid"]:
                return {**base, "action": "REVIEW", "reason_codes": ["HOURS_SOURCE_SCHEDULE_CONFLICT"]}
            if not apply or source["confidence"] < .90:
                return {**base, "action": "REVIEW", "reason_codes": ["HOURS_GROUNDED_EXTRACTION_REQUIRED"]}
            from ..pipeline.metadata_assurance import extract_hours
            host = urlparse(source.get("url") or "").hostname
            provider = "wikidata" if host == "www.wikidata.org" else "openstreetmap" if host in {"openstreetmap.org", "www.openstreetmap.org"} else "official_website"
            extracted = extract_hours(place, {"source": provider, "source_id": source.get("source_id") or source.get("url"),
                "source_url": source.get("url"), "text": payload.source_text, "retrieved_at": date},
                media.router, LocalConfig().hours_research_max_age_days)
            if extracted["action"] != "AUTO_APPLY" or extracted["value"]["normalized"] != schedule:
                return {**base, "action": "REVIEW", "reason_codes": ["HOURS_SOURCE_TEXT_NOT_CORROBORATED"]}
        value = {"raw": payload.source_text, "normalized": schedule, "source": source["source_name"],
                 "retrieved_at": date, "confidence": source["confidence"], "verified": True, "conflicts": []}
    elif result.type == "DESCRIPTION":
        value = payload.description
        if not value or len(value) < 15 or value not in source["source_text"]:
            return {**base, "action": "REVIEW", "reason_codes": ["DESCRIPTION_NOT_SOURCE_EXCERPT"]}
    else:
        value = payload.website
        if not public_source(value) or value not in source["source_text"]:
            return {**base, "action": "REVIEW", "reason_codes": ["WEBSITE_NOT_SOURCE_SUPPORTED"]}
    if source["confidence"] < .90:
        return {**base, "action": "REVIEW", "reason_codes": ["SOURCE_QUALITY_REQUIRES_REVIEW"]}
    return {**base, "action": "AUTO_APPLY", "field": "contact.website" if result.type == "WEBSITE" else field,
            "value": value, "confidence": source["confidence"], "reason_codes": ["SOURCE_GROUNDED_LOCAL_VALIDATION"]}


def import_research(file: Path, *, apply=False, settings=None, **kwargs):
    settings = settings or get_settings()
    if not apply:
        return _import_research(file, apply=False, settings=settings, **kwargs)
    root = settings.data_dir / "research"
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".import-lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError("Another research import is active; retry after it completes") from None
    try:
        return _import_research(file, apply=True, settings=settings, **kwargs)
    finally:
        lock.rmdir()


def _import_research(file: Path, *, apply=False, allow_network=False, output_version="v3-research", settings=None, router=None, media_factory=None):
    settings = settings or get_settings()
    if file.stat().st_size > 20_000_000:
        raise ValueError("Research input exceeds 20 MB limit")
    if Path(output_version).name != output_version or output_version in {".", "..", "v3"}:
        raise ValueError("Output version must be a new single directory name, never v3")
    document = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or set(document) != {"schema_version", "handoff_id", "results"} or document["schema_version"] != "1.0":
        raise ValueError("Invalid research bundle envelope")
    handoff_id = document["handoff_id"]
    if not isinstance(handoff_id, str) or not re.fullmatch(r"handoff_[a-f0-9]{24}", handoff_id):
        raise ValueError("Invalid handoff ID")
    results = document["results"]
    if not isinstance(results, list) or len(results) > 5000:
        raise ValueError("Results must be a list of at most 5000 tasks")
    registry_file = settings.data_dir / "research" / "handoffs" / f"{handoff_id}.json"
    if not registry_file.is_file():
        raise ValueError("Unknown handoff ID; export tasks from this workspace first")
    registry = json.loads(registry_file.read_text(encoding="utf-8"))
    pack = (settings.releases_dir / registry["source_pack"]).resolve()
    if not pack.is_relative_to(settings.releases_dir.resolve()):
        raise ValueError("Invalid registered source pack")
    input_hash = compute_sha256(file)
    history_file = settings.data_dir / "research" / "imports" / f"{digest([handoff_id, input_hash])}.json"
    if history_file.is_file():
        prior = json.loads(history_file.read_text(encoding="utf-8"))
        if prior.get("summary", {}).get("applied"):
            return {**prior, "mode": "APPLY" if apply else "DRY_RUN", "already_applied": True}
    # Recovery if publication succeeded but writing the auxiliary history index failed.
    for previous in pack.parent.glob("*/research_import.json"):
        prior = json.loads(previous.read_text(encoding="utf-8"))
        if prior.get("input_sha256") == input_hash and prior.get("handoff_id") == handoff_id and prior.get("summary", {}).get("applied"):
            if apply:
                atomic_json(history_file, prior)
                _write_head(settings, registry["city"], previous.parent)
            return {**prior, "already_applied": True}
    if snapshot(pack) != registry["snapshot"]:
        raise ValueError("Source snapshot changed; export a new handoff before importing")
    city = json.loads((pack / "city.json").read_text(encoding="utf-8"))
    if {k: city[k] for k in ("id", "name", "state", "country")} != registry["city"]:
        raise ValueError("Registered city context mismatch")
    head_file = settings.data_dir / "research" / "heads" / f"{city_key(city)}.json"
    if head_file.exists():
        head = json.loads(head_file.read_text(encoding="utf-8"))
        if head["output_pack"] != registry["source_pack"]:
            raise ValueError("A newer research pack exists; re-export to avoid overwriting prior research")
    places = json.loads((pack / "places.json").read_text(encoding="utf-8"))
    if len({p["id"] for p in places}) != len(places):
        raise ValueError("Published ID collision requires review before research import")
    by_id = {p["id"]: p for p in places}
    tasks = {task["task_id"]: task for task in registry["tasks"]}
    locks = human_field_locks(settings, city)
    work = settings.staging_dir / "research" / uuid.uuid4().hex
    local_config = LocalConfig()
    if not apply:
        local_config = local_config.model_copy(update={"local_media_allow_download": False})
    selected_router = router if apply and router is not None else AIRouter(city_context(city), settings.cache_dir / "ai") if apply else ReadOnlyRouter()
    media = (media_factory or MediaAssurance)(city, selected_router, work, apply and allow_network,
            ranker=LocalMediaRanker(settings.cache_dir / "local_media", local_config), read_only=not apply)
    assurance = copy.deepcopy(read_assurance(pack))
    evidence = ResearchMediaEvidence(places, assurance, pack, allow_network=apply and allow_network,
                                    threshold=local_config.local_duplicate_threshold)
    provenance_file = pack / "field_provenance.json"
    provenance = json.loads(provenance_file.read_text(encoding="utf-8")) if provenance_file.is_file() else []
    report = {"schema_version": "1.0", "handoff_id": handoff_id, "input_sha256": input_hash,
              "imported_at": datetime.now(timezone.utc).isoformat(), "mode": "APPLY" if apply else "DRY_RUN",
              "city": registry["city"], "source_pack": registry["source_pack"], "decisions": []}
    seen_tasks, pools = set(), {}
    adapter = TypeAdapter(ResearchResult)
    counts = Counter(tasks_supplied=len(results), matched=0, valid=0, auto_applicable=0, review=0,
                     rejected=0, missing_pois=0, invalid_sources=0, invalid_schedules=0,
                     media_requiring_verification=0, applied=0, unresolved=0)
    for raw in results:
        # Only IDs/types/reasons from malformed inputs enter reports; no raw secret-bearing payloads.
        record = {k: raw.get(k) for k in ("task_id", "place_id", "type")} if isinstance(raw, dict) else {}
        try:
            result = adapter.validate_json(json.dumps(raw))
        except (ValidationError, ValueError, TypeError):
            record.update(action="REJECT", reason_codes=["INVALID_RESULT_SCHEMA"])
        else:
            task = tasks.get(result.task_id)
            place = by_id.get(result.place_id)
            if place is None:
                counts["missing_pois"] += 1
                record.update(action="REJECT", reason_codes=["UNKNOWN_PLACE_ID"])
            elif (task is None or task["place_id"] != result.place_id or task["type"] != result.type
                  or task_id(city, result.place_id, result.type) != result.task_id or result.task_id in seen_tasks):
                record.update(action="REJECT", reason_codes=["TASK_ID_OR_PLACE_ID_MISMATCH_OR_DUPLICATE"])
            else:
                seen_tasks.add(result.task_id)
                counts["matched"] += 1
                if place["id"] not in pools:
                    pools[place["id"]] = image_pool(place, pack, local_config.local_duplicate_threshold)
                decision = evaluate(result, task, place, city, media, file.parent, locks, apply=apply,
                                    allow_network=allow_network, pool=pools[place["id"]], evidence=evidence)
                record.update(decision)
                counts["valid"] += record["action"] != "REJECT"
                counts["invalid_sources"] += any("SOURCE" in code and any(v in code for v in ("INVALID", "MISSING", "UNSUPPORTED", "UNVERIFIED")) for code in record["reason_codes"])
                counts["invalid_schedules"] += "INVALID_SCHEDULE" in record["reason_codes"]
                counts["media_requiring_verification"] += result.type == "REAL_PRIMARY_IMAGE" and record["action"] == "REVIEW"
                if record["action"] == "AUTO_APPLY":
                    counts["auto_applicable"] += 1
                    if apply:
                        field = record["field"]
                        if "." in field:
                            parent, key = field.split(".", 1)
                            place[parent][key] = record["value"]
                        else:
                            place[field] = record["value"]
                        if field == "images.primary":
                            assurance.setdefault(place["id"], {})["media"] = {"verified": True, "reason_codes": [],
                                "identity_hash": digest(compact_identity(place)),
                                "verification_hash": media_signature(work, place["images"]["primary"]), "candidates": [record]}
                        if field == "location":
                            assessment = assurance.setdefault(place["id"], {})
                            assessment.update(coordinate={"status": "CORROBORATED", "action": "AUTO_APPLY"}, geography=geography(place, city))
                        provenance.append({"place_id": place["id"], "field": field, "task_id": result.task_id,
                                           "input_sha256": input_hash, "sources": record["sources"],
                                           "value": record["value"], "retrieved_at": record["sources"][0]["retrieved_at"]})
                        counts["applied"] += 1
        counts[{"REVIEW": "review", "REJECT": "rejected", "UNRESOLVED": "unresolved"}.get(record["action"], "accepted")] += 1
        report["decisions"].append(record)
    report.update(summary=dict(counts), ai_usage=selected_router.report(),
                  local_intelligence={**dict(media.stats), "ranker": dict(media.ranker.stats)})
    if apply and counts["applied"]:
        from ..pipeline.offline_export import export_offline
        pack_report = {"assurance": assurance, "field_provenance": provenance,
                       "ai_usage": report["ai_usage"], "research_import": report,
                       "fallback_strategy": json.loads((pack / "manifest.json").read_text(encoding="utf-8")).get("fallback_presentation", {}).get("strategy", "app")}
        output, _ = export_offline(pack, pack.parent / output_version, places, work, pack_report)
        report["output_pack"] = str(output)
        atomic_json(history_file, report)
        _write_head(settings, city, output)
    elif apply:
        atomic_json(history_file, report)
    return report


def _write_head(settings, city, output):
    atomic_json(settings.data_dir / "research" / "heads" / f"{city_key(city)}.json",
                {"output_pack": output.resolve().relative_to(settings.releases_dir.resolve()).as_posix(), "snapshot": snapshot(output)})
