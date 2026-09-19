import json
from collections import Counter
from pathlib import Path

with open('releases/india/rajasthan/jaipur/v2/places.json', encoding='utf-8') as f:
    places = json.load(f)

core = [p for p in places if p.get('tier') == 'core_destination']
print('Total Jaipur Core:', len(core))

cats = Counter(f"{p['classification']['category']}/{p['classification']['subcategory']}" for p in core)
print('\nTop Categories in Core:')
for k, v in cats.most_common(15):
    print(f'  {k}: {v}')

sources = Counter(','.join(sorted(s['source'] for s in p['sources'])) for p in core)
print('\nSource Combinations in Core:')
for k, v in sources.most_common(10):
    print(f'  {k}: {v}')

single_overture = [p for p in core if len(p['sources']) == 1 and p['sources'][0]['source'] == 'overture']
print(f'\nCore supported ONLY by Overture: {len(single_overture)}')
for p in single_overture[:10]:
    print('  -', p['name'], '| Category:', p['classification']['category'], p['classification']['subcategory'], '| Relevance:', p['travel_relevance_score'])
