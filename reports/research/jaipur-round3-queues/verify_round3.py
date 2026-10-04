"""Read-only verification of round-three classification, registration and preservation."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data/research/exports/jaipur/required_images_round3"
sys.path.insert(0, str(ROOT))

from datafactory.ai.config import AIConfig
from datafactory.pipeline.validate import validate_release_package
from datafactory.research.export import make_tasks, snapshot, task_id
from datafactory.research.resolution import resolve_media_tasks
from datafactory.research.schemas import ResultBundle


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = read(REPORT / "before.json")
changed = [p for p, h in before["protected_files"].items()
           if not (ROOT / p).is_file() or sha(ROOT / p) != h]
assert not changed, changed
assert AIConfig.load().mode == "FREE_ONLY"
status = read(OUTPUT / "status_report.json")
pack = Path(status["source_pack"])
assert str(pack) == before["source_pack"]
city = read(pack / "city.json")
tasks = [t for t in make_tasks(read(pack / "places.json"), city, pack, include_optional=True)
         if t["type"] == "REAL_PRIMARY_IMAGE" and t["known_evidence"]["media_policy"] == "REAL_REQUIRED"]
fresh = resolve_media_tasks(pack, tasks)
assert fresh == status["tasks"] and len(fresh) == 35
assert snapshot(pack) == status["source_snapshot"]
groups = {state: {r["task_id"] for r in fresh if r["resolution_state"] == state}
          for state in ("PROVIDER_RETRY", "NEW_RESEARCH_REQUIRED", "MANUAL_REVIEW")}
assert {state: len(ids) for state, ids in groups.items()} == status["resolution_queues"]
assert set().union(*groups.values()) == {t["task_id"] for t in tasks}
assert sum(map(len, groups.values())) == len(set().union(*groups.values()))
assert all(r["task_id"] == task_id(city, r["place_id"], r["type"]) for r in fresh)
for record in fresh:
    if record["resolution_state"] == "PROVIDER_RETRY":
        assert record["source_license_verified"] and record["deterministic_checks_passed"]
        assert record["download_or_reuse_verified"] and not record["web_search_needed"]
        assert record["research_evidence"] and record["candidate"] and record["siglip"]

for folder, state in [("new_research", "NEW_RESEARCH_REQUIRED"), ("provider_retry", "PROVIDER_RETRY")]:
    handoff = read(OUTPUT / folder / "research_handoff.json")
    registered = read(ROOT / "data/research/handoffs" / (handoff["handoff_id"] + ".json"))
    assert registered["tasks"] == handoff["tasks"]
    assert registered["source_pack"] == pack.relative_to(ROOT / "releases").as_posix()
    assert registered["snapshot"] == snapshot(pack)
    assert {t["task_id"] for t in handoff["tasks"]} == groups[state]
    assert read(OUTPUT / folder / "research_results.schema.json") == ResultBundle.model_json_schema()

template = ResultBundle.model_validate_json((OUTPUT / "new_research/research_results.template.json").read_text(encoding="utf-8"))
retry = ResultBundle.model_validate_json((OUTPUT / "provider_retry/research_results.retry.json").read_text(encoding="utf-8"))
assert {r.task_id for r in template.results} == groups["NEW_RESEARCH_REQUIRED"]
assert {r.task_id for r in retry.results} == groups["PROVIDER_RETRY"]
assert template.handoff_id != "handoff_52e106bcb2e1e8881d37ee23"
assert retry.handoff_id != "handoff_0d189314a8392cccadf6173c"
old_schema = read(ROOT / "data/research/exports/jaipur/required_images_remaining/new_research/research_results.schema.json")
assert old_schema == ResultBundle.model_json_schema()

dry = {}
for filename, expected in [("new-research-dry-run.json", 10), ("provider-dry-run.json", 19)]:
    result = read(REPORT / filename)
    assert result["summary"]["tasks_supplied"] == expected
    assert result["summary"]["matched"] == expected and result["summary"]["valid"] == expected
    for key in ("rejected", "missing_pois", "invalid_sources", "invalid_schedules", "applied"):
        assert result["summary"][key] == 0
    assert result["ai_usage"]["stats"]["calls"] == 0
    assert result["ai_usage"]["paid_feature_calls"] == 0
    dry[filename] = result["summary"]
normal_text = (REPORT / "normal-export-check.txt").read_text(encoding="utf-8-sig")
normal = json.JSONDecoder().raw_decode(normal_text[normal_text.index("{"):])[0]
assert normal["total"] == 10 and normal["handoff_id"] == template.handoff_id
assert normal["excluded_resolution_queues"] == {"PROVIDER_RETRY": 19, "MANUAL_REVIEW": 6}

new = read(OUTPUT / "new_research/research_handoff.json")
assert all(t["known_evidence"]["previous_research"] for t in new["tasks"])
assert all("generic activity photograph is not evidence" in t["research_instruction"] for t in new["tasks"])
for t in new["tasks"]:
    if "mobile_card_suitability" in t["previous_attempt"].get("unmet_requirements", []):
        assert "DIFFERENT" in t["research_instruction"] and len(t["known_evidence"]["excluded_source_pages"]) >= 2
manual = read(OUTPUT / "manual_review/review_tasks.json")
assert {t["task_id"] for t in manual["tasks"]} == groups["MANUAL_REVIEW"]
assert all(r["recommended_next_action"] for r in manual["tasks"])
assert not any("anokhi" in r["place_id"] for r in fresh)
assert read(pack / "usability.json") == before["usability"]
assert before["usability"]["real_required_verified"] == 17

validation = validate_release_package(pack)
full = re.search(r"(\d+) passed in ([\d.]+)s", (REPORT / "tests-full.txt").read_text(encoding="utf-8"))
focused = re.search(r"(\d+) passed in ([\d.]+)s", (REPORT / "tests-focused.txt").read_text(encoding="utf-8"))
assert full and focused
verification = {"protected_files_checked": len(before["protected_files"]), "changed_protected_files": changed,
    "verified_required_images": 17, "remaining_required_images": 35,
    "source_pack": str(pack), "resolution_queues": status["resolution_queues"],
    "new_research_handoff_id": template.handoff_id, "provider_retry_handoff_id": retry.handoff_id,
    "dry_runs": dry, "normal_web_export_tasks": normal["total"], "schema_unchanged": True,
    "full_tests": {"passed": int(full[1]), "seconds": float(full[2])},
    "focused_tests": {"passed": int(focused[1]), "seconds": float(focused[2])},
    "provider_calls": 0, "paid_calls": 0, "validation": validation}
(REPORT / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
status["verification"] = verification
(OUTPUT / "status_report.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

lines = ["", "## Current State", "", "Verified required images: **17/52** (32.69%). Remaining: **35**.",
    f"Latest immutable source pack: `{pack}`", "", "## New Research Tasks", ""]
for task in new["tasks"]:
    record = next(r for r in fresh if r["task_id"] == task["task_id"])
    note = (record.get("research_evidence") or {}).get("research_notes", "")
    reason = "Needs a different photograph with good mobile-card framing; exclude all prior candidates." if record["alternate_image_required"] else note
    lines.append(f"- **{record['name']}**: {reason}")
lines += ["", "## Manual Review", ""]
for record in manual["tasks"]:
    note = (record.get("research_evidence") or {}).get("research_notes", "")
    lines.append(f"- **{record['name']}**: {note}")
    if record["review_flags"]:
        lines.append("  MEDIA_POLICY_REVIEW_RECOMMENDED: " + ", ".join(record["media_policy_review_reasons"]) + ". No policy change applied.")
lines += ["", "Elephant Riding is excluded from external research pending exact-listing identity and policy review. EleJungle remains in exact-venue research with an advisory commercial-photo policy flag; generic elephant-riding photographs are forbidden as venue evidence.",
    "", "## Validation", "", "New research: supplied/matched/valid **10/10/10**, unresolved template **10**. Provider bundle: supplied/matched/valid **19/19/19**, review **19**. Both: rejected/missing POIs/invalid sources/invalid schedules **0**; AI calls **0**. Neither bundle was applied.",
    f"New research registration: `{template.handoff_id}`. Provider retry registration: `{retry.handoff_id}`.",
    "Both use the unchanged v3-research-jaipur-images-03 source snapshot. Result schema unchanged. Normal web export includes exactly 10 research tasks and excludes 19 provider holds plus 6 manual reviews.",
    "", "## Tests", "", f"Full suite: **{full[1]} passed in {full[2]}s**. Focused research suite: **{focused[1]} passed in {focused[2]}s**.",
    "```powershell", f".\\.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider --basetemp {ROOT / 'data/staging/round3-resolution-full'} --tb=short", "```",
    "Default tests use fixtures and mocks, with no live provider calls.", "", "## Safety", "",
    f"**{len(before['protected_files']):,} protected hashes matched**: v3, all previous research/source releases, the 17 accepted required images, head, prior registered handoffs/import histories, human curation, FREE_ONLY configuration, importer/schema/assurance/policy unchanged. City Lab was not touched. Provider calls **0**; paid AI calls **0**. No new city pack or media-policy changes were published.",
    "Only queue classification/export context and regression tests/documentation were updated. Provider-held evidence is retained for a later explicitly requested retry.", "", "## Generated Files", ""]
paths = ["new_research/research_handoff.json", "new_research/research_handoff.md", "new_research/research_results.template.json",
    "new_research/research_results.schema.json", "provider_retry/retry_tasks.json", "provider_retry/research_results.retry.json",
    "manual_review/review_tasks.json", "status_report.md", "status_report.json"]
for path in paths:
    assert (OUTPUT / path).is_file()
    lines.append(f"- `{OUTPUT / path}`")
original = (OUTPUT / "status_report.md").read_text(encoding="utf-8").split("\n## Current State")[0]
(OUTPUT / "status_report.md").write_text(original + "\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(verification, ensure_ascii=False, indent=2))
