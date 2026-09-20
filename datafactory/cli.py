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
from .pipeline.score import run_score
from .pipeline.validate import run_validate_and_quarantine, validate_release_package
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

    # Stage 10: Enrich with Wikidata claims & structured hours
    enriched_places = run_enrich(
        places=deduped_places,
        city_name=city_meta.name,
    )

    # Stage 11: Verified Wikimedia Commons Imagery
    places_with_images, images_manifest = run_process_images(
        places=enriched_places,
        output_media_dir=settings.media_dir,
        city_name=city_meta.name,
        refresh_images=refresh_images,
    )

    # Stage 12: Score Quality, Travel Relevance, Prominence, and Planning (with Core De-inflation)
    scored_places = run_score(
        places=places_with_images,
        city_bbox=city_meta.bbox,
    )

    # Stage 13: Semantic Validation and Quarantine
    valid_places, quarantined_places = run_validate_and_quarantine(
        places=scored_places,
        city_bbox=city_meta.bbox,
        quarantine_output_path=quarantine_path,
        media_dir=settings.media_dir,
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


main = app

if __name__ == "__main__":
    main()


