"""Read-only pack preservation/validation audit; writes only this report folder."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from datafactory.ai.config import AIConfig
from datafactory.pipeline.validate import validate_release_package
from datafactory.research.export import snapshot


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(name, data):
    (REPORT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(pack):
    u = read(pack / "usability.json")
    return {k: u[k] for k in ("GENERAL_USABILITY", "REAL_REQUIRED_MEDIA_COVERAGE",
        "real_required_total", "real_required_verified", "critical_blockers",
        "critical_blocker_pois", "SOURCE_DATA_READY", "pack_status")}


def before():
    bundle = read(ROOT / "data/research/import_inputs/jaipur_round2_research_results.json")
    registry = read(ROOT / "data/research/handoffs" / (bundle["handoff_id"] + ".json"))
    source = ROOT / "releases" / registry["source_pack"]
    assert snapshot(source) == registry["snapshot"], "Registered source snapshot changed"
    config = AIConfig.load()
    assert config.mode == "FREE_ONLY", "FREE_ONLY must remain enabled"
    output = source.parent / "v3-research-jaipur-images-03"
    assert not output.exists(), "Requested output version already exists"
    dry = read(REPORT / "dry-run.json")
    structural = {"INVALID_RESULT_SCHEMA", "UNKNOWN_PLACE_ID", "TASK_ID_OR_PLACE_ID_MISMATCH_OR_DUPLICATE",
                  "IMAGE_SOURCE_INVALID", "IMAGE_LICENSE_INVALID"}
    assert not structural.intersection(c for d in dry["decisions"] for c in d["reason_codes"])
    assert dry["summary"]["rejected"] == 0 and dry["summary"]["matched"] == len(bundle["results"])
    protected = set(read(ROOT / "reports/research/jaipur-resolution-queues/before.json")["protected_files"])
    # The current head is the only existing index that successful publication changes.
    protected = {p for p in protected if not p.startswith("data/research/heads/")}
    for directory in ("releases", "data/curated", "config", "datafactory", "data/research/handoffs",
                      "data/research/imports", "data/research/import_inputs"):
        for p in (ROOT / directory).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protected.add(p.relative_to(ROOT).as_posix())
    if (ROOT / ".env").is_file():
        protected.add(".env")
    hashes = {p: sha(ROOT / p) for p in sorted(protected)}
    heads = {p.relative_to(ROOT).as_posix(): read(p) for p in (ROOT / "data/research/heads").glob("*.json")}
    validation = validate_release_package(source)
    record = {"source_pack": str(source), "output_pack_requested": str(output),
        "handoff_id": bundle["handoff_id"], "schema_version": bundle["schema_version"],
        "input_sha256": sha(ROOT / "data/research/import_inputs/jaipur_round2_research_results.json"),
        "results": len(bundle["results"]), "task_types": dict(Counter(r["type"] for r in bundle["results"])),
        "research_statuses": dict(Counter(r["status"] for r in bundle["results"])),
        "metrics": metrics(source), "validation": validation, "heads": heads, "protected_files": hashes,
        "ai_mode": config.mode, "dry_run_summary": dry["summary"]}
    save("before.json", record)
    print(json.dumps({k: v for k, v in record.items() if k not in {"protected_files", "validation", "heads"}}, indent=2))
    print("Protected file count:", len(hashes))


def after():
    prior = read(REPORT / "before.json")
    changed = [p for p, h in prior["protected_files"].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    assert not changed, changed
    applied = read(REPORT / "apply.json")
    source = Path(prior["source_pack"])
    output = Path(applied.get("output_pack", source))
    validation = validate_release_package(output)
    assert applied["ai_usage"]["AI_MODE"] == "FREE_ONLY"
    assert applied["ai_usage"]["paid_feature_calls"] == 0
    assert applied["ai_usage"]["paid_providers_invoked"] == 0
    old_places = {p["id"]: p for p in read(source / "places.json")}
    new_places = {p["id"]: p for p in read(output / "places.json")}
    assert old_places.keys() == new_places.keys(), "Published place IDs changed"
    changed_images = [pid for pid in old_places if old_places[pid].get("images", {}).get("primary") != new_places[pid].get("images", {}).get("primary")]
    accepted = {d["place_id"] for d in applied["decisions"] if d["action"] == "AUTO_APPLY"}
    assert set(changed_images) <= accepted
    decisions = [{"place_id": d["place_id"], "action": d["action"], "reason_codes": d["reason_codes"],
                  "conflicting_fields": d.get("conflicting_fields", [])} for d in applied["decisions"]]
    result = {"before": prior["metrics"], "after": metrics(output), "output_pack": applied.get("output_pack"),
        "apply_summary": applied["summary"], "reason_codes": dict(Counter(c for d in decisions for c in d["reason_codes"])),
        "decisions": decisions, "ai_usage": applied["ai_usage"], "local_intelligence": applied["local_intelligence"],
        "protected_files_checked": len(prior["protected_files"]), "changed_protected_files": changed,
        "changed_primary_images": changed_images, "validation": validation}
    save("verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    {"before": before, "after": after}[sys.argv[1]]()
