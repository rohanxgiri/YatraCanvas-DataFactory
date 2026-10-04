import concurrent.futures
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import httpx

OUT = Path('data/research/manual_resolution/jaipur/evidence_01')
URLS = {
    'suraj_osm': 'https://api.openstreetmap.org/api/0.6/way/863303428/full.json',
    'haveli_osm': 'https://api.openstreetmap.org/api/0.6/way/272782999/full.json',
    'india_osm': 'https://api.openstreetmap.org/api/0.6/node/3771356458.json',
    'elephant_osm': 'https://api.openstreetmap.org/api/0.6/node/5828540786.json',
    'rooftop_osm': 'https://api.openstreetmap.org/api/0.6/node/12367918008.json',
    'rooftop_other_osm': 'https://api.openstreetmap.org/api/0.6/node/11533709370.json',
    'suraj_wikidata': 'https://www.wikidata.org/wiki/Special:EntityData/Q140770830.json',
    'wikivoyage': 'https://en.wikivoyage.org/w/api.php?action=parse&page=Jaipur&prop=wikitext&format=json',
}

def fetch(item):
    key,url=item
    response=httpx.get(url, timeout=30, follow_redirects=True, headers={'User-Agent':'YatraCanvas-DataFactory/1.0 identity research (info@yatracanvas.org)'})
    record={'id':key,'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'http_status':response.status_code}
    if response.status_code==200:
        data=response.json();path=OUT/(key+'.json');path.write_bytes(response.content)
        record.update(file=str(path),sha256=hashlib.sha256(response.content).hexdigest())
        if 'elements' in data:
            record['objects']=[x for x in data['elements'] if x.get('tags')]
        elif 'entities' in data:
            entity=next(iter(data['entities'].values()))
            record['entity']={k:entity.get(k) for k in ('labels','descriptions','aliases','claims')}
        else:
            record['text_length']=len(str(data))
    return record

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(fetch,URLS.items()))
    (OUT/'source_manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in results:
        if 'entity' in r:
            e=r.pop('entity');r['entity_summary']={k:e[k].get('en') for k in ['labels','descriptions','aliases']};r['claims']={k:v for k,v in e['claims'].items() if k in ['P625','P31','P1435','P359','P18','P131']}
        print(json.dumps(r,ensure_ascii=False))
