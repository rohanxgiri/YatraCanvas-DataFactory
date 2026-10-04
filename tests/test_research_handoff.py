import copy
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from typer.testing import CliRunner
from datafactory.config.settings import Settings
from datafactory.utils.atomic import atomic_json
from datafactory.utils.hashing import compute_sha256
from datafactory.research.export import export_research, make_tasks, find_pack
from datafactory.research.importer import import_research
from datafactory.research.schemas import ResultBundle
from datafactory.research.quality import source_quality
from test_local_intelligence import photo


@pytest.fixture
def research_pack(tmp_path, monkeypatch, sample_city_metadata, sample_place):
    from datafactory.config import settings as module
    from datafactory.exporters.json_exporter import export_places_json, export_places_jsonl
    from datafactory.exporters.parquet_exporter import export_places_parquet
    from datafactory.exporters.sqlite_exporter import export_sqlite
    from datafactory.models.place import PlaceTier
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "config", tmp_path / "config")
    settings = Settings(project_root=tmp_path)
    monkeypatch.setattr(module, "_settings", settings)
    pack = settings.releases_dir / "india/rajasthan/jaipur/v3"
    pack.mkdir(parents=True)
    place = sample_place.model_copy(deep=True)
    place.tier = PlaceTier.CORE_DESTINATION
    place.images.primary = None
    place.images.gallery = []
    place.description = None
    place.opening_hours.normalized = None
    place.opening_hours.verified = False
    atomic_json(pack / "city.json", sample_city_metadata.model_dump(mode="json"))
    export_places_json([place], pack / "places.json")
    export_places_jsonl([place], pack / "places.jsonl")
    export_places_parquet([place], pack / "places.parquet")
    export_sqlite(sample_city_metadata, [place], pack / "yatracanvas.db")
    atomic_json(pack / "manifest.json", {"city_id":sample_city_metadata.id,"city_name":sample_city_metadata.name,
        "state":sample_city_metadata.state,"country":sample_city_metadata.country,"generated_at":place.generated_at,
        "counts":{"accepted":1}})
    for filename in ["image_manifest.json", "license_manifest.json", "checksums.json"]:
        atomic_json(pack / filename, {})
    atomic_json(pack / "source_manifest.json", {"sources":{}})
    atomic_json(pack / "media_assurance.json", {place.id:{"media":{"verified":False,"candidates":[]}}})
    output = tmp_path / "handoff"
    report = export_research(pack, output, settings=settings)
    tasks = json.loads((output / "research_handoff.json").read_text())["tasks"]
    return settings, pack, place.model_dump(mode="json"), output, report, tasks


def result_file(fixture, kind="OPENING_HOURS", *, status="FOUND", payload=None, sources=None):
    settings, pack, place, output, report, tasks = fixture
    task = next(task for task in tasks if task["type"] == kind)
    date = datetime.now(timezone.utc).isoformat()
    schedule = "Mo-Sa 09:00-17:00; Su off"
    url = place["contact"]["website"]
    source = {"url":url,"source_name":"Official venue","retrieved_at":date,"source_text":schedule}
    hours = {"opening_hours":schedule,"source_text":schedule,"source_url":url,"source_name":"Official venue","retrieved_at":date}
    row = {"task_id":task["task_id"],"place_id":task["place_id"],"type":kind,"status":status,
           "result":payload if payload is not None else hours,"sources":sources if sources is not None else [source],"research_notes":"Fixture, not external research"}
    file = output / "research_results.json"
    atomic_json(file, {"schema_version":"1.0","handoff_id":report["handoff_id"],"results":[row]})
    return file


def inventory(root):
    return {str(p.relative_to(root)): (compute_sha256(p), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}


def test_export_unresolved_stable_city_priority_and_privacy(research_pack):
    settings, pack, place, output, report, tasks = research_pack
    assert report["by_type"]["REAL_PRIMARY_IMAGE"] == 1
    assert report["by_priority"]["P0"] == 1 and report["by_type"]["OPENING_HOURS"] == 1
    assert all(task["place_id"] == place["id"] and task["city"]["state"] == "Rajasthan" for task in tasks)
    assert any(task["known_evidence"]["zero_candidates"] for task in tasks)
    second = export_research(pack, output / "second", settings=settings)
    assert report["handoff_id"] == second["handoff_id"]
    template = ResultBundle.model_validate_json((output / "research_results.template.json").read_text())
    assert all(row.status == "UNRESOLVED" for row in template.results)
    md = (output / "research_handoff.md").read_text(encoding="utf-8")
    assert "Do not guess" in md and "UNRESOLVED" in md
    place["sources"].append({"source":"official_website","source_id":"x", "retrieved_at":"2026-10-03", "url":"https://hawa-mahal.com/?api_key=private-canary"})
    place["private_notes"] = "private-canary"
    tasks = make_tasks([place], json.loads((pack / "city.json").read_text()), pack)
    assert "private-canary" not in json.dumps(tasks)


def test_hours_dry_run_has_zero_mutation(research_pack):
    file = result_file(research_pack)
    settings = research_pack[0]
    before = inventory(settings.project_root)
    report = import_research(file, settings=settings)
    assert report["summary"]["auto_applicable"] == 1 and report["summary"]["applied"] == 0
    assert report["ai_usage"]["stats"]["calls"] == 0
    assert before == inventory(settings.project_root)


def test_apply_complete_pack_audit_idempotence_and_reexport(research_pack):
    from datafactory.pipeline.validate import validate_release_package
    settings, pack, place, output, exported, tasks = research_pack
    file = result_file(research_pack)
    before = inventory(pack)
    report = import_research(file, settings=settings, apply=True)
    assert report["summary"]["applied"] == 1
    new = Path(report["output_pack"])
    assert new != pack and before == inventory(pack)
    validate_release_package(new)
    applied = json.loads((new / "research_import.json").read_text())
    assert applied["input_sha256"] == compute_sha256(file) and applied["summary"]["applied"] == 1
    assert json.loads((new / "places.json").read_text())[0]["opening_hours"]["verified"]
    before_second = inventory(settings.project_root)
    assert import_research(file, settings=settings, apply=True)["already_applied"]
    assert before_second == inventory(settings.project_root)
    assert find_pack("Jaipur", settings=settings) == new
    exported = export_research(new, output / "after", settings=settings)
    assert exported["by_type"]["OPENING_HOURS"] == 0


@pytest.mark.parametrize("change,reason", [("place", "UNKNOWN_PLACE_ID"), ("task", "TASK_ID_OR_PLACE_ID_MISMATCH_OR_DUPLICATE"), ("extra", "INVALID_RESULT_SCHEMA"), ("wrong_payload", "INVALID_RESULT_SCHEMA")])
def test_id_and_schema_rejection(research_pack, change, reason):
    file = result_file(research_pack)
    data = json.loads(file.read_text())
    row = data["results"][0]
    if change == "place": row["place_id"] = "unknown"
    if change == "task": row["task_id"] = "research_" + "0"*24
    if change == "extra": row["confidence"] = 1.
    if change == "wrong_payload": row["result"] = {"website":"https://example.com"}
    atomic_json(file, data)
    report = import_research(file, settings=research_pack[0])
    assert report["summary"]["rejected"] == 1 and reason in report["decisions"][0]["reason_codes"]


@pytest.mark.parametrize("status", ["PARTIAL", "UNRESOLVED", "CONFLICT"])
def test_non_found_status_never_applies(research_pack, status):
    file = result_file(research_pack, status=status, payload={}, sources=[])
    report = import_research(file, settings=research_pack[0], apply=True)
    assert report["summary"]["applied"] == 0 and "output_pack" not in report


def test_invalid_hours_stale_missing_source_and_claimed_quality(research_pack):
    settings = research_pack[0]
    file = result_file(research_pack)
    data = json.loads(file.read_text())
    row = data["results"][0]
    row["result"]["opening_hours"] = "Mo-Su 99:00-20:00"
    atomic_json(file, data)
    assert import_research(file, settings=settings)["summary"]["invalid_schedules"] == 1
    row["result"]["opening_hours"] = "Mo-Sa 09:00-17:00; Su off"
    row["sources"] = []
    atomic_json(file, data)
    assert import_research(file, settings=settings)["summary"]["invalid_sources"] == 1
    source = {"url":"https://unknown-research-site.example/path","source_name":"Official", "retrieved_at":datetime.now(timezone.utc).isoformat(), "source_text":row["result"]["opening_hours"], "claimed_quality":"OFFICIAL"}
    assert source_quality(source, research_pack[2]) == ("SECONDARY", .60)
    source["url"] = "https://127.0.0.1/path"
    assert source_quality(source, research_pack[2])[0] == "UNKNOWN"


def test_changed_snapshot_and_human_lock(research_pack):
    settings, pack, place, output, report, tasks = research_pack
    file = result_file(research_pack)
    atomic_json(settings.curated_dir / "jaipur/overrides/record.json", {"place_id":place["id"],"verified":True,"opening_hours":"Human"})
    assert "HUMAN_FIELD_LOCK" in import_research(file, settings=settings)["decisions"][0]["reason_codes"]
    places = json.loads((pack / "places.json").read_text())
    places[0]["name"] = "Changed"
    atomic_json(pack / "places.json", places)
    with pytest.raises(ValueError, match="snapshot changed"):
        import_research(file, settings=settings, apply=True)
    assert not (settings.data_dir / "research/.import-lock").exists()


def test_failed_publication_leaves_source_and_head_unchanged(research_pack, monkeypatch):
    import datafactory.pipeline.offline_export as module
    settings, pack, *_ = research_pack
    file = result_file(research_pack)
    before = inventory(pack)
    def fail(*args):
        raise ValueError("Fixture validation failure")
    monkeypatch.setattr(module, "export_offline", fail)
    with pytest.raises(ValueError, match="validation failure"):
        import_research(file, settings=settings, apply=True)
    assert before == inventory(pack)
    assert not (settings.data_dir / "research/heads").exists()
    assert not (settings.data_dir / "research/imports").exists()


def test_filter_priorities_and_ordinary_cafe(research_pack):
    settings, pack, place, output, *_ = research_pack
    report = export_research(pack, output / "p0", priorities=["P0"], settings=settings)
    assert report["total"] == 1
    place.update(tier="discovery", classification={"category":"cafe"})
    city = json.loads((pack / "city.json").read_text())
    assert make_tasks([place], city, pack) == []
    place.update(tier="recommended", prominence_score=.4)
    assert make_tasks([place], city, pack) == []
    place.update(tier="recommended", prominence_score=.9)
    assert any(t["priority"] == "P0" for t in make_tasks([place], city, pack))
    with pytest.raises(ValueError, match="Unknown research"):
        export_research(pack, output / "invalid", types=["WRONG"], settings=settings)


def image_result(research_pack, *, local=True):
    settings, pack, place, output, *_ = research_pack
    page = "https://commons.wikimedia.org/wiki/File:Garden.jpg"
    direct = "https://upload.wikimedia.org/garden.jpg"
    date = datetime.now(timezone.utc).isoformat()
    payload = {"source_page_url":page,"direct_media_url":direct,"source_provider":"Wikimedia Commons",
               "creator":"Photographer","license":"CC BY-SA 4.0","license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
               "attribution":"Photographer / CC BY-SA 4.0"}
    if local:
        (output / "images").mkdir(exist_ok=True)
        (output / "images/garden.png").write_bytes(photo())
        payload["local_file"] = "images/garden.png"
    source = {"url":page,"source_name":"Wikimedia Commons","retrieved_at":date,"source_text":"Garden photograph"}
    info = {"source":"Wikimedia Commons","source_page":page,"url":direct,"author":"Photographer","original_file":"Garden.jpg",
            "license":payload["license"],"license_url":payload["license_url"],"width":800,"height":600,"mime":"image/png"}
    from datafactory.sources.wikimedia import WikimediaCommonsClient
    WikimediaCommonsClient().cache.set("img_Garden.jpg", info)
    return result_file(research_pack, "REAL_PRIMARY_IMAGE", payload=payload, sources=[source])


@pytest.mark.parametrize("change,code", [("license", "IMAGE_LICENSE_OR_ATTRIBUTION_MISSING"), ("host", "ORIGINAL_SOURCE_UNSUPPORTED"), ("file", "LOCAL_IMAGE_MISSING_OR_UNSAFE"), ("traversal", "LOCAL_IMAGE_MISSING_OR_UNSAFE")])
def test_image_import_metadata_and_path_safety(research_pack, change, code):
    file = image_result(research_pack)
    data = json.loads(file.read_text())
    row = data["results"][0]
    if change == "license": row["result"]["license"] = None
    if change == "host":
        row["result"]["source_page_url"] = "https://unsupported.example/image"
        row["sources"][0]["url"] = row["result"]["source_page_url"]
    if change == "file": row["result"]["local_file"] = "images/missing.png"
    if change == "traversal": row["result"]["local_file"] = "../outside.png"
    atomic_json(file, data)
    report = import_research(file, settings=research_pack[0])
    assert code in report["decisions"][0]["reason_codes"]


def test_image_dry_run_requires_verification_and_wrong_image_rejected(research_pack):
    file = image_result(research_pack)
    report = import_research(file, settings=research_pack[0])
    assert report["summary"]["media_requiring_verification"] == 1
    assert report["summary"]["applied"] == 0
    class RejectRouter:
        def analyze(self, *args, **kwargs):
            return {"status":"OK", "result":{"decision":"REJECT","confidence":.99,"identity_match":False,"identity_confidence":.1,
                "real_photograph":True,"wrong_place_risk":.9,"landmark_prominence":.8,"mobile_card_suitability":.8,
                "watermark_or_obstruction":False,"reason_codes":["WRONG_PLACE"]}}
        def report(self): return {"AI_MODE":"FREE_ONLY","stats":{"calls":1},"paid_providers_invoked":0,"paid_feature_calls":0}
    rejected = import_research(file, settings=research_pack[0], apply=True, router=RejectRouter())
    assert rejected["summary"]["rejected"] == 1 and rejected["summary"]["applied"] == 0


@pytest.mark.parametrize("metadata_conflict", [False, True])
def test_image_semicolon_filename_preserves_metadata_and_verification_checks(research_pack, monkeypatch, metadata_conflict):
    from datafactory.sources.wikimedia import WikimediaCommonsClient
    file = image_result(research_pack)
    data = json.loads(file.read_text())
    row = data["results"][0]
    filename = "Garden;_January_2024.jpg"
    page = f"https://commons.wikimedia.org/wiki/File:{filename}"
    row["result"]["source_page_url"] = row["sources"][0]["url"] = page
    atomic_json(file, data)
    info = WikimediaCommonsClient(read_only=True).cache.get("img_Garden.jpg")
    info.update(original_file=filename, source_page=page)
    if metadata_conflict:
        info["author"] = "Different photographer"
    lookups = []
    def image_info(self, requested):
        lookups.append(requested)
        return info
    monkeypatch.setattr(WikimediaCommonsClient, "get_image_info", image_info)
    from datafactory.research.media_evidence import ResearchMediaEvidence
    monkeypatch.setattr(ResearchMediaEvidence, "entity", lambda self, place: None)
    class HoldRouter:
        def analyze(self, *args, **kwargs):
            return {"status":"MEDIA_VERIFICATION_REQUIRED"}
        def report(self):
            return {"AI_MODE":"FREE_ONLY", "stats":{"calls":0}, "paid_providers_invoked":0, "paid_feature_calls":0}
    report = import_research(file, settings=research_pack[0], apply=True, allow_network=True, router=HoldRouter())
    assert lookups == [filename.replace("_", " ")]
    assert report["summary"]["matched"] == report["summary"]["valid"] == 1
    assert report["summary"]["review"] == 1 and report["summary"]["applied"] == 0
    expected = "ORIGINAL_SOURCE_METADATA_CONFLICT" if metadata_conflict else "MEDIA_VERIFICATION_REQUIRED"
    assert expected in report["decisions"][0]["reason_codes"]
    assert "output_pack" not in report and report["ai_usage"]["stats"]["calls"] == 0


def test_manual_image_assurance_webp_complete_export(research_pack):
    from datafactory.pipeline.validate import validate_release_package
    file = image_result(research_pack)
    class AcceptRouter:
        def analyze(self, *args, **kwargs):
            return {"status":"OK", "result":{"decision":"ACCEPT","confidence":.99,"identity_match":True,"identity_confidence":.99,
                "real_photograph":True,"wrong_place_risk":.01,"landmark_prominence":.8,"mobile_card_suitability":.8,
                "watermark_or_obstruction":False,"reason_codes":["FIXTURE_IDENTITY_MATCH"]}}
        def report(self): return {"AI_MODE":"FREE_ONLY","stats":{"calls":1},"paid_providers_invoked":0,"paid_feature_calls":0}
    report = import_research(file, settings=research_pack[0], apply=True, router=AcceptRouter())
    assert report["summary"]["applied"] == 1
    pack = Path(report["output_pack"])
    validate_release_package(pack)
    primary = json.loads((pack / "places.json").read_text())[0]["images"]["primary"]
    assert primary["match_method"] == "research_import" and primary["content_sha256"]
    assert (pack / primary["local_path"]).is_file()
    assert export_research(pack, research_pack[3] / "after_image", settings=research_pack[0])["by_type"]["REAL_PRIMARY_IMAGE"] == 0
    places = json.loads((pack / "places.json").read_text())
    places[0]["images"]["primary"]["license"] = "CC BY 3.0"
    city = json.loads((pack / "city.json").read_text())
    assert any(task["type"] == "REAL_PRIMARY_IMAGE" for task in make_tasks(places, city, pack))


def test_cli_commands(research_pack):
    from datafactory.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["research-export", "--city", "Jaipur", "--all"])
    assert result.exit_code == 0, result.output
    file = result_file(research_pack)
    result = runner.invoke(app, ["research-import", "--file", str(file), "--dry-run"])
    assert result.exit_code == 0 and '"auto_applicable": 1' in result.output


def test_import_schedule_mapping_conflict_and_staleness(research_pack):
    file = result_file(research_pack)
    data = json.loads(file.read_text())
    row = data["results"][0]
    raw = "Mo-Sa 10:00-18:00; Su off"
    row["result"]["source_text"] = raw
    row["sources"][0]["source_text"] = raw
    atomic_json(file, data)
    assert "HOURS_SOURCE_SCHEDULE_CONFLICT" in import_research(file, settings=research_pack[0])["decisions"][0]["reason_codes"]
    row["result"]["opening_hours"] = "24/7"
    row["result"]["source_text"] = row["sources"][0]["source_text"] = "Open 24/7 except Sunday night."
    atomic_json(file, data)
    assert "HOURS_GROUNDED_EXTRACTION_REQUIRED" in import_research(file, settings=research_pack[0])["decisions"][0]["reason_codes"]
    row["result"]["opening_hours"] = "Mo-Sa 09:00-17:00; Su off"
    row["result"]["source_text"] = row["result"]["opening_hours"]
    row["sources"][0]["source_text"] = row["result"]["opening_hours"]
    date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    row["result"]["retrieved_at"] = row["sources"][0]["retrieved_at"] = date
    atomic_json(file, data)
    assert "RECHECK_RECOMMENDED" in import_research(file, settings=research_pack[0])["decisions"][0]["reason_codes"]


def test_unattributed_existing_image_still_requires_identity_review(research_pack):
    file = image_result(research_pack)
    settings, pack, *_ = research_pack
    local = pack / "images/existing.png"
    local.parent.mkdir()
    local.write_bytes(photo())
    places = json.loads((pack / "places.json").read_text())
    places[0]["images"]["gallery"] = [{"image_type":"real", "local_path":"images/existing.png"}]
    # This is a new source snapshot, so register a refreshed handoff before import.
    atomic_json(pack / "places.json", places)
    new = export_research(pack, research_pack[3] / "new", settings=settings)
    data = json.loads(file.read_text())
    data["handoff_id"] = new["handoff_id"]
    atomic_json(file, data)
    report = import_research(file, settings=settings)
    assert report["summary"]["review"] == 1 and report["summary"]["applied"] == 0
    assert "MEDIA_VERIFICATION_REQUIRED" in report["decisions"][0]["reason_codes"]


def test_identity_tasks_and_coordinate_source_matching(research_pack):
    settings, pack, place, output, *_ = research_pack
    city = json.loads((pack / "city.json").read_text())
    assessment = {place["id"]:{"identity_blocker":True,"coordinate":{"status":"CONFLICT"}}}
    atomic_json(pack / "media_assurance.json", assessment)
    exported = export_research(pack, output / "conflicts", settings=settings)
    assert exported["by_type"]["IDENTITY_RESEARCH"] == 1 and exported["by_type"]["COORDINATE_RESEARCH"] == 1
    assert source_quality({"url":"https://www.wikidata.org/wiki/Q99999", "source_id":place["external_ids"]["wikidata_id"]}, place)[1] < .9
    task = next(t for t in json.loads((output / "conflicts/research_handoff.json").read_text())["tasks"] if t["type"] == "IDENTITY_RESEARCH")
    date = datetime.now(timezone.utc).isoformat()
    atomic_json(output / "identity.json", {"schema_version":"1.0","handoff_id":exported["handoff_id"],"results":[{
        "task_id":task["task_id"],"place_id":task["place_id"],"type":task["type"],"status":"FOUND", "result":{"wikidata_id":"Q123"},
        "sources":[{"url":place["contact"]["website"],"source_name":"Official","retrieved_at":date,"source_text":"Identity"}]}]})
    assert "PUBLISHED_IDENTITY_REQUIRES_REVIEW" in import_research(output / "identity.json", settings=settings)["decisions"][0]["reason_codes"]


def test_entity_download_is_independent_of_exhausted_ai_budget(research_pack, monkeypatch):
    import datafactory.pipeline.repair as module
    from datafactory.pipeline.media_assurance import MediaAssurance
    from datafactory.models.media_candidate import MediaCandidate
    from datafactory.ai.router import AIRouter
    from test_ai_assurance import config
    settings, pack, place, *_ = research_pack
    qid = place["external_ids"]["wikidata_id"]
    candidate = MediaCandidate(source="Wikimedia Commons",source_url="https://commons.wikimedia.org/wiki/File:Garden.jpg",
        media_url="https://upload.wikimedia.org/garden.jpg", title="Garden.jpg",creator="Photographer",
        license="CC BY-SA 4.0",license_url="https://creativecommons.org/licenses/by-sa/4.0/",attribution="Photographer / CC BY-SA 4.0",
        width=800,height=600,source_confidence=.99,original_license_verified=True,match_method="wikidata_p18",related_entity_id=qid)
    class Index:
        network_researches = 0
        def __init__(self, *args): pass
        def research(self, value):
            return {"matches":[],"coordinate_evidence":[],"region_associations":[],"media":{"wikidata_p18":"Garden.jpg"},
                    "description_evidence":[],"hours_evidence":[]}
    class Media(MediaAssurance):
        def cached_discovery(self, *args): return [candidate]
        def download(self, *args):
            assert self.allow_network, "Cached P18 download must remain allowed with a zero AI budget"
            return photo()
    monkeypatch.setattr(module,"SourceEvidenceIndex",Index)
    monkeypatch.setattr(module,"MediaAssurance",Media)
    cfg = config()
    cfg.limits.update(calls=0,vision_calls=0,escalations=0)
    router = AIRouter({},settings.cache_dir / "ai",cfg,[])
    report = module.run_repair(pack,allow_network=True,router=router)
    assert report["summary"]["recovered"] == 1 and router.stats["calls"] == 0
