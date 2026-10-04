"""Read-only review of identity proposals; deliberately has no apply operation.

This format is not a Research Handoff result bundle. It cannot register tasks,
change media policy, merge records, or write a release. A successful preview
means the proposal is internally consistent, not that its claims are approved.
"""

from copy import deepcopy
import hashlib
import json
from math import asin, cos, radians, sin, sqrt


ACTIONS = {"KEEP", "RENAME", "MERGE", "REMOVE", "DOWNGRADE", "UNRESOLVED"}
POLICIES = {"REAL_REQUIRED", "REAL_PREFERRED", "FALLBACK_ALLOWED", "REMOVE_POI"}
IDENTITY_FIELDS = {
    "name", "name_en", "alternate_names", "description",
    "location.latitude", "location.longitude",
    "external_ids.osm_id", "external_ids.wikidata_id",
}
STRONG_IDS = ("osm_id", "wikidata_id")


def record_fingerprint(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def distance_m(left: dict, right: dict) -> float:
    a, b = left["location"], right["location"]
    lat1, lat2 = radians(a["latitude"]), radians(b["latitude"])
    delta_lat = lat2 - lat1
    delta_lon = radians(b["longitude"] - a["longitude"])
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371000 * 2 * asin(min(1.0, sqrt(value)))


def identity_equivalence(left: dict, right: dict) -> dict:
    """Conservative merge screening, never an automatic identity resolver.

    Shared names, aliases, categories and proximity are insufficient. Different
    OSM objects may represent one venue, but that requires review outside this
    screen; conflicting IDs or distant coordinates always hold the proposal.
    """
    a, b = left.get("external_ids", {}), right.get("external_ids", {})
    shared = [key for key in STRONG_IDS if a.get(key) and a.get(key) == b.get(key)]
    conflicts = [key for key in STRONG_IDS if a.get(key) and b.get(key) and a[key] != b[key]]
    distance = distance_m(left, right)
    reasons = []
    if conflicts:
        reasons.append("CONFLICTING_EXTERNAL_IDS")
    if not shared:
        reasons.append("NO_SHARED_EXACT_IDENTITY")
    if distance > 250:
        reasons.append("COORDINATE_CONFLICT_REQUIRES_REVIEW")
    return {"eligible_for_merge_review": not reasons, "shared_ids": shared,
            "conflicting_ids": conflicts, "distance_m": round(distance, 1),
            "reason_codes": reasons}


def _field(record: dict, path: str):
    value = record
    for key in path.split("."):
        value = value[key]
    return deepcopy(value)


def preview_manual_changes(places: list[dict], bundle: dict, current_snapshot: dict) -> dict:
    """Return a detached reviewable diff or fail closed; never mutate inputs.

    Snapshot and per-record preconditions prevent reviewing against a different
    release. Evidence is recorded for a human, not scored as proof by this tool.
    Tier/score/media-policy recommendations remain outside field changes.
    """
    if (bundle.get("kind") != "manual_identity_proposals"
            or bundle.get("schema_version") != "1.0"
            or bundle.get("apply_ready") is not False):
        raise ValueError("PROPOSAL_ONLY_FORMAT_REQUIRED")
    if not current_snapshot or bundle.get("source_snapshot") != current_snapshot:
        raise ValueError("STALE_SOURCE_SNAPSHOT")
    by_id = {p["id"]: p for p in places}
    if len(by_id) != len(places):
        raise ValueError("DUPLICATE_SOURCE_PLACE_ID")
    rows, seen = [], set()
    for item in bundle["proposals"]:
        pid = item["place_id"]
        if pid not in by_id or pid in seen:
            raise ValueError("UNKNOWN_OR_DUPLICATE_PLACE_ID")
        seen.add(pid)
        original = by_id[pid]
        if item.get("before_sha256") != record_fingerprint(original):
            raise ValueError("STALE_PLACE_PRECONDITION")
        action = item["action"]
        if action not in ACTIONS:
            raise ValueError("INVALID_PROPOSED_ACTION")
        if not item.get("reason") or not item.get("evidence"):
            raise ValueError("IDENTITY_EVIDENCE_REQUIRED")
        for source in item["evidence"]:
            if not source.get("url", "").startswith("https://") or not source.get("supports"):
                raise ValueError("IDENTITY_EVIDENCE_REQUIRED")
        policy = item["media_policy_recommendation"]
        if (policy.get("current") not in POLICIES or policy.get("recommended") not in POLICIES
                or not policy.get("reason") or policy.get("applied") is not False):
            raise ValueError("SEPARATE_UNAPPLIED_POLICY_RECOMMENDATION_REQUIRED")
        changes = item.get("changes", {})
        if set(changes) - IDENTITY_FIELDS:
            raise ValueError("FIELD_OUTSIDE_IDENTITY_PROPOSAL_SCOPE")
        if action in {"MERGE", "REMOVE"} and changes:
            raise ValueError("DESTRUCTIVE_ACTION_MUST_REMAIN_SEPARATE_PROPOSAL")
        merge_screen = None
        if action == "MERGE":
            target = item.get("target_place_id")
            if target not in by_id or target == pid:
                raise ValueError("INVALID_MERGE_TARGET")
            if item.get("target_before_sha256") != record_fingerprint(by_id[target]):
                raise ValueError("STALE_MERGE_TARGET")
            audit = item.get("reference_audit", {})
            if not all(audit.get(key) == "reviewed" for key in
                       ("aliases", "coordinates", "external_ids", "offline_media", "trip_references", "relations")):
                raise ValueError("MERGE_REFERENCE_AUDIT_INCOMPLETE")
            merge_screen = identity_equivalence(original, by_id[target])
            if not merge_screen["eligible_for_merge_review"]:
                raise ValueError("MERGE_IDENTITY_NOT_ESTABLISHED")
        diff = [{"field": path, "before": _field(original, path), "proposed_after": deepcopy(value)}
                for path, value in changes.items() if _field(original, path) != value]
        rows.append({"place_id": pid, "proposed_action": action, "field_diff": diff,
                     "media_policy_recommendation": deepcopy(policy),
                     "tier_review": deepcopy(item.get("tier_review", {})),
                     "merge_screen": merge_screen, "requires_human_review": True})
    return {"kind": "manual_identity_preview", "validation_status": "STRUCTURALLY_VALID_PROPOSAL",
            "dry_run": True, "apply_ready": False, "applied": 0, "deleted": 0, "merged": 0,
            "media_assigned": 0, "policies_changed": 0, "proposals": len(rows), "rows": rows}
