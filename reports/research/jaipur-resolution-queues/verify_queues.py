"""Verify generated queue partitioning and preservation without any provider calls."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from datafactory.research.export import make_tasks, snapshot
from datafactory.research.resolution import resolve_media_tasks
from datafactory.research.schemas import ResultBundle
from datafactory.utils.hashing import compute_sha256
from datafactory.pipeline.validate import validate_release_package

REPORT=Path(__file__).resolve().parent
OUTPUT=ROOT/'data/research/exports/jaipur/required_images_remaining'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(name,value):(REPORT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


before=read(REPORT/'before.json')
changed=[name for name,sha in before['protected_files'].items()
         if not (ROOT/name).is_file() or compute_sha256(ROOT/name)!=sha]
assert not changed,changed
status=read(OUTPUT/'status_report.json')
pack=Path(status['source_pack']);city=read(pack/'city.json')
tasks=[t for t in make_tasks(read(pack/'places.json'),city,pack,include_optional=True)
       if t['type']=='REAL_PRIMARY_IMAGE' and t['known_evidence']['media_policy']=='REAL_REQUIRED']
fresh=resolve_media_tasks(pack,tasks)
assert fresh==status['tasks']
assert snapshot(pack)==status['source_snapshot']
assert {t['task_id'] for t in tasks}=={t['task_id'] for t in fresh} and len(fresh)==36
groups={state:{r['task_id'] for r in fresh if r['resolution_state']==state}
        for state in ('PROVIDER_RETRY','NEW_RESEARCH_REQUIRED','MANUAL_REVIEW')}
assert not groups['PROVIDER_RETRY']&groups['NEW_RESEARCH_REQUIRED']
assert not groups['MANUAL_REVIEW']&(groups['PROVIDER_RETRY']|groups['NEW_RESEARCH_REQUIRED'])
assert status['resolution_queues']=={key:len(ids) for key,ids in groups.items()}
web=read(OUTPUT/'new_research/research_handoff.json')
retry=ResultBundle.model_validate_json((OUTPUT/'provider_retry/research_results.retry.json').read_text(encoding='utf-8'))
template=ResultBundle.model_validate_json((OUTPUT/'new_research/research_results.template.json').read_text(encoding='utf-8'))
assert {t['task_id'] for t in web['tasks']}==groups['NEW_RESEARCH_REQUIRED']
assert {r.task_id for r in template.results}==groups['NEW_RESEARCH_REQUIRED']
assert {r.task_id for r in retry.results}==groups['PROVIDER_RETRY']
assert read(OUTPUT/'new_research/research_results.schema.json')==ResultBundle.model_json_schema()
for folder in ['new_research','provider_retry']:
    handoff=read(OUTPUT/folder/'research_handoff.json')
    registry=read(ROOT/'data/research/handoffs'/f"{handoff['handoff_id']}.json")
    assert registry['snapshot']==snapshot(pack) and registry['tasks']==handoff['tasks']
for file in ['provider-dry-run.txt','template-dry-run.txt']:
    report=read(REPORT/file)
    assert report['summary']['matched']==16 and report['summary']['rejected']==0
    assert report['summary']['invalid_sources']==0 and report['summary']['missing_pois']==0
    assert report['ai_usage']['stats']['calls']==0 and report['ai_usage']['paid_feature_calls']==0
    save(file.replace('.txt','.json'),report)
normal_text=(REPORT/'normal-export-check.txt').read_text(encoding='utf-8')
normal=json.JSONDecoder().raw_decode(normal_text[normal_text.index('{'):])[0]
assert normal['total']==16 and normal['excluded_resolution_queues']=={'PROVIDER_RETRY':16,'MANUAL_REVIEW':4}
assert normal['handoff_id']==web['handoff_id']
validation=validate_release_package(pack)
tests=re.search(r'(\d+) passed in ([\d.]+)s',(REPORT/'tests-final.txt').read_text(encoding='utf-8'))
targeted=re.search(r'(\d+) passed in ([\d.]+)s',(REPORT/'tests-targeted-final.txt').read_text(encoding='utf-8'))
assert tests and targeted
verification={'protected_files_checked':len(before['protected_files']),'changed_protected_files':changed,
    'accepted_real_required_images_unchanged':read(pack/'usability.json')['real_required_verified'],
    'resolution_queues':status['resolution_queues'],'normal_web_export_tasks':normal['total'],
    'full_tests':{'passed':int(tests[1]),'seconds':float(tests[2])},
    'resolution_tests':{'passed':int(targeted[1]),'seconds':float(targeted[2])},
    'provider_calls':0,'paid_calls':0,'validation':validation,
    'manual_review':[r['name'] for r in fresh if r['resolution_state']=='MANUAL_REVIEW']}
assert verification['accepted_real_required_images_unchanged']==16
save('verification.json',verification)
for filename in ['research_handoff.md','research_handoff.json','research_results.template.json','research_results.schema.json']:
    assert (OUTPUT/'new_research'/filename).is_file()
status['verification']=verification
(OUTPUT/'status_report.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
append=f"""\n\n## Verification\n\nFull pytest: **{tests[1]} passed in {tests[2]}s**. Resolution tests: **{targeted[1]} passed in {targeted[2]}s**.\n\nBoth 16-task bundles match their registered snapshots and pass importer dry-run validation. Normal web export includes 16 research tasks and excludes 16 provider holds plus 4 manual reviews.\n\n## Safety\n\n**{len(before['protected_files'])} protected file hashes matched**: accepted images, latest/historical packs, human curation, configuration, existing research inputs, histories, heads and handoffs unchanged. Verified required images remain **16/52**. City Lab was not touched. No city pack was published and no provider retry was executed. Provider/paid calls: **0**.\n\n## Generated files\n\n"""
paths=['status_report.md','status_report.json','provider_retry/retry_tasks.json','provider_retry/retry_tasks.md',
       'provider_retry/research_results.retry.json','new_research/research_handoff.md','new_research/research_handoff.json',
       'new_research/research_results.template.json','new_research/research_results.schema.json',
       'manual_review/review_tasks.json','manual_review/review_tasks.md']
append+='\n'.join('- `'+str(OUTPUT/name)+'`' for name in paths)+'\n'
md=(OUTPUT/'status_report.md').read_text(encoding='utf-8').split('\n\n## Verification')[0]
(OUTPUT/'status_report.md').write_text(md+append,encoding='utf-8')
print(json.dumps(verification,ensure_ascii=False,indent=2))
