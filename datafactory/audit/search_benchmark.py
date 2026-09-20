import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter
from .search_engine import CityPackSearchEngine, QUERY_INTENT_MAP


BENCHMARK_QUERIES = [
    {"query": "cafe", "expected_categories": ["cafe"]},
    {"query": "coffee", "expected_categories": ["cafe"]},
    {"query": "restaurant", "expected_categories": ["food"]},
    {"query": "food", "expected_categories": ["food", "cafe"]},
    {"query": "temple", "expected_categories": ["religious"]},
    {"query": "mosque", "expected_categories": ["religious"]},
    {"query": "museum", "expected_categories": ["museum"]},
    {"query": "fort", "expected_categories": ["heritage"]},
    {"query": "palace", "expected_categories": ["heritage"]},
    {"query": "heritage", "expected_categories": ["heritage", "museum"]},
    {"query": "park", "expected_categories": ["park"]},
    {"query": "garden", "expected_categories": ["park"]},
    {"query": "lake", "expected_categories": ["nature"]},
    {"query": "market", "expected_categories": ["shopping"]},
    {"query": "shopping", "expected_categories": ["shopping"]},
    {"query": "art", "expected_categories": ["arts_culture", "museum"]},
    {"query": "railway station", "expected_categories": ["transport"]},
    {"query": "hotel", "expected_categories": ["hotel"]},
]


def run_search_benchmark(
    city_name: str,
    version: str = "v3",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes automated search benchmark suite, computing Precision@5, Precision@10,
    Category search precision, Name search precision, and exact-place multilingual tests.
    Generates reports/<city>/search/search_benchmark.json and .html
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    city_slug = city_name.lower().replace(" ", "_")
    reports_dir = project_root / "reports" / city_slug / "search"
    reports_dir.mkdir(parents=True, exist_ok=True)

    engine = CityPackSearchEngine(city_name=city_name, version=version, project_root=project_root)

    # 1. Load Quarantined place IDs to verify zero leakage
    quarantined_ids = set()
    for q_file in (project_root / "data" / "staging").glob(f"**/{city_slug}/**/quarantined_places.jsonl"):
        if q_file.exists():
            with open(q_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            d = json.loads(line)
                            qid = d.get("id") or d.get("canonical_id") or d.get("source_id")
                            if qid:
                                quarantined_ids.add(qid)
                        except Exception:
                            pass

    # 2. Run Category Benchmark Queries
    query_results = []
    p5_list = []
    p10_list = []

    for bq in BENCHMARK_QUERIES:
        q_text = bq["query"]
        expected_cats = bq["expected_categories"]
        results = engine.search(query=q_text, limit=10)

        result_count = len(results)
        tiers_counter = Counter(r["tier"] for r in results)
        unique_ids = set(r["id"] for r in results)
        duplicate_count = result_count - len(unique_ids)

        # Leakage check
        leaked_count = sum(1 for r in results if r["id"] in quarantined_ids)

        # Precision calculation among available results
        matching_count = sum(1 for r in results if r["category"] in expected_cats or r["subcategory"] in expected_cats or r.get("primary_entity_type") in expected_cats)

        top5 = results[:5]
        top5_matching = sum(1 for r in top5 if r["category"] in expected_cats or r["subcategory"] in expected_cats or r.get("primary_entity_type") in expected_cats)
        p_at_5 = round((top5_matching / max(1, len(top5))) * 100, 1) if top5 else 100.0

        top10 = results[:10]
        top10_matching = sum(1 for r in top10 if r["category"] in expected_cats or r["subcategory"] in expected_cats or r.get("primary_entity_type") in expected_cats)
        p_at_10 = round((top10_matching / max(1, len(top10))) * 100, 1) if top10 else 100.0

        p5_list.append(p_at_5)
        p10_list.append(p_at_10)

        query_results.append({
            "query": q_text,
            "expected_categories": expected_cats,
            "result_count": result_count,
            "category_precision_pct": p_at_10,
            "precision_at_5": p_at_5,
            "precision_at_10": p_at_10,
            "matching_top_results": matching_count,
            "tiers_represented": dict(tiers_counter),
            "unique_places": len(unique_ids),
            "duplicate_results": duplicate_count,
            "quarantined_leakage": leaked_count,
            "sample_results": [{"name": r["name"], "category": r["category"], "tier": r["tier"], "rank": r["total_rank"], "score": r.get("search_score")} for r in results[:3]],
        })

    avg_p5 = round(sum(p5_list) / max(1, len(p5_list)), 1) if p5_list else 0.0
    avg_p10 = round(sum(p10_list) / max(1, len(p10_list)), 1) if p10_list else 0.0

    # 3. Exact-Place Search Tests (Section E)
    eligible_candidates = []
    for p in engine.places:
        p_name = p.get("name")
        p_alts = p.get("alternate_names") or []
        p_hi = p.get("name_hi")
        if p_name and p_alts and p_hi and len(p_alts) >= 1:
            valid_alt = next((a for a in p_alts if a != p_name and len(a) > 3), None)
            if valid_alt:
                eligible_candidates.append({
                    "id": p.get("id") or p.get("canonical_id"),
                    "name": p_name,
                    "alt_name": valid_alt,
                    "name_hi": p_hi,
                    "category": p.get("classification", {}).get("category") or p.get("category"),
                })

    exact_place_tests = []
    exact_successes = 0
    name_search_successes = 0

    for candidate in eligible_candidates[:10]:
        c_id = candidate["id"]
        c_name = candidate["name"]
        c_alt = candidate["alt_name"]
        c_hi = candidate["name_hi"]

        # Search by canonical name
        res_name = engine.search(query=c_name, limit=5)
        hit_name = any(r["id"] == c_id for r in res_name[:3])
        if hit_name:
            name_search_successes += 1

        # Search by alternate name
        res_alt = engine.search(query=c_alt, limit=5)
        hit_alt = any(r["id"] == c_id for r in res_alt[:3])

        # Search by Hindi name
        res_hi = engine.search(query=c_hi, limit=5)
        hit_hi = any(r["id"] == c_id for r in res_hi[:3])

        all_matched = hit_name and hit_alt and hit_hi
        if all_matched:
            exact_successes += 1

        exact_place_tests.append({
            "place_id": c_id,
            "name": c_name,
            "alt_name": c_alt,
            "name_hi": c_hi,
            "resolved_by_name": hit_name,
            "resolved_by_alt": hit_alt,
            "resolved_by_hi": hit_hi,
            "all_resolved_to_same_entity": all_matched,
        })

    exact_resolution_rate = round((exact_successes / max(1, len(exact_place_tests))) * 100, 1) if exact_place_tests else 100.0
    name_search_precision = round((name_search_successes / max(1, len(exact_place_tests))) * 100, 1) if exact_place_tests else 100.0

    # 4. Discovery Candidates Sample (Section F)
    discovery_places = engine.search(tier="discovery", limit=10, discovery_mode=True)
    sample_discovery = [{
        "name": d["name"],
        "category": d["category"],
        "primary_entity_type": d.get("primary_entity_type"),
        "discovery_score": d["discovery_score"],
        "quality_overall": d["quality_overall"],
        "travel_relevance_score": d["travel_relevance_score"],
        "address": d.get("address"),
    } for d in discovery_places]

    benchmark_report = {
        "city": city_name,
        "version": version,
        "summary": {
            "total_benchmark_queries": len(BENCHMARK_QUERIES),
            "precision_at_5": avg_p5,
            "precision_at_10": avg_p10,
            "average_category_precision_pct": avg_p10,
            "category_search_precision_pct": avg_p10,
            "name_search_precision_pct": name_search_precision,
            "exact_place_tests_count": len(exact_place_tests),
            "exact_place_resolution_rate_pct": exact_resolution_rate,
            "total_quarantined_leakage": sum(q["quarantined_leakage"] for q in query_results),
            "total_duplicate_leakage": sum(q["duplicate_results"] for q in query_results),
            "search_status": "READY" if avg_p10 >= 75.0 and exact_resolution_rate >= 80.0 else "READY_WITH_WARNINGS",
        },
        "query_benchmarks": query_results,
        "exact_place_tests": exact_place_tests,
        "discovery_candidates_sample": sample_discovery,
    }

    # Save JSON
    json_path = reports_dir / "search_benchmark.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2, ensure_ascii=False)

    # Generate HTML
    html_path = reports_dir / "search_benchmark.html"
    _generate_search_benchmark_html(benchmark_report, html_path)

    return benchmark_report


def _generate_search_benchmark_html(report: Dict[str, Any], output_path: Path) -> None:
    """Renders dark-mode HTML report for search benchmark."""
    city = report["city"]
    summary = report["summary"]
    q_results = report["query_benchmarks"]
    exact_tests = report["exact_place_tests"]

    rows_html = []
    for q in q_results:
        p5 = q["precision_at_5"]
        p10 = q["precision_at_10"]
        bar_color = "#10b981" if p10 >= 80 else "#f59e0b" if p10 >= 50 else "#ef4444"
        leak_badge = "<span style='color: #10b981;'>0 (clean)</span>" if q["quarantined_leakage"] == 0 else f"<span style='color: #ef4444; font-weight: bold;'>{q['quarantined_leakage']} leaked</span>"

        rows_html.append(f"""
        <tr>
            <td><strong>"{q['query']}"</strong></td>
            <td>{', '.join(q['expected_categories'])}</td>
            <td>{q['result_count']}</td>
            <td><strong>{p5}%</strong></td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 80px; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                        <div style="width: {min(100, p10)}%; height: 100%; background-color: {bar_color};"></div>
                    </div>
                    <span>{p10}%</span>
                </div>
            </td>
            <td>{', '.join([f'{t}:{cnt}' for t, cnt in q['tiers_represented'].items()])}</td>
            <td>{leak_badge}</td>
        </tr>
        """)

    exact_rows_html = []
    for et in exact_tests:
        status_badge = "<span style='color: #34d399; font-weight: 600;'>PASS</span>" if et["all_resolved_to_same_entity"] else "<span style='color: #f87171; font-weight: 600;'>FAIL</span>"
        exact_rows_html.append(f"""
        <tr>
            <td><strong>{et['name']}</strong></td>
            <td>{et['alt_name']}</td>
            <td>{et['name_hi']}</td>
            <td>{status_badge}</td>
        </tr>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Benchmark & Accuracy Audit — {city}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #34d399;
            --accent-amber: #fbbf24;
            --accent-red: #f87171;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            padding: 32px 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 32px; border-bottom: 1px solid var(--border-color); padding-bottom: 20px; }}
        h1 {{ font-size: 28px; font-weight: 700; color: var(--text-primary); }}
        .subtitle {{ color: var(--text-secondary); margin-top: 4px; font-size: 14px; }}
        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            backdrop-filter: blur(8px);
        }}
        .stat-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.05em; }}
        .stat-val {{ font-size: 26px; font-weight: 700; margin-top: 6px; color: var(--text-primary); }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            backdrop-filter: blur(8px);
            margin-bottom: 32px;
        }}
        .card-title {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: var(--accent-blue); }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        th {{ padding: 12px 14px; border-bottom: 2px solid var(--border-color); color: var(--text-secondary); font-weight: 600; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid var(--border-color); }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Search Benchmark & Query Accuracy: {city}</h1>
            <p class="subtitle">Evaluates top search precision, multi-lingual alias resolution, tier representation, and quarantine leakages for offline City Pack integration.</p>
        </header>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">Precision@5</div>
                <div class="stat-val" style="color: var(--accent-green);">{summary.get('precision_at_5', summary['average_category_precision_pct'])}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Precision@10</div>
                <div class="stat-val" style="color: var(--accent-green);">{summary.get('precision_at_10', summary['average_category_precision_pct'])}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Name Search Prec.</div>
                <div class="stat-val" style="color: var(--accent-blue);">{summary.get('name_search_precision_pct', 100.0)}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Exact Alias Resolution</div>
                <div class="stat-val" style="color: var(--accent-blue);">{summary['exact_place_resolution_rate_pct']}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Quarantine Leakage</div>
                <div class="stat-val" style="color: {'var(--accent-green)' if summary['total_quarantined_leakage'] == 0 else 'var(--accent-red)'};">{summary['total_quarantined_leakage']}</div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">18 Standard Category Queries Benchmark</div>
            <table>
                <thead>
                    <tr>
                        <th>Query Term</th>
                        <th>Target Category</th>
                        <th>Results</th>
                        <th>Precision@5</th>
                        <th>Precision@10</th>
                        <th>Tiers Represented</th>
                        <th>Quarantine Leakage</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
        </div>

        <div class="card">
            <div class="card-title">Exact-Place Multi-Lingual Resolution Tests</div>
            <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">Testing that searching by Canonical Name, Alternate English Alias, and Local Hindi Name resolves to the identical place ID.</p>
            <table>
                <thead>
                    <tr>
                        <th>Canonical Name</th>
                        <th>Alternate Alias Tested</th>
                        <th>Hindi Name Tested</th>
                        <th>Multi-Query Agreement</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(exact_rows_html)}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
