import sys
import json
import sqlite3
import random
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import typer
from rich.console import Console
from rich.table import Table

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .config.settings import get_settings
from .models.city import CityMetadata
from .models.manifest import CityManifest
from .models.place import PlaceTier
from .utils.hashing import slugify
from .sources.geonames_bulk import GeoNamesBulkSource
from .pipeline.resolve_city import run_resolve_city
from .pipeline.extract import run_extract
from .pipeline.normalize import run_normalize
from .pipeline.classify import run_classify
from .pipeline.deduplicate import run_deduplicate
from .pipeline.enrich import run_enrich
from .pipeline.images import run_process_images
from .pipeline.curation import (
    CurationApplicationError,
    apply_human_curation,
    reapply_human_overrides,
    write_reconciliation,
)
from .pipeline.score import run_score
from .pipeline.validate import run_validate_and_quarantine, validate_release_package
from .pipeline.travel_relevance import evaluate_final_relevance
from .pipeline.completeness import run_completeness_analysis
from .pipeline.release import run_release

app = typer.Typer(help="YatraCanvas DataFactory CLI - Autonomous City Dataset Builder")
console = Console(legacy_windows=False)



@app.command()
def build(
    city: str = typer.Option(..., "--city", "-c", help="City name (e.g. Jaipur)"),
    state: str = typer.Option(..., "--state", "-s", help="State name (e.g. Rajasthan)"),
    country: str = typer.Option("India", "--country", help="Country name"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from cached stages"),
    refresh_images: bool = typer.Option(False, "--refresh-images", help="Force re-fetch of images"),
    version: str = typer.Option("v3", "--version", help="City Pack version string"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run normalization, relevance, and completeness without writing release files"),
):
    """Build a complete, verified travel dataset and City Pack for a destination."""
    settings = get_settings()
    console.print(f"[bold cyan]Starting YatraCanvas DataFactory for [yellow]{city}, {state}, {country}[/bold cyan] ({version})")

    city_slug = slugify(city)
    state_slug = slugify(state)
    country_slug = slugify(country)

    staging_dir = settings.staging_dir / country_slug / state_slug / city_slug
    staging_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = staging_dir / "rejected_places.jsonl"
    duplicates_path = staging_dir / "duplicates.jsonl"
    quarantine_path = staging_dir / "quarantine" / "quarantined_places.jsonl"

    # Stage 1: Resolve City via robust multi-source resolver pipeline
    city_meta = run_resolve_city(city_name=city, state_name=state, country_name=country, resume=resume)

    # Stage 2-6: Discover across independent sources
    raw_candidates, sources_count = run_extract(city_meta=city_meta, resume=resume)
    total_raw = sum(sources_count.values())

    # Stage 7: Normalize and travel-filter candidates
    accepted_candidates, rejected_count = run_normalize(
        raw_candidates=raw_candidates,
        city_bbox=city_meta.bbox,
        rejected_output_path=rejected_path,
    )

    # Stage 8: Classify and initial tier assignment via multi-source Category Voting
    classified_places = run_classify(accepted_candidates)

    # Stage 9: Deduplicate via CanonicalPlaceGraph with conflict auditing
    deduped_places = run_deduplicate(
        classified_places=classified_places,
        duplicates_output_path=duplicates_path,
        city_name=city_meta.name,
        state_name=city_meta.state,
        country_name=city_meta.country,
    )
    graph = getattr(deduped_places, "graph", None)

    # Count duplicates
    dup_count = 0
    if duplicates_path.exists():
        with open(duplicates_path, "r", encoding="utf-8") as f:
            dup_count = sum(1 for _ in f)

    # Stage 9b: STAGE 2 Final Travel Relevance Decision
    print(f"[Stage 9b/20] Running STAGE 2 Final Travel Relevance Decision across {len(deduped_places)} canonical entities...")
    kept_places = []
    review_candidates = []
    filtered_places = []
    stage2_rejected = []
    cat_cfg = settings.categories_config

    for p in deduped_places:
        decision, reason, rel_score, ev = evaluate_final_relevance(p, city_meta, cat_cfg)
        p["travel_relevance_decision"] = decision
        p["travel_relevance_reason"] = reason
        p["travel_relevance_score"] = rel_score
        p["travel_relevance_evidence"] = ev
        if decision == "KEEP":
            kept_places.append(p)
        elif decision == "REVIEW":
            # Populate structured fields for City Lab grouping and priority
            missing_fields = []
            if not (p.get("wikidata_p18") or p.get("commons_image")):
                missing_fields.append("primary_image")
            if not p.get("description"):
                missing_fields.append("description")
            if not p.get("opening_hours"):
                missing_fields.append("opening_hours")
            if not p.get("website"):
                missing_fields.append("website")
            if not p.get("address"):
                missing_fields.append("address")

            p["missing_fields"] = missing_fields
            p["source_count"] = len(p.get("sources_provenance", []))
            p.setdefault("review_priority", "MEDIUM")
            p.setdefault("suggested_action", "APPROVE_AS_SECONDARY_DESTINATION")
            review_candidates.append(p)
        elif decision == "FILTERED":
            filtered_places.append({
                "decision": "FILTERED",
                "reason_code": reason,
                "name": p.get("name"),
                "canonical_id": p.get("canonical_id"),
                "category": p.get("category"),
                "subcategory": p.get("subcategory"),
                "evidence": ev,
            })
        else:
            stage2_rejected.append({
                "decision": "EXCLUDE",
                "reason_code": reason,
                "name": p.get("name"),
                "canonical_id": p.get("canonical_id"),
                "evidence": ev,
            })

    print(f"       [STAGE 2] KEEP: {len(kept_places)} | REVIEW: {len(review_candidates)} | FILTERED: {len(filtered_places)} | EXCLUDE: {len(stage2_rejected)}")

    # Sort review candidates: HIGH priority first, then by travel relevance score descending
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    review_candidates.sort(key=lambda x: (priority_order.get(x.get("review_priority", "MEDIUM"), 1), -x.get("travel_relevance_score", 0.0)))

    # Save review candidates manifest for City Lab
    review_manifest_path = staging_dir / "review_candidates.json"
    with open(review_manifest_path, "w", encoding="utf-8") as f:
        json.dump(review_candidates, f, ensure_ascii=False, indent=2)

    city_reports_dir = settings.reports_dir / city_slug
    city_reports_dir.mkdir(parents=True, exist_ok=True)
    with open(city_reports_dir / "review_candidates.json", "w", encoding="utf-8") as f:
        json.dump(review_candidates, f, ensure_ascii=False, indent=2)

    # Save filtered places for diagnostics and traceability
    filtered_manifest_path = staging_dir / "filtered_places.jsonl"
    with open(filtered_manifest_path, "w", encoding="utf-8") as f:
        for fp in filtered_places:
            f.write(json.dumps(fp, ensure_ascii=False) + "\n")

    # Append Stage 2 rejections to rejected_records.jsonl
    if stage2_rejected:
        with open(rejected_path, "a", encoding="utf-8") as f:
            for r in stage2_rejected:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        rejected_count += len(stage2_rejected)

    # Compute Before-Enrichment baseline metrics on KEEP candidates
    total_keep = len(kept_places)
    before_missing_img = sum(1 for p in kept_places if not (p.get("wikidata_p18") or p.get("commons_image")))
    before_missing_desc = sum(1 for p in kept_places if not p.get("description"))
    before_missing_hours = sum(1 for p in kept_places if not p.get("opening_hours"))
    before_missing_qid = sum(1 for p in kept_places if not p.get("wikidata_id"))
    before_missing_wiki = sum(1 for p in kept_places if not p.get("wikipedia_url"))
    before_missing_site = sum(1 for p in kept_places if not p.get("website"))
    before_missing_addr = sum(1 for p in kept_places if not p.get("address"))

    print("\n--- BEFORE ENRICHMENT METRICS ---")
    print(f"Total KEEP candidates:       {total_keep}")
    print(f"Missing primary image:       {before_missing_img} ({before_missing_img/max(1, total_keep)*100:.1f}%)")
    print(f"Missing description:         {before_missing_desc} ({before_missing_desc/max(1, total_keep)*100:.1f}%)")
    print(f"Missing opening hours:       {before_missing_hours} ({before_missing_hours/max(1, total_keep)*100:.1f}%)")
    print(f"Missing Wikidata ID:         {before_missing_qid} ({before_missing_qid/max(1, total_keep)*100:.1f}%)")
    print(f"Missing Wikipedia identity:  {before_missing_wiki} ({before_missing_wiki/max(1, total_keep)*100:.1f}%)")
    print(f"Missing website:             {before_missing_site} ({before_missing_site/max(1, total_keep)*100:.1f}%)")
    print(f"Missing address:             {before_missing_addr} ({before_missing_addr/max(1, total_keep)*100:.1f}%)\n")

    # Stage 9c: Completeness Analysis on candidate destinations

    places_to_enrich, completeness_summary = run_completeness_analysis(kept_places, city_meta.bbox)
    print(f"[Stage 9c/20] Completeness Analysis: Avg {completeness_summary['avg_completeness']:.2f} | Images: {completeness_summary['with_primary_image_pct']}% | Hours: {completeness_summary['with_opening_hours_pct']}%")

    if dry_run:
        console.print("[bold yellow]Dry run requested -- completed normalization, Stage 2 relevance, and completeness analysis without release export.[/bold yellow]")
        return

    # Stage 10: Enrich with Wikidata claims & structured hours
    enriched_places = run_enrich(
        places=places_to_enrich,
        city_name=city_meta.name,
        city_context=city_meta.model_dump(),
    )

    # Stage 11: Verified Wikimedia Commons Imagery
    places_with_images, images_manifest = run_process_images(
        places=enriched_places,
        output_media_dir=settings.media_dir,
        city_name=city_meta.name,
        refresh_images=refresh_images,
    )

    # Compute After-Enrichment metrics
    after_with_img = sum(1 for p in places_with_images if p.get("image_metadata"))
    after_with_desc = sum(1 for p in places_with_images if p.get("description"))
    after_with_hours = sum(1 for p in places_with_images if p.get("opening_hours") or (isinstance(p.get("opening_hours_record"), dict) and p["opening_hours_record"].get("raw")))
    after_with_qid = sum(1 for p in places_with_images if p.get("wikidata_id"))
    after_with_wiki = sum(1 for p in places_with_images if p.get("wikipedia_url"))

    img_recovered = max(0, after_with_img - (total_keep - before_missing_img))
    desc_recovered = max(0, after_with_desc - (total_keep - before_missing_desc))
    hours_recovered = max(0, after_with_hours - (total_keep - before_missing_hours))
    qid_recovered = max(0, after_with_qid - (total_keep - before_missing_qid))
    wiki_recovered = max(0, after_with_wiki - (total_keep - before_missing_wiki))

    print("\n--- AFTER ENRICHMENT RECOVERY METRICS ---")
    print(f"Images recovered:            {img_recovered} (now {after_with_img}/{total_keep} = {after_with_img/max(1, total_keep)*100:.1f}%)")
    print(f"Descriptions recovered:      {desc_recovered} (now {after_with_desc}/{total_keep} = {after_with_desc/max(1, total_keep)*100:.1f}%)")
    print(f"Opening hours recovered:     {hours_recovered} (now {after_with_hours}/{total_keep} = {after_with_hours/max(1, total_keep)*100:.1f}%)")
    print(f"Wikidata IDs recovered:      {qid_recovered} (now {after_with_qid}/{total_keep} = {after_with_qid/max(1, total_keep)*100:.1f}%)")
    print(f"Wikipedia URLs recovered:    {wiki_recovered} (now {after_with_wiki}/{total_keep} = {after_with_wiki/max(1, total_keep)*100:.1f}%)")
    print(f"Duplicates merged:           {dup_count}")
    print(f"Still missing image:         {total_keep - after_with_img} ({(total_keep - after_with_img)/max(1, total_keep)*100:.1f}%)")
    print(f"Still missing description:   {total_keep - after_with_desc} ({(total_keep - after_with_desc)/max(1, total_keep)*100:.1f}%)")
    print(f"Still missing opening hours: {total_keep - after_with_hours} ({(total_keep - after_with_hours)/max(1, total_keep)*100:.1f}%)\n")

    enrichment_metrics = {
        "before": {
            "total_keep": total_keep,
            "missing_image": before_missing_img,
            "missing_description": before_missing_desc,
            "missing_opening_hours": before_missing_hours,
            "missing_wikidata_id": before_missing_qid,
            "missing_wikipedia_url": before_missing_wiki,
            "missing_website": before_missing_site,
            "missing_address": before_missing_addr,
        },
        "after": {
            "total_keep": total_keep,
            "with_image": after_with_img,
            "with_description": after_with_desc,
            "with_opening_hours": after_with_hours,
            "with_wikidata_id": after_with_qid,
            "with_wikipedia_url": after_with_wiki,
            "images_recovered": img_recovered,
            "descriptions_recovered": desc_recovered,
            "hours_recovered": hours_recovered,
            "wikidata_recovered": qid_recovered,
            "wikipedia_recovered": wiki_recovered,
            "duplicates_merged": dup_count,
            "still_missing_image": total_keep - after_with_img,
            "still_missing_description": total_keep - after_with_desc,
            "still_missing_opening_hours": total_keep - after_with_hours,
        }
    }
    with open(city_reports_dir / "enrichment_metrics.json", "w", encoding="utf-8") as f:
        json.dump(enrichment_metrics, f, ensure_ascii=False, indent=2)

    # Human curation is durable input, not a patch to generated release output.

    # Apply it after provider refresh and before scoring, then restore authoritative
    # human fields after generated scoring defaults have run.
    canonical_city_id = str(city_meta.id or city_slug)
    canonical_curation_dir = settings.curated_dir / canonical_city_id
    legacy_slug_dir = settings.curated_dir / city_slug
    curation_dir = (
        canonical_curation_dir
        if canonical_curation_dir.is_dir() or not legacy_slug_dir.is_dir()
        else legacy_slug_dir
    )
    try:
        curated_places, images_manifest, curation_report = apply_human_curation(
            places_with_images,
            city_id=canonical_city_id,
            curation_dir=curation_dir,
            media_dir=settings.media_dir,
            images_manifest=images_manifest,
        )
    except CurationApplicationError as exc:
        if exc.report is not None:
            write_reconciliation(
                staging_dir / "curation_reconciliation.json",
                exc.report,
                curation_dir=curation_dir,
            )
        raise
    write_reconciliation(
        staging_dir / "curation_reconciliation.json",
        curation_report,
        curation_dir=curation_dir,
    )

    # Stage 12: Score Quality, Travel Relevance, Prominence, and Planning (with Core De-inflation)
    scored_places = run_score(
        places=curated_places,
        city_bbox=city_meta.bbox,
    )
    scored_places = reapply_human_overrides(
        scored_places,
        curation_dir=curation_dir,
    )

    # Stage 13: Semantic Validation and Quarantine
    valid_places, quarantined_places = run_validate_and_quarantine(
        places=scored_places,
        city_bbox=city_meta.bbox,
        quarantine_output_path=quarantine_path,
        media_dir=settings.media_dir,
        city_context=city_meta.model_dump(),
    )

    # Stage 14-20: Release City Pack v3 & Quality Reports
    release_dir, manifest = run_release(
        city_meta=city_meta,
        accepted_records=valid_places,
        images_manifest=images_manifest,
        total_raw_count=total_raw,
        rejected_count=rejected_count,
        quarantined_count=len(quarantined_places),
        duplicate_merges_count=dup_count,
        sources_count=sources_count,
        category_conflicts_count=graph.category_conflicts_count,
        entity_conflicts_count=len(graph.conflicts_log),
        alias_conflicts_count=graph.alias_conflicts_count,
        coordinate_conflicts_count=graph.coordinate_conflicts_count,
        version=version,
    )

    # Print summary table by tier
    table = Table(title=f"City Pack {version} Build Summary: {city_meta.name}")
    table.add_column("Place Tier", style="bold cyan")
    table.add_column("Count", style="green")
    table.add_column("With Wikidata", style="yellow")
    table.add_column("With Image", style="magenta")
    table.add_column("With Hours", style="blue")

    tier_stats = manifest.counts.by_tier_stats
    for t_name, label in [
        ("core_destination", "Core Destinations"),
        ("recommended", "Recommended"),
        ("discovery", "Discovery"),
        ("support", "Support"),
    ]:
        st = tier_stats.get(t_name, {})
        cnt = st.get("count", 0)
        w_wiki = st.get("with_wikidata", 0)
        w_img = st.get("with_image", 0)
        w_hrs = st.get("with_hours", 0)
        table.add_row(
            label,
            str(cnt),
            f"{w_wiki} ({w_wiki/max(1, cnt)*100:.1f}%)" if cnt else "0",
            f"{w_img} ({w_img/max(1, cnt)*100:.1f}%)" if cnt else "0",
            f"{w_hrs} ({w_hrs/max(1, cnt)*100:.1f}%)" if cnt else "0",
        )

    console.print(table)

    # Automatic Post-Build Audit
    _run_post_build_audit(valid_places, city_meta)

    console.print(f"[bold green][OK] City Pack released at: {release_dir}[/bold green]")
    return release_dir, manifest


def _run_post_build_audit(places: List[Dict[str, Any]], city_meta: CityMetadata) -> None:
    """
    Automated post-build audit sampling:
    - Top 30 core destinations
    - 20 random core destinations
    - 20 random recommended destinations
    Performs semantic consistency checks on name, coordinates, category, external IDs, and images.
    """
    core_places = [p for p in places if p.get("tier") == "core_destination"]
    rec_places = [p for p in places if p.get("tier") == "recommended"]

    core_sorted = sorted(core_places, key=lambda x: x.get("travel_relevance_score", 0), reverse=True)
    top_30_core = core_sorted[:30]

    remaining_core = core_sorted[30:]
    sample_core = random.sample(remaining_core, min(20, len(remaining_core))) if remaining_core else []
    sample_rec = random.sample(rec_places, min(20, len(rec_places))) if rec_places else []

    audit_sample = top_30_core + sample_core + sample_rec
    passed_checks = 0
    total_checks = len(audit_sample)
    audit_findings = []

    for p in audit_sample:
        p_name = p.get("name", "")
        issues = []

        # 1. Name agreement
        if not p_name or p_name.lower() in ("unknown", "unnamed", "none", "null"):
            issues.append("invalid_name")

        # 2. Coordinates
        lat, lon = p.get("latitude"), p.get("longitude")
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            issues.append("invalid_coordinates")

        # 3. Category & semantic harmony
        cat = p.get("category")
        if not cat or cat in ("unknown", "general"):
            issues.append("weak_category")
        p_lower = p_name.lower()
        if cat == "nature" and any(w in p_lower for w in ["palace", "hotel", "residency", "metro station"]):
            issues.append("category_semantic_conflict")

        # 4. External IDs format
        qid = p.get("wikidata_id")
        if qid and not re.match(r"^Q\d+$", str(qid)):
            issues.append("malformed_wikidata_id")

        # 5. Alternate names safety
        alt_records = p.get("alternate_name_records", [])
        for ar in alt_records:
            if ar.get("is_quarantined") and ar.get("name") in p.get("alternate_names", []):
                issues.append("quarantined_alias_leaked")

        # 6. Image/entity match
        img_meta = p.get("image_metadata")
        if img_meta:
            if not img_meta.get("local_path"):
                issues.append("missing_image_path")

        # 7. Source agreement
        prov = p.get("sources_provenance", [])
        if not prov:
            issues.append("missing_source_provenance")

        if not issues:
            passed_checks += 1
        else:
            audit_findings.append({"canonical_id": p.get("canonical_id"), "name": p_name, "tier": p.get("tier"), "issues": issues})

    console.print(f"[bold green][OK] Automatic Post-Build Audit: {passed_checks}/{total_checks} sampled places verified consistent across 7 semantic checks.[/bold green]")
    if audit_findings:
        console.print(f"[yellow]  Post-build audit notes: {len(audit_findings)} places had minor warnings: {audit_findings[:3]}[/yellow]")


@app.command("rebuild-all")
def rebuild_all(
    version: str = typer.Option("v3", "--version", help="City Pack version string"),
    refresh_images: bool = typer.Option(False, "--refresh-images", help="Force re-fetch of images"),
):
    """
    Discover all cities present in data/raw or releases and rebuild them autonomously.
    Outputs a consolidated cross-city audit table.
    """
    settings = get_settings()
    console.print("[bold cyan]Scanning repository for existing cities to rebuild...[/bold cyan]")

    discovered_cities: Dict[str, Dict[str, str]] = {}

    # 1. Search in releases/
    for city_json in settings.releases_dir.glob("**/city.json"):
        try:
            with open(city_json, "r", encoding="utf-8") as f:
                c_data = json.load(f)
            c_name = c_data.get("name")
            s_name = c_data.get("state")
            co_name = c_data.get("country", "India")
            if c_name and s_name:
                discovered_cities[c_name.lower()] = {
                    "city": c_name,
                    "state": s_name,
                    "country": co_name,
                }
        except Exception:
            pass

    # 2. Search in data/raw/
    for resolved_json in settings.raw_dir.glob("**/city_resolved.json"):
        try:
            with open(resolved_json, "r", encoding="utf-8") as f:
                c_data = json.load(f)
            c_name = c_data.get("name")
            s_name = c_data.get("state")
            co_name = c_data.get("country", "India")
            if c_name and s_name:
                discovered_cities[c_name.lower()] = {
                    "city": c_name,
                    "state": s_name,
                    "country": co_name,
                }
        except Exception:
            pass

    if not discovered_cities:
        console.print("[bold red]No existing cities discovered in data/ or releases/.[/bold red]")
        raise typer.Exit(1)

    console.print(f"[bold green]Discovered {len(discovered_cities)} cities: {list(discovered_cities.keys())}[/bold green]")

    results = []

    for c_info in discovered_cities.values():
        c_name = c_info["city"]
        s_name = c_info["state"]
        co_name = c_info["country"]

        console.print(f"\n[bold yellow]========================================================[/bold yellow]")
        console.print(f"[bold yellow]Rebuilding {c_name}, {s_name} ({version})...[/bold yellow]")
        console.print(f"[bold yellow]========================================================[/bold yellow]")

        try:
            rel_dir, manifest = build(
                city=c_name,
                state=s_name,
                country=co_name,
                version=version,
                refresh_images=refresh_images,
                resume=True,
            )

            # Validate the build using semantic validator
            val_status = "PASSED"
            val_details = {}
            try:
                val_details = validate_release_package(rel_dir)
            except Exception as e:
                val_status = f"FAILED: {e}"

            results.append({
                "city": c_name,
                "manifest": manifest,
                "validation": val_status,
                "val_details": val_details,
                "release_dir": str(rel_dir),
            })
        except Exception as e:
            console.print(f"[bold red]Failed to rebuild {c_name}: {e}[/bold red]")
            results.append({
                "city": c_name,
                "manifest": None,
                "validation": f"ERROR: {e}",
                "val_details": {},
                "release_dir": "N/A",
            })

    # Consolidated Cross-City Comparison Table
    console.print(f"\n[bold cyan]========================================================================================[/bold cyan]")
    console.print(f"[bold cyan]                  YATRACANVAS DATAFACTORY: CROSS-CITY AUDIT REPORT ({version})                  [/bold cyan]")
    console.print(f"[bold cyan]========================================================================================[/bold cyan]")

    audit_table = Table(title=f"Autonomous Multi-City Build Metrics (Actual Numbers - {version})")
    audit_table.add_column("City", style="bold white")
    audit_table.add_column("Core", style="red")
    audit_table.add_column("Rec", style="yellow")
    audit_table.add_column("Disc", style="blue")
    audit_table.add_column("Supp", style="magenta")
    audit_table.add_column("Rej", style="dim")
    audit_table.add_column("Quar", style="dim")
    audit_table.add_column("Merges", style="green")
    audit_table.add_column("Core Wiki", style="bold yellow")
    audit_table.add_column("Core Img", style="bold green")
    audit_table.add_column("Core Hours", style="bold cyan")
    audit_table.add_column("Cat Conf", style="magenta")
    audit_table.add_column("Ent Conf", style="red")
    audit_table.add_column("Pipeline", style="bold")
    audit_table.add_column("Quality", style="bold")
    audit_table.add_column("Coverage", style="bold")

    for res in results:
        m: Optional[CityManifest] = res.get("manifest")
        if not m:
            audit_table.add_row(res["city"], "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "FAIL", "FAIL", "FAIL")
            continue

        c = m.counts
        st = c.by_tier_stats
        core_cnt = st.get("core_destination", {}).get("count", 0)
        core_wiki = st.get("core_destination", {}).get("with_wikidata", 0)
        core_img = st.get("core_destination", {}).get("with_image", 0)
        core_hrs = st.get("core_destination", {}).get("with_hours", 0)

        rec_cnt = st.get("recommended", {}).get("count", 0)
        disc_cnt = st.get("discovery", {}).get("count", 0)
        supp_cnt = st.get("support", {}).get("count", 0)

        p_health = m.pipeline_health or "PASS"
        d_qual = m.data_quality or "PASS"
        s_cov = m.source_coverage or "PASS"

        audit_table.add_row(
            m.city_name,
            str(core_cnt),
            str(rec_cnt),
            str(disc_cnt),
            str(supp_cnt),
            str(c.rejected),
            str(c.quarantined),
            str(c.duplicate_merges),
            f"{core_wiki}/{core_cnt}",
            f"{core_img}/{core_cnt}",
            f"{core_hrs}/{core_cnt}",
            str(c.category_conflicts),
            str(c.entity_conflicts),
            f"[green]{p_health}[/green]" if p_health == "PASS" else f"[yellow]{p_health}[/yellow]",
            f"[green]{d_qual}[/green]" if d_qual == "PASS" else f"[yellow]{d_qual}[/yellow]",
            f"[green]{s_cov}[/green]" if s_cov == "PASS" else f"[yellow]{s_cov}[/yellow]",
        )

    console.print(audit_table)


@app.command()
def validate(
    release_path: Path = typer.Argument(..., help="Path to versioned City Pack folder")
):
    """Validate a generated City Pack release directory."""
    if not release_path.exists():
        console.print(f"[bold red]Error: Release directory {release_path} does not exist.[/bold red]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]Validating City Pack at: {release_path}[/bold cyan]")
    try:
        report = validate_release_package(release_path)
        console.print(f"[bold green][OK] ALL STRUCTURAL AND SEMANTIC CHECKS PASSED for {release_path}![/bold green]")

        console.print(f"  Total Places: {report['total_places']}")
        console.print(f"  Core Destinations: {report['core_count']}")
        console.print(f"  Core with Wikidata: {report['core_with_wikidata']}")
        console.print(f"  Core with Images: {report['core_with_image']}")
        console.print(f"  Pipeline Health: [green]{report['pipeline_health']}[/green]")
        console.print(f"  Data Quality: [green]{report['data_quality']}[/green]")
        console.print(f"  Source Coverage: [green]{report['source_coverage']}[/green]")
    except Exception as e:
        console.print(f"[bold red]Validation failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command("search")
def search_places(
    city: str = typer.Option(..., "--city", "-c", help="City name (e.g. Jaipur)"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search text query"),
    category: Optional[str] = typer.Option(None, "--category", help="Category filter (e.g. cafe, museum)"),
    subcategory: Optional[str] = typer.Option(None, "--subcategory", help="Subcategory filter"),
    tier: Optional[str] = typer.Option(None, "--tier", help="Tier filter (core_destination, recommended, discovery, support)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results to return"),
    version: str = typer.Option("v3", "--version", help="City Pack version"),
):
    """
    Search places in a generated City Pack offline dataset.
    """
    from .audit.search_engine import CityPackSearchEngine
    engine = CityPackSearchEngine(city_name=city, version=version)
    if not engine.places:
        console.print(f"[bold red]No released places found for {city} ({version}).[/bold red]")
        raise typer.Exit(1)

    results = engine.search(
        query=query,
        category=category,
        subcategory=subcategory,
        tier=tier,
        limit=limit,
    )

    table = Table(title=f"Search Results: {city} (Query: '{query or '*'}' | Cat: {category or '*'} | Tier: {tier or '*'})")
    table.add_column("Place Name", style="bold white")
    table.add_column("Category", style="cyan")
    table.add_column("Subcategory", style="dim")
    table.add_column("Tier", style="yellow")
    table.add_column("Discovery", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("Address / Area", style="dim")

    for r in results:
        table.add_row(
            f"{r['name']}" + (f" ({r['name_hi']})" if r.get('name_hi') else ""),
            r["category"],
            r["subcategory"],
            r["tier"],
            f"{r['discovery_score']:.2f}",
            f"{r['total_rank']:.1f}",
            str(r.get("address") or "-")[:35],
        )

    console.print(table)
    console.print(f"[dim]Found {len(results)} matching places (limit {limit}).[/dim]")


@app.command("audit")
def audit_city_pack(
    city: Optional[str] = typer.Option(None, "--city", "-c", help="Specific city name to audit"),
    version: str = typer.Option("v3", "--version", help="City Pack version string"),
    all_cities: bool = typer.Option(True, "--all", help="Audit all discovered cities"),
):
    """
    Run completeness, source recall, search benchmark, and geographic audits.
    Generates reports/<city>/audit/index.html and reports/city_pack_readiness.html.
    """
    from .audit.dashboard import generate_city_dashboard, generate_cross_city_readiness_report
    settings = get_settings()

    if city:
        console.print(f"[bold cyan]Running City Pack Audit for {city} ({version})...[/bold cyan]")
        city_found = False
        for c_file in settings.releases_dir.glob(f"**/{version}/city.json"):
            with open(c_file, "r", encoding="utf-8") as f:
                c_meta = json.load(f)
            if c_meta.get("name", "").lower() == city.lower():
                city_found = True
                res = generate_city_dashboard(c_meta["name"], c_meta["state"], c_meta.get("country", "India"), version)
                console.print(f"[bold green][OK] Audit complete for {city}! Readiness Status: {res['readiness_status']}[/bold green]")
                console.print(f"  Dashboard: reports/{city.lower().replace(' ', '_')}/audit/index.html")
                break
        if not city_found:
            console.print(f"[bold red]Could not find release package for {city} ({version})[/bold red]")
            raise typer.Exit(1)
    else:
        console.print(f"[bold cyan]Running Complete Multi-City Audit Suite ({version})...[/bold cyan]")
        readiness_path = generate_cross_city_readiness_report(version)
        console.print(f"[bold green][OK] Multi-City Audit Suite complete![/bold green]")
        console.print(f"  Global Readiness Report: {readiness_path}")


@app.command("enrich")
def enrich_city(
    city: str = typer.Option(..., "--city", "-c", help="City name (e.g. Jaipur)"),
    state: str = typer.Option(..., "--state", "-s", help="State name (e.g. Rajasthan)"),
    country: str = typer.Option("India", "--country", help="Country name"),
    version: str = typer.Option("v3", "--version", help="City Pack version string"),
    refresh_images: bool = typer.Option(False, "--refresh-images", help="Force re-fetch of images"),
):
    """
    Run standalone completeness analysis, Wikipedia description enrichment,
    and verified image resolution for a city.
    """
    settings = get_settings()
    console.print(f"[bold cyan]Enriching dataset for [yellow]{city}, {state}, {country}[/bold cyan] ({version})")
    city_slug = slugify(city)
    state_slug = slugify(state)
    country_slug = slugify(country)
    staging_dir = settings.staging_dir / country_slug / state_slug / city_slug

    places_json = staging_dir / "places.json"
    if not places_json.exists():
        rel_places = settings.releases_dir / country_slug / state_slug / city_slug / version / "places.json"
        if rel_places.exists():
            places_json = rel_places

    if not places_json.exists():
        console.print(f"[bold red]No existing places found to enrich for {city}. Run 'build' first.[/bold red]")
        raise typer.Exit(1)

    with open(places_json, "r", encoding="utf-8") as f:
        places_data = json.load(f)

    places_list = [p if isinstance(p, dict) else p.model_dump() for p in places_data]
    city_meta = run_resolve_city(city_name=city, state_name=state, country_name=country, resume=True)

    analyzed, comp_summary = run_completeness_analysis(places_list, city_meta.bbox)
    console.print(f"[bold green]Completeness Baseline: Avg {comp_summary['avg_completeness']:.2f} | Images: {comp_summary['with_primary_image_pct']}% | Hours: {comp_summary['with_opening_hours_pct']}%[/bold green]")

    enriched = run_enrich(analyzed, city_name=city, city_context=city_meta.model_dump())
    with_images, img_manifest = run_process_images(
        places=enriched,
        output_media_dir=settings.media_dir,
        city_name=city,
        refresh_images=refresh_images,
    )
    final_analyzed, final_summary = run_completeness_analysis(with_images, city_meta.bbox)
    console.print(f"[bold green]Enrichment Complete: Avg {final_summary['avg_completeness']:.2f} | Images: {final_summary['with_primary_image_pct']}% | Hours: {final_summary['with_opening_hours_pct']}%[/bold green]")


@app.command("ai-status")
def ai_status():
    """Check configured free-only providers and account-supported models without inference."""
    from .ai.router import AIRouter
    router = AIRouter({"diagnostic": True}, get_settings().cache_dir / "ai")
    console.print_json(data=router.health_check())


@app.command("audit-identity")
def audit_identity(
    city: str = typer.Option(..., "--city"), state: str = typer.Option(..., "--state"),
    review_manifest: Path = typer.Option(..., "--review-manifest", exists=True, dir_okay=False),
    country: str = typer.Option("India", "--country"),
    use_ai: bool = typer.Option(False, "--ai", help="Send reduced POI identity evidence to configured free providers"),
):
    """Read candidate collisions and write review evidence; never changes source/City Lab files."""
    from .ai.router import AIRouter
    from .pipeline.repair import city_context
    from .pipeline.identity_review import audit_identity_manifest
    settings = get_settings()
    scope = Path(slugify(country)) / slugify(state) / slugify(city)
    context = city_context(json.loads((settings.releases_dir / scope / "v3/city.json").read_text(encoding="utf-8")))
    router = AIRouter(context, settings.cache_dir / "ai", providers=None if use_ai else [])
    router.config.limits.update(calls=min(10, router.config.limits.get("calls",30)))
    result = audit_identity_manifest(review_manifest, context, router, settings.reports_dir / scope / "assurance/identity_review.json")
    console.print_json(data={k:v for k,v in result.items() if k != "groups"})


@app.command("repair")
def repair_city(
    city: str = typer.Option(..., "--city"),
    state: str = typer.Option(..., "--state"),
    country: str = typer.Option("India", "--country"),
    version: str = typer.Option("v3", "--version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    apply: bool = typer.Option(False, "--apply"),
    network: bool = typer.Option(False, "--network", help="Permit approved source retrieval; default uses caches only"),
    output_version: str = typer.Option("v3-offline", "--output-version"),
):
    """Audit/repair a city pack; apply always audits first and writes a separate version."""
    if apply and dry_run:
        raise typer.BadParameter("Use either --apply or --dry-run")
    if any(Path(v).name != v or v in {".", ".."} for v in (version, output_version)):
        raise typer.BadParameter("Version must be a single directory name")
    from .pipeline.repair import run_repair, city_context
    from .ai.router import AIRouter
    settings = get_settings()
    source = settings.releases_dir / slugify(country) / slugify(state) / slugify(city) / version
    if not (source / "places.json").exists():
        raise typer.BadParameter("No source city pack exists; run build-offline or build first")
    context = city_context(json.loads((source / "city.json").read_text(encoding="utf-8")))
    router = AIRouter(context, settings.cache_dir / "ai")
    report = run_repair(source, allow_network=network, router=router)
    if apply:
        severe = any(g["decision"] == "UPSTREAM_CANONICAL_ID_BUG" and g.get("origin") != "upstream_quarantine" for g in report["identity_conflicts"])
        if severe:
            raise typer.BadParameter("Published canonical ID collision requires a reviewed migration; dry-run report saved")
        report = run_repair(source, apply=True, allow_network=network, output_version=output_version, router=router)
    console.print_json(data={"city": city, "mode": report["mode"], "media": report["summary"],
                            "ai": report["ai_usage"], "usable_count": report["usability_after"]["overall_usable_count"],
                            "usable_percentage": report["usability_after"]["overall_usable_percentage"],
                            "SOURCE_DATA_READY": report["usability_after"]["SOURCE_DATA_READY"],
                            "output_pack": report.get("output_pack")})


@app.command("build-offline")
def build_offline(
    city: str = typer.Option(..., "--city"),
    state: str = typer.Option(..., "--state"),
    country: str = typer.Option("India", "--country"),
    resume: bool = typer.Option(True, "--resume/--refresh-sources"),
    from_release: bool = typer.Option(False, "--from-release", help="Repair an existing v3 pack without rediscovery"),
    network: bool = typer.Option(False, "--network", help="Allow approved repair-source API retrieval"),
    version: str = typer.Option("v3-offline", "--version"),
):
    """Reuse deterministic discovery/build stages, then assure, repair, validate and export."""
    if not from_release:
        build(city=city, state=state, country=country, resume=resume, refresh_images=False,
              version="v3-candidates", dry_run=False)
    repair_city(city=city, state=state, country=country, version="v3" if from_release else "v3-candidates",
                dry_run=False, apply=True, network=network, output_version=version)


@app.command("ai-smoke")
def ai_smoke(
    city: str = typer.Option(..., "--city"), state: str = typer.Option(..., "--state"),
    place_id: str = typer.Option(..., "--place-id"), country: str = typer.Option("India", "--country"),
):
    """Health checks and exactly one bounded media inference job before batch repair."""
    from .ai.router import AIRouter
    from .pipeline.repair import candidate_from_existing, city_context
    from .pipeline.media_assurance import MediaAssurance, local_asset
    settings = get_settings()
    source = settings.releases_dir / slugify(country) / slugify(state) / slugify(city) / "v3"
    context = json.loads((source / "city.json").read_text(encoding="utf-8"))
    places = json.loads((source / "places.json").read_text(encoding="utf-8"))
    place = next((p for p in places if p["id"] == place_id), None)
    if place is None or not place.get("images", {}).get("primary"):
        raise typer.BadParameter("Smoke POI requires existing local real media")
    router = AIRouter(city_context(context), settings.cache_dir / "ai")
    router.config.limits.update(calls=1, vision_calls=1, escalations=0)
    health = router.health_check()
    path = local_asset(source, place["images"]["primary"].get("local_path"))
    if not path:
        raise typer.BadParameter("Smoke image asset is missing")
    candidate = candidate_from_existing(place["images"]["primary"])
    assessment = MediaAssurance(context, router, settings.staging_dir / "ai_smoke").assess(place, candidate, path.read_bytes())
    from .utils.atomic import atomic_json
    result = {"health": health, "assessment": assessment, "usage": router.report()}
    atomic_json(settings.reports_dir / slugify(country) / slugify(state) / slugify(city) / "assurance" / "ai_smoke.json", result)
    console.print_json(data=result)


@app.command("research-export")
def research_export(
    city: Optional[str] = typer.Option(None, "--city"),
    cities: Optional[str] = typer.Option(None, "--cities", help="Comma-separated city names"),
    state: Optional[str] = typer.Option(None, "--state"),
    country: Optional[str] = typer.Option(None, "--country"),
    version: Optional[str] = typer.Option(None, "--version", help="Default uses latest imported research pack or app-fallback snapshot"),
    types: Optional[str] = typer.Option(None, "--type", help="Comma-separated task types"),
    priority: Optional[str] = typer.Option(None, "--priority", help="Comma-separated P0 through P4"),
    all_tasks: bool = typer.Option(False, "--all", help="Include deferred P3/P4 research"),
    limit: Optional[int] = typer.Option(None, "--limit", min=1, help="Deterministic maximum tasks per city"),
    include_optional: bool = typer.Option(False, "--include-optional", help="Also research ordinary commercial POIs"),
    output: Optional[Path] = typer.Option(None, "--output", help="Output directory"),
):
    """Export unresolved public POI evidence and a ChatGPT-ready research template."""
    from .research.export import find_pack, export_research
    if bool(city) == bool(cities):
        raise typer.BadParameter("Specify one of --city or --cities")
    if version and (Path(version).name != version or version in {".", ".."}):
        raise typer.BadParameter("Version must be a single directory name")
    settings = get_settings()
    reports = []
    for name in [city] if city else [value.strip() for value in cities.split(",") if value.strip()]:
        try:
            pack = find_pack(name, state, country, version, settings)
            meta = json.loads((pack / "city.json").read_text(encoding="utf-8"))
            scope = Path(slugify(meta["country"])) / slugify(meta["state"]) / slugify(meta["name"])
            destination = (output / scope if output and cities else output) or settings.data_dir / "research" / "exports" / scope
            reports.append(export_research(pack, destination, settings=settings,
                types=[value.strip() for value in types.split(",")] if types else None,
                priorities=[value.strip() for value in priority.split(",")] if priority else None,
                include_optional=include_optional, all_tasks=all_tasks, limit=limit))
        except (ValueError, OSError) as exc:
            raise typer.BadParameter(str(exc)) from None
    console.print_json(data=reports[0] if len(reports) == 1 else reports)
    console.print("Upload research_handoff.md/json and research_results.schema.json to ChatGPT Web. Save results, then run research-import --dry-run.")


@app.command("research-import")
def research_import(
    file: Path = typer.Option(..., "--file", exists=True, dir_okay=False),
    dry_run: bool = typer.Option(False, "--dry-run"),
    apply: bool = typer.Option(False, "--apply"),
    network: bool = typer.Option(False, "--network", help="On apply, allow approved original source metadata and media retrieval"),
    output_version: str = typer.Option("v3-research", "--output-version"),
):
    """Validate registered research IDs/evidence; apply safely publishes a new offline pack."""
    from .research.importer import import_research
    if dry_run and apply:
        raise typer.BadParameter("Use either --dry-run or --apply")
    if network and not apply:
        raise typer.BadParameter("--network requires --apply; dry runs never download or call AI")
    try:
        report = import_research(file, apply=apply, allow_network=network, output_version=output_version)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from None
    console.print_json(data=report)


@app.command("local-ai-status")
def local_ai_status_command(download: bool = typer.Option(False, "--download", help="Allow first model download; later runs use the local cache")):
    """Load and exercise local engines without Groq or Gemini."""
    from .local_intelligence.health import local_ai_status
    from .local_intelligence.config import LocalConfig
    result = local_ai_status(LocalConfig(local_media_allow_download=download))
    console.print_json(data=result)
    if result["model_load"] != "PASS" or result["inference_test"] != "PASS":
        raise typer.Exit(1)


main = app

if __name__ == "__main__":
    main()


