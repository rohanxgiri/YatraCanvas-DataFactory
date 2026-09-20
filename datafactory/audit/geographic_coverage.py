import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter


def audit_geographic_coverage(
    city_name: str,
    state_name: str,
    country_name: str = "India",
    version: str = "v3",
    grid_size: int = 8,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Audits spatial distribution of released records across an NxN bounding-box grid.
    Reports density, tier distribution, empty/dense cells, and spatial concentration.
    Generates reports/<city>/coverage/geographic_coverage.json and .html
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    city_slug = city_name.lower().replace(" ", "_")
    state_slug = state_name.lower().replace(" ", "_")
    country_slug = country_name.lower().replace(" ", "_")

    release_dir = project_root / "releases" / country_slug / state_slug / city_slug / version
    reports_dir = project_root / "reports" / city_slug / "coverage"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load city metadata to get bounding box
    city_file = release_dir / "city.json"
    bbox = None
    if city_file.exists():
        with open(city_file, "r", encoding="utf-8") as f:
            c_data = json.load(f)
            bbox = c_data.get("bbox")

    # 2. Load places
    places_file = release_dir / "places.json"
    places = []
    if places_file.exists():
        with open(places_file, "r", encoding="utf-8") as f:
            places = json.load(f)

    if not bbox and places:
        # Fallback bounding box from places
        lats = [p.get("location", {}).get("latitude") or p.get("latitude") for p in places if p.get("location", {}).get("latitude") or p.get("latitude")]
        lons = [p.get("location", {}).get("longitude") or p.get("longitude") for p in places if p.get("location", {}).get("longitude") or p.get("longitude")]
        if lats and lons:
            bbox = [min(lons), min(lats), max(lons), max(lats)]
        else:
            bbox = [75.0, 26.0, 76.0, 27.0]
    elif not bbox:
        bbox = [75.0, 26.0, 76.0, 27.0]

    min_lon, min_lat, max_lon, max_lat = bbox
    lon_step = (max_lon - min_lon) / grid_size
    lat_step = (max_lat - min_lat) / grid_size

    cells: Dict[str, Dict[str, Any]] = {}
    for r in range(grid_size):
        for c in range(grid_size):
            cell_id = f"cell_{r}_{c}"
            cells[cell_id] = {
                "row": r,
                "col": c,
                "bounds": {
                    "min_lat": round(min_lat + r * lat_step, 4),
                    "max_lat": round(min_lat + (r + 1) * lat_step, 4),
                    "min_lon": round(min_lon + c * lon_step, 4),
                    "max_lon": round(min_lon + (c + 1) * lon_step, 4),
                },
                "total_pois": 0,
                "tiers": Counter(),
                "categories": Counter(),
            }

    # Map places to grid
    places_in_grid = 0
    places_outside_grid = 0

    for p in places:
        loc = p.get("location", {})
        lat = loc.get("latitude") or p.get("latitude")
        lon = loc.get("longitude") or p.get("longitude")
        if lat is None or lon is None:
            places_outside_grid += 1
            continue

        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            r = min(grid_size - 1, max(0, int((lat - min_lat) / lat_step)))
            c = min(grid_size - 1, max(0, int((lon - min_lon) / lon_step)))
            cell_id = f"cell_{r}_{c}"
            cells[cell_id]["total_pois"] += 1
            tier = p.get("tier", "discovery")
            cells[cell_id]["tiers"][tier] += 1
            cat = p.get("classification", {}).get("category") or p.get("category", "unknown")
            cells[cell_id]["categories"][cat] += 1
            places_in_grid += 1
        else:
            places_outside_grid += 1

    # Analysis
    counts = [cell["total_pois"] for cell in cells.values()]
    non_empty_cells = sum(1 for cnt in counts if cnt > 0)
    empty_cells = sum(1 for cnt in counts if cnt == 0)
    max_cell_count = max(counts) if counts else 0

    # Top 10% densest cells concentration
    sorted_cells = sorted(cells.values(), key=lambda x: x["total_pois"], reverse=True)
    top_10_pct_count = max(1, int(len(sorted_cells) * 0.10))
    top_cells_sum = sum(c["total_pois"] for c in sorted_cells[:top_10_pct_count])
    concentration_pct = round((top_cells_sum / max(1, places_in_grid)) * 100, 1)

    has_suspicious_concentration = concentration_pct > 85.0 and len(places) > 100

    report = {
        "city": city_name,
        "state": state_name,
        "country": country_name,
        "version": version,
        "grid_dimensions": f"{grid_size}x{grid_size} ({grid_size*grid_size} cells)",
        "bounding_box": {
            "min_lon": min_lon, "min_lat": min_lat,
            "max_lon": max_lon, "max_lat": max_lat,
        },
        "summary": {
            "total_released_places": len(places),
            "places_within_grid": places_in_grid,
            "places_outside_grid": places_outside_grid,
            "total_grid_cells": grid_size * grid_size,
            "non_empty_cells": non_empty_cells,
            "empty_cells": empty_cells,
            "max_cell_density": max_cell_count,
            "top_10_pct_cells_concentration_pct": concentration_pct,
            "suspicious_concentration_detected": has_suspicious_concentration,
            "coverage_warning": f"Extreme clustering: {concentration_pct}% of POIs in top 10% area" if has_suspicious_concentration else None,
        },
        "cells": {
            k: {
                "row": v["row"],
                "col": v["col"],
                "bounds": v["bounds"],
                "total_pois": v["total_pois"],
                "tiers": dict(v["tiers"]),
                "top_categories": dict(v["categories"].most_common(3)),
            } for k, v in cells.items()
        },
    }

    # Save JSON
    json_path = reports_dir / "geographic_coverage.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Save HTML
    html_path = reports_dir / "geographic_coverage.html"
    _generate_geographic_html(report, grid_size, sorted_cells, html_path)

    return report


def _generate_geographic_html(report: Dict[str, Any], grid_size: int, sorted_cells: List[Dict[str, Any]], output_path: Path) -> None:
    """Renders visual CSS grid heatmap for geographic coverage."""
    city = report["city"]
    summary = report["summary"]
    max_d = max(1, summary["max_cell_density"])

    grid_items = []
    for r in reversed(range(grid_size)):  # North at top
        for c in range(grid_size):
            cid = f"cell_{r}_{c}"
            c_info = report["cells"].get(cid, {})
            cnt = c_info.get("total_pois", 0)
            alpha = 0.05 + (cnt / max_d) * 0.85 if cnt > 0 else 0.03
            bg_color = f"rgba(56, 189, 248, {alpha:.2f})" if cnt > 0 else "rgba(255, 255, 255, 0.02)"
            border_color = "rgba(56, 189, 248, 0.4)" if cnt > 0 else "rgba(255, 255, 255, 0.04)"

            tiers_txt = ", ".join([f"{t}:{num}" for t, num in c_info.get("tiers", {}).items()])
            grid_items.append(f"""
            <div class="grid-cell" style="background-color: {bg_color}; border-color: {border_color};" title="Cell ({r},{c}): {cnt} POIs | {tiers_txt}">
                <span class="cell-count">{cnt}</span>
            </div>
            """)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Geographic Coverage & Spatial Density — {city}</title>
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
        .spatial-grid {{
            display: grid;
            grid-template-columns: repeat({grid_size}, 1fr);
            gap: 6px;
            max-width: 600px;
            margin: 20px auto;
            aspect-ratio: 1;
        }}
        .grid-cell {{
            border: 1px solid;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.15s ease;
        }}
        .grid-cell:hover {{ transform: scale(1.08); z-index: 10; }}
        .cell-count {{ font-size: 12px; font-weight: 600; color: var(--text-primary); }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        th {{ padding: 12px 14px; border-bottom: 2px solid var(--border-color); color: var(--text-secondary); font-weight: 600; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid var(--border-color); }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Geographic Coverage & Spatial Distribution: {city}</h1>
            <p class="subtitle">Auditing spatial distribution across an {grid_size}x{grid_size} bounding box grid to detect spatial clustering, coverage gaps, and peripheral POIs.</p>
        </header>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">Grid Dimensions</div>
                <div class="stat-val">{report['grid_dimensions']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Occupied Cells</div>
                <div class="stat-val" style="color: var(--accent-green);">{summary['non_empty_cells']} / {summary['total_grid_cells']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Max Cell POIs</div>
                <div class="stat-val" style="color: var(--accent-blue);">{summary['max_cell_density']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Top 10% Concentration</div>
                <div class="stat-val" style="color: {'var(--accent-amber)' if summary['top_10_pct_cells_concentration_pct'] > 75 else 'var(--accent-green)'};">{summary['top_10_pct_cells_concentration_pct']}%</div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">Spatial Density Grid Map ({grid_size}x{grid_size}) — North at Top</div>
            <div class="spatial-grid">
                {"".join(grid_items)}
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
