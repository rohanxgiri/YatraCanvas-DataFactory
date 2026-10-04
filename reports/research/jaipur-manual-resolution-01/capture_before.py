import json, hashlib
from pathlib import Path
ROOT=Path.cwd(); REPORT=ROOT/'reports/research/jaipur-manual-resolution-01'
prior=json.loads((ROOT/'reports/research/jaipur-round2-import/before.json').read_text(encoding='utf-8'))
paths=set(prior['protected_files'])
paths.add('datafactory/research/resolution.py')
for directory in ['releases/india/rajasthan/jaipur/v3-research-jaipur-images-03','data/research/heads','data/research/handoffs','data/research/imports','data/research/import_inputs','data/research/exports/jaipur/required_images_remaining']:
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*') if p.is_file())
paths.update(['datafactory/research/importer.py','datafactory/research/schemas.py','datafactory/pipeline/media_assurance.py','datafactory/pipeline/media_policy.py'])
protected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}
pack=ROOT/'releases/india/rajasthan/jaipur/v3-research-jaipur-images-03'
record={'source_pack':str(pack),'protected_files':protected,'usability':json.loads((pack/'usability.json').read_text(encoding='utf-8')),'code_before':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['datafactory/research/resolution.py','tests/test_research_resolution.py','docs/local-research-workflow.md']}}
(REPORT/'before.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('Protected hashes recorded:',len(protected))
