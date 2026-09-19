import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

cities = [
    Path('releases/india/uttar_pradesh/varanasi/v2'),
    Path('releases/india/rajasthan/udaipur/v2'),
    Path('releases/india/rajasthan/jaipur/v2'),
]

for cp in cities:
    places_file = cp / 'places.json'
    with open(places_file, encoding='utf-8') as f:
        places = json.load(f)
    
    # Filter core destinations sorted by travel_relevance_score descending
    core_places = [p for p in places if p.get('tier') == 'core_destination']
    core_places.sort(key=lambda x: x.get('travel_relevance_score', 0), reverse=True)
    
    print("=" * 90)
    print(f"Top Core Destinations for: {cp.parts[-2].upper()} (Total core: {len(core_places)})")
    print("=" * 90)
    for p in core_places[:5]:
        name = p.get('name')
        name_hi = p.get('name_hi')
        lat = p.get('location', {}).get('latitude')
        lon = p.get('location', {}).get('longitude')
        category = p.get('classification', {}).get('category')
        subcat = p.get('classification', {}).get('subcategory')
        score = p.get('travel_relevance_score')
        wiki_id = p.get('external_ids', {}).get('wikidata')
        img_meta = p.get('images', {}).get('primary')
        img_path = img_meta.get('local_path') if img_meta else None
        img_attr = (img_meta.get('attribution') or img_meta.get('author')) if img_meta else None
        img_lic = img_meta.get('license') if img_meta else None
        
        print(f"- {name} (Hindi: {name_hi})")
        print(f"  Coordinates: ({lat:.5f}, {lon:.5f}) | Category: {category} / {subcat} | Relevance: {score}")
        print(f"  Wikidata: {wiki_id} | Image: {img_path} | License: {img_lic} | Author: {img_attr}")
        print()
