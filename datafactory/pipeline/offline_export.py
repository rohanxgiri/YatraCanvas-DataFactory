"""Transactional draft pack export using existing v3 exporters, preserving source packs."""
import json
import shutil
import uuid
from pathlib import Path
from ..models.city import CityMetadata
from ..models.place import Place
from ..exporters.json_exporter import export_places_json, export_places_jsonl
from ..exporters.parquet_exporter import export_places_parquet
from ..exporters.sqlite_exporter import export_sqlite
from ..utils.atomic import atomic_json
from ..utils.hashing import compute_sha256


def export_offline(source: Path, output: Path, places: list[dict], work_root: Path, report: dict):
    if source.resolve() == output.resolve():
        raise ValueError("Repair output must use a separate version to preserve the audited source pack")
    # Packs are immutable snapshots. A reader or Windows ACL may lock an older
    # directory; never move or overwrite it when publishing a subsequent build.
    if output.exists():
        output = output.with_name(output.name + "." + uuid.uuid4().hex[:12])
    output.parent.mkdir(parents=True, exist_ok=True)
    # Inherit parent ACLs. Python's Windows mkdtemp uses a private ACL that would
    # make a pack inaccessible when sandbox and host users publish alternately.
    temp = output.parent / (".offline-" + uuid.uuid4().hex)
    temp.mkdir()
    shutil.copytree(source, temp, dirs_exist_ok=True)
    from .geographic_assurance import valid_coordinates, coordinates
    if any(not valid_coordinates(*coordinates(p)) for p in places):
        raise ValueError("Invalid coordinates require source review before export")
    parsed = [Place.model_validate(p) for p in places]
    # Copies are new snapshots. Remove retired artwork only from this snapshot,
    # and never remove a path that is still referenced by retained media.
    referenced = {rel for p in parsed for image in ([p.images.primary] if p.images.primary else []) + p.images.gallery
                  for rel in (image.local_path,image.thumbnail_path) if rel}
    for entry in report.get("retired_factory_fallbacks", []):
        for relative in entry["paths"]:
            if relative not in referenced:
                target = (temp / relative).resolve()
                if not target.is_relative_to(temp.resolve()):
                    raise ValueError("Invalid retired artwork path")
                if target.is_file():
                    target.unlink()
    report["optional_gallery_pruned"] = []
    for place in parsed:
        from .media_assurance import local_asset, deterministic_filter
        from .repair import candidate_from_existing
        gallery = []
        used_paths = {p for p in (place.images.primary.local_path,place.images.primary.thumbnail_path) if p} if place.images.primary else set()
        for image in place.images.gallery:
            paths = (image.local_path,image.thumbnail_path)
            # Repair currently produces primary assets only. A replacement at the
            # same path must never be relabelled with an old gallery's provenance.
            assets = [local_asset(source,rel) for rel in paths]
            if any(p in used_paths for p in paths if p):
                reasons = ["DUPLICATE_PRIMARY_OR_GALLERY_PATH"]
            elif all(assets):
                candidate = candidate_from_existing(image.model_dump())
                if not candidate.attribution and candidate.creator and candidate.creator.lower() != "unknown":
                    candidate.attribution = f"{candidate.creator} / {candidate.source} / {candidate.license}"
                    image.attribution = candidate.attribution
                checks = deterministic_filter(candidate,assets[0].read_bytes())
                if checks["accepted"]:
                    gallery.append(image)
                    used_paths.update(paths)
                    continue
                reasons = checks["reason_codes"]
            else:
                reasons = ["OPTIONAL_GALLERY_ASSET_MISSING"]
            report["optional_gallery_pruned"].append({"place_id":place.id,"original_file":image.original_file,
                "local_path":image.local_path,"thumbnail_path":image.thumbnail_path,"reason_codes":reasons})
        place.images.gallery = gallery
        for image in ([place.images.primary] if place.images.primary else []) + gallery:
            for relative in (image.local_path, image.thumbnail_path):
                if relative:
                    asset = local_asset(work_root, relative) or local_asset(source, relative)
                    if asset is None:
                        raise ValueError(f"Missing export media for {place.id}")
                    target = (temp / relative).resolve()
                    if not target.is_relative_to(temp.resolve()):
                        raise ValueError("Invalid asset path")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(asset, target)
    export_places_json(parsed, temp / "places.json")
    export_places_jsonl(parsed, temp / "places.jsonl")
    export_places_parquet(parsed, temp / "places.parquet")
    city = CityMetadata.model_validate(json.loads((source / "city.json").read_text(encoding="utf-8")))
    export_sqlite(city, parsed, temp / "yatracanvas.db")
    if (temp / "city.db").exists():
        shutil.copyfile(temp / "yatracanvas.db", temp / "city.db")
    images = {p.id: p.images.model_dump() for p in parsed if p.images.primary}
    atomic_json(temp / "image_manifest.json", images)
    atomic_json(temp / "images_manifest.json", images)
    atomic_json(temp / "media_assurance.json", report["assurance"])
    atomic_json(temp / "field_provenance.json", report["field_provenance"])
    if report.get("research_import"):
        report["research_import"]["output_pack"] = str(output)
        atomic_json(temp / "research_import.json", report["research_import"])
    from .usability import usability
    final_usability = usability([p.model_dump() for p in parsed], city.model_dump(), temp, report["assurance"])
    report.update(output_pack=str(output), usability_after=final_usability)
    atomic_json(temp / "usability.json", final_usability)
    manifest = json.loads((temp / "manifest.json").read_text(encoding="utf-8"))
    manifest.update(city_pack_version=output.name, offline_assurance={k: v for k, v in final_usability.items() if k != "places"},
                    ai_cost_safety=report["ai_usage"], repair_source_version=source.name)
    if report.get("research_import"):
        manifest["research_handoff"] = {"handoff_id": report["research_import"]["handoff_id"],
                                       "input_sha256": report["research_import"]["input_sha256"]}
    manifest["fallback_presentation"] = {"strategy":report.get("fallback_strategy", "bundled"),
        "missing_photo_representation":"images.primary=null", "required_real_media_checks_unchanged":True}
    manifest["counts"]["accepted"] = len(parsed)
    manifest["counts"]["by_category"] = dict(__import__("collections").Counter(p.classification.category for p in parsed))
    manifest["counts"]["with_images"] = len(images)
    manifest["counts"]["with_descriptions"] = sum(bool(p.description) for p in parsed)
    manifest["counts"]["with_opening_hours"] = sum(bool(p.opening_hours.raw) for p in parsed)
    from collections import Counter
    manifest['counts']['by_tier'] = dict(Counter(p.tier.value for p in parsed))
    for tier, stats in manifest["counts"].get("by_tier_stats", {}).items():
        members = [p for p in parsed if p.tier.value == tier]
        stats['count'] = len(members)
        stats['with_wikidata'] = sum(bool(p.external_ids.wikidata_id) for p in members)
        stats['with_wikipedia'] = sum(any(s.source == 'wikipedia' for s in p.sources) for p in members)
        stats['with_website'] = sum(bool(p.contact.website) for p in members)
        stats['multi_source'] = sum(len(p.sources) > 1 for p in members)
        stats["with_image"] = sum(bool(p.images.primary) for p in members)
        stats["with_hours"] = sum(bool(p.opening_hours.raw) for p in members)
    source_manifest = json.loads((temp / "source_manifest.json").read_text(encoding="utf-8"))
    sources = source_manifest.setdefault("sources", {})
    if any(image and image.source == "YatraCanvas contextual artwork" for p in parsed for image in [p.images.primary, *p.images.gallery]):
        sources["fallback_artwork"] = {
            "source": "YatraCanvas contextual artwork", "license": "CC0", "attribution": "YatraCanvas contributors",
            "role": "Generic category illustrations, always labelled fallback; never destination photography"}
    else:
        sources.pop("fallback_artwork", None)
    source_manifest["sources"]["wikipedia"] = {
        "source": "Wikipedia", "license": "CC BY-SA", "attribution": "Wikipedia contributors",
        "role": "Source excerpts with original article links in field_provenance.json"}
    atomic_json(temp / "source_manifest.json", source_manifest)
    atomic_json(temp / "manifest.json", manifest)
    if report.get('test_media_records'):
        from .test_media import export_test_media_projection
        # Canonical places and strict assurance remain untouched. The opt-in
        # projection owns its own test assets, metadata, and display metrics.
        report['demo_media_metrics'] = export_test_media_projection(temp,
            [p.model_dump(mode='json') for p in parsed], city.model_dump(mode='json'),
            report['assurance'], report['test_media_records'], work_root)
        manifest['test_media_presentation'] = {'default_enabled': False,
            'configuration': 'ALLOW_TEST_MEDIA', 'usage_scope': 'local_testing_only',
            'demo_pack': 'demo', 'manifest': 'test_media_manifest.json',
            'counts_toward_source_readiness': False, 'demo_metrics': report['demo_media_metrics']}
        atomic_json(temp / 'manifest.json', manifest)
    atomic_json(temp / "ai_repair.json", report)
    from ..reports.html_reporter import generate_html_report
    from ..models.manifest import CityManifest
    generate_html_report(city_meta=city, places=parsed, manifest=CityManifest.model_validate(manifest), output_path=temp / "quality_report.html")
    # Every bundled artifact and image is checksummed, except self-referential manifests.
    checksums = {p.relative_to(temp).as_posix(): compute_sha256(p) for p in temp.rglob("*")
                 if p.is_file() and p.name not in {"checksums.json", "manifest.json"}}
    atomic_json(temp / "checksums.json", checksums)
    manifest["checksums"] = checksums
    atomic_json(temp / "manifest.json", manifest)
    from .validate import validate_release_package
    validate_release_package(temp)
    temp.rename(output)
    return output, final_usability
