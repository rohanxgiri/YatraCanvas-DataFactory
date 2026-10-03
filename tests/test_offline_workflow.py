import json
import hashlib
from pathlib import Path
import pytest
from datafactory.config.settings import Settings
from datafactory.utils.hashing import compute_sha256
from datafactory.utils.atomic import atomic_json
from datafactory.pipeline.repair import run_repair
from datafactory.pipeline.repair import linked_field_repairs, human_field_locks
from datafactory.pipeline.entity_resolution import CanonicalPlaceGraph
from datafactory.pipeline.usability import usability
from datafactory.utils.source_scope import scope_source_cache
from datafactory.pipeline.source_evidence import SourceEvidenceIndex
from test_ai_assurance import Fake, config
from datafactory.ai.router import AIRouter


def test_canonical_id_collision_is_stable_in_source_order(tmp_path, monkeypatch):
    import datafactory.pipeline.entity_resolution as graph_module
    monkeypatch.setattr(graph_module, "get_settings", lambda: Settings(project_root=tmp_path))
    rows = [{"source":"openstreetmap","source_id":f"node/{i}","name":"Generic Temple","latitude":26.9+delta,
             "longitude":75.8,"category":"religious","subcategory":"hindu_temple","wikidata_id":f"Q{i}"}
            for i,delta in [(1,0),(2,.05)]]
    graph=CanonicalPlaceGraph("Jaipur","Rajasthan","India")
    a=graph.resolve(rows,tmp_path/"a.jsonl")
    b=CanonicalPlaceGraph("Jaipur","Rajasthan","India").resolve(rows[::-1],tmp_path/"b.jsonl")
    assert len({p["canonical_id"] for p in a})==2
    assert {p["canonical_id"] for p in a}=={p["canonical_id"] for p in b}


def test_city_cache_scopes_do_not_reuse_wrong_region(tmp_path, sample_city_metadata):
    class Adapter:
        cache_dir=tmp_path
    atomic_json(tmp_path/"jaipur_attractions.json",[{"name":"Local","latitude":26.9,"longitude":75.8}])
    a=scope_source_cache(Adapter(),sample_city_metadata)
    other=sample_city_metadata.model_copy(update={"state":"Another State","center":(15.0,80.0)})
    b=scope_source_cache(Adapter(),other)
    assert a.cache_dir != b.cache_dir
    assert (a.cache_dir/"jaipur_attractions.json").exists()
    assert not (b.cache_dir/"jaipur_attractions.json").exists()


def test_fallback_never_certifies_core(sample_city_metadata,sample_place,tmp_path):
    p=sample_place.model_dump()
    p["tier"]="core_destination"
    p["images"]["primary"]["image_type"]="fallback"
    result=usability([p],sample_city_metadata.model_dump(),tmp_path,{p["id"]:{"media":{"verified":True}}})
    assert not result["SOURCE_DATA_READY"]
    assert "CORE_MEDIA_UNRESOLVED" in result["places"][0]["critical_blockers"]


def test_retiring_artwork_preserves_photos_and_verified_human_choices():
    from datafactory.pipeline.fallbacks import retire_factory_fallbacks, FACTORY_ARTWORK_SOURCE
    art={"image_type":"fallback", "source":FACTORY_ARTWORK_SOURCE,
         "local_path":"images/a.webp", "thumbnail_path":"images/a-thumb.webp"}
    human={**art,"match_method":"verified_human_curation"}
    photo={**art,"image_type":"real","source":"Wikimedia Commons"}
    places=[{"id":"a","images":{"primary":art,"gallery":[photo]}},
            {"id":"b","images":{"primary":human,"gallery":[]}},
            {"id":"c","images":{"primary":photo,"gallery":[]}}]
    removed=retire_factory_fallbacks(places)
    assert len(removed)==1 and places[0]["images"]["primary"] is None
    assert places[0]["images"]["gallery"]==[photo]
    assert places[1]["images"]["primary"]==human and places[2]["images"]["primary"]==photo


def test_linked_fields_reject_ambiguous_occupied_or_unmatched_sources(sample_place):
    place = sample_place.model_dump()
    place["external_ids"]["wikidata_id"] = None
    place["location"]["address"] = None
    row = {"source":"openstreetmap", "source_id":"way/1", "wikidata_id":"Q123", "address":"Exact source address", "identity_match":True}
    corroboration={"source":"wikidata","source_id":"Q123","identity_match":True}
    evidence = {"matches":[row,corroboration]}
    assert {r["field"] for r in linked_field_repairs(place, evidence, set())} == {"external_ids.wikidata_id","location.address"}
    assert len(linked_field_repairs(place, evidence, {"Q123"})) == 1
    assert linked_field_repairs(place, {"matches":[{**row,"identity_match":False}]}, set()) == []
    assert {r["field"] for r in linked_field_repairs(place, {"matches":[row]},set())} == {"location.address"}
    assert {r["field"] for r in linked_field_repairs(place, {"matches":[row,{**corroboration,"identity_match":False}]},set())} == {"location.address"}
    assert linked_field_repairs(place, {"matches":[row,{**row,"wikidata_id":"Q456","address":"Other"}]},set()) == []


def test_verified_human_fields_are_locked(tmp_path, sample_city_metadata):
    root=tmp_path/"data/curated"/sample_city_metadata.id/"overrides"
    atomic_json(root/"record.json",{"place_id":"p","verified":True,"latitude":26.9,"description":"Human text","address":None})
    locks=human_field_locks(Settings(project_root=tmp_path),sample_city_metadata.model_dump())
    assert {"latitude","description"} <= locks["p"] and "address" not in locks["p"]


def test_identity_review_is_read_only_and_sends_reduced_evidence(tmp_path, sample_city_metadata):
    from datafactory.pipeline.identity_review import audit_identity_manifest
    from datafactory.pipeline.entity_resolution import disambiguate_canonical_ids
    import copy
    rows=[{"canonical_id":"p","name":"Generic Venue","latitude":26.9,"longitude":75.8+i*.01,
           "category":"food","external_ids":{"openstreetmap_ids":[f"node/{i}"]},
           "private_curator_notes":"private-canary"} for i in range(2)]
    source=tmp_path/"candidates.json"
    atomic_json(source,rows)
    before=compute_sha256(source)
    prompts=[]
    provider=Fake(outcome={"decision":"DIFFERENT_PLACE","confidence":.99,"reason_codes":["SOURCE_UNCERTAIN"],
        "supporting_evidence":[],"conflicting_evidence":[]})
    analyze=provider.analyze_json
    provider.analyze_json=lambda prompt,schema: (prompts.append(prompt),analyze(prompt,schema))[1]
    router=AIRouter({},tmp_path/"ai",config(),[provider])
    result=audit_identity_manifest(source,sample_city_metadata.model_dump(),router,tmp_path/"audit.json")
    assert result["groups_found"] == 1 and result["auto_resolved"] == 0
    assert result["decisions"] == {"UPSTREAM_CANONICAL_ID_BUG":1}
    assert compute_sha256(source)==before and "private-canary" not in str(prompts)
    a=disambiguate_canonical_ids(copy.deepcopy(rows))
    b=disambiguate_canonical_ids(copy.deepcopy(rows[::-1]))
    assert {r["canonical_id"] for r in a} == {r["canonical_id"] for r in b}


def test_jaipur_dry_run_is_release_read_only(tmp_path, monkeypatch):
    root=Path(__file__).resolve().parents[1]
    pack=root/"releases/india/rajasthan/jaipur/v3"
    if not pack.exists():
        import pytest
        pytest.skip("Real release snapshot is not packaged in this checkout")
    # No network or release mutation; smoke only a cached deterministically reduced source pack.
    before={p.name:compute_sha256(p) for p in [pack/"places.json",pack/"yatracanvas.db",pack/"manifest.json"]}
    import shutil
    from datafactory.config import settings as settings_module
    shutil.copytree(root/"config",tmp_path/"config")
    shutil.copytree(root/"assets",tmp_path/"assets")
    monkeypatch.setattr(settings_module,"_settings",Settings(project_root=tmp_path))
    router=AIRouter({"city":"Jaipur"},tmp_path/"ai-cache",config(),[])
    report=run_repair(pack,router=router)
    after={p.name:compute_sha256(p) for p in [pack/"places.json",pack/"yatracanvas.db",pack/"manifest.json"]}
    assert before==after and report["mode"]=="DRY_RUN"
    assert report["summary"]["REAL_REQUIRED"]>0


@pytest.mark.parametrize("strategy, usable", [("app",0), ("bundled",100)])
def test_offline_apply_exports_consistently_and_preserves_previous_snapshot(tmp_path, monkeypatch, sample_city_metadata, sample_place, strategy, usable):
    import shutil
    import sqlite3
    import pytest
    from datafactory.config import settings as module
    from datafactory.exporters.json_exporter import export_places_json, export_places_jsonl
    from datafactory.exporters.parquet_exporter import export_places_parquet
    from datafactory.exporters.sqlite_exporter import export_sqlite
    from datafactory.pipeline.validate import validate_release_package
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "config", tmp_path / "config")
    shutil.copytree(root / "assets", tmp_path / "assets")
    settings = Settings(project_root=tmp_path)
    settings.load_yaml("assurance.yaml")["fallbacks"]["strategy"] = strategy
    monkeypatch.setattr(module, "_settings", settings)
    source = tmp_path / "releases/india/rajasthan/jaipur/v3"
    source.mkdir(parents=True)
    place = sample_place.model_copy(deep=True)
    place.images.gallery = [place.images.primary.model_copy()]
    place.images.primary = None
    from datafactory.models.place import PlaceTier
    place.tier = PlaceTier.DISCOVERY
    atomic_json(source / "city.json", sample_city_metadata.model_dump())
    export_places_json([place], source / "places.json")
    export_places_jsonl([place], source / "places.jsonl")
    export_places_parquet([place], source / "places.parquet")
    export_sqlite(sample_city_metadata, [place], source / "yatracanvas.db")
    atomic_json(source / "manifest.json", {"city_id":sample_city_metadata.id,"city_name":sample_city_metadata.name,
        "state":sample_city_metadata.state,"country":sample_city_metadata.country,"generated_at":sample_place.generated_at,
        "counts":{"accepted":1}})
    for filename in ["image_manifest.json", "license_manifest.json", "checksums.json"]:
        atomic_json(source / filename, {})
    atomic_json(source / "source_manifest.json", {"sources":{}})
    original_hash = compute_sha256(source / "places.json")
    router = AIRouter({},tmp_path / "ai", config(), [])
    first = run_repair(source, apply=True, router=router)
    pack = Path(first["output_pack"])
    assert validate_release_package(pack)["total_places"] == 1
    assert first["usability_after"]["overall_usable_percentage"] == usable
    assert first["fallback_strategy"] == strategy
    assert bool(json.loads((pack/"places.json").read_text())[0]["images"]["primary"]) == (strategy == "bundled")
    assert len(first["optional_gallery_pruned"]) == 1
    assert json.loads((pack/"places.json").read_text())[0]["images"]["gallery"] == []
    assert len(json.loads((source/"places.json").read_text())[0]["images"]["gallery"]) == 1
    first_hash = compute_sha256(pack / "manifest.json")
    second = run_repair(source, apply=True, router=router)
    assert Path(second["output_pack"]) != pack
    assert compute_sha256(pack / "manifest.json") == first_hash
    assert compute_sha256(source / "places.json") == original_hash
    if strategy == "bundled":
        settings.load_yaml("assurance.yaml")["fallbacks"]["strategy"] = "app"
        clean = run_repair(pack,apply=True,output_version="v3-app-fallbacks",router=router)
        cleaned_pack = Path(clean["output_pack"])
        assert validate_release_package(cleaned_pack)["total_places"] == 1
        assert len(clean["retired_factory_fallbacks"]) == 1
        assert json.loads((cleaned_pack/"places.json").read_text())[0]["images"]["primary"] is None
        for path in clean["retired_factory_fallbacks"][0]["paths"]:
            assert not (cleaned_pack/path).exists() and (pack/path).is_file()
        assert "fallback_artwork" not in json.loads((cleaned_pack/"source_manifest.json").read_text())["sources"]
        assert compute_sha256(pack/"manifest.json") == first_hash
    with sqlite3.connect(pack / "yatracanvas.db") as conn:
        conn.execute("UPDATE places SET name='Corrupted'")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        validate_release_package(pack)
    checksums = json.loads((pack / "checksums.json").read_text())
    checksums["yatracanvas.db"] = compute_sha256(pack / "yatracanvas.db")
    atomic_json(pack / "checksums.json", checksums)
    with pytest.raises(ValueError, match="SQLite differs"):
        validate_release_package(pack)
