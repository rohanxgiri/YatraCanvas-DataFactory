"""Classify the preserved old baseline, export practical batches, verify snapshots."""
import json
from collections import Counter
from pathlib import Path
from datafactory.config.settings import get_settings
from datafactory.research.export import export_research, snapshot, read_assurance
from datafactory.research.worthiness import research_worthiness
from datafactory.pipeline.usability import usability
from datafactory.utils.atomic import atomic_json


def main():
    s=get_settings()
    baseline=json.loads((s.reports_dir/'local_intelligence/research_baseline.json').read_text(encoding='utf-8'))
    rows=[]
    for old in baseline['cities']:
        pack=Path(old['pack']); places=json.loads((pack/'places.json').read_text(encoding='utf-8'))
        city=json.loads((pack/'city.json').read_text(encoding='utf-8')); index={p['id']:p for p in places}; assurance=read_assurance(pack)
        classified=[]
        for task in old['tasks']:
            a=assurance.get(task['place_id'],{})
            critical=bool(a.get('identity_blocker')) or a.get('coordinate',{}).get('status')=='CONFLICT'
            classified.append({**task,**research_worthiness(index[task['place_id']],task['type'],critical=critical)})
        by_priority=Counter(t['priority'] for t in classified); by_worthiness=Counter(t['research_worthiness'] for t in classified)
        output=s.data_dir/'research/exports'/old['city'].lower()/'actionable'
        exported=export_research(pack,output,settings=s)
        useful=usability(places,city,pack,assurance)
        row={'city':old['city'],'baseline_raw_unresolved':old['total'],'baseline_by_priority':dict(by_priority),'baseline_by_worthiness':dict(by_worthiness),
             'default_export':exported,'reduction_percent':round((old['total']-exported['total'])/old['total']*100,2),
             'source_unchanged':snapshot(pack)==old['source_snapshot'],'original_v3_unchanged':snapshot(pack.parent/'v3')==old['v3_snapshot'],
             'readiness':{k:useful[k] for k in ('GENERAL_USABILITY','REAL_REQUIRED_MEDIA_COVERAGE','SOURCE_DATA_READY','critical_blockers')},
             'classified_baseline_tasks':classified}
        rows.append(row)
    jaipur=Path(baseline['cities'][0]['pack'])
    batch=export_research(jaipur,s.data_dir/'research/exports/jaipur/batch_1',limit=75,settings=s)
    markdown=Path(batch['output'])/'research_handoff.md'
    markdown.write_text(markdown.read_text(encoding='utf-8').replace('# Jaipur Research Handoff','# Jaipur Research Batch 1',1),encoding='utf-8')
    images=export_research(jaipur,s.data_dir/'research/exports/jaipur/required_images',types=['REAL_PRIMARY_IMAGE'],priorities=['P0'],settings=s)
    hours=export_research(jaipur,s.data_dir/'research/exports/jaipur/core_hours',types=['OPENING_HOURS'],priorities=['P2'],settings=s)
    report={'cities':rows,'baseline_total':baseline['total'],'actionable_total':sum(r['default_export']['total'] for r in rows),
            'jaipur_batch_1':batch,'jaipur_images':images,'jaipur_hours':hours}
    atomic_json(s.reports_dir/'local_intelligence/research_prioritization.json',report)
    lines=['# Research prioritization after optimization','','Counts below classify exactly the preserved 1,637 baseline tasks. The internal full inventory also records ordinary optional gaps omitted by the old selector. Default exports exclude P3, P4 and DO_NOT_RESEARCH.','',
           '| City | Before | P0 | P1 | P2 | P3 | P4 | No research | Default | Reduction |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        c=r['baseline_by_priority']; lines.append(f"| {r['city']} | {r['baseline_raw_unresolved']} | "+' | '.join(str(c.get(k,0)) for k in ('P0','P1','P2','P3','P4','NO_RESEARCH'))+f" | {r['default_export']['total']} | {r['reduction_percent']}% |")
    lines += ['', '| City | Required | Recommended | Optional defer | Do not research |','|---|---:|---:|---:|---:|']
    for r in rows:
        c=r['baseline_by_worthiness']; lines.append(f"| {r['city']} | "+' | '.join(str(c.get(k,0)) for k in ('RESEARCH_REQUIRED','RESEARCH_RECOMMENDED','OPTIONAL_DEFER','DO_NOT_RESEARCH'))+' |')
    lines+=['','## Jaipur Batch 1','','```json',json.dumps(batch,indent=2),'```','','## Snapshot preservation and readiness','']
    for r in rows:
        lines += [f"- {r['city']}: source unchanged={r['source_unchanged']}; v3 unchanged={r['original_v3_unchanged']}; general usability={r['readiness']['GENERAL_USABILITY']}%; required media={r['readiness']['REAL_REQUIRED_MEDIA_COVERAGE']}%; source ready={r['readiness']['SOURCE_DATA_READY']}"]
    lines+=['','Deferral is field-specific: generic gates/viewpoints/urban parks without controlled-entry evidence do not get hours research; descriptions prioritize important attractions; optional websites defer. Explicit venue words recover schedule relevance when the existing category is generic heritage. No hours or rights are fabricated.','']
    (s.reports_dir/'local_intelligence/research_prioritization.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cities'},indent=2))


if __name__=='__main__':
    main()
