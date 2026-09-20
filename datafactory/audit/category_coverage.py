import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


def audit_category_coverage(
    city_name: str,
    state_name: str,
    country_name: str = "India",
    version: str = "v3",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Audits category, subcategory, and tier retention across all pipeline stages:
    raw candidates -> deduplication -> quarantine -> rejected -> released.
    Generates reports/<city>/coverage/category_coverage.json and .html
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    city_slug = city_name.lower().replace(" ", "_")
    state_slug = state_name.lower().replace(" ", "_")
    country_slug = country_name.lower().replace(" ", "_")

    release_dir = project_root / "releases" / country_slug / state_slug / city_slug / version
    staging_dir = project_root / "data" / "staging" / country_slug / state_slug / city_slug
    reports_dir = project_root / "reports" / city_slug / "coverage"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Released Places
    places_file = release_dir / "places.json"
    released_places: List[Dict[str, Any]] = []
    if places_file.exists():
        with open(places_file, "r", encoding="utf-8") as f:
            released_places = json.load(f)

    # 2. Load Quarantined Places
    quarantine_file = staging_dir / "quarantine" / "quarantined_places.jsonl"
    quarantined_places: List[Dict[str, Any]] = []
    if quarantine_file.exists():
        with open(quarantine_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        quarantined_places.append(json.loads(line))
                    except Exception:
                        pass

    # 3. Load Rejected Places
    rejected_file = staging_dir / "rejected_places.jsonl"
    rejected_places: List[Dict[str, Any]] = []
    if rejected_file.exists():
        with open(rejected_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rejected_places.append(json.loads(line))
                    except Exception:
                        pass

    # 4. Load Duplicate Merges
    duplicates_file = staging_dir / "duplicates.jsonl"
    duplicates_count = 0
    if duplicates_file.exists():
        with open(duplicates_file, "r", encoding="utf-8") as f:
            duplicates_count = sum(1 for line in f if line.strip())

    # Aggregate by category and subcategory
    category_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "raw_candidates": 0,
        "unique_after_dedup": 0,
        "released": 0,
        "quarantined": 0,
        "rejected": 0,
        "retention_rate_pct": 0.0,
        "subcategories": defaultdict(lambda: {
            "released": 0,
            "quarantined": 0,
            "rejected": 0,
        }),
        "tiers": defaultdict(int),
    })

    # Count released
    for p in released_places:
        c_info = p.get("classification", {})
        cat = c_info.get("category") or p.get("category") or "unknown"
        subcat = c_info.get("subcategory") or p.get("subcategory") or "general"
        tier = p.get("tier", "discovery")

        category_data[cat]["released"] += 1
        category_data[cat]["subcategories"][subcat]["released"] += 1
        category_data[cat]["tiers"][tier] += 1

    # Count quarantined
    for q in quarantined_places:
        cat = q.get("category") or "unknown"
        subcat = q.get("subcategory") or "general"
        category_data[cat]["quarantined"] += 1
        category_data[cat]["subcategories"][subcat]["quarantined"] += 1

    # Count rejected
    for r in rejected_places:
        # Some rejected records have raw tags or category hints
        cat_hints = r.get("category_hints") or []
        cat = "unknown"
        if cat_hints:
            h = cat_hints[0].lower()
            if any(w in h for w in ["hotel", "inn", "stay", "guest"]):
                cat = "hotel"
            elif any(w in h for w in ["food", "restaurant", "dining"]):
                cat = "food"
            elif any(w in h for w in ["cafe", "coffee"]):
                cat = "cafe"
            elif any(w in h for w in ["shop", "store", "market"]):
                cat = "shopping"
            elif any(w in h for w in ["temple", "worship", "religious"]):
                cat = "religious"
            elif any(w in h for w in ["museum"]):
                cat = "museum"
            elif any(w in h for w in ["park", "garden"]):
                cat = "park"
            elif any(w in h for w in ["fort", "palace", "heritage"]):
                cat = "heritage"
            else:
                cat = "rejected_other"
        category_data[cat]["rejected"] += 1
        category_data[cat]["subcategories"]["rejected"]["rejected"] += 1

    # Compute raw & unique totals
    for cat, stats in category_data.items():
        stats["unique_after_dedup"] = stats["released"] + stats["quarantined"]
        stats["raw_candidates"] = stats["unique_after_dedup"] + stats["rejected"]
        if stats["unique_after_dedup"] > 0:
            stats["retention_rate_pct"] = round((stats["released"] / stats["unique_after_dedup"]) * 100, 1)
        else:
            stats["retention_rate_pct"] = 0.0

    # Summary overall
    total_released = len(released_places)
    total_quarantined = len(quarantined_places)
    total_rejected = len(rejected_places)
    total_unique = total_released + total_quarantined
    total_raw = total_unique + total_rejected

    report = {
        "city": city_name,
        "state": state_name,
        "country": country_name,
        "version": version,
        "summary": {
            "total_raw_candidates": total_raw,
            "total_unique_places": total_unique,
            "total_released_places": total_released,
            "total_quarantined_places": total_quarantined,
            "total_rejected_places": total_rejected,
            "duplicate_merges": duplicates_count,
            "overall_retention_rate_pct": round((total_released / max(1, total_unique)) * 100, 1),
        },
        "categories": {k: {
            "raw_candidates": v["raw_candidates"],
            "unique_after_dedup": v["unique_after_dedup"],
            "released": v["released"],
            "quarantined": v["quarantined"],
            "rejected": v["rejected"],
            "retention_rate_pct": v["retention_rate_pct"],
            "tiers": dict(v["tiers"]),
            "subcategories": {sub_k: dict(sub_v) for sub_k, sub_v in v["subcategories"].items()},
        } for k, v in sorted(category_data.items(), key=lambda x: x[1]["released"], reverse=True)},
    }

    # Save JSON
    json_path = reports_dir / "category_coverage.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Generate HTML report
    html_path = reports_dir / "category_coverage.html"
    _generate_category_coverage_html(report, html_path)

    return report


def _generate_category_coverage_html(report: Dict[str, Any], output_path: Path) -> None:
    """Generates a responsive modern dark-mode HTML report for Category Coverage."""
    city = report["city"]
    summary = report["summary"]
    cats = report["categories"]

    rows_html = []
    for cat_name, c in cats.items():
        if cat_name in ("unknown", "rejected_other") and c["released"] == 0:
            continue
        pct = c["retention_rate_pct"]
        bar_color = "#10b981" if pct >= 60 else "#f59e0b" if pct >= 30 else "#ef4444"

        tiers_badge = " ".join([f"<span class='badge badge-tier'>{t}: {cnt}</span>" for t, cnt in c.get("tiers", {}).items() if cnt > 0])

        rows_html.append(f"""
        <tr>
            <td><strong>{cat_name.title()}</strong></td>
            <td>{c['raw_candidates']:,}</td>
            <td>{c['unique_after_dedup']:,}</td>
            <td><strong style="color: #60a5fa;">{c['released']:,}</strong></td>
            <td><span style="color: #f87171;">{c['quarantined']:,}</span></td>
            <td><span style="color: #9ca3af;">{c['rejected']:,}</span></td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: {min(100, pct)}%; background-color: {bar_color};"></div>
                    </div>
                    <span>{pct}%</span>
                </div>
            </td>
            <td>{tiers_badge or '-'}</td>
        </tr>
        """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Category Coverage Audit — {city}</title>
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
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
        .stat-val {{ font-size: 28px; font-weight: 700; margin-top: 6px; color: var(--text-primary); }}
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
        .progress-bar-bg {{
            width: 100px;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-bar-fill {{ height: 100%; border-radius: 4px; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-tier {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; margin-right: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Category Coverage & Pipeline Retention: {city}</h1>
            <p class="subtitle">Autonomous verification of candidate survival from raw discovery through filtering and entity resolution to City Pack release ({report['version']}).</p>
        </header>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">Total Raw Discovered</div>
                <div class="stat-val">{summary['total_raw_candidates']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unique Candidates</div>
                <div class="stat-val">{summary['total_unique_places']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Released POIs</div>
                <div class="stat-val" style="color: var(--accent-green);">{summary['total_released_places']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Quarantined</div>
                <div class="stat-val" style="color: var(--accent-red);">{summary['total_quarantined_places']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Overall Retention</div>
                <div class="stat-val" style="color: var(--accent-blue);">{summary['overall_retention_rate_pct']}%</div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">Category-by-Category Funnel & Retention</div>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Raw</th>
                        <th>Unique</th>
                        <th>Released</th>
                        <th>Quarantined</th>
                        <th>Rejected</th>
                        <th>Retention Rate</th>
                        <th>Released Tiers</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
