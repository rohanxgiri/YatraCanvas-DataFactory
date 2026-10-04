"""Re-associate evidence through two registered snapshots, without editing IDs by hand."""
import copy
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from ..config.settings import get_settings
from ..pipeline.identity_assurance import compact_identity
from ..utils.media_metadata import commons_filename, canonical_license, canonical_license_url
from ..utils.atomic import atomic_json
from ..utils.hashing import compute_sha256
from .export import snapshot, task_id, city_key
from .importer import local_file, safe_sources
from .quality import public_source
from .schemas import ResultBundle


def registry(handoff_id, settings):
    if not re.fullmatch(r"handoff_[a-f0-9]{24}", handoff_id):
        raise ValueError("Invalid handoff ID")
    path = settings.data_dir / "research/handoffs" / f"{handoff_id}.json"
    if not path.is_file():
        raise ValueError("Missing registered handoff")
    value = json.loads(path.read_text(encoding="utf-8"))
    pack = (settings.releases_dir / value["source_pack"]).resolve()
    if not pack.is_relative_to(settings.releases_dir.resolve()) or snapshot(pack) != value["snapshot"]:
        raise ValueError("Source snapshot changed; export a new handoff before retry mapping")
    return value, pack


def build_retry_bundle(previous_file: Path, handoff_id: str, output: Path, *, settings=None):
    settings = settings or get_settings()
    if previous_file.stat().st_size > 20_000_000:
        raise ValueError("Research input exceeds 20 MB limit")
    document = json.loads(previous_file.read_text(encoding="utf-8"))
    ResultBundle.model_validate_json(json.dumps(document))
    old, old_pack = registry(document["handoff_id"], settings)
    new, new_pack = registry(handoff_id, settings)
    if old["city"] != new["city"] or old["handoff_id"] == new["handoff_id"]:
        raise ValueError("Retry requires a fresh registered handoff for the same city")
    head_file = settings.data_dir / "research/heads" / f"{city_key(new['city'])}.json"
    if head_file.exists() and json.loads(head_file.read_text(encoding="utf-8"))["output_pack"] != new["source_pack"]:
        raise ValueError("Retry handoff is stale; export from the latest research head")
    old_places = {p["id"]: p for p in json.loads((old_pack / "places.json").read_text(encoding="utf-8"))}
    new_places = {p["id"]: p for p in json.loads((new_pack / "places.json").read_text(encoding="utf-8"))}
    old_tasks = {t["task_id"]: t for t in old["tasks"]}
    prior, seen = {}, set()
    for row in document["results"]:
        task = old_tasks.get(row["task_id"])
        if (not task or task["place_id"] != row["place_id"] or task["type"] != row["type"]
                or row["task_id"] in seen or task_id(old["city"], row["place_id"], row["type"]) != row["task_id"]):
            raise ValueError("Previous result does not match its registered task")
        seen.add(row["task_id"])
        prior[(row["place_id"], row["type"])] = row
    rows, mapping, counts, copies = [], [], Counter(), []
    for task in new["tasks"]:
        pid, kind = task["place_id"], task["type"]
        if task_id(new["city"], pid, kind) != task["task_id"] or pid not in new_places:
            raise ValueError("Invalid new registered task")
        old_row = prior.get((pid, kind))
        reason = None
        if old_row:
            previous_task = old_tasks[old_row["task_id"]]
            if pid not in old_places or compact_identity(old_places[pid]) != compact_identity(new_places[pid]):
                reason = "PLACE_IDENTITY_CHANGED"
            elif (previous_task["priority_reason"] != task["priority_reason"]
                  or previous_task["known_evidence"]["media_policy"] != task["known_evidence"]["media_policy"]):
                reason = "UNRESOLVED_CONDITION_CHANGED"
        else:
            reason = "NO_MATCHING_PRIOR_REGISTERED_RESULT"
        if reason:
            category = "NEW_RESEARCH_REQUIRED"
            row = {"task_id": task["task_id"], "place_id": pid, "type": kind, "status": "UNRESOLVED",
                   "result": {}, "sources": [], "research_notes": reason}
        else:
            row = copy.deepcopy(old_row)
            row["task_id"] = task["task_id"]
            if row["status"] == "CONFLICT":
                category = "GENUINE_CONFLICT"
            elif row["status"] == "UNRESOLVED":
                category = "UNRESOLVED_NO_SOURCE"
            elif row["status"] == "PARTIAL":
                category = "NEW_RESEARCH_REQUIRED"
            else:
                payload = row["result"]
                page = payload.get("source_page_url")
                urls = [s.get("url") for s in row["sources"]]
                typed = ResultBundle.model_validate_json(json.dumps({"schema_version":"1.0", "handoff_id":handoff_id, "results":[row]})).results[0]
                valid = (kind == "REAL_PRIMARY_IMAGE" and commons_filename(page, source_url=True)
                         and page in urls and public_source(page)
                         and any(s.get("url") == page for s in safe_sources(typed, new_places[pid]))
                         and canonical_license(payload.get("license"), payload.get("license_url"))
                         and public_source(canonical_license_url(payload.get("license_url")) or payload.get("license_url"))
                         and payload.get("creator") and payload.get("attribution"))
                category = "RETRYABLE_WITH_EXISTING_RESEARCH" if valid else "NEW_RESEARCH_REQUIRED"
                if not valid:
                    row.update(status="PARTIAL")
                    reason = "PRIOR_EVIDENCE_REQUIRES_NEW_RESEARCH"
                if payload.get("local_file"):
                    path = local_file(previous_file.parent, payload["local_file"])
                    if not path:
                        raise ValueError("Unsafe prior research media path")
                    target = (output.parent / payload["local_file"]).resolve()
                    if not target.is_relative_to(output.parent.resolve()):
                        raise ValueError("Unsafe retry media path")
                    copies.append((path, target))
        rows.append(row)
        counts[category] += 1
        mapping.append({"place_id": pid, "type": kind, "old_task_id": old_row["task_id"] if old_row else None,
                        "new_task_id": task["task_id"], "classification": category, "reason": reason,
                        "source_urls_unchanged": bool(old_row and row["sources"] == old_row["sources"])})
    bundle = {"schema_version": "1.0", "handoff_id": handoff_id, "results": rows}
    ResultBundle.model_validate_json(json.dumps(bundle))
    if output.exists():
        raise ValueError("Retry output already exists; choose a new file")
    for source, target in copies:
        if target.exists() and compute_sha256(target) != compute_sha256(source):
            raise ValueError("Retry media destination already contains different bytes")
    output.parent.mkdir(parents=True, exist_ok=True)
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target:
            shutil.copyfile(source, target)
    atomic_json(output, bundle)
    report = {"schema_version": "1.0", "previous_handoff_id": old["handoff_id"], "handoff_id": handoff_id,
              "previous_input_sha256": compute_sha256(previous_file), "retry_input_sha256": compute_sha256(output),
              "source_pack": new["source_pack"], "remaining_tasks": len(rows), "classification": dict(counts),
              "mapping": mapping, "output_file": str(output.resolve())}
    atomic_json(output.with_suffix(".mapping.json"), report)
    return report
