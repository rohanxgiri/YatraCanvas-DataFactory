"""Reuse is scoped to a POI and independently matched bytes/source evidence."""
import copy
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path
from ..ai.router import digest
from ..models.media_candidate import MediaCandidate
from ..pipeline.identity_assurance import compact_identity
from ..utils.media_metadata import commons_file_key, canonical_license, canonical_license_url, creator_key
from ..pipeline.media_assurance import local_asset, media_signature, deterministic_filter
from ..local_intelligence.duplicates import DuplicateIndex
from ..utils.cache import DiskCache


SOURCE_METHODS = {"wikidata_p18", "wikipedia_lead", "commons_category", "commons_exact_name_search",
                  "commons_alt_name_search", "wikivoyage_listing_image", "openverse_original_commons"}


def metadata_conflicts(payload, info):
    """Legal equivalence is finite; creator equivalence is NFC only."""
    return [key for key, equal in {
        "license": canonical_license(payload.license, payload.license_url) == canonical_license(info.get("license"), info.get("license_url")),
        "creator": creator_key(payload.creator) == creator_key(info.get("author")),
        "license_url": (canonical_license_url(payload.license_url) or payload.license_url) == (canonical_license_url(info.get("license_url")) or info.get("license_url")),
        "source_page_url": commons_file_key(payload.source_page_url) == commons_file_key(info.get("source_page")),
        "original_file": commons_file_key(payload.source_page_url) == commons_file_key(info.get("original_file")),
        "direct_media_url": not payload.direct_media_url or payload.direct_media_url == info.get("url"),
    }.items() if not equal]


def merge_research_media_evidence(existing_candidates, payload, info, place, *, entity=None, identity_blocked=False):
    """Existing methods survive only exact file matches; P18 needs actual QID claims."""
    conflicts = metadata_conflicts(payload, info)
    if conflicts:
        return None, {"reason_codes": ["ORIGINAL_SOURCE_METADATA_CONFLICT"], "conflicting_fields": conflicts}
    candidate = MediaCandidate.from_commons(info, "research_import", .95)
    key = commons_file_key(candidate.source_url)
    reasons, preserved = [], []
    if info.get("license") != candidate.license or info.get("license_url") != candidate.license_url:
        reasons.append("LICENSE_CANONICALIZED")
    if payload.license != candidate.license or payload.license_url != candidate.license_url:
        if "LICENSE_CANONICALIZED" not in reasons:
            reasons.append("LICENSE_CANONICALIZED")
    if payload.creator != candidate.creator or info.get("author") != candidate.creator:
        reasons.append("CREATOR_UNICODE_CANONICALIZED")
    qid = place.get("external_ids", {}).get("wikidata_id")
    for known in existing_candidates:
        if (known.source != "Wikimedia Commons" or commons_file_key(known.source_url) != key
                or commons_file_key(known.title) != key):
            continue
        if known.related_entity_id and known.related_entity_id != qid:
            return None, {"reason_codes": ["CONTRADICTORY_ENTITY_EVIDENCE"]}
        if known.match_method in SOURCE_METHODS and known.match_method != "wikidata_p18":
            preserved.append(known)
    if preserved:
        strongest = max(preserved, key=lambda c: c.source_confidence)
        candidate.match_method = strongest.match_method
        candidate.source_confidence = max(candidate.source_confidence, strongest.source_confidence)
        candidate.related_entity_id = strongest.related_entity_id
        reasons.append("EXISTING_SOURCE_METHOD_PRESERVED")
    evidence = None
    if (not identity_blocked and qid and isinstance(entity, dict) and entity.get("wikidata_id") == qid
            and commons_file_key(entity.get("p18_image")) == key):
        candidate.match_method, candidate.related_entity_id = "wikidata_p18", qid
        candidate.source_confidence = .99
        evidence = {"type": "wikidata_p18", "wikidata_id": qid, "p18_file": entity["p18_image"],
                    "source_url": f"https://www.wikidata.org/wiki/{qid}", "retrieved_at": entity.get("retrieved_at")}
        reasons.append("WIKIDATA_P18_EVIDENCE_VERIFIED")
    return candidate, {"reason_codes": reasons, "identity_evidence": evidence}


class ResearchMediaEvidence:
    def __init__(self, places, assurance, pack, *, allow_network=False, threshold=3):
        self.pack, self.assurance, self.allow_network, self.threshold = pack, assurance, allow_network, threshold
        self.images, self.known, self.qids = defaultdict(list), defaultdict(list), defaultdict(set)
        self.by_source, self.by_hash = defaultdict(set), defaultdict(set)
        self.entity_cache = DiskCache("wikidata", create=allow_network)
        self.entities, self.network_entities = {}, 0
        for place in places:
            pid = place["id"]
            qid = place.get("external_ids", {}).get("wikidata_id")
            if qid:
                self.qids[qid].add(pid)
            images = place.get("images", {})
            for image in [images.get("primary"), *images.get("gallery", [])]:
                if not image or image.get("image_type", "real") != "real":
                    continue
                path = local_asset(pack, image.get("local_path"))
                thumb = local_asset(pack, image.get("thumbnail_path"))
                key = commons_file_key(image.get("source_page")) if image.get("source") == "Wikimedia Commons" else None
                self.images[pid].append({"image": image, "path": path, "thumbnail": thumb, "source_key": key})
                if path and path.stat().st_size <= 20_000_000:
                    self.by_hash[hashlib.sha256(path.read_bytes()).hexdigest()].add(pid)
                    if key:
                        self.by_source[key].add(pid)
                    if image.get("content_sha256"):
                        self.by_hash[image["content_sha256"]].add(pid)
                if key:
                    self.known[pid].append(MediaCandidate.from_commons({
                        "source_page": image.get("source_page"), "original_file": image.get("original_file"),
                        "url": image.get("source_page"), "author": image.get("author"),
                        "license": image.get("license"), "license_url": image.get("license_url"),
                        "attribution": image.get("attribution"), "width": image.get("width") or 0,
                        "height": image.get("height") or 0, "mime": "image/webp"},
                        image.get("match_method") or "legacy", image.get("match_confidence") or 0))
            for row in assurance.get(pid, {}).get("media", {}).get("candidates", []):
                try:
                    if row.get("candidate"):
                        self.known[pid].append(MediaCandidate.model_validate(row["candidate"]))
                except ValueError:
                    pass

    def entity(self, place):
        qid = place.get("external_ids", {}).get("wikidata_id")
        if not qid or len(self.qids[qid]) != 1 or self.assurance.get(place["id"], {}).get("identity_blocker"):
            return None
        if qid not in self.entities:
            info = self.entity_cache.get(f"entity_{qid}")
            if info is None and self.allow_network and self.network_entities < 20:
                from ..sources.wikidata import WikidataEnricher
                self.network_entities += 1
                info = WikidataEnricher().get_entity_details(qid)
            self.entities[qid] = info
        return self.entities[qid]

    def merge(self, place, payload, info):
        return merge_research_media_evidence(self.known[place["id"]], payload, info, place,
            entity=self.entity(place), identity_blocked=bool(self.assurance.get(place["id"], {}).get("identity_blocker")))

    def existing(self, place, candidate, content, *, original_sha256=None):
        pid, key = place["id"], commons_file_key(candidate.source_url)
        sha = hashlib.sha256(content).hexdigest()
        other = (self.by_source.get(key, set()) | self.by_hash.get(sha, set())
                 | self.by_hash.get(original_sha256, set())) - {pid}
        if other:
            return {"conflict": "DUPLICATE_OTHER_POI", "other_place_ids": sorted(other)}
        reusable, other_pool = [], DuplicateIndex(self.threshold)
        for entry in self.images[pid]:
            path = entry["path"]
            if not path or path.stat().st_size > 20_000_000:
                continue
            local = path.read_bytes()
            same_bytes = hashlib.sha256(local).hexdigest() == sha
            probe = DuplicateIndex(self.threshold)
            probe.check(local)
            same_source = entry["source_key"] == key and key is not None
            # Perceptual equality is supporting evidence only when the exact
            # independently verified Commons file also matches.
            if same_bytes or same_source and probe.check(content, add=False)["duplicate"]:
                reusable.append(entry)
            else:
                other_pool.check(local)
        if other_pool.check(content, add=False)["duplicate"]:
            return {"conflict": "DUPLICATE_OTHER_ASSET"}
        for entry in reusable:
            thumb = entry["thumbnail"]
            if not thumb or thumb.stat().st_size > 20_000_000:
                continue
            # Reused primary bytes must independently pass current image checks.
            if not deterministic_filter(candidate, entry["path"].read_bytes())["accepted"]:
                continue
            from PIL import Image
            try:
                with Image.open(thumb) as image:
                    if image.format != "WEBP" or image.width * image.height > 40_000_000:
                        continue
                    image.load()
                with Image.open(entry["path"]) as image:
                    if image.format != "WEBP":
                        continue
            except (OSError, ValueError):
                continue
            assessment = self.assurance.get(pid, {}).get("media", {})
            current = place.get("images", {}).get("primary") or {}
            trusted = (not self.assurance.get(pid, {}).get("identity_blocker")
                       and (not place.get("external_ids", {}).get("wikidata_id") or len(self.qids[place['external_ids']['wikidata_id']]) == 1)
                       and assessment.get("verified") is True and assessment.get("identity_hash") == digest(compact_identity(place))
                       and assessment.get("verification_hash") is not None
                       and assessment["verification_hash"] == media_signature(self.pack, current)
                       and commons_file_key(current.get("source_page")) == key
                       and entry["image"].get("local_path") == current.get("local_path"))
            if trusted:
                old = entry["image"]
                if (old.get("author") and creator_key(old["author"]) != candidate.creator
                        or old.get("original_file") and commons_file_key(old["original_file"]) != commons_file_key(candidate.title)
                        or old.get("license") and canonical_license(old["license"], old.get("license_url")) != candidate.license
                        or old.get("license_url") and (canonical_license_url(old["license_url"]) or old["license_url"]) != candidate.license_url):
                    return {"conflict": "VERIFIED_EXISTING_METADATA_CONFLICT"}
            return {"asset": entry, "verified_identity": {
                "place_id": pid, "identity_hash": digest(compact_identity(place)),
                "content_sha256": sha, "source_key": key} if trusted else None}
        return {}

    def install(self, entry, candidate, assessment, work):
        image = copy.deepcopy(entry["image"])
        for field, value in {"source": candidate.source, "source_page": candidate.source_url,
                "original_file": candidate.title, "author": candidate.creator, "license": candidate.license,
                "license_url": candidate.license_url, "attribution": candidate.attribution,
                "match_method": candidate.match_method, "match_confidence": assessment["final_confidence"],
                "content_sha256": assessment["checks"]["sha256"]}.items():
            image[field] = value
        for key, origin in (("local_path", entry["path"]), ("thumbnail_path", entry["thumbnail"])):
            target = (work / image[key]).resolve()
            if not target.is_relative_to(work.resolve()):
                raise ValueError("Unsafe existing media path")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
        return image

    def register(self, place, candidate, content, original_sha256):
        self.by_source[commons_file_key(candidate.source_url)].add(place["id"])
        self.by_hash[hashlib.sha256(content).hexdigest()].add(place["id"])
        self.by_hash[original_sha256].add(place["id"])
