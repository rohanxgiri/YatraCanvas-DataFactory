"""Reproducible offline Jaipur safe apply and protected-data audit.

Run with python -m scripts.apply_jaipur_safe_resolution baseline|dry-run|apply|queues|verify.
"""
import json
import os
import sys
from pathlib import Path

from datafactory.config.settings import get_settings
from datafactory.utils.atomic import atomic_json
from datafactory.utils.hashing import compute_sha256
from datafactory.research.manual_apply import apply_manual_changes

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/research/jaipur-safe-resolution-01'
PROPOSAL = ROOT / 'data/research/manual_resolution/jaipur/proposed_changeset_01.json'
SELECTED = ['yc_in_rj_jaipur_' + name for name in ('suraj_pol_gate', 'india_gate', 'rooftop_view_stairs')]
BEFORE = ROOT / 'releases/india/rajasthan/jaipur/v3-research-jaipur-images-03'
AFTER = ROOT / 'releases/india/rajasthan/jaipur/v3-research-jaipur-manual-01'
LAB = ROOT.parent / 'YatraCanvas-CityPack-Lab'


def protected_inventory():
    files, errors = {}, []
    roots = [ROOT / name for name in ('releases', 'assets', 'data/media', 'data/curated',
             'data/research/manual_resolution/jaipur', 'config', 'datafactory')]
    roots.append(LAB)
    for base in roots:
        if not base.exists():
            continue
        for directory, dirs, names in os.walk(base, onerror=lambda error: errors.append(str(error))):
            dirs[:] = [name for name in dirs if name not in {'node_modules', '.git', '.next', '__pycache__', '.venv', '.pytest_cache'}]
            for name in names:
                path = Path(directory) / name
                # These are the only implementation files changed by this phase.
                if path in {ROOT / 'datafactory/research/manual_apply.py', ROOT / 'datafactory/pipeline/offline_export.py'}:
                    continue
                try:
                    files[str(path)] = compute_sha256(path)
                except OSError as error:
                    errors.append(str(error))
    return {'files': files, 'errors': errors}


def queues():
    from datafactory.research.resolution import export_resolution_queues, MEDIA_INSTRUCTIONS
    from datafactory.research.export import make_tasks, _write_handoff, read_assurance
    settings = get_settings()
    queue_dir = REPORT / 'resolution_queues'
    if queue_dir.exists():
        queue_dir = REPORT / 'resolution_queues-02'
    summary = export_resolution_queues(AFTER, queue_dir, settings=settings)
    city = json.loads((AFTER / 'city.json').read_text(encoding='utf-8'))
    places = json.loads((AFTER / 'places.json').read_text(encoding='utf-8'))
    tasks = make_tasks(places, city, AFTER, read_assurance(AFTER))
    suraj = next(t for t in tasks if t['place_id'] == SELECTED[0] and t['type'] == 'REAL_PRIMARY_IMAGE')
    reviewed = json.loads(PROPOSAL.read_text(encoding='utf-8'))['proposals'][0]
    suraj['known_evidence']['reviewed_identity_sources'] = reviewed['evidence']
    suraj['known_evidence']['excluded_source_pages'] = ['https://commons.wikimedia.org/wiki/File:Amber_Fort_-_Suraj_pol.jpg']
    suraj['known_evidence']['excluded_entities'] = ['Amber Fort Suraj Pol', 'Suraj Pol inside Amer Fort']
    suraj['research_instruction'] = ("Find a REAL reusable photograph of the Old Jaipur City Suraj Pol Gate. "
        "Coordinates: 26.919156, 75.844935. OSM ID: way/863303428. Wikidata ID: Q140770830. "
        "Do NOT use Amber Fort Suraj Pol, Suraj Pol inside Amer Fort, or Amber_Fort_-_Suraj_pol.jpg. "
        "The photograph should depict the eastern gate of Jaipur's historic walled city. "
        "Use the aliases and municipal identity evidence in known_evidence. All existing media assurance gates apply.")
    handoff = _write_handoff(AFTER, REPORT / 'suraj_pol_research', city, [suraj], tasks, settings, instructions=MEDIA_INSTRUCTIONS)
    atomic_json(REPORT / 'queues.receipt.json', {'queues': summary, 'suraj_handoff': handoff})
    return {'queues': summary['resolution_queues'], 'suraj_handoff': handoff['handoff_id']}


def verify():
    from datafactory.pipeline.validate import validate_release_package
    from datafactory.research.export import snapshot, find_pack
    before = json.loads((REPORT / 'protected.before.json').read_text(encoding='utf-8'))
    supplement = REPORT / 'protected.supplement.json'
    extra_count = 0
    if supplement.exists():
        extra = json.loads(supplement.read_text(encoding='utf-8'))
        proof = json.loads((REPORT / 'protected.supplement.verification.json').read_text(encoding='utf-8'))
        assert not extra['errors'] and not proof['changed'], (extra['errors'], proof)
        assert proof['baseline_sha256'] == compute_sha256(supplement)
        extra_count = len(extra['files'])
    changed = [path for path, sha in before['files'].items() if not Path(path).is_file() or compute_sha256(Path(path)) != sha]
    intended_code = {str(ROOT / 'datafactory/research/resolution.py')}
    protected_changed = [path for path in changed if path not in intended_code]
    current = protected_inventory()
    new_protected = [path for path in current['files'] if path not in before['files'] and not Path(path).is_relative_to(AFTER)]
    assert not protected_changed, protected_changed
    assert not new_protected, new_protected
    assert current['errors'] == before['errors'], current['errors']
    assert not before['errors'] or supplement.exists(), before['errors']
    a = {p['id']: p for p in json.loads((BEFORE / 'places.json').read_text(encoding='utf-8'))}
    b = {p['id']: p for p in json.loads((AFTER / 'places.json').read_text(encoding='utf-8'))}
    assert a.keys() == b.keys()
    assert all(a[pid] == b[pid] for pid in a if pid not in SELECTED)
    assert all(a[pid]['images'] == b[pid]['images'] for pid in a)
    old_assurance = json.loads((BEFORE / 'media_assurance.json').read_text(encoding='utf-8'))
    assert old_assurance == json.loads((AFTER / 'media_assurance.json').read_text(encoding='utf-8'))
    verified = [pid for pid in a if old_assurance.get(pid, {}).get('media', {}).get('verified') is True]
    assert len(verified) == 17
    for pid in verified:
        image = a[pid]['images']['primary']
        for relative in (image['local_path'], image['thumbnail_path']):
            assert compute_sha256(BEFORE / relative) == compute_sha256(AFTER / relative)
    provenance = json.loads((BEFORE / 'field_provenance.json').read_text(encoding='utf-8'))
    new_provenance = json.loads((AFTER / 'field_provenance.json').read_text(encoding='utf-8'))
    assert new_provenance[:len(provenance)] == provenance
    import sqlite3
    from contextlib import closing
    import pyarrow.parquet as pq
    parquet = {p['id']: p for p in pq.read_table(AFTER / 'places.parquet').to_pylist()}
    with closing(sqlite3.connect(AFTER / 'yatracanvas.db')) as connection:
        for pid in SELECTED:
            place = b[pid]
            assert parquet[pid]['osm_id'] == place['external_ids']['osm_id']
            assert json.loads(parquet[pid]['alternate_names']) == place['alternate_names']
            sql = connection.execute('SELECT name, description, tier, osm_id FROM places WHERE id=?', (pid,)).fetchone()
            assert sql == (place['name'], place['description'], place['tier'], place['external_ids']['osm_id'])
    checksums = json.loads((AFTER / 'checksums.json').read_text(encoding='utf-8'))
    assert set(checksums) == {p.relative_to(AFTER).as_posix() for p in AFTER.rglob('*')
                            if p.is_file() and p.name not in {'checksums.json', 'manifest.json'}}
    assert json.loads((AFTER / 'manifest.json').read_text(encoding='utf-8'))['checksums'] == checksums
    assert find_pack('Jaipur').resolve() == AFTER.resolve()
    registry = json.loads((REPORT / 'suraj_pol_research/research_handoff.json').read_text(encoding='utf-8'))
    registered = json.loads((ROOT / 'data/research/handoffs' / (registry['handoff_id'] + '.json')).read_text(encoding='utf-8'))
    assert registered['snapshot'] == snapshot(AFTER)
    assert registered['source_pack'].endswith(AFTER.name)
    queue_receipt = json.loads((REPORT / 'queues.receipt.json').read_text(encoding='utf-8'))
    queue = json.loads((Path(queue_receipt['queues']['output']) / 'status_report.json').read_text(encoding='utf-8'))
    assert SELECTED[1] not in {t['place_id'] for t in queue['tasks']}
    assert SELECTED[2] not in {t['place_id'] for t in queue['tasks']}
    manual = {t['place_id']: t for t in queue['tasks'] if t['resolution_state'] == 'MANUAL_REVIEW'}
    for name in ('jain_mandir', 'haveli', 'elephant_riding'):
        assert 'yc_in_rj_jaipur_' + name in manual
    assert 'PIN_REVIEW_REQUIRED' in manual['yc_in_rj_jaipur_jain_mandir']['review_flags']
    assert any(t['place_id'] == SELECTED[0] and t['resolution_state'] == 'NEW_RESEARCH_REQUIRED' for t in queue['tasks'])
    result = {'validation': validate_release_package(AFTER), 'protected_files_checked': len(before['files']) + extra_count,
              'changed_protected_files': protected_changed, 'intended_code_changes_after_baseline': changed,
              'new_unexpected_protected_files': new_protected,
              'verified_images_preserved': len(verified), 'assurance_unchanged': True,
              'unselected_records_unchanged': len(a) - len(SELECTED), 'provenance_history_preserved': True,
              'reviewed_fields_match_sqlite_and_parquet': True, 'complete_checksum_inventory': True,
              'city_lab_files_checked': sum(Path(p).is_relative_to(LAB) for p in before['files']),
              'paid_ai_calls': 0, 'fresh_registered_snapshot': True, 'manual_review_flags': {
                  pid: row.get('review_flags', []) for pid, row in manual.items()}}
    atomic_json(REPORT / 'validation_and_safety.json', result)
    return result


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'baseline':
        target = REPORT / 'protected.before.json'
        if target.exists():
            raise ValueError('Baseline already captured; do not overwrite protection evidence')
        result = protected_inventory()
        atomic_json(target, result)
        print(json.dumps({'protected_files': len(result['files']), 'errors': result['errors']}))
    elif mode in {'dry-run', 'apply'}:
        receipt = apply_manual_changes(PROPOSAL, SELECTED, REPORT / ('apply' if mode == 'apply' else 'dry_run'), apply=mode == 'apply')
        print(json.dumps({k: v for k, v in receipt.items() if k not in {'usability_after', 'rows'}}))
    elif mode == 'supplement-baseline':
        # Only previously unreadable roots; retain the original baseline evidence.
        target = REPORT / 'protected.supplement.json'
        if target.exists():
            raise ValueError('Supplement already captured')
        files, errors = {}, []
        baseline = json.loads((REPORT / 'protected.before.json').read_text(encoding='utf-8'))
        for message in baseline['errors']:
            base = Path(message.split(': ', 1)[1].strip("'").replace('\\\\', '\\'))
            for directory, _, names in os.walk(base, onerror=lambda error: errors.append(str(error))):
                for name in names:
                    path = Path(directory) / name
                    try:
                        files[str(path)] = compute_sha256(path)
                    except OSError as error:
                        errors.append(str(error))
        atomic_json(target, {'files': files, 'errors': errors})
        print(json.dumps({'protected_files_added': len(files), 'errors': errors}))
    elif mode == 'queues':
        print(json.dumps(queues()))
    elif mode == 'verify-supplement':
        source = REPORT / 'protected.supplement.json'
        baseline = json.loads(source.read_text(encoding='utf-8'))
        changed = [path for path, sha in baseline['files'].items() if not Path(path).is_file() or compute_sha256(Path(path)) != sha]
        atomic_json(REPORT / 'protected.supplement.verification.json', {'baseline_sha256': compute_sha256(source),
                    'files_checked': len(baseline['files']), 'changed': changed})
        print(json.dumps({'files_checked': len(baseline['files']), 'changed': changed}))
    elif mode == 'verify':
        print(json.dumps(verify()))
    else:
        raise ValueError(mode)
