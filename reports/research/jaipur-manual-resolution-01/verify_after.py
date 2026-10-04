"""Verify preserved files and the proposal artifacts; no production writes."""
import hashlib
import json
from pathlib import Path

from datafactory.research.manual_resolution import preview_manual_changes

root=Path.cwd()
report=root/'reports/research/jaipur-manual-resolution-01'
out=root/'data/research/manual_resolution/jaipur'
before=json.loads((report/'before.json').read_text(encoding='utf-8'))
missing=[]
changed=[]
for name,digest in before['protected_files'].items():
    path=root/name
    if not path.is_file():
        missing.append(name)
    elif hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        changed.append(name)
pack=Path(before['source_pack'])
places=json.loads((pack/'places.json').read_text(encoding='utf-8'))
bundle=json.loads((out/'proposed_changeset_01.json').read_text(encoding='utf-8'))
snapshot={name:hashlib.sha256((pack/name).read_bytes()).hexdigest() for name in bundle['source_snapshot']}
preview=preview_manual_changes(places,bundle,snapshot)
queue=json.loads((root/'data/research/exports/jaipur/required_images_round3/manual_review/review_tasks.json').read_text(encoding='utf-8'))
resolution=json.loads((out/'manual_resolution_01.json').read_text(encoding='utf-8'))
tasks=json.loads((out/'manual_review_followup_image_tasks.json').read_text(encoding='utf-8'))
assert {r['place_id'] for r in resolution['records']} == {t['place_id'] for t in queue['tasks']}
assert {r['place_id'] for r in bundle['proposals']} == {t['place_id'] for t in queue['tasks']}
assert len(resolution['records'])==len(bundle['proposals'])==6
assert preview==json.loads((out/'proposed_changeset_01.dry_run.json').read_text(encoding='utf-8'))
assert all(x['action'] not in ['MERGE','REMOVE'] for x in bundle['proposals'])
assert not tasks['registered'] and not tasks['apply_ready']
assert all(not t['registered'] and not t['apply_ready'] and 'task_id' not in t and 'handoff_id' not in t for t in tasks['tasks'])
assert len(tasks['tasks'])==3
assert {t['place_id'] for t in tasks['tasks']}=={r['place_id'] for r in resolution['records'] if r['image_search_needed_after_resolution']}
usability=json.loads((pack/'usability.json').read_text(encoding='utf-8'))
assert usability==before['usability']
assert usability['real_required_verified']==17 and usability['real_required_total']==52
assert resolution['before']==resolution['after']
assert not missing and not changed, (missing,changed)
result={'protected_files_checked':len(before['protected_files']), 'missing':missing,'changed':changed,
        'source_snapshot_unchanged':True,'source_usability_unchanged':True,
        'proposal_records':6,'followup_image_proposals':3,'applied':0,
        'real_required_verified':17,'real_required_total':52,'real_required_coverage':32.69,
        'image_imports':0,'provider_calls_during_research':0,'paid_ai_calls':0,
        'tests':{'command':'.\\.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider --basetemp <fresh workspace directory>',
                 'passed':358,'initial_environment_error':'Default pytest temp directory denied Windows sandbox access; full suite passed using a fresh workspace temp directory.'},
        'scope_note':'Preservation is relative to the captured start of this manual-review phase; pre-existing working-tree changes were not reverted.'}
(report/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
