import json
from pathlib import Path

cities = [
    Path('releases/india/uttar_pradesh/varanasi/v2'),
    Path('releases/india/rajasthan/udaipur/v2'),
    Path('releases/india/rajasthan/jaipur/v2'),
]

for p in cities:
    manifest_file = p / 'manifest.json'
    if not manifest_file.exists():
        print(f"Missing {manifest_file}")
        continue
    with open(manifest_file, encoding='utf-8') as f:
        m = json.load(f)
    c = m['counts']
    st = c['by_tier_stats']
    print("=" * 60)
    print(f"City: {m['city_name']}")
    print(f"  Total Raw: {c['total_raw_candidates']}")
    print(f"  Accepted: {c['accepted']}")
    print(f"  Rejected: {c['rejected']}")
    print(f"  Quarantined: {c['quarantined']}")
    print(f"  Duplicate Merges: {c['duplicate_merges']}")
    print(f"  Core Destinations: {st['core_destination']['count']}")
    print(f"  Recommended: {st['recommended']['count']}")
    print(f"  Discovery: {st['discovery']['count']}")
    print(f"  Support: {st['support']['count']}")
    print(f"  Core with Wikidata: {st['core_destination']['with_wikidata']}")
    print(f"  Core with Exact Image: {st['core_destination']['with_image']}")
    print(f"  Core with Opening Hours: {st['core_destination']['with_hours']}")
    print(f"  Recommended with Image: {st['recommended']['with_image']}")
    print(f"  Total with Images: {c.get('with_images')}")
    print(f"  Total with Wikidata: {c.get('with_wikidata')}")
    print(f"  Total with Opening Hours: {c.get('with_opening_hours')}")
    print(f"  Release Path: {p}")
print("=" * 60)
