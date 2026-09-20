import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..models.place import Place
from ..models.city import CityMetadata


def generate_html_report(
    city_meta: CityMetadata,
    places: List[Place],
    output_path: Path,
    manifest: Optional[Any] = None,
    rejected_count: int = 0,
    quarantined_count: int = 0,
    duplicate_merges_count: int = 0,
    total_raw_count: int = 0,
    sources_count: Optional[Dict[str, int]] = None,
    summary_json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summary_json_path:
        summary_json_path.parent.mkdir(parents=True, exist_ok=True)

    accepted_count = len(places)
    with_images = sum(1 for p in places if p.images.primary is not None)
    with_hours = sum(1 for p in places if p.opening_hours.raw is not None)
    with_wikidata = sum(1 for p in places if p.external_ids.wikidata_id is not None)

    # By tier stats
    tier_counts = {"core_destination": 0, "recommended": 0, "discovery": 0, "support": 0}
    tier_img = {"core_destination": 0, "recommended": 0, "discovery": 0, "support": 0}
    tier_wiki = {"core_destination": 0, "recommended": 0, "discovery": 0, "support": 0}
    tier_hours = {"core_destination": 0, "recommended": 0, "discovery": 0, "support": 0}

    for p in places:
        t = p.tier.value if hasattr(p.tier, "value") else str(p.tier)
        tier_counts[t] = tier_counts.get(t, 0) + 1
        if p.images.primary:
            tier_img[t] = tier_img.get(t, 0) + 1
        if p.external_ids.wikidata_id:
            tier_wiki[t] = tier_wiki.get(t, 0) + 1
        if p.opening_hours.raw:
            tier_hours[t] = tier_hours.get(t, 0) + 1

    # Category counts
    cat_counts: Dict[str, int] = {}
    for p in places:
        c = p.classification.category
        cat_counts[c] = cat_counts.get(c, 0) + 1

    # Top places sorted by travel relevance and tourism priority
    top_places = sorted(
        places,
        key=lambda p: (
            1 if (hasattr(p.tier, "value") and p.tier.value == "core_destination") else 0,
            p.travel_relevance_score,
            p.planning.tourism_priority,
            p.quality.overall
        ),
        reverse=True
    )[:15]

    top_rows_html = ""
    for p in top_places:
        t_val = p.tier.value if hasattr(p.tier, "value") else str(p.tier)
        badge_cls = "badge-core" if t_val == "core_destination" else "badge-rec" if t_val == "recommended" else "badge-gray"
        img_tag = f'<span class="badge badge-success">✓ {p.images.primary.license}</span>' if p.images.primary else '<span class="badge badge-gray">None</span>'
        wiki_tag = f'<a href="https://www.wikidata.org/wiki/{p.external_ids.wikidata_id}" target="_blank">{p.external_ids.wikidata_id}</a>' if p.external_ids.wikidata_id else '<span class="badge badge-gray">None</span>'
        top_rows_html += f"""
        <tr>
            <td><strong>{p.name}</strong><br><small style="color:#666;">{p.classification.subcategory or p.classification.category}</small></td>
            <td><span class="badge {badge_cls}">{t_val}</span></td>
            <td><span class="badge badge-primary">{p.classification.category}</span></td>
            <td>{p.travel_relevance_score:.2f}</td>
            <td>{p.quality.overall:.2f}</td>
            <td>{img_tag}</td>
            <td>{wiki_tag}</td>
            <td>{p.opening_hours.raw or '<span class="text-muted">None</span>'}</td>
        </tr>
        """

    cat_pills_html = "".join([
        f'<div class="stat-card" style="min-width:140px; text-align:center;">'
        f'<div style="font-size:1.4rem; font-weight:700; color:#1a365d;">{cnt}</div>'
        f'<div style="font-size:0.85rem; text-transform:capitalize; color:#4a5568;">{cat}</div>'
        f'</div>'
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YatraCanvas City Pack Report - {city_meta.name}</title>
    <style>
        :root {{
            --primary: #2b6cb0;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --text: #2d3748;
            --border: #e2e8f0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 30px 20px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1150px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 2rem; }}
        .header p {{ margin: 0; opacity: 0.9; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .stat-value {{ font-size: 1.8rem; font-weight: 700; color: #1a365d; }}
        .stat-label {{ font-size: 0.85rem; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; }}
        .tier-card {{ border-left: 4px solid #3182ce; }}
        .tier-core {{ border-left-color: #e53e3e; }}
        .tier-rec {{ border-left-color: #dd6b20; }}
        .tier-disc {{ border-left-color: #3182ce; }}
        .tier-supp {{ border-left-color: #718096; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
        .badge-core {{ background: #fed7d7; color: #9b2c2c; }}
        .badge-rec {{ background: #feebc8; color: #7b341e; }}
        .badge-primary {{ background: #e2e8f0; color: #2d3748; }}
        .badge-success {{ background: #c6f6d5; color: #22543d; }}
        .badge-gray {{ background: #edf2f7; color: #718096; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: white; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
        th {{ background: #edf2f7; color: #4a5568; font-weight: 600; }}
        .section-title {{ font-size: 1.25rem; font-weight: 700; margin: 30px 0 15px 0; color: #1a365d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>YatraCanvas City Pack: {city_meta.name}</h1>
            <p>{city_meta.state}, {city_meta.country} • Open Data Architecture v2.0</p>
        </div>

        <div class="section-title">Coverage By Place Tier</div>
        <div class="stats-grid">
            <div class="stat-card tier-core">
                <div class="stat-value">{tier_counts['core_destination']}</div>
                <div class="stat-label">Core Destinations</div>
                <small>Images: {tier_img['core_destination']} • Wiki: {tier_wiki['core_destination']} • Hours: {tier_hours['core_destination']}</small>
            </div>
            <div class="stat-card tier-rec">
                <div class="stat-value">{tier_counts['recommended']}</div>
                <div class="stat-label">Recommended Places</div>
                <small>Images: {tier_img['recommended']} • Wiki: {tier_wiki['recommended']} • Hours: {tier_hours['recommended']}</small>
            </div>
            <div class="stat-card tier-disc">
                <div class="stat-value">{tier_counts['discovery']}</div>
                <div class="stat-label">Discovery Places</div>
                <small>Long-tail food & shops</small>
            </div>
            <div class="stat-card tier-supp">
                <div class="stat-value">{tier_counts['support']}</div>
                <div class="stat-label">Support / Transit</div>
                <small>Hotels, stations & hubs</small>
            </div>
        </div>

        <div class="section-title">Top Verified Destinations</div>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Tier</th>
                    <th>Category</th>
                    <th>Relevance</th>
                    <th>Quality</th>
                    <th>Exact Image</th>
                    <th>Wikidata QID</th>
                    <th>Opening Hours</th>
                </tr>
            </thead>
            <tbody>
                {top_rows_html}
            </tbody>
        </table>

        <div class="section-title">Category Breakdown</div>
        <div style="display:flex; flex-wrap:wrap; gap:10px;">
            {cat_pills_html}
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "accepted": accepted_count,
        "with_images": with_images,
        "with_hours": with_hours,
        "with_wikidata": with_wikidata,
        "tier_counts": tier_counts,
    }
