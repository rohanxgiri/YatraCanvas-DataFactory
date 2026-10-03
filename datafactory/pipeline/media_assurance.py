import hashlib
import io
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import httpx
from collections import Counter
from PIL import Image, ImageOps
from ..models.media_candidate import MediaCandidate
from ..sources.wikimedia import WikimediaCommonsClient
from ..sources.openverse import OpenverseClient
from ..utils.atomic import atomic_json
from .identity_assurance import compact_identity


def license_allowed(value: str) -> bool:
    value = re.sub(r"[\s_-]+", " ", value.strip()).upper()
    return bool(re.fullmatch(r"(?:CC BY(?: SA)?(?: (?:1\.0|2\.0|2\.5|3\.0|4\.0))?|CC0(?: 1\.0)?|PUBLIC DOMAIN(?: MARK(?: 1\.0)?)?)", value))


def public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.port in {None, 443}
    except ValueError:
        return False


def deterministic_filter(candidate: MediaCandidate, content: bytes | None = None, seen=None):
    reasons = []
    if not public_url(candidate.media_url) or not public_url(candidate.source_url):
        reasons.append("MEDIA_URL_INVALID")
    if candidate.mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        reasons.append("MIME_UNSUPPORTED")
    if candidate.width < 350 or candidate.height < 250:
        reasons.append("IMAGE_TOO_SMALL")
    elif not 0.35 <= candidate.width / candidate.height <= 3:
        reasons.append("EXTREME_ASPECT_RATIO")
    if not license_allowed(candidate.license):
        reasons.append("LICENSE_UNSUPPORTED")
    if not candidate.license_url or not public_url(candidate.license_url):
        reasons.append("LICENSE_URL_MISSING")
    if not candidate.creator or candidate.creator.strip().lower() in {"unknown", "anonymous", "n/a"} or not candidate.attribution:
        reasons.append("ATTRIBUTION_MISSING")
    if re.search(r"\b(logo|map|locator|diagram|poster|document|flag|icon|coat of arms)\b", candidate.title.lower()):
        reasons.append("NOT_PHOTOGRAPH_CANDIDATE")
    hashes = {}
    if content is not None:
        if len(content) > 20_000_000:
            return {"accepted": False, "reason_codes": ["IMAGE_BYTES_EXCEEDED"]}
        hashes["sha256"] = hashlib.sha256(content).hexdigest()
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.width * image.height > 40_000_000:
                    raise ValueError("Image exceeds decode budget")
                image.load()
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    reasons.append("ACTUAL_MIME_UNSUPPORTED")
                w, h = image.size
                if w < 350 or h < 250:
                    reasons.append("ACTUAL_IMAGE_TOO_SMALL")
                elif not 0.35 <= w / h <= 3:
                    reasons.append("ACTUAL_ASPECT_RATIO")
                if seen is not None and hashes["sha256"] not in seen:
                    from ..local_intelligence.duplicates import fingerprints
                    hashes.update(fingerprints(content))
                hashes["dimensions"] = [w, h]
        except Exception:
            reasons.append("IMAGE_DECODE_FAILED")
        if seen is not None:
            if hashes.get("sha256") in seen or (hashes.get("dhash") not in {None, "0000000000000000", "ffffffffffffffff"} and hashes.get("dhash") in seen):
                reasons.append("DUPLICATE_IMAGE")
            if not reasons:
                seen.add(hashes["sha256"])
                if hashes.get("dhash"):
                    seen.add(hashes["dhash"])
    return {"accepted": not reasons, "reason_codes": sorted(set(reasons)), **hashes}


def local_asset(root: Path, relative: str | None):
    if not relative:
        return None
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        return None
    return path


def media_signature(root, image):
    """Tie a verification to the actual bundled assets and legal/source metadata."""
    from ..ai.router import digest
    from ..utils.hashing import compute_sha256
    paths = [local_asset(root, image.get(key)) for key in ("local_path", "thumbnail_path")]
    if not all(paths):
        return None
    metadata = {key: image.get(key) for key in ("source", "source_page", "original_file", "author",
                "license", "license_url", "attribution", "match_method")}
    return digest([metadata, [compute_sha256(path) for path in paths]])


class MediaAssurance:
    def __init__(self, city: dict, router, work_dir: Path, allow_network=False, commons=None, openverse=None, ranker=None, read_only=False):
        self.city, self.router, self.work_dir, self.allow_network = city, router, work_dir, allow_network
        self.commons = commons or WikimediaCommonsClient(read_only=read_only)
        self.openverse = openverse or OpenverseClient(read_only=read_only)
        from ..local_intelligence.media import LocalMediaRanker
        self.ranker = ranker or LocalMediaRanker(work_dir / "local_scores")
        self.stats = Counter()

    def prepare(self, place, candidates):
        """Validate and deduplicate bounded candidates before local ranking/cloud AI."""
        from ..local_intelligence.duplicates import DuplicateIndex
        pool = DuplicateIndex(self.ranker.config.local_duplicate_threshold)
        valid, rejected = [], []
        self.stats["candidates_discovered"] += len(candidates)
        if not candidates:
            self.stats["zero_candidate_handoffs"] += 1
            return [], []
        for candidate in candidates[:self.ranker.config.local_media_max_candidates]:
            checks = deterministic_filter(candidate)
            content = self.download(candidate) if checks["accepted"] else None
            if content is not None:
                checks = deterministic_filter(candidate, content)
                if checks["accepted"]:
                    duplicate = pool.check(content)
                    if duplicate["duplicate"]:
                        self.stats["duplicates_removed"] += 1
                        checks.update(accepted=False, reason_codes=["DUPLICATE_IMAGE"], duplicate=duplicate)
            if not checks["accepted"] or content is None:
                rejected.append({"candidate": candidate.model_dump(), "checks": checks,
                                 "action": "REJECT" if not checks["accepted"] else "UNRESOLVED",
                                 "reason_codes": checks["reason_codes"] or ["DOWNLOAD_UNAVAILABLE"]})
                continue
            qid = place.get("external_ids", {}).get("wikidata_id") or place.get("wikidata_id")
            if qid and candidate.related_entity_id and candidate.related_entity_id != qid:
                rejected.append({"candidate": candidate.model_dump(), "checks": checks, "action": "REJECT",
                                 "reason_codes": ["CONTRADICTORY_ENTITY_EVIDENCE"]})
                self.stats["entity_contradiction_rejections"] += 1
                continue
            # Analysis copies are small; originals stay in the existing download cache.
            path = self.work_dir / "analysis" / (hashlib.sha256(content).hexdigest() + ".webp")
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(io.BytesIO(content)) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((self.ranker.config.local_media_thumbnail_size,)*2)
                    image.save(path, "WEBP", quality=85)
            valid.append((candidate, path))
        self.stats["potential_cloud_checks"] += len(valid)
        self.stats["deterministic_rejections"] += sum(row["action"] == "REJECT" for row in rejected)
        ranked = self.ranker.rank(place, self.city, valid)
        self.stats["siglip_ranked"] += sum(r["local"].get("status") in {"OK", "CACHE_HIT"} for r in ranked)
        return ranked, rejected

    def _discovery_path(self, place, source_evidence):
        from ..ai.router import digest
        identity = {"place": compact_identity(place), "city": {k: self.city.get(k) for k in ("id", "name", "state", "country", "bbox", "center")}, "source_evidence": source_evidence}
        return self.work_dir / "discovery" / f"{digest(identity)}.json"

    def cached_discovery(self, place, source_evidence):
        path = self._discovery_path(place, source_evidence)
        if path.exists():
            import json
            from ..config.settings import get_settings
            try:
                candidates = [MediaCandidate.model_validate(c) for c in json.loads(path.read_text(encoding="utf-8"))]
                ttl = get_settings().cache_ttl_seconds if candidates else 3600
                if time.time() - path.stat().st_mtime <= ttl:
                    return candidates
            except (ValueError, OSError):
                pass
        return None

    def discover(self, place: dict, source_evidence: dict) -> list[MediaCandidate]:
        discovery_path = self._discovery_path(place, source_evidence)
        cached = self.cached_discovery(place,source_evidence)
        if cached is not None:
            return cached
        found = []
        qid = place.get("external_ids", {}).get("wikidata_id") or place.get("wikidata_id")
        def add(filename, method, confidence):
            if not filename:
                return
            info = self.commons.get_image_info(filename) if self.allow_network else self.commons.cache.get(f"img_{filename.removeprefix('File:')}")
            if isinstance(info, dict):
                found.append(MediaCandidate.from_commons(info, method, confidence, qid))
        add(source_evidence.get("wikidata_p18"), "wikidata_p18", 0.99)
        add(source_evidence.get("commons_image"), "wikivoyage_listing_image", 0.95)
        category = source_evidence.get("commons_category")
        if category and self.allow_network:
            for filename in self.commons.search_category_images(category, limit=3):
                add(filename, "commons_category", 0.92)
        wikipedia = source_evidence.get("wikipedia_url")
        if wikipedia and self.allow_network:
            add(self.commons.get_wikipedia_lead_image(wikipedia), "wikipedia_lead", 0.94)
        if self.allow_network:
            for name in [place["name"]] + place.get("alternate_names", [])[:2]:
                add(self.commons.search_commons_image(name, self.city["name"]), "commons_contextual_search", 0.70)
            for candidate in self.openverse.search(f"{place['name']} {self.city['name']} {self.city['state']} {self.city['country']}"):
                # Commons is an approved original-license verification adapter.
                if urlparse(candidate.source_url).hostname == "commons.wikimedia.org" and "/wiki/File:" in candidate.source_url:
                    from urllib.parse import unquote
                    filename = unquote(candidate.source_url.split("/wiki/File:", 1)[1])
                    info = self.commons.get_image_info(filename)
                    if info and info.get("url") == candidate.media_url:
                        candidate = MediaCandidate.from_commons(info, "openverse_original_commons", candidate.source_confidence, qid)
                found.append(candidate)
        unique = {c.media_url: c for c in reversed(found)}
        candidates = sorted(unique.values(), key=lambda c: -c.source_confidence)
        if self.allow_network:
            atomic_json(discovery_path, [c.model_dump() for c in candidates])
        return candidates

    def download(self, candidate):
        # Restrict downloads to approved source CDNs; Openverse is a discovery index.
        allowed = {"upload.wikimedia.org", "live.staticflickr.com", "images.unsplash.com"}
        if urlparse(candidate.media_url).hostname not in allowed:
            return None
        cache_file = self.work_dir / "downloads" / (hashlib.sha256(candidate.media_url.encode()).hexdigest() + ".bin")
        if cache_file.exists():
            return cache_file.read_bytes() if cache_file.stat().st_size <= 20_000_000 else None
        if not self.allow_network:
            return None
        try:
            with httpx.Client(timeout=20, follow_redirects=False) as client:
                with client.stream("GET", candidate.media_url, headers={"User-Agent": self.commons.settings.user_agent}) as response:
                    if response.status_code != 200 or response.headers.get("content-type", "").split(";")[0] not in {"image/jpeg", "image/png", "image/webp"}:
                        return None
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 20_000_000:
                            return None
                        chunks.append(chunk)
            content = b"".join(chunks)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            temp = cache_file.with_suffix(".tmp")
            temp.write_bytes(content)
            temp.replace(cache_file)
            return content
        except (httpx.HTTPError, OSError):
            return None

    def assess(self, place: dict, candidate: MediaCandidate, content: bytes, seen=None, local=None):
        checks = deterministic_filter(candidate, content, seen)
        result = {"candidate": candidate.model_dump(), "checks": checks, "action": "REVIEW"}
        if not checks["accepted"]:
            return {**result, "action": "REJECT", "reason_codes": checks["reason_codes"]}
        if not candidate.original_license_verified:
            return {**result, "reason_codes": ["ORIGINAL_SOURCE_LICENSE_UNVERIFIED"]}
        result["local"] = local or {"status": "NOT_RUN"}
        qid = place.get("external_ids", {}).get("wikidata_id") or place.get("wikidata_id")
        if qid and candidate.related_entity_id and candidate.related_entity_id != qid:
            return {**result, "action": "REJECT", "reason_codes": ["CONTRADICTORY_ENTITY_EVIDENCE"]}
        authoritative = (qid and candidate.related_entity_id == qid and candidate.match_method == "wikidata_p18"
                         and candidate.source == "Wikimedia Commons" and candidate.source_confidence >= .98)
        if authoritative:
            self.stats["accepted_without_cloud_ai"] += 1
            self.stats["cloud_jobs_avoided"] += 1
            return {**result, "action": "AUTO_APPLY", "reason_codes": ["VERIFIED_ENTITY_LINKED_P18"], "final_confidence": .99}
        if local and local.get("non_photo_review"):
            self.stats["local_non_photo_reviews"] += 1
            return {**result, "reason_codes": ["LOCAL_NON_PHOTO_REVIEW"]}
        # Re-encode a bounded finalist to avoid sending full-resolution originals.
        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1024, 1024))
            stream = io.BytesIO()
            image.save(stream, "WEBP", quality=80)
        router_stats = getattr(self.router, "stats", {})
        before = {provider: router_stats.get(f"{provider}_calls", 0) for provider in ("groq", "gemini")}
        from .media_policy import media_policy, MediaPolicy
        important = media_policy(place) in {MediaPolicy.REAL_REQUIRED, MediaPolicy.REAL_PREFERRED}
        ai = self.router.analyze(compact_identity(place), "media_audit", candidate.model_dump(), [stream.getvalue()], important=important)
        for provider in before:
            self.stats[f"{provider}_calls"] += router_stats.get(f"{provider}_calls", 0) - before[provider]
        self.stats["cloud_verification_jobs"] += 1
        result["ai"] = ai
        if ai["status"] != "OK":
            return {**result, "reason_codes": [ai["status"]]}
        decision = ai["result"]
        safe = (decision["decision"] == "ACCEPT" and decision["confidence"] >= 0.9
                and decision["identity_match"] and decision["identity_confidence"] >= 0.9
                and decision["real_photograph"] and decision["wrong_place_risk"] <= 0.05
                and decision["landmark_prominence"] >= 0.65 and decision["mobile_card_suitability"] >= 0.7
                and not decision["watermark_or_obstruction"] and candidate.source_confidence >= 0.9)
        return {**result, "action": "AUTO_APPLY" if safe else ("REJECT" if decision["decision"] == "REJECT" else "REVIEW"),
                "reason_codes": decision["reason_codes"], "final_confidence": min(candidate.source_confidence, decision["identity_confidence"], decision["confidence"])}

    def apply(self, place: dict, candidate: MediaCandidate, assessment: dict, output_media_dir: Path, content=None):
        if assessment.get("action") != "AUTO_APPLY":
            raise ValueError("Only verified AUTO_APPLY media can be installed")
        info = candidate.processing_info()
        content = content if content is not None else self.download(candidate)
        if not content:
            return None
        info["_content"] = content
        # Reuse established WebP asset creation. It validates licensing/dimensions again.
        metadata = self.commons.download_and_process_image(info, place["id"], output_media_dir,
                    candidate.match_method, assessment["final_confidence"], refresh=False)
        if metadata:
            metadata.source = candidate.source
            metadata.content_sha256 = assessment["checks"]["sha256"]
            return metadata.model_dump()
        return None
