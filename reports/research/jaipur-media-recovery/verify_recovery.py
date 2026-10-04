"""Read-only recovery verification; writes reports, never source packs."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from PIL import Image
from datafactory.ai.router import digest
from datafactory.pipeline.identity_assurance import compact_identity
from datafactory.pipeline.media_assurance import deterministic_filter, media_signature
from datafactory.pipeline.repair import candidate_from_existing
from datafactory.pipeline.usability import usability
from datafactory.pipeline.validate import validate_release_package
from datafactory.utils.hashing import compute_sha256
from datafactory.utils.media_metadata import commons_file_key

REPORT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(name, value):
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_cli(name):
    text = (REPORT / name).read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):])


before = read(REPORT / "before.json")
main = read(REPORT / "apply.json")
derivative = parse_cli("derivative-apply.txt")
save("derivative_apply.json", derivative)
source = Path(before["source_pack"])
final = Path(derivative["output_pack"])
initial = before["initial_research_metrics"]

protected = before["protected_files"]
changed = [name for name, sha in protected.items()
           if not (ROOT / name).is_file() or compute_sha256(ROOT / name) != sha]
intermediate = read(REPORT / "images02_snapshot.json")
changed_intermediate = [name for name, sha in intermediate["files"].items()
                        if compute_sha256(Path(intermediate["pack"]) / name) != sha]
assert not changed, changed
assert not changed_intermediate, changed_intermediate

validation = validate_release_package(final)
places = read(final / "places.json")
city = read(final / "city.json")
assurance = read(final / "media_assurance.json")
after = usability(places, city, final, assurance)
assert after == read(final / "usability.json")
save("after.json", after)
save("validation.json", validation)

# The supplementary decision replaces the initial download hold in net outcomes.
decisions = {row["place_id"]: row for row in main["decisions"]}
decisions.update({row["place_id"]: row for row in derivative["decisions"]})
places_by_id = {p["id"]: p for p in places}
source_places = {p["id"]: p for p in read(source / "places.json")}
accepted = [row for row in decisions.values() if row["action"] == "AUTO_APPLY"]
reuse, p18, decoded_assets = [], [], 0
provenance = read(final / "field_provenance.json")
for row in accepted:
    pid = row["place_id"]
    place = places_by_id[pid]
    image = place["images"]["primary"]
    checked = assurance[pid]["media"]
    assert checked["verified"] is True
    assert checked["identity_hash"] == digest(compact_identity(place))
    assert checked["verification_hash"] == media_signature(final, image)
    assert deterministic_filter(candidate_from_existing(image), (final / image["local_path"]).read_bytes())["accepted"]
    assert any(p.get("place_id") == pid and p.get("task_id") == row["task_id"] for p in provenance)
    for relative in (image["local_path"], image["thumbnail_path"]):
        with Image.open(final / relative) as decoded:
            assert decoded.format == "WEBP" and decoded.width * decoded.height <= 40_000_000
            decoded.load()
        decoded_assets += 1
    if "EXISTING_ASSET_REUSE" in row["reason_codes"]:
        relative = row["reuse"]["existing_local_path"]
        assert compute_sha256(source / relative) == compute_sha256(final / image["local_path"])
        old_images = source_places[pid]["images"]
        old_image = next(i for i in [old_images["primary"], *old_images["gallery"]]
                         if i and i["local_path"] == relative)
        assert commons_file_key(old_image["original_file"]) == commons_file_key(image["original_file"])
        reuse.append(place["name"])
    if "VERIFIED_ENTITY_LINKED_P18" in row["reason_codes"]:
        proof = row["evidence_merge"]["identity_evidence"]
        assert proof["wikidata_id"] == place["external_ids"]["wikidata_id"]
        assert commons_file_key(proof["p18_file"]) == commons_file_key(image["original_file"])
        assert image["match_method"] == "wikidata_p18" and row["candidate"]["original_license_verified"]
        p18.append(place["name"])

outcomes = Counter(row["action"] for row in decisions.values())
reasons = Counter(code for row in decisions.values() for code in row["reason_codes"])
mpo = [row for row in decisions.values() if "MPO_PRIMARY_FRAME_NORMALIZED" in row["reason_codes"]]
held = [{"place_id": row["place_id"], "name": places_by_id[row["place_id"]]["name"],
         "action": row["action"], "reason_codes": row["reason_codes"],
         "unmet_requirements": row.get("unmet_requirements"), "ai": row.get("ai")}
        for row in decisions.values() if row["action"] != "AUTO_APPLY"]
# Use primitive counters only; nested ranker counters are reported separately.
local = {key: main["local_intelligence"].get(key, 0) + derivative["local_intelligence"].get(key, 0)
         for key in ("accepted_without_cloud_ai", "cloud_jobs_avoided", "existing_assets_reused",
                     "mpo_encountered", "mpo_normalized", "commons_derivatives_used")}
for report in (main, derivative):
    assert report["ai_usage"]["AI_MODE"] == "FREE_ONLY"
    assert report["ai_usage"]["paid_feature_calls"] == 0
    assert report["ai_usage"]["paid_providers_invoked"] == 0
assert compute_sha256(ROOT / "data/research/import_inputs/jaipur_image_research_results.json") == "126c3f0dad105e87b2079f04bd244089ab9b77f27f53ae6b933e258365c32ec9"
summary = {"output_pack": str(final), "intermediate_pack": main["output_pack"],
    "net_outcomes": {"applied": outcomes["AUTO_APPLY"], "review": outcomes["REVIEW"],
                     "rejected": outcomes["REJECT"], "unresolved": outcomes["UNRESOLVED"]},
    "reason_codes": dict(reasons), "local_intelligence": local,
    "ranker": main["local_intelligence"]["ranker"], "ai_usage": main["ai_usage"],
    "accepted_names": [places_by_id[r["place_id"]]["name"] for r in accepted],
    "reused_asset_names": reuse, "p18_names": p18,
    "mpo": {"encountered": len(mpo), "normalized": len(mpo),
            "accepted": sum(r["action"] == "AUTO_APPLY" for r in mpo),
            "rejected": sum(r["action"] == "REJECT" for r in mpo),
            "held": sum(r["action"] == "REVIEW" for r in mpo)},
    "downloaded_successfully": sum(bool(r.get("download", {}).get("bytes")) for r in decisions.values()),
    "deterministic_rejections": sum(r["action"] == "REJECT" and not r.get("checks", {}).get("accepted", True) for r in decisions.values()),
    "license_holds": sum(any(code in r["reason_codes"] for code in ("IMAGE_LICENSE_INVALID", "ORIGINAL_SOURCE_METADATA_CONFLICT", "ORIGINAL_SOURCE_LICENSE_UNVERIFIED")) for r in decisions.values()),
    "protected_files_checked": len(protected), "changed_protected_files": changed,
    "intermediate_files_checked": len(intermediate["files"]), "changed_intermediate_files": changed_intermediate,
    "new_webp_assets_decoded": decoded_assets, "paid_ai_calls": 0,
    "before_research": initial, "images01": before["usability"],
    "images02_intermediate": read(Path(main["output_pack"]) / "usability.json"), "images02_final": after,
    "validation": validation, "dry_run": read(REPORT / "dry_run.json")["summary"],
    "retry": read(ROOT / "data/research/import_inputs/jaipur_image_retry_results_02.mapping.json")["classification"],
    "remaining_handoff": {"handoff_id": "handoff_3ee479e0891634eb67376284", "tasks": 36,
       "path": str(ROOT / "data/research/exports/jaipur/required_images_after_recovery/research_handoff.md")}}
test_result = re.search(r"(\d+) passed in ([\d.]+)s", (REPORT / "tests-final-02.txt").read_text(encoding="utf-8"))
assert test_result
summary["tests"] = {"passed": int(test_result[1]), "seconds": float(test_result[2]), "log": "tests-final-02.txt"}
save("summary.json", summary)
save("held_images.json", held)
print(json.dumps({key: summary[key] for key in ("net_outcomes", "local_intelligence", "mpo", "downloaded_successfully", "deterministic_rejections", "license_holds", "protected_files_checked", "intermediate_files_checked", "new_webp_assets_decoded", "validation")}, indent=2))
